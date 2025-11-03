from typing import Literal, Union
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

    def update(self):
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

        if percent == "100%":
            return self.get_screen_ami(screen, "80%", year) / 0.8

        return data[year][screen.white_label.state_code][screen.county][limit_type][percent][screen.household_size]


ami = Ami()


class Smi(GoogleSheetsCache):
    sheet_id = "1kH--2b_VMY6lG_DXe2Xdhps3Flfi_ZIqc9oViWcxndE"
    range_name = "SMI!A2:J"
    default = {}

    YEAR_INDEX = 0
    STATE_INDEX = 1
    LIMITS_START_INDEX = 2

    def update(self):
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
