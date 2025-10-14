from integrations.services.income_limits import ami
from programs.programs.calc import Eligibility, ProgramCalculator
import programs.programs.messages as messages


class EnergyCalculatorHomeEfficiencyAssistance(ProgramCalculator):
    amount = 1
    dependencies = ["household_size", "income_amount", "income_frequency", "county", "energy_calculator"]
    presumptive_eligibility = [
        "co_energy_calculator_leap",
    ]
    utility_providers = []
    ami_percent = "60%"

    def household_eligible(self, e: Eligibility):
        # eligible for another program
        has_another_program = False
        for program in self.presumptive_eligibility:
            eligible = self.data[program].eligible
            if eligible:
                has_another_program = True
        e.condition(has_another_program)

        energy_calculator_screen = self.screen.energy_calculator
        # has utility providers
        e.condition(energy_calculator_screen.has_utility_provider(self.utility_providers))

        # must be homeowner
        e.condition((energy_calculator_screen.is_home_owner))

        # income
        income_limit = ami.get_screen_ami(self.screen, self.ami_percent, self.program.year.period)
        income = int(self.screen.calc_gross_income("yearly", ["all"]))
        income_eligible = income <= income_limit
        e.condition(income_eligible, messages.income(income, income_limit))
