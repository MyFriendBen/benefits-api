import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.federal.pe.spm import Lifeline, SchoolLunch


class MoLifeline(Lifeline):
    """
    Missouri Lifeline Phone and Internet Discount calculator.

    Uses PolicyEngine's federal ``lifeline`` calculator as-is. Missouri has no
    state supplement in PolicyEngine: ``lifeline.py`` layers state amounts only for
    CA and OR (via ``gov.states.<state>.fcc.lifeline.in_effect``) and adds explicit
    per-state supplements only for TX (``tx_lifeline_supplement``) and KS
    (``ks_lifeline_supplement``). MO matches none of those branches, so a Missouri
    household receives the federal benefit — $9.25/month, or $34.25/month on
    qualifying rural Tribal land — capped at its combined phone and broadband cost.

    ``MoStateCodeDependency`` is added for the same reason the sibling states add
    theirs: ``pe_input()`` never sends ``state_code`` on its own, and PE's Lifeline
    chain reads ``state_code_str`` in both ``lifeline`` (state supplement branch) and
    ``is_lifeline_income_eligible`` (the TX 150% FPG expansion versus the federal
    135% limit). Sending MO explicitly keeps PE on the federal branch by fact rather
    than by whichever state PE would otherwise default to. Mirrors the KsLifeline /
    TxLifeline / WaLifeline pattern.

    The base ``Lifeline.pe_inputs`` supply broadband and phone cost plus the IRS gross
    income set that feeds ``fcc_fpg_ratio``; MO adds no inputs beyond the state code.
    """

    pe_inputs = [
        *Lifeline.pe_inputs,
        dependency.household.MoStateCodeDependency,
    ]


class MoNslp(SchoolLunch):
    """
    Missouri National School Lunch Program (NSLP) calculator.

    Uses PolicyEngine's federal ``SchoolLunch`` calculator (pe_name
    ``school_meal_net_subsidy``) as-is. NSLP is a federal program with two federal
    income tiers — free at <=130% FPG, reduced-price at <=185% FPG — and no
    Missouri-specific variance, so the federal eligibility and value logic applies
    unchanged. Mirrors the ks_nslp / tx_nslp / il_nslp precedents.

    ``MoStateCodeDependency`` is load-bearing, not boilerplate. PolicyEngine's school
    meal tier branches on the state's universal-free-meals election, and
    ``pe_input()`` never sends ``state_code`` on its own — it is only ever supplied by
    an explicit StateCode dependency in a calculator's ``pe_inputs``. Omit it and PE
    falls back to its own default state, which *does* have universal free meals:
    verified live against PE ``current`` with a household of 2 (one 9-year-old) at
    $90,000/yr — far above the 185% FPG reduced-price limit:

        state_code=MO   -> school_meal_net_subsidy $0.00      school_meal_tier PAID
        state_code omitted -> school_meal_net_subsidy $1130.96 school_meal_tier FREE

    So without this input every Missouri household would be shown eligible for
    free meals regardless of income. ``test_spm.py`` pins it for that reason.
    """

    pe_inputs = [
        *SchoolLunch.pe_inputs,
        dependency.household.MoStateCodeDependency,
    ]
