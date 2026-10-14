# Freight Tiger Shipping Cost Watch Assistant

A Python-based case-study project that aggregates shipment records into weekly route costs, compares each route with historical and peer baselines, and identifies unusual cost increases for human review. It also checks operational context notes for possible explanations.

The implementation is a **deterministic, rule-based prototype** built with Python's standard library. It does not call an LLM or external API. Its rules make results repeatable for the same inputs, but they do not guarantee that every real-world cause will be recognized correctly.

## 1. What the project does

1. **Aggregate shipments:** validate shipment rows and group them by route, route type, and Monday-starting week.
2. **Compare costs:** calculate a trailing historical baseline and a same-week peer baseline.
3. **Detect anomalies:** apply configured thresholds and evaluate context notes for possible explanations.
4. **Answer basic queries:** a command-line assistant summarizes existing output using simple pattern matching. It is not a general-purpose language model.

## 2. Project structure

~~~text
.
├── FreightTiger_Intern_CaseStudy.pdf
├── README.md
├── shipment_records.csv
├── context_notes.csv
├── sample_output_format_v2.csv
├── token_cost_log.md
├── run_pipeline.py
├── src/
│   ├── aggregate_weekly.py
│   ├── compare_history.py
│   ├── detect_anomalies.py
│   └── ask_assistant.py
├── tests/
│   ├── test_pipeline.py
│   └── check_reproducibility.py
└── output/
    ├── weekly_costs.csv
    ├── weekly_comparisons.csv
    ├── final_output.csv
    ├── flagged_anomalies.csv
    └── reproducibility_report.txt
~~~

## 3. Requirements and setup

- Python 3.8 or newer is intended; the project was tested with Python 3.13.
- Only Python standard-library modules are used. No package installation is required.
- Run commands from the project root, where run_pipeline.py is located.

~~~powershell
python --version
~~~

## 4. Run the pipeline and tests

Run the full pipeline:

~~~powershell
python run_pipeline.py
~~~

It creates or refreshes these files under output/: weekly_costs.csv, weekly_comparisons.csv, final_output.csv, and flagged_anomalies.csv.

Run each stage separately, in order:

~~~powershell
python src/aggregate_weekly.py
python src/compare_history.py
python src/detect_anomalies.py
~~~

Run the unit tests:

~~~powershell
python -m unittest discover tests -v
~~~

Run the three-run reproducibility check:

~~~powershell
python tests/check_reproducibility.py
~~~

The reproducibility check runs the pipeline three times, hashes both CSV output files, compares the generated final-output rows, and writes output/reproducibility_report.txt. The report includes a timestamp, so the report file itself is not expected to be byte-for-byte identical across runs.

## 5. Aggregation and cost calculations

The input shipment file contains shipment IDs, route details, quantities, distances, freight costs, and shipment dates. The aggregation stage validates required fields and positive numeric values, then groups records by route, route type, and Monday-starting week.

Transport work is:

~~~text
Tonne-km = Quantity (tonnes) × Distance (km)
~~~

The weekly weighted cost per tonne-kilometre is:

~~~text
Cost per tonne-km = Sum of freight cost (INR) / Sum of tonne-km
~~~

Using aggregate totals avoids taking a simple average of individual shipment rates.

## 6. Baselines and anomaly rule

### Historical baseline

For each exact route and route-type pair, the system uses up to eight weekly records strictly before the week being evaluated. The current week is excluded. If fewer than eight prior weeks exist, all available prior weeks are used. If no prior history exists, the history comparison is marked unavailable.

~~~text
Change vs history (%) =
(Current rate - Historical average) / Historical average × 100
~~~

### Peer baseline

For the same week, a route is compared with other routes of the same route_type. The route itself is excluded from its peer average.

~~~text
Change vs peers (%) =
(Current rate - Peer average) / Peer average × 100
~~~

### Configured anomaly rule

A route-week is considered anomalous when either:
- Its rate is at least **20% above its historical average**; or
- Its rate is at least **20% above its peer average** and its historical change is positive. If historical data is unavailable, a peer increase of at least 20% can trigger the rule.

The 20% threshold is a case-study configuration choice, not a universal freight-industry standard.

## 7. Context matching and verdicts

For each detected anomaly, the system evaluates context_notes.csv using route scope, date windows, and explicit text patterns. Corridor-specific justifying notes are prioritized over notes applying to All Routes, with date proximity used to rank candidates.

Examples in the supplied data include:

