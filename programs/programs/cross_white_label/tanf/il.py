"""IL TANF."""

from programs.programs.cross_white_label.tanf.base import Tanf
import programs.framework.pe_dependencies as dependency


class IlTanf(Tanf):
    program_code = "il_tanf"
    pe_name = "il_tanf"
    pe_inputs = [
        *Tanf.pe_inputs,
        dependency.household.IlStateCodeDependency,
        dependency.spm.IlTanfCountableEarnedIncomeDependency,
        dependency.spm.IlTanfCountableGrossUnearnedIncomeDependency,
    ]

    pe_outputs = [dependency.spm.IlTanf]
