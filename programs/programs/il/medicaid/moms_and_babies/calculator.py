from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility, HouseholdMember
from programs.programs.helpers import medicaid_eligible
import programs.programs.messages as messages
from programs.programs.mixins import IlMedicaidFplIncomeCheckMixin


class MomsAndBabies(ProgramCalculator, IlMedicaidFplIncomeCheckMixin):
    adult_member_amount = 474 * 12  # $474/month for adults
    newborn_member_amount = 284 * 12  # $284/month for newborns
    fpl_percent = 2.13  # 213% FPL
    max_newborn_age_months = 2 / 12  # 2 months as fraction of year
    min_adult_age = 19  # Adults must be 19+
    parent_relationships = ["headOfHousehold", "spouse", "domesticPartner", "parent", "fosterParent"]
    dependencies = ["age", "household_size", "relationship", "pregnant", "income_amount", "income_frequency"]

    def _is_eligible_newborn(self, member: HouseholdMember) -> bool:
        return member.age <= self.max_newborn_age_months

    def _is_eligible_adult(self, member: HouseholdMember) -> bool:
        is_old_enough = member.age >= self.min_adult_age
        is_parent = member.relationship in self.parent_relationships
        is_pregnant = member.pregnant
        has_eligible_newborn = self.screen.num_children(age_max=self.max_newborn_age_months) > 0

        return is_old_enough and is_parent and (is_pregnant or has_eligible_newborn)

    def _has_eligible_adult(self, members: list[HouseholdMember]) -> bool:
        return any(self._is_eligible_adult(member) for member in members)

    def household_eligible(self, e: Eligibility):
        # Must NOT be eligible for FamilyCare
        family_care_eligible = "il_family_care" in self.data and self.data["il_family_care"].eligible

        e.condition(not family_care_eligible, messages.must_not_have_benefit("FamilyCare"))

        # Income must be at or below 213% FPL
        self.check_fpl_income(e, self.fpl_percent)

        # Must have eligible adult
        e.condition(self._has_eligible_adult(self.screen.household_members.all()))

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # Must be an eligible adult or newborn in household with eligible adult
        is_eligible_adult = self._is_eligible_adult(member)
        is_eligible_newborn = self._is_eligible_newborn(member)
        household_has_eligible_adult = self._has_eligible_adult(self.screen.household_members.all())

        e.condition(is_eligible_adult or (is_eligible_newborn and household_has_eligible_adult))

        # Must not have Medicaid
        e.condition(not member.has_benefit("medicaid"))

    def member_value(self, member: HouseholdMember) -> int:
        if self._is_eligible_newborn(member):
            return self.newborn_member_amount

        return self.adult_member_amount
