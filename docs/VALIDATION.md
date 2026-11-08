# Validation record

Checked on 8 November 2026 with Python 3.12 and SQLite 3.53.1.

## Completed

- The full build completed against the pinned public BPI Challenge 2017 file: 31,509 applications, 42,995 offers and 1,202,267 events.
- All 24 automated tests passed, including the real-data regression check. The remaining tests use a small, hand-checkable six-application fixture.
- The evaluation exercised all 56 scenarios: 32 injected-fault cases and 24 clean controls. There were no false positives or false negatives within this documented protocol.
- All 31 generated Power BI files carrying a schema declaration passed Microsoft's public JSON schemas. Tests also checked visual field bindings and page bounds.
- Local code review covered ingestion and resource handling, snapshot timing, metric grain, evidence, independent evaluation truth, query restrictions, exports and report generation.

The local review found that extremely large duplicate contributions could overflow before the normal numeric validation ran. The reconciliation now raises a clear query error instead of leaking an overflow traceback. A regression test exercises that path.

## External review

CodeRabbit completed its review on 8 November 2026. The CLI returned `status: review_completed`, `outcome: completed` and **zero findings** across all 41 source files.

The review used the uncommitted-change scope. Raw data, the SQLite database, generated reports and credentials were excluded. There were no review findings to address, so no code changes or follow-up review were needed. A completed review is another check, not a guarantee that the program has no defects.

The evaluation demonstrates the four documented fault families. It is not evidence of general accuracy on arbitrary SQL, unknown error families or unapproved business definitions.

## Shared report, 9 November 2026

The repository now includes the editable four-page report and all six compressed data tables. Its data URL points to commit `b990a4b725ae512759c3ff2aae9f66eb75ddf735`, rather than a local machine path or a changing branch.

- All 25 tests passed, including the real-data regression and remote-source generation checks.
- All 32 schema-bearing report files passed Microsoft's schemas. Field bindings, page bounds, numeric formats and chronological sorting were also checked.
- The six compressed files decompress exactly to their original CSV exports. Independent checks confirmed the three KPIs, 32 detected faults, 24 clean controls and zero false alarms or misses.
- All six public data downloads returned HTTP 200 and matched the manifest's SHA-256 fingerprints.

A CodeRabbit review was attempted for the generator and packaging changes. The service rejected the Git-provider authentication before analysis; no new external review result was produced. The earlier completed review above covers the earlier source version.

## Native Power BI Desktop check

Checked with Desktop 2.159.1231.0 on 9 November 2026. The full local CSV refresh completed, all four pages rendered, and report-to-evidence and application-to-event filtering worked. Native execution exposed and resolved a reserved DAX table name and missing report-format metadata that schema checks alone had missed.

The final native-saved PBIX was reopened independently. Its six partitions remained ready, all 11 measures compiled, and its saved snapshot contained 31,509 applications and 1,202,267 events. Native measures returned 54.6764416516% accepted-offer share, 37.3886365343 first-offer hours, 98 open applications, 32 detected faults and zero false alarms. The source metadata uses the pinned GitHub gzip exports and contains no local file paths.

The online refresh still needs the user's manual Anonymous access confirmation; it has not been exercised end to end. The delivered PBIX opens with its saved data. The PDF is a static preview of the report's visible tables, rather than a printout of every source row.
