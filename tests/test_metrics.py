import unittest

from kpi_autopsy.database import snapshot, sql, utc_timestamp
from kpi_autopsy.metrics import Cohort, Contribution, METRICS, QueryError, aggregate, calculate, run_query
from tests.support import DataCase


class MetricTests(DataCase):
    def test_reference_values_can_be_checked_by_hand(self):
        values = {row["metric_id"]: row for row in calculate(self.connection, self.cohort)}
        self.assertEqual(values["accepted_offer_rate"]["value"], 20)
        self.assertAlmostEqual(values["first_offer_hours"]["value"], 13.75, places=5)
        self.assertEqual(values["first_offer_hours"]["denominator"], 4)
        self.assertEqual(values["open_backlog"]["value"], 2)

    def test_later_acceptance_does_not_leak_into_earlier_snapshot(self):
        early = self.connection.execute("SELECT accepted_offer FROM case_snapshot WHERE application_id='E'").fetchone()[0]
        cutoff = snapshot(self.connection, "2016-01-15T00:00:00Z")
        later = Cohort.create("2016-01-01", "2016-01-05", cutoff)
        values = {row["metric_id"]: row["value"] for row in calculate(self.connection, later)}
        self.assertEqual(early, 0)
        self.assertEqual(values["accepted_offer_rate"], 40)
        self.assertEqual(values["open_backlog"], 1)

    def test_timestamp_offsets_are_normalized(self):
        self.assertEqual(utc_timestamp("2016-01-01T03:00:00+01:00"), "2016-01-01T02:00:00.000000Z")
        with self.assertRaises(ValueError):
            utc_timestamp("2016-01-01T02:00:00")

    def test_empty_means_are_blank_but_empty_counts_are_zero(self):
        self.assertIsNone(aggregate(METRICS["first_offer_hours"], [])["value"])
        self.assertIsNone(aggregate(METRICS["accepted_offer_rate"], [])["value"])
        self.assertEqual(aggregate(METRICS["open_backlog"], [])["value"], 0)

    def test_non_finite_aggregates_are_rejected(self):
        with self.assertRaises(QueryError):
            aggregate(METRICS["open_backlog"], [Contribution("A", 1e308, 1), Contribution("B", 1e308, 1)])
        with self.assertRaises(QueryError):
            aggregate(METRICS["accepted_offer_rate"], [Contribution("A", 1e308, 1e-308)])

    def test_contract_rejects_reversed_dates_and_unobserved_future(self):
        with self.assertRaises(ValueError):
            Cohort.create("2016-01-05", "2016-01-01", self.cutoff)
        with self.assertRaises(ValueError):
            Cohort.create("2016-01-01", "2016-02-01", self.cutoff)

    def test_snapshot_and_contract_must_use_the_same_cutoff(self):
        other = Cohort.create("2016-01-01", "2016-01-05", "2016-01-11T00:00:00Z")
        with self.assertRaises(QueryError):
            run_query(self.connection, sql("accepted_offer_rate.sql"), other)
        with self.assertRaises(ValueError):
            snapshot(self.connection, "2017-01-01T00:00:00Z")

    def test_submitted_queries_cannot_modify_data(self):
        with self.assertRaises(QueryError):
            run_query(self.connection, "DELETE FROM applications", self.cohort)
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM applications").fetchone()[0], 6)

        self.connection.execute("CREATE TEMP TABLE still_writable (value INTEGER)")

    def test_contribution_interface_rejects_null_and_wrong_columns(self):
        for query in ("SELECT 1 AS wrong", "SELECT 'A' AS application_id, NULL AS numerator, 1 AS denominator"):
            with self.subTest(query=query), self.assertRaises(QueryError):
                run_query(self.connection, query, self.cohort)

    def test_duplicate_offer_does_not_change_application_rate(self):
        before = calculate(self.connection, self.cohort)[0]["value"]
        self.connection.execute("""
            INSERT INTO events VALUES (100, 'B', 'extra-offer', 'b3', 'O_Create Offer', 'Offer',
            'complete', '2016-01-03T01:00:00.000000Z', '2016-01-03T01:00:00Z', 10000)
        """)
        snapshot(self.connection, self.cutoff)
        after = calculate(self.connection, self.cohort)[0]["value"]
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
