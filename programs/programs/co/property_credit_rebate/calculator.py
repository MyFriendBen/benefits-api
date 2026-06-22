from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
import programs.programs.messages as messages
from screener.models import HouseholdMember


class PropertyCreditRebate(ProgramCalculator):
    amount = 1_154
    min_age = 65
    disabled_min_age = 18
    expenses = ["rent", "mortgage"]
    income_limit = {"single": 18_704, "married": 25_261}
    dependencies = ["age", "income_frequency", "income_amount", "relationship"]

    def household_eligible(self, e: Eligibility) -> None:
        # Income test
        relationship_status = "single"
        for _, married_to in self.screen.relationship_map().items():
            if married_to is not None:
                relationship_status = "married"

        gross_income = self.screen.calc_gross_income("yearly", ["all"])
        e.condition(
            gross_income <= self.income_limit[relationship_status],
            messages.income(gross_income, self.income_limit[relationship_status]),
        )

        # has rent or mortgage expense
        e.condition(self._has_expense())

    def _has_expense(self):
        return self.screen.has_expense(self.expenses)

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member
        if member.age is None:
            return

        # disabled
        is_disabled = self._member_is_disabled(member)

        # surviving spouse
        is_surviving_spouse = self._is_surviving_spouse(member)

        # age
        is_old_enough = member.age >= self.min_age

        e.condition(is_disabled or is_old_enough or is_surviving_spouse)

    def _member_is_disabled(self, member: HouseholdMember):
        return member.has_disability() and member.age > self.disabled_min_age

    def _is_surviving_spouse(self, member: HouseholdMember) -> bool:
        # we don't ask this question in the normal MFB route
        return False
