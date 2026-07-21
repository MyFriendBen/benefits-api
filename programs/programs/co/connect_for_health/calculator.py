from integrations.services.sheets.sheets import GoogleSheets
from integrations.services.sheets.cache import GoogleSheetsCache
from programs.co_county_zips import counties_from_screen
from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
from screener.models import HouseholdMember
from programs.programs.helpers import medicaid_eligible
import programs.programs.messages as messages


class CfhCountyValuesCache(GoogleSheetsCache):
    CACHE_KEY = "cfh_county_values"
    sheet_id = "1SuOhwX5psXsipMS_G5DE_f9jLS2qWxf6temxY445EQg"
    range_name = "current report"
    _COUNTY_COLUMN = "County\n(source here)"
    _AVERAGE_COLUMN = "Average Monthly Premium Tax Credit"

    def _fetch_raw(self):
        return GoogleSheets(self.sheet_id, self.range_name).data_by_column(self._COUNTY_COLUMN, self._AVERAGE_COLUMN)

    def _process(self, raw_data):
        values = {}
        for row in raw_data:
            try:
                county_key = row[self._COUNTY_COLUMN].strip() + " County"
                premium_value = float(row[self._AVERAGE_COLUMN])
                values[county_key] = premium_value
            except (KeyError, ValueError, AttributeError):
                continue  # Skip malformed rows
        return values


class ConnectForHealth(ProgramCalculator):
    percent_of_fpl = 4
    dependencies = ["insurance", "income_amount", "income_frequency", "zipcode", "household_size"]
    eligible_insurance_types = ["none", "private"]
    ineligible_insurance_types = ["va"]
    county_values = CfhCountyValuesCache()

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
        values = self.county_values.get_data()
        county = counties_from_screen(self.screen)[0]
        return int(values.get(county, 0) * 12)
