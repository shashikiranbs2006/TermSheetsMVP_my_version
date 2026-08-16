"""
models/outputs.py — Stage 6 output (Emit).

TODO: Riskwolf payload contract is not yet known.
See docs/source/wbcis_extraction_schema.md §10 open question:
  "Riskwolf JSON contract — need the target payload schema + API sandbox
   to confirm step 5 output shape."

riskwolf_payload is stubbed as Optional[dict] until that contract is
confirmed.  Replace this stub before implementing Stage 6 logic.
Do NOT treat the absence of a contract as a reason to invent a shape.
"""

from typing import Optional

from pydantic import BaseModel

from models.validated_termsheet import ValidatedTermsheet


class Outputs(BaseModel):
    """
    Stage 6 (Emit) boundary contract.

    Attributes:
        termsheet:         The Stage 5 validated output being emitted.
        human_readable:    Formatted plain-text termsheet for underwriter review.
                           Produced by the deterministic emission path.
        riskwolf_payload:  TODO — Riskwolf JSON payload.  Shape unknown pending
                           API contract confirmation (see §10 of extraction schema).
                           Stubbed as Optional[dict]; None until implemented.
    """

    termsheet: ValidatedTermsheet
    human_readable: str
    riskwolf_payload: Optional[dict] = None  # TODO: replace when Riskwolf contract confirmed
