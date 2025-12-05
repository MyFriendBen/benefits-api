import programs.programs.federal.pe.member as member
import programs.programs.federal.pe.tax as tax
import programs.programs.policyengine.calculators.dependencies.household as hh_dependency
import programs.programs.policyengine.calculators.dependencies.member as member_dependency
import programs.programs.policyengine.calculators.dependencies.spm as spm_dependency
from programs.programs.policyengine.calculators.base import PolicyEngineMembersCalculator


class IlMedicaid(member.Medicaid):
    """Base Illinois Medicaid eligibility through PolicyEngine"""

    medicaid_categories = {
        "NONE": 0,
        "ADULT": 474,
        "INFANT": 0,
        "YOUNG_CHILD": 0,
        "OLDER_CHILD": 0,
        "PREGNANT": 474,
        "YOUNG_ADULT": 0,
        "PARENT": 474,
        "SSI_RECIPIENT": 474,
        "AGED": 474,
        "DISABLED": 474,
    }
    pe_inputs = [
        *member.Medicaid.pe_inputs,
        hh_dependency.IlStateCodeDependency,
    ]


class IlWic(member.Wic):
    wic_categories = {
        "NONE": 0,
        "INFANT": 130,
        "CHILD": 79,
        "PREGNANT": 104,
        "POSTPARTUM": 88,
        "BREASTFEEDING": 121,
    }
    pe_inputs = [
        *member.Wic.pe_inputs,
        hh_dependency.IlStateCodeDependency,
    ]


class IlAca(tax.Aca):
    pe_name = "aca_ptc"
    pe_inputs = [
        *tax.Aca.pe_inputs,
        hh_dependency.IlStateCodeDependency,
        hh_dependency.IlCountyDependency,
    ]


# TODO: may need to add metered_gas_expense and electricity_expense if PE continues to incorporate expenses
# TODO: send components of IsSSIDisabledDependency instead of IsSSIDisabledDependency
class IlAabd(PolicyEngineMembersCalculator):
    pe_name = "il_aabd_person"
    pe_inputs = [
        member_dependency.AgeDependency,
        member_dependency.IsBlindDependency,
        member_dependency.IsDisabledDependency,
        member_dependency.SsiEarnedIncomeDependency,
        member_dependency.SsiReportedDependency,
        member_dependency.IlAabdGrossEarnedIncomeDependency,
        member_dependency.IlAabdGrossUnearnedIncomeDependency,
        member_dependency.RentDependency,
        member_dependency.PropertyTaxDependency,
        spm_dependency.MortgageDependency,
        spm_dependency.HOADependency,
        spm_dependency.HomeownersInsuranceDependency,
        spm_dependency.CashAssetsDependency,
        spm_dependency.ChildCareDependency,
        hh_dependency.IlStateCodeDependency,
        hh_dependency.IlCountyDependency,
    ]
    pe_outputs = [member_dependency.IlAabd]
