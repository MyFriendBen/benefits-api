from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
from programs.programs.federal.pe.tax import Cdcc, Ctc, Eitc
import programs.framework.pe_dependencies as dependency


class Kseitc(PolicyEngineTaxUnitCalulator):
    name_abbreviated = "ks_eitc"
    pe_name = "ks_total_eitc"
    pe_inputs = [
        *Eitc.pe_inputs,
        dependency.household.KsStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.Kseitc]


class KsCdcc(PolicyEngineTaxUnitCalulator):
    name_abbreviated = "ks_cdcc"
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


class KsCtc(Ctc):
    """
    Federal Child Tax Credit surfaced to Kansas users as ``ks_ctc``.

    Kansas has no state CTC, so this reads PolicyEngine's federal ``ctc_value``
    unchanged. Note the asymmetry with ``ks_eitc``, which resolves to ``Kseitc``
    and does send a state code: that one reads ``ks_total_eitc``, a genuinely
    Kansas-specific PolicyEngine variable. State code follows the variable, not
    the key prefix.
    """

    name_abbreviated = "ks_ctc"


class KsCdccFederal(Cdcc):
    """
    Federal Child and Dependent Care Credit surfaced to Kansas users as
    ``ks_cdcc_federal``.

    Distinct from ``ks_cdcc``, which is Kansas's own credit and has its own
    calculator (``KsCdcc``). This one reads PolicyEngine's federal ``cdcc``
    unchanged and exists so the registry maps one key to one calculator.
    """

    name_abbreviated = "ks_cdcc_federal"
