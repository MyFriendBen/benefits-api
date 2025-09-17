from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility
import programs.programs.messages as messages


class NCLieap(ProgramCalculator):
    fpl_percent = 1.3
    fpl_percent_senior_disabled = 1.5
    earned_deduction = 0.2
    medical_deduction = 85
    expenses = ["rent", "mortgage", "heating", "Childcare", "childSupport"]
    dependencies = [
        "income_frequency",
        "income_amount",
        "household_size",
        "age",
    ]
    large_household_size = 4
    max_value_fpl_percent = 0.5
    small_household_low_income_value = 400
    small_household_large_income_value = 300
    large_household_low_income_value = 500
    large_household_large_income_value = 400

    def household_eligible(self, e: Eligibility):
        # has rent, mortgage or heating expense
        has_program_expense = self.screen.has_expense(NCLieap.expenses)
        e.condition(has_program_expense)

        # Calculate income and limits
        gross_income, income_limit = self._calculate_income_and_limit()

        e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))

    def household_value(self):
        household_size = self.screen.household_size

        # Calculate income and limits
        gross_income, income_limit = self._calculate_income_and_limit()

        # Determine benefit amount based on household size and income
        if household_size < self.large_household_size:
            if gross_income <= income_limit * self.max_value_fpl_percent:
                return self.small_household_low_income_value
            elif gross_income <= income_limit:
                return self.small_household_large_income_value
        else:
            if gross_income <= income_limit * self.max_value_fpl_percent:
                return self.large_household_low_income_value
            elif gross_income <= income_limit:
                return self.large_household_large_income_value

    def _calculate_income_and_limit(self):

        # Calculate gross income and income limit.
        household_size = self.screen.household_size

        # Determine deductions and FPL% based on senior/disabled status
        has_senior_disabled = self._has_senior_or_disabled()
        earned_deduction = 0 if has_senior_disabled else NCLieap.earned_deduction
        fpl_percent = self.fpl_percent_senior_disabled if has_senior_disabled else self.fpl_percent
        medical_deduction = NCLieap.medical_deduction * 12 if has_senior_disabled else 0

        # Calculate childcare expenses
        childcare_expenses = self.screen.calc_expenses("yearly", ["childCare", "childSupport"])

        # Calculate income components
        earned_income = self.screen.calc_gross_income("yearly", ["earned"])
        unearned_income = self.screen.calc_gross_income("yearly", ["unearned"])

        # Apply earned income deduction only to earned income
        if earned_income > 0:
            earned_income = earned_income - (earned_income * earned_deduction)

        # Calculate final gross income and income limit
        gross_income = ((earned_income + unearned_income) - childcare_expenses) - medical_deduction
        income_limit = int(fpl_percent * self.program.year.as_dict()[household_size])

        return gross_income, income_limit

    def _has_senior_or_disabled(self):
        """
        Check if any household member is senior (60+) or disabled.
        """
        for member in self.screen.household_members.all():
            if member.age is not None and member.age >= 60 or member.has_disability():
                return True
        return False
