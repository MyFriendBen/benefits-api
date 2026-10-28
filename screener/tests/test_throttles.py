"""Tests for the hashed-IP rate throttles on the screener's AllowAny proxy endpoints."""

from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from benefits.tests.cache_override import LOCAL_CACHE
from screener.throttles import PlacesRateThrottle


@override_settings(CACHES=LOCAL_CACHE)
class TestUnhandledMethodIsNotThrottled(APITestCase):
    URL = "/api/places/autocomplete/"

    def setUp(self) -> None:
        cache.clear()
        patcher = patch.object(PlacesRateThrottle, "rate", "1/hour", create=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    @patch("screener.views.GooglePlacesClient.autocomplete_address", return_value=[])
    def test_405s_do_not_use_up_the_allowance(self, _autocomplete: Mock) -> None:
        for _ in range(3):
            self.assertEqual(self.client.get(self.URL).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        first = self.client.post(self.URL, {"input": "123 Main"}, format="json")
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        second = self.client.post(self.URL, {"input": "123 Main"}, format="json")
        self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
