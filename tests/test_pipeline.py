"""
Unit test suite for Freight Tiger Shipping Cost Watch Assistant.

Test coverage:
1. TestDataQualityAndSchema:
   - Validates shipment_records.csv schema, types, positive values, exactly 2,940 records.
   - Validates context_notes.csv schema, valid dates, non-empty fields, exactly 10 notes.
2. TestAggregationLogic:
   - Tests Monday-starting week calculation across all weekdays.
   - Tests weighted cost per tonne-km formula (total_cost / total_tonne_km).
3. TestComparisonLogic:
   - Tests trailing 8-week historical rolling baseline (strictly prior weeks, no look-ahead).
   - Tests same-week peer baseline (same route_type, strictly excludes current route).
4. TestContextMatchingAndSampleCases:
   - Tests exact final output schema (8 columns in required order) and 728 row count.
   - Tests exact match for 3 Freight Tiger sample benchmark cases.
   - Tests multi-week flood disruption window (N001) for Chennai-Bangalore.
   - Tests decoy / non-justifying notes (N004, N005, N006, N007, N008, N009, N010).
   - Tests small nationwide fuel rise (N003, 5-7%) is insufficient to justify a >=20% corridor anomaly.
   - Tests post-flood date boundary (week of 2025-03-10 is unexplained after flood ended Mar 8).
   - Tests that flagged_anomalies.csv is strictly a human-review queue of unexplained anomalies (flagged == 'Yes').
5. TestAssistantInterface:
   - Tests natural-language query parsing for justified, unexplained, normal, and ambiguous queries.
"""

import csv
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

# Add project root and src to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import aggregate_weekly
import compare_history
import detect_anomalies
import ask_assistant


