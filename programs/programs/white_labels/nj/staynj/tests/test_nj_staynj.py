"""
NJ Stay NJ property tax credit.

Builds real Screen/HouseholdMember/IncomeStream/Expense rows and runs the real `calc()`, since
eligibility and the offsets come from expenses, relationships and income types a Mock would only
restate. Every spec §8 scenario has a test named for it; the rest cover the value floor, the
county fallbacks, each excluded income type and the missing-field guard.

The spec's amounts with cents are asserted with the cents dropped (1,382.50 → 1,382), as the API
drops them. The calculator never reads `self.program`, so no Program row is built.
"""

from datetime import date
from typing import Optional

from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from programs.programs.white_labels.nj.anchor.calculator import NjAnchor
from programs.programs.white_labels.nj.staynj.calculator import SOCIAL_SECURITY_TYPES, NjStayNj
from programs.util import DependencyError
from screener.models import Expense, HouseholdMember, Screen


def born_in(year: int) -> date:
    """A birth month giving the stated age on December 31, 2025 for a member born in `year`."""
    return date(year, 6, 1)


class NjStayNjTestCase(CustomCalculatorTestCase):
    calculator_class = NjStayNj
    white_label_code = "nj"
    state_code = "NJ"
    default_zipcode = "08608"
    default_county = "Mercer County"
    needs_program_row = False

    def senior(
        self,
        pension: int = 60_000,
        property_tax: Optional[int] = 9_000,
        household_size: int = 1,
        **screen_kwargs,
    ) -> tuple[Screen, HouseholdMember]:
        """A 70-year-old head with a pension and, unless `property_tax` is None, property tax."""
        screen = self.make_screen(household_size=household_size, **screen_kwargs)
        head = self.add_member(screen, "headOfHousehold", 70, yearly_income=pension, income_type="pension")
        if property_tax is not None:
            self.add_expense(head, property_tax, "propertyTax", "yearly")
        return screen, head


class TestRegistration(NjStayNjTestCase):
    def test_program_code(self):
        self.assertEqual(NjStayNj.program_code, "nj_staynj")

    def test_income_counts_social_security_but_otherwise_follows_nj_gross_income(self):
        self.assertEqual(
            sorted(NjStayNj.excluded_income_types),
            sorted(
                ["unemployment", "childSupport", "sSI", "workersComp", "gifts", "cashAssistance"]
                + ["cashAssistanceOther", "veteran"]
            ),
        )
        for income_type in SOCIAL_SECURITY_TYPES:
            self.assertIn(income_type, NjAnchor.excluded_income_types)

    def test_missing_expense_amount_drops_the_program(self):
        screen, head = self.senior(property_tax=None)
        Expense.objects.create(
            screen=screen, household_member=head, type="propertyTax", amount=None, frequency="yearly"
        )

        with self.assertRaises(DependencyError):
            self.calculate(screen, missing=screen.missing_fields())


