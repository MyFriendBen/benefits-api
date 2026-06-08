import requests
from django.conf import settings


class RewiringAmericaClient:
    BASE_URL = "https://api.rewiringamerica.org"

    def fetch_rem_impact(
        self,
        upgrade: str,
        address: str,
        heating_fuel: str,
        water_heater_fuel: str | None = None,
    ) -> dict:
        """Call GET /api/v1/rem/address and return the raw response dict."""
        params: dict[str, str] = {
            "upgrade": upgrade,
            "address": address,
            "heating_fuel": heating_fuel,
        }
        if water_heater_fuel:
            params["water_heater_fuel"] = water_heater_fuel

        response = requests.get(
            f"{self.BASE_URL}/api/v1/rem/address",
            params=params,
            headers={"Authorization": f"Bearer {settings.REWIRING_AMERICA_API_KEY}"},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()
