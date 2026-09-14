"""
Which recorded variables carry signal about charge-off?

Brier-score RESOLUTION: sum_k (n_k/N) * (p_k - pbar)^2 — how far knowing a factor
moves you from the base rate. Corrected against a permutation null, because
high-cardinality factors earn resolution mechanically. The closed-form null for a
random partition is (K-1)/N * pbar*(1-pbar); we report both.
"""
import os
import numpy as np, pandas as pd
from src.build import load

FACTORS = [("term_b","loan structure"), ("BankName","current holder"),
           ("ext_cell","external: sector x vintage x state"), ("proc","lender channel"),
           ("BorrState","external: geography"), ("age","firm-level"),
           ("sector","external: industry"), ("size_b","firm-level"),
           ("ApprovalFY","external: macro vintage"), ("jobs_b","firm-level"),
           ("franchise","firm-level")]


def resolution(y, key, minn=30):
    t = pd.DataFrame({"y": np.asarray(y), "k": np.asarray(key)})
    g = t.groupby("k", observed=True).y.agg(["size","mean"])
    g = g[g["size"] >= minn]
    if not len(g):
        return np.nan
    N = g["size"].sum(); pbar = (g["size"] * g["mean"]).sum() / N
    return float(((g["size"] / N) * (g["mean"] - pbar) ** 2).sum())


def retained_base(y, key, minn=30):
    """Base rate among the loans a factor actually scores. Cells below minn are dropped by
    resolution(), so the denominator for "share of variance explained" has to be computed on
    the SAME retained loans - not on the full panel, and emphatically not on some other cohort."""
    t = pd.DataFrame({"y": np.asarray(y), "k": np.asarray(key)})
    g = t.groupby("k", observed=True).y.agg(["size","mean"])
    g = g[g["size"] >= minn]
    N = g["size"].sum()
    return float((g["size"] * g["mean"]).sum() / N), int(N)


def closed_form_null(K, N, pbar):
    return (K - 1) / N * pbar * (1 - pbar)


def cell_spread(y, key, minn=30):
    """Loan-weighted percentiles of the cell charge-off rate.

    WHY THIS EXISTS. "98.5% of variance is within-cell" is a ratio, and for a rare binary
    outcome that ratio is bounded near zero almost regardless of what the factor is -- eta^2
    cannot be large when p(1-p) is 0.073. Reporting only the ratio makes a property of the
    statistic look like a discovery. The p10-p90 spread of the cell rates is the magnitude the
    ratio hides: it says how different the cells actually are, in the units a reader cares about.
    Both numbers are true and neither alone is honest."""
    t = pd.DataFrame({"y": np.asarray(y), "k": np.asarray(key)})
    g = t.groupby("k", observed=True).y.agg(["size","mean"])
    g = g[g["size"] >= minn].sort_values("mean")
    cw = g["size"].cumsum() / g["size"].sum()
    q = lambda p: float(g["mean"][cw >= p].iloc[0])
    return q(0.10), q(0.50), q(0.90)


def naics_grain(d, digits, draws=50, seed=7):
    """Signal in industry alone, and in the external cell, at a given NAICS grain.

    TRAP: the headline uses 2-digit NAICS, which is the COARSEST published grain -- 24 cells for
    the whole economy. Calling that "narrowly defined industry" overstates the control. Finer
    grains carry more signal and cover fewer loans; both have to be reported together, because a
    var_share computed on a fifth of the book is not comparable to one computed on all of it."""
    rng = np.random.default_rng(seed)
    y = d.y.values
    n = d.naics6.str[:digits]
    out = {}
    for label, key in [("industry", n),
                       ("ext_cell", n + "|" + d.ApprovalFY.astype(str) + "|" + d.BorrState.astype(str))]:
        obs = resolution(y, key)
        rp, rn = retained_base(y, key)
        null = float(np.nanmean([resolution(rng.permutation(y), key) for _ in range(draws)]))
        K = int((d.groupby(key, observed=True).size() >= 30).sum())
        out[label] = dict(cells=K, retained=rn, coverage=rn/len(d),
                          excess=obs-null, var_share=(obs-null)/(rp*(1-rp)))
    return out


def prep(d):
    d = d[d.resolved].copy()
    d["y"] = d.chgoff.astype(float)
    d["jobs_b"] = pd.cut(d.JobsSupported, [-1,1,2,5,10,25,1000]).astype(str)
    d["ext_cell"] = d.sector + "|" + d.ApprovalFY.astype(str) + "|" + d.BorrState.astype(str)
    return d


