# Liability Exposure and Task Delegation

Replication material for *Liability Exposure and Task Delegation: What Usage Data Can and
Cannot Say About Small-Business AI Adoption* (`paper/liability-delegation-v4.docx`).

Every number the paper prints is produced by one of the scripts below. Each script prints
its figures against the tag used in the prose and **exits 2 if any tag fails to resolve**,
so a partial run cannot be mistaken for a complete one.

## What produces what

| Paper element | Script | Tags |
|---|---|---|
| Table 1, operational tasks by liability exposure | `aei/aei_paper.py` | `T1.*` |
| Table 2, collaboration modes underneath the automation share | `aei/aei_liability.py` | `S.*` |
| Table B1, the gap under alternative samples | `aei/aei_liability.py` | `R.*` |
| Appendix B, placebo over all 36 pairs, April and May gaps, bootstrap interval | `aei/aei_liability.py` | `P.*`, `M.*`, `B.*` |
| Table 3, liability and difficulty across the full taxonomy | `aei/aei_liability.py` | `G.*`, `E.*` |
| Artifact-composition and strict-coding checks (Section 3) | `aei/aei_liability.py` | `C.*`, `K.*` |
| Appendix A, the liability coding and the 78 flagged topics | `aei/aei_liability.py` | `K.n_flagged` |
| Figure B1, automation share against the checkability index | `aei/aei_figure1.py` | writes `output/figure1_threshold.png` |
| Section 4, checkability coefficients and the 6,435-partition placebo | `aei/aei_paper.py` | `T2.*`, `L.*`, `X.*`, `D.*` |
| Section 4, artifact-based recode against the keyword coding | `aei/aei_verifiability.py` | — |
| Table 5, sample required to detect a reduction in failures | `aei/power.py` | `W.*` |
| Appendix C, charge-off concentration and AUC | `aei/sba_discrimination.py`, `aei/sba_7a_mix.py` | — |

Table 4 and the barrier rankings in Section 5 are quoted from the published Credit Survey
and BTOS reports. They are not recomputed and have no script.

## Running it

The Index extract is not redistributed here. Point `AEI_CSV` at the Claude.ai file from the
26 June 2026 release:

```
AEI_CSV=/path/to/aei_claude_ai_2026-06-26.csv python3 aei/aei_paper.py
AEI_CSV=/path/to/aei_claude_ai_2026-06-26.csv python3 aei/aei_liability.py
AEI_CSV=/path/to/aei_claude_ai_2026-06-26.csv python3 aei/aei_figure1.py
python3 aei/power.py
```

`aei_liability.py` and `aei_paper.py` use `scipy` only for the Welch test; without it those
two tags are reported as skipped and the run exits 2. Everything else, including the OLS with
heteroskedasticity-robust standard errors, is pure Python.

`power.py` reads the 7(a) panel through `sba-7a/src/build.py` to recover the cohort's own
charge-off rate. If the panel is unreachable it falls back to the recorded 9.24 percent and
says so.

## Rebuilding the paper

The build script is not in this repository; the paper is distributed as a PDF.

<!--

```
NODE_PATH=/opt/homebrew/lib/node_modules node build_liability_delegation.js liability-delegation-v4.docx
```

Requires `docx` (npm) and the figures in `output/`. The build is deterministic: rebuilding
reproduces `word/document.xml` byte for byte, and only the embedded creation timestamp in
`docProps/core.xml` differs between runs.

-->

## Data

- Anthropic Economic Index, release of 26 June 2026, global cut, April and May 2026, CC-BY.
- Federal Reserve Banks, *2026 Report on Employer Firms* (2025 Small Business Credit Survey).
- U.S. Census Bureau, Business Trends and Outlook Survey.
- SBA 7(a) FOIA extract, fiscal 2010–2019, as of 30 June 2026.

## Relationship to the rest of this repository

The loan-file analysis in `src/` is the earlier project: it builds the 7(a) panel,
estimates charge-off models, and computes the break-even thresholds that Section 7
of the paper quotes. `aei/power.py` reads that panel through `src/build.py`, so the
cohort figures in the paper and in `FINDINGS.md` come from the same source and agree:
8,167 greenfield loans under $150,000 a year in fiscal 2021 to 2025, an 11.6%
break-even on guarantee losses, and 3.3 to 4.3% once federal tax exposure is counted.
