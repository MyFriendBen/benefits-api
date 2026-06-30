from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from programs.models import Program
from screener.models import WhiteLabel
from screener.serializers import ScreenSerializer
from validations.models import Validation


class ValidateCommandPeVersionTest(TestCase):
    """Tests for the validate command's --pe-version override."""

    @classmethod
    def setUpTestData(cls):
        cls.white_label = WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")
        cls.program = Program.objects.new_program(white_label="co", name_abbreviated="snap")

    def setUp(self):
        self.out = StringIO()

        # Create a test screen the same way import_validations does.
        screen_data = {
            "white_label": "co",
            "is_test": True,
            "agree_to_tos": True,
            "is_13_or_older": True,
            "zipcode": "80202",
            "household_size": 1,
            "household_members": [
                {
                    "relationship": "headOfHousehold",
                    "age": 30,
                    "has_income": False,
                    "income_streams": [],
                    "insurance": {"none": True},
                }
            ],
            "expenses": [],
        }
        serializer = ScreenSerializer(data=screen_data)
        serializer.is_valid(raise_exception=True)
        self.screen = serializer.save()

        self.validation = Validation.objects.create(
            screen=self.screen,
            program_name="snap",
            eligible=True,
            value=Decimal("250.00"),
        )

    def test_invalid_pe_version_raises(self):
        """A --pe-version that is neither an exact version nor a valid alias errors out."""
        with self.assertRaises(CommandError):
            call_command("validate", "--pe-version", "bogus", stdout=self.out)

    @patch("validations.management.commands.validate.eligibility_results")
    def test_pe_version_alias_is_threaded_through(self, mock_eligibility_results):
        """A valid alias is forwarded to eligibility_results without changing the pin."""
        mock_eligibility_results.return_value = ([], None)

        call_command("validate", "--pe-version", "frontier", stdout=self.out)

        mock_eligibility_results.assert_called_with(self.screen, batch=True, pe_version="frontier")

    @patch("validations.management.commands.validate.eligibility_results")
    def test_default_runs_against_configured_pin(self, mock_eligibility_results):
        """With no --pe-version, eligibility_results is called with pe_version=None (configured pin)."""
        mock_eligibility_results.return_value = ([], None)

        call_command("validate", stdout=self.out)

        mock_eligibility_results.assert_called_with(self.screen, batch=True, pe_version=None)
