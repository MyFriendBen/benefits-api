"""
CESN Property Tax/Rent/Heat Credit Rebate: the "not a dependent" gate is judged on the claim year.

The qualifying-relative income limit is the tax year's (5,200 for 2025), not the screening
year's (5,300 for 2026). A 70-year-old parent earning 5,250 sits between the two: a dependent
under the 2026 limit, not one under the 2025 limit, so they can claim the rebate for 2025.

Real Screen/HouseholdMember/IncomeStream rows, with the screening date pinned late in the
year after the tax year.
"""

from datetime import date

from programs.framework.base import Eligibility
from programs.programs.cross_white_label.cpcr.cesn import EnergyCalculatorPropertyCreditRebate
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from screener.models import EnergyCalculatorMember, HouseholdMember, Screen


class TestCesnDependentGateUsesTheTaxYear(CustomCalculatorTestCase):
    calculator_class = EnergyCalculatorPropertyCreditRebate
    white_label_code = "cesn"
    state_code = "CO"
    fpl_year = "2025"
    reference_date = date(2026, 11, 11)

    def household_with_parent_earning(self, parent_income: int) -> tuple[Screen, HouseholdMember]:
        """A 45-year-old head and their 70-year-old parent; only the parent can qualify by age."""
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", None, birth_year_month=date(1980, 6, 1), yearly_income=10_000)
        parent = self.add_member(screen, "parent", None, birth_year_month=date(1955, 6, 1), yearly_income=parent_income)
        for member in (head, parent):
            EnergyCalculatorMember.objects.create(household_member=member)
        return screen, parent

    def parent_eligible(self, e: Eligibility, parent: HouseholdMember) -> bool:
        (result,) = [m for m in e.eligible_members if m.member.id == parent.id]
        return result.eligible

    def test_the_tax_year_is_2025(self) -> None:
        screen, _ = self.household_with_parent_earning(5_250)
        self.assertEqual(self.make_calculator(screen).tax_year, 2025)

    def test_a_parent_between_the_2025_and_2026_limits_is_not_a_dependent(self) -> None:
        # 5,250 is at or over the 2025 limit (5,200), so not a qualifying relative for 2025.
        # Judged on the 2026 limit (5,300) they would be a dependent and excluded.
        screen, parent = self.household_with_parent_earning(5_250)
        e = self.calculate(screen)

        self.assertTrue(self.parent_eligible(e, parent))
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 1_154)

    def test_a_parent_under_the_2025_limit_is_a_dependent(self) -> None:
        screen, parent = self.household_with_parent_earning(5_000)
        e = self.calculate(screen)

        self.assertFalse(self.parent_eligible(e, parent))
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)
