import programs.programs.il.pe.tax as tax
import programs.programs.il.pe.spm as spm
import programs.programs.il.pe.member as member
from programs.programs.policyengine.calculators.base import PolicyEngineCalulator


tx_member_calculators = {}

il_tax_unit_calculators = {}

il_spm_calculators = {
    "tx_snap": spm.TxSnap,
}

il_pe_calculators: dict[str, type[PolicyEngineCalulator]] = {
    **tx_member_calculators,
    **tx_tax_unit_calculators,
    **tx_spm_calculators,
}
