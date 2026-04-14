import programs.programs.wa.pe.member as member
from programs.programs.policyengine.calculators.base import PolicyEngineCalulator

wa_member_calculators = {
    "wa_wic": member.WaWic,
}

wa_pe_calculators: dict[str, type[PolicyEngineCalulator]] = {
    **wa_member_calculators,
}
