"""
Verify reproducibility of pipeline across 3 consecutive runs.

Contract verified across all runs:
1. Byte-for-byte identical SHA-256 hash for output/final_output.csv.
2. Byte-for-byte identical SHA-256 hash for output/flagged_anomalies.csv.
3. Row-by-row field comparison across all runs:
   - Exact route, week_of, cost_per_tonne_km, vs_own_history, vs_similar_routes,
     flagged, matched_note_id, and reason match 100%.
4. Exact invariant counts:
   - 728 total route-week records
   - 709 normal records (flagged == "No")
   - 16 unexplained anomaly records (flagged == "Yes")
   - 3 justified anomaly records (flagged == "No (justified)")
"""

import csv
import difflib
import hashlib
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import run_pipeline

OUTPUT_DIR = ROOT / "output"
FINAL_CSV = OUTPUT_DIR / "final_output.csv"
FLAGGED_CSV = OUTPUT_DIR / "flagged_anomalies.csv"
REPORT_FILE = OUTPUT_DIR / "reproducibility_report.txt"


def get_file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def main():
    print("=" * 80)
    print("Freight Tiger Reproducibility Verification (3 Untouched Runs)")
    print("=" * 80)

    run_final_hashes = []
    run_flagged_hashes = []
    run_data = []
    temp_files = []

    for run_num in range(1, 4):
        print(f"\n--- Executing Run {run_num}/3 ---")
        run_pipeline.run_pipeline()

        final_copy = OUTPUT_DIR / f"final_output_run{run_num}.csv"
        flagged_copy = OUTPUT_DIR / f"flagged_anomalies_run{run_num}.csv"
        shutil.copy2(FINAL_CSV, final_copy)
        shutil.copy2(FLAGGED_CSV, flagged_copy)
        temp_files.extend([final_copy, flagged_copy])

        final_sha = get_file_hash(final_copy)
        flagged_sha = get_file_hash(flagged_copy)
        run_final_hashes.append(final_sha)
        run_flagged_hashes.append(flagged_sha)

        with open(final_copy, mode="r", newline="", encoding="utf-8") as f:
            records = list(csv.DictReader(f))
        run_data.append(records)

        print(f"Run {run_num} final_output.csv SHA-256:      {final_sha}")
        print(f"Run {run_num} flagged_anomalies.csv SHA-256: {flagged_sha}")

    # 1. Check SHA-256 identicalness
    final_identical = (run_final_hashes[0] == run_final_hashes[1] == run_final_hashes[2])
    flagged_identical = (run_flagged_hashes[0] == run_flagged_hashes[1] == run_flagged_hashes[2])

    # 2. Line-by-line diff between runs
    with open(temp_files[0], "r", encoding="utf-8") as f1, open(temp_files[2], "r", encoding="utf-8") as f2:
        diff_1_2 = list(difflib.unified_diff(f1.readlines(), f2.readlines(), lineterm=""))
    with open(temp_files[2], "r", encoding="utf-8") as f2, open(temp_files[4], "r", encoding="utf-8") as f3:
        diff_2_3 = list(difflib.unified_diff(f2.readlines(), f3.readlines(), lineterm=""))

    # 3. Invariant counts for Run 1
    r1 = run_data[0]
    total_records = len(r1)
    normal_count = sum(1 for r in r1 if r["flagged"] == "No")
    unexplained_count = sum(1 for r in r1 if r["flagged"] == "Yes")
    justified_count = sum(1 for r in r1 if r["flagged"] == "No (justified)")

    # 4. Programmatic row-by-row verification across all runs
    row_mismatches = 0
    for idx in range(total_records):
        row1, row2, row3 = run_data[0][idx], run_data[1][idx], run_data[2][idx]
        if row1 != row2 or row2 != row3:
            row_mismatches += 1

    report_lines = [
        "================================================================================",
        "FREIGHT TIGER CASE STUDY - REPRODUCIBILITY REPORT",
        "================================================================================",
        f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "Total runs evaluated: 3",
        "",
        "SHA-256 Checksums for output/final_output.csv:",
        f"  Run 1: {run_final_hashes[0]}",
        f"  Run 2: {run_final_hashes[1]}",
        f"  Run 3: {run_final_hashes[2]}",
        f"  Byte-for-byte identical across all 3 runs: {final_identical}",
        "",
        "SHA-256 Checksums for output/flagged_anomalies.csv:",
        f"  Run 1: {run_flagged_hashes[0]}",
        f"  Run 2: {run_flagged_hashes[1]}",
        f"  Run 3: {run_flagged_hashes[2]}",
        f"  Byte-for-byte identical across all 3 runs: {flagged_identical}",
        "",
        "Unified Diff Analysis:",
        f"  Diff between Run 1 and Run 2: {'None (0 line differences)' if not diff_1_2 else f'{len(diff_1_2)} lines differed'}",
        f"  Diff between Run 2 and Run 3: {'None (0 line differences)' if not diff_2_3 else f'{len(diff_2_3)} lines differed'}",
        f"  Row-by-row field value mismatches across runs: {row_mismatches}",
        "",
        "Verified Invariant Counts:",
        f"  - Total records processed: {total_records} (expected: 728)",
        f"  - Normal weeks (flagged == 'No'): {normal_count} (expected: 709)",
        f"  - Unexplained anomalies (flagged == 'Yes'): {unexplained_count} (expected: 16)",
        f"  - Justified anomalies (flagged == 'No (justified)'): {justified_count} (expected: 3)",
        f"  - Total anomaly events: {unexplained_count + justified_count} (expected: 19)",
        f"  - Human-review queue (output/flagged_anomalies.csv): {unexplained_count} records",
        "================================================================================",
    ]

    report_text = "\n".join(report_lines)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report_text)

    # Clean up temporary run files
    for f in temp_files:
        if f.exists():
            f.unlink()

    print("\n" + report_text)


if __name__ == "__main__":
    main()
