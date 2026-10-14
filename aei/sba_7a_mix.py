"""
SBA 7(a) loan-level analysis, FY2020-FY2026 (data as of 2026-06-30).
Source: https://data.sba.gov/dataset/7a-504-foia
Question: does SBA 7(a) origination actually reach new/small businesses
whose overhead burden is the binding constraint on formation?
"""
import pandas as pd, numpy as np, os

SRC = os.environ.get("SBA_CSV")
OUT = "output"
os.makedirs(OUT, exist_ok=True)

cols = ["ApprovalFY","GrossApproval","BusinessAge","ProcessingMethod","NaicsCode",
        "NaicsDescription","LoanStatus","JobsSupported","TermInMonths","BorrState","ChargeOffDate"]
df = pd.read_csv(SRC, low_memory=False, usecols=cols)

# Cancelled applications never became loans -> exclude from "businesses reached"
df["cancelled"] = df.LoanStatus.eq("CANCLD")
loans = df[~df.cancelled].copy()

# NAICS 2-digit sector
loans["naics2"] = loans.NaicsCode.astype("Int64").astype(str).str[:2]
SECTOR = {
 "11":"Agriculture/Forestry/Fishing","21":"Mining & Oil/Gas","22":"Utilities","23":"Construction",
 "31":"Manufacturing","32":"Manufacturing","33":"Manufacturing","42":"Wholesale Trade",
 "44":"Retail Trade","45":"Retail Trade","48":"Transportation & Warehousing","49":"Transportation & Warehousing",
 "51":"Information","52":"Finance & Insurance","53":"Real Estate & Leasing",
 "54":"Professional/Scientific/Technical","55":"Mgmt of Companies",
 "56":"Administrative & Support Svcs","61":"Educational Services","62":"Health Care & Social Assistance",
 "71":"Arts/Entertainment/Recreation","72":"Accommodation & Food Services",
 "81":"Other Services","92":"Public Administration"}
loans["sector"] = loans.naics2.map(SECTOR).fillna("Unknown/Unclassified")

# Collapse business age into the analytically meaningful buckets
AGE = {"Startup, Loan Funds will Open Business":"Startup (pre-open)",
       "New Business or 2 years or less":"New (<=2 yrs)",
       "Change of Ownership":"Acquisition",
       "Existing or more than 2 years old":"Established (>2 yrs)",
       "Unanswered":"Unknown"}
loans["age"] = loans.BusinessAge.map(AGE).fillna("Unknown")
loans["greenfield"] = loans.age.isin(["Startup (pre-open)","New (<=2 yrs)"])

def tbl(g, label):
    t = g.agg(loans_n=("GrossApproval","size"),
              dollars=("GrossApproval","sum"),
              med_loan=("GrossApproval","median"),
              med_jobs=("JobsSupported","median")).sort_values("loans_n", ascending=False)
    t["pct_loans"] = 100*t.loans_n/t.loans_n.sum()
    t["pct_dollars"] = 100*t.dollars/t.dollars.sum()
    t["dollars_B"] = t.dollars/1e9
    t = t[["loans_n","pct_loans","dollars_B","pct_dollars","med_loan","med_jobs"]]
    print(f"\n{'='*78}\n{label}\n{'='*78}")
    print(t.round(1).to_string())
    return t

print(f"Records: {len(df):,} | Cancelled excluded: {df.cancelled.sum():,} | Loans analysed: {len(loans):,}")
print(f"Total approved: ${loans.GrossApproval.sum()/1e9:.1f}B  FY{loans.ApprovalFY.min()}-FY{loans.ApprovalFY.max()}")

t_age    = tbl(loans.groupby("age"), "1. BUSINESS AGE -- who actually receives 7(a) credit")
t_sector = tbl(loans.groupby("sector"), "2. INDUSTRY MIX -- all 7(a) loans by NAICS sector")
t_gf     = tbl(loans[loans.greenfield].groupby("sector"), "3. INDUSTRY MIX -- GREENFIELD ONLY (startup + <=2yrs)")

