"""SNAP."""

from datetime import date

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

    @property
    def pe_period_month(self) -> str:
        """The month SNAP's monthly outputs are read at: today, within the requested year.

        A screener answers "what would I get if I applied today", and one input to that
        answer changes mid-year. States re-base their broad-based categorical eligibility
        (BBCE) gross income limit onto the current calendar year's poverty guidelines on
        their own schedule -- October federally, but April in WA, February in MA, January
        in ME and March in OR (PolicyEngine's `fpg_year_start_month`). PolicyEngine reads
        that schedule off the month asked about, so a fixed month pins every screen to one
        side of the cutover for the whole year. Asking about January put Colorado on the
        prior year's guidelines permanently: a household of one at $31,434/yr read $0
        against the stale $31,300 limit instead of eligible against the current $31,920
        one (MFB-1740).

        Only households within the gap between two years' limits -- roughly 2% of income
        -- change, but for them SNAP flips between $0 and eligible, and a $0 program is
        dropped from the results page entirely.

        Clamped to the requested year: `pe_period` comes from the program's configured
        FederalPoveryLimit row, which may lag or lead the current calendar year, and
        `YYYY-MM` has to name a month that year actually had. A past year reads December,
        its final state; a future year reads January, its first.
        """
        today = date.today()

        try:
            requested_year = int(self.pe_period)
        except ValueError:
            # `period` is a free-text column, so a non-numeric value is possible. January
            # is the historical default this replaced, and the safe answer for a period
            # whose calendar year we cannot place.
            return "01"

        if requested_year == today.year:
            return f"{today.month:02d}"

        return "12" if requested_year < today.year else "01"

    def household_value(self):
        return int(self.sim.value(self.pe_category, self.pe_sub_category, self.pe_name, self.pe_month_period)) * 12
