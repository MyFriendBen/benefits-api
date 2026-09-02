"""SNAP."""

import logging
from datetime import date

from programs.framework.pe_base import PolicyEngineSpmCalulator
import programs.framework.pe_dependencies as dependency

logger = logging.getLogger(__name__)

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

        States re-base their broad-based categorical eligibility gross income limit onto
        the current year's poverty guidelines on their own schedule -- October federally,
        April in WA, February in MA, January in ME, March in OR -- and PolicyEngine reads
        that schedule off the month asked about (`fpg_year_start_month`). A fixed month
        would pin every screen to one side of the cutover all year.

        Clamped to the requested year, since `pe_period` may lag or lead the calendar year
        and `YYYY-MM` has to name a month that year had: a past year reads December, a
        future year January.
        """
        today = date.today()

        try:
            requested_year = int(self.pe_period)
        except ValueError:
            # No supported configuration reaches this -- `period` is the numeric year that
            # indexes the FPL figures -- so warn rather than silently serve the prior
            # year's guidelines.
            logger.warning(
                "SNAP program %s has non-numeric FederalPoveryLimit period %r; "
                "falling back to January, which reads the prior year's poverty guidelines.",
                self.program.name_abbreviated,
                self.pe_period,
            )
            return "01"

        if requested_year == today.year:
            return f"{today.month:02d}"

        return "12" if requested_year < today.year else "01"

    def household_value(self):
        return int(self.sim.value(self.pe_category, self.pe_sub_category, self.pe_name, self.pe_month_period)) * 12
