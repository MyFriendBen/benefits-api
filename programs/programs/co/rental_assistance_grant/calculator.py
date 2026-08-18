from programs.framework.base import ProgramCalculator, Eligibility
import programs.framework.eligibility_messages as messages
from programs.co_county_zips import counties_from_screen
from integrations.services.sheets.cache import GoogleSheetsCache
from sentry_sdk import capture_message
import math


class RAGCache(GoogleSheetsCache):
    CACHE_KEY = "rag_income_limits_data"
    sheet_id = "1DntpIXZfUY2yTy1_rAhaGLUH4PUAfpTSAn-j2tf2tts"
    range_name = "'2023 80% AMI'!A2:I65"

    def _process(self, raw_data):
        result = {}
        all_zero_counties = []
        for d in raw_data:
            if len(d) < 2:
                continue
            try:
                county_key = d[0].strip() + " County"
                income_values = []
                for v in d[1:]:
                    try:
                        income_values.append(int(v.replace(",", "")))
                    except (ValueError, AttributeError):
                        income_values.append(0)
                if not any(income_values):
                    # A limit of 0 makes every income check fail, so the program
                    # silently disappears for that county rather than erroring.
                    all_zero_counties.append(county_key)
                result[county_key] = income_values
            except (IndexError, AttributeError):
                continue

        if all_zero_counties:
            capture_message(
                f"RAGCache: all income limits parsed as 0 for {len(all_zero_counties)} "
                f"county/counties: {all_zero_counties!r}",
                level="warning",
            )

        return result


class RentalAssistanceGrant(ProgramCalculator):
    name_abbreviated = "rag"
    amount = 10_000
    dependencies = ["income_amount", "income_frequency", "household_size", "zipcode"]
    income_limits = RAGCache()

    def household_eligible(self, e: Eligibility):
        # income
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))

        limits = self.income_limits.get_data()

        counties = counties_from_screen(self.screen)
        county_name = counties[0]

        for county in counties:
            if county in limits:
                county_name = county
                break

        if county_name in limits:
            income_limit = limits[county_name][self.screen.household_size - 1]
        else:
            income_limit = -math.inf

        e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))
