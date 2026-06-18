import requests
from django.conf import settings


class GooglePlacesClient:
    BASE_URL = "https://maps.googleapis.com"

    def autocomplete_address(self, input_text: str) -> list[dict]:
        response = requests.get(
            f"{self.BASE_URL}/maps/api/place/autocomplete/json",
            params={
                "input": input_text,
                "types": "address",
                "components": "country:us",
                "key": settings.GOOGLE_MAPS_API_KEY,
            },
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
        return [
            {
                "description": p["description"].removesuffix(", USA"),
                "place_id": p["place_id"],
            }
            for p in data.get("predictions", [])
        ]
