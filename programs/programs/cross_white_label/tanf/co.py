"""CO TANF."""

from programs.programs.cross_white_label.tanf.base import Tanf
import programs.framework.pe_dependencies as dependency


class CoTanf(Tanf):
    program_code = "co_tanf"
    pe_name = "co_tanf"
    pe_inputs = [
        *Tanf.pe_inputs,
        dependency.household.CoStateCodeDependency,
        dependency.member.PregnancyDependency,
        dependency.spm.CoTanfCountableGrossIncomeDependency,
        dependency.spm.CoTanfCountableGrossUnearnedIncomeDependency,
    ]

    pe_outputs = [dependency.spm.CoTanf]