class TestSpecScenarios(NjStayNjTestCase):
    def assert_value(self, screen: Screen, value: int) -> None:
        e = self.calculate(screen)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, value)

    def assert_ineligible(self, screen: Screen) -> None:
        e = self.calculate(screen)
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

    def test_1_senior_homeowner_golden_path(self):
        self.assert_value(self.senior()[0], 1_118)

    def test_2_taxes_above_the_cap(self):
        self.assert_value(self.senior(property_tax=20_000)[0], 2_118)

    def test_3_social_security_puts_staynj_income_over_150000_but_not_anchor_income(self):
        screen, head = self.senior(pension=140_000)
        self.add_income(head, 20_000, "sSRetirement", "yearly")

        self.assert_value(screen, 1_118)

    def test_4_income_one_dollar_over_the_100000_tier_boundary(self):
        self.assert_value(self.senior(pension=100_001, property_tax=20_000)[0], 2_118)

    def test_5_income_at_the_150000_tier_boundary(self):
        self.assert_value(self.senior(pension=150_000, property_tax=20_000)[0], 2_118)

    def test_6_income_one_dollar_over_the_150000_boundary(self):
        self.assert_value(self.senior(pension=150_001)[0], 1_368)

    def test_7_income_at_the_senior_freeze_proxy_limit(self):
        self.assert_value(self.senior(pension=168_268)[0], 1_368)

    def test_8_income_one_dollar_over_the_senior_freeze_proxy_limit(self):
        self.assert_value(self.senior(pension=168_269)[0], 1_750)

    def test_9_income_at_the_200000_limit(self):
        self.assert_value(self.senior(pension=200_000, property_tax=20_000)[0], 2_000)

    def test_10_income_one_dollar_over_the_200000_limit(self):
        self.assert_ineligible(self.senior(pension=200_001, property_tax=20_000)[0])

    def test_11_low_property_taxes_offsets_exceed_half_the_tax(self):
        # Eligible at 0, so the frontend hides it; the household is shown ANCHOR on the same PAS-1.
        self.assert_value(self.senior(property_tax=2_000)[0], 0)

    def test_12_mortgage_only_county_average_tax(self):
        screen, head = self.senior(property_tax=None)
        self.add_expense(head, 15_000, "mortgage", "yearly")

        self.assert_value(screen, 1_382)

    def test_13_senior_renter(self):
        screen, head = self.senior(property_tax=None)
        self.add_expense(head, 18_000, "rent", "yearly")

        self.assert_ineligible(screen)

    def test_14_senior_with_no_housing_expense(self):
        self.assert_ineligible(self.senior(property_tax=None)[0])

    def test_15_head_exactly_65_at_the_end_of_2025(self):
        screen = self.make_screen()
        head = self.add_member(
            screen, "headOfHousehold", None, yearly_income=60_000, income_type="pension", birth_year_month=born_in(1960)
        )
        self.add_expense(head, 9_000, "propertyTax", "yearly")

        self.assert_value(screen, 1_118)

    def test_16_head_64_at_the_end_of_2025(self):
        screen = self.make_screen()
        head = self.add_member(
            screen, "headOfHousehold", None, yearly_income=60_000, income_type="pension", birth_year_month=born_in(1961)
        )
        self.add_expense(head, 9_000, "propertyTax", "yearly")

        self.assert_ineligible(screen)

    def test_17_younger_head_with_a_spouse_over_65(self):
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", 60, yearly_income=30_000)
        self.add_member(screen, "spouse", 66, yearly_income=30_000, income_type="pension")
        self.add_expense(head, 9_000, "propertyTax", "yearly")

        self.assert_value(screen, 1_118)

    def test_18_younger_head_with_a_domestic_partner_over_65(self):
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", 60, yearly_income=60_000)
        self.add_member(screen, "domesticPartner", 70, yearly_income=20_000, income_type="pension")
        self.add_expense(head, 9_000, "propertyTax", "yearly")

        self.assert_ineligible(screen)

    def test_19_younger_head_with_a_parent_over_65(self):
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", 45, yearly_income=60_000)
        self.add_member(screen, "parent", 75, yearly_income=18_000, income_type="sSRetirement")
        self.add_expense(head, 9_000, "propertyTax", "yearly")

        self.assert_ineligible(screen)

    def test_20_spouses_combined_income_over_the_limit(self):
        screen, _ = self.senior(pension=120_000, household_size=2)
        self.add_member(screen, "spouse", 68, yearly_income=90_000, income_type="pension")

        self.assert_ineligible(screen)

    def test_21_excluded_income_left_out(self):
        screen, head = self.senior(pension=190_000, property_tax=16_000)
        self.add_income(head, 20_000, "unemployment", "yearly")

        self.assert_value(screen, 2_000)

    def test_22_social_security_counted(self):
        screen, head = self.senior(pension=180_000)
        self.add_income(head, 25_000, "sSRetirement", "yearly")

        self.assert_ineligible(screen)

    def test_23_mortgage_only_no_county_statewide_averages(self):
        screen, head = self.senior(property_tax=None, county=None)
        self.add_expense(head, 15_000, "mortgage", "yearly")

        self.assert_value(screen, 1_503)

    def test_24_mortgage_and_rent_both_entered(self):
        screen, head = self.senior(property_tax=None)
        self.add_expense(head, 15_000, "mortgage", "yearly")
        self.add_expense(head, 12_000, "rent", "yearly")

        self.assert_ineligible(screen)

    def test_25_excluded_income_types_left_out(self):
        screen, head = self.senior(pension=150_000, property_tax=20_000)
        for amount, income_type in [
            (10_000, "sSI"),
            (10_000, "workersComp"),
            (10_000, "gifts"),
            (5_000, "childSupport"),
            (5_000, "cashAssistance"),
            (5_000, "cashAssistanceOther"),
            (20_000, "veteran"),
        ]:
            self.add_income(head, amount, income_type, "yearly")

        self.assert_value(screen, 2_118)

    def test_26_hoa_fees_only_county_average_tax(self):
        screen, head = self.senior(property_tax=None)
        self.add_expense(head, 3_600, "hoa", "yearly")

        self.assert_value(screen, 1_382)

    def test_27_homeowners_insurance_only_county_average_tax(self):
        screen, head = self.senior(property_tax=None)
        self.add_expense(head, 1_800, "homeownersInsurance", "yearly")

        self.assert_value(screen, 1_382)

    def test_28_hoa_fees_and_rent_both_entered(self):
        screen, head = self.senior(property_tax=None)
        self.add_expense(head, 3_600, "hoa", "yearly")
        self.add_expense(head, 12_000, "rent", "yearly")

        self.assert_ineligible(screen)

    def test_29_domestic_partners_income_not_combined(self):
        screen, _ = self.senior(pension=150_000, property_tax=20_000, household_size=2)
        self.add_member(screen, "domesticPartner", 68, yearly_income=60_000, income_type="pension")

        self.assert_value(screen, 2_118)

    def test_30_adult_childs_income_not_combined(self):
        screen, _ = self.senior(pension=150_000, property_tax=20_000, household_size=2)
        self.add_member(screen, "child", 40, yearly_income=60_000)

        self.assert_value(screen, 2_118)

    def test_31_income_one_dollar_over_150000_payment_limit_binds(self):
        self.assert_value(self.senior(pension=150_001, property_tax=20_000)[0], 2_000)

    def test_32_senior_homeowner_in_a_second_county(self):
        self.assert_value(self.senior(zipcode="07601", county="Bergen County")[0], 1_006)


