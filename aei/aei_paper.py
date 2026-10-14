#!/usr/bin/env python3
"""Re-derives every figure in paper/operational-capacity-DRAFT.docx from the AEI extract.

Companion to analysis/aei_verifiability.py, which compares the hand-coded and artifact-based
measures. This script derives what the paper itself prints: Table 1, Table 2, and the
quantities in the limitations section.

  AEI_CSV=<aei_claude_ai_2026-06-26.csv> python3 analysis/aei_paper.py
  (AEI_API_CSV optional; nothing in the current draft depends on it.)

Each printed figure carries the tag used in the prose. Exits 2 if any tag was skipped,
so a partial run cannot be mistaken for a complete one.
"""
import csv, collections, os, sys, math, itertools, re, statistics as st
try:
    from scipy import stats as sps; SCIPY = True
except Exception:
    SCIPY = False

CSV = os.environ.get("AEI_CSV", "data/aei_claude_ai_2026-06-26.csv")
APR, MAY = "2026-04-01", "2026-05-01"

VERIF = ['data_or_spreadsheet','sql_or_database_query','code_fix_or_debug','script_or_snippet',
         'math_or_calculation','config_or_infra','translation','chart_or_visualization']
JUDGE = ['advice_or_recommendation','plan_or_strategy','idea_or_brainstorm','creative_writing',
         'marketing_or_social_content','blog_or_article','academic_paper_or_thesis',
         'presentation_or_slides']
ALL16 = VERIF + JUDGE
SOFT = r'code|program|software|api|sql|database|debug|deploy|devops|git|backend|frontend|\bweb\b|app\b|script|data pipeline|ml |machine learning|cloud|server|test'

TABLE1 = ["Scheduled reporting","Inventory tracking","Business operational finance","Invoicing",
          "Financial reporting","Scheduling","Invoice reconciliation",
          "Regulatory compliance","Taxation"]
LIABILITY = {"Regulatory compliance","Taxation"}
LIAB_RE = r'contract|legal|\blaw\b|regulat|complian|\btax|grant|intellectual property|privacy|procurement|legislat|clinical|health policy|securit|vulnerab|audit|financial reporting|business registration|employee benefits|data governance|access control|building inspection|trade policy|standards|financial model|financial data|accounting|invoic|payment|capital raising|deal analysis|operational finance|payroll|order planning|candidate profile|workforce training|organizational design|leadership|business models|nominations|healthcare business'

emitted, skipped = {}, []
def tag(t, v, f="{:.2f}"):
    emitted[t] = v
    print(f"  [{t}] {f.format(v) if isinstance(v,(int,float)) else v}")
def skip(t, why):
    skipped.append((t, why)); print(f"  [{t}] SKIPPED - {why}")

if not os.path.exists(CSV):
    sys.exit(f"missing {CSV} - set AEI_CSV; see docstring")

def load(cat, lvl):
    M = collections.defaultdict(lambda: collections.defaultdict(dict))
    with open(CSV, newline='') as f:
        for r in csv.DictReader(f):
            if r['geo_level']=='global' and r['category_name']==cat and r['hierarchy_level']==lvl:
                try: M[r['date_start']][r['node_name']][r['metric_id']] = float(r['value'])
                except ValueError: pass
    return M

REQ, ONET = load('request','0'), load('onet','0')

def index(d, V=VERIF, J=JUDGE):
    v = sum(d.get(f'artifact_{k}_pct',0) for k in V)
    j = sum(d.get(f'artifact_{k}_pct',0) for k in J)
    return (v/(v+j), v+j) if v+j > 0 else (None, 0)

def panel(M, period, index_period=None, V=VERIF, J=JUDGE):
    out = []
    for n, d in M[period].items():
        y = d.get('collaboration_bucket_automation_pct'); e = d.get('human_education_years_mean')
        if y is None or e is None: continue
        src = M[index_period].get(n) if index_period else d
        if not src: continue
        av, mass = index(src, V, J)
        if av is None or mass < 5: continue
        out.append(dict(n=n, y=y, av=av, edu=e, mass=mass,
                        soft=int(bool(re.search(SOFT, n, re.I))),
                        L=int(bool(re.search(LIAB_RE, n, re.I))),
                        w=d.get('use_case_work_pct'),
                        lab={k: src.get(f'artifact_{k}_pct', 0) for k in ALL16}))
    return out

