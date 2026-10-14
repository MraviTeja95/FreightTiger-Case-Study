# Freight Tiger Shipping Cost Watch Assistant

An intelligent, production-ready system for monitoring freight shipping rates, detecting unexpected cost spikes across route corridors, and validating anomalies against real-world operational context notes.

---

## 1. Problem Overview

In freight logistics, shippers and transporters negotiate rates based on transport work (measured in **tonne-kilometres**). Rates can fluctuate due to genuine real-world disruptions (such as highway flooding, fuel price revisions, or regional festival surcharges) or quietly creep up without operational justification.

The goal of this system is to:
1. **Aggregate** shipment records into weekly route-level metrics.
2. **Compute Historical Baselines**: Track cost per tonne-kilometre against a trailing 8-week rolling average for the same route and route type.
3. **Compute Peer Baselines**: Compare each route's weekly rate against other routes sharing the same distance category (`Short`, `Medium`, `Long`).
4. **Detect Anomalies**: Flag routes experiencing abnormal cost rises.
5. **Context Matching & Guardrails**: Audit candidate anomalies against operational context notes, strictly distinguishing genuine root causes from decoy updates, ensuring zero hallucinations and 100% reproducible verdicts.
6. **Stretch Goal (Natural Language Interface)**: Allow stakeholders to ask questions in plain English (e.g., *"Why did Chennai-Bangalore get pricier in March 2025?"*).

---

## 2. Architecture & Data Flow

The solution is structured as a modular, three-stage pipeline built entirely on the **Python standard library** (`csv`, `datetime`, `collections`, `re`, `unittest`) to guarantee zero dependency failures and full compliance with strict Windows Application Control environments:

```text
shipment_records.csv
        │
        ▼
[Step 1: src/aggregate_weekly.py]
  - Validates positive quantities, distances, freight costs
  - Groups dates into Monday-starting weeks
  - Calculates weighted Cost per Tonne-Km
        │
        ▼
output/weekly_costs.csv (728 records)
        │
        ▼
[Step 2: src/compare_history.py]
  - Trailing 8-week historical rolling baseline (strictly prior weeks)
  - Same-week peer baseline (strictly excludes current route)
  - Full-precision percentage variance calculations
        │
        ▼
output/weekly_comparisons.csv (728 enriched records)
        │
        ▼
[Step 3: src/detect_anomalies.py] ◄── context_notes.csv (10 real-world notes)
  - Identifies rising cost anomalies (Threshold: >= +20.0%)
  - Evidence-based causal matching (corridor matching, date overlap, decoy filtering)
  - 19 anomaly events detected: 3 justified (No/justified) + 16 unexplained (Yes)
        │
        ├─────────────────────────────────────────┐
        ▼                                         ▼
output/final_output.csv              output/flagged_anomalies.csv
(728 weekly route records,           (16 records — human-review queue;
 all verdicts: No/Yes/No-justified)   only flagged=="Yes", unexplained only)
        │
        ▼
[Interactive: src/ask_assistant.py] (Stretch Goal CLI)
```

---

## 3. Mathematical & Business Formulas

### 3.1 Transport Work & Rate
Transport work is quantified in tonne-kilometres:
$$\text{Tonne-Km} = \text{Quantity (Tonnes)} \times \text{Distance (Km)}$$

The weekly weighted rate per route and route type is:
$$\text{Cost per Tonne-Km} = \frac{\sum \text{Freight Cost (INR)}}{\sum \text{Tonne-Km}}$$

*Note: Rates are calculated over aggregate weekly sums (weighted average), ensuring individual shipment weights are properly accounted for.*

### 3.2 Trailing Historical Baseline (`vs_own_history`)
For a given route, route type, and current week $W$:
- Select up to 8 prior weekly records strictly before $W$ ($W_{prior} < W$).
- No look-ahead is permitted.
- If fewer than 8 prior weeks exist (e.g., during the initial weeks of 2024), the baseline uses all available prior weeks without padding or extrapolation.
- If 0 prior weeks exist (Week 1), the field outputs `N/A (insufficient history)`.

$$\text{Historical Average} = \frac{1}{N} \sum_{i=1}^{N \le 8} \text{Rate}_i$$
$$\text{Percentage Change vs History} = \left( \frac{\text{Current Rate} - \text{Historical Average}}{\text{Historical Average}} \right) \times 100$$

### 3.3 Peer Group Baseline (`vs_similar_routes`)
For a given route $R$ of type $T$ in week $W$:
- Identify all other routes $R' \neq R$ sharing the same $T$ in week $W$.
- The current route $R$ is strictly excluded from its own peer average.

$$\text{Peer Average} = \frac{1}{M} \sum_{R' \neq R} \text{Rate}_{R', W}$$
$$\text{Percentage Change vs Peers} = \left( \frac{\text{Current Rate} - \text{Peer Average}}{\text{Peer Average}} \right) \times 100$$

---

## 4. Anomaly Threshold & Context Matching Rules

