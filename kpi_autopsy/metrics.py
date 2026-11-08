import math
import sqlite3
import time
from dataclasses import dataclass
from datetime import date

from .database import sql, utc_timestamp


@dataclass(frozen=True)
class Cohort:
    start: str
    end: str
    as_of: str

    @classmethod
    def create(cls, start: str, end: str, as_of: str) -> "Cohort":
        first, last = date.fromisoformat(start), date.fromisoformat(end)
        if first.isoformat() != start or last.isoformat() != end:
            raise ValueError("Cohort dates must use YYYY-MM-DD.")
        if first >= last:
            raise ValueError("The cohort start must be earlier than its exclusive end.")
        start_at = utc_timestamp(start + "T00:00:00Z")
        end_at = utc_timestamp(end + "T00:00:00Z")
        cutoff = utc_timestamp(as_of)
        if end_at > cutoff:
            raise ValueError("The cohort must end on or before the as-of timestamp.")
        return cls(start_at, end_at, cutoff)

    def parameters(self) -> dict[str, str]:
        return {"start": self.start, "end": self.end, "as_of": self.as_of}


@dataclass(frozen=True)
class Metric:
    id: str
    title: str
    aggregation: str
    unit: str
    definition: str
    query_file: str


METRICS = {
    "accepted_offer_rate": Metric(
        "accepted_offer_rate", "Applications with an accepted offer", "percentage", "percent",
        "Share of intake-cohort applications with an observed O_Accepted event by the cutoff. "
        "This is an observed offer outcome, not a funded-loan rate.",
        "accepted_offer_rate.sql",
    ),
    "first_offer_hours": Metric(
        "first_offer_hours", "Mean time to first offer", "mean", "hours",
        "Elapsed calendar hours from A_Create Application to the first O_Create Offer, "
        "among cohort applications that had an offer by the cutoff. Not-yet-offered cases are excluded and reported separately.",
        "first_offer_hours.sql",
    ),
    "open_backlog": Metric(
        "open_backlog", "Open applications at cutoff", "sum", "applications",
        "Intake-cohort applications with no O_Accepted event whose latest application event is neither "
        "A_Pending, A_Denied nor A_Cancelled. This is a declared event-state rule, not a bank-verified status definition.",
        "open_backlog.sql",
    ),
}


@dataclass(frozen=True)
class Contribution:
    application_id: str
    numerator: float
    denominator: float


@dataclass
class QueryResult:
    rows: list[Contribution]
    elapsed_ms: float


class QueryError(ValueError):
    pass


def run_query(connection: sqlite3.Connection, query: str, cohort: Cohort) -> QueryResult:
    if connection.execute("SELECT as_of FROM snapshot_info").fetchone()[0] != cohort.as_of:
        raise QueryError("The cohort cutoff does not match the prepared snapshot.")
    allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}

    def authorize(action, first, second, database, trigger):
        if action == sqlite3.SQLITE_FUNCTION and second == "load_extension":
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY

    started = time.perf_counter()
    deadline = started + 15
    connection.set_authorizer(authorize)
    connection.set_progress_handler(lambda: int(time.perf_counter() > deadline), 1000)
    try:
        cursor = connection.execute(query, cohort.parameters())
        columns = [field[0] for field in cursor.description or ()]
        if len(columns) != 3 or set(columns) != {"application_id", "numerator", "denominator"}:
            raise QueryError("A report query must return application_id, numerator, and denominator.")
        rows = []
        for row in cursor:
            if len(rows) >= 250_000:
                raise QueryError("The query returned more than 250,000 contributions. Check its grain.")
            identity = row["application_id"]
            if not isinstance(identity, str) or not identity.strip():
                raise QueryError("Every contribution needs a nonempty application ID.")
            try:
                numerator, denominator = float(row["numerator"]), float(row["denominator"])
            except (TypeError, ValueError) as error:
                raise QueryError("Contribution values must be numeric, not NULL.") from error
            if not math.isfinite(numerator) or not math.isfinite(denominator) or denominator < 0:
                raise QueryError("Contribution values must be finite and denominators cannot be negative.")
            rows.append(Contribution(identity, numerator, denominator))
        return QueryResult(rows, (time.perf_counter() - started) * 1000)
    except sqlite3.Error as error:
        raise QueryError(f"Report query failed: {error}") from error
    finally:
        connection.set_progress_handler(None, 0)
        connection.set_authorizer(None)


def aggregate(metric: Metric, rows: list[Contribution]) -> dict:
    try:
        numerator = math.fsum(row.numerator for row in rows)
        denominator = math.fsum(row.denominator for row in rows)
    except OverflowError as error:
        raise QueryError("The aggregated contributions exceed the numeric range.") from error
    if metric.aggregation == "sum":
        value = numerator
    else:
        value = numerator / denominator if denominator else None
        if value is not None and metric.aggregation == "percentage":
            value *= 100
    if value is not None and not math.isfinite(value):
        raise QueryError("The aggregated metric is not finite.")
    return {
        "metric_id": metric.id, "title": metric.title, "value": value, "unit": metric.unit,
        "numerator": numerator, "denominator": denominator, "contribution_rows": len(rows),
        "unique_applications": len({row.application_id for row in rows}), "definition": metric.definition,
    }


def calculate(connection: sqlite3.Connection, cohort: Cohort) -> list[dict]:
    return [aggregate(metric, run_query(connection, sql(metric.query_file), cohort).rows)
            for metric in METRICS.values()]
