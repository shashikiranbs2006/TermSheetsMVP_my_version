# Testing / Definition of Done per checkpoint

| Checkpoint | Must work                          | AI/LLM involved? |
|---|---|---|
| C0  | Project structure + context         | No |
| C1  | Pydantic contracts (valid/invalid)  | No |
| C2  | Eval harness (field-by-field diff)  | No |
| C3  | Native/scanned router               | No |
| C4  | Raw cells + geometry                | No |
| C5  | Peril segmentation                  | Maybe |
| C6  | Archetype classification            | Maybe |
| C7  | Table reconstruction                | No |
| C8  | Schema mapping                      | Yes — Bedrock |
| C9  | Validation                          | No |
| C10 | Full Orange pipeline                | Yes |
| C11 | Provenance/review                   | No |
| C12 | Other archetypes                    | Yes |
| C13 | Ajmer → Alwar                       | Yes |
| C14 | Riskwolf payload                    | Maybe |

Eval harness is the tiebreaker for every checkpoint: don't trust "looks
right," compare actual JSON against docs/source/sample_orange_jhalawar.json
field by field.
