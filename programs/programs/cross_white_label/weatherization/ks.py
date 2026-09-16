from typing import ClassVar

import programs.framework.eligibility_messages as messages
from programs.framework.base import Eligibility, ProgramCalculator
from screener.models import HouseholdMember


class KsWap(ProgramCalculator):
    """KS Weatherization Assistance Program — free home energy upgrades
    (insulation, air sealing, heating repair) delivered by Kansas's local
    weatherization subrecipients under a Kansas Housing Resources Corporation
    subgrant.

    Eligibility (see specs/ks.md) is `(criterion 1 OR criterion 3) AND
    criterion 4 AND criterion 5`. Categorical receipt substitutes for the
    income test; it is never ANDed with it.

      * Criterion 1: countable annual income at or below 200% of the federal
        poverty guideline for the household size. The program row's `year` pin
        selects the guideline edition — 2026, whose 200% figures reproduce the
        table KHRC prints on its own application exactly, at every size from 1
        to 16 ($31,920 / $43,280 / $54,640 / $66,000 … $202,320). Only sizes 1
        through 8 are reachable in practice: the screener caps household size
        at 8, and that cap is not per-white-label. The threshold arithmetic
        above 8 is correct and tested, but no Kansas household can currently
        reach it.
      * Criterion 2 defines what "income" means for criterion 1: gross cash
        receipts less the exclusions the current DOE Weatherization Program
        Notice lists. See `excluded_income_types` and
        `student_excluded_income_types`.
      * Criterion 3: categorical income eligibility. Kansas admits a household
        currently receiving SSI, TANF (which Kansas administers as TAF) or
        LIEAP, and has also taken both DOE expansions to HUD and USDA
        means-tested programs — of which Section 8 / HCV is the only one MFB
        records. Any one of these bypasses the income test outright.
      * Criterion 6 fixes the unit both criteria measure over: WAP's family
        unit is everyone living in the dwelling. `household_size` and the
        entered member list are used as entered, never reconstructed from
        tax-unit or relationship fields — the Kansas LIEAP convention.

    Handled outside the calculator:
      * Criterion 4 (at least one citizen or Qualified Alien resides at the
        address) — the program's `legal_status_required` config, which commits
        to citizen / gc_5plus / gc_5less / refugee / otherWithWorkPermission and
        excludes the generic `non_citizen`.
      * Criterion 5 (the dwelling is in Kansas) — white-label routing. Each
        subrecipient must serve the whole of its own territory, so service area
        adds no restriction inside Kansas.
      * Priority order (emergencies; then age 60+, disabled, families with
        children 18 or under; then high energy use or burden). These set the
        order of a waiting list among households already eligible, not whether
        one qualifies.

    Data gaps, none of which the calculator treats as disproving eligibility:
      * The HUD and USDA categorical routes beyond Section 8 / HCV, and cash
        assistance received earlier in the preceding twelve months, are
        affirmative pathways MFB cannot observe. Absence of a record is not
        read as proof the pathway does not apply — but neither is it inferred
        true, which would resolve the eligibility disjunction for every Kansas
        household and reduce criterion 1 to dead code. They are disclosed to
        the user in the program description instead.
      * `selfEmployment`, `rental`, `boarder` and `investment` are dropped in
        full because MFB cannot produce the net figures the notice counts (see
        `excluded_income_types`). This is the one inclusive proxy that can
        produce an actionable false positive.
      * The full-time high-school-student disregard is applied to any full-time
        student regardless of age, because MFB records no level of schooling.
        Over-excluding lowers countable income, so it can only widen results.
      * Income is compared as the annualized current recurring figure MFB
        holds. `IncomeStream` carries no dates, so Kansas's twelve-month and
        three-month-annualized methods cannot be reproduced.
      * Occupancy of the dwelling applied for, dwelling type, and the 15-year
        re-weatherization bar are not collected at all.

    SNAP is deliberately absent. Kansas's categorical list names SSI, TANF and
    LIEAP, and the DOE expansions reach HUD and USDA programs — not SNAP. So
    unlike `tx_wap`, `cowap` and `wa_wap`, SNAP receipt does not qualify here.

    Benefit value is a flat $7,475 — Kansas's most recently published average
    program-operations cost per dwelling unit ($7,474.93, 2025 state plan),
    rounded to the dollar. `value_format: lump_sum` on the program row: the
    measures are installed once, and this estimates the in-kind work rather
    than promising a payment.
    """

    program_code = "ks_wap"

    #: Kansas's average cost per weatherized dwelling unit — an estimate of the
    #: in-kind work, delivered once. Not a payment and not a ceiling: the
    #: $8,550 figure in the same state plan caps the grantee's statewide
    #: average, not what one household receives.
    amount = 7_475

    #: 42 U.S.C. § 6862(7)(A) and 10 CFR 440.22(a)(1). The `year` pin on the
    #: program row, not this multiple, is what selects the guideline edition.
    fpl_percent = 2

    #: Excluded from countable income for every member.
    #:
    #: `childSupport` because DOE WPN 25-3 Section E excludes it on both sides,
    #: and `gifts` per Section C — those two are the notice's own policy
    #: exclusions. The rest are MFB inclusive proxies standing in for figures
    #: MFB cannot compute: `selfEmployment`, `rental` and `boarder` because the
    #: notice counts those *net* of business, farm and property expenses (B.2,
    #: B.6) and MFB collects no such expense; `investment` because MFB's single
    #: figure fuses countable dividends and interest (B.5) with excluded
    #: capital gains (C.1) and cannot split them.
    #:
    #: `alimony` is countable (B.3) and deliberately stays in.
    excluded_income_types: ClassVar[tuple[str, ...]] = (
        "childSupport",
        "gifts",
        "selfEmployment",
        "rental",
        "boarder",
        "investment",
    )

    #: Also excluded for a member WPN 25-3 Section D.1 disregards: "earned
    #: income or unemployment compensation for minors under the age of 18 (or
    #: full-time high school students)". Their unearned income — SSI, a
    #: survivor benefit — still counts. `selfEmployment` is the third earned
    #: stream and is already excluded for everyone above.
    student_excluded_income_types: ClassVar[tuple[str, ...]] = ("wages", "unemployment")

    #: Section D.1's age threshold. Under this the disregard is outright,
    #: whatever the member's student status.
    minor_age = 18

    #: Income streams that evidence a categorical route on their own, mapped to
    #: the base program each one stands for. The stream test is a backstop to
    #: the current-benefit row, not a replacement for it: the single-benefit
    #: toggle endpoint does not re-derive the current-benefit row, so a screen
    #: can carry the stream without the row. For TANF it is doing the whole job
    #: — MFB files TANF dollars under `cashAssistance` and never under `tanf`.
    categorical_income_types: ClassVar[tuple[str, ...]] = ("sSI", "cashAssistance")

    #: Base programs whose current receipt admits the household outright.
    #: Matched structurally so any white-label variant counts: `ks_ssi`,
    #: `ks_tanf` and `ks_lieap` today, and a Kansas voucher row the day one is
    #: added. `section_8` is wired ahead of the data — Kansas has no HCV row, so
    #: it changes no current verdict.
    categorical_base_programs: ClassVar[tuple[str, ...]] = ("ssi", "tanf", "liheap", "section_8")

    dependencies: ClassVar[list[str]] = [
        "household_size",
        "income_amount",
        "income_frequency",
    ]

    def household_eligible(self, e: Eligibility):
        # Criterion 3 substitutes for the income test rather than adding to it.
        if self._categorically_eligible():
            e.condition(True, messages.presumed_eligibility())
            return

        # Criterion 1
        income_limit = self._income_limit()

        if income_limit is None:
            # household_size is nullable, and the limit is indexed to it. With
            # no size there is no row to compare against, so the criterion is
            # met rather than guessed at. No message: naming a $0 limit the
            # household did not have to clear would misreport why it passed.
            # Unreachable in production — household_size is a declared
            # dependency, so can_calc() drops the program first.
            e.condition(True)
            return

        income = self._countable_income()
        e.condition(income <= income_limit, messages.income(income, income_limit))

    def _income_limit(self) -> int | None:
        """200% of the federal poverty guideline for the household size, or
        None when no size was entered.

        Read through ``get_limit`` rather than ``as_dict()[household_size]``:
        the dict holds explicit rows only to size 8, and Kansas publishes its
        table to 16. The helper extends past 8 by the per-additional-person
        amount, which is exactly how KHRC's own printed table is built — its
        sizes 9 through 16 are $122,800 through $202,320, and 200% of the 2026
        guideline reproduces every one of them.

        Sizes above 8 are not reachable today: the screener's household-size
        step caps at 8 for every white label. ``get_limit`` is still the right
        call rather than clamping to 8 — there is no hardcoded table here to
        truncate, a clamp would silently understate the limit for a large
        household if the cap is ever raised, and the extrapolation is already
        the published Kansas figure.
        """
        household_size = self.screen.household_size
        if household_size is None:
            return None

        return int(self.fpl_percent * self.program.year.get_limit(household_size))

    def _countable_income(self) -> float:
        """Annual gross income less WPN 25-3's exclusions, summed across the
        household as entered.

        Rounded to cents rather than truncated: the boundary is inclusive, so a
        household $0.50 over its limit must fail, and ``int()`` would floor it
        back onto the limit and admit it. Rounding at cents also absorbs the
        float artifacts a Decimal-to-float sum leaves behind, which would
        otherwise flip an exactly-at-limit household.
        """
        total = 0.0

        for member in self.screen.household_members.all():
            exclude = list(self.excluded_income_types)
            if self._earned_income_disregarded(member):
                exclude += list(self.student_excluded_income_types)
            total += member.calc_gross_income("yearly", ["all"], exclude=exclude)

        return round(total, 2)

    def _earned_income_disregarded(self, member: HouseholdMember) -> bool:
        """Whether Section D.1 disregards this member's earned income and
        unemployment compensation.

        Under 18 is the exact test and needs nothing else. The clause's "(or
        full-time high school students)" half is honoured at any age, because
        MFB records no level of schooling — `student_full_time` is the same
        flag a full-time college student sets. Applying it too widely can only
        lower countable income, so it widens results rather than producing a
        false negative (Data Gap 6).

        Read as `student and student_full_time`, matching
        `FullTimeCollegeStudentDependency`. `student_full_time` is only asked
        once `student` is ticked, but nothing enforces that server-side, so the
        conjunction keeps a non-student's wages counted.

        A member of unknown age with no student flag is treated as an adult:
        the disregard is granted on proof, not assumed without it.
        """
        if bool(member.student and member.student_full_time):
            return True

        age = member.calc_age()
        if age is None:
            return False

        return age < self.minor_age

    def _categorically_eligible(self) -> bool:
        """Criterion 3 — whether a non-income route admits the household
        outright, by either the current-benefit row or the income stream that
        evidences the same receipt."""
        for base_program in self.categorical_base_programs:
            if self.screen.has_base_benefit(base_program):
                return True

        return self.screen.calc_gross_income("yearly", list(self.categorical_income_types)) > 0
