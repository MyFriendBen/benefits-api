from datetime import date
from unittest.mock import Mock

from django.test import TestCase

from programs.programs.co.collegeinvest_first_step.calculator import CoCollegeInvestFirstStep
from programs.util import Dependencies
from screener.models import HouseholdMember, Screen, WhiteLabel


class TestCoCollegeInvestFirstStep(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.white_label = WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")
        cls.mock_program = Mock()

    def _make_screen(self, zipcode: str="80202", county: str="Denver County", household_size: int=2):
        return Screen.objects.create(
            white_label=self.white_label,
            agree_to_tos=True,
            zipcode=zipcode,
            county=county,
            household_size=household_size,
            completed=False,
        )

    def _make_calculator(self, screen):
        return CoCollegeInvestFirstStep(screen, self.mock_program, {}, Dependencies())

    # --- class attributes ---

    def test_member_amount_is_121(self) -> None:
        self.assertEqual(CoCollegeInvestFirstStep.member_amount, 121)

    def test_registered_in_co_calculators(self) -> None:
        from programs.programs.co import co_calculators

        self.assertIn("co_collegeinvest_first_step", co_calculators)
        self.assertIs(co_calculators["co_collegeinvest_first_step"], CoCollegeInvestFirstStep)

    # --- eligible ---

    def test_eligible_newborn(self) -> None:
        """Denver family with newborn child (born 2026, age 0) is eligible."""
        screen = self._make_screen(household_size=2)
        HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=34)
        HouseholdMember.objects.create(screen=screen, relationship="child", age=0, birth_year_month=date(2026, 1, 1))

        calc = self._make_calculator(screen)
        eligibility = calc.eligible()

        self.assertTrue(eligibility.eligible)

    def test_eligible_child_age_7_boundary(self) -> None:
        """Child exactly age 7 is still eligible."""
        screen = self._make_screen(household_size=2)
        HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=35)
        HouseholdMember.objects.create(screen=screen, relationship="child", age=7, birth_year_month=date(2020, 1, 1))

        calc = self._make_calculator(screen)
        eligibility = calc.eligible()

        self.assertTrue(eligibility.eligible)

    def test_eligible_min_birth_year_boundary(self) -> None:
        """Child born January 2020 (minimum birth year) is eligible."""
        screen = self._make_screen(zipcode="80903", county="El Paso County", household_size=2)
        HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=35)
        HouseholdMember.objects.create(screen=screen, relationship="child", age=6, birth_year_month=date(2020, 1, 1))

        calc = self._make_calculator(screen)
        eligibility = calc.eligible()

        self.assertTrue(eligibility.eligible)

    def test_eligible_step_child(self) -> None:
        """stepChild relationship qualifies."""
        screen = self._make_screen(household_size=2)
        HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=35)
        HouseholdMember.objects.create(
            screen=screen, relationship="stepChild", age=3, birth_year_month=date(2023, 1, 1)
        )

        calc = self._make_calculator(screen)
        eligibility = calc.eligible()

        self.assertTrue(eligibility.eligible)

    def test_eligible_foster_child(self) -> None:
        """fosterChild relationship qualifies."""
        screen = self._make_screen(household_size=2)
        HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=35)
        HouseholdMember.objects.create(
            screen=screen, relationship="fosterChild", age=2, birth_year_month=date(2024, 1, 1)
        )

        calc = self._make_calculator(screen)
        eligibility = calc.eligible()

        self.assertTrue(eligibility.eligible)

    def test_eligible_grandchild(self) -> None:
        """grandChild relationship qualifies."""
        screen = self._make_screen(household_size=2)
        HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=50)
        HouseholdMember.objects.create(
            screen=screen, relationship="grandChild", age=1, birth_year_month=date(2025, 1, 1)
        )

        calc = self._make_calculator(screen)
        eligibility = calc.eligible()

        self.assertTrue(eligibility.eligible)

    # --- ineligible ---

    def test_ineligible_child_too_old(self) -> None:
        """Child aged 8 or older is not eligible — primary exclusion."""
        screen = self._make_screen(household_size=2)
        HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=36)
        HouseholdMember.objects.create(screen=screen, relationship="child", age=9, birth_year_month=date(2017, 1, 1))

        calc = self._make_calculator(screen)
        eligibility = calc.eligible()

        self.assertFalse(eligibility.eligible)

    def test_ineligible_child_age_8_boundary(self) -> None:
        """Child exactly age 8 is not eligible."""
        screen = self._make_screen(household_size=2)
        HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=35)
        HouseholdMember.objects.create(screen=screen, relationship="child", age=8, birth_year_month=date(2018, 1, 1))

        calc = self._make_calculator(screen)
        eligibility = calc.eligible()

        self.assertFalse(eligibility.eligible)

    def test_ineligible_birth_year_2019(self) -> None:
        """Child born in 2019 (age ≤ 7) is excluded by the birth year cutoff."""
        screen = self._make_screen(household_size=2)
        HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=35)
        HouseholdMember.objects.create(screen=screen, relationship="child", age=6, birth_year_month=date(2019, 6, 1))

        calc = self._make_calculator(screen)
        eligibility = calc.eligible()

        self.assertFalse(eligibility.eligible)

    def test_ineligible_no_children(self) -> None:
        """Household with no children is not eligible."""
        screen = self._make_screen(household_size=2)
        HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=38)
        HouseholdMember.objects.create(screen=screen, relationship="spouse", age=35)

        calc = self._make_calculator(screen)
        eligibility = calc.eligible()

        self.assertFalse(eligibility.eligible)

    def test_ineligible_non_child_relationship(self) -> None:
        """Members with non-child relationships do not qualify."""
        screen = self._make_screen(household_size=2)
        HouseholdMember.objects.create(
            screen=screen, relationship="headOfHousehold", age=5, birth_year_month=date(2021, 1, 1)
        )
        HouseholdMember.objects.create(screen=screen, relationship="sibling", age=3, birth_year_month=date(2023, 1, 1))

        calc = self._make_calculator(screen)
        eligibility = calc.eligible()

        self.assertFalse(eligibility.eligible)

    # --- benefit value ---

    def test_value_single_eligible_child(self) -> None:
        """Single eligible child yields $121."""
        screen = self._make_screen(household_size=2)
        HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=34)
        HouseholdMember.objects.create(screen=screen, relationship="child", age=0, birth_year_month=date(2026, 1, 1))

        calc = self._make_calculator(screen)
        eligibility = calc.eligible()
        calc.value(eligibility)

        self.assertEqual(eligibility.value, 121)

    def test_value_two_eligible_children(self) -> None:
        """Two eligible children yield $242 (2 × $121)."""
        screen = self._make_screen(household_size=4)
        HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=35)
        HouseholdMember.objects.create(screen=screen, relationship="spouse", age=34)
        HouseholdMember.objects.create(screen=screen, relationship="child", age=3, birth_year_month=date(2023, 2, 1))
        HouseholdMember.objects.create(screen=screen, relationship="child", age=0, birth_year_month=date(2026, 3, 1))

        calc = self._make_calculator(screen)
        eligibility = calc.eligible()
        calc.value(eligibility)

        self.assertEqual(eligibility.value, 242)

    def test_value_mixed_eligible_and_ineligible_children(self) -> None:
        """Only qualifying children count toward the value; over-age child excluded."""
        screen = self._make_screen(household_size=3)
        HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=35)
        HouseholdMember.objects.create(screen=screen, relationship="child", age=9, birth_year_month=date(2017, 1, 1))
        HouseholdMember.objects.create(screen=screen, relationship="child", age=2, birth_year_month=date(2024, 1, 1))

        calc = self._make_calculator(screen)
        eligibility = calc.eligible()
        calc.value(eligibility)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 121)
