from programs.programs.calc import Eligibility, MemberEligibility, ProgramCalculator
from programs.programs.helpers import medicaid_eligible
import programs.programs.messages as messages


class KsWorkingHealthy(ProgramCalculator):
    """
    KanCare Working Healthy (KS) — Medicaid buy-in for workers with disabilities.

    Working Healthy lets employed Kansans with disabilities buy into full Medicaid
    coverage at income levels above regular Medicaid. Eligibility (KEESM §2664):

      1. Age 16 through 64 (coverage runs through the month of the 65th birthday)
      2. Qualifying disability or blindness — screened via ``long_term_disability``
         / ``visually_impaired`` (NOT the generic ``disabled`` flag, matching the
         awd_medicaid precedent)
      3. Currently employed with earned income (wages / self-employment)
      4. Countable earned income above the $65/month disregard floor
      5. Countable income <= 300% FPL for the assistance-plan size, using the
         awd_medicaid disregard method: countable = (earned - $65)*0.5 +
         (unearned - $20), compared to FPL[plan_size] * 3.0
      6. Countable resources <= $15,000 flat (does NOT scale with household size)
      7. Kansas resident (handled by white-label routing)
      8. Not otherwise covered by full Medicaid, not an SSI recipient, not on an
         HCBS waiver — screened via insurance in (none/employer/private) and the
         absence of a reported SSI income stream.

    Assistance-plan size is individual-centric (single -> 1; married -> 2; minor
    under 18 living with a parent -> 2), per the premium-sizing convention
    extended to the income test (MFB policy choice; the stricter 2-person bracket
    is the conservative direction).

    Data gaps (all inclusive defaults, verified at application): FICA/SECA coverage,
    minimum-wage rate for non-hourly entries, IRWE/BWE/SSI-deeming disregards,
    retirement/IDA resource exemptions, institutional residence, residency intent,
    fraud-conviction bar. See spec.md for the full treatment.
    """

    min_age = 16
    max_age = 64
    max_income_percent = 3.0
    earned_deduction = 65
    earned_percent = 0.5
    unearned_deduction = 20
    resource_limit = 15_000
    earned_monthly_floor = 65
    insurance_types = ("employer", "private", "none")

    # $19,051/yr per eligible member: KS Working Healthy program cost per enrollee,
    # from KDHE's Medical Assistance Report (MAR), FY2025 — $24,879,015 total Working
    # Healthy expenditure / 1,306 average monthly beneficiaries. The MAR tracks Working
    # Healthy as its own population line, so this excludes the LTSS/institutional
    # enrollees that inflate the general disabled-Medicaid figure. See spec.md Benefit Value.
    member_amount = 19_051

    dependencies = [
        "age",
        "insurance",
        "household_size",
        "income_type",
        "income_amount",
        "income_frequency",
        "household_assets",
        "relationship",
    ]

    def household_eligible(self, e: Eligibility):
        # Not otherwise covered by full Medicaid through another category.
        e.condition(not medicaid_eligible(self.data), messages.must_not_have_benefit("Medicaid"))

        # Countable resources <= $15,000 flat (any size family group; KEESM §5130).
        assets = self.screen.household_assets if self.screen.household_assets is not None else 0
        e.condition(assets <= self.resource_limit, messages.assets(self.resource_limit))

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # Age 16 through 64.
        e.condition(member.age is not None and self.min_age <= member.age <= self.max_age)

        # Qualifying disability or blindness (not the generic short-term flag).
        e.condition(member.long_term_disability or member.visually_impaired)

        # Insurance: none / employer / private (excludes current Medicaid/Medicare;
        # also catches HCBS-waiver recipients, who receive services through Medicaid).
        e.condition(member.insurance.has_insurance_types(self.insurance_types))

        # SSI recipients remain in the SI program and are excluded from Working
        # Healthy, even when working and within limits.
        e.condition(member.calc_gross_income("monthly", ["sSI"]) <= 0)

        # Employment requirement: must have earned income, and gross monthly earned
        # income must exceed the $65/month floor (KEESM §2664.3).
        gross_monthly_earned = member.calc_gross_income("monthly", ["earned"])
        e.condition(gross_monthly_earned > self.earned_monthly_floor)

        # Countable income <= 300% FPL for the (individual-centric) plan size.
        plan_size = self._assistance_plan_size(member)
        income_limit = self.program.year.get_limit(plan_size) * self.max_income_percent
        earned = max(
            0, int((int(member.calc_gross_income("yearly", ["earned"])) - self.earned_deduction) * self.earned_percent)
        )
        unearned = int(member.calc_gross_income("yearly", ["unearned"])) - self.unearned_deduction
        e.condition(earned + unearned <= income_limit)

    def _assistance_plan_size(self, member) -> int:
        """
        Individual-centric assistance-plan size for the income test:
        married -> 2; minor (<18) living with a parent -> 2; otherwise -> 1.
        (MFB policy choice extended from the premium-sizing convention; the
        stricter 2-person bracket errs toward false negatives, the safe direction.)
        """
        if member.is_married()["is_married"]:
            return 2

        if member.age is not None and member.age < 18:
            has_parent = any(
                m.relationship in ("parent", "stepParent", "fosterParent") for m in self.screen.household_members.all()
            )
            if has_parent:
                return 2

        return 1
