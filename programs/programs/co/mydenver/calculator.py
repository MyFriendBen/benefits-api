from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
from programs.co_county_zips import counties_from_screen
import programs.programs.messages as messages


class MyDenver(ProgramCalculator):
    eligible_counties = ["Denver County"]
    child_age_min = 5
    child_age_max = 18
    member_amount = 150
    dependencies = ["age", "zipcode"]

    def household_eligible(self, e: Eligibility) -> None:
        # location
        county_eligible = False

        counties = counties_from_screen(self.screen)
        for county in counties:
            if county in MyDenver.eligible_counties:
                county_eligible = True
        e.condition(county_eligible, messages.location())

    def member_eligible(self, e: MemberEligibility) -> None:
        if e.member.age is None:
            return
        member = e.member

        # age
        e.condition(MyDenver.child_age_min <= member.age <= MyDenver.child_age_max)
