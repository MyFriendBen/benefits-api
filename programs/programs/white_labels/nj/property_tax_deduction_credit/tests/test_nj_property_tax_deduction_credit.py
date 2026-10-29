"""
NJ Property Tax Deduction/Credit.

Builds real Screen/HouseholdMember/IncomeStream/Expense rows and runs the real `calc()`. Every
spec §8 scenario has a test named for it; the rest cover the exemptions, the pension
exclusion's disability path, the tax year and the missing-field guard.

Ages in the spec are ages at the end of 2025, so members are built from a birth year rather
than today's age. Values are whole dollars, rounded half up from the spec's cents.
"""

from datetime import date

from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from programs.programs.white_labels.nj.property_tax_deduction_credit.calculator import NjPropertyTaxDeductionCredit
from programs.util import DependencyError
from screener.models import Expense, HouseholdMember, Screen


def born_for_age_at_end_of(age: int, year: int = 2025) -> date:
    """A birth month giving the stated age on December 31 of `year`."""
    return date(year - age, 6, 1)


class NjPtdTestCase(CustomCalculatorTestCase):
    calculator_class = NjPropertyTaxDeductionCredit
    white_label_code = "nj"
    state_code = "NJ"
    default_zipcode = "07102"
    default_county = "Essex County"
    fpl_year = "2025"

    def member(self, screen: Screen, relationship: str, age: int, **kwargs) -> HouseholdMember:
        """A member whose `age` is their age at the end of 2025."""
        return self.add_member(screen, relationship, None, birth_year_month=born_for_age_at_end_of(age), **kwargs)

    def household(self, *members: tuple[str, int, dict]) -> tuple[Screen, list[HouseholdMember]]:
        screen = self.make_screen(household_size=len(members))
        return screen, [self.member(screen, relationship, age, **kwargs) for relationship, age, kwargs in members]

    def assertValue(self, screen: Screen, value: int) -> None:
        e = self.calculate(screen)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, value)

    def assertIneligible(self, screen: Screen) -> None:
        e = self.calculate(screen)
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)


class TestRegistration(NjPtdTestCase):
    def test_program_code(self):
        self.assertEqual(NjPropertyTaxDeductionCredit.program_code, "nj_property_tax_deduction_credit")

    def test_constants(self):
        c = NjPropertyTaxDeductionCredit
        self.assertEqual((c.filing_threshold_joint, c.filing_threshold_single), (20_000, 10_000))
        self.assertEqual((c.credit_amount, c.deduction_cap, str(c.rent_as_property_tax)), (50, 15_000, "0.18"))

    def test_missing_expense_amount_drops_the_program(self):
        screen, (head,) = self.household(("headOfHousehold", 40, {"yearly_income": 30_000}))
        Expense.objects.create(screen=screen, household_member=head, type="rent", amount=None, frequency="monthly")

        with self.assertRaises(DependencyError):
            self.calculate(screen, missing=screen.missing_fields())


class TestBirthAfterTheTaxYear(NjPtdTestCase):
    def test_a_member_born_after_the_tax_year_is_not_a_senior(self):
        screen, _ = self.household(("headOfHousehold", 40, {}))
        newborn = self.add_member(screen, "child", None, birth_year_month=date(2026, 1, 1))
        calculator = self.make_calculator(screen)

        self.assertEqual(calculator._age_at_year_end(newborn), 0)
        self.assertFalse(calculator._is_senior(newborn))


