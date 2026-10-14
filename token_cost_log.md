# Token and Cost Log

## Scope

The Freight Tiger case-study pipeline uses a deterministic Python rule engine. It does not call an external LLM or other inference API. The values below describe LLM/API usage for one full pipeline run over the supplied shipment file; they are not a measurement of all CPU, memory, or electricity costs.

## Usage and cost summary

| Metric | Recorded value | Notes |
|---|---:|---|
| Shipment records | 2,940 | Aggregated into 728 route-week records |
| Context notes | 10 | Evaluated using explicit route, date, and text rules |
| External LLM/API calls | 0 | No external inference call is made |
| LLM input tokens | 0 | No prompt sent to a model |
| LLM output tokens | 0 | No model-generated output |
| LLM/API cost per full run | $0.00 | No LLM/API usage |
| Dependencies | Python standard library | No third-party package installation is required |

Pipeline runtime depends on the machine and environment. In the local Windows/Python 3.13 verification log, the three reproducibility runs completed in approximately 0.06–0.08 seconds each. Treat this as an observed local result, not a general performance guarantee.

## Trade-offs

The rule-based implementation is inexpensive and repeatable for fixed inputs and rules. Its limitation is that it depends on explicit patterns and date/corridor rules; unfamiliar wording or an unrepresented cause may not be recognized. A future LLM or retrieval layer would add token/API cost and would need evidence checks to prevent unsupported explanations.

## Reproducibility evidence

The local command shown below ran the pipeline three times:

~~~powershell
python -B tests/check_reproducibility.py
~~~

The reported output hashes were identical across all three runs:

- **output/final_output.csv:** 9b6433b53087263aa7149ed73b0fcd57b7f7b686869fadb7875953b18fd76d0f
- **output/flagged_anomalies.csv:** 322ac9bcdaa12ea99067ade5bb46d0f39533d782d9de4e3feae4aef3d427bf56

The report recorded zero row-by-row field mismatches across the three runs, with 728 final route-week records, 709 normal records, 16 unexplained anomalies, and 3 justified anomalies.

The reproducibility report includes a generation timestamp; therefore, the report text itself can change between runs even when the output CSVs remain identical.
