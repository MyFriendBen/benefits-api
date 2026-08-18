from programs.programs.federal.pe.member import Medicaid
from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
import programs.framework.pe_dependencies as dependency


class Eitc(PolicyEngineTaxUnitCalulator):
    name_abbreviated = "eitc"
    pe_name = "eitc"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.TaxUnitSpouseDependency,
        dependency.member.TaxUnitDependentDependency,
        *dependency.irs_gross_income,
    ]
    pe_outputs = [dependency.tax.Eitc]


class Ctc(PolicyEngineTaxUnitCalulator):
    name_abbreviated = "ctc"
    pe_name = "ctc_value"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.TaxUnitDependentDependency,
        dependency.member.TaxUnitSpouseDependency,
        *dependency.irs_gross_income,
    ]
    pe_outputs = [dependency.tax.Ctc]


class Cdcc(PolicyEngineTaxUnitCalulator):
    name_abbreviated = "ks_cdcc_federal"
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
