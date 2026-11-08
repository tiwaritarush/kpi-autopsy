# Power BI report

Run the project build, then open `generated/KPI_Autopsy.pbip` in a current Power BI Desktop release and select **Refresh**. If you moved the repository, rebuild first so that the `DataFolder` parameter points to the new exports.

The report is generated as editable PBIP/PBIR files with a JSON semantic model. No account, workspace upload or publishing step is needed for local analysis.

## Pages

1. **Overview:** accepted-offer share, first-offer calendar hours, declared open backlog, monthly intake cohorts and loan-purpose comparisons.
2. **Investigate:** fixed-cohort report comparisons and their per-application evidence. Select a report to filter its evidence.
3. **Source records:** select an application and inspect its observed events, lifecycle and offer IDs.
4. **Evaluation:** scenario coverage, recall, clean-report false alarms and every recorded evaluation case.

The neutral blue and white layout uses 24-pixel page margins, aligned metric cards and consistent table positions. All generated visuals are checked to remain inside the page bounds.

## Model

Cases is one row per snapshot application. Audits is one row per submitted demo report. Evidence can contain the same application in several reports. Events contains the full observed event history. Evaluation contains scenario results, while Context retains the export boundaries and fingerprint.

The model relationships are:

```text
Audits 1 -> many Evidence many <-> 1 Cases 1 -> many Events
```

The single bidirectional relationship lets an evidence selection identify its application. There are no additional relationship paths between these tables. Evaluation and Context are independent.

Cases retains outside-cohort applications when they exist in the snapshot. The overview DAX measures explicitly filter `in_cohort = 1`; outside-cohort evidence remains available for investigating a wrong-population report.

Audit values are calculated for the export's fixed cohort. Overview selections do not rerun the Python audit. The Evidence table keeps report IDs visible when multiple report results are displayed together.

## Validate the file format

The optional validator uses Microsoft's published schemas:

```console
python -m pip install -e ".[validation]"
python tools/validate_powerbi.py
```

The core analysis does not need this dependency. Schema validation checks the report structure; unit tests check field bindings and page bounds. Neither substitutes for opening and refreshing the semantic model in Desktop.

Power BI Desktop was unavailable in the build environment, so native opening, M/DAX execution, refresh and visual inspection remain unverified. If Desktop reports an import issue, keep the generated files and report the exact message rather than editing the verified CSV data.

## Keep a customized report

The generator overwrites its own `generated/` output. Save a copy elsewhere before customizing it in Desktop. Refreshing the CSV source does not require regenerating the report definition, so a customized copy can continue using the exported data folder.
