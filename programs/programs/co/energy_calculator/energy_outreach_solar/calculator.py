from integrations.services.income_limits import ami
from programs.programs.calc import Eligibility, ProgramCalculator
from programs.programs.co.energy_calculator.util import has_renter_expenses


class EnergyCalculatorEnergyOutreachSolar(ProgramCalculator):
    amount = 1
    dependencies = ["household_size", "energy_calculator", "income_amount", "income_frequency"]
    electricity_providers = ["co-black-hills-energy", "co-xcel-energy"]
    ami_percent = "80%"

    def household_eligible(self, e: Eligibility):
        # income
        income = self.screen.calc_gross_income("yearly", ["all"])
        income_limit = ami.get_screen_ami(self.screen, self.ami_percent, self.program.year.period)
        e.condition(income < income_limit)

        # utility providers
        e.condition(self.screen.energy_calculator.has_electricity_provider(self.electricity_providers))

        # no renters without expenses
        e.condition(has_renter_expenses(self.screen))
