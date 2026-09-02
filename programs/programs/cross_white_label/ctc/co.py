"""Coctc."""

from programs.programs.cross_white_label.ctc.base import Ctc
from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
import programs.framework.pe_dependencies as dependency


class Coctc(PolicyEngineTaxUnitCalulator):
    program_code = "coctc"
    pe_name = "co_ctc"
    pe_inputs = [
        *Ctc.pe_inputs,
        dependency.household.CoStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.Coctc]
