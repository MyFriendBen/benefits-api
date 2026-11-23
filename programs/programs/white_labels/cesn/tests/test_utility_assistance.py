from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from programs.framework.base import Eligibility
from programs.framework.registry import is_abstract
from programs.programs.white_labels.cesn.bheap.calculator import EnergyCalculatorElectricityAffordabilityBlackHills
from programs.programs.white_labels.cesn.bhgap.calculator import EnergyCalculatorGasAffordabilityBlackHills
from programs.programs.white_labels.cesn.cngba.calculator import EnergyCalculatorNaturalGasBillAssistance
from programs.programs.white_labels.cesn.poipp.calculator import EnergyCalculatorPercentageOfIncomePaymentPlan
from programs.programs.white_labels.cesn.utility_assistance import (
    CesnElectricUtilityAssistance,
    CesnGasUtilityAssistance,
    CesnUtilityAssistance,
)
from programs.programs.white_labels.cesn.xceleap.calculator import EnergyCalculatorElectricityAffordabilityXcel
from programs.programs.white_labels.cesn.xcelgap.calculator import EnergyCalculatorGasAffordabilityXcel

STATE_ROUTES = ("cesn_leap", "cesn_eoc", "cesn_cowap")

GAS = {
    EnergyCalculatorGasAffordabilityXcel: ("cesn_xcelgap", ["co-xcel-energy-gas"], STATE_ROUTES),
    EnergyCalculatorPercentageOfIncomePaymentPlan: ("cesn_poipp", ["co-atmos-energy"], STATE_ROUTES),
    EnergyCalculatorNaturalGasBillAssistance: ("cesn_cngba", ["co-colorado-natural-gas"], STATE_ROUTES),
    EnergyCalculatorGasAffordabilityBlackHills: (
        "cesn_bhgap",
        ["co-black-hills-energy-gas"],
        (*STATE_ROUTES, "cesn_care"),
    ),
}
ELECTRIC = {
    EnergyCalculatorElectricityAffordabilityXcel: ("cesn_xceleap", ["co-xcel-energy"], STATE_ROUTES),
    EnergyCalculatorElectricityAffordabilityBlackHills: (
        "cesn_bheap",
        ["co-black-hills-energy"],
        (*STATE_ROUTES, "cesn_care"),
    ),
}


def make_calculator(cls: type, *, route: bool = True, provider: bool = True, renter_ok: bool = True):
    screen = Mock()
    screen.energy_calculator.has_gas_provider.return_value = provider
    screen.energy_calculator.has_electricity_provider.return_value = provider
    calculator = cls(screen, Mock(), {}, Mock())
    calculator.any_program_eligible = Mock(return_value=route)
    patcher = patch(
        "programs.programs.white_labels.cesn.utility_assistance.has_renter_expenses", return_value=renter_ok
    )
    return calculator, patcher


def eligible(calculator) -> bool:
    e = Eligibility()
    calculator.household_eligible(e)
    return e.eligible


class TestBases(SimpleTestCase):
    def test_bases_are_abstract(self):
        for base in (CesnUtilityAssistance, CesnGasUtilityAssistance, CesnElectricUtilityAssistance):
            self.assertTrue(is_abstract(base), base)

    def test_programs_are_registered_not_abstract(self):
        for cls in (*GAS, *ELECTRIC):
            self.assertFalse(is_abstract(cls), cls)


class TestEachProgram(SimpleTestCase):
    def test_gas_programs(self):
        for cls, (code, providers, gates) in GAS.items():
            with self.subTest(code):
                self.assertTrue(issubclass(cls, CesnGasUtilityAssistance))
                self.assertEqual(cls.program_code, code)
                self.assertEqual(cls.gas_providers, providers)
                self.assertEqual(tuple(cls.gates_on_any), gates)
                self.assertEqual(cls.amount, 1)

    def test_electric_programs(self):
        for cls, (code, providers, gates) in ELECTRIC.items():
            with self.subTest(code):
                self.assertTrue(issubclass(cls, CesnElectricUtilityAssistance))
                self.assertEqual(cls.program_code, code)
                self.assertEqual(cls.electricity_providers, providers)
                self.assertEqual(tuple(cls.gates_on_any), gates)

    def test_dependencies_cover_every_route_and_the_energy_calculator(self):
        for cls in (*GAS, *ELECTRIC):
            self.assertIn("energy_calculator", cls.dependencies)
            self.assertEqual(cls.dependencies, CesnUtilityAssistance.dependencies)


class TestHouseholdEligible(SimpleTestCase):
    def test_eligible_when_all_three_conditions_hold(self):
        for cls in (*GAS, *ELECTRIC):
            calculator, patcher = make_calculator(cls)
            with patcher:
                self.assertTrue(eligible(calculator), cls)

    def test_each_condition_is_required(self):
        for cls in (*GAS, *ELECTRIC):
            for failing in ("route", "provider", "renter_ok"):
                with self.subTest(cls=cls.__name__, failing=failing):
                    calculator, patcher = make_calculator(cls, **{failing: False})
                    with patcher:
                        self.assertFalse(eligible(calculator))

    def test_gas_programs_check_their_gas_providers(self):
        calculator, patcher = make_calculator(EnergyCalculatorGasAffordabilityXcel)
        with patcher:
            eligible(calculator)
        calculator.screen.energy_calculator.has_gas_provider.assert_called_once_with(["co-xcel-energy-gas"])
        calculator.screen.energy_calculator.has_electricity_provider.assert_not_called()

    def test_electric_programs_check_their_electricity_providers(self):
        calculator, patcher = make_calculator(EnergyCalculatorElectricityAffordabilityBlackHills)
        with patcher:
            eligible(calculator)
        calculator.screen.energy_calculator.has_electricity_provider.assert_called_once_with(["co-black-hills-energy"])
        calculator.screen.energy_calculator.has_gas_provider.assert_not_called()

    def test_reads_the_programs_own_gates(self):
        calculator, patcher = make_calculator(EnergyCalculatorGasAffordabilityBlackHills)
        with patcher:
            eligible(calculator)
        calculator.any_program_eligible.assert_called_once_with((*STATE_ROUTES, "cesn_care"))
