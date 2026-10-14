#!/usr/bin/env python3
"""Discrimination, not variance explained: AUC for the published 7(a) covariates.

A referee objected that variance-explained measures are mechanically small for a binary
outcome at an 8% base rate, so "1.53 percent" may overread. This answers that directly.
Predictions are leave-one-out cell rates, so nothing is scored on its own outcome.

  SBA_CSV=<FOIA_7a_FY2010_FY2019.csv> python3 analysis/sba_discrimination.py
"""
import csv, collections, os, sys

CSV = os.environ.get("SBA_CSV", "data/sba/FOIA_7a_FY2010_FY2019.csv")
if not os.path.exists(CSV): sys.exit(f"missing {CSV} - set SBA_CSV")

def band(m):
    try: m = float(m)
    except Exception: return "na"
    return "<=60" if m<=60 else "61-84" if m<=84 else "85-120" if m<=120 else "121-240" if m<=240 else ">240"

loans = []
with open(CSV, newline='', encoding='utf-8', errors='replace') as f:
    for r in csv.DictReader(f):
        s = (r.get('LoanStatus') or '').strip()
        if s not in ('P I F','CHGOFF'): continue
        loans.append((1 if s=='CHGOFF' else 0, (r.get('NaicsCode') or '')[:2],
                      (r.get('ApprovalFY') or '').strip(), (r.get('BorrState') or '').strip(),
                      band(r.get('TermInMonths')), (r.get('BusinessAge') or '').strip()))
n = len(loans); base = sum(l[0] for l in loans)/n
print(f"  [D0] resolved loans {n:,}")
print(f"  [D1] base charge-off {100*base:.2f}%")

def auc(scores, ys):
    pairs = sorted(zip(scores, ys)); r = [0.0]*len(pairs); i = 0
    while i < len(pairs):
        j = i
        while j+1 < len(pairs) and pairs[j+1][0] == pairs[i][0]: j += 1
        avg = (i+j)/2.0 + 1
        for k in range(i, j+1): r[k] = avg
        i = j+1
    pos = sum(1 for _, y in pairs if y == 1); neg = len(pairs)-pos
    ssum = sum(r[k] for k, (_, y) in enumerate(pairs) if y == 1)
    return (ssum - pos*(pos+1)/2)/(pos*neg)

def loo(keyfn, tag, label):
    cells = collections.defaultdict(lambda: [0, 0])
    for l in loans:
        c = cells[keyfn(l)]; c[0] += 1; c[1] += l[0]
    sc, ys = [], []
    for l in loans:
        c = cells[keyfn(l)]
        if c[0] < 2: continue
        sc.append((c[1]-l[0])/(c[0]-1)); ys.append(l[0])
    a = auc(sc, ys)
    print(f"  [{tag}] {label:<42} AUC {a:.3f}   scored {len(sc):,}   cells {len(cells):,}")
    return a

print("\nLeave-one-out discrimination:")
loo(lambda l:(l[1],l[2],l[3]),       "D2", "sector x vintage x state")
loo(lambda l:(l[1],),                "D3", "sector alone")
loo(lambda l:(l[4],),                "D4", "term band alone")
loo(lambda l:(l[5],),                "D5", "firm age alone")
loo(lambda l:(l[1],l[2],l[3],l[4]),  "D6", "sector x vintage x state x term band")
print(f"\n  outcome variance p(1-p) = {base*(1-base):.4f}; variance-explained measures are")
print("  bounded well below 1 for a rare binary outcome, which is why AUC is reported.")
