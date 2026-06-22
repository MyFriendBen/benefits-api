from integrations.services.income_limits import ami
from programs.programs.calc import Eligibility, ProgramCalculator
from programs.programs.co.energy_calculator.util import has_renter_expenses


class EnergyCalculatorEnergyOutreach(ProgramCalculator):
    ami_percent = "80%"
    amount = 1_000_000  # move to the top of the list
    dependencies = ["energy_calculator", "income_frequency", "income_amount", "household_size", "county"]

    def household_eligible(self, e: Eligibility) -> None:
        if self.program.year is None:
            e.condition(False)
            return
        # income
        income = self.screen.calc_gross_income("yearly", ["all"])
        income_limit = ami.get_screen_ami(self.screen, self.ami_percent, self.program.year.period)
        e.condition(income <= income_limit)

        # past due heating
        e.condition(
            self.screen.energy_calculator.electricity_is_disconnected
            or self.screen.energy_calculator.has_past_due_energy_bills
        )

        # no renters without expenses
        e.condition(has_renter_expenses(self.screen))
