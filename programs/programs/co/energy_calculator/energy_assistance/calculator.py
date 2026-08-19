from programs.programs.cross_white_label.liheap.co import EnergyAssistance


class EnergyCalculatorEnergyAssistance(EnergyAssistance):
    program_code = "cesn_leap"

    def _has_expense(self):
        return True
