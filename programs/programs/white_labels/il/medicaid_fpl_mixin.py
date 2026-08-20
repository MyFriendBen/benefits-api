"""Shared FPL income check for Illinois Medicaid-adjacent programs.

All Kids, Moms and Babies, Family Care and ACA Adults apply the same percent-of-FPL
test against the same household income, so the check lives once here rather than in
four calculators."""

from programs.framework.base import Eligibility, MemberEligibility
import programs.framework.eligibility_messages as messages


class IlMedicaidFplIncomeCheckMixin:
    """
    Mixin for Illinois Medicaid programs that check household income against Federal Poverty Level percentages.
    Counts pregnant household members as 2 people when calculating household size.
    """

    def check_fpl_income(self, e: Eligibility, fpl_percent: float) -> None:
        """
        Check household income against FPL percentage with pregnancy-adjusted household size.

        Args:
            e: Eligibility object for condition checks
            fpl_percent: FPL percentage to check (e.g., 1.38 for 138% FPL)
        """
        # Calculate pregnancy-adjusted household size
        pregnant_count = self.screen.household_members.filter(pregnant=True).count()
        adjusted_household_size = self.screen.household_size + pregnant_count

        # Calculate income limit using adjusted household size
        fpl = self.program.year
        income_limit = int(fpl_percent * fpl.get_limit(adjusted_household_size))

        # Calculate gross income
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))

        # Add eligibility condition
        e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))
