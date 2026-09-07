# Trap 4 — prepayment is 92% of exits, and it is not censoring

**Reproduce:** `python3 -m src.incidence` · **Test:** `test_C8_one_minus_KM_more_than_doubles…`

A 7(a) loan leaves the portfolio two ways: it charges off, or it is paid in full. **92.0% of
resolved exits are prepayment** `[C5]`.

The standard reflex is 1−Kaplan-Meier for the cumulative charge-off curve, treating prepaid loans
as censored. That is wrong here, and badly so. Censoring means "still at risk, not yet observed."
A borrower who paid in full is not still at risk of charging off. They are **gone**.

At 120 months:

| estimator | cumulative charge-off |
|---|---|
| 1 − Kaplan-Meier | **15.83%** |
| Aalen-Johansen CIF | **7.14%** |

1−KM overstates lifetime charge-off by **122%** `[C8]`.

The mechanism: KM keeps prepaid loans in the risk set as though they might yet fail, so the hazard
gets applied to a population that has already left. With prepayment at 92% of exits, that
population is almost everyone.

## The reassuring part

The Aalen-Johansen plateau is **7.68%** against a naive resolved-only rate of **7.96%** — a
difference of 0.28pp `[C9]`.

So the simple denominator everyone reaches for first, charge-offs ÷ resolved loans, is **sound as a
lifetime quantity**. It is 1−KM — the more sophisticated-looking choice — that goes wrong. Reaching
for survival machinery without checking what competes for the exit is worse than not reaching for it.

What resolved-only does *not* give you is timing, and timing is what trap 2 turns on. For that you
need the CIF, because the shape of the curve is exactly what a naive rate throws away: only 3.9% of
charge-offs occur within 18 months, and 23.5% within 36 `[C7]`.

`src/incidence.py` implements both estimators directly — about thirty lines each — rather than
taking a dependency, so the difference between them is inspectable rather than a library call.
