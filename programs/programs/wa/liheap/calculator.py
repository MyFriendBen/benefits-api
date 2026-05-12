from programs.programs.calc import ProgramCalculator, Eligibility
import programs.programs.messages as messages
from typing import ClassVar


class WaLiheap(ProgramCalculator):
    """WA LIHEAP — heating assistance for households at or below 150% FPG.
    Benefit is a percentage of annual heat cost scaled by income-to-FPL ratio,
    clamped to $250–$1,250. No categorical eligibility in WA.
    """

    fpl_percent = 1.5
    min_benefit = 250
    max_benefit = 1_250
    # Linear scale: 90% of heat cost at 0% FPL, 50% at 125% FPL
    benefit_pct_at_zero_fpl = 0.90
    benefit_pct_slope = 0.40
    benefit_pct_fpl_upper = 125
    dependencies: ClassVar[list[str]] = [
        "income_frequency",
        "income_amount",
        "household_size",
    ]

    def household_eligible(self, e: Eligibility):
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))
        income_limit = int(self.fpl_percent * self.program.year.get_limit(self.screen.household_size))
        e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))

    def household_value(self) -> int:
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))
        fpl_100 = self.program.year.get_limit(self.screen.household_size)

        if fpl_100 == 0:
            return self.min_benefit

        income_pct_fpl = (gross_income / fpl_100) * 100
        income_pct_fpl = min(income_pct_fpl, self.benefit_pct_fpl_upper)

        benefit_pct = self.benefit_pct_at_zero_fpl - (income_pct_fpl / self.benefit_pct_fpl_upper) * self.benefit_pct_slope

        annual_heat_cost = self.screen.calc_expenses("yearly", ["heating"])
        benefit = benefit_pct * annual_heat_cost

        return int(max(self.min_benefit, min(self.max_benefit, benefit)))
