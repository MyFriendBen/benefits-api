from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
from programs.programs.helpers import medicaid_eligible
import programs.programs.messages as messages
from programs.programs.mixins import IlMedicaidFplIncomeCheckMixin


class AcaAdults(ProgramCalculator, IlMedicaidFplIncomeCheckMixin):
    member_amount = 474 * 12  # $474/month
    min_age = 19
    max_age = 64
    caretaker_roles = [
        "headOfHousehold",
        "spouse",
        "domesticPartner",
        "parent",
        "fosterParent",
    ]
    dependencies = ["age", "household_size", "relationship", "pregnant", "income_amount", "income_frequency"]

    def household_eligible(self, e: Eligibility):
        # Must have base Medicaid eligibility
        e.condition(medicaid_eligible(self.data), messages.must_have_benefit("Medicaid"))

        # Check income against 138% FPL (includes 5% disregard)
        self.check_fpl_income(e, 1.38)

        # Must NOT be eligible for FamilyCare
        family_care_eligible = "il_family_care" in self.data and self.data["il_family_care"].eligible
        e.condition(not family_care_eligible, messages.must_not_have_benefit("FamilyCare"))

        # Must NOT be eligible for Moms & Babies
        moms_and_babies_eligible = "il_moms_and_babies" in self.data and self.data["il_moms_and_babies"].eligible
        e.condition(not moms_and_babies_eligible, messages.must_not_have_benefit("Moms & Babies"))

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # Must be age 19-64
        e.condition(member.age >= self.min_age and member.age <= self.max_age)

        # Must NOT be pregnant
        e.condition(not member.pregnant)

        # Must NOT be a parent/caretaker of children
        is_caretaker = member.relationship in self.caretaker_roles
        has_children = (
            self.screen.num_children(age_max=18, child_relationship=["child", "fosterChild", "stepChild", "grandChild"])
            > 0
        )

        e.condition(not (is_caretaker and has_children))

        # Must not have Medicaid
        e.condition(not member.has_benefit("medicaid"))
