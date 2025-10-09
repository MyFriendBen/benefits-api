import programs.programs.messages as messages
from programs.co_county_zips import counties_from_screen
from programs.programs.co.income_limits_cache.income_limits_cache import IncomeLimitsCache
from programs.programs.calc import Eligibility


def validate_income_limits(screen, eligibility: Eligibility, income_limits_cache: IncomeLimitsCache):
    """
    Validates income eligibility across counties and returns income data.

    Args:
        screen: The screening object with household information
        eligibility: The Eligibility object to record conditions
        income_limits_cache: An instance of IncomeLimitsCache

    Returns:
        tuple: (income_eligible, income, income_limit) if valid
               (False, None, None) if validation failed
    """
    counties = counties_from_screen(screen)
    limits_by_county = income_limits_cache.fetch()
    income_limits = []
    size_index = screen.household_size - 1

    for county in counties:
        if county not in limits_by_county:
            eligibility.condition(False, messages.income_limit_unknown("county_not_found", county))
            continue

        county_data = limits_by_county.get(county)
        if county_data is None:
            eligibility.condition(False, messages.income_limit_unknown("county_data_none", county))
            continue

        # Validate household_size bounds
        if size_index < 0 or size_index >= len(county_data):
            eligibility.condition(False, messages.income_limit_unknown("HH_size_out_of_bounds", county, size_index))
            continue

        try:
            limit_value = county_data[size_index]
            if limit_value is None:
                eligibility.condition(False, messages.income_limit_unknown("income_data_none", county, size_index))
                continue

            income_limits.append(limit_value)
        except IndexError:
            continue

    # Handle case where no valid income limits were found
    if not income_limits:
        eligibility.condition(False, messages.income_limit_unknown("no_valid_income_limits", "all_counties"))
        return False, None, None

    income = int(screen.calc_gross_income("yearly", ["all"]))
    income_limit = min(income_limits)
    income_eligible = income <= income_limit

    # eligibility.condition(income_eligible, messages.income(income, income_limit))

    return income_eligible, income, income_limit
