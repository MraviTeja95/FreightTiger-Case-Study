"""
Compare weekly route costs against trailing historical baseline and peer routes.

Definitions:
- Trailing 8-week baseline: Up to 8 prior weekly records strictly before the current week
  for the exact same (route, route_type). Current week is excluded.
- Peer baseline: All other routes sharing the same route_type in the same week.
  Current route is strictly excluded.
"""

import csv
from collections import defaultdict
from datetime import date
from pathlib import Path

# Project paths
ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = ROOT / "output" / "weekly_costs.csv"
OUTPUT_FILE = ROOT / "output" / "weekly_comparisons.csv"


def load_weekly_costs(filepath: Path):
    """Load weekly route cost records from CSV."""
    records = []
    with open(filepath, mode="r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            record = {
                "route": row["route"].strip(),
                "route_type": row["route_type"].strip(),
                "week_of": row["week_of"].strip(),
                "week_date": date.fromisoformat(row["week_of"].strip()),
                "total_cost": float(row["total_cost"]),
                "total_tonne_km": float(row["total_tonne_km"]),
                "shipment_count": int(row["shipment_count"]),
                "cost_per_tonne_km": float(row["cost_per_tonne_km"]),
            }
            records.append(record)
    return records


def compute_comparisons(records):
    """
    Compute trailing 8-week history comparison and same-week peer comparison.
    Returns enriched records sorted by (week_of, route).
    """
    # Group by (route, route_type) and sort chronologically
    by_route_group = defaultdict(list)
    for r in records:
        key = (r["route"], r["route_type"])
        by_route_group[key].append(r)

    for key in by_route_group:
        by_route_group[key].sort(key=lambda item: item["week_date"])

    # Group by (week_date, route_type) for peer comparisons
    by_week_type = defaultdict(dict)
    for r in records:
        by_week_type[(r["week_date"], r["route_type"])][r["route"]] = r["cost_per_tonne_km"]

    enriched = []

    for r in records:
        route = r["route"]
        route_type = r["route_type"]
        week_dt = r["week_date"]
        current_rate = r["cost_per_tonne_km"]

        # --- 1. Trailing Historical Baseline ---
        # Prior records for same route and route_type strictly before current week
        route_history = by_route_group[(route, route_type)]
        priors = [x for x in route_history if x["week_date"] < week_dt]
        recent_8 = priors[-8:] if len(priors) >= 8 else priors

        if recent_8:
            hist_avg = sum(x["cost_per_tonne_km"] for x in recent_8) / len(recent_8)
            pct_hist = ((current_rate - hist_avg) / hist_avg) * 100.0
            vs_history_str = f"{pct_hist:+.1f}% vs this route's past average"
        else:
            hist_avg = None
            pct_hist = None
            vs_history_str = "N/A (insufficient history)"

        # --- 2. Similar Routes Peer Baseline ---
        # Same week, same route_type, excluding current route
        peers = [
            rate
            for other_route, rate in by_week_type[(week_dt, route_type)].items()
            if other_route != route
        ]

        if peers:
            peer_avg = sum(peers) / len(peers)
            pct_peer = ((current_rate - peer_avg) / peer_avg) * 100.0
            vs_similar_str = f"{pct_peer:+.1f}% vs similar-length routes this week"
        else:
            peer_avg = None
            pct_peer = None
            vs_similar_str = "N/A (no peer data)"

        enriched.append({
            "route": route,
            "route_type": route_type,
            "week_of": r["week_of"],
            "week_date": week_dt,
            "total_cost": r["total_cost"],
            "total_tonne_km": r["total_tonne_km"],
            "shipment_count": r["shipment_count"],
            "cost_per_tonne_km": current_rate,
            "hist_avg_8w": hist_avg,
            "pct_vs_history": pct_hist,
            "vs_own_history": vs_history_str,
            "peer_avg": peer_avg,
            "pct_vs_peers": pct_peer,
            "vs_similar_routes": vs_similar_str,
        })

    # Sort consistently by week_of, route
    enriched.sort(key=lambda x: (x["week_of"], x["route"]))
    return enriched


def save_comparisons(enriched_records, filepath: Path):
    """Save enriched comparison records to CSV."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "route",
        "route_type",
        "week_of",
        "total_cost",
        "total_tonne_km",
        "shipment_count",
        "cost_per_tonne_km",
        "hist_avg_8w",
        "pct_vs_history",
        "vs_own_history",
        "peer_avg",
        "pct_vs_peers",
        "vs_similar_routes",
    ]

    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in enriched_records:
            writer.writerow({
                "route": r["route"],
                "route_type": r["route_type"],
                "week_of": r["week_of"],
                "total_cost": f"{r['total_cost']:.2f}",
                "total_tonne_km": f"{r['total_tonne_km']:.3f}",
                "shipment_count": r["shipment_count"],
                "cost_per_tonne_km": f"{r['cost_per_tonne_km']:.6f}",
                "hist_avg_8w": f"{r['hist_avg_8w']:.6f}" if r["hist_avg_8w"] is not None else "",
                "pct_vs_history": f"{r['pct_vs_history']:.4f}" if r["pct_vs_history"] is not None else "",
                "vs_own_history": r["vs_own_history"],
                "peer_avg": f"{r['peer_avg']:.6f}" if r["peer_avg"] is not None else "",
                "pct_vs_peers": f"{r['pct_vs_peers']:.4f}" if r["pct_vs_peers"] is not None else "",
                "vs_similar_routes": r["vs_similar_routes"],
            })


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}. Run aggregate_weekly.py first."
        )

    records = load_weekly_costs(INPUT_FILE)
    enriched = compute_comparisons(records)
    save_comparisons(enriched, OUTPUT_FILE)

    print(f"Loaded {len(records)} weekly records.")
    print(f"Generated {len(enriched)} enriched comparison records.")
    print(f"Output saved to: {OUTPUT_FILE}")

    # Spot check the sample test cases
    check_targets = [
        ("Delhi-Jaipur", "2024-11-11"),
        ("Ahmedabad-Mumbai", "2025-01-20"),
        ("Mumbai-Pune", "2025-09-15"),
    ]
    print("\n--- Spot Checking Known Sample Cases ---")
    for tr, tw in check_targets:
        match = next((x for x in enriched if x["route"] == tr and x["week_of"] == tw), None)
        if match:
            print(f"[{match['route']} | {match['week_of']}]")
            print(f"  Cost/tonne-km: {match['cost_per_tonne_km']:.2f} ({match['cost_per_tonne_km']:.6f})")
            print(f"  vs own history: {match['vs_own_history']}")
            print(f"  vs similar routes: {match['vs_similar_routes']}")


if __name__ == "__main__":
    main()