from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility
from programs.programs.mixins import IlTransportationMixin


class IlTransitReducedFare(IlTransportationMixin, ProgramCalculator):
    dependencies = ["age", "visually_impaired", "disabled", "county"]
    eligible_counties = [
        "Cook",
        "DeKalb",
        "DuPage",
        "Jackson",
        "Kane",
        "Lake",
        "Madison",
        "McHenry",
        "Peoria",
        "Rock Island",
        "Sangamon",
        "Will",
    ]
    minimum_age_by_county = {
        "Rock Island": 60,
    }

    def household_eligible(self, e: Eligibility):
        e.condition(not self.screen.has_benefit("il_transit_reduced_fare"))

        # Note: SSI/SSDI presumptive eligibility is not checked here because
        # there are currently no eligibility requirements to bypass. County eligibility is the
        # only household-level requirement. Medicare eligibility is checked
        # at the member level instead.

        e.condition(self.screen.county in self.eligible_counties)

    def member_eligible(self, e: MemberEligibility):
        member = e.member
        county = self.screen.county

        age_eligible = member.age >= self.minimum_age_by_county.get(county, self.minimum_age)

        has_minimum_age_with_disability = member.age >= self.minimum_age_with_disability
        has_eligible_disability = member.visually_impaired or member.disabled
        disability_eligible = has_minimum_age_with_disability and has_eligible_disability

        # Check for Medicare as presumptive eligibility
        has_medicare = member.insurance.has_insurance_types(["medicare"])

        # Member is eligible if they have Medicare OR meet age/disability requirements
        e.condition(has_medicare or age_eligible or disability_eligible)
