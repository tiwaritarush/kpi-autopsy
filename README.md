# KPI Autopsy

A SQL/Python project that checks banking reports against defined metrics. It uses the public BPI Challenge 2017 log: 31,509 applications and 1.2 million events.

Each query returns an application ID, numerator and denominator. The audit checks missing applications, duplicate rows and changed contributions.

## Run

Python 3.11 or later. The core uses only the standard library and SQLite.

```sh
python -m kpi_autopsy build
python -m kpi_autopsy demo wrong-stage
python -m unittest discover -s tests -v
```

The first build downloads the source, imports it and generates the reports. Allow space for the database and CSV exports. A deliberate demo mismatch returns exit code 1.

## What it checks

Three metrics: accepted-offer share, time to first offer and open applications. Demo faults cover wrong events, duplicate joins, changed cohorts and outcome filters.

Using `A_Accepted` gives 100% acceptance; the declared `O_Accepted` definition gives 54.68%. Evidence and reference SQL go into `reports/`.

The evaluation has 32 fault cases and 24 clean controls across four cohorts and two SQL forms. No misses or false alarms in that protocol; unknown faults are outside its scope.

## Power BI

Open `powerbi/generated/KPI_Autopsy.pbip` and refresh in Power BI Desktop. Rebuild after moving the folder. The four report pages pass schema and binding checks; native Desktop refresh and rendering remain unverified.

## Read the code

Start with `kpi_autopsy/sql/accepted_offer_rate.sql`, then `metrics.py` and `audit.py`. See the [walkthrough](docs/WALKTHROUGH.md), [metric definitions](docs/METRICS.md), [user stories](docs/BUSINESS_BRIEF.md) and [sources](docs/RESEARCH.md).

Data and generated files are ignored by Git. MIT-licensed code; the dataset keeps its publisher's terms.
