from django.core.cache import cache
from integrations.services.sheets.sheets import GoogleSheets
from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
import programs.programs.messages as messages
from programs.co_county_zips import counties_from_screen


class CoHeadStartCountyEligibleCache:
    CACHE_KEY = "co_head_start_data"
    CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours
    sheet_id = "1suOcBpJPJGIXHljypNSCxGDWEvydG-t8erh2rzUtWcE"
    range_name = "HEAD START COUNTIES FOR MFB!A2:B"

    def _process(self):
        data = GoogleSheets(self.sheet_id, self.range_name).data()

        result = {}
        for row in data:
            if len(row) < 2:
                continue
            try:
                county_key = row[0].strip() + " County"
                is_eligible = row[1] == "TRUE"
                result[county_key] = is_eligible
            except (IndexError, AttributeError):
                continue  # Skip malformed rows

        return result

    def _get_data(self) -> dict:
        data = cache.get(self.CACHE_KEY)
        if data is not None:
            return data
        data = self._process()
        cache.set(self.CACHE_KEY, data, timeout=self.CACHE_TIMEOUT)
        return data


class CoHeadStart(ProgramCalculator):
    member_amount = 10655
    max_age = 5
    min_age = 3
    counties = CoHeadStartCountyEligibleCache()
    adams_percent_of_fpl = 1.3  # Adams County uses 130% FPL instead of 100% FPL
    adams_county = "Adams County"
    dependencies = ["age", "household_size", "income_frequency", "income_amount", "zipcode"]

    def household_eligible(self, e: Eligibility):
        # location
        counties = counties_from_screen(self.screen)

        in_eligible_county = False
        eligible_counties = CoHeadStart.counties._get_data()
        for county in counties:
            if county in eligible_counties:
                in_eligible_county = eligible_counties[county]
                break

        e.condition(in_eligible_county, messages.location())

        # income
        fpl = self.program.year.as_dict()
        income_limit = int(fpl[self.screen.household_size] / 12)
        income_limit_adams_county = int(fpl[self.screen.household_size] / 12 * CoHeadStart.adams_percent_of_fpl)
        gross_income = int(self.screen.calc_gross_income("monthly", ["all"]))

        in_adams = CoHeadStart.adams_county in counties
        if in_adams:
            e.condition(
                gross_income < income_limit_adams_county, messages.income(gross_income, income_limit_adams_county)
            )
        else:
            e.condition(gross_income < income_limit, messages.income(gross_income, income_limit))

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # age
        e.condition(CoHeadStart.min_age <= member.age <= CoHeadStart.max_age)
