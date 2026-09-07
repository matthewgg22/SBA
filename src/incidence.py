"""
How often do these loans actually charge off?

TRAP 4 — competing risks. Most 7(a) loans exit by prepayment, not default. Prepayment
is absorbing and correlated with borrower quality, so treating it as ordinary censoring
in a Kaplan-Meier estimator overstates cumulative default incidence. The right estimand
is the Aalen-Johansen cause-specific cumulative incidence function:
    CIF(t) = sum_{s<=t} h_chgoff(s) * S(s-1)      where S uses ALL exits.

TRAP 2 — resolved-only rates on young vintages. Dividing charge-offs by resolved loans
is a reasonable *lifetime* estimate once a cohort has matured, but badly biased before
then, because charge-offs resolve earlier than prepayments.

Every number here is a ratio of counts a reader can recompute.
"""
import os
import numpy as np, pandas as pd
from src.build import load


def aalen_johansen(duration, cause, grid):
    """Cause-specific CIF for cause==1, competing cause==2, censored cause==0."""
    df = pd.DataFrame({"t": duration, "c": cause}).dropna()
    df = df[df.t >= 0].sort_values("t")
    times = np.sort(df.t.unique())
    n = len(df)
    at_risk, S, cif = n, 1.0, 0.0
    out, ti = [], 0
    tcounts = df.groupby("t").c.value_counts().unstack(fill_value=0)
    for t in times:
        row = tcounts.loc[t]
        d1, d2, d0 = int(row.get(1, 0)), int(row.get(2, 0)), int(row.get(0, 0))
        if at_risk > 0:
            cif += S * d1 / at_risk                       # increment BEFORE updating S
            S *= 1 - (d1 + d2) / at_risk
        at_risk -= (d1 + d2 + d0)
        while ti < len(grid) and grid[ti] <= t:
            out.append(cif); ti += 1
    out += [cif] * (len(grid) - len(out))
    return np.array(out)


def km_one_minus(duration, cause, grid):
    """1 - Kaplan-Meier treating the competing exit as censoring. The wrong estimator."""
    df = pd.DataFrame({"t": duration, "c": cause}).dropna()
    df = df[df.t >= 0].sort_values("t")
    n, S = len(df), 1.0
    out, ti = [], 0
    tcounts = df.groupby("t").c.value_counts().unstack(fill_value=0)
    at_risk = n
    for t in np.sort(df.t.unique()):
        row = tcounts.loc[t]
        d1 = int(row.get(1, 0)); other = int(row.get(2, 0)) + int(row.get(0, 0))
        if at_risk > 0:
            S *= 1 - d1 / at_risk
        at_risk -= (d1 + other)
        while ti < len(grid) and grid[ti] <= t:
            out.append(1 - S); ti += 1
    out += [1 - S] * (len(grid) - len(out))
    return np.array(out)


if __name__ == "__main__":
    os.makedirs("output/tables", exist_ok=True)
    d = load()
    res = d[d.resolved]
    print(f"[C4] disbursed FY2010-19 loans: {len(d):,}; resolved {len(res):,}; "
          f"naive resolved-only charge-off rate {res.chgoff.mean():.4f}")

    print("\n--- exit composition (TRAP 4) ---")
    comp = d.cause.value_counts().rename({0:"censored (still outstanding)",1:"charge-off",2:"paid in full"})
    print(comp.to_string())
    ex = d[d.cause.isin([1,2])]
    print(f"[C5] prepayment is {100*(ex.cause==2).mean():.1f}% of resolved exits")
    print(f"[C6] median months to charge-off {d.loc[d.cause==1,'duration'].median():.1f}; "
          f"to prepayment {d.loc[d.cause==2,'duration'].median():.1f}")
    co = d.loc[d.cause == 1, "duration"]
    print(f"[C7] {100*(co<=18).mean():.1f}% of charge-offs within 18 months; "
          f"{100*(co<=36).mean():.1f}% within 36")

    print("\n--- 1-KM vs Aalen-Johansen CIF (TRAP 4) ---")
    grid = np.array([12,24,36,60,84,120,180])
    cif = aalen_johansen(d.duration.values, d.cause.values, grid)
    km  = km_one_minus(d.duration.values, d.cause.values, grid)
    t = pd.DataFrame({"months": grid, "AJ_CIF_%": 100*cif, "1_minus_KM_%": 100*km})
    t["overstatement_pp"] = t["1_minus_KM_%"] - t["AJ_CIF_%"]
    print(t.round(2).to_string(index=False))
    i120 = list(grid).index(120)
    print(f"[C8] at 120 months KM says {100*km[i120]:.2f}% against AJ {100*cif[i120]:.2f}% — "
          f"overstating by {100*(km[i120]/cif[i120]-1):.0f}%")
    print(f"[C9] AJ plateau {100*cif[-1]:.2f}% vs naive resolved-only {100*res.chgoff.mean():.2f}% "
          f"— the resolved-only convention is sound as a LIFETIME quantity ({100*(res.chgoff.mean()-cif[-1]):+.2f}pp)")

    print("\n--- the same rate on a young vintage (TRAP 2) ---")
    y = load("fy2020_present")
    yr = y[y.resolved]
    print(f"[C10] FY2020-26: {100*(~y.resolved).mean():.1f}% unresolved; naive resolved-only rate "
          f"{100*yr.chgoff.mean():.2f}% against {100*res.chgoff.mean():.2f}% on the mature file")
    obs = (d.as_of.iloc[0] - d.approval_date).dt.days/365.25
    obsy = (y.as_of.iloc[0] - y.approval_date).dt.days/365.25
    print(f"      median observation window: {obs.median():.1f} yrs vs {obsy.median():.1f} yrs")
    # Put BOTH files on the same 36-month observation window and compute the SAME
    # resolved-only statistic on each. Windowing only the mature file is not a
    # like-for-like comparison either: the young file's median window is 2.8 years,
    # but its FY2020 loans have now been observed for six.
    def windowed(df, months=36):
        w = df[df.duration.notna()]
        ex = w[(w.duration <= months) & w.cause.isin([1, 2])]
        return 100 * (ex.cause == 1).mean(), len(ex)

    mrate, mn = windowed(d)
    yrate, yn = windowed(y)
    print(f"[C11] on a common 36-month window the two files give {mrate:.2f}% (mature, n={mn:,}) "
          f"against {yrate:.2f}% (FY2020-26, n={yn:,}) — a gap of {yrate-mrate:.2f}pp, against the "
          f"{100*yr.chgoff.mean()-100*res.chgoff.mean():.2f}pp gap between the unwindowed rates "
          f"({100*yr.chgoff.mean():.2f}% vs {100*res.chgoff.mean():.2f}%). The apparent "
          f"deterioration is almost entirely a horizon artifact.")
    pd.DataFrame({"months":grid,"aj_cif":cif,"one_minus_km":km}).to_csv("output/tables/incidence.csv", index=False)
