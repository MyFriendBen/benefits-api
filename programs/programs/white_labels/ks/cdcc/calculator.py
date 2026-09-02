"""KsCdcc."""

from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
import programs.framework.pe_dependencies as dependency


class KsCdcc(PolicyEngineTaxUnitCalulator):
    program_code = "ks_cdcc"
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
