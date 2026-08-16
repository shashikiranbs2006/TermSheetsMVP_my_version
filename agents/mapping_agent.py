"""
agents/mapping_agent.py — Strands + Bedrock Mapping Agent

Wraps AWS Bedrock via Strands Agent to map reconstructed peril tables
into archetype-specific schema JSON. Operates on one reconstructed peril
at a time.

Rules Enforced:
  - Never invent missing values.
  - Blank source -> null in output, never 0.
  - "Fix" numbers that look wrong is strictly prohibited.
  - Date normalization to ISO YYYY-MM-DD format (e.g. "01-Jul. to 15-Jul." -> {"start": "2019-07-01", "end": "2019-07-15"}).
  - Output is strictly valid JSON conforming to the requested archetype structure.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

import strands
from strands.models import BedrockModel

# ---------------------------------------------------------------------------
# Bedrock Model Configuration
# ---------------------------------------------------------------------------

DEFAULT_MODEL_ID = "amazon.nova-lite-v1:0"
DEFAULT_REGION = "us-east-1"


SYSTEM_PROMPT = """You are a specialized WBCIS insurance termsheet mapping agent.
Your task is to take a single deterministically reconstructed peril table from a WBCIS termsheet and map it into the target archetype JSON structure.

CRITICAL RULES:
1. NEVER invent missing values. If a field or parameter is not present in the input, output null.
2. BLANK IS NULL, NEVER ZERO. If a source cell is blank or missing, set value to null (e.g., strike_2: null, rate_2: null). Never output 0 for missing values.
3. NEVER "fix" or alter numbers that appear unusual. Preserve the exact numeric values from the input.
4. NORMALIZE DATES to ISO YYYY-MM-DD format based on the Indian agricultural scheme year:
   - For Scheme Year "YYYY-YY" (e.g. "2019-20", running from July 2019 to June 2020):
     * Months July, August, September, October, November, December belong to the first year (2019).
     * Months January, February, March, April, May, June belong to the second year (2020).
     * Examples:
       - "01-Jul. to 15-Jul." -> {"start": "2019-07-01", "end": "2019-07-15"}
       - "15 Oct. to 31 Oct." -> {"start": "2019-10-15", "end": "2019-10-31"}
       - "01 Feb. To 14 Feb." -> {"start": "2020-02-01", "end": "2020-02-14"}
       - "16 April to 30 April" -> {"start": "2020-04-16", "end": "2020-04-30"}
   - If the raw text contains an explicit 2-digit year (e.g. "1-Jun-19" -> 2019, "30-Apr-20" -> 2020), use that explicit year.
5. Confidence should be a float number between 0.85 and 1.0 (e.g. 0.95).
6. Output ONLY valid JSON conforming to the requested schema. Do NOT include markdown code fences or explanatory text.
"""

ARCHETYPE_PROMPTS = {
    "temperature_phased": """
Target archetype: "temperature_phased"
Target JSON structure:
{
  "measure": "max_temperature",
  "unit": "°C",
  "direction": "upward",
  "strike": <float>,
  "exit": <float>,
  "payout_rate": <float>,
  "payout_rate_unit": "Rs/°C",
  "max_payout": <float>,
  "phases": [
    {
      "label": "<e.g. I, II, ...>",
      "period": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
      "trigger": <float>
    }
  ],
  "confidence": <float between 0.0 and 1.0>
}
""",
    "rainfall_multistrike": """
Target archetype: "rainfall_multistrike"
Target JSON structure:
{
  "measure": "aggregate_rainfall",
  "unit": "mm",
  "direction": "deficit",
  "rate_unit": "Rs/mm",
  "phases": [
    {
      "label": "Phase I",
      "sub_periods": [
        {
          "period": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
          "strike_1": <float>,
          "strike_2": <float or null>,
          "exit": <float>,
          "rate_1": <float>,
          "rate_2": <float or null>,
          "max_payout": <float>
        }
      ]
    }
  ],
  "total_payout": <float>,
  "confidence": <float between 0.0 and 1.0>
}
Note: Each sub_period has its own strike_1, strike_2, exit, rate_1, rate_2, max_payout.
""",
    "rainfall_single_payout": """
Target archetype: "rainfall_single_payout"
Target JSON structure:
{
  "measure": "aggregate_rainfall",
  "unit": "mm",
  "direction": "unseasonal",
  "payout_mode": "single",
  "periods": [
    {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}
  ],
  "strike_1": <float>,
  "strike_2": <float or null>,
  "exit": <float>,
  "rate_1": <float>,
  "rate_2": <float or null>,
  "rate_unit": "Rs/mm",
  "max_payout": <float>,
  "confidence": <float between 0.0 and 1.0>
}
""",
    "wind_phased": """
Target archetype: "wind_phased"
Target JSON structure:
{
  "measure": "max_wind_speed",
  "unit": "km/h",
  "direction": "upward",
  "strike": <float>,
  "exit": <float>,
  "payout_rate": <float>,
  "payout_rate_unit": "Rs/km/h",
  "max_payout": <float>,
  "trigger_blocks": [
    {
      "block_label": "block_1",
      "period": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
      "phases": [
        {
          "label": "<e.g. I, II, III>",
          "period": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
          "trigger": <float>
        }
      ]
    }
  ],
  "confidence": <float between 0.0 and 1.0>
}
"""
}


class MappingAgent:
    """
    Strands Agent that maps reconstructed peril tables to schema JSON using AWS Bedrock.
    """

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL_ID,
        region_name: str = DEFAULT_REGION,
    ):
        self.model_id = model_id
        self.region_name = region_name
        self.model = BedrockModel(
            model_id=model_id,
            region_name=region_name,
            temperature=0.0,
        )
        self.agent = strands.Agent(
            model=self.model,
            system_prompt=SYSTEM_PROMPT,
        )
        self.interaction_logs: list[dict[str, Any]] = []

    def map_peril(
        self,
        reconstructed_peril: dict[str, Any],
        scheme_year: str = "2019-20",
    ) -> dict[str, Any]:
        """
        Map a single reconstructed peril dictionary into its target archetype JSON structure.
        """
        archetype = reconstructed_peril.get("archetype", "")
        peril_id = reconstructed_peril.get("peril_id", "")
        arch_prompt = ARCHETYPE_PROMPTS.get(archetype, "")

        prompt = f"""Scheme Year: {scheme_year}
Peril ID: {peril_id}
Archetype: {archetype}

{arch_prompt}

Reconstructed Peril Input Data:
{json.dumps(reconstructed_peril, indent=2)}

Map this input data into the exact target JSON structure. Return ONLY valid JSON:"""

        response = self.agent(prompt)
        response_text = getattr(response, "text", str(response)).strip()

        # Clean markdown code blocks if present
        clean_text = response_text
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()

        try:
            parsed = json.loads(clean_text)
        except json.JSONDecodeError as exc:
            # Fallback regex extraction if conversational preamble exists
            match = re.search(r"\{[\s\S]*\}", response_text)
            if match:
                parsed = json.loads(match.group(0))
            else:
                raise ValueError(f"Agent failed to return valid JSON for peril '{peril_id}': {response_text}") from exc

        # Record interaction log
        self.interaction_logs.append({
            "peril_id": peril_id,
            "archetype": archetype,
            "model_id": self.model_id,
            "prompt": prompt,
            "raw_response": response_text,
            "parsed_output": parsed,
        })

        return parsed
