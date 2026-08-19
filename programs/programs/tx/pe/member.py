from programs.programs.federal.pe.member import (
    Wic,
    Ssi,
    CommoditySupplementalFoodProgram,
    HeadStart,
    EarlyHeadStart,
    Msp,
)
from programs.framework.pe_base import (
    PolicyEngineMembersCalculator,
)
import programs.framework.pe_dependencies as dependency
from screener.models import HouseholdMember
from programs.programs.cross_white_label.medicaid.base import Medicaid


class TxWic(Wic):
    """
    Texas WIC calculator that uses PolicyEngine's calculated benefit amounts
    instead of state-specific category amounts.
    """

    program_code = "tx_wic"

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

    program_code = "tx_ssi"

    pe_inputs = [
        *Ssi.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]


class TxCsfp(CommoditySupplementalFoodProgram):
    """
    Texas Commodity Supplemental Food Program (CSFP) calculator that uses PolicyEngine's calculations.
    Extends the federal CSFP calculator with Texas state code dependency.
    """

    program_code = "tx_csfp"

    pe_inputs = [
        *CommoditySupplementalFoodProgram.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]


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

    program_code = "tx_harris_rides"

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

    program_code = "tx_dart"

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


class TxHeadStart(HeadStart):
    """Texas Head Start (ages 3-5) — federal ``HeadStart`` PE calculator + TX state code."""

    program_code = "tx_head_start"

    pe_inputs = [
        *HeadStart.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]


class TxEarlyHeadStart(EarlyHeadStart):
    """Texas Early Head Start (birth-3 / pregnant) — federal ``EarlyHeadStart`` PE calculator + TX state code."""

    program_code = "tx_early_head_start"

    pe_inputs = [
        *EarlyHeadStart.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]


class TxMsp(Msp):
    """Texas Medicare Savings Program. Federal ``Msp`` plus the TX state code and the state's
    Medicaid inputs (see ``Msp`` for why the Medicaid inputs are required)."""

    program_code = "tx_medicare_savings_program"

    pe_inputs = [
        *Msp.pe_inputs,
        dependency.household.TxStateCodeDependency,
        *Medicaid.pe_inputs,
    ]
