from programs.programs.policyengine.calculators.base import PolicyEngineTaxUnitCalulator
import programs.programs.policyengine.calculators.dependencies as dependency


class KsCdcc(PolicyEngineTaxUnitCalulator):
    pe_name = "ks_cdcc"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.TaxUnitHeadDependency,
        dependency.member.TaxUnitSpouseDependency,
        dependency.member.TaxUnitDependentDependency,
        dependency.member.IsDisabledDependency,
        dependency.spm.ChildCareDependency,
        dependency.household.KsStateCodeDependency,
        *dependency.irs_gross_income,
    ]
    pe_outputs = [dependency.tax.KsCdcc]
