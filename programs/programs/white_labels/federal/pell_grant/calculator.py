from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from functools import cached_property
from typing import Iterable, Optional

from programs.framework.base import MemberEligibility, ProgramCalculator
from screener.models import HouseholdMember

#: The award year's first calendar year. A student is independent at 24 by December 31 of it.
AWARD_YEAR = 2026

MAX_PELL = 7_395
MIN_PELL = 740
#: An index at or above twice the maximum award bars any award.
SAI_CUTOFF = 2 * MAX_PELL

#: Income types left out of adjusted gross income (IRS Publication 525). Child support is left
#: out of income but counted with assets in the Student Aid Index.
AGI_EXCLUDED_TYPES = ("sSI", "cashAssistance", "cashAssistanceOther", "childSupport", "gifts", "workersComp", "veteran")

#: A member with one of these relationships to the head is a child of the head.
CHILD_RELATIONSHIPS = ("child", "stepChild", "fosterChild", "grandChild")
SPOUSE_RELATIONSHIPS = ("spouse", "domesticPartner")

#: Maximum-award line, as a multiple of the poverty line: (single parent, otherwise).
MAX_AWARD_MULTIPLE = (Decimal("2.25"), Decimal("1.75"))

# Payroll tax allowance (SAI guide Tables A1, B1 and C1).
HI_RATE = Decimal("0.0145")
HI_HIGH_RATE = Decimal("0.0235")
HI_THRESHOLD = (Decimal(250_000), Decimal(200_000))  # (joint, single)
OASDI_RATE = Decimal("0.062")
OASDI_BASE = (Decimal(337_200), Decimal(168_600))  # (joint, single)

INCOME_ASSESSMENT = Decimal("0.50")
EEA_RATE = Decimal("0.35")
EEA_CAP = 5_000

# Formula A, dependent students.
ASSET_CONVERSION_A = Decimal("0.12")
IPA_DEPENDENT_STUDENT = 11_770
#: Table A2 by family size, and the amount for each person past the last row.
IPA_FAMILY_A2 = ({2: 29_190, 3: 36_330, 4: 44_880, 5: 52_950, 6: 61_930}, 6_990)

# Formula B, independent students without dependents.
ASSET_CONVERSION_B = Decimal("0.20")
IPA_SINGLE = 18_310
IPA_MARRIED_B = 29_350

# Formula C, independent students with dependents.
ASSET_CONVERSION_C = Decimal("0.07")
IPA_MARRIED_C2 = ({3: 57_730, 4: 71_280, 5: 84_120, 6: 98_370}, 11_110)
IPA_SINGLE_PARENT_C3 = ({2: 54_950, 3: 68_430, 4: 84_480, 5: 99_700, 6: 116_590}, 13_180)

#: Tables A5 and C6, which are the same: (upper bound of the bracket, base, rate on the excess
#: over the previous bound). Below -$8,500 the contribution is a flat -$1,870.
AAI_FLOOR = (-8_500, -1_870)
AAI_BRACKETS = (
    (21_800, 0, Decimal("0.22")),
    (27_300, 4_796, Decimal("0.25")),
    (32_800, 6_171, Decimal("0.29")),
    (38_400, 7_766, Decimal("0.34")),
    (43_900, 9_670, Decimal("0.40")),
    (None, 11_870, Decimal("0.47")),
)


def whole(amount: Decimal) -> int:
    """Round to three decimals, then to the dollar, half away from zero, as the SAI guide does."""
    return int(amount.quantize(Decimal("0.001"), ROUND_HALF_UP).quantize(Decimal("1"), ROUND_HALF_UP))


def round_to_5(amount: int) -> int:
    return int((Decimal(amount) / 5).quantize(Decimal("1"), ROUND_HALF_UP)) * 5


def allowance(table: tuple[dict[int, int], int], family_size: int) -> int:
    """An income protection allowance, extended past the table's last row by its per-person amount."""
    rows, additional = table
    smallest, largest = min(rows), max(rows)
    if family_size <= largest:
        return rows[max(family_size, smallest)]

    return rows[largest] + additional * (family_size - largest)


def contribution_from_aai(aai: int) -> int:
    """Tables A5 and C6."""
    floor, floor_contribution = AAI_FLOOR
    if aai < floor:
        return floor_contribution

    lower = 0
    for upper, base, rate in AAI_BRACKETS:
        if upper is None or aai <= upper:
            return base + whole(rate * (aai - lower))
        lower = upper

    raise AssertionError("unreachable: the last bracket is open")


