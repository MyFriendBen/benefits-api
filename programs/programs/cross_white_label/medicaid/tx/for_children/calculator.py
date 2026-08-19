"""TxMedicaidForChildren."""

from programs.programs.cross_white_label.medicaid.base import Medicaid
from screener.models import HouseholdMember
import programs.framework.pe_dependencies as dependency


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
