"""
New Jersey gross income tax pieces that more than one NJ calculator reads: which members file,
which income types New Jersey doesn't tax, and the tax on a taxable income.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import NamedTuple, Optional

from screener.models import HouseholdMember, Screen

#: Income types New Jersey leaves out of gross income: Social Security, SSI, unemployment,
#: workers' compensation, gifts, child support, welfare and veterans' benefits.
EXCLUDED_INCOME_TYPES = (
    "sSRetirement",
    "sSDisability",
    "sSSurvivor",
    "sSDependent",
    "sSI",
    "unemployment",
    "workersComp",
    "gifts",
    "childSupport",
    "cashAssistance",
    "cashAssistanceOther",
    "veteran",
)


def filers(screen: Screen) -> list[HouseholdMember]:
    """The head and a member entered as a spouse. A domestic partner files their own return."""
    return [m for m in screen.household_members.all() if m.is_head() or m.relationship == "spouse"]


class Bracket(NamedTuple):
    top: Optional[int]
    rate: Decimal
    subtract: Decimal


def _brackets(*rows: tuple[Optional[int], str, str]) -> tuple[Bracket, ...]:
    return tuple(Bracket(top, Decimal(rate), Decimal(subtract)) for top, rate, subtract in rows)


#: Table A: single and married filing separately.
TABLE_A = _brackets(
    (20_000, "0.014", "0"),
    (35_000, "0.0175", "70.00"),
    (40_000, "0.035", "682.50"),
    (75_000, "0.05525", "1492.50"),
    (500_000, "0.0637", "2126.25"),
    (1_000_000, "0.0897", "15126.25"),
    (None, "0.1075", "32926.25"),
)

#: Table B: joint, head of household and qualifying widow(er). The 70,000 to 80,000 row
#: subtracts 1,155.00, the figure the Tax Table uses; the statute's 1,154.50 never applies,
#: since everyone in that band is under the Tax Table ceiling.
TABLE_B = _brackets(
    (20_000, "0.014", "0"),
    (50_000, "0.0175", "70.00"),
    (70_000, "0.0245", "420.00"),
    (80_000, "0.035", "1155.00"),
    (150_000, "0.05525", "2775.00"),
    (500_000, "0.0637", "4042.50"),
    (1_000_000, "0.0897", "17042.50"),
    (None, "0.1075", "34842.50"),
)

#: Taxable income below which the Tax Table replaces the rate schedules.
TAX_TABLE_CEILING = 100_000
TAX_TABLE_ROW_WIDTH = 50


def schedule_tax(amount: Decimal, table: tuple[Bracket, ...]) -> Decimal:
    """Tax from the rate schedule: the amount times its row's rate, less the row's subtraction."""
    for bracket in table:
        if bracket.top is None or amount <= bracket.top:
            return amount * bracket.rate - bracket.subtract

    raise ValueError(f"No bracket for {amount}")


def income_tax(taxable_income: Decimal, table: tuple[Bracket, ...]) -> Decimal:
    """
    Tax on a New Jersey taxable income. Below the ceiling it is the Tax Table's figure: the
    rate schedule at the midpoint of the income's row, rounded to the dollar. At or above it,
    the rate schedule applied to the exact amount.
    """
    if taxable_income <= 0:
        return Decimal(0)

    if taxable_income < TAX_TABLE_CEILING:
        row_start = int(taxable_income) // TAX_TABLE_ROW_WIDTH * TAX_TABLE_ROW_WIDTH
        midpoint = Decimal(row_start) + Decimal(TAX_TABLE_ROW_WIDTH) / 2
        return schedule_tax(midpoint, table).quantize(Decimal(1), rounding=ROUND_HALF_UP)

    return schedule_tax(taxable_income, table)