def payroll_allowance(earned: Decimal, joint: bool) -> int:
    """Medicare and Social Security tax on earned income, each rounded to the dollar."""
    earned = max(earned, Decimal(0))
    hi_threshold = HI_THRESHOLD[0] if joint else HI_THRESHOLD[1]
    oasdi_base = OASDI_BASE[0] if joint else OASDI_BASE[1]

    hi = HI_RATE * min(earned, hi_threshold) + HI_HIGH_RATE * max(earned - hi_threshold, Decimal(0))
    oasdi = OASDI_RATE * min(earned, oasdi_base)
    return whole(hi) + whole(oasdi)


def employment_expense_allowance(income: Decimal) -> int:
    return max(0, min(whole(EEA_RATE * income), EEA_CAP))


@dataclass(frozen=True)
class Family:
    """Who a student's need is measured on.

    `contributors` are the people whose income counts: the student and their spouse for an
    independent student, the parents for a dependent one.
    """

    dependent: bool
    contributors: tuple[HouseholdMember, ...]
    married: bool
    has_children: bool
    family_size: int

    @property
    def single_parent(self) -> bool:
        if self.dependent:
            return len(self.contributors) == 1

        return self.has_children and not self.married

    @property
    def min_award_multiple(self) -> Decimal:
        """The minimum-award line, as a multiple of the poverty line."""
        if self.dependent:
            return Decimal("3.25") if self.single_parent else Decimal("2.75")
        if self.single_parent:
            return Decimal("4.00")
        if self.has_children:
            return Decimal("3.50")
        return Decimal("2.75")


