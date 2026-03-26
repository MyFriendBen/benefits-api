from programs.programs.federal.pe.member import Medicaid
from programs.programs.policyengine.calculators.base import PolicyEngineTaxUnitCalulator
import programs.programs.policyengine.calculators.dependencies as dependency


class Eitc(PolicyEngineTaxUnitCalulator):
    pe_name = "eitc"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.TaxUnitSpouseDependency,
        dependency.member.TaxUnitDependentDependency,
        *dependency.irs_gross_income,
    ]
    pe_outputs = [dependency.tax.Eitc]


class Ctc(PolicyEngineTaxUnitCalulator):
    pe_name = "ctc_value"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.TaxUnitDependentDependency,
        dependency.member.TaxUnitSpouseDependency,
        *dependency.irs_gross_income,
    ]
    pe_outputs = [dependency.tax.Ctc]


class Aca(PolicyEngineTaxUnitCalulator):
    pe_name = "aca_ptc"
    pe_inputs = [
        *Medicaid.pe_inputs,
        dependency.member.TaxUnitDependentDependency,
        dependency.member.TaxUnitHeadDependency,
        dependency.member.TaxUnitSpouseDependency,
        dependency.member.AgeDependency,
        dependency.member.IsDisabledDependency,
        dependency.household.ZipCodeDependency,
        *dependency.irs_gross_income,
    ]
    pe_outputs = [dependency.tax.Aca]
