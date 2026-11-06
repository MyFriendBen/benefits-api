"""
Unit tests for the Emergency Medicaid base (``EmergencyMedicaid``).

Exercised through a test-only subclass that supplies what each state sets. The base spec has
no scenarios of its own (each state's spec carries them), so each rule in its sections 3, 4
and 7 gets a test here.
"""

from typing import Optional
from unittest.mock import Mock

from django.test import SimpleTestCase

from programs.framework.base import Eligibility, MemberEligibility
from programs.programs.cross_white_label.medicaid.emergency.base import EmergencyMedicaid
from programs.util import Dependencies, UpstreamAbsentError
from screener.models import HouseholdMember

EPISODE_COST = 5_000


class StateEmergencyMedicaid(EmergencyMedicaid):
    program_code = "test_emergency_medicaid"
    gates_on = ("test_medicaid",)
    emergency_episode_cost = EPISODE_COST

    def state_medicaid_eligible(self, member: HouseholdMember) -> bool:
        return self.member_program_eligible("test_medicaid", member)


def make_member(member_id: int) -> Mock:
    member = Mock()
    member.id = member_id
    return member


def medicaid_result(members: list, eligible_ids: set) -> Eligibility:
    """The state Medicaid result as the eligibility loop stores it: a verdict per member."""
    e = Eligibility()
    for member in members:
        member_e = MemberEligibility(member)
        member_e.condition(member.id in eligible_ids)
        e.add_member_eligibility(member_e)
    return e


def make_calculator(members: list, data: Optional[dict] = None) -> StateEmergencyMedicaid:
    screen = Mock()
    screen.household_members.all.return_value = members
    return StateEmergencyMedicaid(screen, Mock(), {} if data is None else data, Dependencies())


def run(calculator: EmergencyMedicaid) -> Eligibility:
    eligibility = calculator.eligible()
    calculator.value(eligibility)
    return eligibility


class TestClassAttributes(SimpleTestCase):
    def test_base_is_abstract_and_state_is_not(self):
        self.assertTrue(EmergencyMedicaid._abstract)
        self.assertFalse(StateEmergencyMedicaid._abstract)

    def test_base_declares_no_dependencies_of_its_own(self):
        """Every field comes from the state's Medicaid, through ``gates_on``."""
        self.assertEqual(tuple(EmergencyMedicaid.dependencies), ())
        self.assertEqual(EmergencyMedicaid.gates_on, ())


class TestSubclassGuards(SimpleTestCase):
    """A misconfigured state fails at import, not by vanishing from results."""

    def _define(self, **attrs) -> type:
        body = {"program_code": "test_guard", "gates_on": ("test_medicaid",), "emergency_episode_cost": 1, **attrs}
        if "state_medicaid_eligible" not in attrs:
            body["state_medicaid_eligible"] = lambda self, member: True
        return type("GuardedEmergencyMedicaid", (EmergencyMedicaid,), body)

    def test_a_complete_state_defines(self):
        self.assertFalse(self._define()._abstract)

    def test_missing_cost_raises(self):
        with self.assertRaises(TypeError):
            type(
                "NoCost",
                (EmergencyMedicaid,),
                {
                    "program_code": "test_guard",
                    "gates_on": ("test_medicaid",),
                    "state_medicaid_eligible": lambda self, member: True,
                },
            )

    def test_zero_cost_raises(self):
        """A 0 value would report the member eligible and hide them on the results page."""
        with self.assertRaises(TypeError):
            self._define(emergency_episode_cost=0)

    def test_fractional_cost_raises(self):
        """Values are serialized as whole dollars."""
        with self.assertRaises(TypeError):
            self._define(emergency_episode_cost=2_000.5)

    def test_no_gate_raises(self):
        with self.assertRaises(TypeError):
            self._define(gates_on=())

    def test_more_than_one_gate_raises(self):
        with self.assertRaises(TypeError):
            self._define(gates_on=("test_medicaid", "test_chip"))

    def test_missing_state_medicaid_check_raises(self):
        with self.assertRaises(TypeError):
            type(
                "NoCheck",
                (EmergencyMedicaid,),
                {"program_code": "test_guard", "gates_on": ("test_medicaid",), "emergency_episode_cost": 1},
            )

    def test_an_abstract_intermediate_is_not_checked(self):
        Intermediate = type("Intermediate", (EmergencyMedicaid,), {}, abstract=True)
        self.assertTrue(Intermediate._abstract)


class TestStateMedicaidEligibleButForStatus(SimpleTestCase):
    """``state_medicaid_eligible_but_for_status``, member scope."""

    def test_member_eligible_for_state_medicaid_is_eligible(self):
        parent = make_member(1)
        e = run(make_calculator([parent], {"test_medicaid": medicaid_result([parent], {1})}))

        self.assertTrue(e.eligible)
        self.assertTrue(e.eligible_members[0].eligible)

    def test_member_not_eligible_for_state_medicaid_is_not_eligible(self):
        parent = make_member(1)
        e = run(make_calculator([parent], {"test_medicaid": medicaid_result([parent], set())}))

        self.assertFalse(e.eligible)
        self.assertFalse(e.eligible_members[0].eligible)

    def test_read_per_member_not_per_household(self):
        """A parent over Medicaid's income limit with a child under it: only the child."""
        parent, child = make_member(1), make_member(2)
        e = run(make_calculator([parent, child], {"test_medicaid": medicaid_result([parent, child], {2})}))

        self.assertTrue(e.eligible)
        self.assertEqual([m.eligible for m in e.eligible_members], [False, True])

    def test_member_the_state_medicaid_did_not_evaluate_is_not_eligible(self):
        parent, child = make_member(1), make_member(2)
        e = run(make_calculator([parent, child], {"test_medicaid": medicaid_result([parent], {1})}))

        self.assertEqual([m.eligible for m in e.eligible_members], [True, False])

    def test_state_medicaid_not_calculated_raises_rather_than_reading_no(self):
        """An absent upstream drops the program from results instead of reporting it ineligible."""
        with self.assertRaises(UpstreamAbsentError):
            run(make_calculator([make_member(1)]))


class TestValue(SimpleTestCase):
    """Section 7: per member, the state's episode cost, annual."""

    def test_each_eligible_member_gets_the_episode_cost(self):
        members = [make_member(1), make_member(2), make_member(3)]
        e = run(make_calculator(members, {"test_medicaid": medicaid_result(members, {1, 3})}))

        self.assertEqual([m.value for m in e.eligible_members], [EPISODE_COST, 0, EPISODE_COST])
        self.assertEqual(e.value, 2 * EPISODE_COST)

    def test_no_household_amount(self):
        members = [make_member(1)]
        e = run(make_calculator(members, {"test_medicaid": medicaid_result(members, {1})}))

        self.assertEqual(e.household_value, 0)
        self.assertEqual(e.value, EPISODE_COST)

    def test_ineligible_household_has_no_value(self):
        members = [make_member(1)]
        e = run(make_calculator(members, {"test_medicaid": medicaid_result(members, set())}))

        self.assertEqual(e.value, 0)
