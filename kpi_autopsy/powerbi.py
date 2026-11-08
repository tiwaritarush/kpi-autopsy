import csv
import json
import uuid
from pathlib import Path

from .export import write_csv, write_json

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/"
REPORT_SCHEMA = SCHEMA + "item/report/definition/"

TABLES = {
    "Cases": ("cases.csv", {
        "requested_amount": "double", "offer_count": "int64", "accepted_offer": "int64",
        "first_offer_hours": "double", "is_open": "int64", "age_days": "double", "in_cohort": "int64",
    }),
    "Audits": ("audit_reports.csv", {
        "reported_value": "double", "reference_value": "double", "difference": "double",
        "affected_applications": "int64",
    }),
    "Evidence": ("case_evidence.csv", {
        "reported_rows": "int64", "reference_rows": "int64", "reported_numerator": "double",
        "reference_numerator": "double", "reported_denominator": "double",
        "reference_denominator": "double", "offer_count": "int64",
    }),
    "Events": ("events.csv", {"event_row": "int64"}),
    "Evaluation": ("benchmark.csv", {
        "has_fault": "int64", "exercised": "int64", "passed": "int64",
        "affected_applications": "int64", "query_ms": "double",
    }),
    "Context": ("context.csv", {}),
}

MEASURES = {
    "Cases": [
        ("Applications", "CALCULATE(COUNTROWS(Cases), Cases[in_cohort] = 1)", "#,0"),
        ("Accepted applications", "CALCULATE(SUM(Cases[accepted_offer]), Cases[in_cohort] = 1)", "#,0"),
        ("Accepted-offer share", "DIVIDE([Accepted applications], [Applications])", "0.00%"),
        ("Mean first-offer hours", "CALCULATE(AVERAGE(Cases[first_offer_hours]), Cases[in_cohort] = 1)", "0.00"),
        ("Open applications", "CALCULATE(SUM(Cases[is_open]), Cases[in_cohort] = 1)", "#,0"),
    ],
    "Evaluation": [
        ("Evaluation scenarios", "COUNTROWS(Evaluation)", "#,0"),
        ("Exercised faults", "CALCULATE(COUNTROWS(Evaluation), Evaluation[has_fault] = 1, Evaluation[exercised] = 1)", "#,0"),
        ("Detected faults", 'CALCULATE(COUNTROWS(Evaluation), Evaluation[has_fault] = 1, Evaluation[exercised] = 1, Evaluation[detected_issues] <> "NONE")', "#,0"),
        ("False alarms", 'COALESCE(CALCULATE(COUNTROWS(Evaluation), Evaluation[has_fault] = 0, Evaluation[detected_issues] <> "NONE"), 0)', "#,0"),
        ("Detection recall", "DIVIDE([Detected faults], [Exercised faults])", "0.0%"),
        ("Detection precision", "DIVIDE([Detected faults], [Detected faults] + [False alarms])", "0.0%"),
    ],
}


def expression(value) -> dict:
    if isinstance(value, bool):
        literal = str(value).lower()
    elif isinstance(value, (int, float)):
        literal = f"{value}D"
    else:
        literal = "'" + value.replace("'", "''") + "'"
    return {"expr": {"Literal": {"Value": literal}}}


def color(value: str) -> dict:
    return {"solid": {"color": expression(value)}}


def field(table: str, name: str, *, measure: bool = False) -> dict:
    kind = "Measure" if measure else "Column"
    return {
        "field": {kind: {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}},
        "queryRef": f"{table}.{name}", "displayName": name.replace("_", " ").capitalize(),
    }


def visual(name: str, kind: str, title: str, position: tuple, roles: dict) -> dict:
    x, y, width, height = position
    return {
        "$schema": REPORT_SCHEMA + "visualContainer/1.0.0/schema.json",
        "name": name, "position": {"x": x, "y": y, "z": 0, "width": width, "height": height, "tabOrder": y + x / 10000},
        "visual": {
            "visualType": kind,
            "query": {"queryState": {role: {"projections": fields} for role, fields in roles.items()}},
            "visualContainerObjects": {
                "title": [{"properties": {"show": expression(True), "text": expression(title),
                                           "fontSize": expression(12), "fontColor": color("#193750")}}],
                "background": [{"properties": {"show": expression(True), "color": color("#FFFFFF"), "transparency": expression(0)}}],
                "general": [{"properties": {"altText": expression(title)}}],
            },
        },
    }


