#!/usr/bin/env python3
"""Does a delegation measure built from Anthropic's own artifact labels beat a hand-written one?

The delegation model's strongest term was 'verifiable', coded by keyword regex - the weakest
instrument in it. artifact_{label}_pct is Anthropic's classification of what each conversation
PRODUCED: an independent measurement of the same construct, written by someone else.

INDEX   verifiable_share = V / (V + J), from published artifact shares only.
        V  checkable against a ground truth, a spec, or execution
        J  evaluated by taste or judgement, no ground truth
        16 ambiguous labels are EXCLUDED from both rather than assigned. document_or_report
        can be a filled form or a strategy memo; assigning it would smuggle back the very
        discretion the recode exists to remove.

Data (not committed):
  AEI_CSV      release_2026_06_26/data/aei_claude_ai_2026-06-26.csv   (209MB)
  AEI_API_CSV  release_2026_06_26/data/aei_1p_api_2026-06-26.csv       (74MB, optional)
  https://huggingface.co/datasets/Anthropic/EconomicIndex

Each printed figure carries the tag used in the prose. Exits 2 if any tag was skipped.
"""
import csv, collections, statistics as st, math, os, sys, re

WEB_CSV = os.environ.get("AEI_CSV", "data/aei_claude_ai_2026-06-26.csv")
API_CSV = os.environ.get("AEI_API_CSV", "data/aei_1p_api_2026-06-26.csv")
PERIOD  = "2026-05-01"

VERIF = ['data_or_spreadsheet','sql_or_database_query','code_fix_or_debug','script_or_snippet',
         'math_or_calculation','config_or_infra','translation','chart_or_visualization']
JUDGE = ['advice_or_recommendation','plan_or_strategy','idea_or_brainstorm','creative_writing',
         'marketing_or_social_content','blog_or_article','academic_paper_or_thesis',
         'presentation_or_slides']

# Frozen keyword rules, reproduced verbatim from the pre-registered coding in the AEI working
# scripts. Retained only so the recode can be compared like-for-like against what it replaces.
LIAB  = r'contract|legal|\blaw\b|regulat|complian|\btax|grant|intellectual property|privacy|procurement|legislat|clinical|health policy|securit|vulnerab|audit|financial reporting|business registration|employee benefits|data governance|access control|building inspection|trade policy|standards|financial model|financial data|accounting|invoic|payment|capital raising|deal analysis|operational finance|payroll|order planning|candidate profile|workforce training|organizational design|leadership|business models|nominations|healthcare business'
VOICE = r'marketing|copywriting|copy editing|\bseo\b|ad campaign|campaign brief|outreach|correspondence|reply drafting|news writing|news journalism|promotion|go-to-market|pitch deck|strategy deck|subject line|push notification|milestone messaging|photography prompt|listing|local business profile|app store publishing|knowledge base authoring|ui copy|localization|specialized translation|translation review|candidate profile writing'
ENGR  = r'backend|ui behavior|architecture|\bapi\b|\bsql\b|database|pipeline|\btest|code|commit|pull request|devops|deploy|migration|distributed systems|type systems|regex|cms plugin|chatbot|observability|cloud|\borm\b|software|prompt engineering|skill file|spreadsheet ui|add-ins|agent monitoring|\bit\b|platform|json|debugging|instrumentation|data platforms|push notification|app store'
VERIF_YES = r'extract|reconcil|validat|verif|count|match|mapping|alignment|detect|triage|routing|dispatch|monitor|logging|\blogs\b|scanning|quer|lookup|\bsql\b|regex|debug|patching|\btest|deploy|migration|instrumentation|cleaning|integrity|taxonomy|classification|tagging|scoring|provisioning|administration|access control|observability|outage|anomal|record|structured data|localization|transcript|scheduled reporting|coverage analysis|inventory tracking|invoic|payroll document|logistics document|forms and documents|data and metrics|internal metrics lookup|feed performance|industrial logs|spreadsheet automation|data governance|push notification|app store publishing|database'
VERIF_NO  = r'strateg|ideation|advice|recommend|planning|\bplan\b|deck|brief|copywriting|copy editing|\bcopy\b|writing|framing|\bqa\b|coaching|leadership|organizational design|business models|\blaw\b|legal|drafting|nomination|research|intelligence|journalism|complian|regulat|\btax|grant|models|design|methodology|profession|concepts|education|analysis|analytics|policy'

def keyword_code(n):
    s = n.lower()
    return (int(bool(re.search(LIAB, s))), int(bool(re.search(VOICE, s))),
            int(bool(re.search(ENGR, s))),
            int(bool(re.search(VERIF_YES, s)) and not re.search(VERIF_NO, s)))

emitted, skipped = {}, []
def tag(t, v, f="{:.3f}"):
    emitted[t] = v
    print(f"  [{t}] {f.format(v) if isinstance(v,(int,float)) else v}")
def skip(t, why):
    skipped.append((t, why)); print(f"  [{t}] SKIPPED - {why}")

def load(path, cat, lvl):
    M = collections.defaultdict(dict)
    with open(path, newline='') as f:
        for r in csv.DictReader(f):
            if (r['geo_level']=='global' and r['category_name']==cat
                and r['hierarchy_level']==lvl and r['date_start']==PERIOD):
                try: M[r['node_name']][r['metric_id']] = float(r['value'])
                except ValueError: pass
    return M