- **N001:** flooding and longer detours affecting Chennai-Bangalore from February 24 through March 8, 2025.
- **N002:** a regional festival surcharge on Ahmedabad-Mumbai during the week of January 20, 2025.
- **N003:** a general diesel increase of roughly 5–7%. The current rules do not treat this small general increase as sufficient justification for a cost anomaly of 20% or more.
- Other notes describe stable demand, out-of-scope toll changes, improved road conditions, or costs that were not significantly affected.

The final flagged field uses these verdicts:

| Verdict | Meaning |
|---|---|
| No | The configured anomaly rule did not trigger. |
| No (justified) | The rule triggered and a note matched the current justification rules. The note ID and explanation are included. |
| Yes | The rule triggered but no qualifying justification was found; the record is included in the human-review queue. |

**Limitations:** Context classification relies on keywords, negation phrases, route scope, and date windows. It may miss valid causes or interpret unfamiliar wording incorrectly. A nearby note is not automatically causal. Yes means “unexplained by these rules and notes,” not proof of wrongdoing. Review flagged cases before making operational decisions.

## 8. Output files

| File | Contents |
|---|---|
| output/weekly_costs.csv | Weekly aggregates including freight costs, tonne-kilometres, shipment counts, and rates. |
| output/weekly_comparisons.csv | Aggregates enriched with historical and peer baselines. |
| output/final_output.csv | Final route-week results in the required output schema. |
| output/flagged_anomalies.csv | Human-review queue containing records whose verdict is Yes. |
| output/reproducibility_report.txt | Results from the latest three-run check. |
| token_cost_log.md | LLM/API usage and cost accounting. |

The final output columns, in order, are:

~~~text
route,week_of,cost_per_tonne_km,vs_own_history,vs_similar_routes,flagged,matched_note_id,reason
~~~

For the supplied data, 2,940 shipment records produce 728 route-week records. The recorded output contains 19 anomaly events: 3 marked No (justified) and 16 marked Yes. The remaining 709 route-weeks are marked No.

## 9. Benchmark examples

| Route | Week of | Cost per tonne-km | Change vs history | Change vs peers | Verdict |
|---|---|---:|---:|---:|---|
| Delhi-Jaipur | 2024-11-11 | 4.17 | +35.5% | +21.0% | Yes |
| Ahmedabad-Mumbai | 2025-01-20 | 3.29 | +29.5% | +22.5% | No (justified) via N002 |
| Mumbai-Pune | 2025-09-15 | 3.98 | +9.2% | +23.6% | Yes |

The tests check these benchmark records alongside aggregation, baseline exclusions, context-note handling, and assistant responses.

## 10. Command-line assistant

Launch interactively after running the pipeline:

~~~powershell
python src/ask_assistant.py
~~~

Or pass a question:

~~~powershell
python src/ask_assistant.py "why did Chennai-Bangalore get pricier in March 2025?"
python src/ask_assistant.py "what happened to Ahmedabad-Mumbai in January 2025?"
python src/ask_assistant.py "why was Delhi-Jaipur flagged in November 2024?"
~~~

The assistant extracts a route, month, and year using simple string and pattern matching, then summarizes matching rows in final_output.csv. It does not generate new causes. Unsupported wording or dates may not parse as expected.

## 11. Tests and reproducibility

The suite contains **17 tests across five test classes**, covering input validation, Monday-starting weeks, weighted aggregation, historical and peer baselines, output schema, sample cases, flood-window boundaries, decoy-note handling, the small fuel-increase rule, review-queue filtering, and assistant responses.

In the reviewed local version, the unit-test command completed with 17 tests passing. Re-run both the tests and the reproducibility check after changing code or input data. Reproducibility shows that a given version produces consistent outputs for the same inputs; it does not by itself prove that every anomaly classification is correct.

## 12. Token and cost accounting

The implementation makes **zero LLM/API calls**, so the pipeline uses zero LLM input tokens, zero LLM output tokens, and incurs $0.00 in LLM/API charges per run. These figures refer to external LLM usage, not all computer-resource costs. The pipeline uses deterministic Python rules rather than LLM-based semantic retrieval.

## 13. Known limitations and possible extensions

- Context matching is keyword-based and tuned to the ten supplied notes.
- The anomaly threshold is fixed at 20% and may require business-specific calibration.
- The command-line assistant performs basic route/month/year parsing rather than open-ended natural-language understanding.
- Future improvements could include a larger labeled evaluation set, additional edge-case tests, configurable thresholds, analyst feedback, or optional hybrid search with evidence checks.

---

**Summary:** This project provides a reproducible, inspectable baseline for weekly freight-cost monitoring. Its strengths are transparent calculations, explicit anomaly rules, a human-review queue for unexplained increases, and tests for core expected behavior. Treat the output as decision support and review flagged cases before high-impact operational decisions.
