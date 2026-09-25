from programs.framework.base import MemberEligibility, ProgramCalculator, Eligibility, HouseholdMember
from programs.programs.white_labels.il.medicaid_fpl_mixin import IlMedicaidFplIncomeCheckMixin


class MomsAndBabies(ProgramCalculator, IlMedicaidFplIncomeCheckMixin):
    program_code = "il_moms_and_babies"
    adult_member_amount = 474 * 12  # $474/month for adults
    newborn_member_amount = 284 * 12  # $284/month for newborns
    fpl_percent = 2.13  # 213% FPL
    max_newborn_age_months = 2
    min_adult_age = 19  # Adults must be 19+
    parent_relationships = ["headOfHousehold", "spouse", "domesticPartner", "parent", "fosterParent"]
    dependencies = ["age", "household_size", "relationship", "pregnant", "income_amount", "income_frequency"]

    def _is_eligible_newborn(self, member: HouseholdMember) -> bool:
        if member.birth_year_month is None:
            return member.calc_age() == 0

        reference_date = self.screen.get_reference_date()
        age_months = (reference_date.year - member.birth_year) * 12 + reference_date.month - member.birth_month
        return 0 <= age_months <= self.max_newborn_age_months

    def _is_eligible_adult(self, member: HouseholdMember) -> bool:
        is_old_enough = member.calc_age() >= self.min_adult_age
        is_parent = member.relationship in self.parent_relationships
        is_pregnant = member.pregnant
        has_eligible_newborn = any(self._is_eligible_newborn(m) for m in self.screen.household_members.all())

        return is_old_enough and is_parent and (is_pregnant or has_eligible_newborn)

    def _has_eligible_adult(self, members: list[HouseholdMember]) -> bool:
        return any(self._is_eligible_adult(member) for member in members)

    def household_eligible(self, e: Eligibility):
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
        e.condition(not member.has_insurance("medicaid"))

    def member_value(self, member: HouseholdMember) -> int:
        if self._is_eligible_newborn(member):
            return self.newborn_member_amount

        return self.adult_member_amount