def build(M):
    out = []
    for n, d in M.items():
        a = d.get('collaboration_bucket_automation_pct')
        if a is None: continue
        V = sum(d.get(f'artifact_{k}_pct', 0) for k in VERIF)
        J = sum(d.get(f'artifact_{k}_pct', 0) for k in JUDGE)
        if V + J < 5: continue                 # too little classified output to score
        L, Vc, E, kw = keyword_code(n)
        if d.get('human_education_years_mean') is None or d.get('pct') is None: continue
        out.append(dict(n=n, y=a, av=V/(V+J), kw=kw, L=L, V=Vc, E=E,
                        edu=d['human_education_years_mean'], p=d['pct'],
                        w=d.get('use_case_work_pct')))
    return out

def ols(rows, names):
    y = [r['y'] for r in rows]; X = [[1.0]+[float(r[k]) for k in names] for r in rows]
    n, k = len(X), len(names)+1
    XtX = [[sum(X[i][a]*X[i][b] for i in range(n)) for b in range(k)] for a in range(k)]
    Xty = [sum(X[i][a]*y[i] for i in range(n)) for a in range(k)]
    A = [XtX[i][:]+[1.0 if j==i else 0.0 for j in range(k)] for i in range(k)]
    for c in range(k):
        piv = max(range(c,k), key=lambda r_: abs(A[r_][c])); A[c], A[piv] = A[piv], A[c]
        dv = A[c][c]
        if abs(dv) < 1e-12: return None
        A[c] = [v/dv for v in A[c]]
        for r_ in range(k):
            if r_ != c and A[r_][c]:
                f = A[r_][c]; A[r_] = [a-f*b for a,b in zip(A[r_], A[c])]
    inv = [row[k:] for row in A]
    beta = [sum(inv[a][b]*Xty[b] for b in range(k)) for a in range(k)]
    fit = [sum(beta[a]*X[i][a] for a in range(k)) for i in range(n)]
    rss = sum((y[i]-fit[i])**2 for i in range(n)); my = st.mean(y)
    s2 = rss/(n-k)
    return (beta, [math.sqrt(s2*inv[a][a]) for a in range(k)],
            1 - rss/sum((v-my)**2 for v in y), n, k)

def report(rows, names, title):
    r = ols(rows, names)
    if not r: print(f"\n{title}: singular"); return None
    beta, se, r2, n, k = r; lab = ["intercept"]+names
    print(f"\n{title}   (n={n})")
    for a in range(k):
        t = beta[a]/se[a] if se[a] else float('nan')
        s = '***' if abs(t)>2.6 else ('**' if abs(t)>1.97 else ('*' if abs(t)>1.65 else ''))
        print(f"   {lab[a]:<12}{beta[a]:>9.2f}  se {se[a]:>6.2f}  t {t:>7.2f}  {s}")
    print(f"   R2 = {r2:.3f}")
    return dict(zip(lab, zip(beta, se))), r2

def pearson(xs, ys):
    mx, my = st.mean(xs), st.mean(ys)
    num = sum((a-mx)*(b-my) for a,b in zip(xs,ys))
    den = (sum((a-mx)**2 for a in xs)*sum((b-my)**2 for b in ys))**.5
    return num/den if den else float('nan')

if not os.path.exists(WEB_CSV):
    sys.exit(f"missing {WEB_CSV} - set AEI_CSV; see the docstring for the URL")

web  = build(load(WEB_CSV, 'request', '0'))
onet = build(load(WEB_CSV, 'onet', '0'))
fit  = [r for r in web if r['w'] is not None and r['w'] > 80]
MODEL = ['av','L','V','E','edu']

print("\n## Index construction")
tag("V0", len(web), "{:d}")                               # scored claude.ai topics
tag("V0b", st.median([r['av'] for r in web]))             # median index

print("\n## Construct validity vs the keyword code")
tag("V1", pearson([r['kw'] for r in web], [r['av'] for r in web]), "{:+.3f}")

print("\n## Replacement on the original fit set")
kwr = report(fit, ['kw','L','V','E','edu'], "keyword verifiable (original)")
avr = report(fit, MODEL,                    "ARTIFACT verifiable (recode)")
if kwr and avr:
    tag("V2", kwr[1]); tag("V3", avr[1])                  # R2 before / after
    tag("V4", avr[0]['av'][0])                            # artifact coefficient
    tag("V5", kwr[0]['V'][0]); tag("V6", avr[0]['V'][0])  # voice before / after
else:
    skip("V2-V6", "fit-set regression singular")

print("\n## Independence")
allr = report(web, MODEL, "all claude.ai request topics")
onr  = report(onet, MODEL, "O*NET task taxonomy (different taxonomy)")
if allr: tag("V7", allr[0]['edu'][0])                     # education, wider sample
else:    skip("V7", "full-sample regression singular")
if onr:  tag("V8", onr[0]['av'][0])                       # artifact coef, other taxonomy
else:    skip("V8", "onet regression singular")

if os.path.exists(API_CSV):
    api = build(load(API_CSV, 'request', '0'))
    apr = report(api, MODEL, "1P API population (different population)")
    if apr: tag("V9", apr[0]['av'][0])
    else:   skip("V9", "api regression singular")
else:
    skip("V9", f"{API_CSV} not present - set AEI_API_CSV")

print("\n## Shape: index quintiles vs automation")
rs = sorted(web, key=lambda r: r['av']); q = len(rs)//5
qs = []
for i in range(5):
    ch = rs[i*q:(i+1)*q] if i < 4 else rs[4*q:]
    m = st.mean(r['y'] for r in ch); qs.append(m)
    print(f"   Q{i+1}  index {st.mean(r['av'] for r in ch):.2f}   automation {m:5.1f}%   n={len(ch)}")
tag("V10", qs[3]-qs[2], "{:+.1f}")                        # the Q3->Q4 step

if skipped:
    print(f"\n{len(skipped)} tag(s) skipped:"); [print(f"  {t}: {w}") for t, w in skipped]
    sys.exit(2)
print(f"\nall {len(emitted)} tags derived")