def ols(rows, names):
    y = [r['y'] for r in rows]; X = [[1.0]+[r[k] for k in names] for r in rows]
    n, k = len(X), len(names)+1
    XtX = [[sum(X[i][a]*X[i][b] for i in range(n)) for b in range(k)] for a in range(k)]
    Xty = [sum(X[i][a]*y[i] for i in range(n)) for a in range(k)]
    A = [XtX[i][:]+[1.0 if j==i else 0.0 for j in range(k)] for i in range(k)]
    for c in range(k):
        p = max(range(c,k), key=lambda r_: abs(A[r_][c])); A[c], A[p] = A[p], A[c]
        dv = A[c][c]
        if abs(dv) < 1e-12: return None
        A[c] = [v/dv for v in A[c]]
        for r_ in range(k):
            if r_ != c and A[r_][c]:
                f = A[r_][c]; A[r_] = [a-f*b for a,b in zip(A[r_], A[c])]
    inv = [row[k:] for row in A]
    beta = [sum(inv[a][b]*Xty[b] for b in range(k)) for a in range(k)]
    res = [y[i]-sum(beta[a]*X[i][a] for a in range(k)) for i in range(n)]
    rss = sum(e*e for e in res); my = st.mean(y)
    meat = [[sum(X[i][a]*X[i][b]*res[i]**2 for i in range(n)) for b in range(k)] for a in range(k)]
    tmp  = [[sum(inv[a][c]*meat[c][b] for c in range(k)) for b in range(k)] for a in range(k)]
    Vc   = [[sum(tmp[a][c]*inv[c][b] for c in range(k)) for b in range(k)] for a in range(k)]
    se = [math.sqrt(max(Vc[a][a],0)) for a in range(k)]
    return beta, se, 1-rss/sum((v-my)**2 for v in y), n

def pearson(xs, ys):
    mx, my = st.mean(xs), st.mean(ys)
    nu = sum((a-mx)*(b-my) for a,b in zip(xs,ys))
    de = (sum((a-mx)**2 for a in xs)*sum((b-my)**2 for b in ys))**.5
    return nu/de if de else float('nan')

print("\n## Table 1: the back-office task tier")
print(f"   {'task':<30}{'share':>7}{'work':>7}{'deleg':>7}{'index':>7}  liability")
dg, present = {}, []
for t in TABLE1:
    d = REQ[MAY].get(t)
    if not d: skip(f"T1:{t}", "topic not published"); continue
    av, _ = index(d)
    dg[t] = d['collaboration_bucket_automation_pct']; present.append(t)
    print(f"   {t:<30}{d['pct']:>6.2f}%{d['use_case_work_pct']:>6.1f}%"
          f"{dg[t]:>6.1f}%{av:>7.2f}  {'yes' if t in LIABILITY else 'no'}")
tag("T1.share", sum(REQ[MAY][t]['pct'] for t in present))          # tier share of usage
A = [dg[t] for t in present if t not in LIABILITY]
B = [dg[t] for t in present if t in LIABILITY]
tag("T1.routine", st.mean(A), "{:.1f}"); tag("T1.liability", st.mean(B), "{:.1f}")
if SCIPY:
    w = sps.ttest_ind(A, B, equal_var=False)
    tag("T1.welch_t", w.statistic); tag("T1.welch_p", w.pvalue, "{:.3f}")
else:
    skip("T1.welch_t", "scipy unavailable"); skip("T1.welch_p", "scipy unavailable")
ix = [index(REQ[MAY][t])[0] for t in present]
tag("T1.within_r", pearson(ix, [dg[t] for t in present]), "{:+.2f}")
ws = [REQ[MAY][t]['use_case_work_pct'] for t in present]
tag("T1.work_lo", min(ws), "{:.1f}"); tag("T1.work_hi", max(ws), "{:.1f}")
iA = [index(REQ[MAY][t])[0] for t in present if t not in LIABILITY]
iB = [index(REQ[MAY][t])[0] for t in present if t in LIABILITY]
tag("T1.index_routine", st.mean(iA)); tag("T1.index_liability", st.mean(iB))
if SCIPY:
    wi = sps.ttest_ind(iA, iB, equal_var=False)
    tag("T1.index_welch_t", wi.statistic); tag("T1.index_welch_p", wi.pvalue, "{:.3f}")
else:
    skip("T1.index_welch_t", "scipy unavailable"); skip("T1.index_welch_p", "scipy unavailable")

print("\n## Table 2: delegation share and the checkability index")
specs = [("T2.same",  "Same period",                          panel(REQ, MAY)),
         ("T2.apr",   "Index from April, delegation in May",  panel(REQ, MAY, APR)),
         ("T2.may",   "Index from May, delegation in April",  panel(REQ, APR, MAY)),
         ("T2.nosoft","Excluding software and data topics",   [r for r in panel(REQ,MAY) if not r['soft']]),
         ("T2.onet",  "O*NET task taxonomy",                  panel(ONET, MAY))]
