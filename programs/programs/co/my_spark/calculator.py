from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
import programs.programs.messages as messages
from programs.co_county_zips import counties_from_screen


class MySpark(ProgramCalculator):
    member_amount = 1_000
    max_age = 14
    min_age = 11
    county = "Denver County"
    dependencies = ["age", "zipcode"]

    def household_eligible(self, e: Eligibility) -> None:
        # Qualify for FRL
        nslp = self.data.get("nslp")
        is_frl_eligible = nslp is not None and nslp.eligible
        e.condition(is_frl_eligible, messages.must_have_benefit("Free or Reduced Lunch"))

        counties = counties_from_screen(self.screen)

        # Denever County
        e.condition(MySpark.county in counties, messages.location())

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member
        if member.age is None:
            return

        # age
        e.condition(MySpark.min_age <= member.age <= MySpark.max_age)
