# Trap 2 — recent vintages are immature, not deteriorating

**Reproduce:** `python3 -m src.incidence` · **Test:** `test_C10_the_recent_file_is_mostly_unresolved`

**77.8%** of loans in the FY2020–present extract are unresolved `[C10]`. They have neither charged
off nor paid in full; they are simply still running.

The naive charge-off rate on that file is **9.18%**, against **7.96%** on the mature FY2010–2019
file. Read straight, that is a programme getting worse.

It is not. It is a window artefact, and the direction is predictable: **early-resolving loans are
disproportionately charge-offs**, because prepayment takes longer. Median time to charge-off is 55.9
months; to prepayment, 59.3 `[C6]`. A young file has seen the fast failures and few of the slow
successes.

Restrict the *mature* file to exits within 36 months of approval — the same observation window the
recent file has actually had — and the rate is **8.40%** `[C11]`, against 9.18% recent and 7.96%
unrestricted. Most of the apparent deterioration is the window.

The comparison has to be like-for-like in **two** ways, and I got this wrong the first time: both
numerator and denominator must come from the same population. Comparing charge-offs ÷ *all observed
loans* against charge-offs ÷ *resolved loans* is not a comparison of anything. `[C11]` is now a
36-month-window resolved-only rate on both sides.

## Related: `EXEMPT` is maturity censoring, not FOIA redaction

I originally read `EXEMPT` as "withheld under a FOIA exemption." It is not. Its share rises from
1.4% of FY2010 loans to **27.1%** of FY2019 loans, and those loans have a median term of **126
months against 84** for the rest. It marks loans still within their term — long-dated credit that
has not yet had the chance to resolve. Treating it as missing-at-random data loss would bias against
exactly the longest-term loans.
