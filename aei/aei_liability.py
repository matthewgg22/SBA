#!/usr/bin/env python3
"""Re-derives Tables 2 and 3 of paper/liability-delegation-v3.docx, plus the placebo,
the month-by-month split and the bootstrap interval reported alongside them.

Companion to analysis/aei_paper.py, which derives Table 1 and the Section 4 material.
The dependent variable throughout is the Index's own collaboration_bucket_automation_pct.
Liability exposure is the keyword coding described in Section 2 of the paper; the rule is
LIAB_RE below and is identical to the one in aei_paper.py.

  AEI_CSV=<aei_claude_ai_2026-06-26.csv> python3 analysis/aei_liability.py

Each printed figure carries the tag used in the prose. Exits 2 if any tag was skipped,
so a partial run cannot be mistaken for a complete one.
"""
import csv, collections, os, sys, math, itertools, re, random, statistics as st
try:
    from scipy import stats as sps; SCIPY = True
except Exception:
    SCIPY = False

CSV = os.environ.get("AEI_CSV", "data/aei_claude_ai_2026-06-26.csv")
APR, MAY = "2026-04-01", "2026-05-01"

TABLE1 = ["Scheduled reporting","Inventory tracking","Business operational finance","Invoicing",
          "Financial reporting","Scheduling","Invoice reconciliation",
          "Regulatory compliance","Taxation"]
LIABILITY = {"Regulatory compliance","Taxation"}
LIAB_RE = r'contract|legal|\blaw\b|regulat|complian|\btax(?!onom)|grant|intellectual property|privacy|procurement|legislat|clinical|health policy|securit|vulnerab|audit|financial reporting|business registration|employee benefits|data governance|access control|building inspection|trade policy|standards|financial model|financial data|accounting|invoic|payment|capital raising|deal analysis|operational finance|payroll|order planning|candidate profile|workforce training|organizational design|leadership|business models|nominations|healthcare business'

LIAB_STRICT = r'contract|legal|\blaw\b|regulat|complian|\btax(?!onom)|intellectual property|privacy|procurement|legislat|health policy|audit|financial reporting|business registration|employee benefits|trade policy|payroll|accounting|invoic'

emitted, skipped = {}, []
def tag(t, v, f="{:.2f}"):
    emitted[t] = v
    print(f"  [{t}] {f.format(v) if isinstance(v,(int,float)) else v}")
def skip(t, why):
    skipped.append((t, why)); print(f"  [{t}] SKIPPED - {why}")

if not os.path.exists(CSV):
    sys.exit(f"missing {CSV} - set AEI_CSV; see docstring")

def load():
    M = collections.defaultdict(lambda: collections.defaultdict(dict))
    with open(CSV, newline='') as f:
        for r in csv.DictReader(f):
            if r['geo_level']=='global' and r['category_name']=='request' and r['hierarchy_level']=='0':
                try: M[r['date_start']][r['node_name']][r['metric_id']] = float(r['value'])
                except ValueError: pass
    return M
REQ = load()

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

def welch(a, b):
    if SCIPY:
        w = sps.ttest_ind(a, b, equal_var=False); return w.statistic, w.pvalue
    return float('nan'), float('nan')

# ---------------------------------------------------------------- Table 2
print("\n## Table 2: the gap under alternative samples")
D = {t: REQ[MAY][t] for t in TABLE1 if t in REQ[MAY]}
missing = [t for t in TABLE1 if t not in D]
for t in missing: skip(f"R:{t}", "topic not published")
def gap(names, weighted=False):
    A = [t for t in names if t not in LIABILITY]; B = [t for t in names if t in LIABILITY]
    def m(ts):
        if weighted:
            w = sum(D[t]['pct'] for t in ts)
            return sum(D[t]['pct']*D[t]['collaboration_bucket_automation_pct'] for t in ts)/w
        return st.mean(D[t]['collaboration_bucket_automation_pct'] for t in ts)
    return m(A), m(B), m(A)-m(B)

ALLN = [t for t in TABLE1 if t in D]
SPECS = [
    ("all",          ALLN, False),
    ("work80",       [t for t in ALLN if D[t]['use_case_work_pct'] > 80], False),
    ("nosched",      [t for t in ALLN if t != "Scheduled reporting"], False),
    ("nosched_notax",[t for t in ALLN if t not in ("Scheduled reporting","Taxation")], False),
    ("wtd",          ALLN, True),
]
for key, names, w in SPECS:
    r, l, g = gap(names, w)
    print(f"   {key:<16} routine {r:5.1f}  liability {l:5.1f}  gap {g:5.1f}")
    tag(f"R.{key}_routine", r, "{:.1f}"); tag(f"R.{key}_liab", l, "{:.1f}")
    tag(f"R.{key}_gap", g, "{:.1f}")

