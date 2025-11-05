"""
HUD Income Limits API Client

Drop-in replacement for the Google Sheets-based Ami class.

Uses HUD's Multifamily Tax Subsidy Project (MTSP) Income Limits API which provides
all income percentage levels (20%, 30%, 40%, 50%, 60%, 70%, 80%, 100% AMI).

API Documentation: https://www.huduser.gov/portal/dataset/fmr-api.html
"""

from typing import Union, Literal, Optional
from decouple import config
import requests
from sentry_sdk import capture_exception
from django.core.cache import cache


class HudIncomeClientError(Exception):
    """Base exception for HUD Income Client errors"""

    pass


class HudIncomeClient:
    """
    HUD Income Limits API client.

    Primary method: get_screen_ami() - matches the old Ami.get_screen_ami() interface

    Requires:
        - HUD_API_TOKEN environment variable
        - API registration for both FMR and Income Limits datasets
    """

    BASE_URL = "https://www.huduser.gov/hudapi/public"
    CACHE_TTL = 86400  # 24 hours in seconds

    def __init__(self, api_token: Optional[str] = None):
        """Initialize with HUD API token from environment or parameter."""
        self._api_token = api_token
        self._headers = None

    @property
    def headers(self):
        """Lazy-load headers with API token."""
        if self._headers is None:
            token = self._api_token or config("HUD_API_TOKEN", default=None)
            if not token:
                raise HudIncomeClientError(
                    "HUD_API_TOKEN environment variable required. "
                    "Get your token at: https://www.huduser.gov/hudapi/public/register"
                )
            self._headers = {"Authorization": f"Bearer {token}"}
        return self._headers

    def get_screen_ami(
        self,
        screen,
        percent: Union[
            Literal["20%"],
            Literal["30%"],
            Literal["40%"],
            Literal["50%"],
            Literal["60%"],
            Literal["70%"],
            Literal["80%"],
            Literal["100%"],
        ],
        year: Union[int, str],
    ) -> int:
        """
        Get income limit for a Screen object.

        Drop-in replacement for Ami.get_screen_ami()

        Args:
            screen: Screen object with white_label.state_code, county, and household_size
            percent: Income percentage ("20%", "30%", "40%", "50%", "60%", "70%", "80%", "100%")
            year: Year for income limits (e.g., 2025 or "2025")

        Returns:
            Income limit in dollars

        Example:
            >>> hud_client.get_screen_ami(screen, "80%", "2025")
            89520
        """
        if screen.household_size < 1 or screen.household_size > 8:
            raise HudIncomeClientError("Household size must be between 1 and 8")

        year = int(year) if isinstance(year, str) else year

        # Get entity ID for the county (works for any state)
        entity_id = self._get_entity_id(screen.white_label.state_code, screen.county, year)

        # Fetch income limit data using MTSP endpoint (has all percentages: 20-80%)
        cache_key = f"hud_mtsp_{entity_id}_{year}"
        data = cache.get(cache_key)

        if not data:
            params = {"year": str(year)} if year else {}
            data = self._api_request(f"mtspil/data/{entity_id}", params)
            cache.set(cache_key, data, self.CACHE_TTL)

        # Extract income limits data
        if not data or "data" not in data:
            raise HudIncomeClientError(
                f"No income limit data found for {screen.county}, {screen.white_label.state_code}"
            )

        area_data = data["data"]

        # Get the field value based on percent
        # MTSP API structure: {"20percent": {"il20_p1": ...}, "30percent": {...}, ..., "80percent": {...}}
        if percent == "100%":
            value = area_data.get("median_income")
            if value is None:
                raise HudIncomeClientError("No median income data available")
        else:
            # MTSP endpoint provides 20%, 30%, 40%, 50%, 60%, 70%, 80%
            percent_num = percent.rstrip("%")
            category = f"{percent_num}percent"

            if category not in area_data:
                raise HudIncomeClientError(f"No {percent} AMI data available")

            field = f"il{percent_num}_p{screen.household_size}"
            value = area_data[category].get(field)

            if value is None:
                raise HudIncomeClientError(f"No {percent} AMI data for household size {screen.household_size}")

        return int(value)

    def _get_entity_id(self, state_code: str, county_name: str, year: int) -> str:
        """Get FIPS entity ID for a county in any state."""
        # Normalize county name
        county_name = county_name.strip()
        if not county_name.lower().endswith("county"):
            county_name = f"{county_name} County"

        # Check cache
        cache_key = f"hud_counties_{state_code}_{year or 'latest'}"
        counties = cache.get(cache_key)

        if not counties:
            # Use FMR endpoint to list counties (shared across FMR and IL APIs)
            # Note: This requires FMR dataset API access in addition to IL dataset
            counties = self._api_request(f"fmr/listCounties/{state_code.upper()}")
            cache.set(cache_key, counties, self.CACHE_TTL)

        # Find matching county (FMR API returns array directly, not wrapped in data object)
        if not counties or not isinstance(counties, list):
            raise HudIncomeClientError(f"Could not retrieve counties for {state_code}")

        for county in counties:
            if county.get("county_name", "").lower() == county_name.lower():
                return county["fips_code"]

        raise HudIncomeClientError(f"County not found: {county_name}, {state_code}")

    def _api_request(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Make an API request to HUD."""
        try:
            response = requests.get(f"{self.BASE_URL}/{endpoint}", headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            capture_exception(e)
            status_code = e.response.status_code
            if status_code == 401:
                raise HudIncomeClientError("Authentication failed. Check HUD_API_TOKEN is set and valid.")
            elif status_code == 403:
                raise HudIncomeClientError(
                    "Access denied. Ensure your HUD API account is registered for both "
                    "FMR and Income Limits datasets at https://www.huduser.gov/hudapi/public/register"
                )
            elif status_code == 404:
                raise HudIncomeClientError(
                    f"Data not found for endpoint: {endpoint}. " "Check that the state/county exists and year is valid."
                )
            else:
                raise HudIncomeClientError(f"API request failed ({status_code}): {e.response.text}")
        except requests.exceptions.RequestException as e:
            capture_exception(e)
            raise HudIncomeClientError(f"Request failed: {str(e)}")


# Default client instance
hud_client = HudIncomeClient()