def textbox(name: str, title: str, subtitle: str, y: int = 16) -> dict:
    result = visual(name, "textbox", title, (24, y, 1232, 76), {})
    result["visual"].pop("query")
    result["visual"].pop("visualContainerObjects")
    result["visual"]["objects"] = {"general": [{"properties": {"paragraphs": [
        {"textRuns": [{"value": title, "textStyle": {"fontSize": "22pt", "fontFace": "Segoe UI Semibold", "color": "#193750"}}]},
        {"textRuns": [{"value": subtitle, "textStyle": {"fontSize": "10pt", "fontFace": "Segoe UI", "color": "#526575"}}]},
    ]}}]}
    return result


def model_table(name: str, filename: str, types: dict, folder: Path) -> dict:
    with (folder / filename).open(newline="", encoding="utf-8") as stream:
        headers = next(csv.reader(stream))
    type_map = {"string": "type text", "int64": "Int64.Type", "double": "type number"}
    conversions = ", ".join('{"' + header + '", ' + type_map[types.get(header, "string")] + '}' for header in headers)
    query = [
        "let",
        f'    Source = Csv.Document(File.Contents(DataFolder & "/{filename}"), [Delimiter=",", Columns={len(headers)}, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
        "    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),",
        '    EmptyToNull = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),',
        f'    Typed = Table.TransformColumnTypes(EmptyToNull, {{{conversions}}}, "en-US")',
        "in Typed",
    ]
    return {
        "name": name,
        "columns": [{"name": header, "dataType": types.get(header, "string"), "sourceColumn": header,
                     "summarizeBy": "none"} for header in headers],
        "measures": [{"name": title, "expression": dax, "formatString": fmt}
                     for title, dax, fmt in MEASURES.get(name, [])],
        "partitions": [{"name": name, "mode": "import", "source": {"type": "m", "expression": query}}],
    }


