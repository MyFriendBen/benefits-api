"""Income limits derived from a threshold table."""

from collections.abc import Mapping
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from programs.models import FederalPoveryLimit


def fpl_income_limit(fpl: "FederalPoveryLimit", household_size: int, fpl_percent: float) -> int:
    """
    The annual income limit at ``fpl_percent`` of the poverty guideline for a household
    of ``household_size``, truncated to whole dollars.

    Truncation, not rounding, is what every caller used before this was shared. Programs
    that round up or to the nearest dollar compute their own limit.
    """
    return int(fpl_percent * fpl.get_limit(household_size))


def table_income_limit(table: Mapping[int, int], household_size: int, per_extra_person: int) -> int:
    """
    A household's limit from a published table keyed by household size, extended by
    ``per_extra_person`` for each member beyond the largest size the table lists.
    """
    if household_size in table:
        return table[household_size]

    largest_size = max(table)
    return table[largest_size] + (household_size - largest_size) * per_extra_person
