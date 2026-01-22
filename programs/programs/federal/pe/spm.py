from programs.programs.policyengine.calculators.base import PolicyEngineSpmCalulator
import programs.programs.policyengine.calculators.dependencies as dependency


class Snap(PolicyEngineSpmCalulator):
    pe_name = "snap"
    pe_inputs = [
        dependency.spm.SnapUnearnedIncomeDependency,
        dependency.spm.SnapEarnedIncomeDependency,
        dependency.spm.SnapAssetsDependency,
        dependency.spm.SnapEmergencyAllotmentDependency,
        dependency.spm.HousingCostDependency,
        dependency.spm.HasPhoneExpenseDependency,
        dependency.spm.HasHeatingCoolingExpenseDependency,
        dependency.spm.HeatingCoolingExpenseDependency,
        dependency.spm.ChildCareDependency,
        dependency.spm.WaterExpenseDependency,
        dependency.spm.PhoneExpenseDependency,
        dependency.spm.HoaFeesExpenseDependency,
        dependency.spm.HomeownersInsuranceExpenseDependency,
        dependency.member.SnapChildSupportDependency,
        dependency.member.PropertyTaxExpenseDependency,
        dependency.member.AgeDependency,
        dependency.member.MedicalExpenseDependency,
        dependency.member.IsDisabledDependency,
        dependency.member.SnapIneligibleStudentDependency,
    ]
    pe_outputs = [dependency.spm.Snap]
    pe_period_month = "01"

    @property
    def pe_output_period(self):
        return self.pe_period + "-" + self.pe_period_month

    def household_value(self):
        return int(self.sim.value(self.pe_category, self.pe_sub_category, self.pe_name, self.pe_output_period)) * 12


class SchoolLunch(PolicyEngineSpmCalulator):
    pe_name = "school_meal_daily_subsidy"
    pe_inputs = [dependency.spm.SchoolMealCountableIncomeDependency]
    pe_outputs = [dependency.spm.SchoolMealDailySubsidy, dependency.spm.SchoolMealTier]

    amount = 120

    def household_value(self):
        value = 0
        num_children = self.screen.num_children(3, 18)

        if self.get_variable() > 0 and num_children > 0:
            if self.get_dependency_value(dependency.spm.SchoolMealTier) != "PAID":
                value = SchoolLunch.amount * num_children

        return value


class Tanf(PolicyEngineSpmCalulator):
    pe_name = "tanf"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.FullTimeCollegeStudentDependency,
    ]
    pe_outputs = [dependency.spm.Tanf]


class Acp(PolicyEngineSpmCalulator):
    pe_name = "acp"
    pe_inputs = [
        dependency.spm.BroadbandCostDependency,
        *dependency.irs_gross_income,
    ]
    pe_outputs = [dependency.spm.Acp]


class Lifeline(PolicyEngineSpmCalulator):
    pe_name = "lifeline"
    pe_inputs = [
        dependency.spm.BroadbandCostDependency,
        *dependency.irs_gross_income,
    ]
    pe_outputs = [dependency.spm.Lifeline]
