# Liability Exposure and Task Delegation

Replication material for *Liability Exposure and Task Delegation: What Usage Data Can and
Cannot Say About Small-Business AI Adoption* (Greer-Gentis, October 2026).

Every number the paper computes is produced by one of the scripts here. Each prints its
figures against the tag used in the paper's prose and **exits 2 if any tag fails to
resolve**, so a partial run cannot be mistaken for a complete one.

## What produces what

| Paper element | Script | Tags |
|---|---|---|
| Table 2, operational tasks by liability exposure | `aei_paper.py` | `T1.*` |
| Figure 1, how the nine tasks are worked | `aei_figure_modes.py` | writes `output/figure_modes.png` |
| Appendix B, Table B2, collaboration modes | `aei_liability.py` | `S.*` |
| Table 3, liability and difficulty across the full taxonomy | `aei_liability.py` | `G.*` strict headline, `K.*` broad robustness, `E.*` difficulty |
| Table 4, sample required to detect a reduction in failures | `power.py` | `W.*` |
| Section 4, artifact-composition and strict-coding checks | `aei_liability.py` | `C.*`, `K.*` |
| Section 4 and Appendix B, checkability coefficients and the 6,435-partition placebo | `aei_paper.py` | `T2.*`, `L.*`, `X.*`, `D.*` |
| Appendix B, artifact-based recode against the keyword coding | `aei_verifiability.py` | — |
| Appendix A, the strict and broad codings and the topics each flags | `aei_liability.py` | `K.n_flagged`, `K.broad_only_n` |
| Appendix B, Table B1, the gap under alternative samples | `aei_liability.py` | `R.*` |
| Appendix B, placebo over all 36 pairs, April and May gaps, bootstrap | `aei_liability.py` | `P.*`, `M.*`, `B.*` |
| Appendix B, Figure B1, automation share against checkability | `aei_figure1.py` | writes `output/figure1_threshold.png` |
| Appendix C, charge-off concentration and AUC | `sba_discrimination.py`, `sba_7a_mix.py` | — |
| This map and the paper's own cross-references | `check_crossrefs.py` | exits 2 on a stale pointer |

Table 1 and the barrier rankings in Section 2 are quoted from the published Credit Survey
and Census BTOS reports. They are not recomputed here and have no script.

## Running it

The Economic Index extract is not redistributed. Point `AEI_CSV` at the Claude.ai file from
the release of June 26, 2026:

```
AEI_CSV=/path/to/aei_claude_ai_2026-06-26.csv python3 aei/aei_paper.py
AEI_CSV=/path/to/aei_claude_ai_2026-06-26.csv python3 aei/aei_liability.py
AEI_CSV=/path/to/aei_claude_ai_2026-06-26.csv python3 aei/aei_figure1.py
AEI_CSV=/path/to/aei_claude_ai_2026-06-26.csv python3 aei/aei_figure_modes.py
python3 aei/power.py
```

`power.py` needs no external data: it reads the 7(a) panels in `data/` through
`src/build.py`. The two `sba_*.py` scripts want the raw FOIA extract via `SBA_CSV`.

`check_crossrefs.py` reads the built paper, recovers the structure it actually has, and fails if
any reference here or in the paper points at a section, table or figure that does not exist, or if
a row above names a section that does not discuss its subject. It exists because that failure
shipped: this map sent readers to Section 5 for the checkability coefficients after that section
was folded into Section 4.

`aei_liability.py` and `aei_paper.py` use `scipy` only for the Welch test; without it those
two tags report as skipped and the run exits 2. Everything else, including the OLS with
heteroskedasticity-robust standard errors, is pure Python.

## Two windows on the 7(a) cohort

Section 6 of the paper uses the greenfield cohort, meaning 7(a) loans under $150,000 to
businesses less than two years old, through two different windows, and `power.py` keeps
them apart deliberately:

- **Fiscal 2010–2019** supplies the charge-off rate, because a rate can only be observed on
  loans old enough to have resolved. 57,772 approvals, 55,479 resolved, 9.24%.
- **Fiscal 2021–2025** supplies the enrollment scale and the costs, because a trial enrolls
  going forward. 8,167 approvals a year, $1.96M a year at $240 a seat, against $16.9M of
  expected guarantee losses, giving an 11.6% break-even on guarantee losses alone and
  3.3–4.3% once federal tax exposure is counted.

These are the same figures `FINDINGS.md` reports from the loan-file analysis in `src/`;
the paper and this repository agree by construction rather than by coincidence.

## Data

- Anthropic Economic Index, release of June 26, 2026, global cut, April and May 2026, CC-BY.
  The automation and augmentation split and the five collaboration modes are from Handa et
  al. (2025), arXiv:2503.04761.
- Federal Reserve Banks, *2026 Report on Employer Firms* (2025 Small Business Credit Survey).
- U.S. Census Bureau, Business Trends and Outlook Survey.
- SBA 7(a) FOIA extracts, fiscal 2010–2019 and fiscal 2020–present, as of June 30, 2026.
