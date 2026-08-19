"""ACA premium tax credit."""

from programs.programs.cross_white_label.medicaid.base import Medicaid
from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
import programs.framework.pe_dependencies as dependency


class Aca(PolicyEngineTaxUnitCalulator, abstract=True):
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
