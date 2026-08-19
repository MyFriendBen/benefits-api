from programs.programs.federal.pe.tax import Aca
import programs.framework.pe_dependencies as dependency
from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
from programs.programs.cross_white_label.eitc.base import Eitc


class Maeitc(PolicyEngineTaxUnitCalulator):
    program_code = "ma_maeitc"
    pe_name = "ma_eitc"
    pe_inputs = [
        *Eitc.pe_inputs,
        dependency.household.MaStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.Maeitc]


class MaChildFamilyCredit(PolicyEngineTaxUnitCalulator):
    program_code = "ma_cfc"
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
    program_code = "ma_aca"
    pe_inputs = [
        *Aca.pe_inputs,
        dependency.household.MaStateCodeDependency,
    ]
