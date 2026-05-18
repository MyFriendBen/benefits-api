import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.federal.pe.spm import Lifeline, Snap, Tanf


class WaLifeline(Lifeline):
    pe_inputs = [
        *Lifeline.pe_inputs,
        dependency.household.WaStateCodeDependency,
    ]


class WaSnap(Snap):
    pe_inputs = [
        *Snap.pe_inputs,
        dependency.household.WaStateCodeDependency,
    ]


class WaTanf(Tanf):
    """
    Washington TANF / SFA cash assistance calculator using PolicyEngine.

    PolicyEngine's `wa_tanf` variable handles the full eligibility check
    (qualifying dependent child or pregnancy, gross and countable income limits,
    WA residency, resource limit) and calculates the monthly benefit as
    `payment_standard − countable_earned_income − gross_unearned_income`.

    Earned-income disregards (WAC 388-450-0170: $500 flat + 50% of remainder,
    effective 2024-08-01) are applied by PolicyEngine automatically when
    `employment_income_before_lsr` and `self_employment_income_before_lsr` are
    provided as inputs.  Gross income is also checked against the separate WAC
    388-478-0035 income limits table.

    Immigration eligibility is handled at the screener level via
    `legal_status_required`; `wa_show_all_cash_assistance_programs` is set to
    True to bypass PE's per-member immigration check and avoid double-filtering.

    See programs/programs/wa/tanf/spec.md for full eligibility criteria and
    the known gross-income-approximation limitation.
    """

    pe_name = "wa_tanf"
    pe_inputs = [
        *Tanf.pe_inputs,
        dependency.household.WaStateCodeDependency,
        dependency.member.PregnancyDependency,
        dependency.member.EmploymentIncomeBeforeLsrDependency,
        dependency.member.SelfEmploymentIncomeBeforeLsrDependency,
        dependency.member.SocialSecurityIncomeDependency,
        dependency.member.UnemploymentIncomeDependency,
        dependency.spm.CashAssetsDependency,
        dependency.spm.WaShowAllCashAssistanceProgramsDependency,
    ]
    pe_outputs = [dependency.spm.WaTanf]
