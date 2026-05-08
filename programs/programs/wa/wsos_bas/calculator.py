import programs.programs.messages as messages
from programs.programs.calc import Eligibility, MemberEligibility, ProgramCalculator


class WaWsosBas(ProgramCalculator):
    """
    Washington State Opportunity Scholarship — Baccalaureate (BaS) track.

    Up to $22,500 lump-sum scholarship over the program duration, applied to
    Cost of Attendance after other financial aid (Pell, Washington College
    Grant, etc.). Funds are intended for Washington undergraduates pursuing
    a first bachelor's degree in an eligible STEM or health care major at an
    eligible Washington college or university.

    Screener-checkable criteria (what this calculator actually screens):
      - Washington residency: implicit via the `wa` white label
      - At least one household member is a student (`member.student == True`).
        Note: BaS also accepts applicants who plan to enroll but do not yet
        consider themselves a student. The screener cannot disambiguate, so
        this gate is necessarily an underestimate.
      - Household annual income at or below 125% Washington State Median
        Family Income (MFI) for the household size

    Inclusivity assumptions (per spec.md — fields the screener does not
    collect; we assume met for any student respondent and surface the
    caveats in `description`):
      - Has not yet earned a bachelor's degree (BaS funds the *first*
        bachelor's only)
      - Has earned, or will earn by June of the application year, a
        Washington high school credential or passing GED scores
      - Cumulative GPA >= 2.75 on a 4.0 scale (or passing GED score)
      - Has not earned more than 90 quarter / 60 semester credits since
        high school graduation (Running Start / dual-credit excluded).
        Per spec direction this constraint is intentionally NOT surfaced
        in the user-facing description.
      - Plans to enroll in at least three credits every fall, winter, and
        spring term while using the scholarship
      - Enrolled (or planning to enroll) in an eligible STEM or health
        care major at an eligible Washington institution

    Income test: BaS uses a single 125% MFI threshold by household size —
    no expanded / hardship-band like the GRD track. We compare current
    pre-tax household gross income to the 2026 published 125% MFI table.

    Note on the family-of-11 typo: the official 2026 BaS MFI Chart
    publishes $156,500 for a family of 11, which is out of sequence with
    surrounding values and identical to the same typo in the GRD chart.
    Per spec direction, we do not silently "correct" this in code; the
    typo is worth flagging to WSOS once across all WSOS programs rather
    than per-program. This calculator's table contains only the
    monotonic published values for sizes 1-6 plus a documented linear
    extension for sizes 7+.

    Sources:
      - https://waopportunityscholarship.org/applicants/baccalaureate/
        (Eligibility, Education plan, Financial Need)
      - https://waopportunityscholarship.org/wp-content/uploads/2025/10/
        Baccalaureate-C15-MFI-Chart.pdf (Official 2026 BaS MFI Chart)
    """

    # 2026 WSOS BaS 125% MFI thresholds in dollars per year. Per-household-
    # size lookup table sourced from the official BaS MFI Chart linked
    # above. BaS has only this single tier (unlike GRD which also has a
    # 155% expanded band).
    MFI_125_BY_SIZE = {
        1: 90_500,
        2: 118_000,
        3: 146_500,
        4: 174_500,
        5: 202_000,
        6: 230_000,
    }

    # Spec only publishes sizes 1-6 (and a typo at size 11). For larger
    # households, extend by the average increment observed in the
    # published table (~$28,000 per additional person at 125% MFI):
    # 1->2: +27.5K, 2->3: +28.5K, 3->4: +28K, 4->5: +27.5K, 5->6: +28K.
    # Validations only cover sizes 1 and 4 today; this fallback exists so
    # a 7+ person household is not silently denied or crashed.
    MFI_125_PER_EXTRA_PERSON_ABOVE_TABLE = 28_000

    amount = 22_500  # lump-sum scholarship per household, per the program page

    dependencies = ["income_amount", "income_frequency", "household_size"]

    def income_limit_125(self) -> int:
        """
        Annual 125% MFI income cap for the household's size, with linear
        extension for sizes larger than the published table.
        """
        size = self.screen.household_size
        if size in self.MFI_125_BY_SIZE:
            return self.MFI_125_BY_SIZE[size]
        return self.MFI_125_BY_SIZE[6] + (size - 6) * self.MFI_125_PER_EXTRA_PERSON_ABOVE_TABLE

    def household_eligible(self, e: Eligibility):
        # `calc_gross_income` returns a float; compare against the limit at
        # full precision so a household whose annual income is fractionally
        # above the 125% MFI cap (e.g. $174,500.50 for a 4-person household)
        # is correctly screened out instead of being floored down onto the
        # boundary. `messages.income` rounds for display, so passing a float
        # is fine. Same approach as WaWsosGrd.
        gross_income = self.screen.calc_gross_income("yearly", ["all"])
        income_limit = self.income_limit_125()
        e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))

    def member_eligible(self, e: MemberEligibility):
        # Any student counts as the BaS applicant. The base ProgramCalculator
        # auto-fails the household if no member is eligible, which is what we
        # want when nobody in the household is a student.
        e.condition(bool(e.member.student))

    def household_value(self) -> int:
        return self.amount

    def member_value(self, member):
        # The scholarship is a single lump-sum award per household; all of
        # the value is reported at the household level via household_value().
        return 0