# ---------------------------------------------------------------- placebo & months
print("\n## Placebo over all pairs, and the two published periods")
vals = {t: D[t]['collaboration_bucket_automation_pct'] for t in ALLN}
gaps = []
for pair in itertools.combinations(ALLN, 2):
    rest = [vals[t] for t in ALLN if t not in pair]
    gaps.append((st.mean(rest) - st.mean([vals[t] for t in pair]), set(pair)))
gaps.sort(key=lambda z: -z[0])
rank = next(i+1 for i,(g,p) in enumerate(gaps) if p == LIABILITY)
tag("P.n", len(gaps), "{:.0f}"); tag("P.rank", rank, "{:.0f}")
tag("P.p", rank/len(gaps), "{:.3f}")
tag("P.median", st.median([g for g,_ in gaps]), "{:+.1f}")

for lbl, per in (("apr", APR), ("may", MAY)):
    P = REQ[per]
    av = [t for t in TABLE1 if t in P]
    if len(av) < len(TABLE1): skip(f"M.{lbl}_gap", "topic missing in period"); continue
    A = [P[t]['collaboration_bucket_automation_pct'] for t in av if t not in LIABILITY]
    B = [P[t]['collaboration_bucket_automation_pct'] for t in av if t in LIABILITY]
    tag(f"M.{lbl}_gap", st.mean(A)-st.mean(B), "{:.1f}")
    tv, pv = welch(A, B)
    if math.isnan(tv): skip(f"M.{lbl}_t", "scipy unavailable"); skip(f"M.{lbl}_p", "scipy unavailable")
    else: tag(f"M.{lbl}_t", tv); tag(f"M.{lbl}_p", pv, "{:.3f}")

print("\n## Bootstrap over tasks (10,000 resamples, seed 20260626)")
rng = random.Random(20260626)
A0 = [t for t in ALLN if t not in LIABILITY]; B0 = [t for t in ALLN if t in LIABILITY]
bs = []
for _ in range(10000):
    a = [vals[rng.choice(A0)] for _ in A0]; b = [vals[rng.choice(B0)] for _ in B0]
    bs.append(st.mean(a) - st.mean(b))
bs.sort()
tag("B.lo", bs[int(.025*len(bs))], "{:.1f}"); tag("B.hi", bs[int(.975*len(bs))-1], "{:.1f}")
tag("B.nonpos", sum(1 for g in bs if g <= 0), "{:.0f}")

# ---------------------------------------------------------------- Table 3
print("\n## Table 3: liability coefficient across the full taxonomy")
rows = []
for n, d in REQ[MAY].items():
    y = d.get('collaboration_bucket_automation_pct')
    w = d.get('use_case_work_pct'); e = d.get('human_education_years_mean')
    if y is None or w is None or e is None: continue
    rows.append(dict(n=n, y=y, w=w, edu=e, L=float(bool(re.search(LIAB_RE, n, re.I)))))
work = [r for r in rows if r['w'] > 80]
tag("G.sample_n", len(rows), "{:.0f}")
tag("G.liab_topics", sum(r['L'] for r in rows), "{:.0f}")
tag("G.work_n", len(work), "{:.0f}")
tag("G.work_mean", st.mean(r['y'] for r in work), "{:.0f}")

for key, sample, ctrl in (("all", rows, ['L']), ("allw", rows, ['L','w']),
                          ("allwe", rows, ['L','w','edu']),
                          ("w80", work, ['L']), ("w80e", work, ['L','edu'])):
    res = ols(sample, ctrl)
    if res is None: skip(f"G.{key}_b", "singular design"); continue
    beta, se, r2, n = res
    i = ctrl.index('L') + 1
    print(f"   {key:<7} b {beta[i]:7.2f}  se {se[i]:5.2f}  t {beta[i]/se[i]:6.2f}  n {n:5d}  R2 {r2:.3f}")
    tag(f"G.{key}_b", beta[i]); tag(f"G.{key}_se", se[i]); tag(f"G.{key}_t", beta[i]/se[i])
    tag(f"G.{key}_n", n, "{:.0f}"); tag(f"G.{key}_r2", r2, "{:.3f}")


# ---------------------------------------------------------------- horse race
print("\n## Does task difficulty predict delegation? (education coefficient)")
for key, sample, ctrl in (("all", rows, ['edu']), ("allL", rows, ['L','edu']),
                          ("allLw", rows, ['L','w','edu']),
                          ("w80", work, ['edu']), ("w80L", work, ['L','edu'])):
    res = ols(sample, ctrl)
    if res is None: skip(f"E.{key}_b", "singular design"); continue
    beta, se, r2, n = res
    i = ctrl.index('edu') + 1
    tag(f"E.{key}_b", beta[i]); tag(f"E.{key}_t", beta[i]/se[i]); tag(f"E.{key}_n", n, "{:.0f}")

