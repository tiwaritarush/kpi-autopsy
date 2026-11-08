import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SQL_DIR = Path(__file__).parent / "sql"


def sql(name: str) -> str:
    return (SQL_DIR / name).read_text(encoding="utf-8")


def connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def utc_timestamp(value: str) -> str:
    moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if moment.tzinfo is None:
        raise ValueError("Timestamps must include a timezone, for example 2017-02-01T14:11:00Z.")
    return moment.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def metadata(connection: sqlite3.Connection) -> dict[str, str]:
    return dict(connection.execute("SELECT key, value FROM metadata"))


def snapshot(connection: sqlite3.Connection, as_of: str | None = None) -> str:
    last_event = metadata(connection)["last_event_at"]
    cutoff = utc_timestamp(as_of or last_event)
    if cutoff > last_event:
        raise ValueError(f"The source only covers events through {last_event}.")
    connection.execute("DROP TABLE IF EXISTS temp.snapshot_info")
    connection.execute("CREATE TEMP TABLE snapshot_info (as_of TEXT NOT NULL)")
    connection.execute("INSERT INTO snapshot_info VALUES (?)", (cutoff,))
    connection.execute("DROP TABLE IF EXISTS temp.offer_snapshot")
    connection.execute("DROP TABLE IF EXISTS temp.case_snapshot")
    connection.execute(sql("offer_snapshot.sql"), {"as_of": cutoff})
    connection.execute("CREATE INDEX temp.offer_case_idx ON offer_snapshot(application_id)")
    connection.execute(sql("case_snapshot.sql"), {"as_of": cutoff})
    connection.execute("CREATE UNIQUE INDEX temp.case_id_idx ON case_snapshot(application_id)")
    connection.execute("CREATE INDEX temp.case_created_idx ON case_snapshot(created_at)")
    return cutoff
