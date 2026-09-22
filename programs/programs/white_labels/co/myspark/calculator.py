from programs.framework.base import MemberEligibility, ProgramCalculator, Eligibility
import programs.framework.eligibility_messages as messages
from programs.co_county_zips import counties_from_screen


class MySpark(ProgramCalculator):
    program_code = "myspark"
    # PolicyEngine-backed, and not restateable as an income test. `nslp` is PE's
    # `school_meal_net_subsidy`, whose tier honors `meets_school_meal_categorical_eligibility`
    # (SNAP/TANF households keep free meals at any income), derives `is_in_k12_school`
    # internally from age, and frees a whole SPM unit on one foster child. "Qualifies for
    # free or reduced lunch" has no equivalent condition on this household's own facts.
    gates_on = ("nslp",)
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
