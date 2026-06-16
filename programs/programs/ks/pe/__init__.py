import programs.programs.ks.pe.spm as spm
from programs.programs.policyengine.calculators.base import PolicyEngineCalulator

ks_member_calculators = {}

ks_tax_unit_calculators = {}

ks_spm_calculators = {
    "ks_tanf": spm.KsTanf,
}

ks_pe_calculators: dict[str, type[PolicyEngineCalulator]] = {
    **ks_member_calculators,
    **ks_tax_unit_calculators,
    **ks_spm_calculators,
}
