from programs.programs.calc import ProgramCalculator, Eligibility
import programs.programs.messages as messages


class EnergyResourceCenter(ProgramCalculator):
    amount = 4000
    income_bands = {1: 2880, 2: 3766, 3: 4652, 4: 5539, 5: 6425, 6: 7311, 7: 7477, 8: 7644}
    dependencies = ["household_size", "income_amount", "income_frequency"]

    def household_eligible(self, e: Eligibility) -> None:
        # income
        gross_income = self.screen.calc_gross_income("monthly", ["all"])
        income_band = EnergyResourceCenter.income_bands[self.screen.household_size]
        e.condition(gross_income <= income_band, messages.income(gross_income, income_band))
