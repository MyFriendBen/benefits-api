from programs.programs.co.energy_assistance.calculator import EnergyAssistance
from programs.programs.calc import Eligibility, ProgramCalculator


class EnergyCalculatorEnergyAssistance(EnergyAssistance):
    amount = 1000

    def household_eligible(self, e: Eligibility):

        # does not already have LEAP
        e.condition(not self.screen.has_benefit("leap"))

        # user has any expenses
        e.condition(self._has_expense())

    def _has_expense(self):
        """
        Check if household has any expenses.

        Returns True by default for CESN (energy calculator) since we don't
        collect expense information in this flow, unlike the standard Colorado
        screener which validates rent/mortgage expenses.
        """
        return True
