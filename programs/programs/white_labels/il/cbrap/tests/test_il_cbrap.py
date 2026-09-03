from datetime import date
from unittest.mock import patch

from django.test import TestCase

from integrations.clients.hud_income_limits import HudIncomeClientError
from programs.framework.base import ProgramCalculator
from programs.models import FederalPoveryLimit, Program
from programs.programs.white_labels.il.cbrap.calculator import IlCbrap
from programs.util import Dependencies, DependencyError
from screener.models import Expense, HouseholdMember, IncomeStream, Screen, WhiteLabel

#: HUD FY2025 Standard Section 8 low-income (80%) limits for Illinois — the vintage IHDA
#: used for the FY2026 CBRAP round. Keyed by (county, household_size) as the spec's stub
#: contract requires, so a scenario that changes either input changes the limit it is
#: measured against.
FY2025_IL_80_PERCENT_LIMITS = {
    ("Cook", 1): 67_150,
    ("Cook", 4): 95_900,
    ("Adams", 1): 52_150,
}

#: The income-limit vintage CBRAP must ask HUD for. Not the current year.
AMI_VINTAGE = "2025"


def hud_il_ami_stub(screen, percent, year, county_override=None):
    """
    Stand-in for ``hud_client.get_screen_il_ami`` that reads its arguments.

    Raises on any tuple the fixture does not seed — an unseeded county, an unseeded
    household size, or a vintage other than FY2025. A flat stub that ignored its arguments
    would make the county and household-size scenarios vacuous.
    """
    if str(year) != AMI_VINTAGE:
        raise AssertionError(f"HUD lookup used vintage {year!r}; CBRAP must use the FY{AMI_VINTAGE} limits")
    if percent != "80%":
        raise AssertionError(f"HUD lookup used {percent!r}; CBRAP tests the 80% AMI limit")

    key = (county_override or screen.county, screen.household_size)
    if key not in FY2025_IL_80_PERCENT_LIMITS:
        raise AssertionError(f"HUD lookup for unseeded tuple {key}")

    return FY2025_IL_80_PERCENT_LIMITS[key]


class IlCbrapTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.white_label = WhiteLabel.objects.create(name="Illinois", code="il", state_code="IL")
        cls.ami_year = FederalPoveryLimit.objects.create(year=AMI_VINTAGE, period=AMI_VINTAGE)
        cls.program = Program.objects.new_program(white_label="il", name_abbreviated="il_cbrap")
        cls.program.year = cls.ami_year
        cls.program.save()

    def make_screen(self, county="Cook", zipcode="60601", household_size=4, needs_housing_help=False):
        return Screen.objects.create(
            agree_to_tos=True,
            zipcode=zipcode,
            county=county,
            household_size=household_size,
            white_label=self.white_label,
            needs_housing_help=needs_housing_help,
            completed=False,
        )

    def add_member(self, screen, relationship, birth_year, birth_month, age, **flags):
        return HouseholdMember.objects.create(
            screen=screen,
            relationship=relationship,
            age=age,
            birth_year_month=date(birth_year, birth_month, 1),
            has_income=False,
            **flags,
        )

    def add_income(self, screen, member, amount, frequency, income_type="wages"):
        member.has_income = True
        member.save()
        return IncomeStream.objects.create(
            screen=screen,
            household_member=member,
            type=income_type,
            amount=amount,
            frequency=frequency,
        )

    def add_expense(self, screen, member, expense_type, amount, frequency="monthly"):
        return Expense.objects.create(
            screen=screen,
            household_member=member,
            type=expense_type,
            amount=amount,
            frequency=frequency,
        )

    def calculator(self, screen, missing_dependencies=None):
        return IlCbrap(screen, self.program, {}, missing_dependencies or Dependencies())

    def eligibility(self, screen, missing_dependencies=None):
        """Run the calculator end to end with the argument-reading HUD stub."""
        calc = self.calculator(screen, missing_dependencies)
        with patch(
            "programs.programs.white_labels.il.cbrap.calculator.hud_client.get_screen_il_ami",
            side_effect=hud_il_ami_stub,
        ):
            return calc.calc()

    def family_of_four(self, county="Cook", zipcode="60601", needs_housing_help=False):
        """
        The four-person household Scenarios 1-4 share: two adults and two children in a
        Cook County household of four, against the $95,900 four-person limit.
        """
        screen = self.make_screen(
            county=county, zipcode=zipcode, household_size=4, needs_housing_help=needs_housing_help
        )
        head = self.add_member(screen, "headOfHousehold", 1986, 3, 40)
        spouse = self.add_member(screen, "spouse", 1988, 6, 38)
        self.add_member(screen, "child", 2016, 1, 10)
        self.add_member(screen, "child", 2019, 4, 7)
        return screen, head, spouse

    def one_person_household(self, county="Cook", zipcode="60601"):
        """The single-person household Scenarios 5-7 share."""
        screen = self.make_screen(county=county, zipcode=zipcode, household_size=1)
        head = self.add_member(screen, "headOfHousehold", 1986, 3, 40)
        return screen, head


