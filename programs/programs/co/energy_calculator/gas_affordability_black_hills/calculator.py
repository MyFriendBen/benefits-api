from programs.programs.calc import Eligibility, ProgramCalculator
from programs.programs.co.energy_calculator.util import has_renter_expenses
from programs.programs.co.energy_calculator.energy_assistance.calculator import EnergyCalculatorEnergyAssistance
from programs.programs.co.energy_calculator.energy_outreach.calculator import EnergyCalculatorEnergyOutreach
from programs.programs.co.energy_calculator.utility_bill_pay.calculator import EnergyCalculatorUtilityBillPay
from programs.programs.co.energy_calculator.weatherization_assistance.calculator import (
    EnergyCalculatorWeatherizationAssistance,
)


class EnergyCalculatorGasAffordabilityBlackHills(ProgramCalculator):
    amount = 1
    dependencies = [
        *EnergyCalculatorEnergyAssistance.dependencies,
        *EnergyCalculatorEnergyOutreach.dependencies,
        *EnergyCalculatorWeatherizationAssistance.dependencies,
        *EnergyCalculatorUtilityBillPay.dependencies,
        "energy_calculator",
    ]
    presumptive_eligibility = [
        "co_energy_calculator_leap",
        "co_energy_calculator_eoc",
        "co_energy_calculator_cowap",
        "co_energy_calculator_ubp",
        "co_energy_calculator_care",
    ]
    gas_providers = ["co-black-hills-energy-gas"]

    def household_eligible(self, e: Eligibility):
        # eligible for another program
        has_another_program = False
        for program in self.presumptive_eligibility:
            eligible = self.data[program].eligible
            if eligible:
                has_another_program = True
        e.condition(has_another_program)

        # has gas provider
        e.condition(self.screen.energy_calculator.has_gas_provider(self.gas_providers))

        # no renters without expenses
        e.condition(has_renter_expenses(self.screen))
