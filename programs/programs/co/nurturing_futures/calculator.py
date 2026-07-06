from integrations.services.sheets.sheets import GoogleSheets
from django.core.cache import cache
from programs.co_county_zips import counties_from_screen
from programs.programs.calc import Eligibility, ProgramCalculator
import programs.programs.messages as messages


class BoulderAmiCache:
    sheet_id = "1PRpQ76Xa9Ru0U9MiwgYY5Yfl923lFz4Uu8a4g6A5N6Q"
    range_name = "AMI!B2:I2"
    CACHE_KEY = "boulder_ami_data"
    CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours
    DEFAULT_AMI_LIMITS = [0] * 8  # one per household size 1-8, matches the sheet's column count

    def _get_data(self) -> dict:
        data = cache.get(self.CACHE_KEY)
        if data is not None:
            return data
        data = self._process()
        if not data:
            # Don't cache an empty result — retry on the next request instead of
            # locking every NurturingFutures screening out for 24 hours.
            return self.DEFAULT_AMI_LIMITS
        cache.set(self.CACHE_KEY, data, timeout=self.CACHE_TIMEOUT)
        return data

    def _process(self):
        data = GoogleSheets(self.sheet_id, self.range_name).data()

        if not data or len(data) == 0:
            return []

        result = []
        for a in data[0]:
            try:
                cleaned_value = a.replace(",", "").replace("$", "")
                result.append(int(cleaned_value))
            except (ValueError, AttributeError):
                result.append(0)  # Use 0 as default for malformed values
        return result


class NurturingFutures(ProgramCalculator):
    county = "Boulder County"
    head_min_age = 18
    child_max_age = 3
    ami = BoulderAmiCache()
    ami_percent = 0.3
    amount = 3_600

    def household_eligible(self, e: Eligibility):
        # location
        counties = counties_from_screen(self.screen)
        e.condition(NurturingFutures.county in counties, messages.location())

        # head is 18+
        e.condition(self.screen.get_head().age >= NurturingFutures.head_min_age)

        # has child 3 or younger
        e.condition(self.screen.num_children(age_max=NurturingFutures.child_max_age))

        # income
        income_limit = NurturingFutures.ami._get_data()[self.screen.household_size - 1] * NurturingFutures.ami_percent
        income = self.screen.calc_gross_income("yearly", ["all"])
        e.condition(income <= income_limit, messages.income(income, income_limit))
