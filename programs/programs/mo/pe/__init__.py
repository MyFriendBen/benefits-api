from programs.programs.federal.pe.tax import Ctc
import programs.programs.mo.pe.member as member
import programs.programs.mo.pe.spm as spm
from programs.programs.policyengine.calculators.base import PolicyEngineCalulator

mo_member_calculators = {
    "mo_wic": member.MoWic,
    "mo_head_start": member.MoHeadStart,
    "mo_early_head_start": member.MoEarlyHeadStart,
}

mo_spm_calculators = {
    "mo_nslp": spm.MoNslp,
}

mo_tax_unit_calculators = {
    # Federal Child Tax Credit, used as-is (no MO variance). Mirrors ks_ctc and wa_ctc.
    "mo_ctc": Ctc,
}

mo_pe_calculators: dict[str, type[PolicyEngineCalulator]] = {
    **mo_member_calculators,
    **mo_spm_calculators,
    **mo_tax_unit_calculators,
}
