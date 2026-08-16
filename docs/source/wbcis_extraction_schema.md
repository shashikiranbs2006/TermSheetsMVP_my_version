# WBCIS Termsheet Engine — Extraction Schema Spec (MVP)

**Status:** Draft v1 — build spec for interns
**Scope:** WBCIS 2019–20 "Annexure 3" government termsheet format (Rajasthan samples)
**Purpose:** Define the target structured schema that the Extraction Agent produces and the Governed Libraries are built around. Everything downstream (adaptation, index recommendation, validation, JSON output) is built against *this* spec. Lock this before writing extraction code.

---

## 1. Why this document exists

The five sample termsheets (Guava/Sawai Madhopur, Kinnow/Sri Ganganagar, Onion/Ajmer, Onion/Alwar, Orange/Jhalawar) are all the same national WBCIS format but contain **different peril structures on the same document**. The core engineering insight:

> The unit of standardization is **not** the crop or the region. It is the **peril archetype**. A handful of repeating peril structures cover essentially the entire WBCIS set. Model the archetypes correctly and one crop-region becomes every crop-region.

The Onion Ajmer vs Onion Alwar pair is structurally identical and differs only in calibrated values — that pair **is** the product thesis (standardize structure, adapt values) and doubles as the first golden-answer eval (see §8).

---

## 2. Document-level schema (common to every termsheet)

Extracted once per document, regardless of perils present.

| Field | Type | Source in sample | Notes |
|---|---|---|---|
| `scheme_name` | string | Header ("Weather Based Crop Insurance Scheme") | Normalize to `WBCIS` |
| `scheme_year` | string | Header ("2019-20") | |
| `state` | string | State field | **Normalize typos** — "Rajsthan" → "Rajasthan" |
| `district` | string | District field | "S.Madhopur" → "Sawai Madhopur"; keep raw + normalized |
| `crop` | string | Crop field | May include season, e.g. "Onion kharif", "Onion" |
| `season` | string \| null | Parsed from crop field | "kharif" / "rabi" / null |
| `unit` | string | Unit field | e.g. "HECTARE" |
| `reference_weather_station` | string | RWS field | Often "As Per Notification" |
| `annexure_ref` | string | Top-right | e.g. "Annexure 3" |
| `perils` | array | Body | Array of peril objects — see §3 |
| `premium` | object | "Premium Description" block | See §2.1 |
| `source_meta` | object | — | `{file_name, page_range, is_scan: bool, ocr_used: bool}` |

### 2.1 `premium` object

| Field | Type | Notes |
|---|---|---|
| `total_sum_insured` | number | Rs |
| `gross_premium` | number \| null | **Frequently blank** in samples |
| `premium_pct` | number \| null | **Frequently blank** |
| `farmers_premium` | number \| null | Present in Guava sample |

> **Known data trap:** Guava sample shows `total_premium = 0` but `farmers_premium = 1938`. Do not silently "fix" contradictions — capture both and flag in validation (§7).

---

## 3. The peril archetype model (the core of the engine)

Every peril on a termsheet resolves to exactly one **archetype**. Each peril object carries a shared envelope plus an archetype-specific `structure`.

### Shared peril envelope

```json
{
  "peril_id": "high_temperature | deficit_rainfall | unseasonal_rainfall | excess_rainfall | high_wind_speed",
  "peril_label_raw": "1. HIGH TEMPERATURE",
  "archetype": "temperature_phased | rainfall_multistrike | rainfall_single_payout | wind_phased",
  "cover_objective": "string",
  "event_definition": "string",
  "cover_period": { "start": "YYYY-MM-DD", "end": "YYYY-MM-DD" },
  "structure": { ... }   // archetype-specific, see §4
}
```

The four archetypes observed across all five samples:

| Archetype | Appears in | Distinguishing shape |
|---|---|---|
| **A. `temperature_phased`** | Kinnow, Orange | N phases (usually 6), one trigger per phase, single strike + exit + payout-rate spanning all phases |
| **B. `rainfall_multistrike`** | Guava, Kinnow, Orange, Onions | Phase I / Phase II, each with sub-period date columns; 1–2 strikes, 1–2 rates, per-phase max payout + combined total |
| **C. `rainfall_single_payout`** | all (2B covers) | Single flat cover, no phase structure; 1–2 strikes, 1–2 rates, single max payout |
| **D. `wind_phased`** | Guava, Kinnow, Orange | N phases (4 or 6), sometimes grouped in 2 trigger blocks; one trigger per phase, single strike + exit + payout-rate |

