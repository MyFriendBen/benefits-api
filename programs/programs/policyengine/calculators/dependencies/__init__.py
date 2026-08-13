import programs.programs.policyengine.calculators.dependencies.member as member
import programs.programs.policyengine.calculators.dependencies.spm as spm
import programs.programs.policyengine.calculators.dependencies.tax as tax
import programs.programs.policyengine.calculators.dependencies.household as household

irs_gross_income = [
    member.EmploymentIncomeDependency,
    member.SelfEmploymentIncomeDependency,
    member.RentalIncomeDependency,
    member.PensionIncomeDependency,
    member.SocialSecurityIncomeDependency,
    member.UnemploymentIncomeDependency,
    member.InvestmentIncomeDependency,
    member.RetirementDistributionsDependency,
]

# Every variable in PolicyEngine's `gov.usda.wic.income.sources` (7 CFR 246.7(d)(2)(ii)(A))
# that the screener collects. WIC keeps its own source list and does NOT read
# `school_meal_countable_income`, so a calculator sending none of these gets PE's
# imputation instead of the household's reported income.
#
#     wic_countable_income = add(spm_unit, period, sources) + max_(0, capital_gains)
#
# Of WIC's 24 sources this reaches 13, plus the separate positive-only capital-gains
# term. Measured one field at a time against the private API: each moved
# `wic_countable_income` by the amount sent.
#
# Sent under the source's own name:
#   employment_income, self_employment_income, rental_income, social_security,
#   unemployment_compensation, ssi, tanf, workers_compensation, alimony_income,
#   miscellaneous_income (gifts), child_support_received
#
# Reached through a PE `adds` chain, so the field we send and the source differ:
#   taxable_pension_income     -> pension_income            (pension, veteran)
#   taxable_ira_distributions  -> retirement_distributions  (deferredComp)
#   long_term_capital_gains    -> capital_gains             (investment) -- the term,
#                                                           not a source; negatives clamp to 0
#
# `ssi` and `tanf` are dual-role: each sends the reported amount, or None so PE computes
# its own.
#
# The 11 sources we never populate split into three kinds:
#
#   Money we do count, just under a different source. PE keeps SSDI, SS survivor and SS
#   dependent benefits in `social_security` (which `adds` social_security_disability /
#   _survivors / _dependents / _retirement), so the screener's sSDisability, sSSurvivor
#   and sSDependent are counted there. PE's standalone `disability_benefits` and
#   `survivor_benefits` are the NON-Social-Security buckets — they are additive with
#   `social_security`, not overlapping. Likewise `veteran` income counts, but it goes out
#   as taxable_pension_income -> pension_income rather than `veterans_benefits`, and
#   `investment` counts through the capital-gains term rather than `dividend_income` /
#   `interest_income`.
#
#   Money we collect and drop. The screener's state disability types -- cOSDisability
#   (CO), stateDisability (TX/MA) and iLStateDisability (IL) -- are exactly what PE's
#   `disability_benefits` holds, and no dependency reads them, so WIC never sees that
#   income. `boarder` is the same story (it arguably belongs in rental_income). Both are
#   real undercounts, in four of the six WIC states.
#
#   Money the screener never asks about: military_service_income, gi_cash_assistance,
#   financial_assistance, strike_benefits, educational_assistance, railroad_benefits.
wic_income = [
    *irs_gross_income,
    member.WorkersCompensationDependency,
    member.AlimonyIncomeDependency,
    member.MiscellaneousIncomeDependency,
    member.ChildSupportReceivedDependency,
    member.Ssi,
    spm.Tanf,
]

# PolicyEngine's actual-receipt contract: countable income and categorical eligibility follow
# the benefits a household reports receiving, not the ones PolicyEngine simulates them as
# eligible for. See dependencies/receipt.py.
#
# Adopt it whole per calculator — suppressing one simulated benefit while leaving another just
# shifts categorical eligibility onto the phantom that remains.
#
# The version gating is deliberately mixed: the amount inputs predate the contract and stay
# ungated, so flooring them would stop sending reported SSI/TANF to older models. That is safe
# because the gated half is the *suppressing* half — below the floor we send amounts without
# take-up flags, never the reverse. test_receipt_contract.py pins that direction.
receipt_contract = [
    member.Ssi,
    member.ReceivesSsiDependency,
    member.TakesUpSsiIfEligibleDependency,
    spm.Tanf,
    spm.ReceivesTanfDependency,
    spm.TakesUpTanfIfEligibleDependency,
    spm.ReceivesSnapDependency,
    spm.TakesUpSnapIfEligibleDependency,
]
