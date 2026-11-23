"""
Unit tests for the CCDF federal base (``Ccdf``).

Exercised through a test-only subclass that supplies the values each state sets. The base spec
has no scenarios of its own, so each rule in its sections 3, 4 and 7 gets a test here; NJ's spec
scenarios run end to end in ``test_nj.py``.
"""

from datetime import date
from decimal import Decimal

from programs.framework.base import PaymentUnit, ProgramCalculator
from programs.framework.registry import build
from programs.programs.cross_white_label.ccdf.base import CHILD_RELATIONSHIPS, Ccdf
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from programs.util import Dependencies
from screener.models import HouseholdMember, Screen


class StateCcdf(Ccdf):
    """A state that sets a flat limit, rate and copay, so each base rule shows on its own."""

    program_code = "test_ccdf"

    limit = 30_000
    rate = Decimal("1000")
    copay = Decimal("100")

    def income_limit(self) -> int:
        return self.limit

    def payment_rate(self, child: HouseholdMember) -> Decimal:
        return self.rate

    def family_copayment(self, children: list[HouseholdMember]) -> Decimal:
        return self.copay


class ExcludingStateCcdf(StateCcdf):
    program_code = "test_excluding_ccdf"
    income_exclusions = ("cashAssistance",)


class HalfCentStateCcdf(StateCcdf):
    """A rate that lands on half a dollar a year, to show the value rounds half up."""

    program_code = "test_half_cent_ccdf"
    rate = Decimal("1000.375")
    copay = Decimal(0)


class CostlyStateCcdf(StateCcdf):
    """A copay above the rate, to show the value stops at 0."""

    program_code = "test_costly_ccdf"
    copay = Decimal("5000")


class BareStateCcdf(Ccdf):
    """A state that sets nothing, to show which hooks every state must fill."""

    program_code = "test_bare_ccdf"


class CcdfTestCase(CustomCalculatorTestCase):
    calculator_class = StateCcdf
    stores_age = False
    reference_date = date(2026, 11, 15)

    def household(self, child_age: float = 6, relationship: str = "child", **head: object) -> Screen:
        """A working head of household and one child."""
        screen = self.make_screen(household_size=2)
        head.setdefault("monthly_income", 2_000)
        self.add_member(screen, "headOfHousehold", 30, **head)
        self.add_member(screen, relationship, child_age)
        return screen

    def calculate_as(self, cls: type, screen: Screen):
        return cls(screen, self.program, {}, Dependencies(())).calc()


class TestClassAttributes(CcdfTestCase):
    def test_base_backs_no_program(self) -> None:
        registry = build("programs.programs", ProgramCalculator)
        self.assertNotIn(Ccdf, registry.values())

    def test_paid_to_the_household(self) -> None:
        self.assertEqual(Ccdf.payment_unit, PaymentUnit.HOUSEHOLD)

    def test_federal_constants(self) -> None:
        self.assertEqual(Ccdf.max_child_age, 13)
        self.assertEqual(Ccdf.asset_limit, 1_000_000)
        self.assertEqual(Ccdf.income_exclusions, ())

    def test_declares_the_fields_it_reads(self) -> None:
        self.assertEqual(
            set(Ccdf.dependencies),
            {"age", "relationship", "student", "household_size", "income_amount", "income_frequency", "income_type"},
        )

    def test_each_state_supplies_its_limit_rate_and_copay(self) -> None:
        calculator = BareStateCcdf(self.household(), self.program, {}, None)
        with self.assertRaises(NotImplementedError):
            calculator.income_limit()
        with self.assertRaises(NotImplementedError):
            calculator.payment_rate(Ccdf)
        with self.assertRaises(NotImplementedError):
            calculator.family_copayment([])


class TestAgeLimit(CcdfTestCase):
    def test_twelve_is_eligible(self) -> None:
        self.assertTrue(self.calculate(self.household(child_age=12)).eligible)

    def test_thirteen_is_not(self) -> None:
        self.assertFalse(self.calculate(self.household(child_age=13)).eligible)

    def test_newborn_is_eligible(self) -> None:
        self.assertTrue(self.calculate(self.household(child_age=0)).eligible)

    def test_unknown_age_is_not(self) -> None:
        screen = self.household()
        child = screen.household_members.get(relationship="child")
        self.set_age(child, None)

        self.assertFalse(self.calculate(screen).eligible)


class TestChildRelationships(CcdfTestCase):
    def test_each_child_relationship_counts(self) -> None:
        for relationship in CHILD_RELATIONSHIPS:
            with self.subTest(relationship=relationship):
                self.assertTrue(self.calculate(self.household(relationship=relationship)).eligible)

    def test_a_young_roommate_does_not(self) -> None:
        self.assertFalse(self.calculate(self.household(relationship="roommate")).eligible)

    def test_a_young_head_of_household_is_not_a_child(self) -> None:
        screen = self.make_screen(household_size=1)
        self.add_member(screen, "headOfHousehold", 12, monthly_income=2_000)

        self.assertFalse(self.calculate(screen).eligible)


