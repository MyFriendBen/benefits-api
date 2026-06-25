from programs.programs.policyengine.calculators.base import PolicyEngineSpmCalulator
import programs.programs.policyengine.calculators.dependencies as dependency

SNAP_BASE_INPUTS = [
    dependency.spm.SnapUnearnedIncomeDependency,
    dependency.spm.SnapEarnedIncomeDependency,
    dependency.spm.SnapAssetsDependency,
    dependency.member.SnapChildSupportDependency,
    dependency.member.PropertyTaxExpenseDependency,
    dependency.member.AgeDependency,
    dependency.member.MedicalExpenseDependency,
    dependency.member.IsDisabledDependency,
    # Reported SSI receipt. PE's `meets_snap_categorical_eligibility` keys off the computed
    # `ssi` variable, so a real SSI recipient whose unearned income is high enough that PE
    # recomputes `ssi = 0` would otherwise be denied categorical eligibility (and the
    # elderly/disabled asset limit). Feeding reported SSI as the `ssi` input — the same
    # pattern other calculators use — lets actual receipt drive categorical eligibility.
    dependency.member.Ssi,
    # Reported TANF cash receipt. PE doesn't yet honor `tanf` for SNAP categorical eligibility
    # in non-BBCE states (it's modeled for IL / via the BBCE non-cash path only), so this has no
    # effect for KS today — but sending it now means the categorical path is correctly armed and
    # will work the moment PE adds `tanf` to its SNAP categorical_eligibility list. Mirrors `Ssi`.
    dependency.spm.Tanf,
    # PE's SNAP elderly/disabled treatment (uncapped excess-shelter deduction and the higher
    # $4,500 asset limit) keys off `is_usda_disabled`, which requires receipt of a qualifying
    # disability program — NOT the generic `is_disabled` flag. SsdiReportedDependency feeds
    # the SSDI benefit amount so a disabled applicant on SSDI gets the disabled treatment
    # (otherwise the shelter deduction is wrongly capped). MeetsSsiDisabilityCriteriaDependency
    # is version-gated and only takes effect once a supporting PE version is pinned.
    dependency.member.SsdiReportedDependency,
    dependency.member.MeetsSsiDisabilityCriteriaDependency,
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
]


class Snap(PolicyEngineSpmCalulator):
    pe_name = "snap"
    pe_inputs = [
        *SNAP_BASE_INPUTS,
        dependency.member.FullTimeCollegeStudentDependency,
        dependency.member.PartTimeCollegeStudentDependency,
        dependency.member.SnapWorkExceptionDependency,
        dependency.member.SnapJobTrainingStudentDependency,
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
