from programs.programs.il.bap.calculator import IlBenefitAccess
from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility
from programs.programs.mixins import IlTransportationMixin


class IlTransitReducedFare(IlTransportationMixin, ProgramCalculator):
    dependencies = IlTransportationMixin.dependencies + ["county"]
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

        presumptive_eligible = self.check_presumptive_eligibility()

        household_size = self.screen.household_size
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))
        bap_income_limit = IlBenefitAccess.income_limit_by_household_size[min(household_size, 3)]
        income_eligible = gross_income > bap_income_limit

        county = self.screen.county
        county_eligible = county in self.eligible_counties

        e.condition(county_eligible and (presumptive_eligible or income_eligible))

    def member_eligible(self, e: MemberEligibility):
        member = e.member
        county = self.screen.county

        age_eligible = member.age >= self.minimum_age_by_county.get(county, self.minimum_age)

        has_minimum_age_with_disability = member.age >= self.minimum_age_with_disability
        has_eligible_disability = member.visually_impaired or member.disabled
        disability_eligible = has_minimum_age_with_disability and has_eligible_disability

        e.condition(age_eligible or disability_eligible)
