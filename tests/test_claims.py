"""
Every tagged claim in FINDINGS.md and traps/*.md is re-derived here from the panel.

These do NOT import the analysis modules' own conclusions. Where practical they
recompute the quantity a second way, so that a bug in the analysis module and a
bug in the test would have to agree to let a wrong number through.

Tolerances are set to catch a changed FINDING, not a changed rounding. If SBA
republishes the extract these will move; that is the point - the test tells you
WHICH claim moved instead of leaving stale numbers in the prose.
"""
import numpy as np, pytest
from tests.conftest import need
from src import lender, incidence

slow = pytest.mark.slow


# ---------------------------------------------------------------- TRAP 1
@need
def test_L4_holders_carry_loans_predating_their_own_existence(old):
    """The cleanest single refutation. If BankName were the originator, no bank
    could hold loans approved before the bank existed."""
    d = lender.prep(old)          # same resolved-loan base the module reports on
    for name, founded in lender.FOUNDED.items():
        sub = d[d.BankName.eq(name)]
        assert len(sub) > 1_000, f"{name} unexpectedly small"
        share = (sub.ApprovalFY < founded).mean()
        assert share > 0.25, f"{name}: only {share:.1%} predate founding"
    v = d[d.BankName.eq("VelocitySBA, LLC")]
    assert (v.ApprovalFY < 2016).mean() > 0.97      # 98.8%


@need
def test_L5_major_originators_since_acquired_are_entirely_absent(old):
    """If the field recorded who MADE the loan, a bank that originated heavily in
    the 2010s would still appear against those loans after being acquired.
    Not one of them does."""
    names = old.BankName.dropna()
    present = [n for n in lender.MERGED_AWAY
               if names.str.contains(n, regex=False).any()]
    assert present == [], f"expected none, found: {present}"
    assert len(lender.MERGED_AWAY) == 18

@need
def test_L5b_suntrust_survives_as_a_single_loan(old):
    """SunTrust was one of the largest 7(a) originators of the decade. It merged
    into Truist in 2019. Exactly one loan in 479,007 still carries the name -
    a straggler that escaped reassignment, and the clearest possible picture of
    what this field actually records."""
    n = old.BankName.dropna().str.upper().str.contains("SUNTRUST", regex=False).sum()
    assert n == 1


@need
def test_L7_dispersion_is_three_times_larger_on_loans_that_changed_hands(old):
    """The decisive test, computed here WITHOUT the backfit: raw holder-level
    charge-off dispersion, split by whether the loan was ever sold. If holder
    identity measured lending quality, the split would not matter."""
    def sd(sub):
        g = sub.groupby("BankName").chgoff.agg(["mean", "size"])
        return g[g["size"] >= 1_000]["mean"].std()
    never, sold = old[~old.sold], old[old.sold]
    assert len(never) > 300_000 and len(sold) > 100_000
    assert sd(sold) > 2.0 * sd(never), f"sold {sd(sold):.4f} vs never {sd(never):.4f}"
    assert sold.chgoff.mean() > never.chgoff.mean()


@need
def test_L6_dispersion_attenuates_in_older_vintages(old):
    """A real quality effect would be measured MORE precisely in older, fully
    resolved vintages. It is measured LESS precisely - the signature of mixing."""
    def sd(sub):
        g = sub.groupby("BankName").chgoff.agg(["mean", "size"])
        return g[g["size"] >= 200]["mean"].std()
    early = sd(old[old.ApprovalFY.isin([2010, 2011])])
    late  = sd(old[old.ApprovalFY.isin([2018, 2019])])
    assert late > 2.0 * early, f"early {early:.4f} late {late:.4f}"


# ---------------------------------------------------------------- TRAPS 2 & 4
@need
def test_C5_prepayment_dominates_resolved_exits(old):
    r = old[old.resolved]
    assert 0.90 < r.LoanStatus.eq("P I F").mean() < 0.94


@need
def test_C8_one_minus_KM_more_than_doubles_the_true_incidence(old):
    """Treating prepayment as censoring assumes prepaid borrowers were still at
    risk of charging off. They were not - they were gone."""
    grid = np.array([120.0])
    aj = incidence.aalen_johansen(old.duration.values, old.cause.values, grid)[0]
    km = incidence.km_one_minus(old.duration.values, old.cause.values, grid)[0]
    assert 0.06 < aj < 0.08
    assert 0.15 < km < 0.17
    assert km > 2.0 * aj


@need
def test_C10_the_recent_file_is_mostly_unresolved(new):
    """Why the FY2020+ extract cannot be read as an outcome file."""
    assert (~new.resolved).mean() > 0.75


# ---------------------------------------------------------------- break-even
@need
def test_B_breakeven_is_low_and_insensitive_to_the_tax_assumption():
    from src.breakeven import run, Assumptions, SCENARIOS
    bes = [run(Assumptions(eff_income_tax=r))["be_total"] for _, r in SCENARIOS]
    assert max(bes) < 0.05, "break-even should stay under 5% across the band"
    assert max(bes) - min(bes) < 0.02, "conclusion should not hinge on the tax rate"
    r = run()
    assert 7_500 < r["n"] < 8_800
    assert 0.10 < r["be_guarantee"] < 0.13


# ---------------------------------------------------------------- ranking
@need
@slow
def test_ranking_puts_loan_structure_first_and_firm_traits_last(old):
    from src.ranking import run, prep
    t = run(prep(old), draws=40, seed=7).set_index("factor")["excess"]
    assert t.idxmax() == "term_b"
    assert t["ext_cell"] > t["sector"], "sector-vintage-state cell beats sector alone"
    for weak in ["age", "size_b", "jobs_b"]:
        assert t[weak] < t["ext_cell"]
