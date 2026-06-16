import programs.programs.ks.pe.member as member
from programs.programs.policyengine.calculators.base import PolicyEngineCalulator

ks_member_calculators = {
    "ks_medicare_savings": member.KsMsp,
}

ks_pe_calculators: dict[str, type[PolicyEngineCalulator]] = {
    **ks_member_calculators,
}
