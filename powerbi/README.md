# Power BI report

Open `report/KPI_Autopsy.pbip` in the current Power BI Desktop and select **Refresh**. Choose **Anonymous** if asked for access to `raw.githubusercontent.com`. No Python setup or local data path is needed for this copy.

The data URL is pinned to a Git commit. Refreshing loads the same six compressed CSV exports, including all 1,202,267 source events. The [data folder](data/) includes row counts, checksums and the original dataset attribution.

## Four pages

1. **Overview:** the three reference KPIs, monthly acceptance and loan-purpose comparisons.
2. **Investigate:** select a report row to see which applications changed its result. Percentage-rate gaps are percentage points.
3. **Source records:** find an application ID in the slicer and follow its events in timestamp order. `event_row` breaks timestamp ties and traces back to the source file.
4. **Evaluation:** all 56 cases, including clean controls. The result covers four known fault families, not arbitrary SQL.

For a quick walkthrough, compare **Accepted at the wrong stage** with the reference. The reported 100% becomes 54.68% when acceptance means an observed `O_Accepted` event. Pick an affected application ID and look it up on page 3.

With no selections, the Overview should show **54.68%**, **37.39 calendar hours** and **98 open applications**. Its cohort is the 2016 intake, observed through 1 February 2017. These are prototype definitions, not the source bank's approved operating metrics.

## Build your own copy

`python -m kpi_autopsy build` creates `generated/KPI_Autopsy.pbip`, using your local CSV exports. Rebuild after moving the repository. Save a separate copy before customizing it: the generator overwrites its output.

The model follows `Audits → Evidence ↔ Cases → Events`. One bidirectional relationship connects evidence to applications; there is no second filter path. Overview measures always apply `in_cohort = 1`. Selecting a visual does not rerun the Python audit.

See the [validation record](../docs/VALIDATION.md) for the checks performed and their limits.