# ---------------------------------------------------------------- artifact composition
print("\n## Does liability survive controls for artifact composition?")
VERIF = ['data_or_spreadsheet','sql_or_database_query','code_fix_or_debug','script_or_snippet',
         'math_or_calculation','config_or_infra','translation','chart_or_visualization']
JUDGE = ['advice_or_recommendation','plan_or_strategy','idea_or_brainstorm','creative_writing',
         'marketing_or_social_content','blog_or_article','academic_paper_or_thesis',
         'presentation_or_slides']
ck = []
for r in rows:
    d = REQ[MAY][r['n']]
    v = sum(d.get(f'artifact_{k}_pct', 0) for k in VERIF)
    j = sum(d.get(f'artifact_{k}_pct', 0) for k in JUDGE)
    if v + j < 5: continue
    q = dict(r); q['av'] = v / (v + j); ck.append(q)
ckw = [r for r in ck if r['w'] > 80]
tag("C.n", len(ck), "{:.0f}"); tag("C.work_n", len(ckw), "{:.0f}")
for key, sample, ctrl in (("bare", ck, ['L']), ("ck", ck, ['L','av']),
                          ("full", ck, ['L','av','w','edu']),
                          ("workfull", ckw, ['L','av','edu'])):
    res = ols(sample, ctrl)
    if res is None: skip(f"C.{key}_b", "singular design"); continue
    beta, se, r2, n = res
    i = ctrl.index('L') + 1
    print(f"   {key:<10} L {beta[i]:7.2f}  t {beta[i]/se[i]:6.2f}  n {n:5d}  R2 {r2:.3f}")
    tag(f"C.{key}_b", beta[i]); tag(f"C.{key}_se", se[i]); tag(f"C.{key}_t", beta[i]/se[i])
    tag(f"C.{key}_n", n, "{:.0f}"); tag(f"C.{key}_r2", r2, "{:.3f}")

print("\n## Standardized coefficients, full specification")
res = ols(ck, ['L','av','w','edu'])
if res is None:
    for k in ('L','av','w','edu'): skip(f"C.std_{k}", "singular design")
else:
    beta, se, r2, n = res
    sdy = st.pstdev([r['y'] for r in ck])
    for i, k in enumerate(['L','av','w','edu'], start=1):
        tag(f"C.std_{k}", beta[i] * st.pstdev([r[k] for r in ck]) / sdy, "{:+.3f}")

# ---------------------------------------------------------------- collaboration sub-modes
print("\n## Augmentation sub-modes for the nine tasks")
SUBS = ['directive','feedback_loop','task_iteration','learning','validation']
print(f"   {'task':<30}{'auto':>7}" + "".join(f"{s_[:9]:>11}" for s_ in SUBS))
for t in TABLE1:
    d = REQ[MAY].get(t)
    if not d: skip(f"S.{t}", "topic not published"); continue
    key = t.lower().replace(' ', '_')
    line = f"   {t:<30}{d['collaboration_bucket_automation_pct']:>6.1f}%"
    for s_ in SUBS:
        v = d.get(f'collaboration_{s_}_pct')
        if v is None: skip(f"S.{key}_{s_}", "sub-mode not published"); continue
        emitted[f"S.{key}_{s_}"] = v
        line += f"{v:>10.1f}%"
    print(line + ("  <- liability" if t in LIABILITY else ""))

print("\n## Strict coding: only terms carrying plain legal, tax or regulatory consequence")
for r in rows: r['Ls'] = float(bool(re.search(LIAB_STRICT, r['n'], re.I)))
strict_work = [r for r in rows if r['w'] > 80]
tag("K.strict_n", sum(r['Ls'] for r in rows), "{:.0f}")
for key, sample, ctrl in (("all", rows, ['Ls']), ("allwe", rows, ['Ls','w','edu']),
                          ("w80", strict_work, ['Ls']), ("w80e", strict_work, ['Ls','edu'])):
    res = ols(sample, ctrl)
    if res is None: skip(f"K.{key}_b", "singular design"); continue
    beta, se, r2, n = res
    i = ctrl.index('Ls') + 1
    print(f"   strict {key:<8} b {beta[i]:7.2f}  t {beta[i]/se[i]:6.2f}  n {n:5d}")
    tag(f"K.{key}_b", beta[i]); tag(f"K.{key}_t", beta[i]/se[i]); tag(f"K.{key}_n", n, "{:.0f}")

print("\n## Topics flagged by the liability rule")
flagged = sorted(r['n'] for r in rows if r['L'])
tag("K.n_flagged", len(flagged), "{:.0f}")
for i in range(0, len(flagged), 3):
    print("   " + "; ".join(flagged[i:i+3]))

print(f"\n{len(emitted)} figures emitted, {len(skipped)} skipped")
if skipped:
    for t, why in skipped: print(f"  SKIPPED {t}: {why}")
    sys.exit(2)
