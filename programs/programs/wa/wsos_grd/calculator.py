import programs.programs.messages as messages
from programs.programs.calc import Eligibility, MemberEligibility, ProgramCalculator


class WaWsosGrd(ProgramCalculator):
    """
    Washington State Opportunity Scholarship — Graduate Scholarship (GRD) track.

    Up to $25,000 over 3 years (capped at $6,250/term, applied after other financial
    aid up to Cost of Attendance) for nurse practitioner graduate students (DNP/MSN)
    enrolled in approved programs at eligible Washington universities who plan to
    practice in a Washington Medically Underserved Area (MUA) or Health Professional
    Shortage Area (HPSA) for at least two years after graduation.

    Screener-checkable criteria (what this calculator actually screens):
      - Washington residency: implicit via the `wa` white label
      - At least one household member is a student (`member.student == True`)
      - Household annual income at or below 155% Washington State Median Family Income
        (MFI) for the household size

    Inclusivity assumptions (per spec.md — fields the screener does not collect; we
    assume met for any student respondent and surface the program with the caveats
    in `description`):
      - Enrolled in an eligible DNP or MSN program
      - At an eligible WA institution (Gonzaga, Pacific Lutheran, Seattle U,
        UW Seattle, WSU Spokane / Tri-Cities / Vancouver / Yakima)
      - Specialty is AGNP-PC, FNP, PMHNP, or PNP-PC
      - Has completed >= 1 semester or 2 quarters
      - Has >= 75% of clinical hours remaining
      - Enrolled full-time (DNP) or part-time (MSN) and in good academic standing
      - Intends to practice in a WA MUA or HPSA for >= 2 years post-graduation

    Income gate uses the upper 155% MFI cutoff. WSOS GRD has a two-tier income test:
    automatic eligibility at or below 125% MFI, expanded eligibility 126-155% MFI
    contingent on demonstrating financial hardship (student loan debt > $30K, prior
    use of income-based programs, or significant economic hardship). The screener
    cannot verify hardship factors, so per spec we use 155% as the calculator cutoff
    and rely on the program description to surface the hardship caveat for the
    126-155% band.

    Sources:
      - https://waopportunityscholarship.org/applicants/grd/#Eligibility
      - https://waopportunityscholarship.org/wp-content/uploads/2025/12/GRD-C7-MFI-Chart-1-1.pdf
        (Official 2026 WSOS GRD MFI Chart)
    """

    # 2026 WSOS GRD MFI thresholds in dollars per year (155% MFI = upper cutoff used
    # by the screener). Per-household-size lookup table sourced from the official
    # WSOS GRD MFI Chart linked above. The 125% values are kept in the spec for
    # reference; we do not need them in code because the screener cannot distinguish
    # the 125%/155% bands (no hardship verification).
    MFI_155_BY_SIZE = {
        1: 112_500,
        2: 146_500,
        3: 181_500,
        4: 216_000,
        5: 250_500,
        6: 285_000,
    }

    # Spec only publishes sizes 1-6. For larger households, extend by the average
    # increment observed in the published table (~$34,500 per additional person at
    # 155% MFI). Validations only cover sizes 1 and 3 today; this fallback exists
    # so a 7+ person household does not crash and gets a reasonable upper bound.
    MFI_155_PER_EXTRA_PERSON_ABOVE_TABLE = 34_500

    amount = 25_000  # lump-sum scholarship per household

    dependencies = ["income_amount", "income_frequency", "household_size"]

    def income_limit_155(self) -> int:
        """
        Annual 155% MFI income cap for the household's size, with linear extension
        for sizes larger than the published table.
        """
        size = self.screen.household_size
        if size in self.MFI_155_BY_SIZE:
            return self.MFI_155_BY_SIZE[size]
        return self.MFI_155_BY_SIZE[6] + (size - 6) * self.MFI_155_PER_EXTRA_PERSON_ABOVE_TABLE

    def household_eligible(self, e: Eligibility):
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))
        income_limit = self.income_limit_155()
        e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))

    def member_eligible(self, e: MemberEligibility):
        e.condition(bool(e.member.student))

    def household_value(self) -> int:
        return self.amount

    def member_value(self, member):
        # The scholarship is a single lump-sum award per household; all of the
        # value is reported at the household level via household_value().
        return 0
