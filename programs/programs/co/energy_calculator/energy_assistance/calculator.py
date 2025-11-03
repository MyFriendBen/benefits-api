from programs.programs.co.energy_assistance.calculator import EnergyAssistance
from programs.programs.calc import Eligibility, ProgramCalculator


class EnergyCalculatorEnergyAssistance(ProgramCalculator):
    amount = 1000
    dependencies = [
        "income_amount",
        "income_frequency",
        "household_size",
        "has_benefit",
    ]

    def household_eligible(self, e: Eligibility):

        # does not already have LEAP
        e.condition(not self.screen.has_benefit("leap"))

        # user has any expenses
        e.condition(self._has_expense())

    def _has_expense(self):
        """
        Check if household has any expenses
        """
        return True
