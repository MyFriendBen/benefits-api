from programs.programs.federal.pe.tax import Ctc
import programs.programs.wa.pe.member as member
import programs.programs.wa.pe.spm as spm
import programs.programs.wa.pe.tax as tax
from programs.programs.policyengine.calculators.base import PolicyEngineCalulator

wa_member_calculators = {
    "wa_ssi": member.WaSsi,
}

wa_spm_calculators = {
    "wa_lifeline": spm.WaLifeline,
    "wa_snap": spm.WaSnap,
    "wa_tanf": spm.WaTanf,
}

wa_tax_calculators = {
    "wa_ctc": Ctc,
    "wa_eitc": tax.WaEitc,
    "wa_wftc": tax.WaWftc,
}

wa_pe_calculators: dict[str, type[PolicyEngineCalulator]] = {
    **wa_member_calculators,
    **wa_spm_calculators,
    **wa_tax_calculators,
}
