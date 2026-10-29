"""Kseitc."""

from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
import programs.framework.pe_dependencies as dependency


class Kseitc(PolicyEngineTaxUnitCalulator):
    program_code = "ks_eitc"
    pe_name = "ks_total_eitc"
    pe_inputs = [
        *dependency.eitc_inputs,
        dependency.household.KsStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.Kseitc]
