"""
End-to-end ZIP/county validation through `/api/screens/`, against the real crosswalks.

`test_screen_serializer.LocationValidationTests` pins the rule on hand-built maps. These
load each white label's shipped `counties_by_zipcode` so the cases exercise the actual
naming conventions: suffixed (CO, KS, MO, NC, WA), bare (IL, TX), municipalities (MA),
plus MO's independent city.
"""

from unittest.mock import patch

from django.contrib.auth.models import Permission
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from authentication.models import User
from configuration.models import Configuration
from configuration.white_labels import white_label_config
from screener.models import Screen, WhiteLabel
from screener.serializers import ScreenSerializer

CROSSWALK_CODES = [code for code, data in white_label_config.items() if data.counties_by_zipcode]


class LocationValidationApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.white_labels = {}
        for code in CROSSWALK_CODES:
            white_label = WhiteLabel.objects.create(name=code, code=code, state_code=code.upper()[:2])
            Configuration.objects.create(
                white_label=white_label,
                name="counties_by_zipcode",
                data=white_label_config[code].counties_by_zipcode,
                active=True,
            )
            cls.white_labels[code] = white_label

        cls.user = User.objects.create_user(email_or_cell="location@example.com", password="password")
        cls.user.user_permissions.add(
            Permission.objects.get(codename="add_screen"), Permission.objects.get(codename="change_screen")
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _body(self, white_label, **location):
        return {
            "white_label": white_label,
            "household_members": [],
            "expenses": [],
            "current_benefits": [],
            **location,
        }

    def _post(self, white_label, **location):
        return self.client.post("/api/screens/", self._body(white_label, **location), format="json")

    def assertCreated(self, response, county):
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Screen.objects.get(uuid=response.data["uuid"]).county, county)

    def assertRejected(self, response, field, suggests=()):
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn(field, response.data)
        for name in suggests:
            self.assertIn(f"'{name}'", str(response.data[field]))

    # Happy paths: every naming convention is stored verbatim.

    def test_accepts_each_naming_convention(self):
        cases = [
            ("ks", "67202", "Sedgwick County"),  # suffixed
            ("mo", "63101", "St. Louis City"),  # independent city, no suffix
            ("mo", "63105", "St. Louis County"),  # ZIP split between the city and the county
            ("mo", "63105", "St. Louis City"),
            ("il", "60007", "Cook"),  # bare
            ("il", "60101", "DuPage"),
            ("tx", "78701", "Travis"),
            ("ma", "02119", "Boston"),  # municipality
            ("ma", "01002", "Shutesbury"),  # second town on a two-town ZIP
            ("co", "80202", "Denver County"),
        ]
        for code, zipcode, county in cases:
            with self.subTest(code=code, zipcode=zipcode, county=county):
                self.assertCreated(self._post(code, zipcode=zipcode, county=county), county)

    def test_blank_null_and_omitted_county_are_accepted(self):
        for location in ({"county": ""}, {"county": None}, {}):
            with self.subTest(location=location):
                response = self._post("co", zipcode="80202", **location)
                self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_surrounding_whitespace_is_trimmed_before_the_check(self):
        self.assertCreated(self._post("ks", zipcode="67202", county="  Sedgwick County "), "Sedgwick County")

    def test_every_crosswalk_pair_is_accepted(self):
        """No ZIP/county pair the browser dropdown can produce is ever rejected."""
        serializer = ScreenSerializer()
        for code in CROSSWALK_CODES:
            white_label = self.white_labels[code]
            crosswalk = Configuration.counties_by_zipcode(white_label)
            # One read per white label; the read path itself is covered above.
            with patch.object(Configuration, "counties_by_zipcode", return_value=crosswalk):
                for zipcode, counties in crosswalk.items():
                    for county in counties:
                        with self.subTest(code=code, zipcode=zipcode, county=county):
                            serializer._validate_location({"zipcode": zipcode, "county": county}, white_label)

    # Edge cases: values the crosswalk cannot produce are rejected, not silently stored.

    def test_rejects_bare_name_where_the_crosswalk_is_suffixed(self):
        self.assertRejected(self._post("ks", zipcode="67202", county="Sedgwick"), "county", ["Sedgwick County"])

    def test_ambiguous_st_louis_suggests_both_jurisdictions(self):
        response = self._post("mo", zipcode="63105", county="St. Louis")

        self.assertRejected(response, "county")
        self.assertIn("Did you mean 'St. Louis City' or 'St. Louis County'?", str(response.data["county"]))

    def test_rejects_case_mismatch_with_a_suggestion(self):
        self.assertRejected(self._post("ks", zipcode="67202", county="sedgwick county"), "county", ["Sedgwick County"])

    def test_rejects_suffix_where_the_crosswalk_is_bare(self):
        for code, zipcode, county in [("il", "60007", "Cook County"), ("tx", "78701", "Travis County")]:
            with self.subTest(code=code, county=county):
                self.assertRejected(self._post(code, zipcode=zipcode, county=county), "county")

    def test_rejects_ma_county_names_where_the_crosswalk_holds_towns(self):
        for zipcode, county in [("02119", "Suffolk"), ("02139", "Middlesex"), ("02119", "Suffolk County")]:
            with self.subTest(county=county):
                self.assertRejected(self._post("ma", zipcode=zipcode, county=county), "county")

    def test_rejects_zip_outside_the_white_label(self):
        self.assertRejected(self._post("ks", zipcode="63101"), "zipcode")

    def test_rejects_county_from_another_white_label(self):
        self.assertRejected(self._post("ks", zipcode="67202", county="St. Louis City"), "county")

    def test_update_of_a_legacy_bare_county_screen_is_rejected_until_corrected(self):
        """Screens written before the check keep their bare name until the next full write."""
        screen = Screen.objects.create(
            white_label=self.white_labels["ks"], zipcode="67202", county="Sedgwick", completed=False
        )
        url = f"/api/screens/{screen.uuid}/"

        stale = self.client.put(url, self._body("ks", zipcode="67202", county="Sedgwick"), format="json")
        self.assertRejected(stale, "county", ["Sedgwick County"])

        fixed = self.client.put(url, self._body("ks", zipcode="67202", county="Sedgwick County"), format="json")
        self.assertEqual(fixed.status_code, status.HTTP_200_OK, fixed.data)
        screen.refresh_from_db()
        self.assertEqual(screen.county, "Sedgwick County")
