from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
from programs.programs.helpers import medicaid_eligible
import programs.programs.messages as messages
from programs.programs.mixins import IlMedicaidFplIncomeCheckMixin


class FamilyCare(ProgramCalculator, IlMedicaidFplIncomeCheckMixin):
    member_amount = 474 * 12
    max_child_age = 18
    fpl_percent = 1.38
    qualifying_child_relationships = ["child", "fosterChild", "stepChild", "grandChild"]
    caretaker_relationships = ["headOfHousehold", "spouse", "domesticPartner", "parent", "fosterParent"]
    dependencies = ["age", "household_size", "relationship", "pregnant", "income_amount", "income_frequency"]

    def household_eligible(self, e: Eligibility):
        # Must have base Medicaid eligibility
        e.condition(medicaid_eligible(self.data), messages.must_have_benefit("Medicaid"))

        # Check income against 138% FPL (includes 5% disregard)
        self.check_fpl_income(e, self.fpl_percent)

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

        # Must not have Medicaid
        e.condition(not member.has_benefit("medicaid"))
