# Research and data sources

## Dataset

Boudewijn van Dongen, **BPI Challenge 2017**, Eindhoven University of Technology / 4TU.ResearchData.

- Dataset: https://doi.org/10.4121/uuid:5f3067df-f10b-45da-b98b-86ae4c7a310b
- Repository page: https://data.4tu.nl/articles/_/12696884/1
- Publisher's terms: https://doi.org/10.4121/resource:terms_of_use

The log records a Dutch financial institution's loan-application workflow, including multiple offers per application. It covers applications filed in 2016 and their subsequent observed events into February 2017.

Pinned compressed-file SHA-256:

```text
183c5e5189282779c811c78c33ff936351b3dd201165d612211fc220936f8249
```

The downloader checks this fingerprint. The dataset is separate from the MIT-licensed project code and is not bundled into the source ZIP.

## Aggregate explanations

Eugene Wu and Samuel Madden, **Scorpion: Explaining Away Outliers in Aggregate Queries**, PVLDB 6(8), 2013.

- Paper: https://www.vldb.org/pvldb/vol6/p553-wu.pdf
- Original implementation: https://github.com/sirrice/scorpion
- Related interface: https://github.com/sirrice/dbwipes

Scorpion is a predecessor for investigating suspicious aggregate results through their contributing records. KPI Autopsy does not reimplement its general predicate-search algorithms. It uses explicit metric contracts and a small set of evidence-based diagnostic rules.

## Metamorphic testing

T. Y. Chen, S. C. Cheung and S. M. Yiu, **Metamorphic Testing: A New Approach for Generating Next Test Cases**, Technical Report HKUST-CS98-01, 1998; archived on arXiv in 2020.

- Report: https://arxiv.org/abs/2002.12543

The project's concrete example adds an unaccepted offer without changing the application-level accepted-offer rate. That relationship is checked in the tests.

## Existing Power BI functionality

- Analyze explanations: https://learn.microsoft.com/en-us/power-bi/explore-reports/end-user-analyze-visuals
- Editable report format: https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report
- PBIR overview: https://learn.microsoft.com/en-us/power-bi/developer/embedded/projects-enhanced-report-format
- Public schemas: https://github.com/microsoft/json-schemas

Power BI already provides explanations for changes in visualized values. The purpose here is a more specific reporting workflow: compare a result with an explicit definition, retain evidence, and evaluate documented measurement faults.

## Scope of the originality claim

Query explanations, data provenance, reconciliation and metamorphic testing are established ideas. This project combines a banking event log, explicit application-level metric definitions, diagnostic evidence, reproducible SQL and an evaluation with clean controls. It does not claim a new universal debugging algorithm or a first-ever invention.
