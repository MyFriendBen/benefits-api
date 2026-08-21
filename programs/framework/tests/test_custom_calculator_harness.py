"""The custom-calculator fixture builds what a calculator reads.

`CustomCalculatorTestCase` and its builders are shared scaffolding, so a mistake in them
surfaces as a confusing failure in whichever program's suite adopted them next. These
pin the parts a calculator actually depends on: the one-to-one rows that raise when
absent, the fields FPL lookups read, and the two entry points a test calls.
"""

from unittest.mock import Mock

from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator
from screener.models import Insurance
from programs.programs.testing_fixtures.custom_calculator import (
    CustomCalculatorTestCase,
    add_expense,
    add_income,
    add_insurance,
)


class _Uninsured(ProgramCalculator):
    """Reads `member.insurance`, which raises unless the builder created the row."""

    program_code = "test_uninsured"
    member_amount = 100

    def member_eligible(self, e: MemberEligibility):
        e.condition(e.member.insurance.none)


class _OverFpl(ProgramCalculator):
    """Reads `program.year`, which needs a saved `Program` carrying an FPL row."""

    program_code = "test_over_fpl"
    fpl_percent = 1.0
    amount = 50

    def household_eligible(self, e: Eligibility):
        limit = self.program.year.get_limit(self.screen.household_size)
        e.condition(self.screen.calc_gross_income("yearly", ["all"]) <= limit)

    def household_value(self):
        return self.amount


class TestMemberBuilders(CustomCalculatorTestCase):
    calculator_class = _Uninsured
    program_code = "test_uninsured"

    def test_a_new_member_comes_with_an_uninsured_record(self):
        """`member.insurance` raises RelatedObjectDoesNotExist without this row."""
        member = self.add_member(self.make_screen())

        self.assertTrue(member.insurance.none)

    def test_add_insurance_replaces_the_default_record(self):
        member = self.add_member(self.make_screen())

        add_insurance(member, medicaid=True, none=False)

        member.refresh_from_db()
        self.assertTrue(member.insurance.medicaid)
        self.assertFalse(member.insurance.none)

    def test_add_insurance_leaves_one_record_per_member(self):
        """The relation is one-to-one; a second row would make `member.insurance` raise."""
        member = self.add_member(self.make_screen())

        add_insurance(member, medicaid=True, none=False)

        self.assertEqual(Insurance.objects.filter(household_member=member).count(), 1)

    def test_an_uninsured_member_is_paid(self):
        screen = self.make_screen()
        self.add_member(screen)

        self.assertEqual(self.calculate(screen).value, _Uninsured.member_amount)

    def test_an_insured_member_is_not_paid(self):
        screen = self.make_screen()
        add_insurance(self.add_member(screen), medicaid=True, none=False)

        self.assertEqual(self.calculate(screen).value, 0)


class TestIncomeAndExpenseBuilders(CustomCalculatorTestCase):
    calculator_class = _OverFpl
    program_code = "test_over_fpl"

    def test_income_is_annualized_by_frequency(self):
        """A monthly amount counts twelve times, so the builder must not pre-annualize."""
        screen = self.make_screen(household_size=1)
        add_income(self.add_member(screen), 1_000, frequency="monthly")

        self.assertEqual(int(screen.calc_gross_income("yearly", ["all"])), 12_000)

    def test_the_program_row_supplies_an_fpl_limit(self):
        """`program.year.get_limit` fails on an unsaved Program."""
        self.assertGreater(self.program.year.get_limit(1), 0)

    def test_a_household_under_the_limit_is_eligible(self):
        screen = self.make_screen(household_size=1)
        add_income(self.add_member(screen), 100, frequency="monthly")

        self.assertTrue(self.calculate(screen).eligible)

    def test_a_household_over_the_limit_is_not(self):
        screen = self.make_screen(household_size=1)
        add_income(self.add_member(screen), 50_000, frequency="monthly")

        self.assertFalse(self.calculate(screen).eligible)

    def test_add_expense_is_readable_from_the_screen(self):
        screen = self.make_screen()
        add_expense(self.add_member(screen), 800, expense_type="rent")

        self.assertTrue(screen.has_expense(["rent"]))


class TestEntryPoints(CustomCalculatorTestCase):
    calculator_class = _Uninsured
    program_code = "test_uninsured"

    def test_make_calculator_does_not_run_the_calculation(self):
        """Tests that assert on one step need the instance, not the final Eligibility."""
        screen = self.make_screen()
        self.add_member(screen)

        calculator = self.make_calculator(screen)

        self.assertIsInstance(calculator, _Uninsured)
        self.assertTrue(calculator.eligible().eligible)

    def test_calculate_returns_the_eligibility_alone(self):
        """Not a (calculator, eligibility) tuple — some older local helpers return that."""
        screen = self.make_screen()
        self.add_member(screen)

        self.assertIsInstance(self.calculate(screen), Eligibility)

    def test_missing_dependencies_are_passed_through(self):
        screen = self.make_screen()
        self.add_member(screen)

        calculator = self.make_calculator(screen, missing=("income_amount",))

        self.assertIn("income_amount", calculator.missing_dependencies)


class TestProgramRowOptOut(CustomCalculatorTestCase):
    """A calculator that never reads `self.program` can skip building a real row."""

    calculator_class = _Uninsured
    needs_program_row = False

    def test_the_program_is_a_mock(self):
        self.assertIsInstance(self.program, Mock)

    def test_the_white_label_is_still_real(self):
        self.assertEqual(self.white_label.code, self.white_label_code)

    def test_the_calculator_still_runs(self):
        screen = self.make_screen()
        self.add_member(screen)

        self.assertEqual(self.calculate(screen).value, _Uninsured.member_amount)
