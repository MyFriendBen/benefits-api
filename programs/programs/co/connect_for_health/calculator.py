from integrations.services.sheets.sheets import GoogleSheets
from django.core.cache import cache
from programs.co_county_zips import counties_from_screen
from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
from screener.models import HouseholdMember
from programs.programs.helpers import medicaid_eligible
import programs.programs.messages as messages

_CFH_CACHE_KEY = "cfh_county_values"
_CFH_CACHE_TIMEOUT = 60 * 60 * 24  # 1 day

_CFH_SHEET_ID = "1SuOhwX5psXsipMS_G5DE_f9jLS2qWxf6temxY445EQg"
_CFH_RANGE_NAME = "current report"
_CFH_AVERAGE_COLUMN = "Average Monthly Premium Tax Credit"
_CFH_COUNTY_COLUMN = "County\n(source here)"


def _get_cfh_county_values() -> dict:
    values = cache.get(_CFH_CACHE_KEY)
    if values is not None:
        return values

    data = GoogleSheets(_CFH_SHEET_ID, _CFH_RANGE_NAME).data_by_column(_CFH_COUNTY_COLUMN, _CFH_AVERAGE_COLUMN)
    values = {}
    for row in data:
        try:
            county_key = row[_CFH_COUNTY_COLUMN].strip() + " County"
            premium_value = float(row[_CFH_AVERAGE_COLUMN])
            values[county_key] = premium_value
        except (KeyError, ValueError, AttributeError):
            continue  # Skip malformed rows

    if not values:
        # Don't cache an empty result — retry on the next request instead of
        # locking every Connect for Health screening out for 24 hours.
        return values

    cache.set(_CFH_CACHE_KEY, values, timeout=_CFH_CACHE_TIMEOUT)
    return values


class ConnectForHealth(ProgramCalculator):
    percent_of_fpl = 4
    dependencies = ["insurance", "income_amount", "income_frequency", "zipcode", "household_size"]
    eligible_insurance_types = ["none", "private"]
    ineligible_insurance_types = ["va"]

    def household_eligible(self, e: Eligibility):
        # Medicade eligibility
        e.condition(not medicaid_eligible(self.data), messages.must_not_have_benefit("Medicaid"))

        # Income
        fpl = self.program.year.as_dict()
        income_band = int(fpl[self.screen.household_size] * ConnectForHealth.percent_of_fpl)
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"], exclude=["cashAssistance"]))
        e.condition(gross_income < income_band, messages.income(gross_income, income_band))

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # not CHP+ eligible
        chp = self.data.get("chp")
        if chp is not None:
            for member_eligibility in chp.eligible_members:
                if member_eligibility.member.id == member.id:
                    e.condition(not member_eligibility.eligible)

        # no or private insurance
        e.condition(member.insurance.has_insurance_types(ConnectForHealth.eligible_insurance_types))

        # no va insurance
        e.condition(not member.insurance.has_insurance_types(ConnectForHealth.ineligible_insurance_types))

    def member_value(self, member: HouseholdMember):
        values = _get_cfh_county_values()
        county = counties_from_screen(self.screen)[0]
        return int(values.get(county, 0) * 12)
