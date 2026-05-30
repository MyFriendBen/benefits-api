"""
Regression tests for MFB-1006: calculators must not KeyError when an upstream
program referenced via self.data is missing (e.g. because it was deactivated
in admin and screener/views.py skipped it before populating program_eligibility).

These tests construct each affected calculator with an empty data dict and
exercise the methods that perform self.data[...] lookups. The assertion is
narrow: no KeyError. Other AttributeErrors / numeric errors from unrelated
mocked-out logic are caught and ignored, because the regression we're guarding
against is specifically the dict KeyError.
"""

from unittest.mock import MagicMock

import pytest

from programs.programs.calc import Eligibility, MemberEligibility
from programs.programs.co.connect_for_health.calculator import ConnectForHealth
from programs.programs.co.energy_calculator.electric_affordability_black_hills.calculator import (
    EnergyCalculatorElectricityAffordabilityBlackHills,
)
from programs.programs.co.energy_calculator.electric_affordability_xcel.calculator import (
    EnergyCalculatorElectricityAffordabilityXcel,
)
from programs.programs.co.energy_calculator.energy_ebt.calculator import EnergyCalculatorEnergyEbt
from programs.programs.co.energy_calculator.energy_outreach_crisis_intervention.calculator import (
    EnergyCalculatorEnergyOutreachCrisisIntervention,
)
from programs.programs.co.energy_calculator.gas_affordability_black_hills.calculator import (
    EnergyCalculatorGasAffordabilityBlackHills,
)
from programs.programs.co.energy_calculator.gas_affordability_xcel.calculator import (
    EnergyCalculatorGasAffordabilityXcel,
)
from programs.programs.co.energy_calculator.natural_gas_bill_assistance.calculator import (
    EnergyCalculatorNaturalGasBillAssistance,
)
from programs.programs.co.energy_calculator.percentage_of_income_payment_plan.calculator import (
    EnergyCalculatorPercentageOfIncomePaymentPlan,
)
from programs.programs.co.energy_calculator.vehicle_exchange.calculator import EnergyCalculatorVehicleExchange
from programs.programs.co.low_wage_covid_relief.calculator import LowWageCovidRelief
from programs.programs.co.my_spark.calculator import MySpark

HOUSEHOLD_CALCULATORS_WITH_DATA_LOOKUPS = [
    EnergyCalculatorElectricityAffordabilityXcel,
    EnergyCalculatorElectricityAffordabilityBlackHills,
    EnergyCalculatorGasAffordabilityXcel,
    EnergyCalculatorGasAffordabilityBlackHills,
    EnergyCalculatorNaturalGasBillAssistance,
    EnergyCalculatorPercentageOfIncomePaymentPlan,
    EnergyCalculatorVehicleExchange,
    EnergyCalculatorEnergyEbt,
    EnergyCalculatorEnergyOutreachCrisisIntervention,
    LowWageCovidRelief,
    MySpark,
]


def _build_calculator(calculator_cls, data=None):
    """Construct a calculator with mocked screen/program/missing_deps and the given data dict."""
    screen = MagicMock()
    # has_benefit is called in several calculators; default to False so we exercise
    # the self.data fallback path that this PR guards.
    screen.has_benefit.return_value = False
    screen.has_leap = False
    # calc_gross_income must return a number for arithmetic comparisons in some calculators.
    screen.calc_gross_income.return_value = 0
    screen.household_size = 1
    screen.household_members.all.return_value = []
    screen.household_member.all.return_value = []  # low_wage_covid_relief uses singular by mistake

    program = MagicMock()
    program.year.as_dict.return_value = {1: 1_000, 2: 2_000, 3: 3_000, 4: 4_000}
    program.year.period = 2024

    missing_deps = MagicMock()
    missing_deps.has.return_value = False

    return calculator_cls(screen, program, data if data is not None else {}, missing_deps)


# Program-abbreviation keys (strings) that calculators look up in self.data.
# Anything else (e.g. KeyError: 2024 from an AMI/income-limit table) is unrelated
# to the MFB-1006 regression and is ignored.
_PROGRAM_KEY_TYPES = (str,)


def _is_program_data_keyerror(exc: KeyError) -> bool:
    """Return True if this KeyError likely came from a self.data[<program_abbr>] lookup."""
    if not exc.args:
        return False
    return isinstance(exc.args[0], _PROGRAM_KEY_TYPES)


@pytest.mark.parametrize("calculator_cls", HOUSEHOLD_CALCULATORS_WITH_DATA_LOOKUPS)
def test_household_eligible_does_not_keyerror_on_empty_data(calculator_cls):
    """
    Regression for MFB-1006: when an upstream program is deactivated, its key is
    absent from self.data. household_eligible must handle that without raising a
    KeyError on a program-abbreviation key.
    """
    calc = _build_calculator(calculator_cls, data={})
    eligibility = Eligibility()
    try:
        calc.household_eligible(eligibility)
    except KeyError as e:
        if _is_program_data_keyerror(e):
            pytest.fail(
                f"{calculator_cls.__name__}.household_eligible raised KeyError on empty data "
                f"for program key {e.args[0]!r}"
            )
        # Numeric or other KeyErrors come from unrelated mocked lookups (AMI tables,
        # FPL dicts, etc.) and are not what this test guards against.
    except Exception:
        # Other failures (numeric coercion against MagicMock, missing screen attributes,
        # etc.) are not what this test guards against. The PR fixed only the KeyError.
        pass


def test_connect_for_health_member_eligible_does_not_keyerror_on_empty_data():
    """
    ConnectForHealth.member_eligible iterates over self.data["chp"].eligible_members.
    When chp is deactivated and absent from data, the loop must be skipped (not raise).
    """
    calc = _build_calculator(ConnectForHealth, data={})
    member = MagicMock()
    member.insurance.has_insurance_types.return_value = False
    member_eligibility = MemberEligibility(member)
    try:
        calc.member_eligible(member_eligibility)
    except KeyError as e:
        if _is_program_data_keyerror(e):
            pytest.fail(f"ConnectForHealth.member_eligible raised KeyError on empty data for key {e.args[0]!r}")
    except Exception:
        pass
