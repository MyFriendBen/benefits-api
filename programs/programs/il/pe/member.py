import programs.programs.federal.pe.member as member
import programs.programs.federal.pe.tax as tax
import programs.programs.policyengine.calculators.dependencies.household as dependency
import programs.programs.policyengine.calculators.dependencies.member as member_dependency
import programs.programs.policyengine.calculators.dependencies.spm as spm_dependency
from programs.programs.calc import MemberEligibility
from programs.programs.policyengine.calculators.base import PolicyEngineMembersCalculator
from screener.models import HouseholdMember


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


class IlHbwd(PolicyEngineMembersCalculator):
    """
    Illinois Health Benefits for Workers with Disabilities (HBWD).

    HBWD is a Medicaid buy-in program for working individuals with disabilities.

    PolicyEngine calculates eligibility based on:
    - Age (16-64 years via monthly_age)
    - Disability (is_ssi_disabled OR social_security_disability > 0)
    - Employment (il_hbwd_gross_earned_income > 0 as FICA proxy)
    - Income (il_hbwd_countable_income vs spm_unit_fpg threshold)
    - Assets (spm_unit_cash_assets + il_aabd_countable_vehicle_value < $25,000)
    - Immigration (immigration_status = citizen or qualifying noncitizen)

    Returns: 
        - il_hbwd_person = -il_hbwd_premium (negative premium = cost to individual)
        - il_hbwd_eligible
    """

    pe_name = "il_hbwd_person"
    pe_inputs = [
        # age eligible
        member_dependency.AgeDependency,
        # disability eligible (is_ssi_disabled + social_security_disability)
        member_dependency.IsBlindDependency,
        member_dependency.SsiReportedDependency,
        member_dependency.IsDisabledDependency,
        member_dependency.SsiEarnedIncomeDependency,
        member_dependency.SsdiReportedDependency,
        # employment eligible
        member_dependency.IlHbwdGrossEarnedIncomeDependency,
        # income eligible
        # not providing il_aabd_expense_exemption_person - includes details we don't have
        # conservative estimate by excluding it (since subtracted from income)
        member_dependency.IlAabdGrossEarnedIncomeDependency,
        member_dependency.IlAabdGrossUnearnedIncomeDependency,
        member_dependency.IlHbwdGrossUnearnedIncomeDependency,
        # asset eligibility
        # not including il_aabd_countable_vehicle_value since we don't have
        spm_dependency.CashAssetsDependency,
        # state requirement
        dependency.IlStateCodeDependency,
    ]
    pe_outputs = [member_dependency.IlHbwdEligible, member_dependency.IlHbwdPremium]

    def member_value(self, member) -> int:
        """
        Do not use IlHbwdPremium - it returns a negative premium which represents
        the cost to the individual, not the benefit value.
        """
        is_eligible = self.get_member_dependency_value(member_dependency.IlHbwdEligible, member.id)
        if is_eligible:
            # >0 member_value indicates eligible
            return 1
        
        return 0
