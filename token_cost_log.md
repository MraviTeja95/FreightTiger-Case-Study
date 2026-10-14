# Token and Cost Log

## Overview
As specified in the Freight Tiger 24-Hour Challenge brief:
> *"Prefer open-source models and free-tier options. For one full run over the entire shipment file, report total input tokens, total output tokens, number of LLM calls, and the rough cost at your model's published rate."*

To satisfy the strict guardrails on **Zero Hallucination**, **Byte-for-Byte Reproducibility**, and **Windows Environment Resilience** (specifically avoiding binary DLL blocks from Windows Application Control), the production pipeline implements a deterministic Context Retrieval & Rule-Based Validation Engine using Python's standard library.

---

## Resource & Cost Summary (Full Run over 2,940 Shipments)

| Metric | Measured Value | Notes |
| :--- | :--- | :--- |
| **Shipment Records Processed** | 2,940 records | Grouped into 728 route-week records |
| **Context Notes Evaluated** | 10 notes | Classified by corridor, active date window, and causal validity |
| **LLM Calls** | **0 calls** | Pure standard-library deterministic rule engine |
| **Input Tokens** | **0 tokens** | No external LLM token consumption |
| **Output Tokens** | **0 tokens** | No generated LLM tokens |
| **Cost per 1M Tokens** | $0.00 / Free Tier | Open-source / local standard library |
| **Total Cost for One Full Run** | **$0.00** | Zero cloud, inference, or API cost |
| **Full Execution Time** | **~0.10 seconds** | Observed range: 0.08s – 0.12s (Python 3.13 on Windows 11) |
| **Dependencies** | Python Standard Library | Zero external pip dependencies; zero DLL blocking risks |

---

## Architectural Trade-off Analysis: Deterministic Rule Engine vs. Cloud LLM API

| Dimension | Deterministic Rule-Based Engine (Implemented) | Cloud LLM API (e.g. OpenAI / Anthropic) |
| :--- | :--- | :--- |
| **API Cost** | **$0.00** (Zero marginal cost) | Variable per-token API billing per run |
| **Latency** | **~0.10 seconds** total pipeline execution | Typically 10–30+ seconds due to network round-trips |
| **Reproducibility** | **100.0% byte-for-byte identical** across runs (verified via SHA-256) | Non-deterministic risk unless strictly pinned at temperature 0 |
| **Hallucination Risk** | **Strictly bounded** by explicit corridor/date logic | Non-zero risk of inventing plausible-sounding reasons |
| **Portability** | Runs offline on restricted enterprise Windows environments | Requires egress internet access, secret management, and API keys |
| **Scalability to Large Unstructured Data** | Requires explicit pattern definitions for new event types | Naturally generalizes to novel unstructured phrasing via semantic embeddings |

---

## Auditing and Verification
The reproducibility check (`python tests/check_reproducibility.py`) executed 3 consecutive untouched runs of the full pipeline. The SHA-256 checksums across all 3 runs were byte-for-byte identical:
- **`output/final_output.csv`**: `9b6433b53087263aa7149ed73b0fcd57b7f7b686869fadb7875953b18fd76d0f`
- **`output/flagged_anomalies.csv`**: `a72f0c72c1c713b19280d965bb1964f43c3a9f0f97fc7ebec9fc13c321ae54a3`
- **Field-level diff across runs**: 0 mismatches across all 728 rows and 8 columns.