class TestIlCbrapConfiguration(IlCbrapTestBase):
    """Class-level facts the calculator asserts about itself."""

    def test_program_code(self):
        self.assertEqual(IlCbrap.program_code, "il_cbrap")

    def test_registered_under_its_program_code(self):
        from programs.programs import calculators

        self.assertIs(calculators["il_cbrap"], IlCbrap)

    def test_value_is_the_ihda_projection_per_household(self):
        # $50,000,000 / 6,500 approved households = $7,692.31, rounded to the dollar.
        self.assertEqual(IlCbrap.amount, 7_692)

    def test_value_is_a_lump_sum_not_an_annualized_amount(self):
        # CBRAP is one-time and barred from repeating inside 18 months, so the stored value
        # is the award itself and must not be a monthly figure multiplied out.
        self.assertEqual(IlCbrap.amount, 7_692)
        self.assertNotEqual(IlCbrap.amount, 7_692 * 12)

    def test_uses_the_80_percent_ami_limit(self):
        self.assertEqual(IlCbrap.ami_percent, "80%")

    def test_declares_the_hud_lookup_inputs_as_dependencies(self):
        # county and household_size select the limit; a null either side crashes the HUD
        # client on a path that does not raise HudIncomeClientError, so both must be
        # declared rather than caught.
        for dependency in ("county", "household_size", "income_amount", "income_frequency"):
            self.assertIn(dependency, IlCbrap.dependencies)

    def test_no_member_level_value(self):
        # The award is a single household grant, not per-person.
        self.assertEqual(IlCbrap.member_amount, ProgramCalculator.member_amount)


class TestIlCbrapScenarios(IlCbrapTestBase):
    """One test per spec.md Test Scenario, asserting eligibility and benefit value."""

    def test_scenario_1_renter_well_under_the_limit(self):
        """Eligible, $7,692 — $54,000 against the $95,900 four-person Cook limit."""
        screen, head, spouse = self.family_of_four(needs_housing_help=False)
        self.add_income(screen, head, 3_500, "monthly")
        self.add_income(screen, spouse, 1_000, "monthly")
        self.add_expense(screen, head, "rent", 1_500)

        eligibility = self.eligibility(screen)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 7_692)

    def test_scenario_2_income_exactly_at_the_limit(self):
        """
        Eligible, $7,692 — $60,000 monthly-converted plus $35,900 yearly is exactly
        $95,900. Pins the comparison as inclusive, the aggregation as household-wide, and
        the monthly-to-yearly conversion.
        """
        screen, head, spouse = self.family_of_four()
        self.add_income(screen, head, 5_000, "monthly")
        self.add_income(screen, spouse, 35_900, "yearly")
        self.add_expense(screen, head, "rent", 1_500)

        eligibility = self.eligibility(screen)

        self.assertEqual(screen.calc_gross_income("yearly", ["all"]), 95_900)
        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 7_692)

    def test_scenario_3_income_one_dollar_over_the_limit(self):
        """
        Ineligible — $95,901 against the $95,900 limit, with the excess dollar on an
        unearned stream belonging to an adult relative outside the head's tax unit.
        """
        screen = self.make_screen(household_size=4)
        head = self.add_member(screen, "headOfHousehold", 1986, 3, 40)
        # Disability flags pinned false: is_dependent() treats has_disability() as an
        # alternative to the age test, which would pull this member back into the head's tax
        # unit and defeat the scoping this scenario checks.
        relative = self.add_member(
            screen,
            "relatedOther",
            1988,
            6,
            38,
            disabled=False,
            visually_impaired=False,
            long_term_disability=False,
        )
        self.add_member(screen, "child", 2016, 1, 10)
        self.add_member(screen, "child", 2019, 4, 7)
        self.add_income(screen, head, 5_000, "monthly")
        self.add_income(screen, relative, 35_901, "yearly", income_type="unemployment")
        self.add_expense(screen, head, "rent", 1_500)

        eligibility = self.eligibility(screen)

        self.assertEqual(screen.calc_gross_income("yearly", ["all"]), 95_901)
        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.value, 0)

    def test_scenario_4_homeowner_with_no_rent_expense(self):
        """Ineligible — Scenario 1's income with a mortgage instead of rent."""
        screen, head, spouse = self.family_of_four()
        self.add_income(screen, head, 3_500, "monthly")
        self.add_income(screen, spouse, 1_000, "monthly")
        self.add_expense(screen, head, "mortgage", 1_500)

        eligibility = self.eligibility(screen)

        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.value, 0)

    def test_scenario_5_single_person_cook_renter_under_the_limit(self):
        """Eligible, $7,692 — $55,000 against the $67,150 one-person Cook limit."""
        screen, head = self.one_person_household()
        self.add_income(screen, head, 55_000, "yearly")
        self.add_expense(screen, head, "rent", 1_100)

        eligibility = self.eligibility(screen)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 7_692)

    def test_scenario_6_same_household_in_adams_county(self):
        """Ineligible — $55,000 against the lower $52,150 one-person Adams limit."""
        screen, head = self.one_person_household(county="Adams", zipcode="62301")
        self.add_income(screen, head, 55_000, "yearly")
        self.add_expense(screen, head, "rent", 1_100)

        eligibility = self.eligibility(screen)

        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.value, 0)

    def test_scenario_7_single_person_one_dollar_over_the_limit(self):
        """
        Ineligible — $67,151 against the $67,150 one-person limit. Under the four-person
        $95,900 limit this income would wrongly pass.
        """
        screen, head = self.one_person_household()
        self.add_income(screen, head, 67_151, "yearly")
        self.add_expense(screen, head, "rent", 1_100)

        eligibility = self.eligibility(screen)

        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.value, 0)


