import programs.programs.federal.pe.member as member
import programs.programs.federal.pe.tax as tax
import programs.programs.policyengine.calculators.dependencies.household as dependency
import programs.programs.policyengine.calculators.dependencies.member as member_dependency
import programs.programs.policyengine.calculators.dependencies.spm as spm_dependency
from programs.programs.calc import MemberEligibility
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

    Returns: il_hbwd_person = -il_hbwd_premium (negative premium = cost to individual)

    TODO: Add missing dependencies once created in member.py:
          - is_ssi_disabled
          - immigration_status
          - spm_unit_fpg (may exist in spm.py)
          - spm_unit_cash_assets (exists in spm.py)
          - il_aabd_countable_vehicle_value
    """
    pe_name = "il_hbwd_person"
    pe_inputs = [
        # age eligible
        member_dependency.AgeDependency,
        # disability eligible (used to calculate "is_ssi_disabled")
        member_dependency.IsBlindDependency,
        member_dependency.SsiReportedDependency,
        member_dependency.IsDisabledDependency,
        member_dependency.SsiEarnedIncomeDependency,
        member_dependency.SsdiReportedDependency,
        # employment eligible
        member_dependency.IlHbwdGrossEarnedIncomeDependency,
        # income eligible
        member_dependency.IlAabdGrossEarnedIncomeDependency,
        member_dependency.IlAabdGrossUnearnedIncomeDependency,
        member_dependency.IlHbwdGrossUnearnedIncomeDependency,
        # asset eligibility
        spm_dependency.CashAssetsDependency,
        # state requirement
        dependency.IlStateCodeDependency,
    ]
    pe_outputs = [member_dependency.IlHbwdEligible, member_dependency.IlHbwdPremium]

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # Use il_hbwd_eligible for eligibility determination (not il_hbwd_person)
        is_eligible = self.get_member_dependency_value(member_dependency.IlHbwdEligible, member.id)
        e.condition(is_eligible)

        # Call member_value() to set the value
        member_value = self.member_value(member)
        e.value = member_value

    def member_value(self, _):
        """
        HBWD provides access to health coverage but we don't quantify its dollar value.

        NOTE: Do not use il_hbwd_person - it returns a negative premium which represents
        the cost to the individual, not the benefit value. We do not have the estimated value.
        """
        return 0

    def get_member_variable(self, _: int):
        """
        Override to prevent accidental usage of il_hbwd_person.

        This calculator uses il_hbwd_eligible and il_hbwd_premium from pe_outputs
        instead of the il_hbwd_person pe_name variable to avoid confusion with
        negative premium values.
        """
        raise NotImplementedError(
            "Do not use get_member_variable() for IlHbwd. "
            "We only have the premium (IlHbwdPremium) and not the estimated value of the coverage."
        )