> **Variant handling within an archetype:** Archetype B has a one-strike variant (Onions: Strike 1 / Rate 1 only) and a two-strike variant (Orange/Kinnow/Guava: Strike 1 + Strike 2, Rate 1 + Rate 2). Model these as the same archetype with optional `strike_2` / `rate_2` fields — NOT as separate archetypes.

---

## 4. Archetype field specs

### 4.A `temperature_phased`

```json
{
  "measure": "max_temperature",
  "unit": "°C",
  "strike": 4,          // single value, spans all phases
  "exit": 25,           // single value, spans all phases
  "payout_rate": 1428.57,
  "payout_rate_unit": "Rs/°C",
  "max_payout": 30000,
  "phases": [
    { "label": "I",  "period": {"start":"2020-02-01","end":"2020-02-14"}, "trigger": 28.5 },
    { "label": "II", "period": {"start":"2020-02-15","end":"2020-02-28"}, "trigger": 31.0 }
    // ... up to VI
  ]
}
```
*Direction of cover:* upward deviation of max temperature above trigger. Capture `direction: "upward"` from event definition.

### 4.B `rainfall_multistrike`

```json
{
  "measure": "aggregate_rainfall",
  "unit": "mm",
  "direction": "deficit",   // "deficit" or "excess", from cover objective
  "phases": [
    {
      "label": "Phase I",
      "sub_periods": [ {"start":"2019-06-25","end":"2019-08-15"} ],  // may be 1 or more
      "strike_1": 65,
      "strike_2": 20,        // null in one-strike variant
      "exit": 0,
      "rate_1": 100.00,
      "rate_2": 525.00,      // null in one-strike variant
      "rate_unit": "Rs/mm",
      "max_payout": 15000
    },
    { "label": "Phase II", ... }
  ],
  "total_payout": 30000     // "Payout Phase I & II (Rs)"
}
```
> **Extraction difficulty is highest here.** Phase columns contain nested date sub-periods (two-level headers), and Strike/Exit cells are often merged across sub-columns. This is the archetype to prove extraction on first (§9).

### 4.C `rainfall_single_payout`

```json
{
  "measure": "aggregate_rainfall",
  "unit": "mm",
  "direction": "excess | unseasonal",
  "payout_mode": "single",
  "periods": [ {"start":"2019-06-01","end":"2019-06-20"} ],  // sometimes multiple date columns
  "strike_1": 20,
  "strike_2": 45,     // optional
  "exit": 60,
  "rate_1": 279.6,
  "rate_2": 1087.33,  // optional
  "rate_unit": "Rs/mm",
  "max_payout": 23300
}
```

### 4.D `wind_phased`

```json
{
  "measure": "max_wind_speed",
  "unit": "km/h",
  "direction": "upward",
  "strike": 5,           // single, spans phases
  "exit": 40,            // single, spans phases
  "payout_rate": 553.57,
  "payout_rate_unit": "Rs/km/h",
  "max_payout": 19375,
  "trigger_blocks": [    // some sheets split 6 phases into 2 blocks
    {
      "block_label": "block_1",
      "period": {"start":"2019-10-15","end":"2019-11-30"},
      "phases": [
        {"label":"I","period":{"start":"2019-10-15","end":"2019-10-31"},"trigger":50}
        // ...
      ]
    }
  ]
}
```
> Guava has 4 flat phases; Kinnow/Orange split 6 phases into 2 trigger blocks with their own payout rate. Model `trigger_blocks` as an array so both fit (single block = flat case).

---

## 5. Canonical output shape

```json
{
  "document": { /* §2 document-level */ },
  "perils": [ /* array of §3 peril envelopes */ ],
  "extraction_confidence": {
    "overall": 0.0,
    "per_field": { "...": 0.0 }
  },
  "flags": [ /* validation flags, §7 */ ]
}
```
Every extracted value carries a confidence score. Low-confidence fields drive the Underwriter Review Notes — the system's trust layer.

