from typing import ClassVar

import programs.framework.eligibility_messages as messages
from programs.framework.base import Eligibility, ProgramCalculator
from screener.models import HouseholdMember


class MoWap(ProgramCalculator):
    """MO Weatherization Assistance Program — free home energy upgrades
    (insulation, air sealing, heating/cooling repair) delivered by Missouri's
    local weatherization agencies under a DNR subgrant.

    Eligibility (see specs/mo.md) is an OR over income pathways:
      * Criterion 1a: countable annual income at or below 200% of the WAP
        poverty guideline for the household size. DOE publishes its own table
        (WPN 25-3) rather than deferring to the live HHS guidelines, and the
        two can differ by effective date — the program row's `year` pin is what
        holds this calculator on the table DOE has actually issued. Pinned to
        2025, whose 200% figures are the WPN 25-3 attachment verbatim
        ($31,300 / $42,300 / $53,300 / $64,300 … +$11,000 per person past 8).
      * Criterion 1b: cash-assistance categorical eligibility. 10 CFR 440.3
        admits a household paid Title IV (TANF) or Title XVI (SSI) cash
        assistance in the preceding twelve months, so a current `sSI` or
        `cashAssistance` income stream is sufficient on its own and bypasses
        the income test.
      * Criterion 1c: LIHEAP categorical eligibility, which Missouri elected
        under 10 CFR 440.22(a)(3) — a household already deemed income eligible
        for LIHEAP may use that as verification of income. Missouri's LIHEAP
        standard is 60% SMI, which sits above 200% of poverty at every household
        size, so the federal proviso ("provided that such basis is at least 200
        percent of the poverty level") is satisfied and this genuinely widens
        eligibility rather than duplicating Criterion 1a.
      * Criterion 1d: HUD means-tested categorical eligibility, which Missouri
        elected under WPN 22-5. Section 8 / HCV receipt is the one HUD program
        MFB records, matched structurally via `has_base_benefit` so a Missouri
        HCV row activates the pathway the day one is added.

    Countable income for Criterion 1a follows WPN 25-3's "Definition of Income"
    attachment rather than plain gross income — see `excluded_income_types` and
    `minor_excluded_income_types` for what comes out and why.

    Handled outside the calculator:
      * Criterion 3 (qualified aliens) — the program's `legal_status_required`
        config, which commits to citizen / refugee / gc_5plus / gc_5less /
        otherWithWorkPermission and excludes the generic `non_citizen`.
      * Missouri residency — enforced at the screener's ZIP step, so a
        non-Missouri household never reaches this calculator.
      * Priority categories (10 CFR 440.16(b): elderly, disabled, families with
        children, high energy use, high energy burden). These set service order,
        not eligibility or value.

    Data gaps, all handled inclusively — the household keeps every other
    pathway and none of these is treated as disproving eligibility:
      * USDA means-tested program eligibility (Criterion 1e), also elected by
        Missouri, has no screener field at all.
      * Criterion 1c reads *reported LIHEAP receipt*, which is narrower than the
        rule: a household income-eligible for LIHEAP but not enrolled satisfies
        Missouri's plan and is invisible here. Receipt is the inclusive half —
        it admits households the income test would reject, and never rejects one
        the income test would admit.
      * Section D.1's "full-time high school student" clause is honoured only at
        age 18 (see `_income_excluded_as_minor`), so a 19-plus high-school
        student's earned income is counted. MFB collects no level of schooling to
        do better, and past 18 the flag reaches adult education and college far
        more often than high school.
      * The twelve-month cash-assistance lookback: only current receipt is
        visible, so a household paid SSI or TANF earlier in the year reads as
        not having it.
      * HUD programs other than Section 8 (CDBG, HOME, OLHCHH) have no MFB
        representation at all, and Missouri has no `section_8`-base-program row
        today, so Criterion 1d cannot fire for a Missouri household yet.
      * Dwelling type, prior-weatherization history (the 15-year re-weatherization
        bar), and local agency service area are not collected.

    SNAP is deliberately absent. 10 CFR 440.22(a)(2) names Title IV and Title
    XVI only, and Missouri's Master File does not list SNAP as a basis — so
    unlike `tx_wap`, `cowap` and `wa_wap`, SNAP receipt does not qualify here.

    Benefit value is a flat $370, DNR's published average annual heating and
    cooling saving per weatherized house (PUB2832). `value_format:
    estimated_annual` on the program row, so this is an annual savings estimate
    rather than a payment or the cost of the work.
    """

    program_code = "mo_wap"

    #: Average annual energy-cost saving per weatherized home, not a payment.
    amount = 370

    #: DOE's WAP guideline is 200% of poverty; the year pin, not this multiple,
    #: is what selects WPN 25-3's table.
    fpl_percent = 2

    #: Excluded from countable income for every member.
    #:
    #: `selfEmployment`, `rental` and `boarder` because WPN 25-3 counts those
    #: *net* of business, farm and property expenses (B.2, B.6) and MFB collects
    #: no such expense — using the reported gross as net would overstate income
    #: and wrongly exclude households. `investment` because MFB's single figure
    #: conflates countable interest and dividends (B.5) with excluded capital
    #: gains (C.1), with no way to split them. `childSupport` because Section E
    #: excludes it on both sides, and `gifts` per C.6.
    excluded_income_types: ClassVar[tuple[str, ...]] = (
        "selfEmployment",
        "rental",
        "boarder",
        "investment",
        "childSupport",
        "gifts",
    )

    #: Also excluded for a member whose income WPN 25-3 Section D.1 disregards:
    #: "earned income or unemployment compensation for minors under the age of
    #: 18 (or full-time high school students)". Their unearned income — SSI, a
    #: survivor benefit — still counts.
    minor_excluded_income_types: ClassVar[tuple[str, ...]] = ("wages", "selfEmployment", "unemployment")

    #: Section D.1's age threshold. Under this, the disregard is outright; at
    #: exactly this age it needs the full-time student flag; above it, never.
    minor_age = 18

    #: Income streams that evidence Criterion 1b. `cashAssistance` is MFB's
    #: TANF grant (Title IV); `sSI` is Title XVI.
    cash_assistance_income_types: ClassVar[tuple[str, ...]] = ("sSI", "cashAssistance")

    dependencies: ClassVar[list[str]] = [
        "household_size",
        "income_amount",
        "income_frequency",
    ]

    def household_eligible(self, e: Eligibility):
        # Criteria 1b, 1c and 1d bypass the income test entirely
        if self._categorically_eligible():
            e.condition(True, messages.presumed_eligibility())
            return

        # Criterion 1a
        income = self._countable_income()
        income_limit = self._income_limit()
        e.condition(income <= income_limit, messages.income(income, income_limit))

    def _income_limit(self) -> int:
        """200% of the WAP poverty guideline for the household size, extended by
        the table's per-additional-person increment past size 8."""
        household_size = self.screen.household_size or 1

        return int(self.fpl_percent * self.program.year.get_limit(household_size))

    def _countable_income(self) -> float:
        """Annual gross income less WPN 25-3's exclusions.

        Rounded to cents rather than truncated: the boundary is inclusive, so a
        household $0.50 over its limit must fail, and `int()` would admit it.
        """
        total = 0.0

        for member in self.screen.household_members.all():
            exclude = list(self.excluded_income_types)
            if self._income_excluded_as_minor(member):
                exclude += list(self.minor_excluded_income_types)
            total += member.calc_gross_income("yearly", ["all"], exclude=exclude)

        return round(total, 2)

    def _income_excluded_as_minor(self, member: HouseholdMember) -> bool:
        """Whether Section D.1 disregards this member's earned income and
        unemployment compensation.

        Under 18 is the exact test. Section D.1's "(or full-time high school
        students)" clause is honoured only at exactly 18, because MFB collects
        no level of schooling — `student_full_time` is the same flag a full-time
        college or graduate student sets. Reading it at every age would exclude
        a 45-year-old's wages outright, and past 18 the population it would
        actually reach is adult education or a GED rather than high school. So
        the clause is capped at the one age where "still in high school" is the
        ordinary reading, and 19-plus high-school students — a rare enough case
        to be worth the false negative — count their earned income.

        Read as `student and student_full_time`, matching
        `FullTimeCollegeStudentDependency`. `student_full_time` is only asked
        once `student` is ticked, but nothing enforces that server-side: the
        frontend clears it only on a student→non-student transition and only
        outside the energy-calculator flow, and a direct API write can set it
        with `student` false or null. The conjunction keeps a non-student's
        wages counted.

        A member of unknown age is treated as an adult: the disregard is
        granted on proof of age, not assumed without it.
        """
        age = member.calc_age()
        if age is None:
            return False

        if age < self.minor_age:
            return True

        if age == self.minor_age:
            return bool(member.student and member.student_full_time)

        return False

    def _categorically_eligible(self) -> bool:
        """Whether a non-income pathway admits the household outright."""
        cash_assistance = self.screen.calc_gross_income("yearly", list(self.cash_assistance_income_types)) > 0

        # Criterion 1c. `mo_liheap` is the Missouri variant; read structurally so
        # any future LIHEAP row (or a rename) is matched without editing this.
        liheap = self.screen.has_base_benefit("liheap")

        # Section 8 is the HCV program (base_program "section_8"); the bare
        # has_benefit("section_8") is a dead check — no row carries that
        # name_abbreviated. No Missouri HCV row exists yet, so this is wired
        # ahead of the data rather than reading it.
        section_8 = self.screen.has_base_benefit("section_8")

        return cash_assistance or liheap or section_8
