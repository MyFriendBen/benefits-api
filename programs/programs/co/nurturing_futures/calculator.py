from integrations.services.sheets.cache import GoogleSheetsCache
from programs.co_county_zips import counties_from_screen
from programs.framework.base import Eligibility, ProgramCalculator
import programs.framework.eligibility_messages as messages
from sentry_sdk import capture_message


class BoulderAmiCache(GoogleSheetsCache):
    sheet_id = "1PRpQ76Xa9Ru0U9MiwgYY5Yfl923lFz4Uu8a4g6A5N6Q"
    range_name = "AMI!B2:I2"
    CACHE_KEY = "boulder_ami_data"
    DEFAULT_AMI_LIMITS = [0] * 8  # one per household size 1-8, matches the sheet's column count

    def _empty_fallback(self):
        # NurturingFutures indexes this list positionally by household size,
        # so the fallback must be a same-shaped list, not the base class's {}.
        return self.DEFAULT_AMI_LIMITS

    def _process(self, raw_data):
        if not raw_data or len(raw_data) == 0:
            return []

        result = []
        malformed = []
        for a in raw_data[0]:
            try:
                cleaned_value = a.replace(",", "").replace("$", "")
                result.append(int(cleaned_value))
            except (ValueError, AttributeError):
                malformed.append(a)
                result.append(0)  # Use 0 as default for malformed values

        if malformed:
            capture_message(
                f"BoulderAmiCache: {len(malformed)} malformed AMI value(s) in sheet: {malformed!r}",
                level="warning",
            )

        if not any(result):
            # A list of zeros is truthy, so get_data()'s `if not data` guard would
            # cache it for 24h and write it to the 7-day stale key. Every income check
            # would then compare against a limit of 0 and nobody would qualify.
            # Returning empty routes through the stale/fallback path instead.
            capture_message(
                "BoulderAmiCache: every AMI limit parsed as 0; refusing to cache",
                level="error",
            )
            return []

        return result


class NurturingFutures(ProgramCalculator):
    name_abbreviated = "nf"
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
        income_limit = NurturingFutures.ami.get_data()[self.screen.household_size - 1] * NurturingFutures.ami_percent
        income = self.screen.calc_gross_income("yearly", ["all"])
        e.condition(income <= income_limit, messages.income(income, income_limit))
