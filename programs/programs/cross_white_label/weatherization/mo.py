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
      * LIHEAP income-eligibility (Criterion 1c) and USDA means-tested program
        eligibility (Criterion 1e), both elected by Missouri, have no screener
        field. `mo_liheap` exists but is off the has-benefits step, so LIHEAP
        receipt is unreportable.
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

    #: Section D.1's age threshold.
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
        # Criteria 1b and 1d bypass the income test entirely
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

        Under 18 is the exact test. `student_full_time` stands in for the
        "full-time high school student" clause, which MFB cannot distinguish
        from full-time college enrollment — so an over-18 full-time college
        student's wages come out too. That errs toward admitting households,
        which is the safe direction for a program whose alternative pathways
        are themselves unscreenable. A member of unknown age is treated as an
        adult: the disregard is granted on proof of age, not assumed without it.
        """
        age = member.calc_age()
        if age is not None and age < self.minor_age:
            return True

        return bool(member.student_full_time)

    def _categorically_eligible(self) -> bool:
        """Whether a non-income pathway admits the household outright."""
        cash_assistance = self.screen.calc_gross_income("yearly", list(self.cash_assistance_income_types)) > 0

        # Section 8 is the HCV program (base_program "section_8"); the bare
        # has_benefit("section_8") is a dead check — no row carries that
        # name_abbreviated. No Missouri HCV row exists yet, so this is wired
        # ahead of the data rather than reading it.
        section_8 = self.screen.has_base_benefit("section_8")

        return cash_assistance or section_8
