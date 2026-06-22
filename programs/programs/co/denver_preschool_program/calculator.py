from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
import programs.programs.messages as messages
from programs.co_county_zips import counties_from_screen


class DenverPreschoolProgram(ProgramCalculator):
    member_amount = 594 * 12
    min_age = 3
    max_age = 4
    county = "Denver County"
    dependencies = ["age", "zipcode"]

    def household_eligible(self, e: Eligibility) -> None:
        # Lives in Denver
        counties = counties_from_screen(self.screen)
        e.condition(DenverPreschoolProgram.county in counties, messages.location())

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member

        if member.age is None:
            return

        # age
        e.condition(DenverPreschoolProgram.min_age <= member.age <= DenverPreschoolProgram.max_age)
