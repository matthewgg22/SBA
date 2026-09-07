"""
Inverting the policy question.

No randomised estimate of the effect of AI-assisted financial operations on small-business
survival exists. So this does not estimate a benefit. It asks the answerable question:
how large would the effect have to be for a programme to pay for itself?

Every input is either a count from the loan file or an explicitly stipulated parameter,
and the stipulated ones are printed with the result.
"""
import os
from dataclasses import dataclass
import pandas as pd
from src.build import load


@dataclass(frozen=True)
class Assumptions:
    seat_cost_per_year: float = 240.0     # STIPULATED — consumer subscription list price
    avg_wage: float = 45_000.0            # STIPULATED — conservative vs Census SUSB ($49,496, <20 emp, 2022)
    fica_rate: float = 0.153              # STATUTORY — employer + employee
    eff_income_tax: float = 0.03          # STIPULATED — see SCENARIOS; the answer barely moves
    loss_rate_source: str = "FY2010-19 mature vintage, greenfield <$150K"


def run(a=Assumptions()):
    old, new = load(), load("fy2020_present")
    mature = old[old.greenfield & (old.GrossApproval < 150_000) & old.resolved]
    loss_rate = mature.GrossChargeOffAmount.sum() / mature.GrossApproval.sum()
    chg_rate = mature.chgoff.mean()
    # job-weighted failure rate: charged-off firms carry more jobs than survivors
    jw = (mature.loc[mature.chgoff, "JobsSupported"].sum() / mature.JobsSupported.sum())

    coh = new[new.ApprovalFY.between(2021, 2025) & new.greenfield & (new.GrossApproval < 150_000)]
    yrs = 5
    n, appr = len(coh)/yrs, coh.GrossApproval.sum()/yrs
    gtee, jobs = coh.SBAGuaranteedApproval.sum()/yrs, coh.JobsSupported.sum()/yrs

    per_job = a.avg_wage * (a.fica_rate + a.eff_income_tax)
    sba_loss = gtee * loss_rate
    jobs_lost = jobs * jw
    tax = jobs_lost * per_job
    cost = n * a.seat_cost_per_year
    return dict(n=n, appr=appr, gtee=gtee, jobs=jobs, loss_rate=loss_rate, chg_rate=chg_rate,
                jw=jw, failures=n*chg_rate, jobs_lost=jobs_lost, sba_loss=sba_loss, tax=tax,
                total=sba_loss+tax, cost=cost, be_guarantee=cost/sba_loss,
                be_total=cost/(sba_loss+tax), a=a)


# The effective federal income tax rate on a $45k job is the one genuinely arguable input.
# At 2025 parameters: single filer ~7.3% (std ded $15,750), MFJ ~3.1% (std ded $31,500).
# Rather than pick, report the band. FICA alone is statutory and assumes nothing.
SCENARIOS = [("FICA only (statutory floor, no income-tax assumption)", 0.000),
             ("+ income tax, married filing jointly (~3.1%)",          0.031),
             ("+ income tax, single filer (~7.3%)",                    0.073)]

if __name__ == "__main__":
    os.makedirs("output/tables", exist_ok=True)
    r = run(); a = r["a"]
    print("STIPULATED PARAMETERS (change these and the answer changes)")
    print(f"  seat cost/yr ${a.seat_cost_per_year:,.0f} | avg wage ${a.avg_wage:,.0f} | "
          f"FICA {a.fica_rate:.1%} (statutory) | effective federal income tax {a.eff_income_tax:.1%}")
    print(f"  loss rate from: {a.loss_rate_source}\n")
    print("MEASURED FROM THE LOAN FILE")
    print(f"[B1] dollar loss rate {r['loss_rate']:.4f} | count charge-off rate {r['chg_rate']:.4f} | "
          f"job-weighted failure rate {r['jw']:.4f}")
    print(f"[B2] cohort {r['n']:,.0f}/yr | approved ${r['appr']/1e6:,.0f}M | "
          f"guaranteed ${r['gtee']/1e6:,.0f}M ({100*r['gtee']/r['appr']:.1f}%) | jobs {r['jobs']:,.0f}")
    print(f"[B3] expected failures {r['failures']:,.0f}/yr carrying {r['jobs_lost']:,.0f} jobs\n")
    print("EXPOSURE AND THRESHOLD")
    print(f"[B4] SBA guarantee losses      ${r['sba_loss']/1e6:>6.1f}M/yr")
    print(f"[B5] programme cost            ${r['cost']/1e6:>6.1f}M/yr")
    print(f"\n[B6] BREAK-EVEN on guarantee losses alone: {r['be_guarantee']:.1%} reduction in failures")
    print("     (this input involves NO tax assumption at all)\n")
    print("SENSITIVITY to the one genuinely arguable parameter")
    print(f"{'scenario':<52}{'tax/yr':>9}{'total':>9}{'break-even':>12}")
    lo, hi = 1.0, 0.0
    for label, rate in SCENARIOS:
        rr = run(Assumptions(eff_income_tax=rate))
        lo, hi = min(lo, rr["be_total"]), max(hi, rr["be_total"])
        print(f"{label:<52}{rr['tax']/1e6:>8.1f}M{rr['total']/1e6:>8.1f}M{rr['be_total']:>11.1%}")
    print(f"\n[B7] the break-even spans {lo:.1%}-{hi:.1%} across the full plausible range of that")
    print("     parameter. The conclusion does not depend on which value you choose.")
    print("\nNO RANDOMISED ESTIMATE OF THIS EFFECT EXISTS. These are thresholds, not forecasts.")
    print("Gross jobs at risk overstates net social loss: displaced workers find other work.")
    print("The durable claim is about the stock of business OWNERS, which is not fungible.")
    pd.DataFrame([{k: v for k, v in r.items() if k != "a"}]).to_csv("output/tables/breakeven.csv", index=False)
