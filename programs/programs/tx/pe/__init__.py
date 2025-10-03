import programs.programs.tx.pe.spm as spm
from programs.programs.policyengine.calculators.base import PolicyEngineCalulator


tx_member_calculators = {}

tx_tax_unit_calculators = {}

tx_spm_calculators = {
    "tx_snap": spm.TxSnap,
}

tx_pe_calculators: dict[str, type[PolicyEngineCalulator]] = {
    **tx_member_calculators,
    **tx_tax_unit_calculators,
    **tx_spm_calculators,
}
