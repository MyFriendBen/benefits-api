"""
Federal income tax pieces the federal tax credits share: the income the screener records that
is left out of adjusted gross income, each tax year's deduction and bracket figures, and the tax
owed on taxable income. Each credit's spec states the figures it uses.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from screener.models import HouseholdMember

JOINT = "joint"
HEAD_OF_HOUSEHOLD = "head_of_household"
SINGLE = "single"

# Income types that are never taxed. Tuples, since several credits share them.
NEVER_TAXED_INCOME_TYPES = (
    "sSI",
    "cashAssistance",
    "cashAssistanceOther",
    "childSupport",
    "gifts",
    "workersComp",
    "veteran",
)
# Social Security, treated as untaxed because the screener can't tell the taxable part. Where
# that misses, adjusted gross income reads low.
SOCIAL_SECURITY_INCOME_TYPES = ("sSDisability", "sSSurvivor", "sSRetirement", "sSDependent")
# Every type left out of the screener's stand-in for adjusted gross income.
UNTAXED_INCOME_TYPES = NEVER_TAXED_INCOME_TYPES + SOCIAL_SECURITY_INCOME_TYPES

#: A tax bracket: the taxable income it runs up to (None for the top bracket) and its rate.
Bracket = tuple[Optional[int], Decimal]

#: Taxable income from which the Tax Computation Worksheet replaces the Tax Table.
TAX_TABLE_CEILING = 100_000


def brackets(*tops: int) -> tuple[Bracket, ...]:
    """The bracket schedule from the tops of all but the last bracket."""
    rates = ("0.10", "0.12", "0.22", "0.24", "0.32", "0.35")
    return tuple((top, Decimal(rate)) for top, rate in zip(tops, rates)) + ((None, Decimal("0.37")),)


def bracket_tax(amount: Decimal, schedule: tuple[Bracket, ...]) -> Decimal:
    """Tax from the bracket schedule to the cent, as the Tax Computation Worksheet figures it."""
    tax = Decimal(0)
    lower = Decimal(0)
    for top, rate in schedule:
        upper = amount if top is None else min(amount, Decimal(top))
        if upper <= lower:
            break
        tax += (upper - lower) * rate
        lower = upper

    return tax


def tax_table_row(amount: Decimal) -> tuple[int, int]:
    """The Tax Table row holding ``amount``."""
    if amount < 5:
        return 0, 5
    if amount < 15:
        return 5, 15
    if amount < 25:
        return 15, 25

    width = 25 if amount < 3_000 else 50
    low = int(amount) // width * width
    return low, low + width


def income_tax(taxable_income: Decimal, schedule: tuple[Bracket, ...]) -> Decimal:
    """Income tax before credits: Tax Table rows priced at their midpoint below the ceiling, the
    brackets exactly above it."""
    if taxable_income <= 0:
        return Decimal(0)

    if taxable_income < TAX_TABLE_CEILING:
        low, high = tax_table_row(taxable_income)
        return bracket_tax(Decimal(low + high) / 2, schedule).quantize(Decimal(1), rounding=ROUND_HALF_UP)

    return bracket_tax(taxable_income, schedule)


@dataclass(frozen=True)
class FederalTaxYear:
    """One tax year's figures for the tax owed, keyed by filing status."""

    standard_deduction: dict[str, int]
    # The addition for each filer 65 or older, and for each who is blind.
    extra_deduction: dict[str, int]
    senior_age: int
    tax_brackets: dict[str, tuple[Bracket, ...]]


FEDERAL_TAX_YEARS: dict[int, FederalTaxYear] = {
    2025: FederalTaxYear(
        standard_deduction={JOINT: 31_500, HEAD_OF_HOUSEHOLD: 23_625, SINGLE: 15_750},
        extra_deduction={JOINT: 1_600, HEAD_OF_HOUSEHOLD: 2_000, SINGLE: 2_000},
        senior_age=65,
        tax_brackets={
            JOINT: brackets(23_850, 96_950, 206_700, 394_600, 501_050, 751_600),
            HEAD_OF_HOUSEHOLD: brackets(17_000, 64_850, 103_350, 197_300, 250_500, 626_350),
            SINGLE: brackets(11_925, 48_475, 103_350, 197_300, 250_525, 626_350),
        },
    ),
    2026: FederalTaxYear(
        standard_deduction={JOINT: 32_200, HEAD_OF_HOUSEHOLD: 24_150, SINGLE: 16_100},
        extra_deduction={JOINT: 1_650, HEAD_OF_HOUSEHOLD: 2_050, SINGLE: 2_050},
        senior_age=65,
        tax_brackets={
            JOINT: brackets(24_800, 100_800, 211_400, 403_550, 512_450, 768_700),
            HEAD_OF_HOUSEHOLD: brackets(17_700, 67_450, 105_700, 201_750, 256_200, 640_600),
            SINGLE: brackets(12_400, 50_400, 105_700, 201_775, 256_225, 640_600),
        },
    ),
}


def age_or_blind_count(filers: Iterable[HouseholdMember], tax_year: int, year: FederalTaxYear) -> int:
    """The standard deduction's additions: one for each filer 65 or older at the tax year's end,
    and one for each filer who is blind."""
    count = 0
    for filer in filers:
        age = filer.age_at_end_of_year(tax_year)
        count += int(age is not None and age >= year.senior_age) + int(bool(filer.visually_impaired))

    return count


def tax_owed(agi: Decimal, status: str, age_or_blind_count: int, year: FederalTaxYear) -> Decimal:
    """Income tax before credits on ``agi`` less the standard deduction and its additions."""
    deduction = year.standard_deduction[status] + year.extra_deduction[status] * age_or_blind_count
    return income_tax(max(agi - deduction, Decimal(0)), year.tax_brackets[status])
