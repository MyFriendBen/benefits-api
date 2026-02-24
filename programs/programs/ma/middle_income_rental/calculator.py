from programs.programs.calc import ProgramCalculator, Eligibility
import programs.programs.messages as messages
from integrations.clients.hud_income_limits import hud_client, HudIncomeClientError


class MaMiddleIncomeRental(ProgramCalculator):
    """
    Cambridge Middle-Income Rental Program Calculator

    The Middle-Income housing pool provides opportunities for households to rent
    an income-restricted "middle-income" apartment in Cambridge through privately
    owned buildings, with rents set to be affordable based on income.

    Eligibility requirements that can be verified:
    - Cambridge residency
    - Household gross income between 80% and 120% AMI (MTSP)
    - Liquid assets at or below $100,000
    """

    # Cambridge is a city in Middlesex County - used for HUD AMI lookups
    eligible_city = "Cambridge"
    hud_county = "Middlesex"
    min_ami_percent = 0.80
    max_ami_percent = 1.20
    ami_year = 2025
    amount = 1
    asset_limit = 100_000
    dependencies = ["zipcode", "income_amount", "income_frequency", "household_size", "household_assets"]

    def household_eligible(self, e: Eligibility) -> None:
        # Check if user already has this benefit
        e.condition(not self.screen.has_benefit("ma_middle_income_rental"))

        # Location check - must be Cambridge resident
        is_cambridge = self.screen.county == self.eligible_city
        e.condition(is_cambridge, messages.location())

        # Asset limit - household liquid assets must not exceed $100,000
        e.condition(self.screen.household_assets <= self.asset_limit, messages.assets(self.asset_limit))

        # Income eligibility - 80% to 120% AMI (MTSP)
        try:
            min_ami_str = f"{int(self.min_ami_percent * 100)}%"
            ami_min = hud_client.get_screen_mtsp_ami(
                self.screen, min_ami_str, self.ami_year, county_override=self.hud_county
            )
            ami_100 = hud_client.get_screen_mtsp_ami(
                self.screen, "100%", self.ami_year, county_override=self.hud_county
            )
            # HUD MTSP API only provides up to 100% AMI; 120% is derived by multiplying 100% × 1.20
            ami_max = ami_100 * self.max_ami_percent
            gross_income = self.screen.calc_gross_income("yearly", ["all"])
            income_eligible = ami_min <= gross_income <= ami_max
            e.condition(income_eligible, messages.income(gross_income, ami_max))
        except HudIncomeClientError:
            e.condition(False, messages.income_limit_unknown())