class TestValue(NjStayNjTestCase):
    def test_anchor_offset_falls_to_property_tax_below_the_anchor_cap(self):
        # 50% × 1,200 − min(1,200, 1,500) is negative, so the remainder floors at 0.
        e = self.calculate(self.senior(property_tax=1_200)[0])

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 0)

    def test_senior_freeze_estimate_can_use_up_the_remainder(self):
        # 50% × 4,500 − 1,500 = 750 is under Mercer's 764 Senior Freeze average.
        self.assertEqual(self.calculate(self.senior(property_tax=4_500)[0]).value, 0)

    def test_county_not_in_the_table_uses_statewide_averages(self):
        screen, head = self.senior(property_tax=None, county="Not A County")
        self.add_expense(head, 15_000, "mortgage", "yearly")

        self.assertEqual(self.calculate(screen).value, 1_503)

    def test_entered_property_tax_overrides_the_county_average(self):
        e = self.calculate(self.senior(property_tax=12_000)[0])

        # min(6,000, 6,500) − 1,500 − 764 = 3,736; × 2/4 = 1,868.
        self.assertEqual(e.value, 1_868)

    def test_every_county_has_both_averages(self):
        self.assertEqual(len(NjStayNj.county_averages), 21)
        for county, (tax, senior_freeze) in NjStayNj.county_averages.items():
            with self.subTest(county=county):
                self.assertGreater(tax, 0)
                self.assertGreater(senior_freeze, 0)

    def test_monthly_property_tax_is_annualized(self):
        screen, head = self.senior(property_tax=None)
        self.add_expense(head, 750, "propertyTax", "monthly")

        self.assertEqual(self.calculate(screen).value, 1_118)


class TestIncome(NjStayNjTestCase):
    def test_every_excluded_type_is_left_out(self):
        for income_type in NjStayNj.excluded_income_types:
            with self.subTest(income_type=income_type):
                screen, head = self.senior()
                self.add_income(head, 300_000, income_type, "yearly")

                self.assertTrue(self.calculate(screen).eligible)

    def test_every_social_security_type_is_counted(self):
        for income_type in SOCIAL_SECURITY_TYPES:
            with self.subTest(income_type=income_type):
                screen, head = self.senior(pension=0)
                self.add_income(head, 200_001, income_type, "yearly")

                self.assertFalse(self.calculate(screen).eligible)
