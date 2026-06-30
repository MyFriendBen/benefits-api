from django.core.cache import cache
from integrations.services.sheets.sheets import GoogleSheets


class IncomeLimitsCache:
    sheet_id = "1ZzQYhULtiP61crj0pbPjhX62L1TnyAisLcr_dQXbbFg"
    range_name = "A2:K"
    CACHE_KEY = "energy_income_limits_data"
    CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours

    def _get_data(self) -> dict:
        data = cache.get(self.CACHE_KEY)
        if data is not None:
            return data
        data = self._process()
        cache.set(self.CACHE_KEY, data, timeout=self.CACHE_TIMEOUT)
        return data

    def _process(self) -> dict[str, list[float]]:
        data = GoogleSheets(self.sheet_id, self.range_name).data()
        result = {}
        for r in data:
            result[self._format_county(r[0])] = self._format_amounts(r[1:])
        return result

    @staticmethod
    def _format_county(county: str):
        return county.strip() + " County"

    @staticmethod
    def _format_amounts(amounts: list[str]):
        result = []
        for a in amounts:
            cleaned = a.strip().replace("$", "").replace(",", "")
            try:
                result.append(float(cleaned) if cleaned else None)
            except ValueError:
                result.append(None)

        return result
