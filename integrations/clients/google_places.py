import hashlib
import logging
from typing import TypedDict

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

AUTOCOMPLETE_CACHE_TTL = 60 * 60 * 24 * 7  # 7 days


class AddressPrediction(TypedDict):
    description: str
    place_id: str


class GooglePlacesClient:
    BASE_URL = "https://maps.googleapis.com"

    def autocomplete_address(self, input_text: str) -> list[AddressPrediction]:
        cache_key = "places_autocomplete_" + hashlib.md5(input_text.lower().encode()).hexdigest()
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

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
        api_status = data.get("status")
        if api_status not in ("OK", "ZERO_RESULTS"):
            logger.warning("Google Places API returned status %s for input %r", api_status, input_text)
            raise requests.RequestException(f"Google Places API error status: {api_status}")
        results: list[AddressPrediction] = [
            {
                "description": p["description"].removesuffix(", USA"),
                "place_id": p["place_id"],
            }
            for p in data.get("predictions", [])
        ]
        cache.set(cache_key, results, AUTOCOMPLETE_CACHE_TTL)
        return results
