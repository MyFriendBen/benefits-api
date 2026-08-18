from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
from programs.programs.federal.pe.tax import Eitc, Ctc
import programs.framework.pe_dependencies as dependency


class Coeitc(PolicyEngineTaxUnitCalulator):
    program_code = "coeitc"
    pe_name = "co_eitc"
    pe_inputs = [
        *Eitc.pe_inputs,
        dependency.household.CoStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.Coeitc]


class Coctc(PolicyEngineTaxUnitCalulator):
    program_code = "coctc"
    pe_name = "co_ctc"
    pe_inputs = [
        *Ctc.pe_inputs,
        dependency.household.CoStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.Coctc]


class CoCareWorkerCredit(PolicyEngineTaxUnitCalulator):
    program_code = "co_tax_credit_care_worker"
    pe_name = "co_care_worker_credit"
    pe_inputs = [
        dependency.member.CareWorkerEligibleDependency,
        dependency.member.AgeDependency,
        dependency.member.TaxUnitHeadDependency,
        dependency.member.TaxUnitSpouseDependency,
        dependency.household.CoStateCodeDependency,
        *dependency.irs_gross_income,
    ]
    pe_outputs = [dependency.tax.CoCareWorkerCredit]


class CoExpandedEitc(Coeitc):
    """
    Colorado Expanded EITC (``co_expanded_eitc``).

    Currently identical to ``Coeitc``: both rows produce the same eligibility and
    value today. It exists as its own class so the registry maps one key to one
    calculator, and so the real divergence has somewhere to land — MFB-1093 gives
    this program a calculator that recognises the population it was created for
    (ITIN filers and childless filers under 25), which ``Coeitc`` excludes.

    Until then this deliberately overrides nothing.
    """

    program_code = "co_expanded_eitc"
