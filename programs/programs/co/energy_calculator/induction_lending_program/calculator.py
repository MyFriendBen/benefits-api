from programs.co_county_zips import counties_from_screen
from programs.programs.calc import Eligibility, ProgramCalculator


class EnergyCalculatorInductionLendingProgram(ProgramCalculator):
    amount = 1
    county = "Boulder County"
    dependencies = ["energy_calculator", "zipcode"]

    def household_eligible(self, e: Eligibility):
        # must be a Boulder County resident
        counties = counties_from_screen(self.screen)
        e.condition(self.county in counties)
