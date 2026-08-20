from programs.framework.base import MemberEligibility, ProgramCalculator, Eligibility
import programs.framework.eligibility_messages as messages
from programs.programs.white_labels.il.medicaid_fpl_mixin import IlMedicaidFplIncomeCheckMixin


class FamilyCare(ProgramCalculator, IlMedicaidFplIncomeCheckMixin):
    program_code = "il_family_care"
    member_amount = 474 * 12
    max_child_age = 18
    fpl_percent = 1.38
    qualifying_child_relationships = ["child", "fosterChild", "stepChild", "grandChild"]
    caretaker_relationships = ["headOfHousehold", "spouse", "domesticPartner", "parent", "fosterParent"]
    dependencies = ["age", "household_size", "relationship", "pregnant", "income_amount", "income_frequency"]

    def household_eligible(self, e: Eligibility):
        # Must have base Medicaid eligibility
        e.condition(self.medicaid_eligible("il_medicaid"), messages.must_have_benefit("Medicaid"))

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
        e.condition(not member.has_insurance("medicaid"))
