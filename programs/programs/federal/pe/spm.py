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
    # SNAP's categorical eligibility bypasses the income and asset tests for households
    # receiving SSI or TANF, and PolicyEngine now keys that off actual receipt: the
    # reported amount, or receives_ssi / receives_tanf where the household reports receipt
    # we have no amount for. The take-up flags in the same bundle stop a household PE
    # merely *models* as SSI/TANF-eligible from picking up categorical eligibility, and
    # stop that phantom benefit counting as income in SNAP's own income test.
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


class Snap(PolicyEngineSpmCalulator):
    # The value is snap_if_takes_up, not snap: takes_up_snap_if_eligible is False for every
    # household that doesn't already report receiving SNAP, which zeroes `snap` for exactly
    # the households this program should be recommended to.
    pe_name = "snap_if_takes_up"
    pe_inputs = [
        *SNAP_BASE_INPUTS,
        dependency.member.FullTimeCollegeStudentDependency,
        dependency.member.PartTimeCollegeStudentDependency,
        dependency.member.SnapWorkExceptionDependency,
        dependency.member.SnapJobTrainingStudentDependency,
    ]
    pe_outputs = [dependency.spm.SnapIfTakesUp]
    pe_period_month = "01"

    @property
    def pe_output_period(self):
        return self.pe_period + "-" + self.pe_period_month

    def household_value(self):
        return int(self.sim.value(self.pe_category, self.pe_sub_category, self.pe_name, self.pe_output_period)) * 12


class SchoolLunch(PolicyEngineSpmCalulator):
    """
    National School Lunch Program (NSLP) — free/reduced-price school meals.

    The value is PolicyEngine's ``school_meal_net_subsidy``: the annual value of
    free/reduced meals above the full-price baseline, computed from USDA per-meal
    rates × school days × the household's K-12 children (ages 5–17, imputed by PE
    from ``age``). PAID-tier households net to $0, so eligibility is value > 0.
    ``AgeDependency`` is sent so PE can derive ``is_in_k12_school``.
    """

    pe_name = "school_meal_net_subsidy"
    pe_inputs = [
        dependency.spm.SchoolMealCountableIncomeDependency,
        dependency.member.AgeDependency,
    ]
    pe_outputs = [dependency.spm.SchoolMealNetSubsidy, dependency.spm.SchoolMealTier]


class Tanf(PolicyEngineSpmCalulator):
    # tanf_if_takes_up rather than tanf, for the same reason as Snap above: the
    # receipt-gated field is 0 for every household that isn't already on TANF.
    pe_name = "tanf_if_takes_up"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.FullTimeCollegeStudentDependency,
        *dependency.receipt_contract,
    ]
    pe_outputs = [dependency.spm.TanfIfTakesUp]


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
        # phone_cost gates PE's state Lifeline supplements (e.g. KS: the supplement is
        # released only up to phone_cost). Sent for all states that inherit Lifeline so
        # a phone-service supplement is never silently zeroed out; states without such a
        # supplement (TX, WA) are unaffected since their value doesn't depend on it.
        dependency.spm.PhoneCostDependency,
        *dependency.irs_gross_income,
        # Lifeline is categorically eligible off SNAP / TANF / SSI receipt, so it needs the
        # receipt contract to distinguish a household on those programs from one PE merely
        # models as eligible for them.
        *dependency.receipt_contract,
    ]
    pe_outputs = [dependency.spm.Lifeline]
