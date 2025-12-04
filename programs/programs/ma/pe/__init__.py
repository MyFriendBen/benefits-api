import programs.programs.ma.pe.tax as tax
import programs.programs.ma.pe.member as member
import programs.programs.ma.pe.spm as spm
from programs.programs.policyengine.calculators.base import PolicyEngineCalulator


ma_member_calculators = {
    "ma_wic": member.MaWic,
    "ma_ccdf": member.MaCcdf,
    "ma_mass_health": member.MaMassHealth,
    "ma_mass_health_limited": member.MaMassHealthLimited,
    "ma_mbta": member.MaMbta,
    "ma_ssp": member.MaStateSupplementProgram,
    "ma_head_start": member.MaHeadStart,
    "ma_early_head_start": member.MaEarlyHeadStart,
}

ma_tax_unit_calculators = {
    "ma_maeitc": tax.Maeitc,
    "ma_cfc": tax.MaChildFamilyCredit,
    "ma_aca": tax.MaAca,
}

ma_spm_calculators = {
    "ma_snap": spm.MaSnap,
    "ma_tafdc": spm.MaTafdc,
    "ma_eaedc": spm.MaEaedc,
    "ma_heap": spm.MaHeap,
}

ma_pe_calculators: dict[str, type[PolicyEngineCalulator]] = {
    **ma_member_calculators,
    **ma_tax_unit_calculators,
    **ma_spm_calculators,
}
