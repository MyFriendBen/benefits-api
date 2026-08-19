"""Child and Dependent Care Credit."""

from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
import programs.framework.pe_dependencies as dependency


class Cdcc(PolicyEngineTaxUnitCalulator, abstract=True):
    pe_name = "cdcc"
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
        *dependency.irs_gross_income,
    ]
    pe_outputs = [dependency.tax.Cdcc]