### 4.1 Proposed Anomaly Threshold
The brief requires flagging routes where cost is rising and looks out of the ordinary compared to history or peers. Since an exact numerical percentage is not prescribed by the brief, the following justified threshold is implemented:
- **Historical Trigger**: Rate $\ge +20.0\%$ above trailing 8-week historical average, **OR**
- **Peer Trigger**: Rate $\ge +20.0\%$ above same-week peers **AND** rate is positively growing vs history (`pct_vs_history > 0.0%` or insufficient history).

**Justification against benchmark cases**:
1. `Delhi-Jaipur` (2024-11-11): $+35.5\%$ vs history $\to$ Flagged `Yes`.
2. `Ahmedabad-Mumbai` (2025-01-20): $+29.5\%$ vs history $\to$ Flagged `No (justified)` via `N002`.
3. `Mumbai-Pune` (2025-09-15): $+9.2\%$ vs history, but $+23.6\%$ vs peers $\to$ Flagged `Yes` (cross-sectional spike with positive historical growth).

### 4.2 Context Note Classification & Guardrails
The system audits candidate anomalies against `context_notes.csv` (10 operational notes):
- **Causal Drivers (Justifying)**:
  - `N001` (2025-02-24, `Chennai-Bangalore`): Flood detours between Feb 24 and Mar 8. Multi-week active window correctly covers weeks `2025-02-24` and `2025-03-03`.
  - `N002` (2025-01-20, `Ahmedabad-Mumbai`): Regional festival week driving transporter surcharge.
- **Decoys / Non-Justifying Updates**:
  - `N003`: Diesel price increase of roughly 5-7% across all routes. A small general increase does not justify an anomalous spike $\ge 20\%$.
  - `N004`: Toll plaza update, but "affected routes are not part of this dataset".
  - `N005`: Highway maintenance, but "costs were not significantly affected".
  - `N006`: Logistics report noting "stable demand with no major disruptions". (Tested against Mumbai-Pune cost spike).
  - `N007`: Road resurfacing / improved conditions.
  - `N008`: No disruptions reported.
  - `N009`: Repairs completed, returned to normal conditions (post-flood).
  - `N010`: Fleet tracking mandate compliance costs "absorbed by transporters without a rate change".

### 4.3 Output Verdicts Breakdown
- **`No (justified)`** (3 events): Route and week overlap with a genuine causal note $\to$ cites `matched_note_id` and summarizes the real-world cause. These events are resolved and excluded from `flagged_anomalies.csv`.
- **`Yes`** (16 events): Cost rise occurred without causal justification $\to$ `matched_note_id` is left blank `""`. If a non-justifying note was nearby within 14 days, the reason explicitly explains why the nearby note does not justify the rate hike. Written to `output/flagged_anomalies.csv` for human review.
- **`No`** (709 weeks): Normal operating week within expected historical and peer tolerances.

---

## 5. How to Run the Project (Windows / Cross-Platform)

The project requires **Python 3.8+** (tested on Python 3.13) and uses **only Python standard libraries**. No pip installations are required.

### 5.1 Run the Full Pipeline
From the project root:
```powershell
python run_pipeline.py
```
This automatically runs all three stages in sequence:
1. `src/aggregate_weekly.py` $\to$ generates `output/weekly_costs.csv`
2. `src/compare_history.py` $\to$ generates `output/weekly_comparisons.csv`
3. `src/detect_anomalies.py` $\to$ generates `output/final_output.csv` & `output/flagged_anomalies.csv`

### 5.2 Run Individual Steps
```powershell
python src/aggregate_weekly.py
python src/compare_history.py
python src/detect_anomalies.py
```

### 5.3 Run Automated Tests
```powershell
python -m unittest discover tests -v
```

### 5.4 Run Reproducibility Check (3 Runs)
```powershell
python tests/check_reproducibility.py
```

### 5.5 Try the Interactive Smart Assistant (Stretch Goal)
Ask plain-English questions via CLI arguments or interactive mode:
```powershell
python src/ask_assistant.py "why did Chennai-Bangalore get pricier in March 2025?"
python src/ask_assistant.py "what happened to Ahmedabad-Mumbai in January 2025?"
python src/ask_assistant.py "why was Delhi-Jaipur flagged in November 2024?"
```

---

## 6. Output Files Description

All generated artifacts are saved in the `output/` directory:

| File | Records | Description |
| :--- | :--- | :--- |
| `output/final_output.csv` | **728** | The exact final deliverable meeting all schema specifications (`route`, `week_of`, `cost_per_tonne_km`, `vs_own_history`, `vs_similar_routes`, `flagged`, `matched_note_id`, `reason`). Contains every route-week with a clear verdict. |
| `output/flagged_anomalies.csv` | **16** | **Human-review queue**: records where `flagged == "Yes"` only — i.e., cost spikes that could not be matched to any causal context note and require analyst investigation. The 3 justified spikes (`No (justified)`) are resolved and excluded from this file since they need no further action. |
| `output/weekly_costs.csv` | **728** | Intermediate weekly aggregates with total costs, tonne-kms, and shipment counts. |
| `output/weekly_comparisons.csv` | **728** | Enriched comparisons containing exact float values and formatted strings for trailing 8-week history and peer baselines. |
| `output/reproducibility_report.txt` | — | Verification log across 3 untouched pipeline executions confirming byte-for-byte SHA-256 equivalence. |
| `token_cost_log.md` | — | Token usage, API volume, and cost log ($0.00 spend). |

