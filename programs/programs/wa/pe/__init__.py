import programs.programs.wa.pe.member as member
import programs.programs.wa.pe.spm as spm
from programs.programs.policyengine.calculators.base import PolicyEngineCalulator

wa_member_calculators = {
    "wa_ssi": member.WaSsi,
}

wa_spm_calculators = {
    "wa_snap": spm.WaSnap,
}

wa_pe_calculators: dict[str, type[PolicyEngineCalulator]] = {
    **wa_member_calculators,
    **wa_spm_calculators,
}
