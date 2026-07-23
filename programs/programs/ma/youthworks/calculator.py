from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility
import programs.programs.messages as messages


class MaYouthworks(ProgramCalculator):
    """
    YouthWorks (MA)

    Commonwealth Corporation's YouthWorks connects Massachusetts youth ages 14–25
    with paid summer and school-year job placements, plus job-readiness training and
    mentorship, run locally through the 16 MassHire workforce regions.

    Eligibility criteria that can be verified:
    - Age 14–25 (per member)
    - Family gross income ≤ 200% of the Federal Poverty Guidelines. The RFP mandates
      the 2025 FPL tables, so this program's config pins `year: "2025"`.
    - Massachusetts residency — handled upstream by white-label routing (the program
      operates statewide across all 16 MassHire regions, so no sub-state/geographic
      check is applied here).

    Data gap (inclusivity assumption applied):
    - Criterion 4 (risk/demographic factor: e.g. low-income, housing insecurity,
      disability, foster care, limited English) is not collected by the screener.
      Given the breadth of the 11 qualifying factors and the program's focus on
      low-income youth, all users meeting age + income + residency are assumed to
      qualify. See spec.md Criterion 4.

    Benefit value: $2,400/year per eligible youth (160 hrs × $15/hr MA minimum wage,
    a conservative Cycle 1 summer-placement estimate). YouthWorks is a per-person
    placement program, so each eligible youth receives their own placement and values
    sum across eligible members (member_amount).

    Source: https://commcorp.org/program/youthworks/ (see spec.md for full sourcing)
    """

    min_age = 14
    max_age = 25
    fpl_percent = 2
    # $2,400/yr per eligible youth (already annual; 160 hrs × $15/hr).
    member_amount = 2_400
    dependencies = [
        "age",
        "household_size",
        "income_amount",
        "income_frequency",
    ]

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # Age 14–25 at the start of programming.
        age = member.age
        e.condition(age is not None and self.min_age <= age <= self.max_age)

    def household_eligible(self, e: Eligibility):
        # Family gross income must not exceed 200% of the (2025) Federal Poverty Guidelines.
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))
        income_limit = int(self.fpl_percent * self.program.year.get_limit(self.screen.household_size))
        e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))
