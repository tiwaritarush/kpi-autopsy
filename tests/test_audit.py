from kpi_autopsy.audit import audit_query
from kpi_autopsy.benchmark import benchmark, wrapped
from kpi_autopsy.database import snapshot, sql
from kpi_autopsy.metrics import QueryError
from kpi_autopsy.scenarios import SCENARIOS
from tests.support import DataCase
from types import SimpleNamespace
from unittest.mock import patch


class AuditTests(DataCase):
    def test_overflowing_duplicate_contributions_return_a_query_error(self):
        query = """
            SELECT 'A' AS application_id, 1e308 AS numerator, 1 AS denominator
            UNION ALL SELECT 'A', 1e308, 1
        """
        with self.assertRaises(QueryError):
            audit_query(self.connection, "accepted_offer_rate", query, self.cohort)

    def test_each_fault_has_the_expected_evidence(self):
        expected_cases = {
            "wrong-stage": {"B", "D", "E", "F"},
            "offer-join": {"B", "D"},
            "offer-cohort": {"C", "D"},
            "outcome-filter": {"B", "E", "F"},
        }
        for identity, identities in expected_cases.items():
            scenario = SCENARIOS[identity]
            result = audit_query(self.connection, scenario.metric_id, sql(scenario.query_file), self.cohort)
            with self.subTest(scenario=identity):
                self.assertIn(scenario.expected_issue, [issue["code"] for issue in result.issues])
                self.assertEqual({row["application_id"] for row in result.evidence}, identities)

    def test_same_headline_can_hide_invalid_grain(self):
        result = audit_query(self.connection, "accepted_offer_rate", sql("offer_join.sql"), self.cohort)
        self.assertEqual(result.reported["value"], result.reference["value"])
        self.assertEqual(result.status, "mismatch")
        self.assertEqual(result.issues[0]["code"], "GRAIN_MISMATCH")

    def test_clean_controls_do_not_raise_an_issue(self):
        for scenario in SCENARIOS.values():
            if scenario.expected_issue is None:
                for query in (sql(scenario.query_file), wrapped(sql(scenario.query_file))):
                    result = audit_query(self.connection, scenario.metric_id, query, self.cohort)
                    self.assertEqual(result.status, "reconciled")
                    self.assertEqual(result.evidence, [])

    def test_audit_uses_contributions_rather_than_a_query_filename(self):
        query = """
            SELECT application_id, 1 AS denominator,
                   CASE WHEN application_stage_at IS NULL THEN 0 ELSE 1 END AS numerator
            FROM case_snapshot WHERE :start <= created_at AND created_at < :end
        """
        result = audit_query(self.connection, "accepted_offer_rate", query, self.cohort)
        self.assertEqual(result.issues[0]["code"], "EVENT_DEFINITION_MISMATCH")

    def test_benchmark_contains_faults_and_clean_controls(self):
        cutoff = snapshot(self.connection)
        result = benchmark(self.connection, cutoff, [1])
        self.assertEqual(result["cases"], 14)
        self.assertEqual(result["clean_cases"], 6)
        self.assertEqual(result["fault_cases"], 8)
        self.assertEqual(result["false_positives"], 0)
        self.assertEqual(result["false_negatives"], 0)
        self.assertEqual(result["issue_label_accuracy"], 1)

    def test_a_broken_detector_cannot_improve_its_score_by_hiding_evidence(self):
        cutoff = snapshot(self.connection)
        clean_result = SimpleNamespace(issues=[], evidence=[], query_ms=0)
        with patch("kpi_autopsy.benchmark.audit_query", return_value=clean_result):
            result = benchmark(self.connection, cutoff, [1])
        self.assertEqual(result["fault_cases"], 8)
        self.assertEqual(result["false_negatives"], 8)
        self.assertEqual(result["detection_recall"], 0)