# Firm size: the "master of all trades" test
print(f"\n{'='*78}\n4. FIRM SIZE (JobsSupported) -- is the owner doing the admin?\n{'='*78}")
for lbl, sub in [("All loans", loans), ("Greenfield", loans[loans.greenfield]),
                 ("Established", loans[loans.age=='Established (>2 yrs)']),
                 ("Acquisition", loans[loans.age=='Acquisition'])]:
    j = sub.JobsSupported
    print(f"{lbl:<14} n={len(sub):>7,}  median={j.median():>5.1f}  "
          f"pct<=5 jobs={100*(j<=5).mean():>5.1f}%  pct<=10={100*(j<=10).mean():>5.1f}%  "
          f"med loan=${sub.GrossApproval.median():>9,.0f}")

# Trend
print(f"\n{'='*78}\n5. TREND -- greenfield share of originations by fiscal year\n{'='*78}")
tr = loans.groupby("ApprovalFY").agg(n=("GrossApproval","size"),
        gf_n=("greenfield","sum"), dollars=("GrossApproval","sum"))
tr["gf_pct_loans"] = 100*tr.gf_n/tr.n
gfd = loans[loans.greenfield].groupby("ApprovalFY").GrossApproval.sum()
tr["gf_pct_dollars"] = 100*gfd/tr.dollars
tr["dollars_B"] = tr.dollars/1e9
print(tr[["n","dollars_B","gf_pct_loans","gf_pct_dollars"]].round(1).to_string())

# Loan size bands -- where the small-loan volume is
print(f"\n{'='*78}\n6. LOAN SIZE BANDS\n{'='*78}")
bands = [0,25e3,50e3,150e3,350e3,1e6,5.1e6]
lbls = ["<25K","25-50K","50-150K","150-350K","350K-1M","1M-5M"]
loans["band"] = pd.cut(loans.GrossApproval, bands, labels=lbls)
b = loans.groupby("band", observed=True).agg(n=("GrossApproval","size"), d=("GrossApproval","sum"),
        jobs=("JobsSupported","median"), gf=("greenfield","mean"))
b["pct_loans"]=100*b.n/b.n.sum(); b["pct_dollars"]=100*b.d/b.d.sum(); b["gf_pct"]=100*b.gf
print(b[["n","pct_loans","pct_dollars","jobs","gf_pct"]].round(1).to_string())

# Top granular industries among greenfield
print(f"\n{'='*78}\n7. TOP 25 GREENFIELD INDUSTRIES (6-digit NAICS)\n{'='*78}")
top = (loans[loans.greenfield].groupby("NaicsDescription")
        .agg(n=("GrossApproval","size"), med=("GrossApproval","median"), jobs=("JobsSupported","median"))
        .sort_values("n", ascending=False).head(25))
top["pct_of_greenfield"] = 100*top.n/loans.greenfield.sum()
print(top.round(1).to_string())

# Charge-off -- heavily censored, report with caveat
print(f"\n{'='*78}\n8. CHARGE-OFF RATE by business age (resolved loans only)\n{'='*78}")
res = loans[loans.LoanStatus.isin(["P I F","CHGOFF"])]
co = res.groupby("age").agg(resolved=("LoanStatus","size"),
        chgoff=("LoanStatus", lambda s:(s=="CHGOFF").sum()))
co["chgoff_rate_pct"] = 100*co.chgoff/co.resolved
print(co.round(2).to_string())
print(f"\nNOTE: {100*loans.LoanStatus.eq('EXEMPT').mean():.0f}% of loans are status EXEMPT "
      "(open loans withheld under FOIA exemption). Resolved-loan rates are\n"
      "      biased toward older cohorts and short-term loans. Directional only.")

for name, t in [("business_age",t_age),("sector_all",t_sector),("sector_greenfield",t_gf)]:
    t.to_csv(f"{OUT}/{name}.csv")
loans.to_pickle(f"{OUT}/loans.pkl")
print(f"\nSaved tables to {OUT}/")
