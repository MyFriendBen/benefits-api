from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from configuration.models import Configuration
from programs.models import County
from screener.models import WhiteLabel


class AddCountiesTests(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Kansas", code="ks", state_code="KS")

    def _set_crosswalk(self, data):
        Configuration.objects.create(white_label=self.white_label, name="counties_by_zipcode", data=data, active=True)

    def test_creates_one_county_per_crosswalk_name(self):
        self._set_crosswalk(
            {
                "67202": {"Sedgwick County": "Sedgwick County"},
                "66044": {"Douglas County": "Douglas County"},
                "67203": {"Sedgwick County": "Sedgwick County"},
            }
        )

        call_command("add_counties", "ks", stdout=StringIO())

        names = County.objects.filter(white_label=self.white_label).values_list("name", flat=True)
        self.assertEqual(sorted(names), ["Douglas County", "Sedgwick County"])

    def test_missing_crosswalk_warns_and_creates_nothing(self):
        out = StringIO()

        call_command("add_counties", "ks", stdout=out)

        self.assertIn("not in the database", out.getvalue())
        self.assertFalse(County.objects.filter(white_label=self.white_label).exists())

    def test_malformed_crosswalk_fails_with_a_command_error(self):
        self._set_crosswalk(["not", "a", "dict"])

        with self.assertRaisesMessage(CommandError, "must be a JSON object"):
            call_command("add_counties", "ks", stdout=StringIO())
