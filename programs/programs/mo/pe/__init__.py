import programs.programs.mo.pe.member as member
import programs.programs.mo.pe.spm as spm
from programs.programs.policyengine.calculators.base import PolicyEngineCalulator

mo_member_calculators = {
    "mo_wic": member.MoWic,
}

mo_spm_calculators = {
    "mo_nslp": spm.MoNslp,
}

mo_pe_calculators: dict[str, type[PolicyEngineCalulator]] = {
    **mo_member_calculators,
    **mo_spm_calculators,
}
