from datetime import date
from programs.framework.base import MemberEligibility, ProgramCalculator, Eligibility


class TrumpAccount(ProgramCalculator):
    """
    530A ("Trump") Accounts — Section 530A of the IRC as created by the 2025 tax law.

    Government-authorized custodial investment accounts for children under 18. This calculator
    models only the $1,000 pilot contribution: U.S. citizen children born between January 1,
    2025 and December 31, 2028 (pilot window). Children outside this window are not shown —
    while they can technically open an account, there is no government benefit to surface.

    Pilot window is compared using the member's birth_year_month (month + year precision).

    A child who has not been born is not eligible, however near the due date: 26 U.S.C.
    §6434(e) requires the child's Social Security number to be included with the election,
    and an unborn child has none.

    No income limit applies. Citizenship is enforced via legal_status_required config.

    Gaps (not evaluable in screener):
    - SSN requirement (not collected)
    - Duplicate account check (screener does not track existing Trump Accounts)
    - Program launch date (accounts available July 4, 2026 or later)
    """

    program_code = "federal_trump_account"

    pilot_contribution = 1_000
    pilot_start = date(2025, 1, 1)
    pilot_end = date(2028, 12, 31)
    max_age = 17  # must be under 18
    dependencies = ["age"]

    def member_eligible(self, e: MemberEligibility):
        member = e.member
        birth_year_month = member.birth_year_month
        in_pilot_window = birth_year_month is not None and self.pilot_start <= birth_year_month <= self.pilot_end
        e.condition(member.calc_age() <= self.max_age and in_pilot_window)

    def value(self, e: Eligibility):
        # Eligibility is already gated on the pilot window in member_eligible,
        # so every eligible member receives the $1,000 contribution.
        if not e.eligible:
            return

        for member_eligibility in e.eligible_members:
            if not member_eligibility.eligible:
                continue
            member_eligibility.value = self.pilot_contribution
