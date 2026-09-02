"""EITC."""

from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
import programs.framework.pe_dependencies as dependency


class Eitc(PolicyEngineTaxUnitCalulator):
    program_code = "eitc"
    pe_name = "eitc"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.TaxUnitSpouseDependency,
        dependency.member.TaxUnitDependentDependency,
        *dependency.irs_gross_income,
    ]
    pe_outputs = [dependency.tax.Eitc]
