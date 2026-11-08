import math
import sqlite3
from collections import defaultdict
from dataclasses import asdict, dataclass

from .database import metadata, sql
from .metrics import Cohort, Contribution, METRICS, QueryError, aggregate, run_query


@dataclass
class Audit:
    metric_id: str
    source_sha256: str
    cohort: dict
    reported: dict
    reference: dict
    issues: list[dict]
    evidence: list[dict]
    query_ms: float
    submitted_sql: str
    reference_sql: str

    @property
    def status(self) -> str:
        return "mismatch" if self.issues else "reconciled"

    def summary(self) -> dict:
        result = asdict(self)
        result["status"] = self.status
        result.pop("evidence")
        return result


def grouped(rows: list[Contribution]) -> dict[str, list[Contribution]]:
    groups = defaultdict(list)
    for row in rows:
        groups[row.application_id].append(row)
    return dict(groups)


def totals(rows: list[Contribution]) -> tuple[float, float]:
    try:
        return math.fsum(row.numerator for row in rows), math.fsum(row.denominator for row in rows)
    except OverflowError as error:
        raise QueryError("An application's contributions exceed the numeric range.") from error


def same(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=1e-10, abs_tol=1e-7)


def audit_query(connection: sqlite3.Connection, metric_id: str, query: str, cohort: Cohort) -> Audit:
    metric = METRICS[metric_id]
    expected_sql = sql(metric.query_file)
    reference = run_query(connection, expected_sql, cohort)
    measured = run_query(connection, query, cohort)
    expected, observed = grouped(reference.rows), grouped(measured.rows)
    expected_ids, observed_ids = set(expected), set(observed)
    facts = {}
    identities = sorted(expected_ids | observed_ids)
    for offset in range(0, len(identities), 500):
        batch = identities[offset:offset + 500]
        placeholders = ",".join("?" for _ in batch)
        rows = connection.execute(f"SELECT * FROM case_snapshot WHERE application_id IN ({placeholders})", batch)
        facts.update((row["application_id"], dict(row)) for row in rows)
    missing, extra = expected_ids - observed_ids, observed_ids - expected_ids
    duplicates = {key for key, rows in observed.items() if len(rows) > 1}
    different = {
        key for key in expected_ids & observed_ids
        if not all(same(a, b) for a, b in zip(totals(expected[key]), totals(observed[key])))
    }
    issues = []
    if duplicates:
        issues.append({
            "code": "GRAIN_MISMATCH", "cases": len(duplicates),
            "message": f"{len(duplicates):,} applications contribute more than once; the contract requires one row per application.",
        })
    if missing or extra:
        accepted_subset = {key for key in expected_ids if facts[key]["accepted_offer"]}
        is_outcome_filter = (metric_id == "first_offer_hours" and bool(missing)
                             and observed_ids == accepted_subset)
        issues.append({
            "code": "OUTCOME_FILTER" if is_outcome_filter else "COHORT_MISMATCH",
            "cases": len(missing | extra),
            "message": (
                "The measured population matches only applications with an accepted offer; "
                "the contract includes all applications with an observed first offer."
                if is_outcome_filter else
                f"The result omits {len(missing):,} eligible applications and adds {len(extra):,} applications outside the defined population."
            ),
        })
    if different and not duplicates:
        matches_stage = (
            metric_id == "accepted_offer_rate" and not missing and not extra
            and all(same(rows[0].numerator, int(facts[key]["application_stage_at"] is not None))
                    and same(rows[0].denominator, 1) for key, rows in observed.items())
        )
        issues.append({
            "code": "EVENT_DEFINITION_MISMATCH" if matches_stage else "CONTRIBUTION_MISMATCH",
            "cases": len(different),
            "message": (
                "Measured flags match A_Accepted rather than the contract's O_Accepted event. "
                "This is an evidence-supported candidate explanation; inspect the submitted SQL to confirm it."
                if matches_stage else
                f"{len(different):,} applications have different contributions under the declared metric definition."
            ),
        })

    evidence = []
    for key in sorted(missing | extra | duplicates | different):
        expected_total = totals(expected.get(key, []))
        observed_total = totals(observed.get(key, []))
        fact = facts.get(key, {})
        reasons = []
        if key in duplicates:
            reasons.append("duplicate contribution")
        if key in missing:
            reasons.append("missing application")
        if key in extra:
            reasons.append("unexpected application")
        if key in different:
            reasons.append("different contribution")
        evidence.append({
            "application_id": key, "reason": "; ".join(reasons),
            "reported_rows": len(observed.get(key, [])), "reference_rows": len(expected.get(key, [])),
            "reported_numerator": observed_total[0], "reference_numerator": expected_total[0],
            "reported_denominator": observed_total[1], "reference_denominator": expected_total[1],
            "created_at": fact.get("created_at"), "first_offer_at": fact.get("first_offer_at"),
            "accepted_offer_at": fact.get("accepted_offer_at"), "offer_count": fact.get("offer_count"),
        })
    return Audit(metric_id, metadata(connection)["source_sha256"], asdict(cohort), aggregate(metric, measured.rows),
                 aggregate(metric, reference.rows), issues, evidence, measured.elapsed_ms,
                 query, expected_sql)
