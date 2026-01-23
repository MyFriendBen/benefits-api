from programs.programs.policyengine.calculators.base import PolicyEngineTaxUnitCalulator
from programs.programs.federal.pe.tax import Eitc, Ctc
import programs.programs.policyengine.calculators.dependencies as dependency


class Coeitc(PolicyEngineTaxUnitCalulator):
    pe_name = "co_eitc"
    pe_inputs = [
        *Eitc.pe_inputs,
        dependency.household.CoStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.Coeitc]


class Coctc(PolicyEngineTaxUnitCalulator):
    pe_name = "co_ctc"
    pe_inputs = [
        *Ctc.pe_inputs,
        dependency.household.CoStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.Coctc]


class CoCareWorkerCredit(PolicyEngineTaxUnitCalulator):
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
