import programs.programs.il.pe.tax as tax
import programs.programs.il.pe.spm as spm
import programs.programs.il.pe.member as member
from programs.programs.policyengine.calculators.base import PolicyEngineCalulator


il_member_calculators = {
    "il_medicaid": member.IlMedicaid,
    "il_wic": member.IlWic,
    "il_aca": member.IlAca,
    "il_aabd": member.IlAabd,
}

il_tax_unit_calculators = {
    "il_eitc": tax.Ileitc,
    "il_ctc": tax.Ilctc,
}

il_spm_calculators = {
    "il_snap": spm.IlSnap,
    "il_nslp": spm.IlNslp,
    "il_tanf": spm.IlTanf,
}

il_pe_calculators: dict[str, type[PolicyEngineCalulator]] = {
    **il_member_calculators,
    **il_tax_unit_calculators,
    **il_spm_calculators,
}