def generate(data_folder: Path, output: Path) -> Path:
    data_folder = data_folder.resolve()
    if not (data_folder / "benchmark.csv").exists():
        write_csv(data_folder / "benchmark.csv", [], [
            "month", "scenario", "variant", "expected_issue", "detected_issues", "has_fault",
            "exercised", "passed", "affected_applications", "query_ms",
        ])
    context = json.loads((data_folder / "context.json").read_text(encoding="utf-8"))
    report = output / "KPI_Autopsy.Report"
    semantic_model = output / "KPI_Autopsy.SemanticModel"
    tables = [model_table(name, filename, types, data_folder) for name, (filename, types) in TABLES.items()]
    relationships = []
    for many, column, one, key, both in [
        ("Evidence", "application_id", "Cases", "application_id", True),
        ("Evidence", "report_id", "Audits", "report_id", False),
        ("Events", "application_id", "Cases", "application_id", False),
    ]:
        relationships.append({
            "name": str(uuid.uuid5(uuid.NAMESPACE_URL, f"kpi-autopsy/{many}/{column}/{one}/{key}")),
            "fromTable": many, "fromColumn": column, "toTable": one, "toColumn": key,
            "crossFilteringBehavior": "bothDirections" if both else "oneDirection",
        })
    folder_expression = '"' + data_folder.as_posix().replace('"', '""') + '" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'
    write_json(semantic_model / "model.bim", {
        "name": "KPI_Autopsy", "compatibilityLevel": 1600,
        "model": {"culture": "en-US", "defaultPowerBIDataSourceVersion": "powerBI_V3",
                  "tables": tables, "relationships": relationships,
                  "expressions": [{"name": "DataFolder", "kind": "m", "expression": folder_expression}]},
    })
    write_json(semantic_model / "definition.pbism", {
        "$schema": SCHEMA + "item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "1.0", "settings": {"qnaEnabled": False},
    })
    write_json(report / "definition.pbir", {
        "$schema": SCHEMA + "item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0", "datasetReference": {"byPath": {"path": "../KPI_Autopsy.SemanticModel"}},
    })
    definition = report / "definition"
    write_json(definition / "version.json", {"$schema": REPORT_SCHEMA + "versionMetadata/1.0.0/schema.json", "version": "1.0.0"})
    write_json(definition / "report.json", {
        "$schema": REPORT_SCHEMA + "report/1.0.0/schema.json", "layoutOptimization": "None",
        "themeCollection": {"baseTheme": {"name": "CY24SU06", "reportVersionAtImport": "5.55", "type": "SharedResources"}},
    })

    def card(name, title, table, measure, x):
        return visual(name, "card", title, (x, 108, 400, 112), {"Values": [field(table, measure, measure=True)]})

    def table(name, title, table_name, columns, position):
        return visual(name, "tableEx", title, position, {"Values": [field(table_name, column) for column in columns]})

    subtitle = f"Intake {context['start'][:10]} to {context['end'][:10]} (end exclusive) | Observed through {context['as_of']} | UTC"
    pages = {
        "overview": ("01 Overview", [
            textbox("heading", "KPI Autopsy | Banking metrics", subtitle),
            card("acceptance", "Applications with an accepted offer", "Cases", "Accepted-offer share", 24),
            card("delay", "Mean time to first offer (calendar hours)", "Cases", "Mean first-offer hours", 440),
            card("backlog", "Open applications under the declared state rule", "Cases", "Open applications", 856),
            visual("monthly_share", "lineChart", "Accepted-offer share by intake month", (24, 244, 744, 412),
                   {"Category": [field("Cases", "created_month")], "Y": [field("Cases", "Accepted-offer share", measure=True)]}),
            visual("cohorts", "tableEx", "Compare loan purposes", (792, 244, 464, 412), {"Values": [
                field("Cases", "loan_goal"), field("Cases", "Applications", measure=True),
                field("Cases", "Accepted-offer share", measure=True), field("Cases", "Mean first-offer hours", measure=True)]}),
            textbox("note", "Definitions matter", "Accepted offer is an observed event outcome. Turnaround covers offered applications; backlog follows a declared event-state rule.", 668),
        ]),
        "audits": ("02 Investigate", [
            textbox("heading", "Investigate a misleading report", "Fixed export cohort. Select a report row to filter its evidence; the reference SQL is saved beside the audit JSON."),
            table("reports", "Reported and reconciled values — read the unit column", "Audits",
                  ["title", "status", "reported_value", "reference_value", "difference", "unit", "affected_applications"], (24, 108, 1232, 220)),
            table("evidence", "Affected applications and their contributions", "Evidence",
                  ["report_id", "application_id", "reason", "reported_rows", "reference_rows", "reported_numerator", "reference_numerator", "offer_count"], (24, 352, 1232, 304)),
            textbox("note", "Evidence before explanation", "The auditor compares records with a supplied metric contract. Candidate explanations do not establish stakeholder intent or a unique root cause.", 668),
        ]),
        "events": ("03 Source records", [
            textbox("heading", "Follow an application to its source events", "Select an application, then inspect its timestamps, lifecycle and offer IDs. Events are bounded by the export cutoff."),
            visual("application", "slicer", "Application ID", (24, 108, 360, 548), {"Values": [field("Cases", "application_id")]}),
            table("events", "Source event history", "Events",
                  ["application_id", "occurred_at", "activity", "lifecycle", "offer_id", "source_event_id"], (408, 108, 848, 548)),
            textbox("note", "A row can be traced", "event_row is the stable position in the pinned XES file; source_event_id and the original timezone-bearing timestamp are retained in the export.", 668),
        ]),
        "evaluation": ("04 Evaluation", [
            textbox("heading", "Evaluate the documented fault families", "Separate September–December cohorts; original and equivalent wrapped SQL; clean controls included. No model is trained."),
            card("scenarios", "Evaluation scenarios", "Evaluation", "Evaluation scenarios", 24),
            card("recall", "Detection recall on exercised known faults", "Evaluation", "Detection recall", 440),
            card("alarms", "False alarms on clean reports", "Evaluation", "False alarms", 856),
            table("results", "Every evaluation case remains inspectable", "Evaluation",
                  ["month", "scenario", "variant", "expected_issue", "detected_issues", "exercised", "passed", "query_ms"], (24, 244, 1232, 412)),
            textbox("note", "Read the scope with the score", "Unexercised faults remain visible. Scores cover known error families and separate cohorts, not arbitrary SQL or unseen business rules.", 668),
        ]),
    }
    for name, (title, visuals) in pages.items():
        page_dir = definition / "pages" / name
        write_json(page_dir / "page.json", {
            "$schema": REPORT_SCHEMA + "page/1.0.0/schema.json", "name": name,
            "displayName": title, "displayOption": "FitToPage", "width": 1280, "height": 760,
            "objects": {"background": [{"properties": {"color": color("#F4F7FA"), "transparency": expression(0)}}]},
        })
        for item in visuals:
            write_json(page_dir / "visuals" / item["name"] / "visual.json", item)
    write_json(definition / "pages" / "pages.json", {
        "$schema": REPORT_SCHEMA + "pagesMetadata/1.0.0/schema.json",
        "pageOrder": list(pages), "activePageName": "overview",
    })
    project = output / "KPI_Autopsy.pbip"
    write_json(project, {"$schema": SCHEMA + "pbip/pbipProperties/1.0.0/schema.json",
                         "version": "1.0", "artifacts": [{"report": {"path": "KPI_Autopsy.Report"}}],
                         "settings": {"enableAutoRecovery": True}})
    return project.resolve()
