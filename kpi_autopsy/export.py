import csv
import json
import sqlite3
from pathlib import Path

from .audit import Audit, audit_query
from .database import metadata, sql
from .metrics import Cohort, calculate
from .scenarios import SCENARIOS


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def save_audit(audit: Audit, folder: Path) -> None:
    write_json(folder / "audit.json", audit.summary())
    write_csv(folder / "evidence.csv", audit.evidence, [
        "application_id", "reason", "reported_rows", "reference_rows", "reported_numerator",
        "reference_numerator", "reported_denominator", "reference_denominator", "created_at",
        "first_offer_at", "accepted_offer_at", "offer_count",
    ])
    (folder / "submitted.sql").write_text(audit.submitted_sql, encoding="utf-8")
    (folder / "reference.sql").write_text(audit.reference_sql, encoding="utf-8")


def export_reports(connection: sqlite3.Connection, cohort: Cohort, folder: Path) -> dict:
    cases = [dict(row) for row in connection.execute("""
        SELECT *, CASE WHEN created_at >= :start AND created_at < :end THEN 1 ELSE 0 END AS in_cohort
        FROM case_snapshot ORDER BY application_id
    """, cohort.parameters())]
    cohort_size = sum(row["in_cohort"] for row in cases)
    if not cohort_size:
        raise ValueError("The requested cohort has no applications. Choose another cohort before exporting.")
    values = calculate(connection, cohort)
    write_json(folder / "metrics.json", {"cohort": cohort.parameters(), "metrics": values})
    write_json(folder / "source.json", metadata(connection))
    write_csv(folder / "powerbi" / "metrics.csv", values)
    write_csv(folder / "powerbi" / "cases.csv", cases)
    reports, evidence, sample_ids = [], [], set()
    for scenario_id, scenario in SCENARIOS.items():
        result = audit_query(connection, scenario.metric_id, sql(scenario.query_file), cohort)
        save_audit(result, folder / "audits" / scenario_id)
        observed, reference = result.reported["value"], result.reference["value"]
        reports.append({
            "report_id": scenario_id, "title": scenario.title, "metric_id": scenario.metric_id,
            "status": result.status, "reported_value": observed, "reference_value": reference,
            "difference": observed - reference if observed is not None and reference is not None else None,
            "unit": result.reported["unit"], "affected_applications": len(result.evidence),
            "issue_codes": "; ".join(issue["code"] for issue in result.issues) or "NONE",
            "explanation": " ".join(issue["message"] for issue in result.issues) or "All contributions match the contract.",
        })
        evidence.extend({"report_id": scenario_id, **row} for row in result.evidence)
        sample_ids.update(row["application_id"] for row in result.evidence[:5])
    write_csv(folder / "powerbi" / "audit_reports.csv", reports)
    write_csv(folder / "powerbi" / "case_evidence.csv", evidence, [
        "report_id", "application_id", "reason", "reported_rows", "reference_rows",
        "reported_numerator", "reference_numerator", "reported_denominator", "reference_denominator",
        "created_at", "first_offer_at", "accepted_offer_at", "offer_count",
    ])
    traces = []
    for identity in sorted(sample_ids):
        traces.extend(dict(row) for row in connection.execute("""
            SELECT application_id, event_row, activity, event_origin, lifecycle, occurred_at,
                   source_timestamp, offer_id, source_event_id
            FROM events WHERE application_id = ? AND occurred_at <= ?
            ORDER BY occurred_at, event_row
        """, (identity, cohort.as_of)))
    write_csv(folder / "powerbi" / "sample_events.csv", traces, [
        "application_id", "event_row", "activity", "event_origin", "lifecycle", "occurred_at",
        "source_timestamp", "offer_id", "source_event_id",
    ])
    event_fields = ["application_id", "event_row", "activity", "event_origin", "lifecycle",
                    "occurred_at", "source_timestamp", "offer_id", "source_event_id"]
    event_count = 0
    with (folder / "powerbi" / "events.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(event_fields)
        for row in connection.execute("""
            SELECT e.application_id, e.event_row, e.activity, e.event_origin, e.lifecycle,
                   e.occurred_at, e.source_timestamp, e.offer_id, e.source_event_id
            FROM events e JOIN case_snapshot c ON c.application_id = e.application_id
            WHERE e.occurred_at <= :as_of
            ORDER BY e.application_id, e.occurred_at, e.event_row
        """, cohort.parameters()):
            writer.writerow(tuple(row))
            event_count += 1
    context = {
        **cohort.parameters(), "source_sha256": metadata(connection)["source_sha256"],
        "timezone": "UTC", "sample_event_scope": "Up to five affected applications per audit; use trace for any other application.",
    }
    write_json(folder / "powerbi" / "context.json", context)
    write_csv(folder / "powerbi" / "context.csv", [context])
    return {"applications": cohort_size, "snapshot_applications": len(cases),
            "reports": len(reports), "evidence_rows": len(evidence),
            "sample_event_rows": len(traces), "event_rows": event_count, "folder": str(folder.resolve())}
