import programs.programs.messages as messages
from programs.programs.calc import Eligibility, MemberEligibility, ProgramCalculator


class WaWsosCts(ProgramCalculator):
    """
    Washington State Opportunity Scholarship — Career & Technical Scholarship (CTS).

    CTS supports students in approved associate degree, certificate, and apprenticeship
    programs at Washington community/technical colleges (and listed apprenticeship
    sponsors). Unlike BaS/GRD, WSOS does not publish a single household benefit lump sum;
    awards are up to $1,500/quarter (with part-time proration) after other aid and COA.
    This calculator returns eligibility only — benefit value stays 0.

    Screener-checkable criteria:
      - Washington residency: implicit via the `wa` white label (ZIP/county).
      - At least one household member is a student (`member.student is True`), used as
        a proxy for enrollment in an eligible CTS pathway (per spec inclusivity note).
      - Household annual gross income at or below 125% Washington State Median Family
        Income (MFI) for household size. CTS uses only this tier (no GRD-style
        expanded band above 125% MFI).

    Inclusivity assumptions (screener gaps; assume met for student respondents — see
    program `description` for applicant-facing detail):
      - Enrolled or planning eligible program/institution; not pursuing/immediate
        bachelor's (BaS applies instead); high school credential by June of application
        year; credit/enrollment intensity rules (e.g. ≥3 credits/term).
    """

    # 2026 WSOS CTS 125% MFI ($/year) by household size — official CTS MFI chart
    # (same published 125% tier values as BaS for sizes 1–6).
    MFI_125_BY_SIZE = {
        1: 90_500,
        2: 118_000,
        3: 146_500,
        4: 174_500,
        5: 202_000,
        6: 230_000,
    }

    MFI_125_PER_EXTRA_PERSON_ABOVE_TABLE = 28_000

    amount = 0

    dependencies = ["income_amount", "income_frequency", "household_size"]

    def income_limit_125(self) -> int:
        size = self.screen.household_size
        if size in self.MFI_125_BY_SIZE:
            return self.MFI_125_BY_SIZE[size]
        return self.MFI_125_BY_SIZE[6] + (size - 6) * self.MFI_125_PER_EXTRA_PERSON_ABOVE_TABLE

    def household_eligible(self, e: Eligibility):
        """
        Apply the 125% MFI income gate against household annual gross income.

        `calc_gross_income` can return a float; compare at full precision so a
        household fractionally above the cap is excluded instead of being
        floored onto an inclusive boundary. `messages.income` rounds for display.
        Same approach as `WaWsosBas` / `WaWsosGrd`.
        """
        gross_income = self.screen.calc_gross_income("yearly", ["all"])
        income_limit = self.income_limit_125()
        e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))

    def member_eligible(self, e: MemberEligibility):
        """
        At least one member with `student is True` qualifies the household CTS path.

        `bool(...)` maps the BooleanField tri-state (`True` / `False` / `None`) so
        only explicit student yes counts, matching `WaWsosBas`.
        """
        e.condition(bool(e.member.student))

    def household_value(self) -> int:
        return 0

    def member_value(self, member):
        return 0
