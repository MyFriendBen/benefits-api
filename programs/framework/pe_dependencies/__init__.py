import programs.framework.pe_dependencies.member as member
import programs.framework.pe_dependencies.spm as spm
import programs.framework.pe_dependencies.tax as tax
import programs.framework.pe_dependencies.household as household

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

# The TANF income sources the screener collects beyond the taxable set.
# `irs_gross_income` is the taxable contract: child support received and alimony are not
# taxable, so they are correctly absent from it. TANF counts them anyway
# (`gov.hhs.tanf.cash.income.sources.unearned`), so a state TANF calculator sending only
# `irs_gross_income` drops them from every gate. Same shape as `wic_income` below.
#
# Alimony is here on the strength of that source list rather than a scenario: no state spec
# exercises it yet. Every field reaches PE the same way, so leaving one out keeps the same
# silent-drop bug for it that including the others fixes.
#
# Not here: workers' compensation. PolicyEngine's TANF source list does not name it, so
# sending it would be inert — see each state's spec for the disclosed treatment.
tanf_income = [
    *irs_gross_income,
    member.ChildSupportReceivedDependency,
    member.AlimonyIncomeDependency,
    member.MiscellaneousIncomeDependency,
]

# PolicyEngine's actual-receipt contract: countable income and categorical eligibility follow
# the benefits a household reports receiving, not the ones PolicyEngine simulates them as
# eligible for. See dependencies/receipt.py.
#
# Adopt it whole per calculator — suppressing one simulated benefit while leaving another just
# shifts categorical eligibility onto the phantom that remains.
#
# The version gating is deliberately mixed: the amount inputs stay ungated, since every
# supported model reads them and flooring them would withhold reported SSI/TANF from older
# ones. That is safe because the gated half is the *suppressing* half — below the floor we
# send amounts without take-up flags, never the reverse. test_pe_receipt_contract.py pins that
# direction.
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
