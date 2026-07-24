from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from django.core.cache import cache
from integrations.services.sheets.sheets import GoogleSheets
from sentry_sdk import capture_exception

T = TypeVar("T")


class GoogleSheetsCache(ABC, Generic[T]):
    """
    Abstract base class for caching Google Sheets data. Subclasses must implement the `_process` method to define how to process the raw data from Google Sheets into the desired format.
    """

    sheet_id: str
    range_name: str
    CACHE_KEY: str
    CACHE_TIMEOUT: int = 60 * 60 * 24  # default to 24 hours; subclasses can override this value as needed.
    STALE_CACHE_TIMEOUT: int = 60 * 60 * 24 * 7  # default to 7 days; subclasses can override this value as needed.

    @property
    def _stale_cache_key(self) -> str:
        """
        Generate a key for stale cache data. This can be used to store data that is considered stale but still retrievable.
        """
        return f"{self.CACHE_KEY}_stale"

    def get_data(self) -> T:
        """
        Retrieve data from the cache if available; otherwise, process the data and store it in the cache.
        """
        data = cache.get(self.CACHE_KEY)
        if data is not None:
            return data
        try:
            data = self._process(self._fetch_raw())
        except Exception as exc:
            capture_exception(exc)
            stale_data = cache.get(self._stale_cache_key)
            return stale_data if stale_data is not None else self._empty_fallback()

        if not data:
            # don't cache empty data/falsy result - retry on the next request, return it directly
            # instead of locking every dependent screening out for 24h.
            return self._empty_fallback()

        cache.set(self.CACHE_KEY, data, timeout=self.CACHE_TIMEOUT)
        cache.set(self._stale_cache_key, data, timeout=self.STALE_CACHE_TIMEOUT)
        return data

    def _fetch_raw(self):
        """
        Fetch raw data from Google Sheets.
        """
        return GoogleSheets(self.sheet_id, self.range_name).data()

    @abstractmethod
    def _process(self, raw_data) -> T:
        """
        Process the raw data from Google Sheets into the desired format.
        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement the _process method.")

    def _empty_fallback(self) -> T:
        """
        Provide a fallback value when the processed data is empty or falsy.
        Subclasses can override this method to provide specific fallback behavior.
        """
        return {}  # Default implementation returns an empty dict; subclasses can override as needed.
