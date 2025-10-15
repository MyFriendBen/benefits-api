from programs.programs.co.energy_programs_shared.income_limits_cache import (
    IncomeLimitsCache,
)
from sentry_sdk import capture_message
from screener.models import Screen


def _log_income_limit_error(message: str, county: str | None, **additional_extras) -> None:
    """
    Helper to log income limit validation errors.

    Args:
        message: Error message
        county: County name (can be None if not available)
        **additional_extras: Any additional context fields (e.g., household_size, size_index)
    """
    extras = {"county": county}
    extras.update(additional_extras)
    capture_message(message, level="error", extras=extras)


def get_income_limit(screen: Screen) -> int | None:
    """
    Retrieves the income limit for the household's county.
    ONLY retrieves data - does NOT set any eligibility conditions.

    Args:
        screen: The screening object with household information

    Returns:
        Optional[int]: The income limit (or None if not found)
    """

    # Get county
    county = screen.county

    # Fetch income limits data (keys are "Adams County", "Alamosa County", etc.)
    income_limits_cache = IncomeLimitsCache()
    limits_by_county = income_limits_cache.fetch()
    size_index = screen.household_size - 1 if screen.household_size else None

    # Check for valid income_limit
    if county not in limits_by_county:
        _log_income_limit_error("County data not found", county=county)
        return None

    if limits_by_county.get(county) is None:
        _log_income_limit_error("Data for county is not found", county=county)
        return None

    try:
        income_limit = limits_by_county[county][size_index]
    except IndexError:
        _log_income_limit_error(
            "Invalid HH size given income limit data",
            county=county,
            household_size=screen.household_size,
        )
        return None
    except TypeError:
        _log_income_limit_error(
            "Invalid HH size",
            county=county,
            household_size=screen.household_size,
        )
        return None

    if income_limit is None:
        _log_income_limit_error(
            "Income limit for county and given HH Size is missing or misformatted",
            county=county,
            household_size=screen.household_size,
        )
        return None

    # valid income_limit
    return int(income_limit)
