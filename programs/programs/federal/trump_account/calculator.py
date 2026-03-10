from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility


class TrumpAccount(ProgramCalculator):
    """
    530A ("Trump") Accounts — Section 530A of the IRC as created by the 2025 tax law.

    Government-authorized custodial investment accounts for children under 18. The federal
    government makes a one-time $1,000 pilot contribution for U.S. citizen children born
    between January 1, 2025 and December 31, 2028. Children outside this birth window can
    still open an account but receive no government contribution (value = $0).

    No income limit applies. Citizenship is enforced via legal_status_required config.

    Gaps (not evaluable in screener):
    - SSN requirement (not collected)
    - Duplicate account check (screener does not track existing Trump Accounts)
    - Program launch date (accounts available July 4, 2026 or later)
    """

    pilot_contribution = 1_000
    pilot_birth_year_min = 2025
    pilot_birth_year_max = 2028
    max_age = 17  # must be under 18
    dependencies = ["age"]

    def member_eligible(self, e: MemberEligibility):
        member = e.member
        e.condition(member.age <= TrumpAccount.max_age)

    def value(self, e: Eligibility):
        # All under-18 children are eligible to open an account (value = $0 by default).
        # Only children born in the pilot window (2025–2028) receive the $1,000 government
        # contribution
        if not e.eligible:
            return

        for member_eligibility in e.eligible_members:
            if not member_eligibility.eligible:
                continue
            member = member_eligibility.member
            birth_year = member.birth_year
            if birth_year is not None and TrumpAccount.pilot_birth_year_min <= birth_year <= TrumpAccount.pilot_birth_year_max:
                member_eligibility.value = TrumpAccount.pilot_contribution
