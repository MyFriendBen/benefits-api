from datetime import date
from typing import Optional

from screener.models import HouseholdMember
from programs.framework.base import MemberEligibility, ProgramCalculator


class MaBabySteps(ProgramCalculator):
    """
    BabySteps Savings Plan (MA)

    Massachusetts seeds a one-time $50 deposit into a MEFA U.Fund 529 account for each
    qualifying child. Eligibility is evaluated per child, so a household with multiple
    qualifying children is worth $50 per child, not a flat $50.

    Evaluable criteria:
    - The member must be a beneficiary candidate (see `beneficiary_relationships`). No source
      maps BabySteps beneficiary status onto MFB `relationship` values, so Product committed
      this mapping directly: the child roles are candidates, adult caregiver/partner roles are
      not. Two edge cases are accepted: an adult-adopted beneficiary reported as
      `headOfHousehold` is missed, and an older `sibling`/`other` may be valued via the
      adoption fallback below. See spec.md "Beneficiary/member-identification mapping".
    - Birth pathway: born on or after Jan 1, 2020 with the account opened before the first
      birthday. The screener only collects birth month/year, so the entire first-birthday
      month is treated as inside the window (`birth_pathway_eligible`).

    Massachusetts residency (Criterion 1) is handled upstream by white-label routing — the
    program operates statewide, so no sub-state or ZIP check is applied here.

    Data gaps, all handled inclusively (each is disclosed in the program description):
    - Adoption pathway (Criterion 2b): the screener collects no adoption status or date, and
      adopted children of any age can qualify within a year of adoption. A candidate whose
      birth-pathway window has closed is therefore still eligible via `adoption_fallback`
      rather than being denied by a hard age cutoff.
    - Prior BabySteps receipt (Criterion 3): the current-benefits field is household-level and
      cannot identify per-child receipt, so it is not read here. A family that already claimed
      BabySteps for one child may still have a newly born or adopted child who qualifies.
    - Born or adopted in Massachusetts (Criterion 4): birthplace/adoption location is not
      collected, so it is not used to exclude anyone.

    No income, asset, health-insurance, or benefit-receipt gate applies. SNAP receipt neither
    qualifies nor disqualifies — the separate "SNAP into BabySteps" $120 add-on is out of scope.

    Sources: https://www.mass.gov/info-details/babysteps; https://www.mefa.org/article/babysteps/
    (full sourcing in spec.md)
    """

    # One-time $50 seed deposit per qualifying child (lump sum, not a monthly benefit).
    member_amount = 50
    # BabySteps began operating January 1, 2020 — no earlier birth qualifies via the birth pathway.
    program_start = date(2020, 1, 1)
    # The account must be opened before the child's first birthday.
    enrollment_window_months = 12
    beneficiary_relationships = ["child", "fosterChild", "grandChild", "sibling", "other"]
    dependencies = ["relationship", "birth_year"]

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # Beneficiary candidacy is the only evaluable member gate: a candidate qualifies either
        # through the birth pathway or through the adoption-pathway inclusive fallback.
        e.condition(self.is_beneficiary_candidate(member.relationship))

    def is_beneficiary_candidate(self, relationship: Optional[str]) -> bool:
        """
        Whether a `relationship` value describes a possible BabySteps beneficiary.

        This defines the assistance unit — which members are in scope for evaluation at all —
        and is separate from the inclusive defaults applied to unverifiable facts about a
        candidate already in scope.
        """
        return relationship in self.beneficiary_relationships

    def birth_pathway_eligible(self, member: HouseholdMember) -> bool:
        """
        Whether the member qualifies through the birth pathway: born on or after
        January 1, 2020 and still within the one-year enrollment window.

        The screener collects birth month and year but not day, so a child in the month of
        their first birthday could fall on either side of the exact deadline. The whole
        first-birthday month is treated inclusively as inside the window.
        """
        birth_year_month = member.birth_year_month
        if birth_year_month is None:
            return False

        if birth_year_month < self.program_start:
            return False

        reference_date = self.screen.get_reference_date()
        months_since_birth = (reference_date.year - birth_year_month.year) * 12 + (
            reference_date.month - birth_year_month.month
        )

        return 0 <= months_since_birth <= self.enrollment_window_months

    def adoption_fallback_applied(self, member: HouseholdMember) -> bool:
        """
        Whether this member is eligible only through the adoption-pathway inclusive default
        (Criterion 2b) rather than a confirmed birth-pathway result.

        A child adopted within the past year qualifies at any age, and the screener collects
        no adoption information, so a candidate whose birth-pathway window has closed is not
        denied. This is a screening assumption — actual eligibility is verified at enrollment.
        """
        return self.is_beneficiary_candidate(member.relationship) and not self.birth_pathway_eligible(member)
