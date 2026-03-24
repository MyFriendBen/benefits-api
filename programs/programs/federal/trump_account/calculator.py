from datetime import date, timedelta
from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility


class TrumpAccount(ProgramCalculator):
    """
    530A ("Trump") Accounts — Section 530A of the IRC as created by the 2025 tax law.

    Government-authorized custodial investment accounts for children under 18. This calculator
    models only the $1,000 pilot contribution: U.S. citizen children born between January 1,
    2025 and December 31, 2028 (pilot window). Children outside this window are not shown —
    while they can technically open an account, there is no government benefit to surface.

    Pilot window is compared using the member's birth_year_month (month + year precision).

    Pregnant members are included: if the estimated due date (today + 280 days) falls within
    the pilot window, they receive the $1,000 contribution.

    No income limit applies. Citizenship is enforced via legal_status_required config.

    Gaps (not evaluable in screener):
    - SSN requirement (not collected)
    - Duplicate account check (screener does not track existing Trump Accounts)
    - Program launch date (accounts available July 4, 2026 or later)
    """

    pilot_contribution = 1_000
    pilot_start = date(2025, 1, 1)
    pilot_end = date(2028, 12, 31)
    max_age = 17  # must be under 18
    gestation_days = 280  # 40 weeks
    dependencies = ["age", "pregnant"]

    def member_eligible(self, e: MemberEligibility):
        member = e.member
        if member.pregnant:
            estimated_due_date = self.screen.get_reference_date() + timedelta(days=self.gestation_days)
            e.condition(self.pilot_start <= estimated_due_date <= self.pilot_end)
        else:
            birth_year_month = member.birth_year_month
            in_pilot_window = birth_year_month is not None and self.pilot_start <= birth_year_month <= self.pilot_end
            e.condition(member.age <= self.max_age and in_pilot_window)

    def value(self, e: Eligibility):
        # Eligibility is already gated on the pilot window in member_eligible,
        # so every eligible member receives the $1,000 contribution.
        if not e.eligible:
            return

        for member_eligibility in e.eligible_members:
            if not member_eligibility.eligible:
                continue
            member_eligibility.value = self.pilot_contribution
