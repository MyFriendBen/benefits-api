import programs.programs.tx.pe.member as member
import programs.programs.tx.pe.spm as spm
import programs.programs.tx.pe.tax as tax
from programs.programs.policyengine.calculators.base import PolicyEngineCalulator


tx_member_calculators = {
    "tx_wic": member.TxWic,
}

tx_tax_unit_calculators = {
    "tx_eitc": tax.TxEitc,
}

tx_spm_calculators = {
    "tx_snap": spm.TxSnap,
    "tx_lifeline": spm.TxLifeline,
}

tx_pe_calculators: dict[str, type[PolicyEngineCalulator]] = {
    **tx_member_calculators,
    **tx_tax_unit_calculators,
    **tx_spm_calculators,
}
