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

Put **both** files on a common 36-month observation window and compute the same resolved-only
statistic on each: **8.40%** on the mature file (n=95,608) against **8.47%** on FY2020–26
(n=41,717). A gap of **0.07pp**, against the 1.22pp gap between the unwindowed rates `[C11]`.
Roughly 94% of the apparent deterioration is horizon.

I got this wrong twice, in two different ways, and both are worth stating.

**First**, I compared charge-offs ÷ *all observed loans* against charge-offs ÷ *resolved loans*.
Numerator and denominator have to come from the same population; that comparison is not one.

**Second**, having fixed that, I windowed only the *mature* file — restricting it to 36 months and
comparing against the young file's unrestricted rate. That is still not like-for-like. The young
file's median observation window is 2.8 years, but its FY2020 loans have now been observed for six,
so it carries slow exits the 36-month restriction is supposed to exclude. Both sides need the same
window. Applying it to both is what collapses the gap from 1.22pp to 0.07pp.

## Related: `EXEMPT` is maturity censoring, not FOIA redaction

I originally read `EXEMPT` as "withheld under a FOIA exemption." It is not. Its share rises from
1.4% of FY2010 loans to **27.1%** of FY2019 loans, and those loans have a median term of **126
months against 84** for the rest. It marks loans still within their term — long-dated credit that
has not yet had the chance to resolve. Treating it as missing-at-random data loss would bias against
exactly the longest-term loans.
