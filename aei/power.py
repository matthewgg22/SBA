"""
Trial sizing for the target cohort (greenfield 7(a) under $150K).

Two-proportion test, equal arms, two-sided alpha = 0.05, power = 0.80.
Base rate is the MATURE-vintage charge-off rate for the cohort. Earlier versions of
this calculation reported PER-ARM figures against the retired 17.4% base rate; both
errors are corrected here and the totals are what the PAE quotes.

Run:  SBA_2010=<path to FY2010-19 FOIA csv> python3 analysis/power.py
"""
import math, os, sys

Z_A, Z_B = 1.959963985, 0.841621234       # alpha .05 two-sided, power .80

emitted, skipped = {}, []
def tag(t, v, f="{:.2f}"):
    emitted[t] = v
    print(f"  [{t}] {f.format(v) if isinstance(v,(int,float)) else v}")
def skip(t, why):
    skipped.append((t, why)); print(f"  [{t}] SKIPPED - {why}")


def n_total(p1, rel_reduction, z_a=Z_A, z_b=Z_B):
    """Total N across BOTH arms to detect a relative reduction from p1."""
    p2 = p1 * (1 - rel_reduction)
    var = p1 * (1 - p1) + p2 * (1 - p2)
    per_arm = (z_a + z_b) ** 2 * var / (p1 - p2) ** 2
    return 2 * math.ceil(per_arm), math.ceil(per_arm), p2


MATURE = (2010, 2019)      # vintages old enough to have resolved
CURRENT = (2021, 2025)     # the scale a trial would actually enroll at
SEAT = 240                 # dollars per borrower per year
GUARANTEE_LOSSES = 16.9e6  # expected annual guarantee losses on the current cohort


def cohort_facts():
    """Base rate from matured vintages; enrollment scale from the current ones.

    These are two different windows on purpose. A charge-off rate can only be
    observed on loans old enough to have resolved, so it comes from FY2010-2019.
    A trial enrolls going forward, so its scale and its costs come from FY2021-2025.
    An earlier version of this script divided by the FY2010-2019 count instead,
    which mixed a historical cohort size into a forward-looking calculation.
    """
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import pandas as pd
        from src.build import load
        d = load()
        m = d[d.greenfield & (d.GrossApproval < 150_000) & d.resolved]
        here = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "data", "panel_fy2020_present.parquet")
        c = pd.read_parquet(here)
        c = c[c.greenfield & (c.GrossApproval < 150_000)
              & c.ApprovalFY.between(*CURRENT)]
        annual = len(c) / (CURRENT[1] - CURRENT[0] + 1)
        return float(m.chgoff.mean()), len(m), annual
    except Exception as e:
        print(f"  (panel unavailable: {e}; falling back to the recorded values)")
        return 0.0924, None, 8167.0

if __name__ == "__main__":
    p1, n, annual = cohort_facts()
    print(f"base charge-off rate {p1:.4f}" + (f" on {n:,} resolved cohort loans" if n else ""))
    print(f"annual cohort {annual:,.0f}\n")
    print(f"{'effect':<34}{'p2':>8}{'per arm':>10}{'TOTAL':>9}{'months of cohort':>18}")
    for label, rel in [("20% relative reduction", 0.20),
                       ("11.6% (guarantee break-even)", 0.116),
                       ("4.3% (total-exposure break-even)", 0.043)]:
        tot, arm, p2 = n_total(p1, rel)
        print(f"{label:<34}{p2:>8.4f}{arm:>10,}{tot:>9,}{12*tot/annual:>17.1f}")
    print("\nThese are TOTALS across both arms. Powering on charge-off alone is why the design")
    print("accumulates across cohorts and is powered on intermediate outcomes.")

    # Table 5 of paper/liability-delegation-v3.docx, tagged as the prose quotes it.
    print("\n## Table 5: sample required to detect a reduction in failures")
    tag("W.base", 100 * p1, "{:.2f}")
    if n: tag("W.resolved", n, "{:,.0f}")
    tag("W.cohort", annual, "{:,.0f}")
    cost = annual * SEAT
    tag("W.seat_cost", cost, "{:,.0f}")
    tag("W.breakeven_guarantee", 100 * cost / GUARANTEE_LOSSES, "{:.1f}")
    for key, rel in [("r33", 0.033), ("r43", 0.043), ("r116", 0.116),
                     ("r20", 0.200), ("r30", 0.300)]:
        tot, arm, p2 = n_total(p1, rel)
        tag(f"W.{key}_rate", 100 * p2, "{:.2f}")
        tag(f"W.{key}_arm", arm, "{:,.0f}")
        tag(f"W.{key}_total", tot, "{:,.0f}")
        tag(f"W.{key}_years", tot / annual, "{:.1f}")
    print(f"\n{len(emitted)} figures emitted, {len(skipped)} skipped")
    if skipped:
        for t, why in skipped: print(f"  SKIPPED {t}: {why}")
        sys.exit(2)
