"""
The TANF MFB federal base (``MfbTanf``), tested through a stand-in state that sets the figures a
state sets. The base spec (``programs/cross_white_label/tanf/base/tanf_base_spec.md`` in
program-ops) has no scenarios of its own; NJ's run end to end in ``test_nj.py``.
"""

from decimal import Decimal

from programs.framework.base import Eligibility
from programs.util import Dependencies
from programs.programs import calculators
from programs.programs.cross_white_label.tanf.mfb_base import MfbTanf
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from screener.models import Screen


class StandInTanf(MfbTanf, abstract=True):
    """A state with a flat 500 dollar income standard and grant, counting all income in full."""

    resource_limit = 3_000

    def countable_income(self) -> Decimal:
        return Decimal(str(self.screen.calc_gross_income("monthly", ["all"])))

    def income_standard(self) -> Decimal:
        return Decimal(500)

    def benefit_amount(self) -> Decimal:
        return Decimal(500) - self.countable_income()


class StandInWithoutResourceTest(StandInTanf, abstract=True):
    resource_limit = None


class StandInWithoutPregnancyRoute(StandInTanf, abstract=True):
    serves_pregnant_individual = False


class MfbTanfTestCase(CustomCalculatorTestCase):
    calculator_class = StandInTanf
    needs_program_row = False
    stores_age = False

    def household(self, *members: tuple[str, int], assets: int = 0, head_wages: int = 0) -> Screen:
        """A screen with a head of household aged 30 and the members listed as (relationship, age)."""
        screen = self.make_screen(household_size=len(members) + 1, household_assets=assets)
        self.add_member(screen, "headOfHousehold", 30, monthly_income=head_wages)
        for relationship, age in members:
            self.add_member(screen, relationship, age)

        return screen

    def assert_eligible(self, eligibility: Eligibility, value: int) -> None:
        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, value)

    def assert_ineligible(self, eligibility: Eligibility) -> None:
        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.value, 0)


class TestRegistration(MfbTanfTestCase):
    def test_base_is_abstract(self):
        self.assertTrue(MfbTanf._abstract)
        self.assertNotIn(MfbTanf, calculators.values())

    def test_nj_is_registered(self):
        self.assertEqual(calculators["nj_tanf"].__name__, "NjTanf")

    def test_base_sets_no_figures(self):
        calculator = MfbTanf(self.household(("child", 5)), self.program, {}, Dependencies())
        for method in (calculator.countable_income, calculator.income_standard, calculator.benefit_amount):
            with self.assertRaises(NotImplementedError):
                method()

    def test_base_defaults(self):
        self.assertIsNone(MfbTanf.resource_limit)
        self.assertTrue(MfbTanf.serves_pregnant_individual)
        self.assertEqual(MfbTanf.minor_child_age, 18)

    def test_dependencies(self):
        self.assertEqual(
            set(MfbTanf.dependencies),
            {"age", "relationship", "household_assets", "income_type", "income_amount", "income_frequency"},
        )
        self.assertNotIn("pregnant", MfbTanf.dependencies)


class TestMinorChild(MfbTanfTestCase):
    def test_child_under_18(self):
        self.assert_eligible(self.calculate(self.household(("child", 17))), 6_000)

    def test_any_relationship_under_18_counts(self):
        self.assert_eligible(self.calculate(self.household(("roommate", 10))), 6_000)

    def test_18_year_old_child_counts(self):
        self.assert_eligible(self.calculate(self.household(("child", 18))), 6_000)

    def test_19_year_old_does_not_count(self):
        self.assert_ineligible(self.calculate(self.household(("child", 19))))

    def test_18_year_old_head_does_not_count(self):
        screen = self.make_screen(household_size=1)
        self.add_member(screen, "headOfHousehold", 18)

        self.assert_ineligible(self.calculate(screen))

    def test_18_year_old_spouse_or_partner_does_not_count(self):
        for relationship in ("spouse", "domesticPartner"):
            with self.subTest(relationship=relationship):
                self.assert_ineligible(self.calculate(self.household((relationship, 18))))

    def test_17_year_old_spouse_counts(self):
        self.assert_eligible(self.calculate(self.household(("spouse", 17))), 6_000)

    def test_member_with_no_age_is_not_a_child(self):
        screen = self.household()
        member = self.add_member(screen, "child", 5)
        self.set_age(member, None)

        self.assert_ineligible(self.calculate(screen))

    def test_no_child_fails_with_the_child_message(self):
        eligibility = self.calculate(self.household(("parent", 60)))

        self.assert_ineligible(eligibility)
        self.assertEqual(len(eligibility.fail_messages), 1)


class TestPregnancy(MfbTanfTestCase):
    def pregnant_household(self, pregnant) -> Screen:
        screen = self.make_screen(household_size=1)
        self.add_member(screen, "headOfHousehold", 24, pregnant=pregnant)

        return screen

    def test_pregnant_member_alone(self):
        self.assert_eligible(self.calculate(self.pregnant_household(True)), 6_000)

    def test_not_pregnant(self):
        self.assert_ineligible(self.calculate(self.pregnant_household(False)))

    def test_pregnancy_not_asked(self):
        self.assert_ineligible(self.calculate(self.pregnant_household(None)))

    def test_state_without_the_pregnancy_route(self):
        calculator = StandInWithoutPregnancyRoute(self.pregnant_household(True), self.program, {}, Dependencies())

        self.assert_ineligible(calculator.calc())


class TestIncome(MfbTanfTestCase):
    def test_at_the_standard(self):
        self.assert_eligible(self.calculate(self.household(("child", 5), head_wages=499)), 12)

    def test_one_dollar_over(self):
        self.assert_ineligible(self.calculate(self.household(("child", 5), head_wages=501)))

    def test_value_below_a_dollar_a_year_shows_as_one(self):
        self.assert_eligible(self.calculate(self.household(("child", 5), head_wages=500)), 1)


class TestResources(MfbTanfTestCase):
    def test_at_the_limit(self):
        self.assert_eligible(self.calculate(self.household(("child", 5), assets=3_000)), 6_000)

    def test_one_dollar_over(self):
        self.assert_ineligible(self.calculate(self.household(("child", 5), assets=3_001)))

    def test_unanswered_assets_read_as_none(self):
        screen = self.household(("child", 5))
        screen.household_assets = None

        self.assert_eligible(self.calculate(screen), 6_000)

    def test_state_without_a_resource_test(self):
        calculator = StandInWithoutResourceTest(
            self.household(("child", 5), assets=1_000_000), self.program, {}, Dependencies()
        )

        self.assert_eligible(calculator.calc(), 6_000)


class TestValue(MfbTanfTestCase):
    def test_monthly_benefit_made_annual_and_rounded_half_up(self):
        calculator = self.make_calculator(self.household(("child", 5)))
        for monthly, annual in ((Decimal("139.50"), 1_674), (Decimal("10.0417"), 121), (Decimal("10.0416"), 120)):
            with self.subTest(monthly=monthly):
                calculator.benefit_amount = lambda monthly=monthly: monthly
                self.assertEqual(calculator.household_value(), annual)

    def test_value_is_for_the_household(self):
        eligibility = self.calculate(self.household(("child", 5), ("child", 3)))

        self.assertEqual(eligibility.household_value, 6_000)
        self.assertTrue(all(member.value == 0 for member in eligibility.eligible_members))
