from programs.framework.base import Eligibility, ProgramCalculator
from programs.programs.cross_white_label.liheap.cesn import EnergyCalculatorEnergyAssistance
from programs.programs.cross_white_label.weatherization.cesn import (
    EnergyCalculatorWeatherizationAssistance,
)
from programs.programs.white_labels.cesn.eoc.calculator import EnergyCalculatorEnergyOutreach
from programs.programs.white_labels.cesn.util import has_renter_expenses


class CesnUtilityAssistance(ProgramCalculator, abstract=True):
    """
    A utility's own bill-assistance program: open to a household that qualifies for one of
    the state routes (LEAP, EOC, CO WAP), is a customer of the utility, and, if renting,
    pays its own energy bills.

    A subclass names the utility through ``has_utility_provider``; the gas and electric
    bases below do that from a provider list.
    """

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
    #
    # Each subclass declares its own `gates_on_any` (the state routes, plus any of its
    # own) in its own file: the gate graph check in `screener/tests/test_calc_order.py`
    # attributes an inherited gate to the subclass that declares the codes.
    gates_on_any: tuple[str, ...]

    def has_utility_provider(self) -> bool:
        raise NotImplementedError

    def household_eligible(self, e: Eligibility) -> None:
        # eligible for another program
        e.condition(self.any_program_eligible(self.gates_on_any))

        # customer of this utility
        e.condition(self.has_utility_provider())

        # no renters without expenses
        e.condition(has_renter_expenses(self.screen))


class CesnGasUtilityAssistance(CesnUtilityAssistance, abstract=True):
    gas_providers: list[str]

    def has_utility_provider(self) -> bool:
        return self.screen.energy_calculator.has_gas_provider(self.gas_providers)


class CesnElectricUtilityAssistance(CesnUtilityAssistance, abstract=True):
    electricity_providers: list[str]

    def has_utility_provider(self) -> bool:
        return self.screen.energy_calculator.has_electricity_provider(self.electricity_providers)
