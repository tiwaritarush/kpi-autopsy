# Business brief

## Problem

A metrics team needs to distinguish a change in business performance from a change in measurement. Reports can use different stages, denominators, dates or join grain while producing valid SQL and plausible numbers.

This prototype uses a public loan-application workflow as a financial-operations case study. It is not based on Morgan Stanley data. The example report defects are deliberately introduced.

## Decision supported

Before reacting to a reported acceptance or turnaround change, an analyst can establish the intended definition, reconcile the contributing applications and inspect the evidence behind a discrepancy.

## Recorded findings

Scope: applications created in 2016, observed through `2017-02-01T14:11:03.499000Z`.

| Demonstration | Reported | Reference | Interpretation |
|---|---:|---:|---|
| Wrong accepted stage | 100.0000% | 54.6764% | Different event definitions measure different process stages |
| Offer join | 56.1647% | 54.6764% | Applications with more offers receive more weight |
| Offer-date cohort | 54.7279% | 54.6764% | A small headline difference can hide a changed population |
| Accepted-only first-offer delay | 33.3404 hours | 37.3886 hours | Filtering by outcome changes the population described by the mean |

The reference event-state backlog is 98 applications. These are prototype definitions; the metric owner must approve their business meaning.

The evaluation ran 56 scenarios: 32 injected-fault cases and 24 clean controls. All were exercised, with no false alarms or missed injected faults in that protocol. The protocol covers four known failure families in two SQL forms across separate monthly cohorts.

## Recommended analyst workflow

1. Agree the metric definition with its owner.
2. Export the report's application-level contributions.
3. Reconcile the population, row grain and values.
4. Review the affected IDs, source events and reference query.
5. Confirm a correction with the metric owner and rerun the report.

## User stories and acceptance criteria

### Story 1: consistent acceptance reporting

As a reporting analyst, I need an agreed intake cohort and accepted-offer event definition so that two reports can be reconciled.

- Each eligible application contributes once.
- Applications without the defined outcome remain in the denominator.
- Events after the observation cutoff cannot contribute.
- The evidence identifies the applications responsible for a mismatch.

### Story 2: investigate changed turnaround

As an operations stakeholder, I need to know which population a turnaround mean describes before comparing it with another report.

- The report names its start event, end event and calendar-time unit.
- Not-yet-offered cases remain visible in the case export.
- An accepted-only filter is identified when the contract calls for all offered applications.
- Empty means display as unavailable rather than zero.

### Story 3: repeatable release checks

As a squad member, I need clean controls and documented fault scenarios so that changes to reporting logic can be checked before delivery.

- The evaluator records every cohort, query form and expected issue.
- Detection truth is established independently of the detector's own evidence list.
- Clean controls contribute to the false-alarm calculation.
- A fault with no observable effect is marked unexercised and remains in the results.

## Backlog for a real team

| Priority | Item | Completion evidence |
|---|---|---|
| 1 | Approve metric definitions | Signed-off event, population and cutoff rules |
| 2 | Add one new report source | Reconciled contributions and a clean control |
| 3 | Add a new fault family | Independent expected result and regression fixture |
| 4 | Review Power BI refresh in Desktop | Successful refresh and visual inspection |

Claims about revenue impact, prevented losses or reduced analyst hours require measurement in a real workflow. They are not inferred from this demonstration.
