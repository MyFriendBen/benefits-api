from programs.programs.calc import Eligibility
from screener.models import Screen, HouseholdMember

STATE_MEDICAID_OPTIONS = ("co_medicaid", "nc_medicaid", "il_medicaid")


def medicaid_eligible(data: dict[str, Eligibility]):
    for name in STATE_MEDICAID_OPTIONS:
        if name in data:
            return data[name].eligible

    return False


def snap_ineligible_student(screen: Screen, member: HouseholdMember) -> bool:
    if not member.student:
        return False

    # Exemption 1 and 2: Age exemptions (under 18 or 50+)
    if member.age < 18 or member.age >= 50:
        return False

    # Exemption 3: Any disability type
    if member.has_disability():
        return False

    # Exemption 4: Parent (head or spouse) with a dependent child under 6
    head_or_spouse = member.is_head() or member.is_spouse()
    if head_or_spouse and screen.num_children(age_max=5) > 0:
        return False

    # Exemption 5: Single adult with child under 12
    single_parent = member.is_head() and not member.is_married()["is_married"]
    if single_parent and screen.num_children(age_max=11) > 0:
        return False

    # Exemption 6: Household currently receives TANF
    if screen.has_tanf:
        return False

    return True
