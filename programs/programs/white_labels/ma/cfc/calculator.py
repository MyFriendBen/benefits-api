"""MaChildFamilyCredit."""

from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
import programs.framework.pe_dependencies as dependency


class MaChildFamilyCredit(PolicyEngineTaxUnitCalulator):
    program_code = "ma_cfc"
    pe_name = "ma_child_and_family_credit"
    pe_inputs = [
        dependency.member.TaxUnitDependentDependency,
        dependency.member.AgeDependency,
        dependency.member.IsDisabledDependency,
        dependency.household.MaStateCodeDependency,
        *dependency.irs_gross_income,
    ]
    pe_outputs = [dependency.tax.MaChildFamilyCredit]
