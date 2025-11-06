import programs.programs.tx.pe.member as member
import programs.programs.tx.pe.spm as spm
import programs.programs.tx.pe.tax as tax
from programs.programs.policyengine.calculators.base import PolicyEngineCalulator


tx_member_calculators = {
    "tx_wic": member.TxWic,
    "tx_ssi": member.TxSsi,
    "tx_csfp": member.TxCsfp,
}

tx_tax_unit_calculators = {
    "tx_eitc": tax.TxEitc,
    "tx_ctc": tax.TxCtc,
    "tx_aca": tax.TxAca,
}

tx_spm_calculators = {
    "tx_snap": spm.TxSnap,
    "tx_lifeline": spm.TxLifeline,
    "tx_nslp": spm.TxNslp,
}

tx_pe_calculators: dict[str, type[PolicyEngineCalulator]] = {
    **tx_member_calculators,
    **tx_tax_unit_calculators,
    **tx_spm_calculators,
}