class TestSpecScenarios(NjPtdTestCase):
    def test_1_renting_couple_with_one_child_on_moderate_wages(self):
        screen, (head, _, _) = self.household(
            ("headOfHousehold", 35, {"monthly_income": 4_000}), ("spouse", 34, {}), ("child", 6, {})
        )
        self.add_expense(head, 1_800, "rent", "monthly")
        self.assertValue(screen, 68)

    def test_2_single_homeowner_paying_9000_in_property_tax(self):
        screen, (head,) = self.household(("headOfHousehold", 45, {"monthly_income": 5_500}))
        self.add_expense(head, 750, "propertyTax", "monthly")
        self.assertValue(screen, 497)

    def test_3_property_tax_above_the_15000_cap(self):
        screen, (head, _) = self.household(("headOfHousehold", 50, {"monthly_income": 12_000}), ("spouse", 48, {}))
        self.add_expense(head, 20_000, "propertyTax", "yearly")
        # Spec: 828.75.
        self.assertValue(screen, 829)

    def test_4_low_rent_where_the_deduction_is_worth_less_than_50(self):
        screen, (head,) = self.household(("headOfHousehold", 30, {"monthly_income": 1_500}))
        self.add_expense(head, 600, "rent", "monthly")
        self.assertValue(screen, 50)

    def couple(self, wages: int) -> Screen:
        screen, (head, _) = self.household(("headOfHousehold", 40, {"yearly_income": wages}), ("spouse", 38, {}))
        self.add_expense(head, 1_000, "rent", "monthly")
        return screen

    def test_5_couple_exactly_at_the_20000_threshold(self):
        self.assertIneligible(self.couple(20_000))

    def test_6_couple_1_over_the_20000_threshold(self):
        self.assertValue(self.couple(20_001), 50)

    def single(self, wages: int) -> Screen:
        screen, (head,) = self.household(("headOfHousehold", 30, {"yearly_income": wages}))
        self.add_expense(head, 800, "rent", "monthly")
        return screen

    def test_7_single_filer_exactly_at_the_10000_threshold(self):
        self.assertIneligible(self.single(10_000))

    def test_8_single_filer_1_over_the_10000_threshold(self):
        self.assertValue(self.single(10_001), 50)

    def test_9_senior_living_on_social_security(self):
        screen, (head,) = self.household(
            ("headOfHousehold", 70, {"monthly_income": 2_500, "income_type": "sSRetirement"})
        )
        self.add_expense(head, 1_500, "rent", "monthly")
        self.assertValue(screen, 50)

    def low_income(self, age: int, **kwargs) -> Screen:
        screen, (head,) = self.household(("headOfHousehold", age, {"monthly_income": 700, **kwargs}))
        self.add_expense(head, 900, "rent", "monthly")
        return screen

    def test_10_age_64_below_the_threshold(self):
        self.assertIneligible(self.low_income(64))

    def test_11_age_65_below_the_threshold(self):
        self.assertValue(self.low_income(65), 50)

    def test_12_blind_filer_under_65_below_the_threshold(self):
        self.assertValue(self.low_income(40, visually_impaired=True), 50)

    def test_13_disabled_filer_under_65_below_the_threshold(self):
        self.assertValue(self.low_income(50, disabled=True), 50)

    def test_14_no_rent_or_property_tax_entered(self):
        screen, _ = self.household(("headOfHousehold", 40, {"monthly_income": 3_500}))
        self.assertIneligible(screen)

    def test_15_deduction_that_crosses_a_bracket_boundary(self):
        screen, (head,) = self.household(("headOfHousehold", 30, {"monthly_income": 3_500}))
        self.add_expense(head, 1_400, "rent", "monthly")
        self.assertValue(screen, 127)

    def test_16_single_parent_at_12000(self):
        screen, (head, _) = self.household(("headOfHousehold", 30, {"monthly_income": 1_000}), ("child", 5, {}))
        self.add_expense(head, 900, "rent", "monthly")
        self.assertIneligible(screen)

    def test_17_single_parent_1_over_the_20000_threshold(self):
        screen, (head, _) = self.household(("headOfHousehold", 30, {"yearly_income": 20_001}), ("child", 5, {}))
        self.add_expense(head, 1_000, "rent", "monthly")
        self.assertValue(screen, 50)

    def test_18_retiree_at_63_whose_pension_is_excluded(self):
        screen, (head,) = self.household(("headOfHousehold", 63, {"monthly_income": 2_500, "income_type": "pension"}))
        self.add_expense(head, 1_500, "rent", "monthly")
        self.assertIneligible(screen)

    def retired_couple(self, pension: int, property_tax: int = 6_000, medical: int = 0) -> Screen:
        screen, (head, _) = self.household(
            ("headOfHousehold", 70, {"yearly_income": pension, "income_type": "pension"}), ("spouse", 70, {})
        )
        self.add_expense(head, property_tax, "propertyTax", "yearly")
        if medical:
            self.add_expense(head, medical, "medical", "yearly")
        return screen

    def test_19_retired_couple_with_a_100000_pension(self):
        self.assertValue(self.retired_couple(100_000), 50)

    def test_20_retired_couple_with_a_100001_pension(self):
        self.assertValue(self.retired_couple(100_001), 105)

    def test_21_retired_couple_with_a_125000_pension(self):
        self.assertValue(self.retired_couple(125_000), 147)

    def test_22_retired_couple_with_a_125001_pension(self):
        self.assertValue(self.retired_couple(125_001), 331)

    def test_23_retired_couple_with_a_150000_pension_and_medical_bills(self):
        self.assertValue(self.retired_couple(150_000, property_tax=15_000, medical=20_000), 743)

    def test_24_retired_couple_with_a_150001_pension_and_medical_bills(self):
        # Spec: 828.75.
        self.assertValue(self.retired_couple(150_001, property_tax=15_000, medical=20_000), 829)

    def single_retiree(self, pension: int) -> Screen:
        screen, (head,) = self.household(("headOfHousehold", 63, {"yearly_income": pension, "income_type": "pension"}))
        self.add_income(head, 10_000, "wages", "yearly")
        self.add_expense(head, 1_000, "rent", "monthly")
        return screen

    def test_25_single_retiree_at_63_with_a_75000_pension_and_10000_in_wages(self):
        self.assertIneligible(self.single_retiree(75_000))

    def test_26_single_retiree_at_63_with_a_75001_pension_and_10000_in_wages(self):
        self.assertValue(self.single_retiree(75_001), 50)

    def test_27_domestic_partners_under_65_each_earning_8000(self):
        screen, (head, _) = self.household(
            ("headOfHousehold", 40, {"yearly_income": 8_000}), ("domesticPartner", 40, {"yearly_income": 8_000})
        )
        self.add_expense(head, 1_000, "rent", "monthly")
        self.assertIneligible(screen)


