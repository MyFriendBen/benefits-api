from integrations.services.sheets import GoogleSheetsCache
from programs.co_county_zips import counties_from_screen
from programs.programs.calc import Eligibility, ProgramCalculator
import programs.programs.messages as messages

class IncomeLimitsCache(GoogleSheetsCache):
    sheet_id = "1ZzQYhULtiP61crj0pbPjhX62L1TnyAisLcr_dQXbbFg"
    range_name = "A2:K"
    default = {}

    def update(self):
        data = super().update()
    
        return {self._format_county(r[0]): self._format_amounts(r[1:9]) for r in data}
    
    @staticmethod
    def _format_county(county: str):
        return county.strip() + " County"
    
    @staticmethod
    def _format_amounts(amounts: list[str]):
        return [float(a.strip().replace("$","").replace(",","")) for a in amounts]

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
        income_limits = []
        for county in counties:
            income_limits.append(self.income_limits.fetch()[county][self.screen.household_size - 1])
        income_limit =  min(income_limits)

        income = int(self.screen.calc_gross_income("yearly", ["all"]))
        income_eligible = income <= income_limit
        
        e.condition(income_eligible, messages.income(income, income_limit))

        e.condition(presumptive_eligible)

        # has rent or mortgage expense
        e.condition(self._has_expense())

    def _has_expense(self):
        return self.screen.has_expense(["rent", "mortgage"])
