"""TxEmergencyMedicaid."""

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
