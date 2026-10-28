"""
Federal income tax pieces the federal tax credits share: the income the screener records that
is left out of adjusted gross income, and the tax on taxable income. Each credit's spec states
the figures it uses; the year tables stay with each credit.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

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
