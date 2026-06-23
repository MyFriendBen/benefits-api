import hashlib

import requests
from django.conf import settings
from django.core.cache import cache

AUTOCOMPLETE_CACHE_TTL = 60 * 60 * 24 * 7  # 7 days


class GooglePlacesClient:
    BASE_URL = "https://maps.googleapis.com"

    def autocomplete_address(self, input_text: str) -> list[dict]:
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
        results = [
            {
                "description": p["description"].removesuffix(", USA"),
                "place_id": p["place_id"],
            }
            for p in data.get("predictions", [])
        ]
        cache.set(cache_key, results, AUTOCOMPLETE_CACHE_TTL)
        return results
