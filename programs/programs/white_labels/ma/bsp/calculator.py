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
      not. One edge case is accepted: an adult-adopted beneficiary reported as
      `headOfHousehold` is missed. See spec.md "Beneficiary/member-identification mapping".
    - Birth pathway: born on or after Jan 1, 2020 with the account opened before the first
      birthday. The screener only collects birth month/year, so the entire first-birthday
      month is treated as inside the window (`birth_pathway_eligible`).

    Massachusetts residency (Criterion 1) is handled upstream by white-label routing — the
    program operates statewide, so no sub-state or ZIP check is applied here.

    The adoption pathway (Criterion 2b) is not evaluable: an adopted child of any age
    qualifies within one year of the adoption, but the screener collects no adoption status
    or date. Because that window turns on the adoption date rather than age, it cannot be
    approximated from birth date — so the birth-pathway cutoff applies to every candidate and
    the program description directs recently adopting families to check directly. This is a
    known false negative for that group.

    Data gaps handled inclusively (each is disclosed in the program description):
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

    program_code = "ma_bsp"

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

        # A beneficiary candidate qualifies through the birth pathway: born on or after the
        # program start date and still inside the one-year enrollment window. The adoption
        # pathway opens a separate one-year window off the adoption date, which the screener
        # collects no input for, so it cannot be evaluated here — the program description
        # tells families with a recently adopted child of any age to check directly.
        e.condition(self.is_beneficiary_candidate(member.relationship))
        e.condition(self.birth_pathway_eligible(member))

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
