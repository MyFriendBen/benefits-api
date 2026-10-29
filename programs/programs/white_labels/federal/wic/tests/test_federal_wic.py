"""Federal WIC scenarios, one per spec section 8, plus the structural checks.

The income limits are 185% of the 2026 poverty guideline, the program's year. The spec states
the value as $64.89 a month per participant; the calculator carries the annual figure every
program value does, rounded to the dollar, so each assertion is $779 per eligible member.

Section 4's `legal_status` has no scenario: it is `Enforced by: program-record`
(`legal_status_required`), which the calculator never reads. `state_residency` is enforced by
the white label.
"""

from programs.framework.base import Eligibility
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from programs.programs.white_labels.federal.wic.calculator import FederalWic
from screener.models import HouseholdMember, Screen
from screener.serializers import _write_current_benefits
from screener.tests.helpers import seed_program

ANNUAL_VALUE = 779  # $64.89 × 12 = $778.68


class FederalWicTestCase(CustomCalculatorTestCase):
    calculator_class = FederalWic
    white_label_code = "federal"
    state_code = ""
    fpl_year = "2026"
    # The calculator reads age only through `calc_age()`.
    stores_age = False

    def household(self, *members: tuple, wages: int = 0, size: int | None = None) -> Screen:
        """A household of `(relationship, age, flags)` members; the head earns `wages` a year.

        `household_size` is the member count unless `size` says otherwise.
        """
        screen = self.make_screen(household_size=size or len(members))
        for index, (relationship, age, *flags) in enumerate(members):
            self.add_member(
                screen, relationship, age=age, yearly_income=wages if index == 0 else 0, **(flags[0] if flags else {})
            )

        return screen

    def member(self, screen: Screen, index: int) -> HouseholdMember:
        return screen.household_members.order_by("id")[index]

    def on_medicaid(self, member: HouseholdMember, insurance_type: str = "medicaid") -> None:
        self.add_insurance(member, **{insurance_type: True, "none": False})

    def receive(self, screen: Screen, base_program: str) -> None:
        name = f"test_{base_program}"
        seed_program(self.white_label, name, base_program=base_program)
        _write_current_benefits(screen, [name])
        screen.invalidate_current_benefits_cache()

    def assert_eligible(self, e: Eligibility, members: int = 1) -> None:
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, members * ANNUAL_VALUE)

    def assert_ineligible(self, e: Eligibility) -> None:
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)


class TestRegistration(FederalWicTestCase):
    def test_program_code_is_the_prefixed_federal_name(self):
        """The registry resolves a calculator by matching `program_code` to
        `Program.name_abbreviated`, so the federal row's prefixed name has to be here."""
        self.assertEqual(FederalWic.program_code, "federal_wic")

    def test_value_is_the_monthly_average_times_twelve(self):
        self.assertEqual(FederalWic.member_amount, ANNUAL_VALUE)

    def test_pregnancy_is_not_a_dependency(self):
        """The Get Ahead apps never send `pregnant`; a missing answer reads as not pregnant
        rather than dropping the program."""
        self.assertNotIn("pregnant", FederalWic.dependencies)

    def test_insurance_is_not_a_dependency(self):
        """Medicaid is one way in among several; a screen with no insurance answer loses that
        route, not the program."""
        self.assertNotIn("insurance", FederalWic.dependencies)


