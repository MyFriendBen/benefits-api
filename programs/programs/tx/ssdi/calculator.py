from programs.programs.calc import MemberEligibility, ProgramCalculator


class TxSsdi(ProgramCalculator):
    income_limit = 1_690  # 2026 non-blind SGA threshold
    income_limit_blind = 2_830  # 2026 blind SGA threshold
    member_amount = 1_580 * 12  # average annual SSDI benefit
    dependencies = ["income_amount", "income_frequency", "household_size"]

    @staticmethod
    def _full_retirement_age(birth_year: int | None) -> int | float:
        """Return FRA in years per the SSA schedule. Falls back to 67 when birth year is unknown."""
        if birth_year is None or birth_year >= 1960:
            return 67
        if birth_year >= 1955:
            return 66 + (birth_year - 1954) * 2 / 12  # 66y2m → 66y10m
        if birth_year >= 1943:
            return 66
        # Pre-1943 cohort is 83+ today and always past FRA
        return 65

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
        e.condition(member.calc_gross_income("monthly", ["earned"]) <= income_limit)

        # under Full Retirement Age (varies by birth year per SSA schedule)
        e.condition(member.fraction_age() < TxSsdi._full_retirement_age(member.birth_year))
