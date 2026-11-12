"""
NJ Child and Dependent Care Credit.

Builds real Screen/HouseholdMember/IncomeStream/Expense rows and runs the real `calc()`. Every
spec §8 scenario has a test named for it; the rest cover the federal credit at 0, the property tax
deduction's filing threshold, the exemptions for a spouse, and the missing-field guard.

Ages in the spec are ages at the end of the tax year, so members are built from a birth month
rather than today's age; the scenarios that turn on a birthday give the month itself. The
screening date is pinned to March of the year after the tax year, when returns for it are filed.
"""

from datetime import date
from typing import Optional
from unittest.mock import patch

from programs.framework.base import Eligibility
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from programs.programs.white_labels.federal.cdcc.calculator import FederalCdcc
from programs.programs.white_labels.nj.cdcc.calculator import NjCdcc
from programs.util import DependencyError
from screener.models import Expense, HouseholdMember, Screen

TAX_YEAR = 2025


def born_for_age_at_end_of(age: int, year: int = TAX_YEAR) -> date:
    """A birth month giving the stated age on December 31 of `year`."""
    return date(year - age, 6, 1)


class NjCdccTestCase(CustomCalculatorTestCase):
    calculator_class = NjCdcc
    white_label_code = "nj"
    state_code = "NJ"
    default_zipcode = "07102"
    default_county = "Essex County"
    fpl_year = str(TAX_YEAR)
    reference_date = date(TAX_YEAR + 1, 3, 15)

    def member(
        self,
        screen: Screen,
        relationship: str,
        age: Optional[int] = None,
        income: Optional[dict[str, int]] = None,
        birth_year_month: Optional[date] = None,
        **kwargs: object,
    ) -> HouseholdMember:
        """A member whose `age` is their age at the end of the tax year, with yearly income by type."""
        born = birth_year_month if birth_year_month is not None else born_for_age_at_end_of(age)
        member = self.add_member(screen, relationship, None, birth_year_month=born, **kwargs)
        for income_type, amount in (income or {}).items():
            self.add_income(member, amount, income_type, "yearly")

        return member

    def parent_with_child(self, wages: int, care: int = 300) -> tuple[Screen, HouseholdMember]:
        """The spec's usual household: a head of 30 on `wages` and a child of 5, with monthly child care."""
        screen = self.make_screen(household_size=2)
        head = self.member(screen, "headOfHousehold", 30, income={"wages": wages})
        self.member(screen, "child", 5)
        self.add_expense(head, care, "childCare", "monthly")
        return screen, head

    def assertValue(self, screen: Screen, value: int) -> None:
        e = self.calculate(screen)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, value)

    def assertIneligible(self, screen: Screen) -> Eligibility:
        e = self.calculate(screen)
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)
        return e


class TestRegistration(NjCdccTestCase):
    def test_program_code(self):
        self.assertEqual(NjCdcc.program_code, "nj_cdcc")

    def test_constants(self):
        c = NjCdcc
        self.assertEqual(c.income_limit, 150_000)
        self.assertEqual(
            [(top, str(rate)) for top, rate in c.nj_rates],
            [
                (30_000, "0.50"),
                (60_000, "0.40"),
                (90_000, "0.30"),
                (120_000, "0.20"),
                (150_000, "0.10"),
            ],
        )
        self.assertEqual((c.personal_exemption, c.senior_exemption, c.senior_age), (1_000, 1_000, 65))
        self.assertEqual((c.blind_disabled_exemption, c.dependent_exemption), (1_000, 1_500))
        self.assertEqual((c.college_exemption, c.college_age_limit), (1_000, 22))
        self.assertEqual((str(c.medical_floor), str(c.rent_as_property_tax), c.deduction_cap), ("0.02", "0.18", 15_000))
        self.assertEqual((c.filing_threshold_joint, c.filing_threshold_single), (20_000, 10_000))

    def test_dependencies_add_the_nj_fields_to_the_federal_ones(self):
        self.assertTrue(set(FederalCdcc.dependencies) <= set(NjCdcc.dependencies))
        for field in ("student", "visually_impaired", "disabled", "long_term_disability"):
            self.assertIn(field, NjCdcc.dependencies)

    def test_a_missing_expense_amount_raises(self):
        screen, head = self.parent_with_child(32_500)
        Expense.objects.create(screen=screen, household_member=head, type="rent", amount=None, frequency="monthly")

        with self.assertRaises(DependencyError):
            self.calculate(screen, missing=screen.missing_fields())


