from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility
import programs.programs.messages as messages


class NCLieap(ProgramCalculator):
    fpl_percent = 1.3
    fpl_percent_senior_disabled = 1.5
    earned_deduction = 0.2
    medical_deduction = 85
    expenses = ["rent", "mortgage", "heating", "Childcare"]
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
        household_size = self.screen.household_size

        #  set earned deduction based on senior/disabled status
        earned_deduction = 0 if getattr(self, "_has_senior_or_disabled", False) else NCLieap.earned_deduction

        # has rent, mortgage or heating expense
        has_program_expense = self.screen.has_expense(NCLieap.expenses)
        e.condition(has_program_expense)

        # Get child care expenses (yearly)
        childcare_expenses = self.screen.calc_expenses("yearly", ["childCare"])

        # Use higher FPL% if any member is senior or disabled
        fpl_percent = (
            self.fpl_percent_senior_disabled if getattr(self, "_has_senior_or_disabled", False) else self.fpl_percent
        )

        # Set medical_deduction  based on senior/disabled status
        medical_deduction = NCLieap.medical_deduction * 12 if getattr(self, "_has_senior_or_disabled", False) else 0

        # Calculate earned income (wages + self-employment only)
        earned_income = self.screen.calc_gross_income("yearly", ["earned"])

        # Calculate unearned income
        unearned_income = self.screen.calc_gross_income("yearly", ["unearned"], ["sSI"])

        # Apply earned income deduction only to earned income
        if earned_income > 0:
            gross_income = (earned_income - (earned_income * earned_deduction) - childcare_expenses) - medical_deduction
        elif unearned_income > 0:
            gross_income = (unearned_income - childcare_expenses) - medical_deduction
        else:
            gross_income = 0

        income_limit = int(fpl_percent * self.program.year.as_dict()[household_size])

        e.condition(gross_income < income_limit, messages.income(gross_income, income_limit))

    def household_value(self):
        household_size = self.screen.household_size

        # Calculate earned vs other income separately
        earned_income = self.screen.calc_gross_income("yearly", ["earned"])
        unearned_income = self.screen.calc_gross_income("yearly", ["unearned"], ["sSI"])

        # Use same FPL% logic as household_eligible
        fpl_percent = (
            self.fpl_percent_senior_disabled if getattr(self, "_has_senior_or_disabled", False) else self.fpl_percent
        )

        #  set earned deduction based on senior/disabled status
        earned_deduction = 0 if getattr(self, "_has_senior_or_disabled", False) else NCLieap.earned_deduction
        # Set medical_deduction  based on senior/disabled status
        medical_deduction = NCLieap.medical_deduction * 12 if getattr(self, "_has_senior_or_disabled", False) else 0

        childcare_expenses = self.screen.calc_expenses("yearly", ["childCare"])

        # Apply earned income deduction only to earned income
        if earned_income > 0:
            gross_income = (
                (earned_income - (earned_income * earned_deduction)) - childcare_expenses
            ) - medical_deduction
        elif unearned_income > 0:
            gross_income = (unearned_income - childcare_expenses) - medical_deduction
        else:
            gross_income = 0

        income_limit = int(fpl_percent * self.program.year.as_dict()[household_size])

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

    def member_eligible(self, e: MemberEligibility):
        member = e.member
        # Check if member is senior (60+) or has disability. Set calculator-level flag
        # but don't mark member ineligible - LIEAP is a household program.
        is_senior = member.age is not None and member.age >= 60
        has_disability = member.has_disability()

        if is_senior or has_disability:
            setattr(self, "_has_senior_or_disabled", True)
