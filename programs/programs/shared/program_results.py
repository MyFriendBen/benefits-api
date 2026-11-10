"""Reading other programs' results from an urgent need."""

from collections.abc import Iterable
from typing import Optional

from screener.models import Screen


def eligible_in_results(results: Optional[Iterable], program_code: str) -> bool:
    """
    Whether the eligibility results list marks ``program_code`` eligible.

    ``results`` is the list of serialized program results an urgent need receives as
    ``data``. It can be empty or ``None`` when no programs were calculated, and entries
    that aren't dicts are skipped.
    """
    return any(
        isinstance(result, dict) and result.get("name_abbreviated") == program_code and bool(result.get("eligible"))
        for result in results or []
    )


def has_or_is_eligible_for(screen: Screen, results: Optional[Iterable], program_code: str) -> bool:
    """Whether the household already receives ``program_code`` or the results mark it eligible."""
    return screen.has_benefit(program_code) or eligible_in_results(results, program_code)
