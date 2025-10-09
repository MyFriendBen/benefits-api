from integrations.services.sheets import GoogleSheetsCache
from programs.co_county_zips import counties_from_screen
from programs.programs.calc import Eligibility, ProgramCalculator
from programs.programs.co.income_limits_cache.income_limits_cache import IncomeLimitsCache
import programs.programs.messages as messages


class UtilityBillPay(ProgramCalculator):
    presumptive_eligibility = ("snap", "ssi", "andcs", "tanf", "wic", "chp")
    member_presumptive_eligibility = ("co_medicaid", "emergency_medicaid")
    amount = 400

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.income_limits = IncomeLimitsCache()

    def household_eligible(self, e: Eligibility):
        # has other programs
        presumptive_eligible = False
        for benefit in self.presumptive_eligibility:
            if self.screen.has_benefit(benefit):
                presumptive_eligible = True
                break
            elif benefit in self.data and self.data[benefit].eligible:
                presumptive_eligible = True
                break

        for benefit in self.member_presumptive_eligibility:
            if presumptive_eligible:
                break
            if any(member.has_benefit(benefit) for member in self.screen.household_members.all()):
                presumptive_eligible = True

        # income condition
        counties = counties_from_screen(self.screen)
        limits_by_county = self.income_limits.fetch()
        income_limits = []
        size_index = self.screen.household_size - 1
        for county in counties:
            if county not in limits_by_county:
                continue
            county_data = limits_by_county.get(county)
            if county_data is None:
                continue

            # Validate household_size bounds (1-8)
            if size_index < 0 or size_index >= len(county_data):
                continue
            try:
                income_limits.append(county_data[size_index])
            except IndexError:
                continue

        income = int(self.screen.calc_gross_income("yearly", ["all"]))
        if not income_limits:
            e.condition(False, messages.income_limit_lookup_failed())
            return
        income_limit = min(income_limits)

        income_eligible = income <= income_limit

        e.condition(income_eligible, messages.income(income, income_limit))

        e.condition(presumptive_eligible)

        # has rent or mortgage expense
        e.condition(self._has_expense())

    def _has_expense(self):
        return self.screen.has_expense(["rent", "mortgage"])