---

## 6. Extraction challenges observed in the real samples

These are not hypothetical — each is present in your five documents. The interns should have a test case for each before calling extraction "done."

1. **Typos / abbreviations** — "Rajsthan", "S.Madhopur", "Feb." vs "Feb". Normalize but keep raw.
2. **Merged cells** — Strike/Exit span all phase columns (all wind + temp sheets). Naive row parsing mis-aligns these.
3. **Two-level headers** — Phase I → {sub-period date columns}. Hierarchical, not flat.
4. **Blank fields** — INDEX row, Gross Premium, Premium % routinely empty. Missing ≠ zero.
5. **Internal contradictions** — premium = 0 vs farmer's premium ≠ 0. Capture, don't correct.
6. **Multi-peril documents** — one file = 2–4 perils, each a different archetype. Section headers ("1.", "2.", "2B.", "3.") delimit them.
7. **Split trigger blocks** — 6 wind phases presented as two 3-phase blocks with separate payout rates.
8. **Date parsing** — "01 April to 15 April", "1 SEP.. TO 30 SEPT" — inconsistent formatting, needs robust parsing to ISO dates.

---

## 7. Validation rules (feeds the Validation Agent + Review Notes)

Minimum checks for MVP:

- **Completeness:** every archetype's required fields present; flag blanks that shouldn't be blank.
- **Monotonicity / sanity:** exit vs strike relationship consistent with cover direction (e.g. deficit: exit ≤ strike).
- **Payout arithmetic:** per-phase max payouts roughly reconcile to stated total.
- **Premium consistency:** flag the premium=0 / farmer's-premium≠0 class of contradiction.
- **SI presence:** total sum insured must be present and > 0.
- **Confidence threshold:** any field below threshold → routed to Underwriter Review Notes, not auto-passed.

Output = a structured validation report, not a pass/fail boolean. In insurance the flags *are* the product.

---

## 8. The built-in eval pair (use this from day one)

**Onion / Ajmer** and **Onion / Alwar** are the same crop, same peril structures (deficit rainfall + excess rainfall single-payout), differing only in calibrated values and SI.

Use as the first golden-answer test:
1. Extract Ajmer → structured JSON (hand-verify once; this becomes ground truth).
2. Run Adaptation Agent: adapt Ajmer structure to Alwar region.
3. Compare generated Alwar output against the *real* Alwar termsheet.
4. Measure field-level accuracy against that ground truth.

This is your acceptance test for the adaptation loop — no synthetic test case needed.

---

## 9. MVP build sequence (for the interns)

Hold this order. Depth on one archetype before breadth.

1. **Lock this schema** (this doc) — agree field names, get sign-off before coding.
2. **Extraction on the hardest sample first** — Guava or Orange (`rainfall_multistrike` with sub-periods + merged cells). If the ugly one works, the clean ones are free.
3. **Governed libraries** — Standard Index Library (archetype definitions), Crop Ontology, Template Library. Real reusable structures even at one-crop scale. **This is the core IP.**
4. **Agent pipeline on ONE archetype end-to-end** — `rainfall_multistrike` (or the Onion `rainfall_single_payout` for the eval pair). Extraction → Adaptation → Index Rec → Validation → JSON.
5. **JSON payload that loads into the Riskwolf sandbox** — this is the real acceptance criterion and the demo moment.
6. **Add remaining archetypes one at a time** — temperature, wind, then variants.

### Explicitly OUT of MVP scope
- Multiple states / "nationwide" anything
- Private-insurer formats (all samples are government WBCIS)
- The headline KPIs (>95% acreage, >90% standardization) — those are the vision, not the MVP deliverable
- Edge-case gold-plating on archetype #1

---

## 10. Open questions to resolve before build

- **Native PDF vs scan?** Decides whether OCR is on the critical path. Check the actual source files.
- **Riskwolf JSON contract** — need the target payload schema + API sandbox to confirm step 5 output shape.
- **Which archetype leads** — `rainfall_multistrike` (hardest, highest coverage) vs `rainfall_single_payout` (has the ready-made Onion eval pair). Recommend leading with the eval pair for a faster first green test, then hardening on the multistrike.
