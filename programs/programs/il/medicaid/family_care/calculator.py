from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
from programs.programs.helpers import medicaid_eligible
import programs.programs.messages as messages


class FamilyCare(ProgramCalculator):
    member_amount = 474 * 12
    max_child_age = 18
    fpl_percent = 1.38
    qualifying_child_relationships = ["child", "fosterChild", "stepChild", "grandChild"]
    caretaker_relationships = ["headOfHousehold", "spouse", "domesticPartner", "parent", "fosterParent"]
    dependencies = ["age", "household_size", "relationship", "pregnant", "income_amount", "income_frequency"]

    def household_eligible(self, e: Eligibility):
        # Must have base Medicaid eligibility
        e.condition(medicaid_eligible(self.data), messages.must_have_benefit("Medicaid"))

        # Income must be at or below 138% FPL
        fpl = self.program.year
        income_limit = int(self.fpl_percent * fpl.get_limit(self.screen.household_size))
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))

        e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # Pregnant members are eligible
        is_pregnant = member.pregnant

        # Caretakers of qualifying children are eligible
        has_qualifying_children = (
            self.screen.num_children(age_max=self.max_child_age, child_relationship=self.qualifying_child_relationships)
            > 0
        )

        is_caretaker = member.relationship in self.caretaker_relationships

        e.condition(is_pregnant or (has_qualifying_children and is_caretaker))
