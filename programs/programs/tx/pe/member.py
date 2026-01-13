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
            if member.has_benefit("medicaid"):
                return True

            # Check if child qualifies for Medicaid (PE value > 0)
            child_medicaid_value = self.get_member_dependency_value(dependency.member.Medicaid, member.id)
            if child_medicaid_value > 0:
                return True

        return False


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
        # Must not have other health insurance
        if not member.has_insurance_types(("none",)):
            return 0

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


class TxHarrisCountyRides(PolicyEngineMembersCalculator):
    """
    Texas Harris County RIDES program calculator.

    Provides discounted rides on public transit for individuals who are 65 or older
    or have a disability and are unable to access METRO services.

    The pe_name is "tx_harris_rides_eligible" which returns a boolean from PolicyEngine.
    When eligible, we return 1 to indicate eligibility (the actual value will be
    overridden to "Varies" in the admin console).

    PolicyEngine handles all eligibility requirements
    """

    pe_name = "tx_harris_rides_eligible"
    pe_outputs = [dependency.member.TxHarrisRidesEligible]
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.IsDisabledDependency,
        dependency.member.IsBlindDependency,
        dependency.household.TxStateCodeDependency,
        dependency.household.TxCountyDependency,
    ]
    dependencies = ["county"]

    def member_value(self, member):
        # Check if household already has the benefit
        if self.screen.has_benefit("tx_harris_rides"):
            return 0

        pe_eligible = self.get_member_variable(member.id)

        return 1 if pe_eligible else 0


class TxDart(PolicyEngineMembersCalculator):
    """
    Texas Dallas Area Rapid Transit (DART) reduced fare program calculator.

    DART provides transit benefits to Dallas area residents:
    - Free Ride: Children under 5 ride free
    - Reduced Fare available to:
      - Seniors (65+) or children ages 5-14
      - Disabled individuals
      - Veterans
      - Full-time students
      - People enrolled in qualifying programs (SNAP, Medicaid, Medicare, CHIP, WIC, TANF)

    PolicyEngine returns the maximum of free ride and reduced fare benefits.

    Reference: https://www.dart.org/fare/general-fares-and-overview/reduced-fares
    """

    pe_name = "tx_dart_benefit_person"
    pe_inputs = [
        # Core demographics
        dependency.member.AgeDependency,
        dependency.member.IsDisabledDependency,
        dependency.member.IsVeteranDependency,
        dependency.member.FullTimeCollegeStudentDependency,
        # TX state code for state-specific calculations
        dependency.household.TxStateCodeDependency,
        # Income dependencies for program eligibility calculations
        *Medicaid.pe_inputs,
    ]
    pe_outputs = [dependency.member.TxDartBenefitPerson]

    def member_value(self, member: HouseholdMember):
        """
        Returns the DART benefit value for this member.

        PolicyEngine handles all eligibility logic including:
        - Age-based eligibility (free for under 5, reduced for 5-14 or 65+)
        - Disability status
        - Veteran status
        - Student status
        - Enrollment in qualifying assistance programs

        We return the PolicyEngine-calculated value directly.
        """
        return self.get_member_variable(member.id)


class TxFpp(PolicyEngineMembersCalculator):
    """
    Texas Family Planning Program (FPP) calculator using PolicyEngine.

    This program provides family planning benefits to help individuals choose when to become
    a parent. Services may include birth control, pregnancy testing, and health care screenings.

    Eligibility requirements (handled by PolicyEngine):
    - Age eligibility (64 or younger per tx_fpp_age_eligible)
    - Income at or below 250% of Federal Poverty Level (per tx_fpp_income_eligible)

    Additional eligibility requirements (handled in member_value):
    - Must not have other health insurance (program is for those who earn too much for Medicaid)
    """

    pe_name = "tx_fpp_benefit"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.household.TxStateCodeDependency,
    ]
    pe_outputs = [dependency.member.TxFpp]

    def member_value(self, member: HouseholdMember):
        """
        Returns the FPP benefit value for this member.

        PolicyEngine calculates age and income eligibility. We additionally check
        that the member does not have other health insurance, as FPP is designed
        for those who earn too much for regular Medicaid benefits.
        """
        # Must not have other health insurance (FPP is for those without Medicaid coverage)
        if not member.has_insurance_types(("none",)):
            return 0

        # Return PolicyEngine-calculated value (handles age and income eligibility)
        return self.get_member_variable(member.id)