class TestDataQualityAndSchema(unittest.TestCase):
    def test_shipment_records_schema_and_values(self):
        """Validate input shipment_records.csv schema and numeric constraints."""
        file_path = ROOT / "shipment_records.csv"
        self.assertTrue(file_path.exists(), "shipment_records.csv must exist")

        with open(file_path, mode="r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            expected_cols = {
                "shipment_id", "origin", "destination", "route_type",
                "material", "quantity_tonnes", "distance_km",
                "freight_cost_inr", "shipment_date"
            }
            self.assertTrue(expected_cols.issubset(set(reader.fieldnames or [])))

            seen_ids = set()
            count = 0
            for row_num, row in enumerate(reader, start=2):
                sid = row["shipment_id"].strip()
                self.assertTrue(sid, f"Missing shipment_id at row {row_num}")
                self.assertNotIn(sid, seen_ids, f"Duplicate shipment_id {sid}")
                seen_ids.add(sid)

                qty = float(row["quantity_tonnes"])
                dist = float(row["distance_km"])
                cost = float(row["freight_cost_inr"])
                self.assertGreater(qty, 0, f"Non-positive quantity at row {row_num}")
                self.assertGreater(dist, 0, f"Non-positive distance at row {row_num}")
                self.assertGreater(cost, 0, f"Non-positive cost at row {row_num}")
                count += 1

            self.assertEqual(count, 2940, "Expected exactly 2,940 shipment records")

    def test_context_notes_schema(self):
        """Validate context_notes.csv schema and dates."""
        file_path = ROOT / "context_notes.csv"
        self.assertTrue(file_path.exists(), "context_notes.csv must exist")

        with open(file_path, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            expected_cols = {"note_id", "date", "applies_to", "note"}
            self.assertTrue(expected_cols.issubset(set(reader.fieldnames or [])))

            notes = list(reader)
            self.assertEqual(len(notes), 10, "Expected exactly 10 context notes")
            for n in notes:
                self.assertTrue(n["note_id"].startswith("N"))
                d = date.fromisoformat(n["date"])
                self.assertIsInstance(d, date)
                self.assertTrue(n["applies_to"])
                self.assertTrue(n["note"])


class TestAggregationLogic(unittest.TestCase):
    def test_monday_starting_week(self):
        """Verify Monday-starting week logic for arbitrary dates."""
        # Wednesday
        d1 = date(2024, 11, 13)
        mon1 = d1 - timedelta(days=d1.weekday())
        self.assertEqual(mon1, date(2024, 11, 11))
        self.assertEqual(mon1.weekday(), 0)  # Monday is 0

        # Sunday
        d2 = date(2024, 11, 17)
        mon2 = d2 - timedelta(days=d2.weekday())
        self.assertEqual(mon2, date(2024, 11, 11))
        self.assertEqual(mon2.weekday(), 0)

        # Monday itself
        d3 = date(2024, 11, 11)
        mon3 = d3 - timedelta(days=d3.weekday())
        self.assertEqual(mon3, date(2024, 11, 11))

    def test_weighted_cost_per_tonne_km(self):
        """Verify cost per tonne-km is total_cost / total_tonne_km."""
        weekly_file = ROOT / "output" / "weekly_costs.csv"
        self.assertTrue(weekly_file.exists())

        with open(weekly_file, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cost = float(row["total_cost"])
                tonne_km = float(row["total_tonne_km"])
                rate = float(row["cost_per_tonne_km"])
                expected_rate = cost / tonne_km
                self.assertAlmostEqual(rate, expected_rate, places=5)


class TestComparisonLogic(unittest.TestCase):
    def test_historical_baseline_excludes_current_week(self):
        """Verify historical trailing 8 weeks excludes current week and does not look ahead."""
        records = compare_history.load_weekly_costs(ROOT / "output" / "weekly_costs.csv")
        enriched = compare_history.compute_comparisons(records)

        for r in enriched:
            week_dt = r["week_date"]
            route = r["route"]
            rtype = r["route_type"]

            priors = [
                x for x in records
                if x["route"] == route and x["route_type"] == rtype and x["week_date"] < week_dt
            ]
            recent_8 = priors[-8:] if len(priors) >= 8 else priors

            if recent_8:
                expected_avg = sum(x["cost_per_tonne_km"] for x in recent_8) / len(recent_8)
                self.assertAlmostEqual(r["hist_avg_8w"], expected_avg, places=5)
                expected_pct = ((r["cost_per_tonne_km"] - expected_avg) / expected_avg) * 100
                self.assertAlmostEqual(r["pct_vs_history"], expected_pct, places=3)
            else:
                self.assertIsNone(r["hist_avg_8w"])
                self.assertIsNone(r["pct_vs_history"])
                self.assertEqual(r["vs_own_history"], "N/A (insufficient history)")

    def test_peer_baseline_excludes_current_route(self):
        """Verify peer baseline strictly excludes the current route itself."""
        records = compare_history.load_weekly_costs(ROOT / "output" / "weekly_costs.csv")
        enriched = compare_history.compute_comparisons(records)

        for r in enriched:
            week_dt = r["week_date"]
            route = r["route"]
            rtype = r["route_type"]

            peers = [
                x for x in records
                if x["week_date"] == week_dt and x["route_type"] == rtype and x["route"] != route
            ]

            if peers:
                expected_peer_avg = sum(x["cost_per_tonne_km"] for x in peers) / len(peers)
                self.assertAlmostEqual(r["peer_avg"], expected_peer_avg, places=5)
                expected_peer_pct = ((r["cost_per_tonne_km"] - expected_peer_avg) / expected_peer_avg) * 100
                self.assertAlmostEqual(r["pct_vs_peers"], expected_peer_pct, places=3)
            else:
                self.assertIsNone(r["peer_avg"])
                self.assertIsNone(r["pct_vs_peers"])
                self.assertEqual(r["vs_similar_routes"], "N/A (no peer data)")


class TestContextMatchingAndSampleCases(unittest.TestCase):
    def setUp(self):
        self.final_file = ROOT / "output" / "final_output.csv"
        with open(self.final_file, mode="r", newline="", encoding="utf-8") as f:
            self.final_records = list(csv.DictReader(f))
        self.final_map = {(r["route"], r["week_of"]): r for r in self.final_records}

    def test_final_csv_schema_and_order(self):
        """Verify exact columns, ordering, and total row count."""
        expected_columns = [
            "route",
            "week_of",
            "cost_per_tonne_km",
            "vs_own_history",
            "vs_similar_routes",
            "flagged",
            "matched_note_id",
            "reason",
        ]
        with open(self.final_file, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)
            self.assertEqual(headers, expected_columns)

        self.assertEqual(len(self.final_records), 728, "Expected exactly 728 route-week records")

    def test_known_sample_cases_exact_match(self):
        """Verify known test cases: Delhi-Jaipur, Ahmedabad-Mumbai, Mumbai-Pune."""
        # 1. Delhi-Jaipur, 2024-11-11
        dj = self.final_map.get(("Delhi-Jaipur", "2024-11-11"))
        self.assertIsNotNone(dj)
        self.assertEqual(dj["cost_per_tonne_km"], "4.17")
        self.assertEqual(dj["vs_own_history"], "+35.5% vs this route's past average")
        self.assertEqual(dj["vs_similar_routes"], "+21.0% vs similar-length routes this week")
        self.assertEqual(dj["flagged"], "Yes")
        self.assertEqual(dj["matched_note_id"], "")
        self.assertIn("No matching note found", dj["reason"])

        # 2. Ahmedabad-Mumbai, 2025-01-20
        am = self.final_map.get(("Ahmedabad-Mumbai", "2025-01-20"))
        self.assertIsNotNone(am)
        self.assertEqual(am["cost_per_tonne_km"], "3.29")
        self.assertEqual(am["vs_own_history"], "+29.5% vs this route's past average")
        self.assertEqual(am["vs_similar_routes"], "+22.5% vs similar-length routes this week")
        self.assertEqual(am["flagged"], "No (justified)")
        self.assertEqual(am["matched_note_id"], "N002")
        self.assertIn("Matches note N002 dated 2025-01-20", am["reason"])

        # 3. Mumbai-Pune, 2025-09-15
        mp = self.final_map.get(("Mumbai-Pune", "2025-09-15"))
        self.assertIsNotNone(mp)
        self.assertEqual(mp["cost_per_tonne_km"], "3.98")
        self.assertEqual(mp["vs_own_history"], "+9.2% vs this route's past average")
        self.assertEqual(mp["vs_similar_routes"], "+23.6% vs similar-length routes this week")
        self.assertEqual(mp["flagged"], "Yes")
        self.assertEqual(mp["matched_note_id"], "")
        self.assertIn("The closest note (N006, 2025-09-22) mentions stable demand with no major disruptions", mp["reason"])

    def test_chennai_bangalore_flood_justified(self):
        """Verify Chennai-Bangalore during flood event (N001) is justified across multi-week active window."""
        cb_feb24 = self.final_map.get(("Chennai-Bangalore", "2025-02-24"))
        self.assertIsNotNone(cb_feb24)
        self.assertEqual(cb_feb24["flagged"], "No (justified)")
        self.assertEqual(cb_feb24["matched_note_id"], "N001")
        self.assertIn("Matches note N001", cb_feb24["reason"])

        cb_mar03 = self.final_map.get(("Chennai-Bangalore", "2025-03-03"))
        self.assertIsNotNone(cb_mar03)
        self.assertEqual(cb_mar03["flagged"], "No (justified)")
        self.assertEqual(cb_mar03["matched_note_id"], "N001")

    def test_flood_event_date_boundaries(self):
        """Verify that after flood ended (Mar 8), subsequent weeks are flagged unexplained."""
        cb_mar10 = self.final_map.get(("Chennai-Bangalore", "2025-03-10"))
        self.assertIsNotNone(cb_mar10)
        self.assertEqual(cb_mar10["flagged"], "Yes")
        self.assertEqual(cb_mar10["matched_note_id"], "")

        cb_mar17 = self.final_map.get(("Chennai-Bangalore", "2025-03-17"))
        self.assertIsNotNone(cb_mar17)
        self.assertEqual(cb_mar17["flagged"], "Yes")
        self.assertEqual(cb_mar17["matched_note_id"], "")

    def test_decoy_and_non_justifying_notes(self):
        """Verify decoy notes are correctly evaluated as non-justifying."""
        notes = detect_anomalies.load_context_notes(ROOT / "context_notes.csv")
        notes_by_id = {n["note_id"]: n for n in notes}

        # N004 (out of dataset), N005 (costs not affected), N006 (stable demand),
        # N007 (improved road), N008 (no disruptions), N009 (returned to normal),
        # N010 (costs absorbed without rate change) must all be False
        non_justifying_ids = ["N004", "N005", "N006", "N007", "N008", "N009", "N010"]
        for nid in non_justifying_ids:
            self.assertFalse(
                notes_by_id[nid]["is_justification"],
                f"Note {nid} should be evaluated as non-justifying decoy"
            )

    def test_fuel_price_small_increase_not_justifying_anomaly(self):
        """Verify N003 (5-7% diesel increase) does not justify an anomalous spike (>=20%)."""
        notes = detect_anomalies.load_context_notes(ROOT / "context_notes.csv")
        n003 = next(n for n in notes if n["note_id"] == "N003")
        self.assertFalse(
            n003["is_justification"],
            "N003 (5-7% diesel increase) must not justify an anomaly threshold of >=20%"
        )

    def test_flagged_anomalies_review_queue_filter(self):
        """Verify flagged_anomalies.csv contains strictly unexplained anomalies (flagged == 'Yes')."""
        queue_file = ROOT / "output" / "flagged_anomalies.csv"
        self.assertTrue(queue_file.exists())

        with open(queue_file, mode="r", newline="", encoding="utf-8") as f:
            queue_records = list(csv.DictReader(f))

        self.assertEqual(len(queue_records), 16, "Review queue must contain exactly 16 records")
        for r in queue_records:
            self.assertEqual(r["flagged"], "Yes", f"Review queue row {r['route']} {r['week_of']} must be 'Yes'")
            self.assertEqual(r["matched_note_id"], "", "Unexplained anomaly must have blank matched_note_id")


class TestAssistantInterface(unittest.TestCase):
    def setUp(self):
        self.records = ask_assistant.load_final_data()

    def test_justified_query(self):
        """Test assistant response for a justified anomaly."""
        res = ask_assistant.answer_query("Why did Chennai-Bangalore get pricier in March 2025?", self.records)
        self.assertIn("Chennai-Bangalore", res)
        self.assertIn("No (justified)", res)
        self.assertIn("N001", res)

    def test_unexplained_query(self):
        """Test assistant response for an unexplained anomaly."""
        res = ask_assistant.answer_query("Why was Delhi-Jaipur flagged in November 2024?", self.records)
        self.assertIn("Delhi-Jaipur", res)
        self.assertIn("Yes", res)
        self.assertIn("No matching note found", res)

    def test_normal_period_query(self):
        """Test assistant response for a normal non-anomaly period."""
        res = ask_assistant.answer_query("How was Mumbai-Delhi in March 2024?", self.records)
        self.assertIn("Mumbai-Delhi", res)
        self.assertIn("No unusual cost spikes were detected", res)

    def test_ambiguous_query(self):
        """Test assistant handling of query without route name."""
        res = ask_assistant.answer_query("What happened in March 2025?", self.records)
        self.assertIn("I could not identify the specific route", res)
        self.assertIn("Available routes are:", res)


if __name__ == "__main__":
    unittest.main()
