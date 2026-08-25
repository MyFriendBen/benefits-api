from programs.framework.base import Eligibility, ProgramCalculator
from programs.programs.cross_white_label.liheap.cesn import EnergyCalculatorEnergyAssistance
from programs.programs.white_labels.cesn.util import has_renter_expenses


class EnergyCalculatorEnergyOutreachCrisisIntervention(ProgramCalculator):
    program_code = "cesn_eoccip"
    amount = 1
    dependencies = [*EnergyCalculatorEnergyAssistance.dependencies, "energy_calculator"]

    def household_eligible(self, e: Eligibility):
        # eligible for LEAP
        e.condition(self.program_eligible("cesn_leap"))

        # heating is not working
        needs_heating = self.screen.energy_calculator.needs_hvac
        e.condition(needs_heating)

        # no renters without expenses
        e.condition(has_renter_expenses(self.screen))
