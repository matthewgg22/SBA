"""Fetch the SBA 7(a) FOIA extracts. Warns on drift, never dies."""
import hashlib, os, sys, urllib.request

BASE = "https://data.sba.gov/sites/default/files/uploaded_resources/"
FILES = {
    "7a_fy2010_2019.csv": "FOIA_7a_FY2010_FY2019_asof_260630.csv",
    "7a_fy2020_present.csv": "FOIA_7a_FY2020_Present_asof_260630.csv",
}
# SHA-256 of the as-of 2026-06-30 extracts used for every number in this repo.
EXPECTED = {
    "7a_fy2010_2019.csv": None,   # filled by --record
    "7a_fy2020_present.csv": None,
}
RAW = os.path.join(os.path.dirname(__file__), "raw")
UA = {"User-Agent": "Mozilla/5.0 (compatible; sba-7a research replication)"}


def sha256(path, buf=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(buf):
            h.update(chunk)
    return h.hexdigest()


def fetch(local, remote):
    os.makedirs(RAW, exist_ok=True)
    dest = os.path.join(RAW, local)
    if os.path.exists(dest):
        print(f"  have {local} ({os.path.getsize(dest)/1e6:.0f} MB)")
    else:
        print(f"  downloading {remote} …")
        req = urllib.request.Request(BASE + remote, headers=UA)
        with urllib.request.urlopen(req, timeout=600) as r, open(dest, "wb") as f:
            while chunk := r.read(1 << 20):
                f.write(chunk)
        print(f"  saved {local} ({os.path.getsize(dest)/1e6:.0f} MB)")
    got = sha256(dest)
    want = EXPECTED.get(local)
    if want and got != want:
        print(f"  !! HASH DRIFT for {local}\n     expected {want}\n     got      {got}\n"
              "     SBA rotates these files quarterly. Numbers in this repo were computed on the\n"
              "     as-of 2026-06-30 extract. Results may differ; the traps will not.")
    return dest, got


if __name__ == "__main__":
    print("SBA 7(a) FOIA extracts — https://data.sba.gov/dataset/7a-504-foia")
    hashes = {}
    for local, remote in FILES.items():
        _, h = fetch(local, remote)
        hashes[local] = h
    if "--record" in sys.argv:
        print("\nEXPECTED = {")
        for k, v in hashes.items():
            print(f'    "{k}": "{v}",')
        print("}")