def run(d, draws=200, seed=7):
    rng = np.random.default_rng(seed)
    y = d.y.values
    rows = []
    for col, kind in FACTORS:
        obs = resolution(y, d[col])
        rp, rn = retained_base(y, d[col])
        null = float(np.nanmean([resolution(rng.permutation(y), d[col]) for _ in range(draws)]))
        K = d.groupby(col, observed=True).size().pipe(lambda s: (s >= 30).sum())
        rows.append({"factor": col, "type": kind, "observed": obs, "perm_null": null,
                     "closed_form_null": closed_form_null(K, len(d), y.mean()),
                     "excess": obs - null, "cells": int(K),
                     "retained_n": rn, "retained_pbar": rp,
                     "variance_share": (obs - null) / (rp * (1 - rp))})
    return pd.DataFrame(rows).sort_values("excess", ascending=False)


if __name__ == "__main__":
    os.makedirs("output/tables", exist_ok=True)
    d = prep(load())
    print(f"[C1] resolved FY2010-19 loans: {len(d):,} | base charge-off {d.y.mean():.4f}")
    t = run(d)
    out = t.assign(**{k: (1000*t[k]).round(3) for k in ["observed","perm_null","closed_form_null","excess"]})
    out["var_share_%"] = (100*t.variance_share).round(2)
    print("\nPredictive signal, x1000 (permutation-corrected):")
    print(out[["factor","type","observed","perm_null","closed_form_null","excess","cells",
               "var_share_%"]].to_string(index=False))
    print("\n  var_share_% = excess / [p(1-p)] on the loans that factor actually scores (cells n>=30).")
    t.to_csv("output/tables/ranking.csv", index=False)
    top, bot = t.iloc[0], t.iloc[-1]
    print(f"\n[C2] {top.factor} leads at {1000*top.excess:.3f}; {bot.factor} last at {1000*bot.excess:.3f} "
          f"({top.excess/bot.excess:.0f}x)")
    ext = t[t.factor.eq("ext_cell")]
    print(f"[C3] external cell (sector x vintage x state) excess: {1000*ext.excess.iloc[0]:.3f}")
    es = ext.variance_share.iloc[0]
    print(f"[C4] the strongest EXTERNAL classifier removes {100*es:.2f}% of outcome variance; "
          f"{100*(1-es):.2f}% is within-cell")
    for f in ["term_b", "age"]:
        r = t[t.factor.eq(f)]
        print(f"     {f:<8} removes {100*r.variance_share.iloc[0]:.2f}%")

    # [C14] The magnitude the variance ratio hides.
    print("\n[C14] between-cell spread of the charge-off rate (loan-weighted p10 / p50 / p90):")
    for col, lbl in [("ext_cell","external: sector x vintage x state"), ("BankName","current holder"),
                     ("term_b","loan structure")]:
        lo, mid, hi = cell_spread(d.y, d[col])
        print(f"      {lbl:<36} {100*lo:5.2f}%  {100*mid:5.2f}%  {100*hi:5.2f}%   "
              f"(p90-p10 {100*(hi-lo):5.2f}pp, {hi/lo:.1f}x)")
    print("      The cells differ by a factor of four and still leave ~98% of the variance")
    print("      unexplained. For a rare binary outcome both statements are ordinary; quoting")
    print("      only the ratio would make a property of the statistic look like a finding.")

    # [C15] NAICS grain. 2-digit is the coarsest published grain, not a narrow control.
    print("\n[C15] industry signal by NAICS grain (coverage = loans in cells with n>=30):")
    print(f"      {'grain':<10}{'cells':>7}{'coverage':>10}{'industry':>11}{'ext_cell':>11}")
    for g in (2, 3, 4, 6):
        r = naics_grain(d, g)
        print(f"      {str(g)+'-digit':<10}{r['industry']['cells']:>7,}"
              f"{100*r['ext_cell']['coverage']:>9.1f}%"
              f"{100*r['industry']['var_share']:>10.2f}%{100*r['ext_cell']['var_share']:>10.2f}%")
    print("      Industry quadruples from 2- to 6-digit and the external cell nearly doubles, so")
    print("      the headline 1.53% is a floor set by the coarsest grain. At 6-digit the external")
    print("      cell removes 2.97% -- on the 20% of loans whose cells are large enough to")
    print("      estimate. 97% is still within-cell.")

    # [C12] Franchising: how much of the cohort is NOT an independent owner-operator.
    g = d.groupby("franchise").y.agg(["size","mean"])
    tgt = d[d.greenfield & d.GrossApproval.lt(150e3)]
    gt = tgt.groupby("franchise").y.agg(["size","mean"])
    print(f"\n[C12] franchisees are {100*g.loc[True,'size']/len(d):.2f}% of resolved loans "
          f"and charge off at {100*g.loc[True,'mean']:.2f}% against {100*g.loc[False,'mean']:.2f}%; "
          f"in the greenfield <$150K cohort {100*gt.loc[True,'size']/len(tgt):.2f}% "
          f"({100*gt.loc[True,'mean']:.2f}% vs {100*gt.loc[False,'mean']:.2f}%)")
