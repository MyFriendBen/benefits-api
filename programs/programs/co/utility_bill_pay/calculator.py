from programs.programs.calc import Eligibility, ProgramCalculator
from integrations.services.income_limits import income_limits_cache
import programs.programs.messages as messages


class UtilityBillPay(ProgramCalculator):
    presumptive_eligibility = ("snap", "ssi", "andcs", "tanf", "wic", "chp")
    member_presumptive_eligibility = ("co_medicaid", "emergency_medicaid")
    amount = 400

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def household_eligible(self, e: Eligibility):
        presumed_eligibility = False
        for benefit in self.presumptive_eligibility:
            if self.screen.has_benefit(benefit) or (benefit in self.data and self.data[benefit].eligible):
                presumed_eligibility = True
                break

        if not presumed_eligibility:
            for benefit in self.member_presumptive_eligibility:
                if any(member.has_benefit(benefit) for member in self.screen.household_members.all()):
                    presumed_eligibility = True
                    break

        # Must have EITHER income eligible OR presumed eligibility
        if presumed_eligibility:
            e.condition(presumed_eligibility, messages.presumed_eligibility())
        else:
            # check income limit and expenses
            income_limit = income_limits_cache.get_income_limit(self.screen)
            if income_limit:
                user_income = int(self.screen.calc_gross_income("yearly", ["all"]))
                income_eligible = user_income <= income_limit
                e.condition(income_eligible, messages.income(user_income, income_limit))
            else:
                # no income limit data
                e.condition(False, messages.income_limit_unknown())

            # has rent or mortgage expense
            e.condition(self._has_expense())

    def _has_expense(self):
        return self.screen.has_expense(["rent", "mortgage"])
