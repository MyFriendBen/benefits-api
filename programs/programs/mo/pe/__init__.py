import programs.programs.mo.pe.member as member
from programs.programs.policyengine.calculators.base import PolicyEngineCalulator

mo_member_calculators = {
    "mo_wic": member.MoWic,
    "mo_early_head_start": member.MoEarlyHeadStart,
}

mo_pe_calculators: dict[str, type[PolicyEngineCalulator]] = {
    **mo_member_calculators,
}
