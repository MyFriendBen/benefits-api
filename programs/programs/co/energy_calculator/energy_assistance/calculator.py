from programs.programs.co.energy_assistance.calculator import EnergyAssistance


class EnergyCalculatorEnergyAssistance(EnergyAssistance):
    program_code = "cesn_leap"

    def _has_expense(self):
        return True
