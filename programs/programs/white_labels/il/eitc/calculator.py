"""Ileitc."""

from programs.programs.cross_white_label.eitc.base import Eitc
from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
import programs.framework.pe_dependencies as dependency


class Ileitc(PolicyEngineTaxUnitCalulator):
    program_code = "il_eitc"
    pe_name = "il_eitc"
    pe_inputs = [
        *Eitc.pe_inputs,
        dependency.household.IlStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.Ileitc]
