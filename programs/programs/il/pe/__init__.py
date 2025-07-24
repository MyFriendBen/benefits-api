import programs.programs.il.pe.tax as tax
import programs.programs.il.pe.spm as spm
from programs.programs.policyengine.calculators.base import PolicyEngineCalulator


il_member_calculators = {}

il_tax_unit_calculators = {}

il_spm_calculators = {
    "il_snap": spm.IlSnap,
}

il_pe_calculators: dict[str, type[PolicyEngineCalulator]] = {
    **il_member_calculators,
    **il_tax_unit_calculators,
    **il_spm_calculators,
}
