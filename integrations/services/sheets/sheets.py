from decouple import config
from googleapiclient.discovery import build
from google.oauth2 import service_account
import json
import os
from integrations.util.cache import Cache


class GoogleSheets:
    google_creds = config("GOOGLE_APPLICATION_CREDENTIALS")
    if os.path.exists(google_creds):
        fh = open(google_creds)
        info = json.load(fh)
    else:
        info = json.loads(google_creds)
    creds = service_account.Credentials.from_service_account_info(info)
    service = build("sheets", "v4", credentials=creds)
    sheet = service.spreadsheets()

    class ColumnDoesNotExist(Exception):
        pass

    def __init__(self, spreadsheet_id: str, cell_range: str) -> None:
        self.spreadsheet_id = spreadsheet_id
        self.cell_range = cell_range

    def data(self) -> list[list[any]]:
        """
        return a list of rows in the cell range
        """
        result = self.sheet.values().get(spreadsheetId=self.spreadsheet_id, range=self.cell_range).execute()
        values = result.get("values", [])

        return values

    def data_by_column(self, *column_names: str) -> list[dict[str, any]]:
        """
        return an array of dictionaries containing the column names and their values
        """
        data = self.data()

        raw_column_names = data[0]

        remaining_rows = data[1:]

        needed_columns = {}
        for i, name in enumerate(raw_column_names):
            if name in column_names:
                needed_columns[i] = name

        if len(needed_columns) != len(column_names):
            self._raise_missing_columns(column_names, needed_columns.values())

        organized_data = []
        for row in remaining_rows:
            row_data = {}
            for i, value in enumerate(row):
                if i not in needed_columns:
                    continue

                row_data[needed_columns[i]] = value

            organized_data.append(row_data)

        return organized_data

    def print_raw_column_names(self):
        """
        print the column names of the spreadsheet

        WARN: this should only be used during development
        """
        raw_column_names = self.data()[0]

        for name in raw_column_names:
            print(repr(name))

    def _raise_missing_columns(self, needed_columns: list[str], existing_columns: list[str]):
        """
        raise an exception with the column names from needed_columns that are not in existing_columns
        """
        missing_columns = []

        for column in needed_columns:
            if column not in existing_columns:
                missing_columns.append(column)

        raise self.ColumnDoesNotExist(f"The following column headers are missing: {missing_columns}")


class GoogleSheetsCache(Cache):
    expire_time = 60 * 60 * 24
    default = []

    sheet_id = ""
    range_name = ""

    def update(self):
        sheet_values = GoogleSheets(self.sheet_id, self.range_name).data()

        return sheet_values
