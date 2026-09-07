"""
BusinessAge harmonisation across the two FOIA extracts.

TRAP 3: the vocabulary is not stable. FY2010-19 uses graduated bands; FY2020-26
uses a coarse scheme. Worse, the switch happens *inside* the FY2010-19 file —
FY2019 records carry only the coarse labels, so a naive greenfield filter written
against either vocabulary silently mis-classifies most of a decade.

Two facts a user must know:
  1. FY2010-17 bands are <1yr, [2,3), [3,4), [4,5), 5+ — there is NO [1,2) band.
     A full year is missing from a two-year window, so FY2010-19 "greenfield" is
     narrower than FY2020-26 "greenfield" by construction.
  2. "Unanswered" is 8.8% of FY2010-19 against 1.1% of FY2020-26 and is folded to
     non-greenfield here. Its charge-off rate sits between the two groups, so the
     asymmetry distorts cross-file comparison. Reported, not corrected.
"""
GRADUATED = {
    "Startup, Loan Funds will Open Business": "Startup",
    "New, Less than 1 Year old":              "New (<1yr)",
    "Less than 3 years old but at least 2":   "Existing 2-3",
    "Less than 4 years old but at least 3":   "Existing 3-4",
    "Less than 5 years old but at least 4":   "Existing 4-5",
    "Existing, 5 or more years":              "Existing 5+",
}
COARSE = {
    "Startup, Loan Funds will Open Business": "Startup",
    "New Business or 2 years or less":        "New (<=2yr)",
    "Existing or more than 2 years old":      "Existing 2+",
}
SHARED = {"Change of Ownership": "Acquisition", "Unanswered": "Unknown"}
CROSSWALK = {**GRADUATED, **COARSE, **SHARED}
GREENFIELD = {"Startup", "New (<1yr)", "New (<=2yr)"}


def harmonise(series):
    """Map raw BusinessAge to the common scheme. Unmapped -> 'Unknown'."""
    return series.map(CROSSWALK).fillna("Unknown")


def is_greenfield(series):
    return harmonise(series).isin(GREENFIELD)


def unmapped(series):
    """Labels present in the data that the crosswalk does not cover."""
    return sorted(set(series.dropna().unique()) - set(CROSSWALK))
