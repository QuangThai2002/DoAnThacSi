# AI source audit - RAG TEST candidate v2

Audit date: 2026-10-03

Scope: 10 records in the `test` split of
`src/evaluation/benchmark_candidate_v2.jsonl`. The assistant rendered and
read the original PDF pages named by every record. This is an AI-assisted
source audit, not a substitute for an independently signed human review;
therefore every record remains `gold_verified=false`.

| Record(s) | Source and page inspected | Result |
| --- | --- | --- |
| `v2_api_shop_signature_006`, `v2_api_merchant_signature_007` | `SHP_API_002`, p. 3 | Pass. The API documentation gives the Shop and Merchant base-string parameter orders. |
| `v2_fee_headphones_004`, `v2_fee_audio_cable_005` | `SHP_FEE_006`, p. 1 | Pass. Both categories show a 10.00% fixed fee, applicable from 01/05/2026. |
| `v2_return_ship_back_004`, `v2_return_appeal_button_005` | `SHP_RET_003`, p. 4 | Pass after rewriting the first question for clarity. The source states 6 days to return and a 2-day appeal-button period. |
| `v2_listing_prohibited_003` | `SHP_POL_007`, p. 1 | Updated. The prior evidence only quoted the heading; it now summarizes the complete list of prohibited groups and has a source-grounded answer. |
| `v2_finance_service_fee_003` | `SHP_FIN_002`, p. 2 | Pass. The Service Fee Details page shows orders with service fees. |
| `v2_sea_gmv_002` | `SEA_REP_003`, p. 1 | Pass. Q4 2025 Shopee GMV is US$36.7bn, +28.6% year-on-year. |
| `v2_privacy_consent_002` | `SHP_POL_001`, p. 1 | Pass. The policy names collection, use, disclosure and/or processing of personal data. |

## Next scientific step

Open the annotation workbench, check the rendered pages independently, and
set each record to `verified` only after a named reviewer confirms the source.
Then lock the TEST split and run the official retrieval evaluation with the
verified guard enabled.
