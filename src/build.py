"""
Raw FOIA CSV -> analysis parquet. Every cleaning decision lives here and nowhere else.

CANCLD rows are approved applications that never disbursed. They are dropped, and the
count is logged, because "934,092 loans" is a figure you get by not dropping them.
"""
import os, pandas as pd
from src.vocab import harmonise, is_greenfield, unmapped

RAW = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
OUT = os.path.join(os.path.dirname(__file__), "..", "data")
KEEP = ["ApprovalDate","ApprovalFY","GrossApproval","SBAGuaranteedApproval","BusinessAge",
        "LoanStatus","TermInMonths","BorrState","NaicsCode","BankName","ProcessingMethod",
        "JobsSupported","ChargeOffDate","PaidInFullDate","GrossChargeOffAmount","SoldSecMrktInd",
        "AsOfDate",
        "BankFDICNumber","BankNCUANumber","BankState"]
SECTOR = {"31":"31-33","32":"31-33","33":"31-33","44":"44-45","45":"44-45","48":"48-49","49":"48-49"}


def build(src, dest):
    d = pd.read_csv(os.path.join(RAW, src), low_memory=False,
                    usecols=lambda c: c in KEEP)
    n0 = len(d)
    miss = unmapped(d.BusinessAge)
    if miss:
        raise ValueError(f"BusinessAge labels not in crosswalk: {miss}")
    cancelled = int(d.LoanStatus.eq("CANCLD").sum())
    d = d[d.LoanStatus.ne("CANCLD")].copy()
    print(f"  {src}: {n0:,} rows -> {len(d):,} disbursed ({cancelled:,} CANCLD dropped, "
          f"{100*cancelled/n0:.1f}%)")

    d["age"] = harmonise(d.BusinessAge)
    d["greenfield"] = is_greenfield(d.BusinessAge)
    d["sector"] = d.NaicsCode.astype("Int64").astype(str).str[:2].replace(SECTOR)
    d["size_b"] = pd.cut(d.GrossApproval, [0,50e3,150e3,350e3,1e6,5.1e6]).astype(str)
    d["term_b"] = pd.cut(d.TermInMonths, [0,36,84,120,300]).astype(str)
    d["proc"] = d.ProcessingMethod.fillna("Unknown")
    d["resolved"] = d.LoanStatus.isin(["P I F","CHGOFF"])
    d["chgoff"] = d.LoanStatus.eq("CHGOFF")
    d["sold"] = d.SoldSecMrktInd.astype(str).str.upper().str.startswith("Y")
    d["depository"] = d.BankFDICNumber.notna() | d.BankNCUANumber.notna()
    ad = pd.to_datetime(d.ApprovalDate, errors="coerce")
    co = pd.to_datetime(d.ChargeOffDate, errors="coerce")
    pf = pd.to_datetime(d.PaidInFullDate, errors="coerce")
    asof = pd.to_datetime(d.AsOfDate, errors="coerce").max()
    d["months_to_chgoff"] = (co - ad).dt.days / 30.44
    d["months_to_pif"] = (pf - ad).dt.days / 30.44
    # duration and cause for competing-risks analysis:
    #   1 = charge-off, 2 = paid in full (absorbing competing exit), 0 = censored at as-of
    d["cause"] = 0
    d.loc[d.chgoff & co.notna(), "cause"] = 1
    d.loc[d.LoanStatus.eq("P I F") & pf.notna(), "cause"] = 2
    d["duration"] = d.months_to_chgoff.where(d.cause.eq(1),
                    d.months_to_pif.where(d.cause.eq(2), (asof - ad).dt.days / 30.44))
    d["approval_date"] = ad
    d["as_of"] = asof
    d.drop(columns=["ApprovalDate","ChargeOffDate","PaidInFullDate","AsOfDate","NaicsCode","ProcessingMethod",
                    "SoldSecMrktInd","BusinessAge"], inplace=True, errors="ignore")
    d.to_parquet(os.path.join(OUT, dest), index=False)
    print(f"  -> {dest} ({os.path.getsize(os.path.join(OUT,dest))/1e6:.1f} MB)")
    return d


def load(which="fy2010_2019"):
    return pd.read_parquet(os.path.join(OUT, f"panel_{which}.parquet"))


if __name__ == "__main__":
    print("Building analysis panels")
    build("7a_fy2010_2019.csv", "panel_fy2010_2019.parquet")
    build("7a_fy2020_present.csv", "panel_fy2020_present.parquet")
