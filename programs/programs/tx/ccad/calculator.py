from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility


class TxCcad(ProgramCalculator):
    min_age = 65
    min_age_disabled = 21
    fpl_percent = 3
    amount = 10_000
    dependencies = [
        "age",
        "household_size",
        "income_amount",
        "income_frequency",
    ]

    def member_eligible(self, e: MemberEligibility):
        member = e.member
        age = member.age
        age_eligible = age is not None and (
            age >= self.min_age or (age >= self.min_age_disabled and member.has_disability())
        )
        e.condition(bool(age_eligible))

    def household_eligible(self, e: Eligibility):
        # SNAP and TANF are household-level benefits that bypass the income test
        presumed_eligible = self.screen.has_benefit("snap") or self.screen.has_benefit("tanf")

        # SSI and Medicaid are individual — only counts if the age-eligible member has it
        if not presumed_eligible:
            for member_e in e.eligible_members:
                if not member_e.eligible:
                    continue
                member = member_e.member
                has_ssi = member.calc_gross_income("yearly", ["sSI"]) > 0
                has_medicaid = member.has_benefit("medicaid")
                if has_ssi or has_medicaid:
                    presumed_eligible = True
                    break

        gross_income = self.screen.calc_gross_income("yearly", ["all"])
        income_limit = int(self.fpl_percent * self.program.year.get_limit(self.screen.household_size))

        e.condition(presumed_eligible or gross_income <= income_limit)
