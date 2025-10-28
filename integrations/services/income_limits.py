from typing import ClassVar, Literal, Union

from sentry_sdk import capture_message, new_scope

from integrations.services.sheets.sheets import GoogleSheetsCache
from screener.models import Screen


class Ami(GoogleSheetsCache):
    sheet_id = "1ZnOg_IuT7TYz2HeF31k_FSPcA-nraaMG3RUWJFUIIb8"
    range_name = "current!A2:CH"
    default = {}

    YEAR_INDEX = 0
    STATE_INDEX = 1
    COUNTY_INDEX = 2
    MTSP_LIMITS_START_INDEX = 6
    MAX_HOUSEHOLD_SIZE = 8
    IL_PERCENTS = ["80%", "50%", "30%"]
    IL_LIMITS_START_INDEX = 62

    def update(self) -> dict[str, dict[str, dict[str, dict[int, int]]]]:  # type: ignore[override]
        data = super().update()

        ami: dict[str, dict[str, dict[str, dict[int, int]]]] = {}

        for row in data:
            year = row[self.YEAR_INDEX]
            state = row[self.STATE_INDEX]
            county = row[self.COUNTY_INDEX]

            values = {"mtsp": {}, "il": {}}
            continue_outer = False
            percent = 80
            for i in range(
                self.MTSP_LIMITS_START_INDEX,
                self.MAX_HOUSEHOLD_SIZE * 7,
                self.MAX_HOUSEHOLD_SIZE,
            ):
                try:
                    income_limit_values = self._get_income_limits(row[i : i + self.MAX_HOUSEHOLD_SIZE])
                except ValueError:
                    continue_outer = True
                    break
                values["mtsp"][str(percent) + "%"] = income_limit_values
                percent -= 10

            i = self.IL_LIMITS_START_INDEX
            for percent in self.IL_PERCENTS:
                try:
                    income_limit_values = self._get_income_limits(row[i : i + self.MAX_HOUSEHOLD_SIZE])
                except ValueError:
                    continue_outer = True
                    break
                values["il"][percent] = income_limit_values
                i += self.MAX_HOUSEHOLD_SIZE

            if continue_outer:
                continue

            if year not in ami:
                ami[year] = {}
            if state not in ami[year]:
                ami[year][state] = {}

            ami[year][state][county] = values

        return ami

    def _get_income_limits(self, values: list[str]):
        income_limit_values = {}
        for i, raw_value in enumerate(values):
            value = int(float(raw_value))

            income_limit_values[i + 1] = value

        return income_limit_values

    def get_screen_ami(
        self,
        screen: Screen,
        percent: Union[
            Literal["100%"],
            Literal["80%"],
            Literal["70%"],
            Literal["60%"],
            Literal["50%"],
            Literal["40%"],
            Literal["30%"],
            Literal["20%"],
        ],
        year: str,
        limit_type: Union[Literal["mtsp"], Literal["il"]] = "mtsp",
    ):
        data = self.fetch()
        # print("income limit file data1:",percent)
        # print("income limit file data2:",data[year])
        print("income limit file data:",percent)
        if percent == "100%":
            return self.get_screen_ami(screen, "80%", year) / 0.8
        print("income limit file data3:",data[year][screen.white_label.state_code][screen.county][limit_type][percent][screen.household_size])
        return data[year][screen.white_label.state_code][screen.county][limit_type][percent][screen.household_size]


ami = Ami()


class Smi(GoogleSheetsCache):
    sheet_id = "1kH--2b_VMY6lG_DXe2Xdhps3Flfi_ZIqc9oViWcxndE"
    range_name = "SMI!A2:J"
    default = {}

    YEAR_INDEX = 0
    STATE_INDEX = 1
    LIMITS_START_INDEX = 2

    def update(self) -> dict[str, dict[str, dict[int, int]]]:  # type: ignore[override]
        data = super().update()

        smi = {}
        for row in data:
            year = row[self.YEAR_INDEX]
            state = row[self.STATE_INDEX]

            limits = {}
            for i, limit in enumerate(row[self.LIMITS_START_INDEX :]):
                limits[i + 1] = int(float(limit))

            if year not in smi:
                smi[year] = {}

            smi[year][state] = limits

        return smi

    def get_screen_smi(self, screen: Screen, year: int):
        data = self.fetch()

        return data[year][screen.white_label.state_code][screen.household_size]


smi = Smi()


class IncomeLimitsCache(GoogleSheetsCache):
    """
    Income Limits data used for
    - UtilityBillPay
    - WeatherizationAssistance
    """

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

    @staticmethod
    def _log_income_limit_error(message: str, county: str | None = None, **additional_extras) -> None:
        """
        Helper to log income limit validation errors to Sentry.

        Args:
            message: Error message describing the issue
            county: County name where the error occurred
            **additional_extras: Any additional context fields (e.g., household_size)
        """
        with new_scope() as scope:
            if county is not None:
                scope.set_extra("county", county)
            for key, value in additional_extras.items():
                scope.set_extra(key, value)
            capture_message(message, level="warning")

    def get_income_limit(self, screen: Screen) -> int | None:
        """
        Retrieves the income limit for the given household size and county.
        Logs any issues in calculating the income limit

        Args:
            screen: The screening object with household information

        Returns:
            Optional[int]: The income limit (or None if not found)
        """

        # Get county
        county = screen.county

        # Fetch income limits data (keys are "Adams County", "Alamosa County", etc.)
        limits_by_county = self.fetch()
        size_index = screen.household_size - 1 if screen.household_size else None

        # Check for valid income_limit
        if county not in limits_by_county:
            self._log_income_limit_error("County data not found", county=county)
            return None

        if limits_by_county.get(county) is None:
            self._log_income_limit_error("Data for county is not found", county=county)
            return None

        try:
            income_limit = limits_by_county[county][size_index]
        except IndexError:
            self._log_income_limit_error(
                "Invalid HH size given income limit data",
                county=county,
                household_size=screen.household_size,
            )
            return None
        except TypeError:
            self._log_income_limit_error(
                "Invalid HH size",
                county=county,
                household_size=screen.household_size,
            )
            return None

        if income_limit is None:
            self._log_income_limit_error(
                "Income limit for county and given HH Size is missing or misformatted",
                county=county,
                household_size=screen.household_size,
            )
            return None

        # valid income_limit
        return int(income_limit)


income_limits_cache = IncomeLimitsCache()
