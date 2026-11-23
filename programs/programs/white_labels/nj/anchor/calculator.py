from programs.framework.base import ProgramCalculator, Eligibility
import programs.framework.eligibility_messages as messages
from programs.programs.white_labels.nj.income_tax import EXCLUDED_INCOME_TYPES, filers
from screener.models import HouseholdMember


class NjAnchor(ProgramCalculator):
    """
    ANCHOR (Affordable New Jersey Communities for Homeowners and Renters): a yearly New
    Jersey property tax rebate, here for the 2025 benefit year.

    Two routes, read from housing expenses because the screener doesn't ask about ownership.
    Any rent puts the household on the renter route; property tax or a mortgage with no rent
    puts it on the homeowner route.

    - Homeowner: 2025 NJ gross income up to $250,000. The benefit is the property tax entered,
      capped at $1,500 (income up to $150,000) or $1,000 (above that). A household that entered
      only a mortgage gets the full cap.
    - Renter: income up to $150,000. A flat $450, plus $250 when the head or spouse is 65 or
      older at the end of 2025.

    NJ gross income is approximated by the head's and spouse's current income minus the types
    New Jersey doesn't tax. A domestic partner isn't combined, since NJ treats domestic
    partners as single filers.

    Data gaps (spec §5): 2025 income and October 1 tenure, ownership shares and co-claimants,
    PILOT and fully exempt homes, mobile home park sites, and civil union partners entered as
    domestic partners.
    """

    program_code = "nj_anchor"

    # The amounts and limits below are set for this benefit year by the FY2027 Appropriations Act.
    benefit_year = 2025

    homeowner_income_limit = 250_000
    renter_income_limit = 150_000

    homeowner_cap_income = 150_000
    homeowner_cap_low = 1_500
    homeowner_cap_high = 1_000

    renter_benefit = 450
    senior_supplement = 250
    supplement_age = 65

    excluded_income_types = list(EXCLUDED_INCOME_TYPES)

    dependencies = [
        "age",
        "relationship",
        "income_type",
        "income_amount",
        "income_frequency",
        "expense_type",
        "expense_amount",
        "expense_frequency",
    ]

    def household_eligible(self, e: Eligibility) -> None:
        is_renter = self._is_renter()
        is_homeowner = self._is_homeowner()

        e.condition(is_renter or is_homeowner)
        if not (is_renter or is_homeowner):
            return

        income = self._claimant_income()
        income_limit = self.renter_income_limit if is_renter else self.homeowner_income_limit
        e.condition(income <= income_limit, messages.income(income, income_limit))

    def household_value(self) -> int:
        if self._is_renter():
            if any(self._is_senior(m) for m in self._claimants()):
                return self.renter_benefit + self.senior_supplement
            return self.renter_benefit

        cap = (
            self.homeowner_cap_low if self._claimant_income() <= self.homeowner_cap_income else self.homeowner_cap_high
        )
        property_tax = self.screen.calc_expenses("yearly", ["propertyTax"])
        if property_tax <= 0:
            # Only a mortgage was entered, so the taxes paid through it are unknown.
            return cap

        # Floored at 1 so a few cents of property tax still shows an eligible household.
        return max(int(min(property_tax, cap)), 1)

    def _is_renter(self) -> bool:
        return self.screen.calc_expenses("yearly", ["rent"]) > 0

    def _is_homeowner(self) -> bool:
        return not self._is_renter() and self.screen.calc_expenses("yearly", ["propertyTax", "mortgage"]) > 0

    def _claimants(self) -> list[HouseholdMember]:
        """The head and a member entered as a spouse. A domestic partner files separately."""
        return filers(self.screen)

    def _claimant_income(self) -> float:
        return sum(
            m.calc_gross_income("yearly", ["all"], exclude=self.excluded_income_types) for m in self._claimants()
        )

    def _is_senior(self, member: HouseholdMember) -> bool:
        age = member.age_at_end_of_year(self.benefit_year)
        return age is not None and age >= self.supplement_age
