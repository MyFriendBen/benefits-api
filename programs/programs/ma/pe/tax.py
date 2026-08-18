from programs.programs.federal.pe.tax import Aca, Eitc
import programs.framework.pe_dependencies as dependency
from programs.framework.pe_base import PolicyEngineTaxUnitCalulator


class Maeitc(PolicyEngineTaxUnitCalulator):
    pe_name = "ma_eitc"
    pe_inputs = [
        *Eitc.pe_inputs,
        dependency.household.MaStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.Maeitc]


class MaChildFamilyCredit(PolicyEngineTaxUnitCalulator):
    pe_name = "ma_child_and_family_credit"
    pe_inputs = [
        dependency.member.TaxUnitDependentDependency,
        dependency.member.AgeDependency,
        dependency.member.IsDisabledDependency,
        dependency.household.MaStateCodeDependency,
        *dependency.irs_gross_income,
    ]
    pe_outputs = [dependency.tax.MaChildFamilyCredit]


class MaAca(Aca):
    pe_inputs = [
        *Aca.pe_inputs,
        dependency.household.MaStateCodeDependency,
    ]
