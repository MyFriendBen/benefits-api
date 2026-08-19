from programs.framework.pe_base import (
    PolicyEngineMembersCalculator,
)
import programs.framework.pe_dependencies as dependency
from screener.models import HouseholdMember
from programs.programs.cross_white_label.medicaid.base import Medicaid
from programs.programs.cross_white_label.wic.base import Wic
from programs.programs.cross_white_label.ssi.base import Ssi
from programs.programs.cross_white_label.msp.base import Msp
from programs.programs.cross_white_label.head_start.base import HeadStart
from programs.programs.cross_white_label.early_head_start.base import EarlyHeadStart
from programs.programs.cross_white_label.csfp.base import CommoditySupplementalFoodProgram


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
