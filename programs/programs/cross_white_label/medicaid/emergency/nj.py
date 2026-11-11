"""NJ Medical Emergency Payment Program (MEPP) — the first state on the Emergency Medicaid base."""

from programs.framework.base import MemberEligibility
from programs.programs.cross_white_label.medicaid.emergency.base import EmergencyMedicaid
from screener.models import HouseholdMember


class NjEmergencyMedicaid(EmergencyMedicaid):
    """
    NJ's Emergency Medicaid, the Medical Emergency Payment Program (MEPP). Rules: program-ops
    ``programs/cross_white_label/medicaid/emergency/nj/emergency_nj_spec.md``.

    A member is eligible when NJ Medicaid finds them eligible (the base's "eligible but for
    status" test, read from NJ Medicaid's per-member result) and they are 19 or older: a child
    under 19 gets full NJ FamilyCare whatever their immigration status. NJ Medicaid's answer
    doesn't test the Medically Needy path, so a member who would qualify only that way is not
    shown this program.

    Immigration status is the program record's ``legal_status_required``, and residency the
    white label's. NJ's sources set no insurance rule, so none is checked. Not evaluated, because
    the screener collects none of them: an emergency medical condition, care in a hospital (or,
    for a birth, a birth center or elsewhere), and care unrelated to an organ transplant.

    The value is §7's MFB estimate: 115% of Medicare's average total payment for an
    uncomplicated vaginal delivery in NJ (N.J.S.A. 26:2H-12.52's cap on what a hospital may
    charge an uninsured resident), $8,265.30 rounded to the dollar. It is not what MEPP pays.
    """

    program_code = "nj_emergency_medicaid"
    gates_on = ("nj_medicaid",)
    dependencies = ["age"]

    emergency_episode_cost = 8_265
    min_age = 19

    def state_medicaid_eligible(self, member: HouseholdMember) -> bool:
        return self.member_program_eligible("nj_medicaid", member)

    def member_eligible(self, e: MemberEligibility) -> None:
        age = e.member.calc_age()
        e.condition(age is not None and age >= self.min_age)
        super().member_eligible(e)
