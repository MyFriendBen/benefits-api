import programs.programs.ks.pe.member as member
import programs.programs.ks.pe.spm as spm
import programs.programs.ks.pe.tax as tax
from programs.programs.federal.pe.tax import Ctc, Cdcc
from programs.programs.policyengine.calculators.base import PolicyEngineCalulator

ks_member_calculators = {
    "ks_medicaid": member.KsKanCare,
    "ks_chip": member.KsChip,
    "ks_ssi": member.KsSsi,
    "ks_head_start": member.KsHeadStart,
    "ks_early_head_start": member.KsEarlyHeadStart,
    "ks_medicare_savings": member.KsMsp,
}

ks_tax_unit_calculators = {
    "ks_eitc": tax.Kseitc,
    "ks_cdcc": tax.KsCdcc,
    "ks_cdcc_federal": Cdcc,
    "ks_ctc": Ctc,
}

ks_spm_calculators = {
    "ks_snap": spm.KsSnap,
    "ks_nslp": spm.KsNslp,
}

ks_pe_calculators: dict[str, type[PolicyEngineCalulator]] = {
    **ks_member_calculators,
    **ks_tax_unit_calculators,
    **ks_spm_calculators,
}
