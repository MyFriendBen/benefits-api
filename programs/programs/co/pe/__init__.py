from programs.programs.co.pe import spm
import programs.programs.co.pe.tax as tax
import programs.programs.co.pe.member as member
import programs.programs.co.pe.spm as spm
from programs.programs.policyengine.calculators.base import PolicyEngineCalulator

co_member_calculators = {
    "co_medicaid": member.CoMedicaid,
    "andcs": member.AidToTheNeedyAndDisabled,
    "oap": member.OldAgePension,
    "chp": member.Chp,
    "fatc": member.FamilyAffordabilityTaxCredit,
    "co_wic": member.CoWic,
    "ede": member.EveryDayEats,
}

co_tax_unit_calculators = {
    "coeitc": tax.Coeitc,
    "coctc": tax.Coctc,
    "co_tax_credit_care_worker": tax.CoCareWorkerCredit,
}

co_spm_calculators = {
    "co_snap": spm.CoSnap,
    "co_tanf": spm.CoTanf,
}

co_pe_calculators: dict[str, type[PolicyEngineCalulator]] = {
    **co_member_calculators,
    **co_tax_unit_calculators,
    **co_spm_calculators,
}
