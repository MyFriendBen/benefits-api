from programs.framework.base import MemberEligibility, ProgramCalculator, Eligibility
from programs.framework.helpers import medicaid_eligible
import programs.framework.eligibility_messages as messages
from integrations.services.sheets.cache import GoogleSheetsCache
from screener.models import HouseholdMember
from sentry_sdk import capture_message


class ACACache(GoogleSheetsCache):
    CACHE_KEY = "nc_aca_data"
    sheet_id = "1tk8zfO_Ou96UvGrIwZoI3Pv8TvPZZipg7YfzGMT2o3c"
    range_name = "'current report'!A2:B101"

    def _process(self, raw_data):
        result = {}
        for d in raw_data:
            if len(d) < 2:
                continue
            try:
                county_key = d[0].strip() + " County"
                premium_value = float(d[1].replace(",", ""))
                result[county_key] = premium_value
            except (IndexError, ValueError, AttributeError):
                continue  # Skip malformed rows
        return result


class ACASubsidiesNC(ProgramCalculator):
    percent_of_fpl = 4
    dependencies = ["insurance", "income_amount", "income_frequency", "county", "household_size"]
    eligible_insurance_types = ["none", "private"]
    ineligible_insurance_types = ["va"]
    county_values = ACACache()

    def household_eligible(self, e: Eligibility):
        # Medicade eligibility
        e.condition(not medicaid_eligible(self.data), messages.must_not_have_benefit("Medicaid"))

        # Income
        fpl = self.program.year.as_dict()
        income_band = int(fpl[self.screen.household_size] * ACASubsidiesNC.percent_of_fpl)
        gross_income = int(self.screen.calc_gross_income("yearly", ("all",)))
        e.condition(gross_income < income_band, messages.income(gross_income, income_band))

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # no or private insurance
        e.condition(member.insurance.has_insurance_types(ACASubsidiesNC.eligible_insurance_types))

        # no va insurance
        e.condition(not member.insurance.has_insurance_types(ACASubsidiesNC.ineligible_insurance_types))

    def member_value(self, member: HouseholdMember):
        values = self.county_values.get_data()
        county = self.screen.county
        if county not in values:
            # A $0 value is filtered out by the frontend's `value > 0` check, so the
            # program silently vanishes from results rather than erroring. Report it,
            # otherwise a renamed county or an empty sheet fetch is undetectable.
            capture_message(
                f"ACASubsidiesNC: no premium value for county {county!r} of {len(values)} cached",
                level="warning",
            )
            return 0
        return values[county] * 12
