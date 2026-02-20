from integrations.clients.hud_income_limits import hud_client, HudIncomeClientError
from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility
import programs.programs.messages as messages


class MaCpp(ProgramCalculator):
    """
    Cambridge Preschool Program (CPP)

    Provides free, high-quality preschool for Cambridge children age 3–4, run by
    Cambridge Public Schools, the City of Cambridge, and local childcare providers.
    Families apply once and are matched to available spots based on eligibility
    and family preferences.

    Eligibility:
    - Cambridge resident (screen.county == "Cambridge")
    - Child age 3 or 4
    - For 3-year-olds: household income ≤65% Area Median Income (AMI)
      (approximated as 60% MTSP — nearest HUD MTSP tier below 65%;
      exact dollar thresholds should be verified against the annual CPP income guidelines)
    - For 4-year-olds: no income restriction

    Data gaps:
    - Lottery/waitlist selection cannot be verified (warning message added)
    - Birthday cutoff (Aug 31) cannot be checked; age stored as integer

    Source: https://earlychildhoodcambridge.org/cpp/
    """

    amount = 1  # Value varies (free tuition); frontend displays "Varies"
    eligible_city = "Cambridge"
    hud_county = "Middlesex"  # Cambridge is in Middlesex County, MA
    max_ami_percent = "60%"  # HUD API doesn't support 65% AMI; using 60% MTSP as a conservative approximation
    min_child_age = 3
    max_child_age = 4
    dependencies = ["income_amount", "income_frequency", "household_size", "county"]

    def household_eligible(self, e: Eligibility):
        # Exclude households already enrolled in CPP
        e.condition(not self.screen.has_benefit("ma_cpp"))

        # Cambridge residency required
        # Note: MA stores city name in county field (see MFB-548)
        is_cambridge = self.screen.county == self.eligible_city
        e.condition(is_cambridge, messages.location())

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # Child must be age 3 or 4
        is_preschool_age = self.min_child_age <= member.age <= self.max_child_age
        e.condition(is_preschool_age)

        # 3-year-olds have an income restriction (≤65% AMI, approximated as 60% MTSP).
        # 4-year-olds have no income restriction.
        if member.age == 3:
            try:
                income = self.screen.calc_gross_income("yearly", ["all"])
                income_limit = hud_client.get_screen_mtsp_ami(
                    self.screen,
                    self.max_ami_percent,
                    self.program.year.period,
                    county_override=self.hud_county,
                )
                e.condition(income <= income_limit)
            except HudIncomeClientError:
                e.condition(False)
