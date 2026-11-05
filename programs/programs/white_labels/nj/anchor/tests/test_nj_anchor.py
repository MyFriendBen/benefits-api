"""
NJ ANCHOR property tax relief.

Builds real Screen/HouseholdMember/IncomeStream/Expense rows and runs the real `calc()`, since
the route and the claimants come from expenses and relationships a Mock would only restate.
Every spec §8 scenario has a test named for it; the rest cover the excluded income types,
the value floor and the missing-field guard.

The calculator never reads `self.program`, so no Program row is built.
"""

from datetime import date

from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from programs.programs.white_labels.nj.anchor.calculator import NjAnchor
from programs.util import DependencyError
from screener.models import Expense, HouseholdMember, Screen


def born_in(year: int) -> date:
    """A birth month giving the stated age on December 31, 2025 for a member born in `year`."""
    return date(year, 6, 1)


class NjAnchorTestCase(CustomCalculatorTestCase):
    calculator_class = NjAnchor
    white_label_code = "nj"
    state_code = "NJ"
    default_zipcode = "08608"
    default_county = "Mercer County"
    needs_program_row = False

    def head(self, wages: int, age: float | None = 45, **kwargs) -> tuple[Screen, HouseholdMember]:
        """A one-person household whose head earns `wages` a year."""
        screen = self.make_screen(household_size=kwargs.pop("household_size", 1))
        if "birth_year_month" in kwargs:
            age = None
        head = self.add_member(screen, "headOfHousehold", age, yearly_income=wages, **kwargs)
        return screen, head

    def homeowner(self, wages: int, property_tax: int = 8_000, **kwargs) -> Screen:
        screen, head = self.head(wages, **kwargs)
        self.add_expense(head, property_tax, "propertyTax", "yearly")
        return screen

    def renter(self, wages: int, rent: int = 1_500, **kwargs) -> tuple[Screen, HouseholdMember]:
        screen, head = self.head(wages, **kwargs)
        self.add_expense(head, rent, "rent", "monthly")
        return screen, head


class TestRegistration(NjAnchorTestCase):
    def test_program_code(self):
        self.assertEqual(NjAnchor.program_code, "nj_anchor")

    def test_missing_expense_amount_drops_the_program(self):
        screen, head = self.head(60_000)
        Expense.objects.create(screen=screen, household_member=head, type="rent", amount=None, frequency="monthly")

        with self.assertRaises(DependencyError):
            self.calculate(screen, missing=screen.missing_fields())


