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

## Remaining verification

- Open and refresh the generated project in Power BI Desktop, then inspect all four pages. Desktop was unavailable here; native M/DAX execution and visual rendering are unverified.

The evaluation demonstrates the four documented fault families. It is not evidence of general accuracy on arbitrary SQL, unknown error families or unapproved business definitions.
