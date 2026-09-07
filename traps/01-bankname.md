# Trap 1 — `BankName` is not the originating lender

**Reproduce:** `python3 -m src.lender` · **Test:** `tests/test_claims.py::test_L4…L7`

## What I thought I had

Holder-level charge-off rates in the FY2010–2019 file vary enormously. Conditioning on sector,
approval year, borrower state, loan size band, term band, firm age and lender channel — additive
fixed effects fitted by Gauss-Seidel backfitting, so that no minimum cell size is needed and every
row is genuinely conditioned — dispersion across the 60 institutions with ≥1,000 resolved loans is
**9.33%**, against a raw dispersion of **9.25%** `[L2]`.

The controls remove nothing. Correlation between raw and adjusted rates is **0.980** `[L3]`.

Read at face value this says: which lender you borrow from matters more than your industry, your
state, your vintage and your firm's characteristics combined. That is a strong, publishable,
policy-relevant claim. I believed it for about a day.

## The line I had not read

From SBA's own data dictionary for this file:

> Name of the bank that the loan is currently assigned to.

*Currently.* Not "the bank that made the loan." The field is the holder as of the extract date,
stamped retroactively across sixteen years of bank mergers, bank failures, and secondary-market
sales. It is not a lender identifier at all. It is an ownership snapshot.

## Four checks

I did not want this to be true, so I tried to establish it four independent ways.

**`[L4]` Holders carry loans that predate their own existence.** If the field recorded who *made*
the loan, this would be impossible.

| institution | founded | loans | approved before it existed |
|---|---|---|---|
| VelocitySBA, LLC | ~2016 | 4,984 | **98.8%** |
| Truist Bank | 2019 | 6,428 | **94.4%** |
| BayFirst National Bank | ~2017 | 2,264 | 26.9% |

Truist did not exist until the BB&T–SunTrust merger closed in December 2019. It is credited here
with 6,428 loans approved in FY2010–2019, 94.4% of them before it existed.

**`[L5]` The originators that merged away hold nothing.** I listed 18 major 7(a) originators of the
2010s that have since been acquired or failed — Ridgestone, First Home Bank, BB&T, CenterState,
BBVA Compass, MB Financial, MUFG Union, and others. If the field recorded origination, they would
still appear against the loans they made.

**Zero of the 18 appear in the file at all.**

SunTrust — one of the decade's largest 7(a) originators — survives as **exactly one loan in
479,007**. A single straggler that escaped reassignment.

**`[L6]` Dispersion attenuates in older vintages.**

| vintage | holder sd |
|---|---|
| FY2010–11 | 3.44% |
| FY2012–13 | 3.33% |
| FY2014–15 | 4.31% |
| FY2016–17 | 9.49% |
| FY2018–19 | **12.27%** |

This runs the wrong way for a real effect. Older vintages are more fully resolved, so a genuine
difference in lending quality would be measured *more* precisely there. Instead it is measured
less precisely. Attenuation with age is what mixing looks like: the longer a loan has been
outstanding, the more chances it has had to be reassigned, and the more the holder's book converges
on the population average.

**`[L7]` The decisive test: loans that never changed hands.** The file flags whether a loan was sold
on the secondary market. Split on it and refit:

| | n | charge-off | holder FE sd |
|---|---|---|---|
| never sold | 324,191 | 6.97% | **3.72%** |
| sold | 104,683 | 11.03% | **10.02%** |

If holder identity measured lending quality, this split would not matter. Dispersion is nearly
**three times larger** among loans that demonstrably changed hands.

`tests/test_claims.py` recomputes this one *without* the backfit — raw dispersion, same split, same
conclusion — so a bug in the fixed-effects code and a bug in the test would have to agree.

## What survives

Nothing at the lender level. `BankName` cannot support cross-lender inference in this file, and the
9.33% dispersion is a measurement of portfolio reassignment, not of lending.

Note that the never-sold dispersion is 3.72%, not zero. Some of that is residual real variation.
But "never sold on the secondary market" does not mean "never reassigned" — whole-bank acquisitions
move loans without any secondary-market sale, which is exactly what `[L5]` shows. So 3.72% is an
upper bound on the real effect, not an estimate of it.

## What would actually fix it

A loan-level diff of `BankName` across two extract dates would convert "uninterpretable" into a
**measured reassignment rate**. That is the single highest-value next step for anyone working with
this file. I could not do it: SBA's older bulk extracts now return 404, and I have only one
snapshot. If you have an archived earlier extract, this is the analysis to run.

## The general lesson

The result was robust to every specification I tried. Adding controls did not weaken it —
correlation 0.980. Robustness is not validity. The variable simply did not mean what the column
name implied, and no amount of careful econometrics on a mislabelled variable recovers from that.

The check that killed it was not statistical. It was reading the data dictionary.
