from programs.programs.calc import Eligibility, ProgramCalculator
from programs.programs.co.energy_programs_shared.income_limits_cache import IncomeLimitsCache
from programs.programs.co.energy_programs_shared.income_validation import validate_income_eligibility


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

        # Validate income eligibility (sets condition internally, returns success/failure)
        income_validation_passed = validate_income_eligibility(self.screen, e, self.income_limits)

        if not income_validation_passed:
            # Income validation failed completely
            return

        # Presumptive eligibility check
        e.condition(presumptive_eligible)

        # has rent or mortgage expense
        e.condition(self._has_expense())

    def _has_expense(self):
        return self.screen.has_expense(["rent", "mortgage"])
