from programs.framework.base import MemberEligibility, ProgramCalculator, Eligibility
import programs.framework.eligibility_messages as messages
from programs.co_county_zips import counties_from_screen


class DenverPreschoolProgram(ProgramCalculator):
    member_amount = 594 * 12
    min_age = 3
    max_age = 4
    county = "Denver County"
    dependencies = ["age", "zipcode"]

    def household_eligible(self, e: Eligibility):
        # Lives in Denver
        counties = counties_from_screen(self.screen)
        e.condition(DenverPreschoolProgram.county in counties, messages.location())

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # age
        e.condition(DenverPreschoolProgram.min_age <= member.age <= DenverPreschoolProgram.max_age)
