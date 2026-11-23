"""Coctc."""

from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
import programs.framework.pe_dependencies as dependency


class Coctc(PolicyEngineTaxUnitCalulator):
    program_code = "coctc"
    pe_name = "co_ctc"
    pe_inputs = [
        *dependency.ctc_inputs,
        dependency.household.CoStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.Coctc]
