"""SNAP."""

from programs.framework.pe_base import PolicyEngineSpmCalulator
import programs.framework.pe_dependencies as dependency

SNAP_BASE_INPUTS = [
    dependency.spm.SnapUnearnedIncomeDependency,
    dependency.spm.SnapEarnedIncomeDependency,
    dependency.spm.SnapAssetsDependency,
    dependency.member.SnapChildSupportDependency,
    dependency.member.PropertyTaxExpenseDependency,
    dependency.member.AgeDependency,
    dependency.member.MedicalExpenseDependency,
    dependency.member.IsDisabledDependency,
    # SNAP's categorical eligibility bypasses the income and asset tests for SSI/TANF
    # recipients, which PolicyEngine keys off actual receipt rather than simulated benefits.
    *dependency.receipt_contract,
    # Disabled treatment (uncapped shelter deduction, $4,500 asset limit) requires disability-
    # program receipt via is_usda_disabled, not the generic is_disabled flag: SsdiReportedDependency
    # feeds the SSDI amount, MeetsSsiDisabilityCriteriaDependency the SSI-disability input PE needs
    # (both version-gated; see the dependency classes).
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

# Kept out of SNAP_BASE_INPUTS so each variant states which hours class it sends. MA has
# to swap in MaTotalHoursWorkedDependency rather than add it -- see MaSnap.
SNAP_HOURS_INPUT = dependency.member.TotalHoursWorkedDependency


class Snap(PolicyEngineSpmCalulator):
    program_code = "snap"
    # PolicyEngine gates `snap` on the take-up flag, so it reads 0 for any household reporting
    # no SNAP — exactly the households this program should be recommended to. The ungated
    # output is what they'd receive if they applied, which is the number worth showing them.
    pe_name = "snap_if_takes_up"
    pe_inputs = [
        *SNAP_BASE_INPUTS,
        dependency.member.FullTimeCollegeStudentDependency,
        dependency.member.PartTimeCollegeStudentDependency,
        dependency.member.SnapWorkExceptionDependency,
        dependency.member.SnapJobTrainingStudentDependency,
        # meets_snap_work_exception covers only PolicyEngine's student rules, so hours are
        # the sole lever on the general work and ABAWD tests. Both are ANDed into
        # is_snap_eligible for the whole SPM unit, and PolicyEngine stopped defaulting this
        # field to 40 hours in 1.815.1 -- unsent, every adult reads as working zero hours
        # and one of them zeroes out the household's SNAP (MFB-1637).
        SNAP_HOURS_INPUT,
    ]
    pe_outputs = [dependency.spm.SnapIfTakesUp]
    # PolicyEngine defines snap monthly, so it is read monthly and annualized.
    pe_monthly_outputs = [dependency.spm.SnapIfTakesUp]
    pe_period_month = "01"

    def household_value(self):
        return int(self.sim.value(self.pe_category, self.pe_sub_category, self.pe_name, self.pe_month_period)) * 12
