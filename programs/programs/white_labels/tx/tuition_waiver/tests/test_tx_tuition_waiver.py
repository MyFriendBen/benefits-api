"""Tests for the TX State College Tuition and Fee Waiver for foster youth.

Scenarios 1–7 are the spec's §8 test scenarios, one test each
(program-ops `programs/white_labels/tx/tuition_waiver/tx_tuition_waiver_spec.md`). An eligible
member is valued at the 1-dollar sentinel; the "Varies" text comes from the program record.
"""

from programs.framework.base import Eligibility, PaymentUnit
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from programs.programs.white_labels.tx.tuition_waiver.calculator import TxTuitionWaiver
from screener.models import Screen


class TestTxTuitionWaiver(CustomCalculatorTestCase):
    calculator_class = TxTuitionWaiver
    white_label_code = "tx"
    state_code = "TX"
    default_zipcode = "78701"
    default_county = "Travis"
    needs_program_row = False

    def eligible_flags(self, e: Eligibility) -> list[bool]:
        return [m.eligible for m in e.eligible_members]

    def member_values(self, e: Eligibility) -> list[int]:
        return [m.value for m in e.eligible_members]

    def screen_of(self, household_size: int) -> Screen:
        return self.make_screen(household_size=household_size)

    # --- class attributes ---

    def test_program_code_matches_record(self) -> None:
        self.assertEqual(TxTuitionWaiver.program_code, "tx_tuition_waiver")

    def test_valued_per_member_at_the_sentinel(self) -> None:
        self.assertEqual(TxTuitionWaiver.payment_unit, PaymentUnit.MEMBER)
        self.assertEqual(TxTuitionWaiver.member_amount, 1)
        self.assertEqual(TxTuitionWaiver.amount, 0)

    def test_dependencies(self) -> None:
        self.assertEqual(TxTuitionWaiver.dependencies, ["relationship"])

    # --- spec §8 scenarios ---

    def test_scenario_1_17_year_old_who_reports_foster_care(self) -> None:
        """No minimum age: a 17-year-old who ticks the foster-care tile is shown the waiver."""
        screen = self.screen_of(1)
        self.add_member(screen, "headOfHousehold", 17, was_in_foster_care=True)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 1)

    def test_scenario_2_young_adult_never_in_foster_care(self) -> None:
        screen = self.screen_of(1)
        self.add_member(screen, "headOfHousehold", 19, monthly_income=1_200, was_in_foster_care=False)

        e = self.calculate(screen)

        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

    def test_scenario_3_former_foster_youth_aged_30(self) -> None:
        """No age-27 cutoff: the enrollment deadline is a data gap, not an age limit."""
        screen = self.screen_of(1)
        self.add_member(screen, "headOfHousehold", 30, monthly_income=2_000, was_in_foster_care=True)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 1)

    def test_scenario_4_only_a_younger_member_was_in_foster_care(self) -> None:
        """Evaluated per member, not on the head of household."""
        screen = self.screen_of(2)
        self.add_member(screen, "headOfHousehold", 45, monthly_income=3_500, was_in_foster_care=False)
        self.add_member(screen, "child", 20, was_in_foster_care=True)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(self.eligible_flags(e), [False, True])
        self.assertEqual(self.member_values(e), [0, 1])
        self.assertEqual(e.value, 1)

    def test_scenario_5_foster_child_by_relationship_tile_not_ticked(self) -> None:
        """The relationship alone qualifies; both signals aren't required."""
        screen = self.screen_of(2)
        self.add_member(screen, "headOfHousehold", 45, monthly_income=3_500, was_in_foster_care=False)
        self.add_member(screen, "fosterChild", 16, was_in_foster_care=False)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(self.eligible_flags(e), [False, True])
        self.assertEqual(e.value, 1)

    def test_scenario_6_foster_parent_and_roommate_are_not_counted(self) -> None:
        """Only the head of household is a foster youth; the foster parent and roommate aren't."""
        screen = self.screen_of(3)
        self.add_member(screen, "headOfHousehold", 19, monthly_income=1_200, was_in_foster_care=True)
        self.add_member(screen, "fosterParent", 50, monthly_income=3_500, was_in_foster_care=False)
        self.add_member(screen, "roommate", 22, monthly_income=1_500, was_in_foster_care=False)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(self.eligible_flags(e), [True, False, False])
        self.assertEqual(e.value, 1)

    def test_scenario_7_head_lists_a_foster_parent_tile_not_ticked(self) -> None:
        """A head of household who lists a foster parent counts, without the tile."""
        screen = self.screen_of(2)
        self.add_member(screen, "headOfHousehold", 18, monthly_income=900, was_in_foster_care=False)
        self.add_member(screen, "fosterParent", 50, monthly_income=3_500, was_in_foster_care=False)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(self.eligible_flags(e), [True, False])
        self.assertEqual(e.value, 1)

    # --- edges beyond the scenarios ---

    def test_each_eligible_member_gets_the_sentinel(self) -> None:
        screen = self.screen_of(3)
        self.add_member(screen, "headOfHousehold", 24, was_in_foster_care=True)
        self.add_member(screen, "fosterChild", 15, was_in_foster_care=False)
        self.add_member(screen, "sisterOrBrother", 20, was_in_foster_care=True)

        e = self.calculate(screen)

        self.assertEqual(self.member_values(e), [1, 1, 1])
        self.assertEqual(e.value, 3)

    def test_foster_parent_branch_qualifies_only_the_head(self) -> None:
        """Relationships are relative to the head, so a listed foster parent says nothing about a roommate.

        Neither member ticked the tile, so the head qualifies through this branch alone.
        """
        screen = self.screen_of(3)
        self.add_member(screen, "headOfHousehold", 20, was_in_foster_care=False)
        self.add_member(screen, "fosterParent", 55, was_in_foster_care=False)
        self.add_member(screen, "roommate", 19, was_in_foster_care=False)

        e = self.calculate(screen)

        self.assertEqual(self.eligible_flags(e), [True, False, False])
        self.assertEqual(e.value, 1)

    def test_unanswered_foster_care_tile_reads_as_no(self) -> None:
        """The tile isn't a reported-missing field, so a null answer must not qualify anyone."""
        screen = self.screen_of(1)
        self.add_member(screen, "headOfHousehold", 19, was_in_foster_care=None)

        e = self.calculate(screen)

        self.assertFalse(e.eligible)

    def test_missing_relationship_skips_the_program(self) -> None:
        screen = self.screen_of(1)
        self.add_member(screen, "headOfHousehold", 19, was_in_foster_care=True)

        calculator = self.make_calculator(screen, missing=("relationship",))

        self.assertFalse(calculator.can_calc())
