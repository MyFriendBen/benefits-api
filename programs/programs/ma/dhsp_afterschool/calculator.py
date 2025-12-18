from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility
import programs.programs.messages as messages


class MaDhspAfterschool(ProgramCalculator):
    """
    Cambridge DHSP Afterschool Programs Lottery Calculator

    DHSP Afterschool provides affordable afterschool care and enrichment for
    Cambridge children in grades K-8, with tuition based on what families can afford
    via a sliding scale based on household size and income.

    Eligibility requirements that can be verified:
    - Cambridge residency
    - Has children in K-8 age range (approximately ages 5-14)

    Requirements that cannot be verified programmatically:
    - Lottery selection (application does not guarantee a slot)
    - Specific program availability by school/site

    Note: Tuition is on a sliding scale based on household size and income.
    Some programs are free for eligible grades (e.g., free tuition for 6-8th graders
    enrolled in CYP afterschool).

    Source: https://www.finditcambridge.org/programs/dhsp-afterschool-programs-lottery
    """

    eligible_city = "Cambridge"
    # K-8 typically covers ages 5-14 (Kindergarten through 8th grade)
    min_child_age = 5
    max_child_age = 14
    # Using an estimated average annual benefit amount based on market afterschool cost – sliding-scale tuition paid
    amount = 900 * 12
    dependencies = ["zipcode", "household_size"]

    def household_eligible(self, e: Eligibility):
        # Check if user already has this benefit
        e.condition(not self.screen.has_benefit("ma_dhsp_afterschool"))

        # Location check - must be Cambridge resident
        is_cambridge = self.screen.county == self.eligible_city
        e.condition(is_cambridge, messages.location())

    def member_eligible(self, e: MemberEligibility):
        member = e.member
        # Child must be in K-8 age range (approximately 5-14 years old)
        is_child_age = self.min_child_age <= member.age <= self.max_child_age
        e.condition(is_child_age)
