"""Chp."""

from screener.models import HouseholdMember
from programs.framework.pe_base import PolicyEngineMembersCalculator
import programs.framework.pe_dependencies as dependency


class Chp(PolicyEngineMembersCalculator):
    program_code = "chp"
    pe_name = "co_chp"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.PregnancyDependency,
        dependency.member.ExpectedChildrenPregnancyDependency,
        dependency.household.CoStateCodeDependency,
        *dependency.irs_gross_income,
    ]
    pe_outputs = [dependency.member.ChpEligible]

    amount = 200 * 12

    def member_value(self, member: HouseholdMember):
        chp_eligible = self.get_member_dependency_value(dependency.member.ChpEligible, member.id) > 0

        if chp_eligible and self.screen.has_insurance_types(("none",)):
            return self.amount

        return 0
