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
        # is_person_demographic_tanf_eligible reads is_in_secondary_school to pick the
        # minor-child age limit (45 CFR 260.30: 19 for a secondary student, else 18). The
        # PE variable has no default, so leaving it unsent applies the lower limit to
        # everyone and an 18-year-old student stops being a minor child. Sent here rather
        # than per state because that demographic test is in every state's chain.
        dependency.member.InSecondarySchoolDependency,
        # receipt_contract sends any reported cashAssistance amount as PE's `tanf` input,
        # which PE excludes from TANF's own unearned-income sources — right for a household
        # re-reporting the grant being recalculated, wrong for one reporting a different
        # program's cash assistance. This routes the latter to a source the gates read.
        dependency.member.NonTanfCashAssistanceIncomeDependency,
        *dependency.receipt_contract,
    ]
    pe_outputs = [dependency.spm.TanfIfTakesUp]
