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

    def _get_data(self) -> dict:
        data = cache.get(self.CACHE_KEY)
        if data is not None:
            return data
        data = self._process()
        cache.set(self.CACHE_KEY, data, timeout=self.CACHE_TIMEOUT)
        return data

    def _process(self):
        data = GoogleSheets(self.sheet_id, self.range_name).data()

        return [int(a.replace(",", "").replace("$", "")) for a in data[0]]


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
