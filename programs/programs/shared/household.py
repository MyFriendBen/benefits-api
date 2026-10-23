"""Household composition and needs."""

from screener.models import Screen


def needs_child_development_help(screen: Screen, max_child_age: int) -> bool:
    """
    Whether the household asked for help with a child's development and has a child
    (counting a pregnancy) no older than ``max_child_age``.
    """
    has_child = screen.num_children(age_max=max_child_age, include_pregnant=True) > 0
    return bool(screen.needs_child_dev_help) and has_child
