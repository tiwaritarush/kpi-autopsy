import unittest
from contextlib import closing
from pathlib import Path

from kpi_autopsy.database import connect, metadata, snapshot
from kpi_autopsy.metrics import Cohort, calculate

DATABASE = Path(__file__).resolve().parents[1] / "data/autopsy.sqlite"


@unittest.skipUnless(DATABASE.is_file(), "Optional real-data check: run the build command first.")
class RealDataTests(unittest.TestCase):
    def test_pinned_dataset_counts_and_reference_values(self):
        with closing(connect(DATABASE)) as connection:
            info = metadata(connection)
            self.assertEqual(info["applications"], "31509")
            self.assertEqual(info["events"], "1202267")
            cutoff = snapshot(connection)
            values = {row["metric_id"]: row["value"] for row in calculate(
                connection, Cohort.create("2016-01-01", "2017-01-01", cutoff))}
            self.assertAlmostEqual(values["accepted_offer_rate"], 17228 / 31509 * 100)
            self.assertAlmostEqual(values["first_offer_hours"], 37.38863653433503)
            self.assertEqual(values["open_backlog"], 98)
