from programs.programs.co.energy_assistance.calculator import EnergyAssistance


class EnergyCalculatorEnergyAssistance(EnergyAssistance):
    def _has_expense(self):
        return True
