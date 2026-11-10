"""
The MFB ACA base (``MfbAca``) through a stand-in state: the rules NJ's scenarios don't reach.
Rules: program-ops ``programs/cross_white_label/aca/base/aca_base_spec.md``.

The stand-in prices every member at a flat 500 dollars a month and reads no Medicaid or CHIP
program, so each test isolates one base rule.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from programs.programs.cross_white_label.aca.mfb_base import APPLICABLE_PERCENTAGE_TABLES, MfbAca
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from screener.models import HouseholdMember, Screen


class StandInAca(MfbAca, abstract=True):
    state_taxable_income_types = ("testStateTaxable",)

    def benchmark_premium(self, members: list[HouseholdMember]) -> Decimal:
        return Decimal(500) * len(members)


class MfbAcaTestCase(CustomCalculatorTestCase):
    calculator_class = StandInAca
    program_code = "test_aca"
    fpl_year = "2026"
    reference_date = date(2026, 11, 15)

    def calculator(self, screen: Screen) -> StandInAca:
        return self.make_calculator(screen)


class TestApplicablePercentage(MfbAcaTestCase):
    def setUp(self):
        super().setUp()
        screen = self.make_screen()
        self.add_member(screen, yearly_income=40_000)
        self.aca = self.calculator(screen)

    def test_2027_band_edges(self):
        cases = {
            100: "2.15",
            132: "2.15",
            133: "3.23",
            149: "4.24",  # 3.23 + 1.07 × 16/17 = 4.2371
            150: "4.3",
            200: "6.78",
            231: "7.95",  # scenario 12: 6.78 + 1.88 × 31/50 = 7.9456
            250: "8.66",
            299: "10.19",  # 8.66 + 1.56 × 49/50 = 10.1888
            300: "10.22",
            400: "10.22",
        }
        for fpl_percent, expected in cases.items():
            with self.subTest(fpl_percent=fpl_percent):
                self.assertEqual(self.aca.applicable_percentage(fpl_percent), Decimal(expected))

    def test_over_400_percent_is_outside_the_table(self):
        with self.assertRaises(ValueError):
            self.aca.applicable_percentage(401)

    def test_2026_coverage_reads_the_2026_table(self):
        with patch.object(Screen, "get_reference_date", lambda _self: date(2026, 6, 1)):
            screen = self.make_screen()
            self.add_member(screen, yearly_income=40_000)
            aca = self.calculator(screen)

            self.assertEqual(aca.applicable_percentage(250), Decimal("8.44"))

    def test_a_coverage_year_with_no_table_uses_the_latest_and_reports_it(self):
        with patch.object(Screen, "get_reference_date", lambda _self: date(2027, 11, 1)):
            screen = self.make_screen()
            self.add_member(screen, yearly_income=40_000)
            aca = self.calculator(screen)

            with patch("programs.programs.cross_white_label.aca.mfb_base.capture_message") as report:
                percentage = aca.applicable_percentage(250)

        self.assertEqual(percentage, APPLICABLE_PERCENTAGE_TABLES[max(APPLICABLE_PERCENTAGE_TABLES)][4].initial)
        self.assertIn("coverage year 2028", report.call_args.args[0])


class TestHouseholdIncome(MfbAcaTestCase):
    def household(self, **dependent) -> tuple[StandInAca, HouseholdMember]:
        screen = self.make_screen(household_size=2)
        self.add_member(screen, age=40, yearly_income=30_000)
        child = self.add_member(screen, relationship="child", age=dependent.pop("age", 17), **dependent)
        return self.calculator(screen), child

    def test_a_dependent_under_the_filing_threshold_is_left_out(self):
        aca, _ = self.household(yearly_income=15_750)

        self.assertEqual(aca.household_income(), 30_000)

    def test_a_dependent_over_the_earned_threshold_is_counted(self):
        aca, _ = self.household(yearly_income=15_751)

        self.assertEqual(aca.household_income(), 45_751)

    def test_a_dependent_with_400_dollars_of_self_employment_is_counted(self):
        aca, _ = self.household(yearly_income=400, income_type="selfEmployment")

        self.assertEqual(aca.household_income(), 30_400)

    def test_a_dependent_over_the_unearned_threshold_is_counted(self):
        aca, _ = self.household(yearly_income=1_351, income_type="investment")

        self.assertEqual(aca.household_income(), 31_351)

    def test_a_dependent_over_the_gross_threshold_is_counted(self):
        """$1,000 wages + $1,000 investment: unearned and earned are each under their limits,
        but $2,000 is over max($1,350, $1,000 + $450)."""
        aca, child = self.household(yearly_income=1_000)
        self.add_income(child, 1_000, income_type="investment", frequency="yearly")

        self.assertEqual(aca.household_income(), 32_000)

    def test_a_blind_dependent_files_at_the_higher_threshold(self):
        aca, _ = self.household(yearly_income=1_351, income_type="investment", visually_impaired=True)

        self.assertEqual(aca.household_income(), 30_000)

    def test_social_security_counts_toward_filing_only_above_the_base_amount(self):
        aca, child = self.household(yearly_income=30_000, income_type="sSSurvivor")

        # $15,000 (half the benefits) + $0 other is under $25,000, so they don't file.
        self.assertEqual(aca.household_income(), 30_000)

        self.add_income(child, 12_000, income_type="investment", frequency="yearly")
        aca = self.calculator(child.screen)

        # $15,000 + $12,000 is over $25,000: the benefits are unearned income, so they file.
        self.assertEqual(aca.household_income(), 72_000)

    def test_untaxed_income_is_left_out(self):
        screen = self.make_screen()
        head = self.add_member(screen, yearly_income=30_000)
        for income_type in ("sSI", "childSupport", "gifts", "workersComp", "veteran", "alimony", "cashAssistance"):
            self.add_income(head, 1_000, income_type=income_type, frequency="yearly")

        self.assertEqual(self.calculator(screen).household_income(), 30_000)

    def test_a_states_own_taxable_income_type_counts(self):
        screen = self.make_screen()
        head = self.add_member(screen, yearly_income=30_000)
        self.add_income(head, 1_000, income_type="testStateTaxable", frequency="yearly")

        self.assertEqual(self.calculator(screen).household_income(), 31_000)


class TestTurns65Month(MfbAcaTestCase):
    def member(self, **kwargs) -> tuple[StandInAca, HouseholdMember]:
        screen = self.make_screen()
        member = self.add_member(screen, **kwargs)
        return self.calculator(screen), member

    def test_older_than_65_in_the_coverage_year_is_january(self):
        aca, member = self.member(age=None, birth_year_month=date(1961, 12, 1))

        self.assertEqual(aca.turns_65_month(member), 1)

    def test_turning_65_in_the_coverage_year_is_the_birth_month(self):
        aca, member = self.member(age=None, birth_year_month=date(1962, 9, 1))

        self.assertEqual(aca.turns_65_month(member), 9)

    def test_younger_is_none(self):
        aca, member = self.member(age=None, birth_year_month=date(1963, 1, 1))

        self.assertIsNone(aca.turns_65_month(member))

    def test_without_a_birth_month_65_or_older_today_is_january(self):
        aca, member = self.member(age=65, birth_year_month=None)
        member.birth_year_month = None

        self.assertEqual(aca.turns_65_month(member), 1)


class TestHouseholdEligibility(MfbAcaTestCase):
    def test_no_member_in_the_coverage_family_is_ineligible(self):
        screen = self.make_screen()
        head = self.add_member(screen, yearly_income=40_000)
        self.add_insurance(head, medicare=True, none=False)

        self.assertFalse(self.calculate(screen).eligible)

    def test_a_household_exactly_at_the_poverty_line_is_eligible(self):
        screen = self.make_screen()
        self.add_member(screen, yearly_income=15_960)

        self.assertTrue(self.calculate(screen).eligible)
