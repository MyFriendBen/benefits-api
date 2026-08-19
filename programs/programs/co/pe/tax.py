from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
import programs.framework.pe_dependencies as dependency
from programs.programs.cross_white_label.eitc.base import Eitc
from programs.programs.cross_white_label.ctc.base import Ctc


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
