from programs.programs.calc import MemberEligibility, ProgramCalculator

# Full Retirement Age in fractional years by birth year (SSA schedule).
# 1937 and earlier → 65, 1960 and later → 67 (handled in _full_retirement_age).
_FRA_BY_BIRTH_YEAR: dict[int, float] = {
    1938: 65 + 2 / 12,
    1939: 65 + 4 / 12,
    1940: 65 + 6 / 12,
    1941: 65 + 8 / 12,
    1942: 65 + 10 / 12,
    **{year: 66.0 for year in range(1943, 1955)},
    1955: 66 + 2 / 12,
    1956: 66 + 4 / 12,
    1957: 66 + 6 / 12,
    1958: 66 + 8 / 12,
    1959: 66 + 10 / 12,
}


class TxSsdi(ProgramCalculator):
    income_limit = 1_690  # 2026 non-blind SGA threshold
    income_limit_blind = 2_830  # 2026 blind SGA threshold
    member_amount = 1_580 * 12  # average annual SSDI benefit
    dependencies = ["income_amount", "income_frequency", "household_size"]

    @staticmethod
    def _full_retirement_age(birth_year: int | None) -> float:
        """Return FRA in fractional years. Falls back to 67 when birth year is unknown."""
        if birth_year is None or birth_year >= 1960:
            return 67.0
        if birth_year <= 1937:
            return 65.0
        return _FRA_BY_BIRTH_YEAR[birth_year]

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
        fra = TxSsdi._full_retirement_age(member.birth_year)
        e.condition(member.fraction_age() < fra)
