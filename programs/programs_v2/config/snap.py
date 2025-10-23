"""
SNAP program configuration classes.

Config classes define:
- What PolicyEngine inputs are needed
- What PolicyEngine outputs are needed
- Calculation period (from Program.year.period)
- Any program-specific settings
"""

from typing import List, Type
from programs.programs_v2.policyengine.inputs.base import PolicyEngineInput
from programs.programs_v2.policyengine.outputs.base import PolicyEngineOutput
from .base import Config
from programs.programs_v2.policyengine.inputs.spm_unit_inputs import (
    SnapEarnedIncomeInput,
    SnapUnearnedIncomeInput,
    SnapAssetsInput,
    SnapEmergencyAllotmentInput,
    HousingCostInput,
    HasPhoneExpenseInput,
    HasHeatingCoolingExpenseInput,
    HeatingCoolingExpenseInput,
    SnapDependentCareDeductionInput,
    WaterExpenseInput,
    PhoneExpenseInput,
    HoaFeesExpenseInput,
    HomeownersInsuranceExpenseInput,
)
from programs.programs_v2.policyengine.inputs.member_inputs import (
    SnapChildSupportInput,
    PropertyTaxExpenseInput,
    AgeInput,
    MedicalExpenseInput,
    IsDisabledInput,
    SnapIneligibleStudentInput,
)
from programs.programs_v2.policyengine.inputs.household_inputs import TxStateCodeInput
from programs.programs_v2.policyengine.outputs.spm_unit_outputs import SnapOutput


class SnapConfig(Config):
    """Base SNAP configuration."""

    # PolicyEngine inputs needed for SNAP calculation
    pe_inputs: List[Type[PolicyEngineInput]] = [
        # SPM unit level
        SnapEarnedIncomeInput,
        SnapUnearnedIncomeInput,
        SnapAssetsInput,
        SnapEmergencyAllotmentInput,
        HousingCostInput,
        HasPhoneExpenseInput,
        HasHeatingCoolingExpenseInput,
        HeatingCoolingExpenseInput,
        SnapDependentCareDeductionInput,
        WaterExpenseInput,
        PhoneExpenseInput,
        HoaFeesExpenseInput,
        HomeownersInsuranceExpenseInput,
        # Member level
        SnapChildSupportInput,
        PropertyTaxExpenseInput,
        AgeInput,
        MedicalExpenseInput,
        IsDisabledInput,
        SnapIneligibleStudentInput,
    ]

    # PolicyEngine outputs needed
    pe_outputs: List[PolicyEngineOutput] = [
        SnapOutput
    ]

    # SNAP uses January for calculations
    pe_period_month = "01"


class TxSnapConfig(SnapConfig):
    """Texas-specific SNAP configuration."""

    # Add TX state code to inputs
    pe_inputs: List[Type[PolicyEngineInput]] = [
        *SnapConfig.pe_inputs,
        TxStateCodeInput,
    ]

    # TX SNAP uses the same outputs as base SNAP
    # No TX-specific benefit amounts needed (uses PolicyEngine values)
