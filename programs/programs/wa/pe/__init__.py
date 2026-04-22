import programs.programs.wa.pe.spm as spm
from programs.programs.policyengine.calculators.base import PolicyEngineCalulator

wa_spm_calculators = {
    "wa_nslp": spm.WaSchoolLunch,
}

wa_pe_calculators: dict[str, type[PolicyEngineCalulator]] = {
    **wa_spm_calculators,
}
