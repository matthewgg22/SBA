"""
TRAP 1, measured.

The README used to say the reassignment rate could not be measured from public data,
because SBA publishes only the current as-of snapshot of each coverage period. That was
wrong, and finding out it was wrong is the point of this module: **the Internet Archive
has earlier snapshots.** A CDX query returns FOIA_7a_FY2010_FY2019_asof_260331.csv,
captured 17 July 2026 and still served in full.

Two snapshots three months apart give the diff that turns "uninterpretable" into a rate.

Run:  python3 -m src.reassignment          (downloads ~224MB on first run, then caches)
"""
import os, re, urllib.request
import pandas as pd

WAYBACK = ("https://web.archive.org/web/20260717201857id_/"
           "https://data.sba.gov/sites/default/files/uploaded_resources/"
           "FOIA_7a_FY2010_FY2019_asof_260331.csv")
CACHE = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "7a_2010_2019_asof_260331.csv")
CURRENT = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "7a_fy2010_2019.csv")
KEY = ["BorrName", "BorrStreet", "BorrCity", "BorrState", "ApprovalDate", "GrossApproval"]

# Expansions that make two spellings of ONE institution compare equal. Without this the
# rate is inflated by ~30% purely by SBA tidying strings between releases.
ABBR = [(r"\bFCU\b", "FEDERAL CREDIT UNION"), (r"\bCU\b", "CREDIT UNION"),
        (r"\bNA\b", "NATIONAL ASSOCIATION"), (r"\bN A\b", "NATIONAL ASSOCIATION"),
        (r"\bNATL\b", "NATIONAL"), (r"\bASSOC\b", "ASSOCIATION"), (r"\bBK\b", "BANK"),
        (r"\bCO\b", "COMPANY"), (r"\bCORP\b", "CORPORATION"),
        (r"\bINC\b", ""), (r"\bLLC\b", ""), (r"\bLP\b", ""), (r"\bTHE\b", ""),
        (r"\bOF\b", ""), (r"\bSSB\b", "BANK"), (r"\bFSB\b", "BANK"),
        (r"\bNATIONAL ASSOCIATION\b", "")]


def normalise(x):
    x = str(x).upper()
    x = x.replace("&", " AND ")          # BEFORE stripping punctuation, or it is lost
    x = re.sub(r"[^A-Z0-9 ]", " ", x)
    for a, b in ABBR:
        x = re.sub(a, b, x)
    return re.sub(r"\s+", " ", x).strip()


def fetch():
    """The archived snapshot. Auto-downloads; ~224MB, cached thereafter."""
    if not os.path.exists(CACHE):
        print("downloading the 31 Mar 2026 snapshot from the Internet Archive (~224MB)...")
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        urllib.request.urlretrieve(WAYBACK, CACHE)
    return CACHE


def available():
    """Both snapshots present? The CURRENT extract is not committed (436MB) and is
    fetched by `make data`, so this module is the one part of the repo that cannot
    run from the committed panels alone."""
    return os.path.exists(CURRENT)


def key(d):
    s = lambda c: d[c].astype(str).str.strip().str.upper().str.replace(r"\s+", " ", regex=True)
    dt = pd.to_datetime(d.ApprovalDate, errors="coerce", format="mixed").dt.strftime("%Y%m%d")
    amt = pd.to_numeric(d.GrossApproval, errors="coerce").round(0).astype("Int64").astype(str)
    return (s("BorrName") + "|" + s("BorrStreet") + "|" + s("BorrCity") + "|" +
            s("BorrState") + "|" + dt + "|" + amt)


def load_pair():
    if not available():
        raise FileNotFoundError(
            "the current FY2010-19 extract is not on disk.\n"
            "    This module needs BOTH snapshots and the raw extracts are not committed.\n"
            "    Run `make data` (or `python3 data/get_data.py`) to fetch it, then retry.")
    cols = KEY + ["BankName", "LoanStatus"]
    jun = pd.read_csv(CURRENT, usecols=cols, low_memory=False)
    mar = pd.read_csv(fetch(), low_memory=False)
    mar.columns = [c.lower() for c in mar.columns]
    mar = mar[[c.lower() for c in cols]]
    mar.columns = cols
    jun["k"], mar["k"] = key(jun), key(mar)
    # keep=False drops ambiguous keys on BOTH sides rather than matching them arbitrarily
    j = jun.drop_duplicates("k", keep=False).set_index("k")
    m = mar.drop_duplicates("k", keep=False).set_index("k")
    both = j.index.intersection(m.index)
    return j.loc[both], m.loc[both]


def run():
    j, m = load_pair()
    raw = (m.BankName.astype(str).str.strip().str.upper()
           != j.BankName.astype(str).str.strip().str.upper())
    real = m.BankName.map(normalise) != j.BankName.map(normalise)
    q = float(real.mean())
    return dict(matched=len(j), raw=int(raw.sum()), real=int(real.sum()), q=q,
                j=j, m=m, real_mask=real)


if __name__ == "__main__":
    os.makedirs("output/tables", exist_ok=True)
    r = run()
    print(f"[R1] matched across both snapshots: {r['matched']:,} loans "
          f"({100*r['matched']/545_751:.1f}% of the file)")
    print(f"[R2] BankName string differs      : {r['raw']:,}  ({100*r['raw']/r['matched']:.3f}%)")
    print(f"[R3] after normalising name forms : {r['real']:,}  ({100*r['q']:.3f}%)")
    print(f"     {r['raw']-r['real']:,} of the raw differences were one institution respelled")
    print(f"\n[R4] ONE QUARTER of holder change: {100*r['q']:.3f}%")
    print(f"     annualised at a constant rate : ~{100*(1-(1-r['q'])**4):.2f}%")
    print(f"     compounded over the file's 16 years: ~{100*(1-(1-r['q'])**64):.0f}% of loans")
    print(f"     would have changed holder at least once.\n")
    print("     THE LAST TWO LINES ARE ARITHMETIC, NOT MEASUREMENT. One quarter is one")
    print("     observation, and this one contains two lumpy events (Meadows Bank and")
    print("     LendingClub each moving ~600 loans). Treat the 0.65% as measured and the")
    print("     16-year figure as an illustration of what that rate implies if sustained.\n")
    fl = pd.DataFrame({"mar": r["m"].BankName[r["real_mask"]],
                       "jun": r["j"].BankName[r["real_mask"]]}).value_counts()
    print("[R5] largest holder changes in the quarter:")
    for (a, b), n in fl.head(8).items():
        print(f"     {n:>5,}  {a[:36]:<36} -> {b[:36]}")
    pd.DataFrame({"march_holder": r["m"].BankName, "june_holder": r["j"].BankName,
                  "changed": r["real_mask"]}).to_csv("output/tables/reassignment.csv")
