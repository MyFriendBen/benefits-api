"""TX Medicaid."""

from programs.programs.cross_white_label.medicaid.base import Medicaid
from screener.models import HouseholdMember
import programs.framework.pe_dependencies as dependency


class TxEmergencyMedicaid(Medicaid):
    """
    Texas Emergency Medicaid for Non-Citizens calculator that uses PolicyEngine's calculated benefit amounts.

    This program provides limited public health insurance that covers only emergency health care costs.
    It helps people who cannot get standard Medicaid because of their immigration status.

    Eligibility requirements:
    - Must have a life-threatening or serious medical condition requiring urgent care
    - Immigration status makes them ineligible for standard Medicaid
    - Covers emergency services including emergency labor and delivery
    - Only covers services needed to stabilize the condition, not ongoing care

    Notes:
    - The citizenship eligibility is handled at the program configuration level
      (legal_status_required), not in this calculator.
    - We do not ask users whether they have an emergency medical condition in the screener.
      Instead, this requirement is communicated in the program's description so users understand
      they must have a qualifying condition to receive benefits.
    """

    program_code = "tx_emergency_medicaid"

    pe_inputs = [
        *Medicaid.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]

    def member_value(self, member: HouseholdMember):
        """
        Returns 1 if the member is eligible for Emergency Medicaid, 0 otherwise.

        The actual benefit value varies based on the emergency care needed, so we return
        a nominal value of 1 to indicate eligibility rather than a specific dollar amount.
        """
        # Must not have other health insurance
        if not member.has_insurance_types(("none",)):
            return 0

        pe_value = self.get_member_variable(member.id)
        return 1 if pe_value > 0 else 0


class TxMedicaidForChildren(Medicaid):
    """
    Texas Medicaid for Children calculator that uses PolicyEngine's calculated benefit amounts.

    This program provides free health insurance for children under 19 who do not have
    other health insurance coverage.

    Eligibility requirements:
    - Must be under 19 years old (18 and under)
    - Must not have other health insurance
    - Income eligibility determined by PolicyEngine
    """

    program_code = "tx_medicaid_for_children"

    pe_inputs = [
        *Medicaid.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]

    def member_value(self, member: HouseholdMember):
        """
        Returns the Medicaid benefit value for children under 19 without other insurance.
        """
        # Must be under 19
        if member.age >= 19:
            return 0

        # Must not have other health insurance
        if not member.has_insurance_types(("none",)):
            return 0

        # Return PolicyEngine-calculated value
        return self.get_member_variable(member.id)


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


class TxMedicaidForPregnantWomen(Medicaid):
    """
    Texas Medicaid for Pregnant Women calculator that uses PolicyEngine's calculated benefit amounts.

    This program provides free health insurance for pregnant women who do not have
    other health insurance coverage.

    Eligibility requirements:
    - Must be pregnant
    - Must not have other health insurance
    - Income eligibility determined by PolicyEngine
    """

    program_code = "tx_medicaid_for_pregnant_women"

    pe_inputs = [
        *Medicaid.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]

    def member_value(self, member: HouseholdMember):
        """
        Returns the Medicaid benefit value for pregnant women without other insurance.
        """
        # Must be pregnant
        if not member.pregnant:
            return 0

        # Must not have other health insurance
        if not member.has_insurance_types(("none",)):
            return 0

        # Return PolicyEngine-calculated value
        return self.get_member_variable(member.id)
