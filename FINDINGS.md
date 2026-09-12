# Findings

Every claim carries a tag. `make fast` prints the tag; `make test` re-derives it from the panel
without importing the analysis module's own conclusion. If SBA republishes the extract, the tests
tell you *which* claim moved rather than leaving a stale number in the prose.

Base: 479,007 disbursed 7(a) loans approved FY2010–2019 (66,744 cancelled loans dropped, 12.2%),
plus 338,234 approved FY2020–present (50,104 dropped, 12.9%). Extract as of 2026-06-30.

---

## 1. Nothing in this file explains business failure

`[C1]`–`[C3]` · `src/ranking.py`

Each candidate variable is scored by how much it improves a Brier score against a permutation null
(200 draws), so that a variable with many small cells cannot win by chopping the data finely. The
permutation null matches the closed-form null `(K−1)/N · p̄(1−p̄)` on every factor.

| factor | what it is | excess ×1000 | cells | % of variance |
|---|---|---|---|---|
| `term_b` | loan structure | **5.360** | 5 | **7.31** |
| `BankName` | *current holder* — see trap 1 | 3.155 | 875 | 4.29 |
| `ext_cell` | sector × vintage × state | 1.146 | 3,484 | **1.53** |
| `proc` | lender channel | 0.381 | 20 | 0.52 |
| `BorrState` | geography | 0.356 | 54 | 0.49 |
| `age` | firm age | 0.225 | 9 | 0.31 |
| `sector` | industry | 0.200 | 20 | 0.27 |
| `size_b` | loan size band | 0.179 | 5 | 0.24 |
| `ApprovalFY` | macro vintage | 0.177 | 10 | 0.24 |
| `jobs_b` | jobs supported | 0.040 | 6 | 0.05 |

The base charge-off rate on the 428,874 resolved loans is **7.96%** `[C1]`, so total outcome
variance is `p̄(1−p̄)` = 0.0733. The last column divides each excess by that variance, computed on
the loans each factor actually scores — cells below n=30 are dropped by `resolution()`, so for
`ext_cell` the denominator is the retained-loan rate of 8.13% rather than the population 7.96%.
`src/ranking.py` emits this column directly, so it cannot drift from the prose. So:

- the strongest **external** classifier — sector × vintage × state, 3,484 cells — removes **1.53%**
  of outcome variance `[C4]`. Roughly **98.5% of the variation in whether a small business fails
  sits *within* a narrowly defined industry, year, and state cell.**
- firm age removes **0.31%**. Jobs supported is near zero, at 0.05%.
- what the file *does* predict is loan **structure**: the term band alone removes **7.31%**, more
  than every firm characteristic combined (age + size + jobs = 0.60%). That is a fact about how
  loans are written, not about which businesses survive. Term is set at underwriting, jointly with
  the lender's read of the borrower, and encodes information the file does not otherwise carry —
  so reading it as a borrower characteristic inverts the causal direction.

**What the null does not say.** It is not a claim that failure is random, and not a claim that
industry and geography are irrelevant. It is a statement about *recorded covariates in one
administrative file*. Two mechanisms fit it and this file cannot separate them: the determinants
may be genuinely idiosyncratic, or systematic but unrecorded — cash-flow management, the quality of
the books. Establishing that the public file cannot tell them apart, and quantifying how far short
it falls, is the contribution.

The government guarantees these loans, has published this file for over a decade, and records
neither why a business failed nor a stable identifier for who lent the money.

`BankName` ranks second. That is trap 1, and it is not a finding.

---

## 2. The lender result, and why it is not real

`[L1]`–`[L7]` · `src/lender.py` · full write-up in [`traps/01-bankname.md`](traps/01-bankname.md)

Conditioning on sector, vintage, state, loan size, term, firm age and lender channel via additive
fixed effects (Gauss-Seidel backfitting, no minimum cell size), holder-level charge-off dispersion
across the 60 institutions with ≥1,000 resolved loans is **9.33%** — against a raw dispersion of
9.25%. `[L2]` The controls remove nothing: correlation between raw and adjusted is **0.980** `[L3]`.

Four checks kill it:

| | check | result |
|---|---|---|
| `[L4]` | holders carry loans predating their own existence | VelocitySBA **98.8%**, Truist **94.4%**, BayFirst 26.9% |
| `[L5]` | 18 major 2010s originators since acquired | **0 appear in the file at all** |
| `[L6]` | dispersion by vintage | FY2010-11 **3.44%** → FY2018-19 **12.27%** — *attenuates* with age |
| `[L7]` | never-sold vs sold loans | holder FE sd **3.72%** vs **10.02%** |

`[L7]` is decisive. On 324,191 loans that never left the originator, holder dispersion is 3.72%.
On the 104,683 that were sold, it is 10.02% — nearly threefold. If holder identity measured lending
quality, that split would not matter.

`[L6]` runs the wrong way for a real effect: older vintages are *more* fully resolved, so a genuine
quality difference would be measured *more* precisely there, not less. Attenuation with age is the
signature of mixing — older loans have had more time to be reassigned.

SunTrust, one of the decade's largest 7(a) originators, survives in the file as **exactly one loan
in 479,007**.

**The error is not classical, which is why it is large.** Classical measurement error in a
regressor attenuates — it pulls estimates toward zero. Reassignment does not, because it is not
random with respect to the outcome: sold loans charge off at 11.03% against 6.97% for never-sold.
The loans that move are disproportionately the loans that fail, so the induced error correlates
with charge-off rather than being independent of it, and its sign in any comparison depends on
which institutions sold and when. That is why the artifact dominates every borrower characteristic
rather than adding noise to a weak signal. (The split is consistent with selection on risk but is
not a test of it: the file records the sale flag and the outcome, not what the seller knew.)

