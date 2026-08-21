"""TANF."""

from programs.framework.pe_base import PolicyEngineSpmCalulator
import programs.framework.pe_dependencies as dependency


class Tanf(PolicyEngineSpmCalulator):
    program_code = "tanf"
    # The ungated output, for the same reason as Snap above.
    pe_name = "tanf_if_takes_up"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.FullTimeCollegeStudentDependency,
        # Sent here rather than per state: every state's chain reads it, and the PE variable
        # has no default, so an unsent input silently narrows the minor-child age limit.
        dependency.member.InSecondarySchoolDependency,
        *dependency.receipt_contract,
    ]
    pe_outputs = [dependency.spm.TanfIfTakesUp]
