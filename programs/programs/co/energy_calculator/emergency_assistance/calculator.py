from programs.co_county_zips import counties_from_screen
from programs.framework.base import Eligibility, ProgramCalculator


class EnergyCalculatorEmergencyAssistance(ProgramCalculator):
    program_code = "cesn_ea"
    amount = 1
    county = "Denver County"
    fpl_percent = 4
    dependencies = ["energy_calculator", "household_size", "income_amount", "income_frequency", "zipcode"]

    def household_eligible(self, e: Eligibility):
        # location
        counties = counties_from_screen(self.screen)
        e.condition(self.county in counties)

        # income
        limit = self.program.year.as_dict()[self.screen.household_size] * self.fpl_percent
        income = self.screen.calc_gross_income("yearly", ["all"])
        e.condition(income <= limit)
