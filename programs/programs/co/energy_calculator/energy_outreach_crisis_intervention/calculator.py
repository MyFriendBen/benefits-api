from programs.programs.calc import Eligibility, ProgramCalculator
from programs.programs.co.energy_calculator.energy_assistance.calculator import EnergyCalculatorEnergyAssistance
from programs.programs.co.energy_calculator.util import has_renter_expenses


class EnergyCalculatorEnergyOutreachCrisisIntervention(ProgramCalculator):
    amount = 1
    dependencies = [*EnergyCalculatorEnergyAssistance.dependencies, "energy_calculator"]

    def household_eligible(self, e: Eligibility):
        # eligible for LEAP
        leap_eligible = self.data["cesn_leap"].eligible
        e.condition(leap_eligible)

        # heating is not working
        needs_heating = self.screen.energy_calculator.needs_hvac
        e.condition(needs_heating)

        # no renters without expenses
        e.condition(has_renter_expenses(self.screen))