print(f"   {'specification':<38}{'N':>6}{'coef':>8}{'se':>7}{'t':>7}{'R2':>8}")
for key, lab, rows in specs:
    r = ols(rows, ['av','edu'])
    if not r: skip(key, "singular"); continue
    beta, se, r2, n = r
    print(f"   {lab:<38}{n:>6}{beta[1]:>8.2f}{se[1]:>7.2f}{beta[1]/se[1]:>7.2f}{r2:>8.3f}")
    tag(key, beta[1])

print("\n## Limitations")
base = panel(REQ, MAY)
tag("L.mass_median", st.median([r['mass'] for r in base]), "{:.1f}")
tag("L.edu_corr", pearson([r['edu'] for r in base], [r['av'] for r in base]), "{:+.3f}")
m = ols(base, ['av','edu'])
avs = sorted(r['av'] for r in base); edus = sorted(r['edu'] for r in base)
q = lambda v,p: v[int(p*(len(v)-1))]
tag("L.iqr_index", m[0][1]*(q(avs,.75)-q(avs,.25)), "{:+.1f}")
tag("L.iqr_edu",   m[0][2]*(q(edus,.75)-q(edus,.25)), "{:+.1f}")
print("\n## Lookup against kept output")
LOOK = ['explanation_or_answer','advice_or_recommendation']
KEEP = ['data_or_spreadsheet','document_or_report','app_or_website','chart_or_visualization',
        'script_or_snippet','sql_or_database_query','presentation_or_slides','code_fix_or_debug',
        'marketing_or_social_content','email_or_message','plan_or_strategy','config_or_infra']
ov = {}
with open(CSV, newline='') as f:
    for r in csv.DictReader(f):
        if (r['geo_level']=='global' and r['category_name']=='overall'
            and r['date_start']==MAY):
            try: ov[r['metric_id']] = float(r['value'])
            except ValueError: pass
lk = sum(ov.get(f'artifact_{a}_pct',0) for a in LOOK)
kp = sum(ov.get(f'artifact_{a}_pct',0) for a in KEEP)
tag("K.baseline_ratio", kp/lk)                       # kept output : lookup, all conversations
ratios = []
for t in present:
    d = REQ[MAY][t]
    l = sum(d.get(f'artifact_{a}_pct',0) for a in LOOK)
    k = sum(d.get(f'artifact_{a}_pct',0) for a in KEEP)
    if l: ratios.append((k/l, t))
ratios.sort()
tag("K.tier_lo", ratios[0][0], "{:.1f}"); tag("K.tier_hi", ratios[-1][0], "{:.1f}")
print(f"       lowest  {ratios[0][1]} at {ratios[0][0]:.1f}")
print(f"       highest {ratios[-1][1]} at {ratios[-1][0]:.1f}")

print("\n## The contract-theory interaction")
for r in base: r['avL'] = r['av']*r['L']
work = [r for r in base if r['w'] is not None and r['w'] > 80]
for r in work: r['avL'] = r['av']*r['L']
ia = ols(base, ['av','L','avL','edu']); iw = ols(work, ['av','L','avL','edu'])
tag("X.interact_all", ia[0][3]); tag("X.interact_all_t", ia[0][3]/ia[1][3])
tag("X.slope_lo_all", ia[0][1], "{:.1f}"); tag("X.slope_hi_all", ia[0][1]+ia[0][3], "{:.1f}")
tag("X.interact_work", iw[0][3]); tag("X.interact_work_t", iw[0][3]/iw[1][3])

print("\n## Step against line")
for r in base: r['step'] = 1.0 if r['av'] >= 0.55 else 0.0
tag("D.lin_r2", ols(base, ['av','edu'])[2], "{:.3f}")
tag("D.step_r2", ols(base, ['step','edu'])[2], "{:.3f}")

print("\n## Placebo: all 6,435 label partitions (slow)")
actual = abs(m[0][1]); draws = []
pre = [(r, [r['lab'][k] for k in ALL16]) for r in base]
for combo in itertools.combinations(range(16), 8):
    sel = set(combo)
    if 0 not in sel: continue           # fix one label to a side; removes mirror duplicates
    sub = []
    for r, v in pre:
        V = sum(v[i] for i in sel); J = sum(v[i] for i in range(16) if i not in sel)
        if V+J < 5: continue
        sub.append(dict(y=r['y'], av=V/(V+J), edu=r['edu']))
    if len(sub) < 300: continue
    rr = ols(sub, ['av','edu'])
    if rr: draws.append(abs(rr[0][1]))
tag("L.placebo_n", len(draws), "{:d}")
tag("L.placebo_median", st.median(draws), "{:.1f}")
tag("L.placebo_pct", 100*sum(1 for d in draws if d >= actual)/len(draws), "{:.1f}")

if skipped:
    print(f"\n{len(skipped)} tag(s) skipped:"); [print(f"  {t}: {w}") for t, w in skipped]
    sys.exit(2)
print(f"\nall {len(emitted)} tags derived")
