import programs.programs.ks.pe.spm as spm
import programs.programs.ks.pe.tax as tax
import programs.programs.ks.pe.member as member
from programs.programs.federal.pe.tax import Ctc
from programs.programs.policyengine.calculators.base import PolicyEngineCalulator

ks_member_calculators = {
    "ks_medicaid": member.KsKanCare,
    "ks_chip": member.KsChip,
    "ks_ssi": member.KsSsi,
    "ks_head_start": member.KsHeadStart,
}

ks_tax_unit_calculators = {
    "ks_eitc": tax.Kseitc,
    "ks_cdcc": tax.KsCdcc,
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
