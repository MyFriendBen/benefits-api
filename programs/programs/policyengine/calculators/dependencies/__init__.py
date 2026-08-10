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
# `irs_gross_income` already reaches eight of the sources, several through PE `adds`
# chains rather than by name. Measured against the private API (MO, pregnant adult +
# 3yo + infant), each of these moves `wic_countable_income` by the amount sent:
#
#   employment_income, self_employment_income, rental_income, social_security,
#   unemployment_compensation  -> read by name
#   taxable_pension_income     -> pension_income            (pension, veteran)
#   taxable_ira_distributions  -> retirement_distributions  (deferredComp)
#   long_term_capital_gains    -> capital_gains, a term of wic_countable_income
#
# The rest below are the remaining sources the screener asks about. `ssi` and `tanf`
# are dual-role: each sends the reported amount, or None so PE computes its own.
#
# WIC sources with no screener field, so still unreachable: military_service_income,
# gi_cash_assistance, financial_assistance, strike_benefits, educational_assistance,
# railroad_benefits, disability_benefits. (Veterans' and survivor benefits are
# collected, but reach PE folded into taxable_pension_income / social_security.)
wic_income = [
    *irs_gross_income,
    member.WorkersCompensationDependency,
    member.AlimonyIncomeDependency,
    member.MiscellaneousIncomeDependency,
    member.ChildSupportReceivedDependency,
    member.Ssi,
    spm.Tanf,
]