class TestExemptions(NjPtdTestCase):
    def exemptions(self, screen: Screen) -> int:
        return self.make_calculator(screen)._exemptions

    def test_filers_take_senior_disability_and_veteran_exemptions(self):
        screen, _ = self.household(
            ("headOfHousehold", 66, {"veteran": True, "disabled": True}), ("spouse", 60, {}), ("child", 10, {})
        )
        # Two personal, one senior, one disability, one veteran, one dependent.
        self.assertEqual(self.exemptions(screen), 1_000 * 2 + 1_000 + 1_000 + 6_000 + 1_500)

    def test_a_domestic_partner_takes_only_the_personal_exemption(self):
        screen, _ = self.household(
            ("headOfHousehold", 40, {}), ("domesticPartner", 70, {"veteran": True, "visually_impaired": True})
        )
        self.assertEqual(self.exemptions(screen), 1_000 * 2)

    def test_a_veteran_exemption_lowers_the_saving_band(self):
        """A head with 6,000 more in exemptions is taxed in a lower band, so the deduction saves less."""
        values = []
        for veteran in (False, True):
            screen, (head,) = self.household(("headOfHousehold", 45, {"yearly_income": 46_000, "veteran": veteran}))
            self.add_expense(head, 8_000, "propertyTax", "yearly")
            values.append(self.calculate(screen).value)

        self.assertGreater(values[0], values[1])


class TestPensionExclusion(NjPtdTestCase):
    def test_a_disabled_filer_under_62_has_their_pension_excluded(self):
        screen, (head,) = self.household(
            ("headOfHousehold", 50, {"yearly_income": 30_000, "income_type": "pension", "disabled": True})
        )
        self.add_expense(head, 1_500, "rent", "monthly")

        self.assertEqual(self.make_calculator(screen)._gross_income, 0)
        self.assertValue(screen, 50)

    def test_a_filer_under_62_without_a_disability_counts_their_pension(self):
        screen, (head,) = self.household(("headOfHousehold", 50, {"yearly_income": 30_000, "income_type": "pension"}))
        self.add_expense(head, 1_500, "rent", "monthly")

        self.assertEqual(self.make_calculator(screen)._gross_income, 30_000)

    def test_a_domestic_partners_income_is_not_counted(self):
        screen, (head, _) = self.household(
            ("headOfHousehold", 40, {"yearly_income": 30_000}), ("domesticPartner", 40, {"yearly_income": 90_000})
        )
        self.add_expense(head, 1_500, "rent", "monthly")

        self.assertEqual(self.make_calculator(screen)._gross_income, 30_000)


class TestTaxYear(NjPtdTestCase):
    """The age test follows the program's tax year, not the screening date."""

    fpl_year = "2026"

    def test_a_filer_65_at_the_end_of_the_programs_tax_year_qualifies(self):
        # 64 at the end of 2025, 65 at the end of 2026.
        screen = self.make_screen()
        head = self.add_member(screen, "headOfHousehold", None, birth_year_month=date(1961, 6, 1), monthly_income=700)
        self.add_expense(head, 900, "rent", "monthly")

        self.assertValue(screen, 50)
