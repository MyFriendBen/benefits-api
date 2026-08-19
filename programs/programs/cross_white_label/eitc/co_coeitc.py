"""Coeitc."""

from programs.programs.cross_white_label.eitc.base import Eitc
from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
import programs.framework.pe_dependencies as dependency


class Coeitc(PolicyEngineTaxUnitCalulator):
    program_code = "coeitc"
    pe_name = "co_eitc"
    pe_inputs = [
        *Eitc.pe_inputs,
        dependency.household.CoStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.Coeitc]
