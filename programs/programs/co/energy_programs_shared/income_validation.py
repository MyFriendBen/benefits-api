import programs.programs.messages as messages
from programs.co_county_zips import counties_from_screen
from programs.programs.co.energy_programs_shared.income_limits_cache import IncomeLimitsCache
from programs.programs.calc import Eligibility


def _get_county_name(screen) -> str:
    """
    Helper function to get formatted county name from screen.
    Handles both County objects and strings from zipcode lookup.

    Returns:
        str: County name in "County Name County" format, or "unknown" if not found
    """
    counties = counties_from_screen(screen)

    if not counties:
        return "unknown"

    first_county = counties[0]

    # Handle both county object (has .name) and string (from zipcode lookup)
    if isinstance(first_county, str):
        return first_county  # Example: Already "Adams County" from zipcodes dict
    else:
        return first_county.name + " County"  # Example: County object with name="Adams"


def get_income_limit(screen, income_limits_cache: IncomeLimitsCache) -> tuple[int | None, str | None]:
    """
    Retrieves the income limit for the household's county.
    ONLY retrieves data - does NOT set any eligibility conditions.

    Args:
        screen: The screening object with household information
        income_limits_cache: An instance of IncomeLimitsCache

    Returns:
        tuple: (income_limit, error_detail)
               - income_limit: The income limit (or None if not found)
               - error_detail: Error reason string (or None if successful)
    """
    # Get county from screen (handles both direct county selection and zipcode lookup)
    counties = counties_from_screen(screen)
    if not counties:
        return None, "no_county_provided"

    # Get formatted county name
    county = _get_county_name(screen)

    # Fetch income limits data (keys are "Adams County", "Alamosa County", etc.)
    limits_by_county = income_limits_cache.fetch()
    size_index = screen.household_size - 1

    # Check conditions using if/elif (only one condition will be checked)
    if county not in limits_by_county:
        return None, "county_not_found"
    elif limits_by_county.get(county) is None:
        return None, "county_data_none"
    elif size_index < 0 or size_index >= len(limits_by_county[county]):
        return None, "HH_size_out_of_bounds"
    else:
        try:
            limit_value = limits_by_county[county][size_index]
            if limit_value is None:
                return None, "income_data_none_or_misformatted"
            else:
                return int(limit_value), None
        except IndexError:
            return None, "index_error"


def validate_income_eligibility(screen, eligibility: Eligibility, income_limits_cache: IncomeLimitsCache) -> bool:
    """
    Validates income eligibility and sets eligibility condition.
    This is the standard validation used by UtilityBillPay.

    Args:
        screen: The screening object with household information
        eligibility: The Eligibility object to record conditions
        income_limits_cache: An instance of IncomeLimitsCache

    Returns:
        bool: True if validation succeeded (income_limit found), False otherwise
    """
    # Get income limit (data retrieval only)
    income_limit, error_detail = get_income_limit(screen, income_limits_cache)

    # Handle error case
    if income_limit is None:
        county = _get_county_name(screen)
        size_index = screen.household_size - 1
        eligibility.condition(False, messages.income_limit_unknown(error_detail, county, size_index))
        return False

    # Calculate user's income
    user_income = int(screen.calc_gross_income("yearly", ["all"]))

    # Check income eligibility (business logic)
    income_eligible = user_income <= income_limit

    # Set ONE eligibility condition
    eligibility.condition(income_eligible, messages.income(user_income, income_limit))

    return True  # Validation succeeded (data was found)
