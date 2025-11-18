from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility
import programs.programs.messages as messages


class NCLieap(ProgramCalculator):
    fpl_percent = 1.3
    # fpl_percent = 0.5
    fpl_percent_senior_disabled = 1.5
    earned_deduction = 0.2
    medical_deduction_senior_disabled = 85
    expenses = ["rent", "mortgage", "heating"]
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
        gross_income = self._calculate_gross_income()
        income_limit = self._calculate_income_limit()

        e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))

    def household_value(self):
        household_size = self.screen.household_size

        # Calculate income and limits
        gross_income = self._calculate_gross_income()
        income_limit = self._calculate_income_limit()
        base_income_limit = self.program.year.as_dict()[household_size]

        if household_size < self.large_household_size:  # 1-3 person household
            if gross_income <= base_income_limit * self.max_value_fpl_percent:  # 0-50% FPL
                return self.small_household_low_income_value  # $400/month
            elif gross_income <= base_income_limit:  # 51%+ FPL
                return self.small_household_large_income_value  # $300/month
        else:  # 4+ person household
            if gross_income <= base_income_limit * self.max_value_fpl_percent:  # 0-50% FPL
                return self.large_household_low_income_value  # $500/month
            elif gross_income <= base_income_limit:  # 51%+ FPL
                return self.large_household_large_income_value  # $400/month

        return 0

    def _calculate_gross_income(self):

        # Determine deductions based on senior/disabled status
        has_senior_disabled = self._has_senior_or_disabled()
        medical_deduction_senior_disabled = NCLieap.medical_deduction_senior_disabled * 12 if has_senior_disabled else 0

        # Calculate childcare expenses
        childcare_expenses = self.screen.calc_expenses("yearly", ["childCare", "childSupport"])

        # Calculate income components
        earned_income = self.screen.calc_gross_income("yearly", ["earned"])
        unearned_income = self.screen.calc_gross_income("yearly", ["unearned"])

        # Apply earned income deduction only to earned income
        if earned_income > 0:
            earned_income -= earned_income * NCLieap.earned_deduction

        # Calculate gross income
        gross_income = max(
            0, (earned_income + unearned_income) - childcare_expenses - medical_deduction_senior_disabled
        )

        return gross_income

    def _calculate_income_limit(self):

        # Determine FPL% based on senior/disabled status
        has_senior_disabled = self._has_senior_or_disabled()
        fpl_percent = self.fpl_percent_senior_disabled if has_senior_disabled else self.fpl_percent

        # Calculate income limit
        household_size = self.screen.household_size
        income_limit = int(fpl_percent * self.program.year.as_dict()[household_size])
        return income_limit

    def _has_senior_or_disabled(self):
        """
        Check if any household member is senior (60+) or disabled.
        """
        for member in self.screen.household_members.all():
            if member.age is not None and member.age >= 60 or member.has_disability():
                return True
        return False
