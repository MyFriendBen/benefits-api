from integrations.services.sheets import GoogleSheetsCache
from typing import ClassVar


class IncomeLimitsCache(GoogleSheetsCache):
    sheet_id = "1ZzQYhULtiP61crj0pbPjhX62L1TnyAisLcr_dQXbbFg"
    range_name = "A2:K"
    default: ClassVar[dict] = {}

    def update(self) -> dict[str, list[float]]:
        data = super().update()
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
