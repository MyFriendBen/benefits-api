from integrations.clients.hud_income_limits import hud_client, HudIncomeClientError
from programs.programs.calc import Eligibility, ProgramCalculator
import programs.programs.messages as messages


class Cha(ProgramCalculator):
    """
    Cambridge Housing Authority (CHA) - Housing and Rental Assistance

    CHA administers rental housing and rental assistance for families in need.
    Depending on meeting family and income standards, households can receive
    rental vouchers or locations.

    Eligibility:
    - Income: ≤80% AMI for public housing, ≤50% AMI for vouchers/SRO
    - Must be a U.S. citizen or eligible immigrant
    - Must be able to pass background check
    - Cambridge resident/work preferences may apply for waitlist ordering

    Value: Voucher holders typically pay about 30% of income toward rent,
    with subsidy covering the rest up to a cap.
    """

    # Value is highly variable (depends on income, rent, waitlist status)
    # Return 1 to indicate eligibility; frontend displays "Varies"
    amount = 1
    eligible_city = "Cambridge"
    # Cambridge is a city in Middlesex County - used for HUD AMI lookups
    hud_county = "Middlesex"
    # Use 50% AMI as primary threshold (vouchers are more common than public housing)
    ami_percent = "50%"
    dependencies = ["income_amount", "income_frequency", "household_size", "county"]

    def household_eligible(self, e: Eligibility):
        # Location: Must be in Cambridge
        # (Note: currently, our MA implementation stores city name in 'county' field, see MFB-548 for details)
        is_cambridge = self.screen.county == self.eligible_city
        e.condition(is_cambridge, messages.location())

        # Income test: ≤50% AMI for vouchers (most common program)
        # Using Standard Section 8 Income Limits (appropriate for housing vouchers)
        try:
            income = self.screen.calc_gross_income("yearly", ["all"])
            income_limit = hud_client.get_screen_il_ami(
                self.screen, self.ami_percent, self.program.year.period, county_override=self.hud_county
            )
            e.condition(income <= income_limit, messages.income(income, income_limit))
        except HudIncomeClientError:
            e.condition(False, messages.income_limit_unknown())
