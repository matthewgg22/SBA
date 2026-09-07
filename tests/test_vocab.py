"""TRAP 3. The BusinessAge vocabulary changes INSIDE the FY2010-19 file."""
import pandas as pd, pytest
from src import vocab
from tests.conftest import need, ROOT

def test_startup_is_the_only_label_shared_by_both_vocabularies():
    """Every other label is unique to one vocabulary. "Startup" is the sole
    overlap, which is why a filter written for one vocabulary still returns
    plausible-looking output on the other file - it matches on Startup and
    silently drops everything else."""
    assert set(vocab.GRADUATED) & set(vocab.COARSE) == {"Startup, Loan Funds will Open Business"}

def test_greenfield_labels_all_exist_in_crosswalk():
    assert vocab.GREENFIELD <= set(vocab.CROSSWALK.values())

def test_no_1_to_2_year_band_exists():
    """There is no [1,2) band in either vocabulary. A filter written for one
    vocabulary silently drops the other's loans - the bug this module exists for."""
    assert not any("1 year" in k.lower() and "2" in k for k in vocab.GRADUATED)

@need
def test_unknown_is_nonresponse_not_a_crosswalk_gap(old):
    """"Unknown" is 9.2% of the 2010s file. That is NOT a stale crosswalk: the
    raw values behind it are the explicit code "Unanswered" plus a few blanks.
    unmapped() below is the test that would actually catch a stale crosswalk."""
    assert 0.08 < old.age.eq("Unknown").mean() < 0.11

@need
def test_age_nonresponse_doubles_across_the_decade(old):
    """[V1] BusinessAge non-response rises 9.1% (FY2010) -> 18.7% (FY2019).
    Any share computed on this variable rests on an eroding base, and the
    erosion is concentrated in exactly the recent years most people analyse."""
    by = old.age.eq("Unknown").groupby(old.ApprovalFY).mean()
    assert by.loc[2019] > 0.17
    assert by.loc[2019] > 2 * by.loc[2013]

@need
def test_raw_labels_are_fully_mapped_if_raw_csv_is_present():
    import pathlib
    raw = ROOT/"data/raw/7a_fy2010_2019.csv"
    if not raw.exists():
        pytest.skip("raw CSV not downloaded - run `make all`")
    s = pd.read_csv(raw, usecols=["BusinessAge"], low_memory=False)["BusinessAge"]
    assert vocab.unmapped(s) == [], f"unmapped: {vocab.unmapped(s)}"

@need
def test_both_vocabularies_appear_inside_the_2010s_file(old):
    """The regression guard. The FY2010-19 file switches vocabulary partway
    through. If only one output family is ever present, the crosswalk is being
    applied to something that no longer has the split and the silent-drop bug
    could return unnoticed."""
    lab = set(old.age.dropna().unique())
    assert lab & set(vocab.GRADUATED.values()), "graduated vocabulary absent"
    assert lab & set(vocab.COARSE.values()),    "coarse vocabulary absent"

@need
def test_greenfield_share_is_about_a_quarter(old):
    """Was 14.8% under the buggy filter; 24.8% once both vocabularies are mapped."""
    assert 0.23 < old.greenfield.mean() < 0.27
