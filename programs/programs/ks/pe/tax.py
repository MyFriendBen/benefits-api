from programs.programs.policyengine.calculators.base import PolicyEngineTaxUnitCalulator
from programs.programs.federal.pe.tax import Eitc
import programs.programs.policyengine.calculators.dependencies as dependency


class Kseitc(PolicyEngineTaxUnitCalulator):
    pe_name = "ks_total_eitc"
    pe_inputs = [
        *Eitc.pe_inputs,
        dependency.household.KsStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.Kseitc]


class KsCdcc(PolicyEngineTaxUnitCalulator):
    pe_name = "ks_cdcc"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.TaxUnitHeadDependency,
        dependency.member.TaxUnitSpouseDependency,
        dependency.member.TaxUnitDependentDependency,
        dependency.member.IsDisabledDependency,
        dependency.member.IsIncapableOfSelfCareDependency,
        dependency.member.FullTimeCollegeStudentDependency,
        dependency.spm.ChildCareDependency,
        dependency.member.CareExpensesDependency,
        dependency.household.KsStateCodeDependency,
        *dependency.irs_gross_income,
    ]
    pe_outputs = [dependency.tax.KsCdcc]
