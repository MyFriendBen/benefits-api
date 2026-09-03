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
        # Unsent, this reads False for everyone and narrows the minor-child age limit. It lands
        # in the whole screen's payload, but no other program we ship reads it: SNAP does not,
        # and Medicaid's is_parent_for_medicaid_nfc deliberately leaves it out.
        dependency.member.InSecondarySchoolDependency,
        *dependency.receipt_contract,
    ]
    pe_outputs = [dependency.spm.TanfIfTakesUp]
