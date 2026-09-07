# Data provenance

Two loan-level FOIA extracts published by the U.S. Small Business Administration:

| file | coverage | rows | after cleaning |
|---|---|---|---|
| `7a_fy2010_2019.csv` | FY2010–FY2019 | 545,751 | 479,007 |
| `7a_fy2020_present.csv` | FY2020–present | 388,338 | 338,234 |

Extract as of **2026-06-30**. Field definitions are in SBA's
[7(a) and 504 FOIA data dictionary](https://data.sba.gov/sites/default/files/uploaded_resources/7a_504_foia_data_dictionary.xlsx)
(accessed 7 September 2026) — the source of the `BankName` definition that trap 1 turns on.

**SBA publishes only the current as-of snapshot of each coverage period.** Earlier as-of dates
return 404, so the public files cannot supply the two observation dates a reassignment diff needs.

| file | SHA-256 |
|---|---|
| `7a_fy2010_2019.csv` | `01a3e2c7988a6f4052e53f218a309feb2ec2fe42887bebdc0fa94ac8b1024ade` |
| `7a_fy2020_present.csv` | `6c1e9132b5141a19f82bdc8ccafb86c9a01662461cad41ddb36a3cf409d8a4fe` |

These are recorded in `EXPECTED` in `get_data.py`, which checks them on download.
`python3 data/get_data.py` downloads both and prints a SHA-256 for each. If a hash differs from the
recorded one, it warns and continues — SBA republishes these periodically, and a changed hash means
the numbers in `FINDINGS.md` may have moved. `make test` is what tells you *which* ones.
Run `python3 data/get_data.py --record` to print current hashes for updating.

## Cleaning

All of it lives in `src/build.py`, deliberately in one place:

- **Cancelled loans dropped.** `LoanStatus == "CANCLD"` means the loan was approved but never
  disbursed. 66,744 in the older file (12.2%), 50,104 in the newer (12.9%). Leaving them in would
  put non-loans in the denominator of every rate.
- **`BusinessAge` harmonised** across the two vocabularies in the FY2010–19 file — see
  [`../traps/03-businessage.md`](../traps/03-businessage.md).
- **Competing-risks fields added**: `cause` (0 censored, 1 charge-off, 2 paid in full) and
  `duration` in months, from approval to the relevant event or to the extract date.

Nothing is imputed and nothing else is dropped.

## Raw files are not committed

`data/raw/` is gitignored — the two CSVs are 436MB together (255MB + 181MB). The **harmonised panels are committed**, so
`make fast` reproduces every claim with no network access. `make all` re-downloads and rebuilds
from raw.

## Licence

These are works of the United States Government, not subject to domestic copyright protection
(17 U.S.C. §105). This repository is not affiliated with or endorsed by the SBA.
