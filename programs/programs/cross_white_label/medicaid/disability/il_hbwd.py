"""IlHbwd."""

from programs.framework.pe_base import PolicyEngineMembersCalculator
import programs.framework.pe_dependencies.household as household_dependency
import programs.framework.pe_dependencies.member as member_dependency
import programs.framework.pe_dependencies.spm as spm_dependency


class IlHbwd(PolicyEngineMembersCalculator):
    """
    Illinois Health Benefits for Workers with Disabilities (HBWD).

    HBWD is a Medicaid buy-in program for working individuals with disabilities.

    PolicyEngine calculates eligibility based on:
    - Age (16-64 years via monthly_age)
    - Disability (is_disabled OR social_security_disability > 0)
    - Employment (il_hbwd_gross_earned_income > 0 as FICA proxy)
    - Income (il_hbwd_countable_income vs spm_unit_fpg threshold)
    - Assets (spm_unit_cash_assets < $25,000; vehicle value not sent since we don't have)
    - Immigration (immigration_status = citizen or qualifying noncitizen)

    Returns:
        - il_hbwd_eligible (boolean eligibility flag)
        - il_hbwd_premium (negative premium = cost to the individual, surfaced but
          not used as the program's member_value)
    """

    program_code = "il_hbwd"

    pe_name = "il_hbwd_person"
    pe_inputs = [
        # age eligible
        member_dependency.AgeDependency,
        # disability eligible
        member_dependency.IsDisabledDependency,
        member_dependency.SsdiReportedDependency,
        # income eligible - unearned income types
        member_dependency.SocialSecurityIncomeDependency,
        member_dependency.WorkersCompensationDependency,
        member_dependency.UnemploymentIncomeDependency,
        member_dependency.RetirementDistributionsDependency,
        member_dependency.AlimonyIncomeDependency,
        member_dependency.InvestmentIncomeDependency,  # covers dividend_income, interest_income, and capital_gains (combined)
        #   farm_income - not collected
        #   farm_rent_income - not collected
        #   debt_relief (cancellation_of_debt) - not collected
        #   illicit_income - not collected
        member_dependency.MiscellaneousIncomeDependency,
        # employment/income eligible - earned income types
        member_dependency.EmploymentIncomeDependency,
        member_dependency.SelfEmploymentIncomeDependency,
        member_dependency.IsBlindDependency,
        # asset eligibility
        #   il_aabd_countable_vehicle_value - not collected
        spm_dependency.CashAssetsDependency,
        # state requirement
        household_dependency.IlStateCodeDependency,
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
