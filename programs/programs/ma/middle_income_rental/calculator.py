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
    - Head of household must be at least 18 years old
    - Household gross income between 80% and 120% AMI (MTSP)
      - Section 8 / housing voucher holders are exempt from the 80% floor
    - Liquid assets at or below $75,000
      - Households where all members are 62+ or all members are disabled: $150,000

    Sources:
    - https://www.cambridgema.gov/CDD/housing/forapplicants/middleincomerentalprogram
    - https://www.cambridgema.gov/-/media/Files/CDD/Housing/ForApplicants/hsg_mid_inc_app.pdf
    - https://www.cambridgema.gov/~/media/Files/CDD/Housing/incomelimits/hudincomeguidelines.ashx
    """

    # Cambridge is a city in Middlesex County - used for HUD AMI lookups
    eligible_city = "Cambridge"
    hud_county = "Middlesex"
    min_ami_percent = 0.80
    max_ami_percent = 1.20
    ami_year = 2025
    amount = 1
    asset_limit = 75_000
    senior_asset_limit = 150_000
    min_head_age = 18
    ami_max_multiplier = 1.5  # 120% AMI = 80% AMI x 1.5
    dependencies = ["zipcode", "income_amount", "income_frequency", "household_size", "household_assets"]

    def household_eligible(self, e: Eligibility) -> None:
        # Check if user already has this benefit
        e.condition(not self.screen.has_benefit("ma_middle_income_rental"))

        # Location check - must be Cambridge resident
        is_cambridge = self.screen.county == self.eligible_city
        e.condition(is_cambridge, messages.location())

        # Head of household must be at least 18
        head = self.screen.get_head()
        head_age = head.age
        e.condition(head_age is not None and head_age >= self.min_head_age, messages.older_than(self.min_head_age))

        # Asset limit - seniors (all 62+) or all-disabled households get $150,000; otherwise $75,000
        members = self.screen.household_members.all()
        all_senior = all(m.age is not None and m.age >= 62 for m in members)
        all_disabled = all(m.has_disability() for m in members)
        limit = self.senior_asset_limit if (all_senior or all_disabled) else self.asset_limit
        e.condition(self.screen.household_assets <= limit, messages.assets(limit))

        # Income eligibility - 80% to 120% AMI (MTSP)
        # Section 8 / housing voucher holders are exempt from the 80% floor.
        try:
            ami_min = hud_client.get_screen_mtsp_ami(self.screen, "80%", self.ami_year, county_override=self.hud_county)
            # HUD API doesn't provide 120% directly; estimate from 80% AMI
            ami_max = ami_min * self.ami_max_multiplier
            gross_income = self.screen.calc_gross_income("yearly", ["all"])
            # Minimum Income Limits do not apply to households who have tenant based or mobile housing vouchers
            if self.screen.has_section_8:
                income_eligible = gross_income <= ami_max
            else:
                income_eligible = ami_min <= gross_income <= ami_max
            e.condition(income_eligible, messages.income_range(gross_income, ami_min, ami_max))
        except HudIncomeClientError:
            e.condition(False, messages.income_limit_unknown())
