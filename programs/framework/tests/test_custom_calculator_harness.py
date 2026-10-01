"""The custom-calculator fixture builds what a calculator reads.

`CustomCalculatorTestCase` and its builders are shared scaffolding, so a mistake in them
surfaces as a confusing failure in whichever program's suite adopted them next. These
pin the parts a calculator actually depends on: the one-to-one rows that raise when
absent, the fields FPL lookups read, and the two entry points a test calls.
"""

import uuid
from datetime import date
from unittest.mock import Mock

from django.utils import timezone

from integrations.clients.hud_income_limits import hud_client  # noqa: F401 -- hud_ami patches it here
from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator
from screener.models import HouseholdMember, Insurance
from screener.serializers import ScreenSerializer
from programs.programs.testing_fixtures.custom_calculator import (
    CustomCalculatorTestCase,
    add_expense,
    birth_year_month_for_age,
    add_income,
    add_insurance,
    hud_ami,
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


class _Voucher(ProgramCalculator):
    """Asks HUD for a band and a payment standard, and degrades to $0 on any error.

    The swallowing is what the HCV calculators do, and why `hud_ami` reports a lookup it
    was not given on exit rather than raising where the calculator could catch it.
    """

    program_code = "test_voucher"

    def household_value(self):
        try:
            limit = hud_client.get_screen_il_ami(self.screen, "50%", "2025")
            return hud_client.get_screen_payment_standard(self.screen, 1, "2025") if limit else 0
        except Exception:
            return 0


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

    `birth_year_month` is the member's age: `calc_age()`/`fraction_age()` derive it against the
    screen's reference date, and the stored `age` column is a copy kept only while calculators
    still read it. A member built from an age has to satisfy both, on whatever day the suite
    happens to run.
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

        member = self.add_member(self.make_screen(), age=None, birth_year_month=birth)

        self.assertEqual(member.birth_year_month, birth)

    def test_the_stored_age_is_derived_from_an_explicit_birth_month(self):
        birth = date(2020, 3, 1)

        member = self.add_member(self.make_screen(), age=None, birth_year_month=birth)

        self.assertEqual(member.age, member.calc_age())

    def test_an_age_contradicting_the_birth_month_is_rejected(self):
        screen = self.make_screen()
        birth = birth_year_month_for_age(7, screen.get_reference_date())

        with self.assertRaises(ValueError):
            self.add_member(screen, age=30, birth_year_month=birth)

    def test_set_age_moves_the_birth_month_too(self):
        """Assigning `member.age` alone would leave `calc_age()` reading the old birth month."""
        member = self.add_member(self.make_screen(), age=30)

        self.set_age(member, 17)
        member.refresh_from_db()

        self.assertEqual(member.age, 17)
        self.assertEqual(member.calc_age(), 17)

    def test_set_age_none_clears_both_fields(self):
        member = self.add_member(self.make_screen(), age=30)

        self.set_age(member, None)
        member.refresh_from_db()

        self.assertIsNone(member.age)
        self.assertIsNone(member.calc_age())


class TestWithoutStoredAge(CustomCalculatorTestCase):
    """`stores_age = False` builds members as they will be once the `age` column is gone."""

    calculator_class = _Uninsured
    needs_program_row = False
    stores_age = False

    def test_the_stored_age_is_null(self):
        self.assertIsNone(self.add_member(self.make_screen(), age=7).age)

    def test_the_derived_age_is_unaffected(self):
        self.assertEqual(self.add_member(self.make_screen(), age=7).calc_age(), 7)

    def test_set_age_leaves_it_null(self):
        member = self.set_age(self.add_member(self.make_screen(), age=7), 17)

        self.assertIsNone(member.age)
        self.assertEqual(member.calc_age(), 17)

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

    def test_income_added_afterwards_sets_has_income(self):
        """The screener sets `has_income` from the streams, however the test adds them."""
        member = self.add_member(self.make_screen())

        add_income(member, 1_000)
        member.refresh_from_db()

        self.assertTrue(member.has_income)

    def test_a_scenario_may_say_otherwise(self):
        """A row written through the API can disagree with its streams; the screener's never do."""
        member = self.add_member(self.make_screen(), monthly_income=1_000, has_income=False)
        member.refresh_from_db()

        self.assertFalse(member.has_income)


class TestHudAmi(CustomCalculatorTestCase):
    """`hud_ami` answers only what the test states, and says so when asked for more."""

    calculator_class = _Voucher
    needs_program_row = False

    def household(self):
        screen = self.make_screen()
        self.add_member(screen)

        return screen

    def test_a_scalar_limit_answers_every_band(self):
        with hud_ami(_Voucher, 50_000, payment_standard=900):
            self.assertEqual(self.calculate(self.household()).value, 900)

    def test_a_dict_limit_answers_by_band(self):
        with hud_ami(_Voucher, {"50%": 50_000}, payment_standard=900) as hud:
            self.assertEqual(self.calculate(self.household()).value, 900)

        hud.get_screen_il_ami.assert_called_once()

    def test_a_band_missing_from_the_dict_fails(self):
        with self.assertRaisesRegex(AssertionError, "50% AMI band"):
            with hud_ami(_Voucher, {"80%": 80_000}, payment_standard=900):
                self.calculate(self.household())

    def test_an_ami_lookup_with_no_limit_fails(self):
        with self.assertRaisesRegex(AssertionError, "get_screen_il_ami"):
            with hud_ami(_Voucher, payment_standard=900):
                self.calculate(self.household())

    def test_a_payment_standard_lookup_with_none_given_fails(self):
        """The calculator would swallow a raise here and report $0, so it is caught on exit."""
        with self.assertRaisesRegex(AssertionError, "get_screen_payment_standard"):
            with hud_ami(_Voucher, 50_000):
                self.calculate(self.household())

    def test_an_unasked_lookup_needs_no_value(self):
        """A test asserting HUD is not consulted can leave `limit` unset."""
        with hud_ami(_Voucher) as hud:
            pass

        hud.get_screen_il_ami.assert_not_called()

    def test_an_outage_is_not_an_unanswered_lookup(self):
        with hud_ami(_Voucher, unavailable=True):
            self.assertEqual(self.calculate(self.household()).value, 0)

    def test_a_callable_limit_sees_what_hud_was_asked(self):
        asked = []

        def limit(_screen, percent, _year, **_kwargs):
            asked.append(percent)
            return 50_000

        with hud_ami(_Voucher, limit, payment_standard=900):
            self.calculate(self.household())

        self.assertEqual(asked, ["50%"])


class TestMatchesTheScreener(CustomCalculatorTestCase):
    """A fixture member is the member the screener would have saved for the same answers.

    The payload mirrors `getScreensBody` in benefits-calculator (`src/Assets/updateScreen.ts`):
    birth month and year always sent, `age` null for a new member, every condition checkbox
    false unless ticked, the student follow-ups null for a non-student. If the fixture drifts
    from it, a test exercises a household no user can submit.
    """

    calculator_class = _Uninsured
    needs_program_row = False

    MEMBER_FIELDS = (
        "relationship",
        "age",
        "birth_year_month",
        "student",
        "student_full_time",
        "student_job_training_program",
        "student_has_work_study",
        "student_works_20_plus_hrs",
        "pregnant",
        "visually_impaired",
        "disabled",
        "long_term_disability",
        "was_in_foster_care",
        "has_income",
    )
    INSURANCE_FIELDS = ("none", "employer", "private", "medicaid", "medicare", "chp")

    def screener_screen(self, age: int, monthly_income: int = 0):
        birth = birth_year_month_for_age(age, timezone.now().date())
        income_streams = (
            [{"type": "wages", "amount": monthly_income, "frequency": "monthly", "hours_worked": None}]
            if monthly_income
            else []
        )
        payload = {
            "white_label": self.white_label_code,
            "is_test": True,
            "agree_to_tos": True,
            "is_13_or_older": True,
            "zipcode": "",
            "county": "",
            "household_size": 1,
            "household_assets": 0,
            "expenses": [],
            "energy_calculator": None,
            "household_members": [
                {
                    "frontend_id": str(uuid.uuid4()),
                    "age": None,
                    "birth_year": birth.year,
                    "birth_month": birth.month,
                    "relationship": "headOfHousehold",
                    "student": False,
                    "student_full_time": None,
                    "student_job_training_program": None,
                    "student_has_work_study": None,
                    "student_works_20_plus_hrs": None,
                    "pregnant": False,
                    "visually_impaired": False,
                    "disabled": False,
                    "long_term_disability": False,
                    "was_in_foster_care": False,
                    "has_income": bool(monthly_income),
                    "income_streams": income_streams,
                    "energy_calculator": None,
                    "insurance": {field: field == "none" for field in self.INSURANCE_FIELDS},
                }
            ],
        }

        serializer = ScreenSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        return serializer.save()

    def assert_same_member(self, age: int, monthly_income: int = 0):
        screener = self.screener_screen(age, monthly_income)
        fixture = self.make_screen()
        self.add_member(fixture, "headOfHousehold", age, monthly_income=monthly_income)

        screener_member = screener.household_members.get()
        fixture_member = fixture.household_members.get()

        for field in self.MEMBER_FIELDS:
            with self.subTest(field=field):
                self.assertEqual(getattr(fixture_member, field), getattr(screener_member, field))

        for field in self.INSURANCE_FIELDS:
            with self.subTest(insurance=field):
                self.assertEqual(getattr(fixture_member.insurance, field), getattr(screener_member.insurance, field))

        self.assertEqual(
            list(fixture_member.income_streams.values_list("type", "amount", "frequency")),
            list(screener_member.income_streams.values_list("type", "amount", "frequency")),
        )

        # What production hands the calculator as `missing_dependencies`.
        self.assertEqual(fixture.missing_fields(), screener.missing_fields())

    def test_an_adult_with_income(self):
        self.assert_same_member(34, monthly_income=1_500)

    def test_a_child_without_income(self):
        self.assert_same_member(4)
