from integrations.services.sheets import GoogleSheetsCache
from programs.co_county_zips import counties_from_screen
from programs.programs.calc import Eligibility, ProgramCalculator
import programs.programs.messages as messages
from typing import ClassVar


class IncomeLimitsCache(GoogleSheetsCache):
    sheet_id = "1ZzQYhULtiP61crj0pbPjhX62L1TnyAisLcr_dQXbbFg"
    range_name = "A2:K"
    default: ClassVar[dict] = {}

    def update(self) -> dict[str, list[float]]:
        data = super().update()
        result = {}
        for r in data:
            if len(r) < 9:
                continue
            result[self._format_county(r[0])] = self._format_amounts(r[1:9])
        return result

    @staticmethod
    def _format_county(county: str):
        return county.strip() + " County"

    @staticmethod
    def _format_amounts(amounts: list[str]):
        result = []
        for a in amounts:
            cleaned = a.strip().replace("$", "").replace(",", "")
            if cleaned:
                try:
                    result.append(float(cleaned))
                except ValueError:
                    result.append(0.0)
            else:
                result.append(0.0)
        return result


class UtilityBillPay(ProgramCalculator):
    income_limits = IncomeLimitsCache()
    presumptive_eligibility = ("snap", "ssi", "andcs", "tanf", "wic", "chp")
    member_presumptive_eligibility = ("co_medicaid", "emergency_medicaid")
    amount = 400

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
        size_index = self.screen.household_size - 1
        income_limits = []
        for county in counties:
            county_data = self.income_limits.fetch().get(county)
            if not county_data:
                continue

            # Validate household_size bounds (1-8)
            if size_index < 0 or size_index >= len(county_data):
                continue
            income_limits.append(county_data[size_index])

        if not income_limits:
            e.condition(False, messages.income())
            return
        income_limit = min(income_limits)

        income = int(self.screen.calc_gross_income("yearly", ["all"]))
        income_eligible = income <= income_limit

        e.condition(income_eligible, messages.income(income, income_limit))

        e.condition(presumptive_eligible)

        # has rent or mortgage expense
        e.condition(self._has_expense())

    def _has_expense(self):
        return self.screen.has_expense(["rent", "mortgage"])
