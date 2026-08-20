from programs.framework.base import Eligibility, ProgramCalculator
from programs.programs.cross_white_label.liheap.cesn import EnergyCalculatorEnergyAssistance
from programs.programs.white_labels.cesn.eoc.calculator import EnergyCalculatorEnergyOutreach
from programs.programs.white_labels.cesn.util import has_renter_expenses
from programs.programs.cross_white_label.weatherization.cesn import (
    EnergyCalculatorWeatherizationAssistance,
)


class EnergyCalculatorGasAffordabilityXcel(ProgramCalculator):
    program_code = "cesn_xcelgap"
    amount = 1
    dependencies = [
        *EnergyCalculatorEnergyAssistance.dependencies,
        *EnergyCalculatorEnergyOutreach.dependencies,
        *EnergyCalculatorWeatherizationAssistance.dependencies,
        "energy_calculator",
    ]
    presumptive_eligibility = [
        "cesn_leap",
        "cesn_eoc",
        "cesn_cowap",
    ]
    gas_providers = ["co-xcel-energy-gas"]

    def household_eligible(self, e: Eligibility):
        # eligible for another program
        has_another_program = False
        for program in self.presumptive_eligibility:
            entry = self.data.get(program)
            if entry is not None and entry.eligible:
                has_another_program = True
        e.condition(has_another_program)

        # has gas provider
        e.condition(self.screen.energy_calculator.has_gas_provider(self.gas_providers))

        # no renters without expenses
        e.condition(has_renter_expenses(self.screen))