class TestScenarios(NjCdccTestCase):
    def test_scenario_01_top_of_the_50_percent_band(self):
        screen, _ = self.parent_with_child(32_500)
        self.assertValue(screen, 390)

    def test_scenario_02_one_dollar_into_the_40_percent_band(self):
        screen, _ = self.parent_with_child(32_501)
        self.assertValue(screen, 312)

    def test_scenario_03_top_of_the_40_percent_band(self):
        screen, _ = self.parent_with_child(62_500)
        self.assertValue(screen, 240)

    def test_scenario_04_one_dollar_into_the_30_percent_band(self):
        screen, _ = self.parent_with_child(62_501)
        self.assertValue(screen, 180)

    def test_scenario_05_top_of_the_30_percent_band(self):
        screen, _ = self.parent_with_child(92_500)
        self.assertValue(screen, 180)

    def test_scenario_06_one_dollar_into_the_20_percent_band(self):
        screen, _ = self.parent_with_child(92_501)
        self.assertValue(screen, 120)

    def test_scenario_07_top_of_the_20_percent_band(self):
        screen, _ = self.parent_with_child(122_500)
        self.assertValue(screen, 120)

    def test_scenario_08_one_dollar_into_the_10_percent_band(self):
        screen, _ = self.parent_with_child(122_501)
        self.assertValue(screen, 60)

    def test_scenario_09_top_of_the_10_percent_band(self):
        screen, _ = self.parent_with_child(152_500)
        self.assertValue(screen, 60)

    def test_scenario_10_one_dollar_over_150000(self):
        screen, _ = self.parent_with_child(152_501)
        self.assertIneligible(screen)

        # Only the NJ limit fails: the federal credit is there.
        calculator = self.make_calculator(screen)
        self.assertEqual(calculator._taxable_income, 150_001)
        self.assertGreater(calculator._federal_credit, 0)

    def test_scenario_11_pays_for_care_but_owes_no_federal_tax(self):
        screen, _ = self.parent_with_child(20_000)
        self.assertIneligible(screen)

        # Only the federal credit fails: the NJ income is well under the limit.
        calculator = self.make_calculator(screen)
        self.assertEqual(calculator._income_tax, 0)
        self.assertEqual(calculator._taxable_income, 17_500)

    def test_scenario_12_married_couple(self):
        screen = self.make_screen(household_size=3)
        head = self.member(screen, "headOfHousehold", 35, income={"wages": 23_500})
        self.member(screen, "spouse", 34, income={"wages": 40_000})
        self.member(screen, "child", 5)
        self.add_expense(head, 300, "childCare", "monthly")

        self.assertValue(screen, 240)
        self.assertEqual(self.make_calculator(screen)._taxable_income, 60_000)

    def test_scenario_13_disabled_head_of_household(self):
        screen = self.make_screen(household_size=2)
        head = self.member(screen, "headOfHousehold", 30, income={"wages": 63_500}, disabled=True)
        self.member(screen, "child", 5)
        self.add_expense(head, 300, "childCare", "monthly")

        self.assertValue(screen, 240)

    def test_scenario_14_college_student_dependent(self):
        screen = self.make_screen(household_size=3)
        head = self.member(screen, "headOfHousehold", 45, income={"wages": 65_000})
        self.member(screen, "child", 5)
        self.member(screen, "child", 19, student=True, student_full_time=True)
        self.add_expense(head, 300, "childCare", "monthly")

        self.assertValue(screen, 240)
        self.assertEqual(self.make_calculator(screen)._exemptions, 5_000)

    def test_scenario_15_medical_costs_over_2_percent_of_income(self):
        screen, head = self.parent_with_child(64_000)
        self.add_expense(head, 500, "medical", "monthly")

        self.assertValue(screen, 240)
        self.assertEqual(self.make_calculator(screen)._taxable_income, 56_780)

    def test_scenario_16_renters_property_tax_deduction_moves_the_band(self):
        screen, head = self.parent_with_child(66_000)
        self.add_expense(head, 2_000, "rent", "monthly")

        self.assertValue(screen, 240)
        self.assertEqual(self.make_calculator(screen)._taxable_income, 59_180)

    def test_scenario_17_unemployment_and_veteran_benefits_left_out(self):
        screen = self.make_screen(household_size=2)
        head = self.member(
            screen,
            "headOfHousehold",
            30,
            income={"wages": 62_000, "unemployment": 5_000, "veteran": 5_000},
        )
        self.member(screen, "child", 5)
        self.add_expense(head, 300, "childCare", "monthly")

        self.assertValue(screen, 240)
        self.assertEqual(self.make_calculator(screen)._taxable_income, 59_500)

    def test_scenario_18_two_children_raise_the_federal_credit(self):
        screen = self.make_screen(household_size=3)
        head = self.member(screen, "headOfHousehold", 30, income={"wages": 65_000})
        self.member(screen, "child", 5)
        self.member(screen, "child", 8)
        self.add_expense(head, 600, "childCare", "monthly")

        self.assertValue(screen, 360)

    def test_scenario_19_domestic_partners_income_left_out(self):
        screen = self.make_screen(household_size=3)
        head = self.member(screen, "headOfHousehold", 30, income={"wages": 57_500})
        self.member(screen, "domesticPartner", 31, income={"wages": 40_000})
        self.member(screen, "child", 5)
        self.add_expense(head, 300, "childCare", "monthly")

        self.assertValue(screen, 240)
        self.assertEqual(self.make_calculator(screen)._taxable_income, 55_000)

    def test_scenario_20_federal_credit_cut_to_the_tax_owed_and_a_half_dollar_rounded_up(self):
        screen, _ = self.parent_with_child(25_030)

        self.assertEqual(self.make_calculator(screen)._federal_credit, 141)
        self.assertValue(screen, 71)

    def test_scenario_21_a_credit_that_rounds_to_0(self):
        """Eligible at 0, with no minimum: the spec reports it as a known value."""
        screen, _ = self.parent_with_child(122_501, care=1)

        self.assertEqual(self.make_calculator(screen)._federal_credit, 2)
        self.assertValue(screen, 0)

    def test_scenario_22_care_costs_below_the_federal_expense_limit(self):
        screen, _ = self.parent_with_child(57_500, care=200)
        self.assertValue(screen, 192)

    def test_scenario_23_homeowners_property_tax_deduction_capped_at_15000(self):
        screen, head = self.parent_with_child(63_000)
        self.add_expense(head, 31_000, "propertyTax", "yearly")

        self.assertValue(screen, 240)
        self.assertEqual(self.make_calculator(screen)._taxable_income, 45_500)

    def test_scenario_24_medical_costs_where_the_2_percent_floor_decides_the_band(self):
        screen, head = self.parent_with_child(64_300)
        self.add_expense(head, 250, "medical", "monthly")

        self.assertValue(screen, 180)
        self.assertEqual(self.make_calculator(screen)._taxable_income, 60_086)

    def test_scenario_25_head_65_or_older_and_blind(self):
        screen = self.make_screen(household_size=2)
        head = self.member(screen, "headOfHousehold", 67, income={"wages": 64_500}, visually_impaired=True)
        self.member(screen, "child", 5)
        self.add_expense(head, 300, "childCare", "monthly")

        self.assertValue(screen, 240)
        self.assertEqual(self.make_calculator(screen)._exemptions, 4_500)

    def test_scenario_26_long_term_condition_counted_for_the_disabled_exemption(self):
        screen = self.make_screen(household_size=2)
        head = self.member(screen, "headOfHousehold", 30, income={"wages": 63_500}, long_term_disability=True)
        self.member(screen, "child", 5)
        self.add_expense(head, 300, "childCare", "monthly")

        self.assertValue(screen, 240)

    def test_scenario_27_baby_born_after_the_tax_year(self):
        screen, head = self.parent_with_child(62_501, care=250)
        self.member(screen, "child", birth_year_month=date(TAX_YEAR + 1, 3, 1))

        self.assertValue(screen, 180)
        self.assertEqual(self.make_calculator(screen)._exemptions, 2_500)

    def test_scenario_28_domestic_partner_with_no_earnings(self):
        screen = self.make_screen(household_size=3)
        head = self.member(screen, "headOfHousehold", 30, income={"wages": 62_501})
        self.member(screen, "domesticPartner", 31)
        self.member(screen, "child", 5)
        self.add_expense(head, 300, "childCare", "monthly")

        self.assertValue(screen, 180)

    def test_scenario_29_renters_deduction_at_18_percent_of_rent(self):
        screen, head = self.parent_with_child(47_500)
        self.add_expense(head, 1_500, "rent", "monthly")

        self.assertValue(screen, 240)
        self.assertEqual(self.make_calculator(screen)._taxable_income, 41_760)

    def test_scenario_30_head_65_on_the_last_day_of_the_tax_year(self):
        screen = self.make_screen(household_size=2)
        head = self.member(
            screen, "headOfHousehold", income={"wages": 63_500}, birth_year_month=date(TAX_YEAR - 65, 12, 1)
        )
        self.member(screen, "child", 5)
        self.add_expense(head, 300, "childCare", "monthly")

        self.assertValue(screen, 240)

    def test_scenario_31_head_64_at_the_end_of_the_tax_year_65_when_screened(self):
        screen = self.make_screen(household_size=2)
        head = self.member(
            screen, "headOfHousehold", income={"wages": 62_501}, birth_year_month=date(TAX_YEAR - 64, 1, 1)
        )
        self.member(screen, "child", 5)
        self.add_expense(head, 300, "childCare", "monthly")

        self.assertEqual(head.calc_age(), 65)
        self.assertValue(screen, 180)

    def test_scenario_32_college_student_21_at_the_end_of_the_tax_year_22_when_screened(self):
        screen = self.make_screen(household_size=3)
        head = self.member(screen, "headOfHousehold", 45, income={"wages": 65_000})
        self.member(screen, "child", 5)
        student = self.member(
            screen, "child", birth_year_month=date(TAX_YEAR - 21, 1, 1), student=True, student_full_time=True
        )
        self.add_expense(head, 300, "childCare", "monthly")

        self.assertEqual(student.calc_age(), 22)
        self.assertValue(screen, 240)

    def test_scenario_33_college_student_22_at_the_end_of_the_tax_year(self):
        screen = self.make_screen(household_size=3)
        head = self.member(screen, "headOfHousehold", 45, income={"wages": 64_001})
        self.member(screen, "child", 5)
        self.member(screen, "child", birth_year_month=date(TAX_YEAR - 22, 12, 1), student=True, student_full_time=True)
        self.add_expense(head, 300, "childCare", "monthly")

        self.assertValue(screen, 180)
        self.assertEqual(self.make_calculator(screen)._exemptions, 4_000)

    def test_scenario_34_lower_earning_spouse_caps_the_federal_credit(self):
        screen = self.make_screen(household_size=3)
        head = self.member(screen, "headOfHousehold", 35, income={"wages": 60_000})
        self.member(screen, "spouse", 34, income={"wages": 2_000})
        self.member(screen, "child", 5)
        self.add_expense(head, 300, "childCare", "monthly")

        self.assertValue(screen, 160)

    def test_scenario_35_homeowners_property_tax_counted_in_full(self):
        screen, head = self.parent_with_child(63_000)
        self.add_expense(head, 1_000, "propertyTax", "yearly")

        self.assertValue(screen, 240)
        self.assertEqual(self.make_calculator(screen)._taxable_income, 59_500)


