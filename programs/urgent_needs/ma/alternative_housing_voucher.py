from integrations.services.income_limits import ami
from ..base import UrgentNeedFunction


class AlternativeHousingVoucher(UrgentNeedFunction):
    dependencies = ["income_amount", "income_frequency", "household_size", "county"]
    ami_percent = "80%"
    max_age = 60

    def eligible(self):
        # income
        income_limit = ami.get_screen_ami(self.screen, self.ami_percent, self.urgent_need.year.period, limit_type="il")
        income = self.screen.calc_gross_income("yearly", ["all"])
        income_eligible = income <= income_limit

        # disability
        member_eligible = False
        for member in self.screen.household_members.all():
            if member.has_disability() and member.age < self.max_age:
                member_eligible = True

        return member_eligible and income_eligible
