from programs.programs.federal.pe.member import (
    Wic,
    Ssi,
    Medicaid,
    CommoditySupplementalFoodProgram,
)
from programs.programs.policyengine.calculators.base import (
    PolicyEngineMembersCalculator,
)
import programs.programs.policyengine.calculators.dependencies as dependency
from screener.models import HouseholdMember


class TxWic(Wic):
    """
    Texas WIC calculator that uses PolicyEngine's calculated benefit amounts
    instead of state-specific category amounts.
    """

    pe_inputs = [
        *Wic.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]

    def member_value(self, member: HouseholdMember):
        """
        Returns the PolicyEngine-calculated WIC benefit amount for this member.
        Unlike the parent class, this doesn't use hardcoded category-based amounts.
        """
        return self.get_member_variable(member.id)


class TxSsi(Ssi):
    """
    Texas SSI calculator that uses PolicyEngine's calculated benefit amounts.
    Extends the federal SSI calculator with Texas state code dependency.
    """

    pe_inputs = [
        *Ssi.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]


class TxCsfp(CommoditySupplementalFoodProgram):
    """
    Texas Commodity Supplemental Food Program (CSFP) calculator that uses PolicyEngine's calculations.
    Extends the federal CSFP calculator with Texas state code dependency.
    """

    pe_inputs = [
        *CommoditySupplementalFoodProgram.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]


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
        pe_value = self.get_member_variable(member.id)
        return 1 if pe_value > 0 else 0


class TxChip(PolicyEngineMembersCalculator):
    """
    Texas CHIP calculator that uses PolicyEngine's calculated benefit amounts
    for TX-specific CHIP eligibility determination.
    Inherits from PolicyEngineMembersCalculator and uses the same inputs as the federal Chip calculator.
    """

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
    # results (see: benefits-be/programs/programs/co/pe/member.py#L74).
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
