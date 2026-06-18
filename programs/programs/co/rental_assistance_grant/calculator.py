from programs.programs.calc import ProgramCalculator, Eligibility
import programs.programs.messages as messages
from programs.co_county_zips import counties_from_screen
from integrations.services.sheets.sheets import GoogleSheets
from django.core.cache import cache
import math


class RAGCache:
    CACHE_KEY = "rag_income_limits_data"
    CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours

    sheet_id = "1DntpIXZfUY2yTy1_rAhaGLUH4PUAfpTSAn-j2tf2tts"
    range_name = "'2023 80% AMI'!A2:I65"

    def _get_data(self) -> dict:
        data = cache.get(self.CACHE_KEY)
        if data is not None:
            return data
        data = self._process()
        cache.set(self.CACHE_KEY, data, timeout=self.CACHE_TIMEOUT)
        return data

    def _process(self):
        data = GoogleSheets(self.sheet_id, self.range_name).data()

        result = {}
        for d in data:
            if len(d) < 2:
                continue
            try:
                county_key = d[0].strip() + " County"
                income_values = []
                for v in d[1:]:
                    try:
                        income_values.append(int(v.replace(",", "")))
                    except (ValueError, AttributeError):
                        income_values.append(0)  # Default for malformed values
                result[county_key] = income_values
            except (IndexError, AttributeError):
                continue  # Skip malformed rows
        return result


class RentalAssistanceGrant(ProgramCalculator):
    amount = 10_000
    dependencies = ["income_amount", "income_frequency", "household_size", "zipcode"]
    income_limits = RAGCache()

    def household_eligible(self, e: Eligibility):
        # income
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))

        limits = self.income_limits._get_data()

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
