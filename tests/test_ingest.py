import gzip
import unittest
from pathlib import Path
from xml.etree.ElementTree import ParseError

from kpi_autopsy.database import connect, metadata
from kpi_autopsy.ingest import ingest
from tests.fixtures import write_log
from tests.support import temporary_directory


class IngestionTests(unittest.TestCase):
    def test_source_cannot_be_used_as_the_database_target(self):
        with temporary_directory() as directory:
            source = write_log(Path(directory) / "source.xes.gz")
            before = source.read_bytes()
            with self.assertRaises(ValueError):
                ingest(source, source, force=True)
            self.assertEqual(source.read_bytes(), before)

    def test_idempotent_ingestion_and_atomic_rebuild(self):
        with temporary_directory() as directory:
            root = Path(directory)
            source = write_log(root / "source.xes.gz")
            target = root / "test.sqlite"
            first = ingest(source, target)
            self.assertEqual(first["applications"], "6")
            self.assertEqual(ingest(source, target), first)
            bad = root / "bad.xes.gz"
            with gzip.open(bad, "wb") as stream:
                stream.write(b"<log><trace>")
            with self.assertRaises(ParseError):
                ingest(bad, target, force=True)
            connection = connect(target)
            try:
                self.assertEqual(metadata(connection), first)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM applications").fetchone()[0], 6)
            finally:
                connection.close()
