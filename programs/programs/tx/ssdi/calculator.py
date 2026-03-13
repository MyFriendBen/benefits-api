from programs.programs.calc import MemberEligibility, ProgramCalculator


class TxSsdi(ProgramCalculator):
    income_limit = 1_690  # 2026 non-blind SGA threshold
    income_limit_blind = 2_830  # 2026 blind SGA threshold
    member_amount = 1_580 * 12  # average annual SSDI benefit
    max_age = 67  # Full Retirement Age for those born 1960+
    dependencies = ["income_amount", "income_frequency", "household_size"]

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # long-term disability required (12+ months expected duration)
        e.condition(member.long_term_disability)

        # not already receiving SSDI (current benefits checkbox)
        e.condition(not self.screen.has_benefit("tx_ssdi"))

        # not already receiving Social Security retirement benefits
        e.condition(member.calc_gross_income("monthly", ["sSRetirement"]) == 0)

        # income below SGA threshold (inclusive of limit per SSA rules)
        income_limit = TxSsdi.income_limit_blind if member.visually_impaired else TxSsdi.income_limit
        e.condition(member.calc_gross_income("monthly", ("all",)) <= income_limit)

        # under Full Retirement Age
        e.condition(member.age < TxSsdi.max_age)
