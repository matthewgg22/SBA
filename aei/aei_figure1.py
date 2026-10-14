#!/usr/bin/env python3
"""Figure 1: binned scatter of delegation share against the artifact verifiability index.

The quintile means reported in the limitations section show a threshold rather than a
gradient. Twenty equal-count bins make the shape visible. Output: output/figure1_threshold.png

  AEI_CSV=<path to aei_claude_ai_2026-06-26.csv> python3 analysis/aei_figure1.py
"""
import csv, collections, os, sys, statistics as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CSV = os.environ.get("AEI_CSV", "data/aei_claude_ai_2026-06-26.csv")
PERIOD = "2026-05-01"
ACCENT = "#8A2432"
VERIF = ['data_or_spreadsheet','sql_or_database_query','code_fix_or_debug','script_or_snippet',
         'math_or_calculation','config_or_infra','translation','chart_or_visualization']
JUDGE = ['advice_or_recommendation','plan_or_strategy','idea_or_brainstorm','creative_writing',
         'marketing_or_social_content','blog_or_article','academic_paper_or_thesis',
         'presentation_or_slides']

if not os.path.exists(CSV): sys.exit(f"missing {CSV} - set AEI_CSV")

M = collections.defaultdict(dict)
with open(CSV, newline='') as f:
    for r in csv.DictReader(f):
        if (r['geo_level']=='global' and r['category_name']=='request'
            and r['hierarchy_level']=='0' and r['date_start']==PERIOD):
            try: M[r['node_name']][r['metric_id']] = float(r['value'])
            except ValueError: pass

pts = []
for n, d in M.items():
    a = d.get('collaboration_bucket_automation_pct')
    if a is None: continue
    V = sum(d.get(f'artifact_{k}_pct', 0) for k in VERIF)
    J = sum(d.get(f'artifact_{k}_pct', 0) for k in JUDGE)
    if V + J < 5: continue
    pts.append((V/(V+J), a))
pts.sort()
print(f"topics plotted: {len(pts)}")

NB = 20
per = len(pts)//NB
bx, by = [], []
for i in range(NB):
    ch = pts[i*per:(i+1)*per] if i < NB-1 else pts[(NB-1)*per:]
    bx.append(st.mean(p[0] for p in ch)); by.append(st.mean(p[1] for p in ch))

q = len(pts)//5
qx, qy = [], []
for i in range(5):
    ch = pts[i*q:(i+1)*q] if i < 4 else pts[4*q:]
    qx.append(st.mean(p[0] for p in ch)); qy.append(st.mean(p[1] for p in ch))
print("quintile means:", [f"{v:.1f}" for v in qy])

plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
                     "font.size": 9, "axes.linewidth": 0.8})
fig, ax = plt.subplots(figsize=(6.3, 3.4), dpi=300)
ax.step(qx, qy, where="mid", color=ACCENT, alpha=0.30, linewidth=6, solid_joinstyle="miter",
        label="Quintile averages")
ax.scatter(bx, by, s=26, color=ACCENT, zorder=3, label="Topics, grouped into twenty equal bins")
ax.axvline(0.55, color="#999999", linestyle=(0,(4,3)), linewidth=0.8, zorder=1)
ax.annotate("step at ~0.55", xy=(0.55, 41.2), xytext=(0.585, 41.2),
            fontsize=8, color="#666666", va="center")
ax.set_xlabel("Checkability of the task's output\n"
              "0 = output can only be judged          1 = output can be checked", linespacing=1.5)
ax.set_ylabel("Delegation share (%)")
ax.set_xlim(-0.03, 1.03); ax.set_ylim(39.5, 69)
ax.set_yticks([45, 50, 55, 60, 65])
ax.grid(axis="y", color="#E6E6E6", linewidth=0.7)
ax.set_axisbelow(True)
for sp in ("top","right"): ax.spines[sp].set_visible(False)
for sp in ("left","bottom"): ax.spines[sp].set_color("#555555")
ax.legend(frameon=False, loc="upper left", fontsize=8)
fig.tight_layout(pad=0.4)
os.makedirs("output", exist_ok=True)
fig.savefig("output/figure1_threshold.png", bbox_inches="tight", facecolor="white")
print("written: output/figure1_threshold.png")
