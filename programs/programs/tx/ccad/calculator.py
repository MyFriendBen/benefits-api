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
        age_eligible = member.age is not None and (
            member.age >= self.min_age or (member.age >= self.min_age_disabled and member.has_disability())
        )
        e.condition(age_eligible)

    def household_eligible(self, e: Eligibility):
        e.condition(not self.screen.has_benefit("tx_ccad"))

        household_size = self.screen.household_size
        gross_income = self.screen.calc_gross_income("yearly", ["all"])
        income_limit = int(self.fpl_percent * self.program.year.get_limit(household_size))

        categorically_eligible = (
            self.screen.has_snap
            or self.screen.has_ssi
            or self.screen.has_tanf
            or self.screen.has_medicaid
        )

        e.condition(categorically_eligible or gross_income <= income_limit)
