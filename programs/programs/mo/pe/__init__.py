from programs.programs.federal.pe.tax import Cdcc, Ctc, Eitc
import programs.programs.mo.pe.member as member
import programs.programs.mo.pe.spm as spm
import programs.programs.mo.pe.tax as tax
from programs.framework.pe_base import PolicyEngineCalulator

mo_member_calculators = {
    "mo_wic": member.MoWic,
    "mo_head_start": member.MoHeadStart,
    "mo_early_head_start": member.MoEarlyHeadStart,
    "mo_ssi": member.MoSsi,
}

mo_spm_calculators = {
    "mo_lifeline": spm.MoLifeline,
    "mo_nslp": spm.MoNslp,
}

mo_tax_unit_calculators = {
    "mo_ctc": Ctc,
    "mo_eitc": Eitc,
    "mo_cdcc_federal": Cdcc,
    "mo_aca_ptc": tax.MoAca,
}

mo_pe_calculators: dict[str, type[PolicyEngineCalulator]] = {
    **mo_member_calculators,
    **mo_spm_calculators,
    **mo_tax_unit_calculators,
}
