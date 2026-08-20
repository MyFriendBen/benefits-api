from programs.framework.base import Eligibility, ProgramCalculator
from programs.programs.white_labels.cesn.util import has_renter_expenses
from programs.programs.cross_white_label.liheap.cesn import EnergyCalculatorEnergyAssistance
from programs.programs.white_labels.cesn.eoc.calculator import EnergyCalculatorEnergyOutreach
from programs.programs.cross_white_label.weatherization.cesn import (
    EnergyCalculatorWeatherizationAssistance,
)


class EnergyCalculatorPercentageOfIncomePaymentPlan(ProgramCalculator):
    program_code = "cesn_poipp"
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
    gas_providers = ["co-atmos-energy"]

    def household_eligible(self, e: Eligibility):
        # eligible for another program
        e.condition(self.any_program_eligible(self.presumptive_eligibility))

        # has gas provider
        e.condition(self.screen.energy_calculator.has_gas_provider(self.gas_providers))

        # no renters without expenses
        e.condition(has_renter_expenses(self.screen))
