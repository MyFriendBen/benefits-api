from datetime import date

from integrations.clients.hud_income_limits import HudIncomeClientError, hud_client
from programs.co_county_zips import counties_from_screen
from programs.framework.base import Eligibility, ProgramCalculator
import programs.framework.eligibility_messages as messages
from screener.models import HouseholdMember
from sentry_sdk import capture_exception


class NurturingFutures(ProgramCalculator):
    """
    Nurturing Futures (Boulder County, CO)

    A guaranteed-income program: Boulder County pays eligible families with a young child a
    flat monthly amount they can spend on anything. Payments are administered by AidKit.

    Eligibility:
    - Lives in Boulder County
    - Head of household is 18 or older
    - A child born on or after Nov. 3, 2022. The screener stores a birth month, not a day,
      so every November 2022 birth passes; the program description states the exact date.
    - Gross household income, every type counted, at or below 30% of Boulder County AMI —
      unless someone already reports Nurturing Futures income. Returning participants
      reapply with no income limit. Health First Colorado or Colorado Works enrollment only
      verifies income for the county; it does not waive the limit.

    The county's published limits are HUD's MTSP 30% figures for the Boulder MSA, so they
    are read from HUD rather than kept here. If HUD is unavailable the program is hidden and
    the failure is reported, never compared against a zero limit.

    Value: $600/month per household from January 2027.

    References:
    - https://bouldercounty.gov/families/financial/nurturing-futures/
    """

    program_code = "co_nf"
    county = "Boulder County"
    head_min_age = 18
    earliest_child_birth_month = date(2022, 11, 1)
    ami_percent = "30%"
    ami_year = 2026
    participant_income_type = "nurturingFutures"
    amount = 600 * 12
    dependencies = ["zipcode", "household_size", "income_type", "income_amount", "income_frequency"]

    def household_eligible(self, e: Eligibility) -> None:
        counties = counties_from_screen(self.screen)
        e.condition(NurturingFutures.county in counties, messages.location())

        head_age = self.screen.get_head().calc_age()
        e.condition(head_age is not None and head_age >= NurturingFutures.head_min_age)

        e.condition(any(self._is_qualifying_child(member) for member in self.screen.household_members.all()))

        if self._is_returning_participant():
            return

        try:
            income_limit = hud_client.get_screen_mtsp_ami(
                self.screen, NurturingFutures.ami_percent, NurturingFutures.ami_year, county_override=self.county
            )
        except HudIncomeClientError as error:
            capture_exception(error)
            e.condition(False, messages.income_limit_unknown())
            return

        income = self.screen.calc_gross_income("yearly", ["all"])
        e.condition(income <= income_limit, messages.income(income, income_limit))

    def _is_qualifying_child(self, member: HouseholdMember) -> bool:
        birth = member.birth_year_month
        return birth is not None and birth >= NurturingFutures.earliest_child_birth_month

    def _is_returning_participant(self) -> bool:
        return self.screen.income_streams.filter(type=NurturingFutures.participant_income_type).exists()
