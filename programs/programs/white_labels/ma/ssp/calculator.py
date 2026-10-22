"""MaStateSupplementProgram."""

from programs.framework.pe_base import PolicyEngineMembersCalculator
import programs.framework.pe_dependencies as dependency


class MaStateSupplementProgram(PolicyEngineMembersCalculator):
    program_code = "ma_ssp"
    pe_name = "ma_state_supplement"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.IsDisabledDependency,
        dependency.member.IsBlindDependency,
        dependency.member.SsiCountableResourcesDependency,
        *dependency.ssi_inputs,
        dependency.household.MaStateCodeDependency,
    ]
    pe_outputs = [dependency.member.MaStateSupplementProgram]
