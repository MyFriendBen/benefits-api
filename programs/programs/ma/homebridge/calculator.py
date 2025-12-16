from programs.programs.calc import ProgramCalculator, Eligibility
import programs.programs.messages as messages
from integrations.clients.hud_income_limits import hud_client, HudIncomeClientError


class MaHomeBridge(ProgramCalculator):
    """
    Cambridge HomeBridge Program Calculator

    HomeBridge helps first-time homebuyers in Cambridge receive funding to cover
    a large portion of the purchase price in exchange for long-term affordability
    restrictions.

    Eligibility requirements that can be verified:
    - Cambridge residency (or works full-time in Cambridge - we check residency only)
    - Household income between 60% and 120% AMI

    Requirements that cannot be verified programmatically:
    - First-time homebuyer status
    - CHAPA-certified homebuyer class completion
    - Conventional, fixed-rate mortgage
    - Monthly housing costs between 25% and 33% of gross monthly income
    - Sufficient assets for down payment and closing costs
    - Liquid assets above $40,000 contributed to purchase
    """

    # Cambridge is a city in Middlesex County - used for HUD AMI lookups
    eligible_city = "Cambridge"
    hud_county = "Middlesex"
    min_ami_percent = 0.60
    max_ami_percent = 1.20
    ami_year = 2025
    amount = 1
    dependencies = ["zipcode", "income_amount", "income_frequency", "household_size"]

    def household_eligible(self, e: Eligibility):
        # Check if user already has this benefit
        e.condition(not self.screen.has_benefit("ma_homebridge"))

        # Location check - must be Cambridge resident
        is_cambridge = self.screen.county == self.eligible_city
        e.condition(is_cambridge, messages.location())

        # Income eligibility - 60% to 120% AMI
        try:
            ami_60 = hud_client.get_screen_mtsp_ami(
                self.screen, "60%", self.ami_year, county_override=self.hud_county
            )
            ami_100 = hud_client.get_screen_mtsp_ami(
                self.screen, "100%", self.ami_year, county_override=self.hud_county
            )
            ami_120 = ami_100 * self.max_ami_percent
            gross_income = self.screen.calc_gross_income("yearly", ["all"])
            income_eligible = ami_60 <= gross_income <= ami_120
            e.condition(income_eligible, messages.income(gross_income, ami_120))
        except HudIncomeClientError:
            e.condition(False, messages.income_limit_unknown())
