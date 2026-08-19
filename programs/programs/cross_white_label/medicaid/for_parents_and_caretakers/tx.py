"""TxMedicaidForParentsAndCaretakers."""

from programs.programs.cross_white_label.medicaid.base import Medicaid
from screener.models import HouseholdMember
import programs.framework.pe_dependencies as dependency


class TxMedicaidForParentsAndCaretakers(Medicaid):
    """
    Texas Medicaid for Parents and Caretakers calculator that uses PolicyEngine's calculated benefit amounts.

    This program provides free or low-cost health insurance for low-income caretakers of children
    who receive Medicaid. Eligible caretakers must meet income rules and have a qualifying relationship
    to a child in the household who has or qualifies for Medicaid.

    Eligibility requirements:
    - Must be 19 years or older (adult)
    - Must not have other health insurance
    - Household must have a child under 19
    - Child must have Medicaid or qualify for Medicaid (PE-calculated value > 0)
    - Must have a qualifying relationship to a child: parent, step-parent, sibling, step-sibling, grandparent, or related in some other way
    - Income eligibility determined by PolicyEngine
    """

    program_code = "tx_medicaid_for_parents_and_caretakers"

    pe_inputs = [
        *Medicaid.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]

    # Relationships that qualify as caretakers for this program.
    # Note that the relationship field describes each member's relationship TO
    # the head of household. We're including "headOfHousehold" here because
    # the head has relationship="headOfHousehold", and we're assuming that
    # they're an adult.
    caretaker_relationships = [
        "headOfHousehold",
        "spouse",
        "domesticPartner",
        "parent",
        "stepParent",
        "grandParent",
        "sisterOrBrother",
        "stepSisterOrBrother",
        "relatedOther",
    ]

    def member_value(self, member: HouseholdMember):
        """
        Returns the Medicaid benefit value for adults who are caretakers of children with Medicaid.
        """
        # Must be 19 or older (adult caretaker)
        if member.age < 19:
            return 0

        # Must not have other health insurance
        if not member.has_insurance_types(("none",)):
            return 0

        # Must have a qualifying caretaker relationship
        if member.relationship not in self.caretaker_relationships:
            return 0

        # Household must have a child under 19 who has or qualifies for Medicaid
        if not self._has_child_with_medicaid():
            return 0

        # Return PolicyEngine-calculated value
        return self.get_member_variable(member.id)

    def _has_child_with_medicaid(self) -> bool:
        """
        Check if the household has at least one child under 19 who has Medicaid
        or qualifies for Medicaid (based on PE calculation).
        """
        for member in self.screen.household_members.all():
            # Child must be under 19
            if member.age >= 19:
                continue

            # Check if child has Medicaid already
            if member.has_insurance("medicaid"):
                return True

            # Check if child qualifies for Medicaid (PE value > 0)
            child_medicaid_value = self.get_member_dependency_value(dependency.member.Medicaid, member.id)
            if child_medicaid_value > 0:
                return True

        return False
