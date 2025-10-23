"""
SPM Unit level PolicyEngine input classes.

These inputs operate at the SPM (Supplemental Poverty Measure) unit level,
representing the household as a single unit.
"""

from .base import PolicyEngineInput


class SnapEarnedIncomeInput(PolicyEngineInput):
    """SNAP earned income for the SPM unit."""
    field = "snap_earned_income"
    unit = "spm_units"
    sub_unit = "spm_unit"
    dependencies = ("income_type", "income_amount", "income_frequency")

    def value(self):
        return self.screen.calc_gross_income("yearly", ["earned"])


class SnapUnearnedIncomeInput(PolicyEngineInput):
    """SNAP unearned income for the SPM unit."""
    field = "snap_unearned_income"
    unit = "spm_units"
    sub_unit = "spm_unit"
    dependencies = ("income_type", "income_amount", "income_frequency")

    def value(self):
        return self.screen.calc_gross_income("yearly", ["unearned"])


class SnapAssetsInput(PolicyEngineInput):
    """SNAP countable assets for the SPM unit."""
    field = "snap_assets"
    unit = "spm_units"
    sub_unit = "spm_unit"

    def value(self):
        assets = self.screen.household_assets or 0
        return int(assets)


class SnapEmergencyAllotmentInput(PolicyEngineInput):
    """SNAP emergency allotment flag."""
    field = "snap_emergency_allotment"
    unit = "spm_units"
    sub_unit = "spm_unit"

    def value(self):
        # Emergency allotment ended, always False
        return False


class HousingCostInput(PolicyEngineInput):
    """Housing costs (rent, mortgage, subsidized rent)."""
    field = "housing_cost"
    unit = "spm_units"
    sub_unit = "spm_unit"

    def value(self):
        return int(self.screen.calc_expenses("yearly", ["rent", "mortgage", "subsidizedRent"]))


class HasPhoneExpenseInput(PolicyEngineInput):
    """Whether household has phone expenses."""
    field = "has_phone_expense"
    unit = "spm_units"
    sub_unit = "spm_unit"

    def value(self):
        return self.screen.has_expense(["telephone"])


class HasHeatingCoolingExpenseInput(PolicyEngineInput):
    """Whether household has heating or cooling expenses."""
    field = "has_heating_cooling_expense"
    unit = "spm_units"
    sub_unit = "spm_unit"

    def value(self):
        return self.screen.has_expense(["heating", "cooling"])


class HeatingCoolingExpenseInput(PolicyEngineInput):
    """Heating and cooling expenses."""
    field = "heating_cooling_expense"
    unit = "spm_units"
    sub_unit = "spm_unit"

    def value(self):
        return self.screen.calc_expenses("yearly", ["heating", "cooling"])


class SnapDependentCareDeductionInput(PolicyEngineInput):
    """Dependent care (childcare) expenses for SNAP."""
    field = "childcare_expenses"
    unit = "spm_units"
    sub_unit = "spm_unit"

    def value(self):
        return self.screen.calc_expenses("yearly", ["childCare"])


class WaterExpenseInput(PolicyEngineInput):
    """Water utility expenses."""
    field = "water_expense"
    unit = "spm_units"
    sub_unit = "spm_unit"

    def value(self):
        return self.screen.calc_expenses("yearly", ["water"])


class PhoneExpenseInput(PolicyEngineInput):
    """Phone/telephone expenses."""
    field = "phone_expense"
    unit = "spm_units"
    sub_unit = "spm_unit"

    def value(self):
        return self.screen.calc_expenses("yearly", ["telephone"])


class HoaFeesExpenseInput(PolicyEngineInput):
    """HOA fees expenses."""
    field = "hoa_fees"
    unit = "spm_units"
    sub_unit = "spm_unit"

    def value(self):
        return self.screen.calc_expenses("yearly", ["hoaFees"])


class HomeownersInsuranceExpenseInput(PolicyEngineInput):
    """Homeowners insurance expenses."""
    field = "homeowners_insurance"
    unit = "spm_units"
    sub_unit = "spm_unit"

    def value(self):
        return self.screen.calc_expenses("yearly", ["homeownersInsurance"])
