from programs.framework.base import Eligibility, ProgramCalculator
from programs.programs.white_labels.cesn.util import has_renter_expenses
from programs.programs.cross_white_label.liheap.cesn import EnergyCalculatorEnergyAssistance
from programs.programs.white_labels.cesn.eoc.calculator import EnergyCalculatorEnergyOutreach
from programs.programs.cross_white_label.weatherization.cesn import (
    EnergyCalculatorWeatherizationAssistance,
)


class EnergyCalculatorNaturalGasBillAssistance(ProgramCalculator):
    program_code = "cesn_cngba"
    amount = 1
    dependencies = [
        *EnergyCalculatorEnergyAssistance.dependencies,
        *EnergyCalculatorEnergyOutreach.dependencies,
        *EnergyCalculatorWeatherizationAssistance.dependencies,
        "energy_calculator",
    ]
    # Tolerant gate: `any_program_eligible` reads an upstream that was not calculated as
    # "no", so an absent route costs this household that route, not the program. Every
    # route is a custom calculator and force-calculated, so they survive a row being
    # deactivated. The `dependencies` splat above is kept deliberately — a tolerant gate
    # contributes nothing to `can_calc`, and without it this program would report a
    # definite "not eligible" on a screen too incomplete to evaluate any route.
    gates_on_any = (
        "cesn_leap",
        "cesn_eoc",
        "cesn_cowap",
    )
    gas_providers = ["co-colorado-natural-gas"]

    def household_eligible(self, e: Eligibility):
        # eligible for another program
        e.condition(self.any_program_eligible(self.gates_on_any))

        # has gas provider
        e.condition(self.screen.energy_calculator.has_gas_provider(self.gas_providers))

        # no renters without expenses
        e.condition(has_renter_expenses(self.screen))
