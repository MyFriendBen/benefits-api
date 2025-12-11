import programs.programs.federal.pe.member as member
import programs.programs.federal.pe.tax as tax
import programs.programs.policyengine.calculators.dependencies.household as dependency
import programs.programs.policyengine.calculators.dependencies.member as member_dependency
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
        dependency.IlStateCodeDependency,
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
        dependency.IlStateCodeDependency,
    ]


class IlAca(tax.Aca):
    pe_name = "aca_ptc"
    pe_inputs = [
        *tax.Aca.pe_inputs,
        dependency.IlStateCodeDependency,
        dependency.IlCountyDependency,
    ]


class IlAabd(PolicyEngineMembersCalculator):
    pe_name = "il_aabd_person"
    pe_inputs = [
        member_dependency.AgeDependency,
        member_dependency.IsDisabledDependency,
        member_dependency.IsBlindDependency,
        member_dependency.IlAabdGrossEarnedIncomeDependency,
        member_dependency.IlAabdGrossUnearnedIncomeDependency,
        dependency.IlStateCodeDependency,
    ]
    pe_outputs = [member_dependency.IlAabd]


class IlMpe(PolicyEngineMembersCalculator):
    # name = "Medicaid Presumptive Eligibility (Pregnancy)"
    pe_name = "il_mpe_eligible"
    pe_category = "people"

    pe_inputs = [
        member_dependency.AgeDependency,
        member_dependency.IlMpeIncomeEligibleDependency,
        dependency.IlStateCodeDependency,
        member_dependency.PregnancyDependency,
    ]

    pe_outputs = [
        member_dependency.IlMpeEligible,
    ]

    def member_value(self, member):
        is_eligible = super().member_value(member)
        is_pregnant = member.pregnant

        insurance = getattr(member, "insurance", None)
        has_medicaid = getattr(insurance, "medicaid", False)
        if has_medicaid:
            return False

        return is_eligible and is_pregnant
