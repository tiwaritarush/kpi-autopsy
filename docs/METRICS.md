# Metric definitions and data dictionary

## Reporting boundaries

The cohort contains applications created in `[start, end)`. Both boundaries are midnight UTC. An explicit, timezone-aware `as_of` timestamp controls which events can be observed. The default is the latest event in the pinned source.

The cohort must end by that observation cutoff. A cutoff beyond source coverage is rejected. Timestamps are normalized to fixed-width UTC strings, while their original source representation is preserved.

## Accepted-offer share

- Entity: application.
- Numerator: eligible applications with at least one `O_Accepted` event observed by the cutoff.
- Denominator: all intake-cohort applications.
- Aggregation: `100 * numerator / denominator`.
- Empty population: unavailable, represented as JSON null / a blank report value.

This is an ever-observed accepted-offer event share. It does not establish disbursement, funding, regulatory approval or eventual customer retention. A later cancellation does not erase the earlier observed event under this definition.

`A_Accepted` is a separate event and cannot be substituted merely because its name contains "Accepted".

## Mean time to first offer

- Entity: application with an observed `O_Create Offer` event.
- Value per application: calendar hours from `A_Create Application` to the earliest observed `O_Create Offer`.
- Denominator: eligible applications that have an offer by the cutoff.
- Aggregation: sum of elapsed hours divided by the number of contributing applications.
- Empty population: unavailable, not zero hours.

This conditional mean describes offered applications. It is not the average eventual turnaround of all applications. The Cases export retains `first_offer_at` and blank `first_offer_hours` for not-yet-offered cases, so that excluded population can be counted separately. The full 2016 cohort has a first offer for every application at the final source cutoff.

The measure uses elapsed calendar time. It does not subtract weekends, holidays, idle intervals or time spent waiting for a customer.

## Open backlog

- Entity: application in the intake cohort.
- Open-state rule: no observed `O_Accepted`, and the latest application-origin event is not `A_Pending`, `A_Denied` or `A_Cancelled`.
- Aggregation: sum of the open flags.
- Empty population: zero applications.

This is an explicit event-state interpretation for the prototype, not a definition approved by the source institution. A real stakeholder must approve the terminal-state mapping before using it for operational decisions. Future events are not consulted to resolve an earlier state.

## Permanent tables

| Table | Grain | Important fields |
|---|---|---|
| `applications` | One application | ID, type, loan goal, requested amount |
| `events` | One source event | Stable event row, application ID, source event ID, offer ID, activity, origin, lifecycle, UTC timestamp, original timestamp |
| `metadata` | One metadata key | Schema version, source fingerprint, row counts, event coverage |

An event's source ID is retained without assuming that it is globally unique. The ingestion sequence supplies a separate primary key. The source file's fingerprint identifies which sequence that key belongs to.

## Snapshot and report tables

| Table/file | Purpose |
|---|---|
| `offer_snapshot` | Offer records using only events observed by the cutoff |
| `case_snapshot` | One application row with observed event times and state |
| `cases.csv` | Snapshot cases plus `in_cohort`; outside-cohort cases remain available for investigation |
| `audit_reports.csv` | Reported and reference values, units, diagnosis labels and counts |
| `case_evidence.csv` | Per-application row counts and numerator/denominator differences |
| `events.csv` | Full observed event history for exported snapshot applications |
| `benchmark.csv` | Every evaluation scenario, including clean controls and unexercised faults |

The audit does not express a ratio discrepancy as an additive per-case percentage-point attribution. A changed denominator makes such an attribution require another declared method. Evidence therefore shows the actual numerator and denominator contributions.

## Query interface

A submitted SQL query returns exactly:

```text
application_id  nonempty text identifying the contributing application
numerator       finite number
denominator     finite, nonnegative number
```

The reference query defines the intended population and contributions. Duplicate application rows violate the current contracts. Unknown applications and changed populations remain evidence rather than being silently dropped.

## Diagnosis scope

- `GRAIN_MISMATCH`: duplicate contributions at application grain.
- `COHORT_MISMATCH`: missing or unexpected applications.
- `OUTCOME_FILTER`: the first-offer population matches the accepted-only subset.
- `EVENT_DEFINITION_MISMATCH`: acceptance flags agree with the known earlier-stage alternative and differ from the contract.
- `CONTRIBUTION_MISMATCH`: other value differences within the contribution interface.

Several faults can produce the same observations. The evidence establishes a contract mismatch; a candidate explanation still needs inspection of the submitted SQL and business requirements.
