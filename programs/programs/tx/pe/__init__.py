import programs.programs.tx.pe.member as member
import programs.programs.tx.pe.spm as spm
import programs.programs.tx.pe.tax as tax
from programs.programs.policyengine.calculators.base import PolicyEngineCalulator


tx_member_calculators = {
    "tx_wic": member.TxWic,
    "tx_ssi": member.TxSsi,
    "tx_csfp": member.TxCsfp,
    "tx_chip": member.TxChip,
    "tx_medicaid_for_children": member.TxMedicaidForChildren,
    "tx_medicaid_for_pregnant_women": member.TxMedicaidForPregnantWomen,
    "tx_medicaid_for_parents_and_caretakers": member.TxMedicaidForParentsAndCaretakers,
    "tx_harris_rides": member.TxHarrisCountyRides,
    "tx_emergency_medicaid": member.TxEmergencyMedicaid,
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
    "tx_tanf": spm.TxTanf,
}

tx_pe_calculators: dict[str, type[PolicyEngineCalulator]] = {
    **tx_member_calculators,
    **tx_tax_unit_calculators,
    **tx_spm_calculators,
}
