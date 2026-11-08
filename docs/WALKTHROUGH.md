# Understand the project step by step

## 1. Start with the business question

The first metric is the share of intake-cohort applications that have an observed accepted offer by a specified cutoff. Before writing SQL, settle four things:

- An application is the entity being counted.
- Membership depends on application creation time.
- `O_Accepted` is the event used for this declared outcome.
- The denominator includes every eligible application, including applications that never reached that outcome.

These are requirements, not facts a query engine can discover automatically. The other two definitions are in [METRICS.md](METRICS.md).

## 2. Inspect the source model

The XES file contains application traces and their events. An application may have several offers, and an offer may have several lifecycle events. These levels are different.

`ingest.py` reads one application trace at a time and inserts events in batches. It keeps the source event ID, the original timestamp and a stable event-row position. The compressed source SHA-256 goes into the database metadata.

The database has two permanent data tables:

```text
applications: one row per application
events:       one row per source event
```

An atomic rebuild writes a temporary database first. If parsing fails, the previous database remains available.

## 3. Build a point-in-time snapshot

`offer_snapshot.sql` groups observed offer records. `case_snapshot.sql` computes one row per application, including first offer, accepted-offer event, offer count and latest application event.

The cutoff applies to source events before their timestamps are aggregated. An acceptance recorded after the cutoff cannot appear in an earlier snapshot. This is tested explicitly with application E in the small fixture.

The latest application state uses `ROW_NUMBER()` ordered by event time and then source-row position. The second key makes equal-timestamp ordering reproducible.

## 4. Read the contribution query

Open `kpi_autopsy/sql/accepted_offer_rate.sql`:

```sql
SELECT application_id, accepted_offer AS numerator, 1 AS denominator
FROM case_snapshot
WHERE created_at >= :start AND created_at < :end;
```

Each eligible application contributes once. Its numerator is 1 if the defined event was observed, otherwise 0. Its denominator is 1 either way.

The final rate is `100 * SUM(numerator) / SUM(denominator)`.

The first-offer metric uses elapsed hours as the numerator and one as the denominator. Backlog sums the open-state flag. The same small interface supports all three aggregations.

## 5. Run one faulty report

```console
python -m kpi_autopsy demo wrong-stage
```

The deliberate query uses `A_Accepted` rather than the event in the contract. In the full dataset, that earlier application event appears for every application. The report says 100%; the declared accepted-offer share is 54.6764%.

Open `reports/demo/audit.json`, `evidence.csv`, `submitted.sql` and `reference.sql`. The diagnosis is backed by application-level differences. It does not depend on the filename of the query.

## 6. Follow one application

```console
python -m kpi_autopsy trace Application_1000086665
```

This application contributes 1 to the wrong-stage numerator and 0 to the reference numerator. Compare its application and offer events. The output retains event order, source IDs and both timestamp forms.

Use the application IDs printed by any other audit to repeat the investigation.

## 7. Explain a duplicate join

```console
python -m kpi_autopsy demo offer-join
```

The report joins applications to offers and then counts the resulting rows. Applications with multiple offers contribute more than once. The auditor identifies the duplicate application IDs and compares their summed contributions with the one-row-per-application reference.

The six-application test fixture contains a stronger edge case: duplication and omission happen to leave the headline percentage unchanged. The grain and population checks still report a mismatch. Comparing percentages alone would miss it.

## 8. Separate evaluation truth from the detector

```console
python -m kpi_autopsy benchmark
```

The scenario registry contains the deliberately introduced fault labels. The auditor does not receive those labels.

For each monthly cohort and SQL form, the evaluator independently compares the submitted and reference contribution multisets to establish whether the fault was exercised. It then asks the auditor for its verdict. A unit test replaces the detector with one that always reports no issues; the evaluation correctly records missed faults rather than excluding them.

Clean queries count as negative controls. Equivalent wrapped SQL checks that superficial query formatting does not drive the result.

## 9. Open the Power BI report

Build the project, open `powerbi/generated/KPI_Autopsy.pbip` and refresh. Read the Overview page first, then select a report on Investigate and inspect its evidence. Source records lets you filter an application and review the full observed event history.

The exported Cases table retains applications outside the requested intake cohort because those records may explain a wrong-population report. The `in_cohort` flag controls the overview measures. An unexpected application must remain inspectable without silently entering the reference denominator.

Audit comparisons are fixed to the exported cohort. Interactive overview measures are separate from rerunning the SQL audit; refreshing a slicer does not launch Python.

## 10. Make one change yourself

Read `tests/fixtures.py` before editing an algorithm. The six cases have known outcomes and times. Add a second unaccepted offer to application B, rebuild the snapshot and reason about which metric should remain unchanged.

Then inspect `test_duplicate_offer_does_not_change_application_rate`. This is the project's concrete metamorphic test: a controlled input transformation has an expected relationship to the output.

You should be able to explain each step above before extending the fault catalog or adding more metrics.
