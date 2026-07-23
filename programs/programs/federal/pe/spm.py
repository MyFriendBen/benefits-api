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
    # TANF cash receipt drives SNAP categorical eligibility (income/asset tests bypassed):
    # send the reported tanf amount directly as the tanf value. TANF has no reported/toggle
    # seam, so a positive tanf value is what confers categorical eligibility.
    #
    # SSI categorical eligibility is deliberately NOT wired here. It requires
    # use_reported_ssi, which is global per PE request (flips applicable_ssi for every
    # program in the request — SNAP, IL AABD, KS TANF, TX CEAP), so it's a federal
    # all-state change with cross-program effects (verified IL AABD $0->$10k swing).
    # That work lives in MFB-1312 with all-consumer QA, not in this KS SNAP PR.
    dependency.spm.Tanf,
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
        # phone_cost gates PE's state Lifeline supplements (e.g. KS: the supplement is
        # released only up to phone_cost). Sent for all states that inherit Lifeline so
        # a phone-service supplement is never silently zeroed out; states without such a
        # supplement (TX, WA) are unaffected since their value doesn't depend on it.
        dependency.spm.PhoneCostDependency,
        *dependency.irs_gross_income,
    ]
    pe_outputs = [dependency.spm.Lifeline]