class TestIncomeLimit(CcdfTestCase):
    def test_at_the_limit(self) -> None:
        self.assertTrue(self.calculate(self.household(monthly_income=0, yearly_income=30_000)).eligible)

    def test_one_dollar_over(self) -> None:
        e = self.calculate(self.household(monthly_income=0, yearly_income=30_001))

        self.assertFalse(e.eligible)
        self.assertEqual(len(e.fail_messages), 1)

    def test_counts_everyone_listed(self) -> None:
        screen = self.household(monthly_income=0, yearly_income=20_000)
        self.add_member(screen, "roommate", 40, yearly_income=10_001)

        self.assertFalse(self.calculate(screen).eligible)

    def test_counts_every_income_type_by_default(self) -> None:
        screen = self.household(monthly_income=0, yearly_income=29_000)
        self.add_income(screen.household_members.get(relationship="headOfHousehold"), 1_001, "cashAssistance", "yearly")

        self.assertFalse(self.calculate(screen).eligible)

    def test_a_state_can_leave_income_types_out(self) -> None:
        screen = self.household(monthly_income=0, yearly_income=29_000)
        self.add_income(screen.household_members.get(relationship="headOfHousehold"), 1_001, "cashAssistance", "yearly")

        self.assertTrue(self.calculate_as(ExcludingStateCcdf, screen).eligible)


class TestAssetLimit(CcdfTestCase):
    def test_at_the_limit(self) -> None:
        screen = self.household()
        screen.household_assets = 1_000_000

        self.assertTrue(self.calculate(screen).eligible)

    def test_one_dollar_over(self) -> None:
        screen = self.household()
        screen.household_assets = 1_000_001

        self.assertFalse(self.calculate(screen).eligible)

    def test_unanswered_passes(self) -> None:
        screen = self.household()
        screen.household_assets = None

        self.assertTrue(self.calculate(screen).eligible)


class TestParentActivity(CcdfTestCase):
    def test_wages(self) -> None:
        self.assertTrue(self.calculate(self.household()).eligible)

    def test_self_employment(self) -> None:
        self.assertTrue(self.calculate(self.household(income_type="selfEmployment")).eligible)

    def test_student(self) -> None:
        self.assertTrue(self.calculate(self.household(monthly_income=0, student=True)).eligible)

    def test_job_training(self) -> None:
        self.assertTrue(self.calculate(self.household(monthly_income=0, student_job_training_program=True)).eligible)

    def test_other_income_is_not_work(self) -> None:
        self.assertFalse(self.calculate(self.household(income_type="unemployment")).eligible)

    def test_nobody_active(self) -> None:
        self.assertFalse(self.calculate(self.household(monthly_income=0)).eligible)

    def test_the_heads_partner_counts(self) -> None:
        for relationship in ("spouse", "domesticPartner"):
            with self.subTest(relationship=relationship):
                screen = self.household(monthly_income=0)
                self.add_member(screen, relationship, 30, monthly_income=2_000)

                self.assertTrue(self.calculate(screen).eligible)

    def test_another_adult_does_not(self) -> None:
        for relationship in ("roommate", "parent", "boyfriendOrGirlfriend"):
            with self.subTest(relationship=relationship):
                screen = self.household(monthly_income=0)
                self.add_member(screen, relationship, 30, monthly_income=2_000)

                self.assertFalse(self.calculate(screen).eligible)


class TestValue(CcdfTestCase):
    def test_rate_less_copay_for_a_year(self) -> None:
        self.assertEqual(self.calculate(self.household()).value, (1_000 - 100) * 12)

    def test_each_eligible_child_adds_a_rate_and_the_copay_is_charged_once(self) -> None:
        screen = self.household()
        self.add_member(screen, "child", 3)
        self.add_member(screen, "child", 14)

        self.assertEqual(self.calculate(screen).value, (2 * 1_000 - 100) * 12)

    def test_paid_to_the_household_not_to_members(self) -> None:
        e = self.calculate(self.household())

        self.assertEqual(e.household_value, e.value)
        self.assertTrue(all(member_e.value == 0 for member_e in e.eligible_members))

    def test_never_below_zero(self) -> None:
        self.assertEqual(self.calculate_as(CostlyStateCcdf, self.household()).value, 0)

    def test_rounds_half_up_to_the_dollar(self) -> None:
        # 1,000.375 a month is 12,004.50 a year.
        self.assertEqual(self.calculate_as(HalfCentStateCcdf, self.household()).value, 12_005)

    def test_ineligible_household_has_no_value(self) -> None:
        self.assertEqual(self.calculate(self.household(child_age=13)).value, 0)
