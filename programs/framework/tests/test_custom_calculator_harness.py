"""The custom-calculator fixture builds what a calculator reads.

`CustomCalculatorTestCase` and its builders are shared scaffolding, so a mistake in them
surfaces as a confusing failure in whichever program's suite adopted them next. These
pin the parts a calculator actually depends on: the one-to-one rows that raise when
absent, the fields FPL lookups read, and the two entry points a test calls.
"""

from datetime import date
from unittest.mock import Mock

from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator
from screener.models import HouseholdMember, Insurance
from programs.programs.testing_fixtures.custom_calculator import (
    CustomCalculatorTestCase,
    add_expense,
    birth_year_month_for_age,
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


class TestAgeDerivation(CustomCalculatorTestCase):
    """`add_member(age=...)` sets a `birth_year_month` that reads back as the same age.

    Calculators read age two ways — the stored `age` field, and `calc_age()`/`fraction_age()`
    derived from `birth_year_month` against the current date. A member built from an age has
    to satisfy both, on whatever day the suite happens to run.
    """

    calculator_class = _Uninsured
    needs_program_row = False

    def test_whole_year_ages_read_back_unchanged(self):
        """`calc_age()` returns the age that was asked for, across the range programs gate on."""
        screen = self.make_screen()

        for age in (0, 1, 2, 3, 5, 6, 12, 13, 17, 18, 19, 21, 59, 62, 64, 65, 80):
            with self.subTest(age=age):
                self.assertEqual(self.add_member(screen, age=age).calc_age(), age)

    def test_a_derived_age_holds_in_every_reference_month(self):
        """The reference month cancels out, so the run date cannot move the answer."""
        for month in range(1, 13):
            reference = date(2026, month, 15)
            for age in (0, 3, 17, 65):
                with self.subTest(month=month, age=age):
                    birth = birth_year_month_for_age(age, reference)

                    self.assertEqual(HouseholdMember.age_from_date(birth, reference), age)

    def test_fractional_ages_read_back_through_fraction_age(self):
        """`3.5` is three years six months, for the calculators reading month precision."""
        screen = self.make_screen()

        for age in (0.5, 2.5, 3.25, 3.5, 12.75):
            with self.subTest(age=age):
                self.assertAlmostEqual(self.add_member(screen, age=age).fraction_age(), age, places=6)

    def test_a_fractional_age_truncates_to_the_whole_year(self):
        """A member aged 3.5 is 3 to a calculator reading whole years."""
        member = self.add_member(self.make_screen(), age=3.5)

        self.assertEqual(member.calc_age(), 3)

    def test_the_stored_age_and_the_derived_age_agree(self):
        """Calculators read both fields; a member must not be two different people."""
        member = self.add_member(self.make_screen(), age=7)

        self.assertEqual(member.age, 7)
        self.assertEqual(member.calc_age(), 7)

    def test_an_explicit_birth_year_month_is_left_alone(self):
        """Scenarios pinned to a calendar window supply the date themselves."""
        birth = date(2020, 3, 1)

        member = self.add_member(self.make_screen(), age=5, birth_year_month=birth)

        self.assertEqual(member.birth_year_month, birth)

    def test_a_fractional_age_survives_a_database_round_trip(self):
        """`age` is a PositiveIntegerField, so the fraction lives in `birth_year_month`."""
        member = self.add_member(self.make_screen(), age=3.5)
        member.refresh_from_db()

        self.assertAlmostEqual(member.fraction_age(), 3.5, places=6)
        self.assertEqual(member.calc_age(), 3)


class TestPinnedReferenceDate(CustomCalculatorTestCase):
    """`reference_date` freezes the clock scenarios written against a calendar are read by."""

    calculator_class = _Uninsured
    needs_program_row = False
    reference_date = date(2026, 7, 22)

    def test_the_screen_reads_the_pinned_date(self):
        self.assertEqual(self.make_screen().get_reference_date(), date(2026, 7, 22))

    def test_a_literal_birth_month_is_read_against_the_pin(self):
        """A date copied from a spec keeps its age as the calendar moves."""
        member = self.add_member(self.make_screen(), age=None, birth_year_month=date(2020, 3, 1))

        self.assertEqual(member.calc_age(), 6)

    def test_an_age_still_round_trips(self):
        """Derivation uses the same pinned clock the calculator reads."""
        self.assertEqual(self.add_member(self.make_screen(), age=4).calc_age(), 4)


class TestDefaultLocation(CustomCalculatorTestCase):
    """A white label whose programs are local to one place states it once."""

    calculator_class = _Uninsured
    needs_program_row = False
    default_zipcode = "02101"
    default_county = "Boston"

    def test_a_screen_takes_the_class_default(self):
        screen = self.make_screen()

        self.assertEqual(screen.zipcode, "02101")
        self.assertEqual(screen.county, "Boston")

    def test_a_scenario_can_move_away_from_it(self):
        screen = self.make_screen(county="Malden")

        self.assertEqual(screen.county, "Malden")
        self.assertEqual(screen.zipcode, "02101")

    def test_a_yearly_income_is_not_divided_down(self):
        """An annual figure stays annual, so a boundary test is not lost to rounding."""
        screen = self.make_screen()
        self.add_member(screen, yearly_income=146_500)

        self.assertEqual(int(screen.calc_gross_income("yearly", ["all"])), 146_500)

    def test_both_frequencies_can_describe_one_member(self):
        screen = self.make_screen()
        self.add_member(screen, monthly_income=1_000, yearly_income=6_000)

        self.assertEqual(int(screen.calc_gross_income("yearly", ["all"])), 18_000)


class TestProgramCodeGuard(CustomCalculatorTestCase):
    """A `program_code` that disagrees with the calculator's fails at setup, not later."""

    calculator_class = _Uninsured
    program_code = "test_uninsured"
    needs_program_row = False

    def test_the_code_defaults_from_the_calculator(self):
        self.assertEqual(self.program_code, _Uninsured.program_code)

    def test_a_mismatched_code_is_rejected(self):
        class Mismatched(CustomCalculatorTestCase):
            calculator_class = _Uninsured
            program_code = "something_else"

        with self.assertRaises(AssertionError) as caught:
            Mismatched.setUpTestData()

        self.assertIn("something_else", str(caught.exception))


class TestInsuranceIsVisibleImmediately(CustomCalculatorTestCase):
    """`add_insurance` updates the member a test is holding, not just the database row."""

    calculator_class = _Uninsured
    needs_program_row = False

    def test_the_member_in_hand_sees_the_new_record(self):
        member = self.add_member(self.make_screen())

        add_insurance(member, medicare=True, none=False)

        self.assertTrue(member.insurance.medicare)
        self.assertFalse(member.insurance.none)


class TestHasIncomeFollowsTheIncome(CustomCalculatorTestCase):
    calculator_class = _Uninsured
    needs_program_row = False

    def test_a_member_given_income_has_income(self):
        self.assertTrue(self.add_member(self.make_screen(), monthly_income=1_000).has_income)

    def test_a_member_without_income_does_not(self):
        self.assertFalse(self.add_member(self.make_screen()).has_income)

    def test_a_scenario_may_say_otherwise(self):
        """A screener answer that disagrees with the streams is a real shape to test."""
        member = self.add_member(self.make_screen(), monthly_income=1_000, has_income=False)

        self.assertFalse(member.has_income)