class TestFederalCredit(NjCdccTestCase):
    def test_a_federal_credit_of_0_fails(self):
        """The federal rules can pass while the credit rounds to 0; New Jersey needs it above 0."""
        screen, _ = self.parent_with_child(32_500)

        with patch.object(FederalCdcc, "household_value", return_value=0):
            self.assertIneligible(screen)

    def test_the_value_is_the_bands_share_of_the_federal_credit(self):
        screen, _ = self.parent_with_child(32_500)

        with patch.object(FederalCdcc, "household_value", return_value=1_001):
            # 50% of 1,001 is 500.50, rounded half up.
            self.assertValue(screen, 501)


class TestTaxableIncome(NjCdccTestCase):
    def test_a_spouse_takes_the_senior_and_disabled_exemptions(self):
        screen = self.make_screen(household_size=3)
        self.member(screen, "headOfHousehold", 40, income={"wages": 60_000})
        self.member(screen, "spouse", 66, visually_impaired=True)
        self.member(screen, "child", 5)

        # Head 1,000, spouse 1,000 + 1,000 (65 or older) + 1,000 (blind), child 1,500.
        self.assertEqual(self.make_calculator(screen)._exemptions, 5_500)

    def test_a_domestic_partner_takes_no_exemption(self):
        screen = self.make_screen(household_size=2)
        self.member(screen, "headOfHousehold", 40, income={"wages": 60_000})
        self.member(screen, "domesticPartner", 66, visually_impaired=True)

        self.assertEqual(self.make_calculator(screen)._exemptions, 1_000)

    def test_no_property_tax_deduction_at_or_under_the_filing_threshold(self):
        """A head with a dependent files over 20,000; at 20,000 the deduction isn't taken."""
        screen, head = self.parent_with_child(20_000)
        self.add_expense(head, 1_000, "rent", "monthly")

        self.assertEqual(self.make_calculator(screen)._property_tax_deduction, 0)

    def test_a_single_filer_takes_the_deduction_over_10000(self):
        screen = self.make_screen(household_size=1)
        head = self.member(screen, "headOfHousehold", 40, income={"wages": 10_001})
        self.add_expense(head, 1_000, "rent", "monthly")

        self.assertEqual(self.make_calculator(screen)._property_tax_deduction, 2_160)

    def test_a_single_filer_at_10000_takes_no_deduction(self):
        screen = self.make_screen(household_size=1)
        head = self.member(screen, "headOfHousehold", 40, income={"wages": 10_000})
        self.add_expense(head, 1_000, "rent", "monthly")

        self.assertEqual(self.make_calculator(screen)._property_tax_deduction, 0)

    def test_taxable_income_never_goes_below_0(self):
        screen, head = self.parent_with_child(3_000)
        self.add_expense(head, 1_000, "medical", "monthly")

        self.assertEqual(self.make_calculator(screen)._taxable_income, 0)
