from programs.framework.base import MemberEligibility, ProgramCalculator, Eligibility
import programs.framework.eligibility_messages as messages
from programs.co_county_zips import counties_from_screen


class MySpark(ProgramCalculator):
    program_code = "myspark"
    member_amount = 1_000
    max_age = 14
    min_age = 11
    county = "Denver County"
    dependencies = ["age", "zipcode"]

    def household_eligible(self, e: Eligibility):
        # Qualify for FRL
        e.condition(self.program_eligible("nslp"), messages.must_have_benefit("Free or Reduced Lunch"))

        counties = counties_from_screen(self.screen)

        # Denever County
        e.condition(MySpark.county in counties, messages.location())

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # age
        e.condition(MySpark.min_age <= member.age <= MySpark.max_age)
