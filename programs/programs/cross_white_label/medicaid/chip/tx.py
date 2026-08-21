"""TxChip."""

from programs.programs.cross_white_label.medicaid.base import Medicaid
from programs.framework.pe_base import PolicyEngineMembersCalculator
import programs.framework.pe_dependencies as dependency


class TxChip(PolicyEngineMembersCalculator):
    """
    Texas CHIP calculator that uses PolicyEngine's calculated benefit amounts
    for TX-specific CHIP eligibility determination.
    Inherits from PolicyEngineMembersCalculator and uses the same inputs as the federal Chip calculator.
    """

    program_code = "tx_chip"

    pe_name = "chip"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.PregnancyDependency,
        *Medicaid.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]
    pe_outputs = [dependency.member.Chip]

    # NOTE: This feels like it belongs in member_eligible, but due to the PolicyEngineCalculator.member_eligible
    # implementation (which sets both MemberEligibilty.eligible and confusingly MemberEligibility.value), this turned
    # out to be the lesser of two evils. It also follows an established pattern for using business logic to act on PE's
    # results (see: benefits-be/programs/programs/cross_white_label/medicaid/chip/co.py#L74).
    def member_value(self, member):
        """
        Returns the CHIP benefit value for this member, applying additional insurance eligibility rules.
        """
        pe_value = self.get_member_variable(member.id)

        # If the member has any insurance, they are not eligible for CHIP
        # NOTE: all other eligibility logic (e.g age requirement) is built into the value returned from PE)
        if member.has_insurance_types(("none",)):
            return pe_value

        return 0
