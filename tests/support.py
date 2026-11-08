import tempfile
import unittest
from pathlib import Path

from kpi_autopsy.database import connect, snapshot
from kpi_autopsy.ingest import ingest
from kpi_autopsy.metrics import Cohort
from tests.fixtures import write_log


def temporary_directory():
    root = Path(__file__).resolve().parents[1] / ".test-tmp"
    root.mkdir(exist_ok=True)
    return tempfile.TemporaryDirectory(prefix="case-", dir=root)


class DataCase(unittest.TestCase):
    def setUp(self):
        self.directory = temporary_directory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        source = write_log(self.root / "source.xes.gz")
        ingest(source, self.root / "test.sqlite")
        self.connection = connect(self.root / "test.sqlite")
        self.addCleanup(self.connection.close)
        self.cutoff = snapshot(self.connection, "2016-01-10T00:00:00Z")
        self.cohort = Cohort.create("2016-01-01", "2016-01-05", self.cutoff)
