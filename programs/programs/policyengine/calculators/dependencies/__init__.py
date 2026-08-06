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

# Every source in PolicyEngine's `gov.usda.wic.income.sources` (7 CFR 246.7(d)(2)(ii)(A))
# that the screener actually collects. WIC's list is its own — it does NOT read
# `school_meal_countable_income`, and `wic_countable_income` sums these plus positive
# `capital_gains`, so a WIC calculator that sends none of them gets PE's imputation
# instead of the household's income.
#
# Eight of WIC's sources are already reached through irs_gross_income, several via PE's
# `adds` chains rather than by name — measured against the live API, each of these moves
# `wic_countable_income` by the amount sent:
#
#   employment_income, self_employment_income, rental_income, social_security,
#   unemployment_compensation  -> sent by name
#   taxable_pension_income     -> pension_income          (pension, veteran)
#   taxable_ira_distributions  -> retirement_distributions (deferredComp)
#   long_term_capital_gains    -> capital_gains            (investment)
#
# The five added here are the rest of what the screener asks about. `ssi` and `tanf` are
# WIC sources too and are dual-role: each sends the reported amount or None, leaving PE to
# compute when nothing was reported.
#
# WIC sources with no screener field, so unreachable: military_service_income,
# gi_cash_assistance, financial_assistance, strike_benefits, educational_assistance,
# railroad_benefits, disability_benefits. (veterans_benefits and survivor_benefits are
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
