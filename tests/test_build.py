import pytest
from tests.conftest import need

@need
def test_cancelled_loans_are_dropped(old, new):
    assert not old.LoanStatus.eq("CANCLD").any()
    assert not new.LoanStatus.eq("CANCLD").any()

@need
def test_panel_sizes(old, new):
    assert 470_000 < len(old) < 490_000
    assert 330_000 < len(new) < 350_000

@need
def test_competing_risks_causes_are_coherent(old):
    assert set(old.cause.unique()) <= {0, 1, 2}
    assert (old.loc[old.cause == 1, "chgoff"]).all()
    assert old.loc[old.cause == 2, "LoanStatus"].eq("P I F").all()
    # 2 paid-in-full loans carry a PIF date days BEFORE disbursement - date-entry
    # noise. Pin the count and the magnitude; both are immaterial but should not grow.
    assert (old.duration < 0).sum() == 2
    assert old.duration.min() > -1.0

@need
def test_resolved_matches_cause_except_for_ten_dateless_chargeoffs(old):
    """A real quirk in the file: 10 loans carry LoanStatus == CHGOFF with no
    ChargeOffDate. They count as resolved but cannot be placed on a timeline,
    so competing-risks treats them as censored. 10 of 479,007 changes nothing,
    but pin the count so it cannot grow silently."""
    odd = old.resolved & old.cause.eq(0)
    assert odd.sum() == 10
    assert old.loc[odd, "LoanStatus"].eq("CHGOFF").all()
    assert (~old.resolved & old.cause.ne(0)).sum() == 0
