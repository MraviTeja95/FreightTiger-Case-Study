"""
Smart Shipping Cost Assistant - Interactive Query Interface (Stretch Goal).

Allows users to ask plain-English questions regarding route cost changes and findings,
e.g.:
- "Why did Chennai-Bangalore get pricier in March 2025?"
- "What happened to Ahmedabad-Mumbai in January 2025?"
- "Why was Delhi-Jaipur flagged in November 2024?"
- "Did Mumbai-Pune have any unexplained spikes in September?"
"""

import csv
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINAL_OUTPUT_FILE = ROOT / "output" / "final_output.csv"

MONTH_NAMES = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5, "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}


def load_final_data():
    if not FINAL_OUTPUT_FILE.exists():
        raise FileNotFoundError(
            f"Final output file not found: {FINAL_OUTPUT_FILE}. Run run_pipeline.py first."
        )
    with open(FINAL_OUTPUT_FILE, mode="r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_query(query: str, available_routes):
    query_lower = query.lower()

    # Detect route
    matched_route = None
    for r in available_routes:
        parts = [p.lower() for p in r.split("-")]
        if r.lower() in query_lower or all(p in query_lower for p in parts):
            matched_route = r
            break

    # Detect year
    matched_year = None
    year_match = re.search(r'\b(2024|2025)\b', query)
    if year_match:
        matched_year = int(year_match.group(1))

    # Detect month
    matched_month = None
    for m_name, m_num in MONTH_NAMES.items():
        if re.search(rf'\b{m_name}\b', query_lower):
            matched_month = m_num
            break

    return matched_route, matched_year, matched_month


def answer_query(query: str, records):
    routes = sorted(set(r["route"] for r in records))
    matched_route, matched_year, matched_month = parse_query(query, routes)

    if not matched_route:
        return (
            "I could not identify the specific route from your question.\n"
            f"Available routes are: {', '.join(routes)}\n"
            "Example query: 'Why did Chennai-Bangalore get pricier in March 2025?'"
        )

    # Filter records
    matching_records = []
    for r in records:
        if r["route"] != matched_route:
            continue
        dt = date.fromisoformat(r["week_of"])
        if matched_year and dt.year != matched_year:
            continue
        if matched_month and dt.month != matched_month:
            continue
        matching_records.append(r)

    if not matching_records:
        time_desc = ""
        if matched_month and matched_year:
            time_desc = f" in {matched_month}/{matched_year}"
        elif matched_month:
            time_desc = f" in month {matched_month}"
        elif matched_year:
            time_desc = f" in {matched_year}"
        return f"No records found for route '{matched_route}'{time_desc}."

    anomalies = [r for r in matching_records if r["flagged"] != "No"]

    lines = []
    lines.append(f"Route: {matched_route}")
    if matched_month or matched_year:
        time_str = f"Timeframe: {matched_month or '*'}/{matched_year or '*'}"
        lines.append(time_str)
    lines.append("-" * 60)

    if anomalies:
        lines.append(f"Found {len(anomalies)} flagged anomaly period(s):")
        for a in anomalies:
            lines.append(f"\n* Week of {a['week_of']}:")
            lines.append(f"  - Cost per tonne-km: INR {a['cost_per_tonne_km']}")
            lines.append(f"  - Baseline comparison: {a['vs_own_history']} | {a['vs_similar_routes']}")
            lines.append(f"  - Verdict: {a['flagged']}")
            if a["matched_note_id"]:
                lines.append(f"  - Cited Note: {a['matched_note_id']}")
            lines.append(f"  - Explanation: {a['reason']}")
    else:
        lines.append("No unusual cost spikes were detected during this period.")
        sample_rec = matching_records[0]
        lines.append(
            f"Cost per tonne-km was normal (e.g. INR {sample_rec['cost_per_tonne_km']} in week {sample_rec['week_of']}), "
            f"tracking within regular historical and peer bounds."
        )

    return "\n".join(lines)


def main():
    records = load_final_data()

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        print(f"\nUser Query: \"{query}\"\n")
        response = answer_query(query, records)
        print(response)
    else:
        print("Smart Shipping Cost Assistant (Interactive Mode)")
        print("Type 'exit' or 'quit' to end.\n")
        while True:
            try:
                query = input("Ask a question: ").strip()
                if not query:
                    continue
                if query.lower() in ("exit", "quit", "q"):
                    break
                print("\n" + answer_query(query, records) + "\n")
            except (KeyboardInterrupt, EOFError):
                break


if __name__ == "__main__":
    main()
