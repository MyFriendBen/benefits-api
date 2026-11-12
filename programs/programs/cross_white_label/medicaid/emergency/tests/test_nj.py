"""
Unit tests for NJ's Emergency Medicaid, the Medical Emergency Payment Program (``NjEmergencyMedicaid``).

NJ Medicaid's answer is supplied here, so these pin what NJ's class does with it: the age rule,
the per-member read and the value. The spec's Test Scenarios run against NJ Medicaid's real
PolicyEngine answer in ``test_nj_scenarios.py``.
"""

from datetime import date

from programs.framework.base import Eligibility, MemberEligibility
from programs.programs.cross_white_label.medicaid.emergency.base import EmergencyMedicaid
from programs.programs.cross_white_label.medicaid.emergency.nj import NjEmergencyMedicaid
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from programs.util import UpstreamAbsentError
from screener.models import HouseholdMember, Screen

EPISODE_COST = 8_265


def nj_medicaid_covers(*members: HouseholdMember) -> dict[str, Eligibility]:
    """NJ Medicaid's result, finding exactly ``members`` eligible."""
    result = Eligibility()
    for member in members:
        result.add_member_eligibility(MemberEligibility(member))
    return {"nj_medicaid": result}


class NjEmergencyMedicaidTestCase(CustomCalculatorTestCase):
    calculator_class = NjEmergencyMedicaid
    white_label_code = "nj"
    state_code = "NJ"
    fpl_year = "2026"
    default_zipcode = "07102"
    default_county = "Essex County"
    reference_date = date(2026, 11, 15)
    needs_program_row = False

    def eligible_ids(self, e: Eligibility) -> set[int]:
        return {member_e.member.id for member_e in e.eligible_members if member_e.eligible}


class TestNjEmergencyMedicaidClass(NjEmergencyMedicaidTestCase):
    def test_program_code(self) -> None:
        self.assertEqual(NjEmergencyMedicaid.program_code, "nj_emergency_medicaid")

    def test_is_the_base_gated_on_nj_medicaid(self) -> None:
        self.assertTrue(issubclass(NjEmergencyMedicaid, EmergencyMedicaid))
        self.assertFalse(NjEmergencyMedicaid._abstract)
        self.assertEqual(NjEmergencyMedicaid.gates_on, ("nj_medicaid",))

    def test_episode_cost_is_the_spec_figure_to_the_dollar(self) -> None:
        """§7: 1.15 × 7,187.21 = 8,265.30, rounded to whole dollars."""
        self.assertEqual(NjEmergencyMedicaid.emergency_episode_cost, EPISODE_COST)

    def test_reads_age(self) -> None:
        self.assertIn("age", NjEmergencyMedicaid.all_dependencies())


class TestNjEmergencyMedicaidAge(NjEmergencyMedicaidTestCase):
    """``age_19_or_older``: a child under 19 gets full NJ FamilyCare whatever their status."""

    def adult_aged(self, age: int) -> Eligibility:
        screen = self.make_screen()
        member = self.add_member(screen, age=age)
        return self.calculate(screen, data=nj_medicaid_covers(member))

    def test_19_is_eligible(self) -> None:
        e = self.adult_aged(19)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, EPISODE_COST)

    def test_18_is_not(self) -> None:
        e = self.adult_aged(18)
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

    def test_no_upper_age_limit(self) -> None:
        self.assertTrue(self.adult_aged(90).eligible)

    def test_age_is_judged_on_the_screening_date(self) -> None:
        """A member born in December 2007 is 18 on 2026-11-15, though 19 by year end."""
        screen = self.make_screen()
        member = self.add_member(screen, age=None, birth_year_month=date(2007, 12, 1))
        self.assertFalse(self.calculate(screen, data=nj_medicaid_covers(member)).eligible)

    def test_unknown_age_is_not_eligible(self) -> None:
        screen = self.make_screen()
        member = self.add_member(screen)
        self.set_age(member, None)
        self.assertFalse(self.calculate(screen, data=nj_medicaid_covers(member)).eligible)

    def test_a_missing_age_drops_the_program(self) -> None:
        screen = self.make_screen()
        self.add_member(screen)
        self.assertFalse(self.make_calculator(screen, missing=("age",)).can_calc())


class TestNjEmergencyMedicaidReadsNjMedicaid(NjEmergencyMedicaidTestCase):
    """``state_medicaid_eligible_but_for_status_nj``: NJ Medicaid's answer, per member."""

    def test_an_adult_nj_medicaid_finds_eligible_qualifies(self) -> None:
        screen = self.make_screen()
        head = self.add_member(screen, age=35)
        self.assertTrue(self.calculate(screen, data=nj_medicaid_covers(head)).eligible)

    def test_an_adult_nj_medicaid_turns_away_does_not(self) -> None:
        screen = self.make_screen()
        self.add_member(screen, age=40)
        e = self.calculate(screen, data=nj_medicaid_covers())
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

    def test_each_member_is_read_on_their_own(self) -> None:
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, age=30)
        spouse = self.add_member(screen, relationship="spouse", age=29, pregnant=True)

        e = self.calculate(screen, data=nj_medicaid_covers(spouse))

        self.assertEqual(self.eligible_ids(e), {spouse.id})
        self.assertNotIn(head.id, self.eligible_ids(e))
        self.assertEqual(e.value, EPISODE_COST)

    def test_a_child_nj_medicaid_covers_is_left_out(self) -> None:
        screen = self.make_screen(household_size=2)
        parent = self.add_member(screen, age=30)
        child = self.add_member(screen, relationship="child", age=17)

        e = self.calculate(screen, data=nj_medicaid_covers(parent, child))

        self.assertEqual(self.eligible_ids(e), {parent.id})
        self.assertEqual(e.value, EPISODE_COST)

    def test_each_eligible_adult_is_valued(self) -> None:
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, age=40)
        spouse = self.add_member(screen, relationship="spouse", age=38)

        e = self.calculate(screen, data=nj_medicaid_covers(head, spouse))

        self.assertEqual(e.value, 2 * EPISODE_COST)

    def test_health_insurance_does_not_matter(self) -> None:
        """NJ's sources set no insurance rule, so a member with coverage still qualifies."""
        screen = self.make_screen()
        head = self.add_member(screen, age=35)
        self.add_insurance(head, employer=True)
        self.assertTrue(self.calculate(screen, data=nj_medicaid_covers(head)).eligible)

    def test_left_out_when_nj_medicaid_was_not_calculated(self) -> None:
        screen = self.make_screen()
        self.add_member(screen, age=35)
        with self.assertRaises(UpstreamAbsentError):
            self.calculate(screen, data={})
