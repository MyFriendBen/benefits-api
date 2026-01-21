from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
from programs.co_county_zips import counties_from_screen
import programs.programs.messages as messages


class JeffcoStudentBenefits(ProgramCalculator):
    county = "Jefferson County"
    child_age_min = 3
    child_age_max = 19
    amount = 500
    dependencies = ["age", "county"]

    def household_eligible(self, e: Eligibility):
        # Location: must be in Jefferson County
        counties = counties_from_screen(self.screen)
        e.condition(JeffcoStudentBenefits.county in counties, messages.location())

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # Age: must be between 3 and 19
        e.condition(JeffcoStudentBenefits.child_age_min <= member.age <= JeffcoStudentBenefits.child_age_max)