class TestSpecScenarios(NjAnchorTestCase):
    def test_1_homeowner_with_property_taxes_above_the_cap(self):
        e = self.calculate(self.homeowner(60_000, property_tax=9_000))

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 1_500)

    def test_2_homeowner_with_property_taxes_below_the_cap(self):
        e = self.calculate(self.homeowner(60_000, property_tax=1_200))

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 1_200)

    def test_3_homeowner_at_the_150000_cap_boundary(self):
        e = self.calculate(self.homeowner(150_000))

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 1_500)

    def test_4_homeowner_one_dollar_over_the_150000_cap_boundary(self):
        e = self.calculate(self.homeowner(150_001))

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 1_000)

    def test_5_homeowner_at_the_250000_income_limit(self):
        e = self.calculate(self.homeowner(250_000))

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 1_000)

    def test_6_homeowner_one_dollar_over_the_income_limit(self):
        e = self.calculate(self.homeowner(250_001))

        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

    def test_7_homeowner_who_entered_only_a_mortgage(self):
        screen, head = self.head(80_000)
        self.add_expense(head, 2_000, "mortgage", "monthly")

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 1_500)

    def test_8_no_rent_mortgage_or_property_tax(self):
        screen, _ = self.head(60_000)

        e = self.calculate(screen)

        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

    def test_9_renter_who_was_64_at_the_end_of_2025(self):
        screen, _ = self.renter(40_000, birth_year_month=born_in(1961))

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 450)

    def test_10_renter_who_turned_65_by_the_end_of_2025(self):
        screen = self.make_screen()
        head = self.add_member(
            screen,
            "headOfHousehold",
            None,
            yearly_income=24_000,
            income_type="sSRetirement",
            birth_year_month=born_in(1960),
        )
        self.add_expense(head, 1_000, "rent", "monthly")

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 700)

    def test_11_renter_at_the_150000_income_limit(self):
        screen, _ = self.renter(150_000, rent=2_000, age=40)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 450)

    def test_12_renter_one_dollar_over_the_income_limit(self):
        screen, _ = self.renter(150_001, rent=2_000, age=40)

        e = self.calculate(screen)

        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

    def test_13_household_paying_both_rent_and_a_mortgage(self):
        screen, head = self.renter(200_000, rent=1_000)
        self.add_expense(head, 1_500, "mortgage", "monthly")

        e = self.calculate(screen)

        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

    def test_14_renter_couple_where_only_the_spouse_is_65_or_older(self):
        screen, _ = self.renter(50_000, rent=1_200, age=60, household_size=2)
        self.add_member(screen, "spouse", None, birth_year_month=born_in(1959))

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 700)

    def test_15_spouse_social_security_is_not_counted(self):
        screen, _ = self.renter(130_000, age=50, household_size=2)
        self.add_member(screen, "spouse", 52, yearly_income=30_000, income_type="sSDisability")

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 450)

    def test_16_adult_child_income_is_not_counted(self):
        screen, _ = self.renter(100_000, rent=1_800, age=55, household_size=2)
        self.add_member(screen, "child", 25, yearly_income=60_000)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 450)

    def test_17_renter_couple_whose_combined_income_exceeds_the_limit(self):
        screen, _ = self.renter(100_000, age=40, household_size=2)
        self.add_member(screen, "spouse", 40, yearly_income=60_000)

        e = self.calculate(screen)

        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

    def test_18_renter_living_with_a_domestic_partner(self):
        screen, _ = self.renter(100_000, age=40, household_size=2)
        self.add_member(screen, "domesticPartner", None, yearly_income=60_000, birth_year_month=born_in(1959))

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 450)

    def test_19_homeowner_who_was_66_at_the_end_of_2025(self):
        screen = self.homeowner(60_000, property_tax=9_000, birth_year_month=born_in(1959))

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 1_500)

    def test_20_homeowner_with_a_mortgage_and_property_taxes_below_the_cap(self):
        screen = self.homeowner(60_000, property_tax=1_200)
        self.add_expense(screen.get_head(), 1_500, "mortgage", "monthly")

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 1_200)


class TestIncome(NjAnchorTestCase):
    def test_every_excluded_type_is_left_out(self):
        for income_type in NjAnchor.excluded_income_types:
            with self.subTest(income_type=income_type):
                screen, head = self.renter(0)
                self.add_income(head, 200_000, income_type, "yearly")

                self.assertTrue(self.calculate(screen).eligible)

    def test_counted_unearned_income_is_included(self):
        screen, head = self.renter(100_000)
        self.add_income(head, 60_000, "pension", "yearly")

        self.assertFalse(self.calculate(screen).eligible)

    def test_mortgage_holder_over_150000_gets_the_lower_cap(self):
        screen, head = self.head(200_000)
        self.add_expense(head, 2_000, "mortgage", "monthly")

        self.assertEqual(self.calculate(screen).value, 1_000)


class TestValue(NjAnchorTestCase):
    def test_a_few_cents_of_property_tax_is_floored_at_one(self):
        screen = self.homeowner(60_000, property_tax=0)
        Expense.objects.filter(screen=screen).update(amount=0.5)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 1)

    def test_renter_with_no_birth_date_gets_no_supplement(self):
        screen, head = self.renter(40_000)
        head.birth_year_month = None
        head.age = None
        head.save()

        self.assertEqual(self.calculate(screen).value, 450)
