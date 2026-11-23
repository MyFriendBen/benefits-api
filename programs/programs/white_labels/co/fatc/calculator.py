"""FamilyAffordabilityTaxCredit."""

from programs.framework.pe_base import PolicyEngineMembersCalculator
import programs.framework.pe_dependencies as dependency


class FamilyAffordabilityTaxCredit(PolicyEngineMembersCalculator):
    program_code = "fatc"
    pe_name = "co_family_affordability_credit"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.TaxUnitDependentDependency,
        dependency.household.CoStateCodeDependency,
        dependency.member.TaxUnitSpouseDependency,
        *dependency.irs_gross_income,
    ]
    pe_outputs = [dependency.member.FamilyAffordabilityTaxCredit]
