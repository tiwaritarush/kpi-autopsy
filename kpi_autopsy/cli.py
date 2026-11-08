import argparse
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from xml.etree.ElementTree import ParseError

from .audit import audit_query
from .benchmark import benchmark
from .database import connect, metadata, snapshot, sql, utc_timestamp
from .export import export_reports, save_audit, write_csv, write_json
from .ingest import download, ingest
from .metrics import Cohort, METRICS, calculate
from .scenarios import SCENARIOS


def cohort_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--database", type=Path, default=Path("data/autopsy.sqlite"))
    parser.add_argument("--start", default="2016-01-01", help="Inclusive intake date, in UTC.")
    parser.add_argument("--end", default="2017-01-01", help="Exclusive intake date, in UTC.")
    parser.add_argument("--as-of", help="Timezone-aware observation cutoff. Defaults to the last source event.")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Reconcile a banking report with its metric definition.")
    commands = root.add_subparsers(dest="command", required=True)
    fetch = commands.add_parser("fetch", help="Download and checksum the public event log.")
    fetch.add_argument("--source", type=Path, default=Path("data/raw/bpi2017.xes.gz"))
    load = commands.add_parser("ingest", help="Stream the XES log into SQLite.")
    load.add_argument("--source", type=Path, default=Path("data/raw/bpi2017.xes.gz"))
    load.add_argument("--database", type=Path, default=Path("data/autopsy.sqlite"))
    load.add_argument("--force", action="store_true")
    metrics = commands.add_parser("metrics", help="Calculate the three reference metrics.")
    cohort_options(metrics)
    metrics.add_argument("--json", action="store_true")
    audit = commands.add_parser("audit", help="Audit a SQL file through the contribution interface.")
    cohort_options(audit)
    audit.add_argument("--metric", choices=METRICS, required=True)
    audit.add_argument("--query", type=Path, required=True)
    audit.add_argument("--output", type=Path, default=Path("reports/custom-audit"))
    demo = commands.add_parser("demo", help="Run one documented fault or clean control.")
    cohort_options(demo)
    demo.add_argument("scenario", choices=SCENARIOS)
    demo.add_argument("--output", type=Path, default=Path("reports/demo"))
    evaluate = commands.add_parser("benchmark", help="Evaluate fixed fault families on monthly cohorts.")
    cohort_options(evaluate)
    evaluate.add_argument("--months", default="9,10,11,12", help="2016 months, separated by commas.")
    evaluate.add_argument("--output", type=Path, default=Path("reports"))
    export = commands.add_parser("export", help="Export reference metrics, audits, and Power BI tables.")
    cohort_options(export)
    export.add_argument("--output", type=Path, default=Path("reports"))
    build = commands.add_parser("build", help="Run ingestion, analysis, evaluation, and report generation.")
    cohort_options(build)
    build.add_argument("--source", type=Path, default=Path("data/raw/bpi2017.xes.gz"))
    build.add_argument("--output", type=Path, default=Path("reports"))
    build.add_argument("--force", action="store_true")
    build.add_argument("--skip-benchmark", action="store_true")
    trace = commands.add_parser("trace", help="Show the original events for one application.")
    trace.add_argument("application_id")
    trace.add_argument("--database", type=Path, default=Path("data/autopsy.sqlite"))
    trace.add_argument("--as-of")
    return root


def display_audit(result) -> None:
    print(f"{result.status.upper()}: {result.reference['title']}")
    print(f"Reported: {result.reported['value']} {result.reported['unit']}")
    print(f"Reference: {result.reference['value']} {result.reference['unit']}")
    print(f"Affected applications: {len(result.evidence):,}")
    for issue in result.issues:
        print(f"  {issue['code']}: {issue['message']}")
    for row in result.evidence[:3]:
        print(f"  {row['application_id']}: {row['reason']}")


def write_benchmark(connection, cutoff: str, months: list[int], output: Path) -> dict:
    if not months or any(month < 1 or month > 12 for month in months) or len(set(months)) != len(months):
        raise ValueError("Choose distinct month numbers between 1 and 12.")
    result = benchmark(connection, cutoff, months)
    write_json(output / "benchmark.json", result)
    write_csv(output / "powerbi" / "benchmark.csv", result["results"])
    print(f"Evaluation: {result['exercised_cases']}/{result['cases']} scenarios exercised; "
          f"{result['false_positives']} false positives, {result['false_negatives']} false negatives.")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "fetch":
            print(download(args.source))
            return 0
        if args.command == "ingest":
            print(json.dumps(ingest(args.source, args.database, force=args.force), indent=2))
            return 0
        if args.command == "build":
            print("1/4  Checking the source and building the database...", flush=True)
            if not args.source.exists():
                download(args.source)
            print(json.dumps(ingest(args.source, args.database, force=args.force), indent=2), flush=True)
        if not args.database.is_file():
            raise FileNotFoundError("Database not found. Run python -m kpi_autopsy build first.")
        with closing(connect(args.database)) as connection:
            if args.command == "trace":
                cutoff = utc_timestamp(args.as_of or metadata(connection)["last_event_at"])
                rows = [dict(row) for row in connection.execute("""
                    SELECT event_row, source_event_id, activity, event_origin, lifecycle,
                           occurred_at, source_timestamp, offer_id
                    FROM events WHERE application_id = ? AND occurred_at <= ?
                    ORDER BY occurred_at, event_row
                """, (args.application_id, cutoff))]
                if not rows:
                    raise ValueError("No events match that application and cutoff.")
                print(json.dumps(rows, indent=2))
                return 0
            cutoff = snapshot(connection, args.as_of)
            cohort = Cohort.create(args.start, args.end, cutoff)
            if args.command == "metrics":
                result = calculate(connection, cohort)
                if args.json:
                    print(json.dumps({"cohort": cohort.parameters(), "metrics": result}, indent=2))
                else:
                    for row in result:
                        value = "not available" if row["value"] is None else f"{row['value']:,.4f}"
                        print(f"{row['title']}: {value} {row['unit']} (n={row['denominator']:,.0f})")
                return 0
            if args.command in {"audit", "demo"}:
                if args.command == "demo":
                    scenario = SCENARIOS[args.scenario]
                    metric_id, query = scenario.metric_id, sql(scenario.query_file)
                else:
                    metric_id, query = args.metric, args.query.read_text(encoding="utf-8")
                result = audit_query(connection, metric_id, query, cohort)
                save_audit(result, args.output)
                write_json(args.output / "source.json", metadata(connection))
                display_audit(result)
                return int(bool(result.issues))
            if args.command == "benchmark":
                write_benchmark(connection, cutoff, [int(item) for item in args.months.split(",")], args.output)
                return 0
            if args.command == "build":
                print("2/4  Calculating metrics and reconciling the report scenarios...", flush=True)
            print(json.dumps(export_reports(connection, cohort, args.output), indent=2), flush=True)
            if args.command == "build" and not args.skip_benchmark:
                print("3/4  Evaluating September-December cohorts...", flush=True)
                write_benchmark(connection, cutoff, [9, 10, 11, 12], args.output)
            if args.command == "build":
                print("4/4  Writing the Power BI project...", flush=True)
            from .powerbi import generate
            report = generate(args.output / "powerbi", Path("powerbi/generated"))
            print(f"Power BI project: {report}")
            return 0
    except (OSError, ValueError, KeyError, ParseError, sqlite3.Error) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