---

## 7. Validation Results & Benchmark Alignment

The automated test suite (`tests/test_pipeline.py`) contains **17 test methods** across **5 test classes**, covering data quality, baselines, decoy rejection, flood boundaries, review queue filters, and assistant queries. Verified result: **Ran 17 tests in ~0.28s — OK**.

| Test Class | Tests | What Is Validated |
| :--- | :--- | :--- |
| `TestDataQualityAndSchema` | 2 | Input schemas; all 2,940 shipment IDs unique and positive; context_notes.csv has 10 rows |
| `TestAggregationLogic` | 2 | Monday-starting week logic for all weekdays; weighted cost-per-tonne-km formula |
| `TestComparisonLogic` | 2 | Historical baseline strictly excludes current week; peer baseline strictly excludes current route |
| `TestContextMatchingAndSampleCases` | 7 | Exact column schema and 728 row count; 3 benchmark cases match sample output character-for-character; Chennai-Bangalore flood weeks correctly justified via N001; decoy notes rejection; small fuel increase (N003) rejection; review queue filter strictly contains `flagged == 'Yes'` |
| `TestAssistantInterface` | 4 | Query parsing and response generation for justified, unexplained, normal, and ambiguous queries |

The three benchmark rows in `final_output.csv` match `sample_output_format_v2.csv` character-for-character:

```csv
Delhi-Jaipur,2024-11-11,4.17,+35.5% vs this route's past average,+21.0% vs similar-length routes this week,Yes,,No matching note found for this route or date range. Cost rise looks unexplained and worth a human review.
Ahmedabad-Mumbai,2025-01-20,3.29,+29.5% vs this route's past average,+22.5% vs similar-length routes this week,No (justified),N002,Matches note N002 dated 2025-01-20: a regional festival week drove a temporary surcharge on this corridor. The cost rise has a clear explanation.
Mumbai-Pune,2025-09-15,3.98,+9.2% vs this route's past average,+23.6% vs similar-length routes this week,Yes,,The closest note (N006, 2025-09-22) mentions stable demand with no major disruptions -- it does not describe a reason for a cost rise on this route. No genuine justification found; flagged for review.
```

---

## 8. Round 2 Walkthrough Outline (10 Minutes)

When presenting this solution in Round 2, use this recommended structure:

1. **Problem Framing (1 min)**:
   - Freight cost creep is subtle because costs fluctuate with payload and distance.
   - We normalized transport work to weighted Cost per Tonne-Km grouped by Monday-starting weeks.
2. **Dual-Baseline Architecture (2 mins)**:
   - *Temporal baseline*: Trailing 8-week rolling average on the exact corridor (strict prior weeks, no look-ahead).
   - *Cross-sectional baseline*: Same-week peer average across same distance tier (`Short`, `Medium`, `Long`), strictly excluding the route itself.
3. **Anomaly Threshold Selection (2 mins)**:
   - Analyzed variance distributions across 728 route-weeks.
   - Selected $\ge +20.0\%$ variance, which cleanly isolates real spikes while filtering out minor fuel/seasonal noise.
   - Directly verified against Delhi-Jaipur (+35.5%), Ahmedabad-Mumbai (+29.5%), and Mumbai-Pune (+23.6% peer spike).
4. **Context Matching & Guardrails (3 mins)**:
   - Evaluated 10 context notes: identified 2 genuine corridor causal drivers (N001, N002) and 8 decoy/non-justifying updates (including N003's small general diesel rise).
   - Explained why naive nearest-date matching fails (e.g. Note N006 on 2025-09-22 mentions stable demand and cannot justify Mumbai-Pune's rate spike).
   - Flood date parsing (Feb 24 - Mar 8) correctly covers multi-week disruptions for Chennai-Bangalore.
5. **Engineering Excellence & Trade-offs (2 mins)**:
   - Zero-cost, standard-library architecture: avoids DLL blocking issues on restricted OS environments, runs in ~0.10 seconds, achieves 100% byte-for-byte reproducibility across runs.
   - 19 anomaly events detected total: 3 resolved via context notes, 16 written to `flagged_anomalies.csv` as a clean human-review queue.
   - Interactive plain-English assistant demo (`src/ask_assistant.py`).

---

## 9. Known Limitations & Extensibility to LLM/RAG

- **Rule-Based Engine vs. Embedding RAG**: The deterministic retrieval engine operates on explicit date windows, corridor matching, and negation keyword patterns. This is optimal and 100% reproducible for the fixed 10-note context set, but does not generalize to thousands of unstructured, open-domain operational logs without semantic vector search (e.g. Sentence-Transformers or Chroma/FAISS).
- **Extensibility Path**: In a full enterprise deployment, this module can be upgraded to hybrid search (dense vector embeddings + sparse BM25) with a re-ranking stage and a guardrail filter that prevents small general cost notes from justifying large corridor-specific spikes.
