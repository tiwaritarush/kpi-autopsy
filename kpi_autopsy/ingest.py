import gzip
import hashlib
import math
import tempfile
import urllib.request
from contextlib import closing
from pathlib import Path
from xml.etree import ElementTree as ET

from .database import connect, metadata, sql, utc_timestamp

DATA_URL = "https://data.4tu.nl/file/34c3f44b-3101-4ea9-8281-e38905c68b8d/f3aec4f7-d52c-4217-82f4-57d719a8298c"
DATA_SHA256 = "183c5e5189282779c811c78c33ff936351b3dd201165d612211fc220936f8249"


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def download(target: Path) -> Path:
    if target.exists():
        if sha256(target) != DATA_SHA256:
            raise ValueError(f"The existing source file has an unexpected checksum: {target}")
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".part", delete=False) as stream:
        temporary = Path(stream.name)
    try:
        request = urllib.request.Request(DATA_URL, headers={"User-Agent": "KPI-Autopsy/0.1"})
        with urllib.request.urlopen(request, timeout=60) as response, temporary.open("wb") as stream:
            while chunk := response.read(1024 * 1024):
                stream.write(chunk)
        if sha256(temporary) != DATA_SHA256:
            raise ValueError("The downloaded file does not match the pinned dataset checksum.")
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def attributes(element: ET.Element) -> dict[str, str]:
    return {child.attrib["key"]: child.attrib["value"] for child in element
            if "key" in child.attrib and "value" in child.attrib}


def number(value: str | None) -> float | None:
    if value is None:
        return None
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("A numeric source field contains a non-finite value.")
    return result


def ingest(source: Path, target: Path, *, force: bool = False) -> dict[str, str]:
    if source.resolve() == target.resolve():
        raise ValueError("Source and database must be different files.")
    checksum = sha256(source)
    if target.exists() and not force:
        with closing(connect(target)) as existing:
            info = metadata(existing)
        if info.get("schema_version") != "1":
            raise ValueError("The database uses a different schema. Use --force to rebuild it.")
        if info.get("source_sha256") != checksum:
            raise ValueError("The database was built from a different file. Use --force to rebuild it.")
        return info

    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".sqlite", delete=False) as stream:
        temporary = Path(stream.name)
    connection = connect(temporary)
    try:
        connection.executescript(sql("schema.sql"))
        event_count = 0
        application_count = 0
        pending = []
        first_at, last_at = None, None
        with gzip.open(source, "rb") as stream:
            parser = ET.iterparse(stream, events=("start", "end"))
            _, root = next(parser)
            for action, trace in parser:
                if action != "end" or trace.tag.rsplit("}", 1)[-1] != "trace":
                    continue
                fields = attributes(trace)
                application_id = fields["concept:name"]
                connection.execute("INSERT INTO applications VALUES (?, ?, ?, ?)", (
                    application_id, fields.get("ApplicationType"), fields.get("LoanGoal"),
                    number(fields.get("RequestedAmount")),
                ))
                application_count += 1
                for event in trace:
                    if event.tag.rsplit("}", 1)[-1] != "event":
                        continue
                    fields = attributes(event)
                    timestamp = utc_timestamp(fields["time:timestamp"])
                    event_count += 1
                    first_at = min(first_at or timestamp, timestamp)
                    last_at = max(last_at or timestamp, timestamp)
                    pending.append((
                        event_count, application_id, fields.get("EventID"), fields.get("OfferID"),
                        fields["concept:name"], fields.get("EventOrigin", ""),
                        fields.get("lifecycle:transition"), timestamp, fields["time:timestamp"],
                        number(fields.get("OfferedAmount")),
                    ))
                    if len(pending) >= 5000:
                        connection.executemany("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", pending)
                        pending.clear()
                trace.clear()
                root.clear()
        if pending:
            connection.executemany("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", pending)
        if not application_count or not event_count:
            raise ValueError("The source contains no applications or events.")
        invalid = connection.execute("""
            SELECT COUNT(*) FROM (
                SELECT offer_id FROM events WHERE offer_id IS NOT NULL
                GROUP BY offer_id HAVING COUNT(DISTINCT application_id) > 1
            )
        """).fetchone()[0]
        if invalid:
            raise ValueError("An offer ID belongs to more than one application.")
        connection.execute("CREATE INDEX event_case_time_idx ON events(application_id, occurred_at, event_row)")
        connection.execute("CREATE INDEX event_offer_idx ON events(offer_id)")
        info = {
            "schema_version": "1", "source_sha256": checksum,
            "applications": str(application_count), "events": str(event_count),
            "first_event_at": first_at, "last_event_at": last_at,
        }
        connection.executemany("INSERT INTO metadata VALUES (?, ?)", info.items())
        connection.commit()
        connection.close()
        temporary.replace(target)
        return info
    finally:
        connection.close()
        temporary.unlink(missing_ok=True)
