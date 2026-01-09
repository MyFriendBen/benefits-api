import programs.programs.federal.pe.tax as tax
import programs.programs.federal.pe.spm as spm
import programs.programs.federal.pe.member as member
from programs.programs.policyengine.calculators.base import PolicyEngineCalulator


federal_member_calculators = {
    "wic": member.Wic,
    "pell_grant": member.PellGrant,
    "ssi": member.Ssi,
    "csfp": member.CommoditySupplementalFoodProgram,
    "emergency_medicaid": member.EmergencyMedicaid,
}

federal_spm_unit_calculators = {
    "acp": spm.Acp,
    "lifeline": spm.Lifeline,
    "nslp": spm.SchoolLunch,
    "snap": spm.Snap,
    "tanf": spm.Tanf,
}

federal_tax_unit_calculators = {
    "eitc": tax.Eitc,
    "ctc": tax.Ctc,
}

federal_pe_calculators: dict[str, type[PolicyEngineCalulator]] = {
    **federal_member_calculators,
    **federal_spm_unit_calculators,
    **federal_tax_unit_calculators,
}
