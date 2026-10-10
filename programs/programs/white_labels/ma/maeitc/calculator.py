"""Maeitc."""

from programs.programs.cross_white_label.eitc.base import Eitc
from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
import programs.framework.pe_dependencies as dependency


class Maeitc(PolicyEngineTaxUnitCalulator):
    program_code = "ma_maeitc"
    pe_name = "ma_eitc"
    pe_inputs = [
        *Eitc.pe_inputs,
        dependency.household.MaStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.Maeitc]