class TestScenarios(FederalWicTestCase):
    def test_scenario_1_pregnant_woman_and_her_infant(self):
        screen = self.household(("headOfHousehold", 28, {"pregnant": True}), ("child", 0), wages=20_000)

        self.assert_eligible(self.calculate(screen), members=2)

    def test_scenario_2_household_of_two_at_the_limit(self):
        screen = self.household(("headOfHousehold", 30), ("child", 3), wages=40_034)

        self.assert_eligible(self.calculate(screen))

    def test_scenario_3_household_of_two_one_dollar_over(self):
        screen = self.household(("headOfHousehold", 30), ("child", 3), wages=40_035)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_4_household_of_four_at_the_limit(self):
        screen = self.household(("headOfHousehold", 34), ("spouse", 33), ("child", 2), ("child", 9), wages=61_050)

        self.assert_eligible(self.calculate(screen))

    def test_scenario_5_household_of_four_one_dollar_over(self):
        screen = self.household(("headOfHousehold", 34), ("spouse", 33), ("child", 2), ("child", 9), wages=61_051)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_6_pregnancy_counts_toward_family_size(self):
        screen = self.household(("headOfHousehold", 26, {"pregnant": True}), wages=40_034)

        self.assert_eligible(self.calculate(screen))

    def test_scenario_6_one_dollar_over_the_family_of_two_limit(self):
        screen = self.household(("headOfHousehold", 26, {"pregnant": True}), wages=40_035)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_7_over_the_limit_and_on_snap(self):
        screen = self.household(("headOfHousehold", 30), ("child", 2), wages=60_000)
        self.receive(screen, "snap")

        self.assert_eligible(self.calculate(screen))

    def test_scenario_8_over_the_limit_and_on_tanf(self):
        screen = self.household(("headOfHousehold", 30), ("child", 2), wages=60_000)
        self.receive(screen, "tanf")

        self.assert_eligible(self.calculate(screen))

    def test_scenario_9_over_the_limit_and_the_child_is_on_medicaid(self):
        screen = self.household(("headOfHousehold", 30), ("child", 2), wages=60_000)
        self.on_medicaid(self.member(screen, 1))

        self.assert_eligible(self.calculate(screen))

    def test_scenario_10_an_infant_on_medicaid_reaches_the_family(self):
        screen = self.household(("headOfHousehold", 30), ("child", 0), ("child", 3), wages=70_000)
        self.on_medicaid(self.member(screen, 1))

        self.assert_eligible(self.calculate(screen), members=2)

    def test_scenario_11_only_a_parent_on_medicaid(self):
        screen = self.household(("headOfHousehold", 30), ("child", 3), wages=60_000)
        self.on_medicaid(self.member(screen, 0))

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_12_child_aged_four(self):
        screen = self.household(("headOfHousehold", 30), ("child", 4), wages=20_000)

        self.assert_eligible(self.calculate(screen))

    def test_scenario_13_child_aged_five(self):
        screen = self.household(("headOfHousehold", 30), ("child", 5), wages=20_000)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_14_child_aged_one(self):
        screen = self.household(("headOfHousehold", 30), ("child", 1), wages=20_000)

        self.assert_eligible(self.calculate(screen))

    def test_scenario_15_adult_not_pregnant_with_no_children(self):
        screen = self.household(("headOfHousehold", 30), wages=10_000)

        self.assert_ineligible(self.calculate(screen))

    def test_scenario_16_over_the_limit_and_the_child_is_on_masshealth(self):
        """MA's screener records Medicaid only as MassHealth."""
        screen = self.household(("headOfHousehold", 30), ("child", 2), wages=60_000)
        self.on_medicaid(self.member(screen, 1), "mass_health")

        self.assert_eligible(self.calculate(screen))


class TestEdges(FederalWicTestCase):
    def test_a_pregnant_member_on_medicaid_reaches_the_family(self):
        screen = self.household(("headOfHousehold", 30, {"pregnant": True}), ("child", 3), wages=70_000)
        self.on_medicaid(self.member(screen, 0))

        self.assert_eligible(self.calculate(screen), members=2)

    def test_adjunctive_eligibility_does_not_widen_the_categories(self):
        screen = self.household(("headOfHousehold", 30), ("child", 6), wages=60_000)
        self.receive(screen, "snap")

        self.assert_ineligible(self.calculate(screen))

    def test_a_missing_pregnancy_answer_reads_as_not_pregnant(self):
        screen = self.household(("headOfHousehold", 30, {"pregnant": None}), wages=10_000)

        self.assert_ineligible(self.calculate(screen))

    def test_a_child_with_no_pregnancy_answers_in_the_household(self):
        """What every Get Ahead screen looks like: they never send `pregnant`, so the endpoint
        reports it missing, and the program still calculates."""
        screen = self.household(("headOfHousehold", 30, {"pregnant": None}), ("child", 3), wages=10_000)

        self.assert_eligible(self.calculate(screen, missing=("pregnant",)))

    def test_household_size_is_what_the_screen_says(self):
        """The limit reads `household_size`, not the members entered."""
        screen = self.household(("headOfHousehold", 30), ("child", 3), wages=50_542, size=3)

        self.assert_eligible(self.calculate(screen))

    def test_failing_the_income_test_reports_the_limit(self):
        screen = self.household(("headOfHousehold", 30), ("child", 3), wages=40_035)

        calculator = self.make_calculator(screen)
        e = calculator.calc()

        self.assertEqual(calculator.income_limit, 40_034)
        self.assertTrue(e.fail_messages)
