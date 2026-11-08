import csv
import json
import math
import io
from contextlib import redirect_stdout

from kpi_autopsy.cli import main
from kpi_autopsy.export import export_reports
from kpi_autopsy.metrics import Cohort
from kpi_autopsy.powerbi import generate
from tests.support import DataCase


class ReportTests(DataCase):
    def test_export_retains_unexpected_cases_for_evidence_and_filters_reference_metrics(self):
        result = export_reports(self.connection, self.cohort, self.root / "reports")
        self.assertEqual(result["applications"], 5)
        self.assertEqual(result["snapshot_applications"], 6)
        folder = self.root / "reports" / "powerbi"
        with (folder / "cases.csv").open(newline="", encoding="utf-8") as stream:
            cases = list(csv.DictReader(stream))
        cohort = [row for row in cases if row["in_cohort"] == "1"]
        self.assertEqual(len(cohort), 5)
        self.assertEqual(next(row for row in cases if row["application_id"] == "C")["in_cohort"], "0")
        self.assertEqual(sum(int(row["accepted_offer"]) for row in cohort) / len(cohort) * 100, 20)
        self.assertAlmostEqual(math.fsum(float(row["first_offer_hours"]) for row in cohort if row["first_offer_hours"]) / 4, 13.75, places=5)
        identities = {row["application_id"] for row in cases}
        with (folder / "case_evidence.csv").open(newline="", encoding="utf-8") as stream:
            evidence = list(csv.DictReader(stream))
        self.assertTrue({row["application_id"] for row in evidence} <= identities)
        self.assertIn("C", {row["application_id"] for row in evidence})

    def test_generated_report_has_valid_bindings_and_no_off_page_visuals(self):
        export_reports(self.connection, self.cohort, self.root / "reports")
        project = generate(self.root / "reports" / "powerbi", self.root / "powerbi")
        self.assertTrue(project.is_file())
        model = json.loads((self.root / "powerbi/KPI_Autopsy.SemanticModel/model.bim").read_text())["model"]
        tables = {table["name"]: table for table in model["tables"]}
        for path in (self.root / "powerbi/KPI_Autopsy.Report/definition/pages").glob("*/page.json"):
            page = json.loads(path.read_text())
            for visual_path in path.parent.glob("visuals/*/visual.json"):
                visual = json.loads(visual_path.read_text())
                position = visual["position"]
                self.assertGreaterEqual(position["x"], 0)
                self.assertGreaterEqual(position["y"], 0)
                self.assertLessEqual(position["x"] + position["width"], page["width"])
                self.assertLessEqual(position["y"] + position["height"], page["height"])
                for role in visual["visual"].get("query", {}).get("queryState", {}).values():
                    for projection in role["projections"]:
                        kind, binding = next(iter(projection["field"].items()))
                        table = tables[binding["Expression"]["SourceRef"]["Entity"]]
                        names = {field["name"] for field in table["measures" if kind == "Measure" else "columns"]}
                        self.assertIn(binding["Property"], names)

    def test_empty_cohort_does_not_write_partial_reports(self):
        empty = Cohort.create("2015-01-01", "2015-02-01", self.cutoff)
        output = self.root / "empty"
        with self.assertRaises(ValueError):
            export_reports(self.connection, empty, output)
        self.assertFalse(output.exists())

    def test_audit_cli_exit_status_distinguishes_mismatch_from_error(self):
        common = ["--database", str(self.root / "test.sqlite"), "--start", "2016-01-01",
                  "--end", "2016-01-05", "--as-of", self.cutoff,
                  "--output", str(self.root / "cli-report")]
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["demo", "wrong-stage", *common]), 1)
            self.assertEqual(main(["demo", "clean-rate", *common]), 0)
