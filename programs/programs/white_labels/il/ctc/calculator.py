"""Ilctc."""

from programs.programs.cross_white_label.ctc.base import Ctc
from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
import programs.framework.pe_dependencies as dependency


class Ilctc(PolicyEngineTaxUnitCalulator):
    program_code = "il_ctc"
    pe_name = "il_ctc"
    pe_inputs = [
        *Ctc.pe_inputs,
        dependency.household.IlStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.Ilctc]
