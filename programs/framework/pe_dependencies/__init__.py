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

# What a child tax credit is computed from: each member's age, the tax unit's dependent and
# spouse structure, and every IRS gross income stream. The state credits (`Coctc`, `Ilctc`)
# send this plus their state code; the federal credit is an MFB calculator and sends nothing.
ctc_inputs = [
    member.AgeDependency,
    member.TaxUnitDependentDependency,
    member.TaxUnitSpouseDependency,
    *irs_gross_income,
]

# The TANF income sources the screener collects beyond the taxable set: child support
# received, alimony, gifts (PE's `miscellaneous_income`) and non-TANF cash assistance (PE's
# `financial_assistance`). None are taxable, so `irs_gross_income` — the taxable contract —
# correctly omits all four. TANF counts them (`gov.hhs.tanf.cash.income.sources.unearned`), so
# a state TANF calculator sending only `irs_gross_income` drops them from every gate.
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
    member.NonTanfCashAssistanceIncomeDependency,
]

# The dependencies covering PolicyEngine's
# `gov.states.ma.eec.ccfa.income.countable_income.sources` that the screener collects, a
# wider base than the federal CCDF test this replaced, which read no benefit income at all.
# Veterans' benefits, military retirement pay and dividend/interest income are deliberately
# absent: the first already counts through `pension_income`, the second the screener never
# asks for, and CCFA exempts the capital gains our single `investment` stream becomes.
ma_ccfa_income = [
    member.EmploymentIncomeDependency,
    member.SelfEmploymentIncomeDependency,
    member.RentalIncomeDependency,
    member.PensionIncomeDependency,
    member.SocialSecurityIncomeDependency,
    member.UnemploymentIncomeDependency,
    member.WorkersCompensationDependency,
    member.AlimonyIncomeDependency,
    member.ChildSupportReceivedDependency,
    member.Ssi,
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

# The inputs PolicyEngine needs to model SSI for a household, for the programs whose own
# formula reads PolicyEngine's SSI (Massachusetts' state supplement and EAEDC). SSI itself is
# computed in our own code (`programs/programs/white_labels/federal/ssi`), so no calculator
# reads PolicyEngine's `ssi_if_takes_up` output.
#
# Two of these are load-bearing rather than boilerplate: `meets_ssi_disability_criteria`,
# without which a disabled non-aged, non-blind member reads as not SSI-disabled (version
# gated, so it only reaches models that define it), and `ssi_countable_resources`, the hard
# resource cutoff, which splits the household's reported assets across its adults.
ssi_inputs = [
    member.SsiCountableResourcesDependency,
    *receipt_contract,
    member.IsBlindDependency,
    member.IsDisabledDependency,
    member.MeetsSsiDisabilityCriteriaDependency,
    member.SsiEarnedIncomeDependency,
    member.SsiUnearnedIncomeDependency,
    member.AgeDependency,
    member.TaxUnitSpouseDependency,
    member.TaxUnitHeadDependency,
    member.TaxUnitDependentDependency,
]
