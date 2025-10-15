from programs.programs.calc import Eligibility, ProgramCalculator
from programs.programs.co.energy_programs_shared.income_validation import get_income_limit
import programs.programs.messages as messages

class UtilityBillPay(ProgramCalculator):
    presumptive_eligibility = ("snap", "ssi", "andcs", "tanf", "wic", "chp")
    member_presumptive_eligibility = ("co_medicaid", "emergency_medicaid")
    amount = 400

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def household_eligible(self, e: Eligibility):
        # has other programs
        presumptive_eligible = False
        for benefit in self.presumptive_eligibility:
            if self.screen.has_benefit(benefit) or (benefit in self.data and self.data[benefit].eligible):
                presumptive_eligible = True
                break

        if not presumptive_eligible:
            for benefit in self.member_presumptive_eligibility:
                if any(member.has_benefit(benefit) for member in self.screen.household_members.all()):
                    presumptive_eligible = True
                    break

         # Presumptive eligibility check
        e.condition(presumptive_eligible)

        # Validate income eligibility (sets condition internally, returns success/failure)
        income_limit = get_income_limit(self.screen)

        # Handle missing data
        if income_limit is None:
            e.condition(
                False, messages.income_limit_unknown()
            )

        user_income = int(self.screen.calc_gross_income("yearly", ["all"]))
        income_eligible = user_income <= income_limit
        e.condition(income_eligible, messages.income(user_income, income_limit))    

        # has rent or mortgage expense
        e.condition(self._has_expense())


    def _has_expense(self):
        return self.screen.has_expense(["rent", "mortgage"])
