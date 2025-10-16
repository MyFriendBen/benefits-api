from integrations.services.income_limits import ami
from programs.programs.calc import Eligibility, ProgramCalculator
import programs.programs.messages as messages


class EnergyCalculatorHomeEfficiencyAssistance(ProgramCalculator):
    amount = 1 # default to 1 since not calculating value
    dependencies = ["household_size", "income_amount", "income_frequency", "county", "energy_calculator"]
    presumptive_eligibility = [
        "co_energy_calculator_leap",
    ]
    utility_providers = []
    ami_percent = "60%"

    def household_eligible(self, e: Eligibility):
        energy_calculator_screen = self.screen.energy_calculator

        presumed_eligible = any(
            self.data[program].eligible 
            for program in self.presumptive_eligibility 
            if program in self.data
        )

        if presumed_eligible:
            # if presumptive eligbility via LEAP, done
            e.condition(presumed_eligible)
        else:
            # otherwise, must meet all 3 conditions
            e.condition(energy_calculator_screen.has_utility_provider(self.utility_providers, messages.has_utility_provider(self.utility_providers)))

            e.condition(energy_calculator_screen.is_home_owner, messages.is_home_owners())

            income_limit = ami.get_screen_ami(self.screen, self.ami_percent, self.program.year.period)
            income = int(self.screen.calc_gross_income("yearly", ["all"]))
            income_eligible = income <= income_limit
            e.condition(income_eligible, messages.income(income, income_limit))