**The general shape.** `BankName` is not mismeasured, mislinked or misreported. It is correct — as
of the date the file was produced. The variable is defined at **extract time** rather than **event
time**, so every quarterly release silently restates sixteen years of history to match present
ownership. That is a failure mode with no survey analogue, and it is invisible to the checks
researchers normally run: the data are complete, internally consistent, stable in format, and the
column has a plausible name.

### The rate, measured

`[R1]`–`[R5]` · `src/reassignment.py`

An earlier version of this file said the reassignment rate could not be measured from public data.
It can: the **Internet Archive** holds `FOIA_7a_FY2010_FY2019_asof_260331.csv`, three months before
the current snapshot. Joining the two on borrower and loan identity:

| | |
|---|---|
| matched in both snapshots | **536,486** (98.3%) |
| `BankName` string differs | 8,527 (1.589%) |
| **differs after normalising name forms** | **3,300 (0.615%)** |

**0.615% of loans change holder per quarter** `[R4]`. Two further things fall out. First, **61% of
the apparent change is SBA respelling one institution** — a trap for anyone matching this field
across releases. Second, at a constant rate 0.615% a quarter compounds to roughly a third of the
file changing holder at least once over sixteen years, which is the order of magnitude the
reassignment story needs. *That last figure is arithmetic on one quarter's observation, not a
measurement.*

---

## 3. Prepayment is the dominant exit, and it is not censoring

`[C5]`–`[C9]` · `src/incidence.py` · [`traps/04-competing-risks.md`](traps/04-competing-risks.md)

- **92.0%** of resolved exits are prepayment, not charge-off `[C5]`
- median time to charge-off 55.9 months; to prepayment 59.3 months `[C6]`
- only 3.9% of charge-offs occur within 18 months; 23.5% within 36 `[C7]`
- at 120 months, 1−Kaplan-Meier says **15.83%** against an Aalen-Johansen CIF of **7.14%** —
  overstating lifetime charge-off by **122%** `[C8]`

Treating prepayment as censoring assumes prepaid borrowers remained at risk of charging off. They
did not; they were gone. The AJ plateau (7.68%) and the naive resolved-only rate (7.96%) differ by
0.28pp `[C9]` — so **resolved-only is sound as a lifetime quantity**, and 1−KM is not.

---

## 4. Recent vintages are immature, not deteriorating

`[C10]`–`[C11]` · [`traps/02-resolved-only.md`](traps/02-resolved-only.md)

**77.8%** of FY2020–2026 loans are unresolved `[C10]`. The naive charge-off rate on that file is
9.18% against 7.96% on the mature file — which reads as deterioration.

It is not. Restricting the *mature* file to exits within 36 months of approval — the same
observation window the recent file has had — gives **8.40%** `[C11]`. Early-resolving loans are
disproportionately charge-offs, because prepayment takes longer. Most of the apparent gap is the
window, not the borrowers.

---

## 5. What it would take to be worth doing

`[B1]`–`[B7]` · `src/breakeven.py`

This does not estimate a benefit. No randomised estimate of the effect of AI-assisted financial
operations on small-business survival exists. It asks the answerable question instead: how large
would the effect have to be to pay for itself?

Greenfield 7(a) borrowers under $150K, FY2021–2025: **8,167 loans/yr**, $393M approved, $256M
guaranteed (65.2%), **41,430 jobs** `[B2]`. At the mature-vintage loss rate, **754 expected
failures/yr carrying 4,125 jobs** `[B3]`, and **$16.9M** of annual guarantee losses `[B4]`.
A $240/seat programme for the whole cohort costs **$2.0M/yr** `[B5]`.

- break-even on **guarantee losses alone**: **11.6%** reduction in failures `[B6]` — this involves
  no tax assumption whatsoever
- including the federal tax base: **3.3%–4.3%**, across the full plausible range of the one
  genuinely arguable parameter `[B7]`

| scenario | tax/yr | total exposure | break-even |
|---|---|---|---|
| FICA only (statutory floor) | $28.4M | $45.3M | 4.3% |
| + income tax, married filing jointly (~3.1%) | $34.2M | $51.0M | 3.8% |
| + income tax, single filer (~7.3%) | $42.0M | $58.8M | 3.3% |

The conclusion does not depend on which value you choose. **These are thresholds, not forecasts.**
Gross jobs at risk also overstates net social loss — displaced workers find other work. The durable
claim is about the stock of business *owners*, which is not fungible in the same way.

---

## 6. Data quality facts worth knowing

`[V1]` and the pinned quirks in `tests/test_build.py`

- **`BusinessAge` non-response rises 9.1% (FY2010) → 18.7% (FY2019)** `[V1]`. The raw code is
  literally `"Unanswered"`. Any share computed on this variable rests on an eroding base, and the
  erosion concentrates in exactly the recent years most people analyse.
- **10 loans** carry `LoanStatus == CHGOFF` with no charge-off date — resolved, but impossible to
  place on a timeline.
- **2 loans** carry a paid-in-full date days *before* disbursement.
- `EXEMPT` status is **maturity censoring, not FOIA redaction**: its share rises 1.4% (FY2010) to
  27.1% (FY2019), and those loans have a median term of 126 months against 84 for the rest.

The last one is a correction to my own earlier reading of the file.
