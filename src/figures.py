"""Two figures. Both are results that read better as a picture than as a table."""
import os
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from src.build import load
from src import incidence

OUT = "output/figures"
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.dpi": 150, "savefig.bbox": "tight"})


def fig_competing_risks(d):
    grid = np.arange(6, 187, 6, dtype=float)
    aj = incidence.aalen_johansen(d.duration.values, d.cause.values, grid)
    km = incidence.km_one_minus(d.duration.values, d.cause.values, grid)
    fig, ax = plt.subplots(figsize=(5.6, 3.6))
    ax.plot(grid, 100*km, lw=2, color="#c0392b", label="1 − Kaplan-Meier\n(prepayment as censoring)")
    ax.plot(grid, 100*aj, lw=2, color="#2c3e50", label="Aalen-Johansen CIF\n(prepayment as competing exit)")
    ax.fill_between(grid, 100*aj, 100*km, color="#c0392b", alpha=.10)
    i = list(grid).index(120)
    ax.annotate(f"at 120 months:\n{100*km[i]:.1f}% vs {100*aj[i]:.1f}%\noverstated by {100*(km[i]/aj[i]-1):.0f}%",
                xy=(120, 100*km[i]), xytext=(126, 8.0), fontsize=8,
                arrowprops=dict(arrowstyle="->", color="#555", lw=.8))
    ax.set_xlabel("months since approval"); ax.set_ylabel("cumulative charge-off (%)")
    ax.set_title("Prepayment is 92% of exits. Treating it as censoring\ndoubles apparent lifetime charge-off.",
                 loc="left", fontsize=10)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    fig.savefig(f"{OUT}/competing-risks.png"); plt.close(fig)
    print(f"wrote {OUT}/competing-risks.png")


def fig_never_sold(d):
    fig, ax = plt.subplots(figsize=(5.6, 3.6))
    for lbl, sub, col in [("never sold\n(n=324,191)", d[~d.sold], "#2c3e50"),
                          ("sold on the secondary\nmarket (n=104,683)", d[d.sold], "#c0392b")]:
        g = sub.groupby("BankName").chgoff.agg(["mean", "size"])
        r = 100 * g[g["size"] >= 1_000]["mean"]
        ax.hist(r, bins=np.arange(0, 46, 2.5), alpha=.62, color=col,
                label=f"{lbl}\nraw sd = {r.std():.2f}%")
    ax.set_xlabel("unadjusted holder-level charge-off rate (%), institutions with $\\geq$1,000 loans")
    ax.set_ylabel("institutions")
    ax.set_title("The 'lender effect' is reassignment. Unadjusted dispersion is\n"
                 "five times larger among loans that changed hands.", loc="left", fontsize=10)
    ax.text(0.99, 0.42, "with controls (additive fixed effects):\n3.72% vs 10.02%  [L7]",
            transform=ax.transAxes, ha="right", fontsize=7.5, color="#555")
    ax.legend(frameon=False, fontsize=8)
    fig.savefig(f"{OUT}/never-sold.png"); plt.close(fig)
    print(f"wrote {OUT}/never-sold.png")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    d = load()
    fig_competing_risks(d)
    fig_never_sold(d[d.resolved])
