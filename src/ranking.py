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
           ("ApprovalFY","external: macro vintage"), ("jobs_b","firm-level")]


def resolution(y, key, minn=30):
    t = pd.DataFrame({"y": np.asarray(y), "k": np.asarray(key)})
    g = t.groupby("k", observed=True).y.agg(["size","mean"])
    g = g[g["size"] >= minn]
    if not len(g):
        return np.nan
    N = g["size"].sum(); pbar = (g["size"] * g["mean"]).sum() / N
    return float(((g["size"] / N) * (g["mean"] - pbar) ** 2).sum())


def closed_form_null(K, N, pbar):
    return (K - 1) / N * pbar * (1 - pbar)


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
        null = float(np.nanmean([resolution(rng.permutation(y), d[col]) for _ in range(draws)]))
        K = d.groupby(col, observed=True).size().pipe(lambda s: (s >= 30).sum())
        rows.append({"factor": col, "type": kind, "observed": obs, "perm_null": null,
                     "closed_form_null": closed_form_null(K, len(d), y.mean()),
                     "excess": obs - null, "cells": int(K)})
    return pd.DataFrame(rows).sort_values("excess", ascending=False)


if __name__ == "__main__":
    os.makedirs("output/tables", exist_ok=True)
    d = prep(load())
    print(f"[C1] resolved FY2010-19 loans: {len(d):,} | base charge-off {d.y.mean():.4f}")
    t = run(d)
    out = t.assign(**{k: (1000*t[k]).round(3) for k in ["observed","perm_null","closed_form_null","excess"]})
    print("\nPredictive signal, x1000 (permutation-corrected):")
    print(out[["factor","type","observed","perm_null","closed_form_null","excess","cells"]].to_string(index=False))
    t.to_csv("output/tables/ranking.csv", index=False)
    top, bot = t.iloc[0], t.iloc[-1]
    print(f"\n[C2] {top.factor} leads at {1000*top.excess:.3f}; {bot.factor} last at {1000*bot.excess:.3f} "
          f"({top.excess/bot.excess:.0f}x)")
    ext = t[t.factor.eq("ext_cell")].excess.iloc[0]
    print(f"[C3] external cell (sector x vintage x state) excess: {1000*ext:.3f}")
