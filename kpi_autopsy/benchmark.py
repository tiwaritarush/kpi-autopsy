import sqlite3
import time
from collections import Counter

from .audit import audit_query
from .database import sql
from .metrics import Cohort, METRICS, run_query
from .scenarios import SCENARIOS


def wrapped(query: str) -> str:
    return "SELECT * FROM (\n" + query.strip().rstrip(";") + "\n) AS report_rows;"


def benchmark(connection: sqlite3.Connection, as_of: str, months: list[int]) -> dict:
    records = []
    started = time.perf_counter()
    for month in months:
        start = f"2016-{month:02d}-01"
        next_year, next_month = (2017, 1) if month == 12 else (2016, month + 1)
        end = f"{next_year}-{next_month:02d}-01"
        cohort = Cohort.create(start, end, as_of)
        for scenario_id, scenario in SCENARIOS.items():
            for variant in ("original", "wrapped"):
                query = sql(scenario.query_file)
                if variant == "wrapped":
                    query = wrapped(query)


                expected_rows = run_query(connection, sql(METRICS[scenario.metric_id].query_file), cohort).rows
                submitted_rows = run_query(connection, query, cohort).rows
                exercised = (scenario.expected_issue is None
                             or Counter(expected_rows) != Counter(submitted_rows))
                audit = audit_query(connection, scenario.metric_id, query, cohort)
                codes = [issue["code"] for issue in audit.issues]
                passed = (not codes if scenario.expected_issue is None
                          else scenario.expected_issue in codes)
                records.append({
                    "month": start[:7], "scenario": scenario_id, "variant": variant,
                    "expected_issue": scenario.expected_issue or "NONE",
                    "detected_issues": "; ".join(codes) or "NONE",
                    "has_fault": int(scenario.expected_issue is not None),
                    "exercised": int(exercised), "passed": int(bool(passed) and exercised),
                    "affected_applications": len(audit.evidence),
                    "query_ms": round(audit.query_ms, 3),
                })
    eligible = [row for row in records if row["exercised"]]
    positives = [row for row in eligible if row["has_fault"]]
    negatives = [row for row in eligible if not row["has_fault"]]
    true_positive = sum(row["detected_issues"] != "NONE" for row in positives)
    false_positive = sum(row["detected_issues"] != "NONE" for row in negatives)
    detected = true_positive + false_positive
    return {
        "protocol": "Four known fault families and three clean reports, each in two SQL forms. "
                    "Monthly cohorts are evaluated independently; no model is trained.",
        "cohorts": [f"2016-{month:02d}" for month in months],
        "cases": len(records), "exercised_cases": len(eligible),
        "unexercised_cases": len(records) - len(eligible),
        "fault_cases": len(positives), "clean_cases": len(negatives),
        "true_positives": true_positive, "false_positives": false_positive,
        "false_negatives": len(positives) - true_positive,
        "detection_precision": true_positive / detected if detected else None,
        "detection_recall": true_positive / len(positives) if positives else None,
        "issue_label_accuracy": sum(row["passed"] for row in positives) / len(positives) if positives else None,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "results": records,
        "limitation": "This measures the documented fault families, not arbitrary SQL errors or unseen business definitions.",
    }
