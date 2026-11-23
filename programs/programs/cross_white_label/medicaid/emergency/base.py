"""Emergency Medicaid — MFB federal base."""

from typing import ClassVar

from programs.framework.base import MemberEligibility, ProgramCalculator
from screener.models import HouseholdMember


class EmergencyMedicaid(ProgramCalculator, abstract=True):
    """
    Federal Emergency Medicaid (42 U.S.C. 1396b(v), 42 CFR 435.406(b) and 440.255(c)):
    Medicaid payment for treatment of an emergency medical condition, including labor and
    delivery, for a person who would qualify for the state's Medicaid except for their
    immigration status.

    A member is eligible when they would qualify for their state's Medicaid. That result is
    computed without regard to immigration status, so this is the "eligible but for status"
    test. The other rules are enforced elsewhere:

    - immigration status: the program record's ``legal_status_required``
    - state residency: the white label

    Not evaluated, because the screener collects neither (both widen the result):

    - whether the member has an emergency medical condition
    - whether the care is related to an organ transplant

    No federal rule requires the member to be uninsured, so the base does not check it. A
    state whose own sources require it adds it in its subclass.

    Each state sets:

    - ``gates_on``: its Medicaid program code, and nothing else
    - ``state_medicaid_eligible``: ``return self.member_program_eligible("<code>", member)``,
      with the code written out. ``screener/tests/test_calc_order.py`` reads that literal
      to check the state's Medicaid is calculated first, so it must not be read off an
      attribute here.
    - ``emergency_episode_cost``: annual dollars per eligible member, the state's cited
      cost of treating one emergency episode uninsured

    Spec: program-ops ``programs/cross_white_label/medicaid/emergency/base/emergency_base_spec.md``.
    """

    emergency_episode_cost: ClassVar[int]

    def __init_subclass__(cls, abstract: bool = False, **kwargs) -> None:
        super().__init_subclass__(abstract=abstract, **kwargs)
        if abstract:
            return

        # Checked at import, which the registry does at startup, so a misconfigured state
        # fails the deploy rather than silently dropping out of results. A cost of 0 would
        # report the member eligible and then hide them: the results page drops programs
        # whose value is not above 0.
        cost = getattr(cls, "emergency_episode_cost", None)
        if not isinstance(cost, int) or cost <= 0:
            raise TypeError(f"{cls.__name__} must set emergency_episode_cost to a positive whole-dollar amount")
        if len(cls.gates_on) != 1:
            raise TypeError(f"{cls.__name__} must declare exactly its state's Medicaid program code in gates_on")
        if cls.state_medicaid_eligible is EmergencyMedicaid.state_medicaid_eligible:
            raise TypeError(f"{cls.__name__} must implement state_medicaid_eligible")

    def state_medicaid_eligible(self, member: HouseholdMember) -> bool:
        """Whether ``member`` qualifies for this state's Medicaid, immigration status aside."""
        raise NotImplementedError

    def member_eligible(self, e: MemberEligibility) -> None:
        e.condition(self.state_medicaid_eligible(e.member))

    def member_value(self, member: HouseholdMember) -> int:
        return self.emergency_episode_cost
