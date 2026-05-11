from programs.programs.calc import Eligibility
from screener.models import Screen, HouseholdMember

STATE_MEDICAID_OPTIONS = ("co_medicaid", "nc_medicaid", "il_medicaid")


def medicaid_eligible(data: dict[str, Eligibility]):
    for name in STATE_MEDICAID_OPTIONS:
        if name in data:
            return data[name].eligible

    return False


def snap_ineligible_student(screen: Screen, member: HouseholdMember) -> bool:

    # Step 1: Only half-time+ students are subject to the student restriction
    if not member.student:
        return False

    # Only apply part-time exemption for states that collect this field (currently NC only)
    nc_screen = screen.white_label.state_code == "NC"
    if nc_screen and member.student_full_time is False:
        return False

    # Step 2: Automatic exemptions derived from existing screener data

    # E1/E2: Age exemptions (under 18 or 50+)
    if member.age < 18 or member.age >= 50:
        return False

    # E3: Any disability type
    if member.has_disability():
        return False

    # E4: Parent (head or spouse) with a dependent child under 6
    head_or_spouse = member.is_head() or member.is_spouse()
    if head_or_spouse and screen.num_children(age_max=5) > 0:
        return False

    # E5: Single adult with child under 12
    single_parent = member.is_head() and not member.is_married()["is_married"]

    if single_parent and screen.num_children(age_max=11) > 0:
        return False

    # E6: Household currently receives TANF
    if screen.has_tanf:
        return False

    # Step 3: Employment/program exemptions (fields added in MFB-480)
    if nc_screen and (
        member.student_job_training_program or member.student_has_work_study or member.student_works_20_plus_hrs
    ):
        return False

    # Step 4: No exemption met — exclude from SNAP household
    return True