class TestIlCbrapIncomeTest(IlCbrapTestBase):
    """The income rule beyond the scenarios' boundary pairs."""

    def test_zero_income_household_is_eligible(self):
        screen, head = self.one_person_household()
        self.add_expense(screen, head, "rent", 1_100)

        eligibility = self.eligibility(screen)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 7_692)

    def test_hud_lookup_uses_the_fy2025_vintage_not_the_current_year(self):
        screen, head = self.one_person_household()
        self.add_income(screen, head, 55_000, "yearly")
        self.add_expense(screen, head, "rent", 1_100)
        calc = self.calculator(screen)

        with patch(
            "programs.programs.white_labels.il.cbrap.calculator.hud_client.get_screen_il_ami",
            side_effect=hud_il_ami_stub,
        ) as mock_lookup:
            calc.calc()

        mock_lookup.assert_called_once_with(screen, "80%", AMI_VINTAGE)

    def test_income_counts_unearned_streams(self):
        """A household under the limit on wages alone fails once unearned income is added."""
        screen, head = self.one_person_household()
        self.add_income(screen, head, 40_000, "yearly")
        self.add_expense(screen, head, "rent", 1_100)
        self.assertTrue(self.eligibility(screen).eligible)

        self.add_income(screen, head, 30_000, "yearly", income_type="sSRetirement")

        self.assertFalse(self.eligibility(screen).eligible)


class TestIlCbrapUngatedRules(IlCbrapTestBase):
    """Rules CBRAP deliberately does not apply."""

    def test_needs_housing_help_does_not_gate_the_program(self):
        """
        The gate IlRenterAssistance has and CBRAP does not. An eligible household must come
        out eligible with the housing-need box unticked and ticked alike.
        """
        for needs_housing_help in (False, True):
            with self.subTest(needs_housing_help=needs_housing_help):
                screen, head, spouse = self.family_of_four(needs_housing_help=needs_housing_help)
                self.add_income(screen, head, 3_500, "monthly")
                self.add_expense(screen, head, "rent", 1_500)

                eligibility = self.eligibility(screen)

                self.assertTrue(eligibility.eligible)
                self.assertEqual(eligibility.value, 7_692)

    def test_immigration_status_is_not_read_by_the_calculator(self):
        """
        Criterion 3 is config-owned: eligibility must not vary with a member's status, which
        the calculator never reads. Verified here as the absence of any such gate.
        """
        screen, head = self.one_person_household()
        self.add_expense(screen, head, "rent", 1_100)

        self.assertTrue(self.eligibility(screen).eligible)

    def test_eviction_case_is_assumed_met(self):
        """
        No screener field records an eviction case, so a household in eviction court and one
        not in eviction court screen identically. Asserted so that adding a gate on a proxy
        field breaks a test.
        """
        screen, head = self.one_person_household()
        self.add_expense(screen, head, "rent", 1_100)

        self.assertTrue(self.eligibility(screen).eligible)


class TestIlCbrapFailurePaths(IlCbrapTestBase):
    """A failure must never reach the household as a policy answer."""

    def test_hud_client_error_skips_the_program_rather_than_denying(self):
        screen, head = self.one_person_household()
        self.add_income(screen, head, 55_000, "yearly")
        self.add_expense(screen, head, "rent", 1_100)
        calc = self.calculator(screen)

        with patch(
            "programs.programs.white_labels.il.cbrap.calculator.hud_client.get_screen_il_ami",
            side_effect=HudIncomeClientError("County not found: Cook County, IL"),
        ):
            with self.assertRaises(DependencyError):
                calc.calc()

    def test_missing_county_skips_the_program(self):
        screen, head = self.one_person_household()
        self.add_expense(screen, head, "rent", 1_100)

        with self.assertRaises(DependencyError):
            self.eligibility(screen, missing_dependencies=Dependencies({"county"}))

    def test_missing_household_size_skips_the_program(self):
        screen, head = self.one_person_household()
        self.add_expense(screen, head, "rent", 1_100)

        with self.assertRaises(DependencyError):
            self.eligibility(screen, missing_dependencies=Dependencies({"household_size"}))

    def test_missing_program_year_raises_rather_than_dereferencing_null(self):
        screen, head = self.one_person_household()
        self.add_expense(screen, head, "rent", 1_100)
        self.program.year = None
        self.program.save()
        self.addCleanup(self.restore_program_year)

        with self.assertRaises(ValueError):
            self.eligibility(screen)

    def restore_program_year(self):
        self.program.year = self.ami_year
        self.program.save()
