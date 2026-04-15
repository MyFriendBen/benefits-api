from programs.co_county_zips import counties_from_screen
from programs.programs.calc import Eligibility, ProgramCalculator


class EnergyCalculatorInductionLendingProgram(ProgramCalculator):
    """
    Induction Lending Program calculator for Boulder County residents.

    This program provides a free 3-week loan of a portable induction cooktop
    (with cooking utensils) to eligible Boulder County residents through the
    Energy Smart Colorado program.

    Eligibility criteria:
    - Must be a Boulder County resident (verified via ZIP code)
    """
    # Equpiment retails ~$150; value set to reflect that + loan access benefit
    amount = 100 
    county = "Boulder County"
    dependencies = ["energy_calculator", "zipcode"]

    def household_eligible(self, e: Eligibility):
        # must be a Boulder County resident
        counties = counties_from_screen(self.screen)
        e.condition(self.county in counties)
