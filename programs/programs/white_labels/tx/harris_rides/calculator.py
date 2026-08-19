"""TxHarrisCountyRides."""

from programs.framework.pe_base import PolicyEngineMembersCalculator
import programs.framework.pe_dependencies as dependency


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
