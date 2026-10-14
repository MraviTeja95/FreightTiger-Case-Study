"""
End-to-end execution pipeline for Freight Tiger Shipping Cost Watch Assistant.

Steps:
1. Aggregate raw shipment records by route, route_type, and Monday-starting week (src/aggregate_weekly.py).
2. Compute historical trailing 8-week baselines and similar-routes peer baselines (src/compare_history.py).
3. Detect cost anomalies and match real-world context notes (src/detect_anomalies.py).
"""

import sys
import time
from pathlib import Path

# Add project root and src to path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import aggregate_weekly
import compare_history
import detect_anomalies


def run_pipeline():
    print("=" * 70)
    print("Freight Tiger Shipping Cost Watch Assistant - Full Pipeline")
    print("=" * 70)

    start_time = time.time()

    # Step 1: Aggregate weekly
    print("\n[Step 1/3] Aggregating shipment records by week and route...")
    aggregate_weekly.main()

    # Step 2: Compare history and peers
    print("\n[Step 2/3] Computing trailing 8-week and peer route baselines...")
    compare_history.main()

    # Step 3: Detect anomalies and match context notes
    print("\n[Step 3/3] Detecting cost anomalies and matching context notes...")
    detect_anomalies.run_detection()

    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print(f"Pipeline completed successfully in {elapsed:.3f} seconds.")
    print("=" * 70)


if __name__ == "__main__":
    run_pipeline()
