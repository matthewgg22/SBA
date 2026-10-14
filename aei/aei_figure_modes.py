#!/usr/bin/env python3
"""Figure 1: how the nine back-office tasks are worked, not just how much.

The automation share is one number; the five collaboration modes underneath it say
whether a low share means a user supervising a task or a user asking a question.
Stacking them makes the compliance-versus-tax contrast visible at a glance.
Output: output/figure_modes.png

  AEI_CSV=<path to aei_claude_ai_2026-06-26.csv> python3 analysis/aei_figure_modes.py
"""
import csv, collections, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

CSV = os.environ.get("AEI_CSV", "data/aei_claude_ai_2026-06-26.csv")
PERIOD = "2026-05-01"
ACCENT = "#8A2432"

TASKS = ["Scheduled reporting","Inventory tracking","Business operational finance","Invoicing",
         "Financial reporting","Scheduling","Invoice reconciliation",
         "Regulatory compliance","Taxation"]
LIABILITY = {"Regulatory compliance","Taxation"}
MODES = [("directive","Directive","#8A2432"),
         ("feedback_loop","Feedback loop","#B5565F"),
         ("task_iteration","Task iteration","#C9A227"),
         ("learning","Learning","#2E6E8E"),
         ("validation","Validation","#4F8F6B")]

if not os.path.exists(CSV): sys.exit(f"missing {CSV} - set AEI_CSV")

M = collections.defaultdict(dict)
with open(CSV, newline='') as f:
    for r in csv.DictReader(f):
        if (r['geo_level']=='global' and r['category_name']=='request'
            and r['hierarchy_level']=='0' and r['date_start']==PERIOD
            and r['node_name'] in TASKS):
            try: M[r['node_name']][r['metric_id']] = float(r['value'])
            except ValueError: pass

missing = [t for t in TASKS if t not in M]
if missing: sys.exit(f"topics absent from the release: {missing}")

order = sorted(TASKS, key=lambda t: M[t]['collaboration_bucket_automation_pct'])
fig, ax = plt.subplots(figsize=(7.4, 4.0))
for y, t in enumerate(order):
    left = 0.0
    for key, _, colour in MODES:
        v = M[t][f'collaboration_{key}_pct']
        ax.barh(y, v, left=left, color=colour, height=0.62,
                edgecolor="white", linewidth=0.6)
        if v >= 7:
            ax.text(left + v/2, y, f"{v:.0f}", ha="center", va="center",
                    color="white", fontsize=7.5)
        left += v

ax.set_yticks(range(len(order)))
ax.set_yticklabels([("%s  ◀" % t) if t in LIABILITY else t for t in order], fontsize=8.5)
for lab, t in zip(ax.get_yticklabels(), order):
    if t in LIABILITY: lab.set_fontweight("bold")
ax.set_xlim(0, 100); ax.set_xlabel("Share of a topic's conversations (%)", fontsize=8.5)
ax.tick_params(axis="x", labelsize=8)
ax.set_axisbelow(True); ax.xaxis.grid(True, color="#E6E0DA", linewidth=0.7)
for s in ("top","right","left"): ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color("#999999")
ax.legend(handles=[Patch(facecolor=c, label=l) for _, l, c in MODES],
          loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=5,
          frameon=False, fontsize=8)
ax.text(1.0, -0.185, "◀ carries tax or regulatory consequence",
        transform=ax.transAxes, ha="right", fontsize=7.5, color="#6B5B54")
plt.tight_layout()
os.makedirs("output", exist_ok=True)
plt.savefig("output/figure_modes.png", dpi=220, bbox_inches="tight")
print("wrote output/figure_modes.png")
for t in order:
    d = M[t]
    print(f"  {t:<30} " + "  ".join(f"{k[:4]}={d[f'collaboration_{k}_pct']:5.1f}" for k,_,_ in MODES))
