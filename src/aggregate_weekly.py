
import csv
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

# Locate the project directory.
ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = ROOT / "shipment_records.csv"
OUTPUT_FILE = ROOT / "output" / "weekly_costs.csv"


def main():
    # Each key represents one route, route type and week.
    weekly_totals = defaultdict(
        lambda: {
            "total_cost": 0.0,
            "total_tonne_km": 0.0,
            "shipment_count": 0,
        }
    )

    seen_ids = set()
    shipment_count = 0

    # Open and read the CSV file.
    with open(
        INPUT_FILE,
        mode="r",
        newline="",
        encoding="utf-8-sig",
    ) as file:

        reader = csv.DictReader(file)

        required_columns = {
            "shipment_id",
            "origin",
            "destination",
            "route_type",
            "quantity_tonnes",
            "distance_km",
            "freight_cost_inr",
            "shipment_date",
        }

        missing = required_columns - set(reader.fieldnames or [])

        if missing:
            raise ValueError(
                f"Missing columns: {sorted(missing)}"
            )

        for row_number, row in enumerate(reader, start=2):
            shipment_id = row["shipment_id"].strip()

            # Reject missing or duplicate shipment IDs.
            if not shipment_id:
                raise ValueError(
                    f"Missing shipment ID at row {row_number}"
                )

            if shipment_id in seen_ids:
                raise ValueError(
                    f"Duplicate shipment ID: {shipment_id}"
                )

            seen_ids.add(shipment_id)

            # Read and validate the numeric values.
            quantity = float(row["quantity_tonnes"])
            distance = float(row["distance_km"])
            cost = float(row["freight_cost_inr"])

            if quantity <= 0 or distance <= 0 or cost <= 0:
                raise ValueError(
                    f"Invalid quantity, distance or cost "
                    f"at row {row_number}"
                )

            # Convert the shipment date into a date object.
            shipment_date = date.fromisoformat(
                row["shipment_date"].strip()[:10]
            )

            # Calculate the Monday starting this week.
            week_of = shipment_date - timedelta(
                days=shipment_date.weekday()
            )

            origin = row["origin"].strip()
            destination = row["destination"].strip()
            route_type = row["route_type"].strip()

            route = f"{origin}-{destination}"

            # Transport work is measured in tonne-kilometres.
            tonne_km = quantity * distance

            key = (route, route_type, week_of)
            totals = weekly_totals[key]

            totals["total_cost"] += cost
            totals["total_tonne_km"] += tonne_km
            totals["shipment_count"] += 1

            shipment_count += 1

    # Create the output directory if necessary.
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    columns = [
        "route",
        "route_type",
        "week_of",
        "total_cost",
        "total_tonne_km",
        "shipment_count",
        "cost_per_tonne_km",
    ]

    # Write one record per route, route type and week.
    with open(
        OUTPUT_FILE,
        mode="w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()

        for key, totals in sorted(weekly_totals.items()):
            route, route_type, week_of = key

            rate = (
                totals["total_cost"]
                / totals["total_tonne_km"]
            )

            writer.writerow({
                "route": route,
                "route_type": route_type,
                "week_of": week_of.isoformat(),
                "total_cost": f'{totals["total_cost"]:.2f}',
                "total_tonne_km": (
                    f'{totals["total_tonne_km"]:.3f}'
                ),
                "shipment_count": totals["shipment_count"],
                "cost_per_tonne_km": f"{rate:.6f}",
            })

    print("Shipment records processed:", shipment_count)
    print("Weekly route records:", len(weekly_totals))
    print("Output saved to:", OUTPUT_FILE)

    # Verify a known example from the sample output.
    example_key = (
        "Delhi-Jaipur",
        "Short",
        date(2024, 11, 11),
    )

    if example_key in weekly_totals:
        totals = weekly_totals[example_key]
        rate = (
            totals["total_cost"]
            / totals["total_tonne_km"]
        )

        print(
            "Delhi-Jaipur example cost per tonne-km:",
            f"{rate:.6f}",
        )
    else:
        print("The sample route-week was not found.")


if __name__ == "__main__":
    main()

