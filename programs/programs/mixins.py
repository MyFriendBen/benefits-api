from programs.programs.calc import Eligibility
import programs.programs.messages as messages


class FplIncomeCheckMixin:
    """
    Mixin for programs that check household income against Federal Poverty Level percentages.
    """

    def check_fpl_income(self, e: Eligibility, fpl_percent: float) -> None:
        """
        Check household income against FPL percentage.

        Args:
            e: Eligibility object for condition checks
            fpl_percent: FPL percentage to check (e.g., 1.38 for 138% FPL)
        """
        # Calculate income limit
        fpl = self.program.year
        income_limit = int(fpl_percent * fpl.get_limit(self.screen.household_size))

        # Calculate gross income
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))

        # Add eligibility condition
        e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))
