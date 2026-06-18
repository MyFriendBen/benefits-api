from programs.programs.calc import MemberEligibility, ProgramCalculator
from programs.util import Dependencies
from screener.models import HouseholdMember, Screen
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from programs.models import Program


class Ssdi(ProgramCalculator):
    income_limit = 1_620
    income_limit_blind = 2_700
    amount = 1_580
    min_age = 18
    max_age = 65
    ineligible_relationships = ["fosterChild", "grandChild"]
    parent_relationships = ["spouse", "domesticPartner", "headOfHousehold"]
    dependencies = ["income_amount", "income_frequency", "household_size"]

    def __init__(self, screen: Screen, program: "Program", data, missing_dependencies: Dependencies) -> None:
        self.eligible_members = []
        super().__init__(screen, program, data, missing_dependencies)

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member

        # disability
        e.condition(member.has_disability())

        # no SSDI income
        e.condition(member.calc_gross_income("yearly", ["sSDisability"]) == 0)

        # income
        income_limit = Ssdi.income_limit_blind if member.visually_impaired else Ssdi.income_limit
        member_income = member.calc_gross_income("monthly", ("all",))
        e.condition(member_income < income_limit)

        # age
        if member.age is None:
            return
        e.condition(member.age >= Ssdi.min_age or self._child_eligible(member))
        e.condition(member.age <= Ssdi.max_age)

        if e.eligible:
            self.eligible_members.append(member)

    def _parents_with_disability_ssdi_value(self):
        total = 0
        for member in self.screen.household_members.all():
            if not self._is_parent_with_disability(member):
                continue
            total += member.calc_gross_income("monthly", ("sSDisability",))

        return total

    def _is_parent_with_disability(self, member: HouseholdMember) -> bool:
        # min parent age
        if member.age is None:
            return False
        if member.age < Ssdi.min_age:
            return False

        # parent relationship
        if member.relationship not in Ssdi.parent_relationships:
            return False

        # has disability
        if not member.has_disability():
            return False

        return True

    def _child_eligible(self, member: HouseholdMember) -> bool:
        # child relationship
        if member.relationship in Ssdi.ineligible_relationships:
            return False

        # unmaried
        if member.is_married()["is_married"]:
            return False

        # parent must also have a disability
        for other_member in self.screen.household_members.all():
            if self._is_parent_with_disability(other_member):
                return True

        return False

    def _parents_with_disability_ssdi_value(self):
        total = 0
        for member in self.screen.household_members.all():
            if not self._is_parent_with_disability(member):
                continue
            total += member.calc_gross_income("monthly", ("sSDisability",))

        return total

    def household_value(self):
        # NOTE: use household value because the total child value has a cap
        child_value = 0
        adult_value = 0
        child_ssdi_value = (self._parents_with_disability_ssdi_value() or Ssdi.amount) / 2
        for member in self.eligible_members:
            if member.age >= Ssdi.min_age:
                adult_value += Ssdi.amount
            else:
                child_value += child_ssdi_value

        total_value = adult_value + min(child_value, Ssdi.amount / 2)

        return total_value * 12
