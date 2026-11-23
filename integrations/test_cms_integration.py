"""Tests for the contact payload that HubSpotIntegration sends to HubSpot."""

from typing import Optional

from django.test import SimpleTestCase

from authentication.models import User
from integrations.services.cms_integration import TxHubSpotIntegration
from screener.models import Screen


class TestHubSpotContactData(SimpleTestCase):
    def _contact_data(self, referrer_code: Optional[str] = None, cell: Optional[str] = None) -> dict:
        user = User(first_name="Test", last_name="User", email="test@example.com", cell=cell, send_offers=True)
        screen = Screen(referrer_code=referrer_code)
        return TxHubSpotIntegration(user, screen)._hubspot_contact_data()

    def test_includes_referrer_code_when_present(self) -> None:
        contact = self._contact_data("propel")

        self.assertEqual(contact["mfb_referrer_code"], "propel")

    def test_omits_referrer_code_when_none(self) -> None:
        self.assertNotIn("mfb_referrer_code", self._contact_data(None))

    def test_omits_referrer_code_when_empty(self) -> None:
        # An empty string would overwrite an existing HubSpot value on update.
        self.assertNotIn("mfb_referrer_code", self._contact_data(""))

    def test_still_sends_uuid_and_state(self) -> None:
        contact = self._contact_data("propel")

        self.assertEqual(contact["states"], "TX")
        self.assertIn("uuid", contact)

    def test_sends_phone_when_present(self) -> None:
        self.assertEqual(self._contact_data(cell="+12145551234")["phone"], "+12145551234")

    def test_omits_phone_when_no_cell(self) -> None:
        # str(None) would send the literal "None" as the phone number.
        contact = self._contact_data(cell=None)

        self.assertNotIn("phone", contact)
        self.assertNotIn("None", contact.values())