class PellGrant(ProgramCalculator):
    """
    Federal Pell Grant, valued per student for the 2026-27 award year. Rules and figures:
    program-ops `programs/white_labels/federal/pell_grant/federal_pell_grant_spec.md`.

    Each student's need is measured on their own income (and their spouse's) when independent,
    and on their parents' when dependent. A student is independent at 24 by the end of 2026,
    when married (a `spouse` or `domesticPartner`), with a child in the household, or when ever
    in foster care. A dependent student whose parents can't be found in the household gets
    nothing.

    The award is the maximum when income is above zero and within 175% of the poverty line
    (225% for a single parent); otherwise the maximum less the Student Aid Index, if that is at
    least the minimum; otherwise the minimum when income is within 275% to 400% of the poverty
    line by family type. An index at or above $14,790 bars both reduced awards. The index is the
    SAI guide's Formula A, B or C, fed only by income, child support, household assets and
    family size; the other FAFSA inputs aren't collected.

    Deviations: income is current gross income less the types outside AGI, not the 2024 return;
    the poverty line is the 2026 48-state guideline everywhere, since no white label serves
    Alaska or Hawaii; the award assumes full-time enrollment with no cost-of-attendance cap.
    Citizenship is the program's `legal_status_required`.
    """

    program_code = "federal_pell_grant"

    dependencies = [
        "age",
        "relationship",
        "student",
        "household_size",
        "income_type",
        "income_amount",
        "income_frequency",
    ]

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member
        e.condition(member.student is True)
        if e.eligible:
            e.condition(self.award(member) > 0)

    def member_value(self, member: HouseholdMember) -> int:
        return self.award(member)

    def award(self, student: HouseholdMember) -> int:
        """The student's estimated award, or 0 when they get none."""
        if student.id not in self._awards:
            self._awards[student.id] = self._award(student)

        return self._awards[student.id]

    @cached_property
    def _awards(self) -> dict[int, int]:
        return {}

    def _award(self, student: HouseholdMember) -> int:
        family = self.family(student)
        if family is None:
            return 0

        agi = self._agi(family.contributors)
        poverty_line = Decimal(self.program.year.get_limit(family.family_size))
        max_multiple = MAX_AWARD_MULTIPLE[0] if family.single_parent else MAX_AWARD_MULTIPLE[1]

        if 0 < agi <= whole(max_multiple * poverty_line):
            return MAX_PELL

        sai = self.student_aid_index(student, family)
        if sai >= SAI_CUTOFF:
            return 0

        # Compared with the minimum before rounding to $5.
        calculated = MAX_PELL - max(sai, 0)
        if calculated >= MIN_PELL:
            return round_to_5(calculated)

        if agi <= whole(family.min_award_multiple * poverty_line):
            return MIN_PELL

        return 0

    # Who counts

    def family(self, student: HouseholdMember) -> Optional[Family]:
        """The student's family for the need test, or None for a dependent student with no parent found."""
        spouses = self._spouses(student)
        children = self._children(student)
        married = len(spouses) > 0
        age = student.age_at_end_of_year(AWARD_YEAR)
        independent = (age is not None and age >= 24) or married or bool(children) or student.was_in_foster_care is True

        if independent:
            return Family(
                dependent=False,
                contributors=(student, *spouses),
                married=married,
                has_children=bool(children),
                family_size=1 + len(spouses) + len(children),
            )

        parents = self._parents(student)
        if not parents:
            return None

        return Family(
            dependent=True,
            contributors=tuple(parents),
            married=False,
            has_children=False,
            family_size=self.screen.household_size,
        )

    def _spouses(self, student: HouseholdMember) -> list[HouseholdMember]:
        if student.relationship == "headOfHousehold":
            return [m for m in self._others(student) if m.relationship in SPOUSE_RELATIONSHIPS]
        if student.relationship in SPOUSE_RELATIONSHIPS:
            return [m for m in self._others(student) if m.relationship == "headOfHousehold"]
        return []

    def _children(self, student: HouseholdMember) -> list[HouseholdMember]:
        if student.relationship not in ("headOfHousehold", "spouse"):
            return []
        return [m for m in self._others(student) if m.relationship in CHILD_RELATIONSHIPS]

    def _parents(self, student: HouseholdMember) -> list[HouseholdMember]:
        """The head and their `spouse` for the head's child; `parent`s, and a `stepParent` beside one, for the head."""
        others = self._others(student)
        if student.relationship == "child":
            return [m for m in others if m.relationship in ("headOfHousehold", "spouse")]

        if student.relationship == "headOfHousehold":
            parents = [m for m in others if m.relationship == "parent"]
            if parents:
                parents += [m for m in others if m.relationship == "stepParent"]
            return parents

        return []

    def _others(self, student: HouseholdMember) -> list[HouseholdMember]:
        return [m for m in self._members if m.id != student.id]

    @cached_property
    def _members(self) -> list[HouseholdMember]:
        return list(self.screen.household_members.all())

    # Income and assets

    def _agi(self, people: Iterable[HouseholdMember]) -> Decimal:
        return self._income(people, ["all"], exclude=AGI_EXCLUDED_TYPES)

    def _earned(self, people: Iterable[HouseholdMember]) -> Decimal:
        return self._income(people, ["earned"])

    def _assets(self, people: Iterable[HouseholdMember]) -> Decimal:
        """Child support the contributors receive plus the household's assets, blank as $0."""
        return self._income(people, ["childSupport"]) + Decimal(self.screen.household_assets or 0)

    @staticmethod
    def _income(people: Iterable[HouseholdMember], types: list[str], exclude: Iterable[str] = ()) -> Decimal:
        total = sum(m.calc_gross_income("yearly", types, exclude=tuple(exclude)) for m in people)
        return Decimal(str(round(total, 2)))

    # Student Aid Index

    def student_aid_index(self, student: HouseholdMember, family: Family) -> int:
        if family.dependent:
            return self._formula_a(student, family)
        if family.has_children:
            return self._formula_c(family)
        return self._formula_b(family)

    def _formula_a(self, student: HouseholdMember, family: Family) -> int:
        parents = family.contributors
        parents_agi = self._agi(parents)
        parents_aai = (
            parents_agi
            - payroll_allowance(self._earned(parents), joint=len(parents) > 1)
            - allowance(IPA_FAMILY_A2, family.family_size)
            - employment_expense_allowance(parents_agi)
            + whole(ASSET_CONVERSION_A * self._assets(parents))
        )
        parents_aai = whole(parents_aai)

        student_available = (
            self._agi([student])
            - payroll_allowance(self._earned([student]), joint=False)
            - IPA_DEPENDENT_STUDENT
            - max(0, -parents_aai)
        )
        student_contribution = max(0, whole(INCOME_ASSESSMENT * student_available))

        return contribution_from_aai(parents_aai) + student_contribution

    def _formula_b(self, family: Family) -> int:
        people = family.contributors
        earned = self._earned(people)
        available = (
            self._agi(people)
            - payroll_allowance(earned, joint=family.married)
            - (IPA_MARRIED_B if family.married else IPA_SINGLE)
            - (employment_expense_allowance(earned) if family.married else 0)
        )

        return whole(INCOME_ASSESSMENT * available) + whole(ASSET_CONVERSION_B * self._assets(people))

    def _formula_c(self, family: Family) -> int:
        people = family.contributors
        earned = self._earned(people)
        ipa_table = IPA_MARRIED_C2 if family.married else IPA_SINGLE_PARENT_C3
        aai = (
            self._agi(people)
            - payroll_allowance(earned, joint=family.married)
            - allowance(ipa_table, family.family_size)
            - employment_expense_allowance(earned)
            + whole(ASSET_CONVERSION_C * self._assets(people))
        )

        return contribution_from_aai(whole(aai))
