"""MaStateSupplementProgram."""

from programs.framework.pe_base import PolicyEngineMembersCalculator
from programs.programs.cross_white_label.ssi.base import Ssi
import programs.framework.pe_dependencies as dependency


class MaStateSupplementProgram(PolicyEngineMembersCalculator):
    program_code = "ma_ssp"
    pe_name = "ma_state_supplement"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.IsDisabledDependency,
        dependency.member.IsBlindDependency,
        dependency.member.SsiCountableResourcesDependency,
        *Ssi.pe_inputs,
    ]
    pe_outputs = [dependency.member.MaStateSupplementProgram]
