"""The phone hash that stands in for a number in Benji SMS (MFB-2435).

The two things that must never break: every spelling of one number hashes the same
(or a texted reply never finds the binding the form created), and nothing is hashed
without the key.
"""

import hashlib
import hmac

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from integrations.services.communications import benji_sms_hash
from integrations.services.communications.benji_sms_hash import InvalidPhoneNumber, normalize, phone_hash

KEY = "k" * 64
OTHER_KEY = "j" * 64
E164 = "+13035550100"


@override_settings(BENJI_SMS_HASH_KEY=KEY)
class TestPhoneHash(SimpleTestCase):
    def test_is_hmac_sha256_of_the_e164_number_under_the_key(self):
        """Pins the algorithm. Changing it orphans every binding, like rotating the key."""
        expected = hmac.new(KEY.encode(), E164.encode(), hashlib.sha256).hexdigest()

        self.assertEqual(phone_hash(E164), expected)
        self.assertEqual(len(phone_hash(E164)), 64)

    def test_every_spelling_of_one_number_hashes_the_same(self):
        """The on-ramp form takes what the person typed; Twilio's `From` is E.164."""
        spellings = ["+13035550100", "(303) 555-0100", "303-555-0100", "303.555.0100", "+1 303 555 0100", "3035550100"]

        self.assertEqual({phone_hash(s) for s in spellings}, {phone_hash(E164)})

    def test_different_numbers_hash_differently(self):
        self.assertNotEqual(phone_hash("+13035550100"), phone_hash("+13035550101"))

    def test_the_key_changes_the_hash(self):
        with override_settings(BENJI_SMS_HASH_KEY=OTHER_KEY):
            other = phone_hash(E164)

        self.assertNotEqual(phone_hash(E164), other)

    def test_a_number_with_a_country_code_keeps_it(self):
        self.assertEqual(normalize("+44 20 7946 0958"), "+442079460958")


class TestPhoneHashKey(SimpleTestCase):
    def test_refuses_without_a_key(self):
        with override_settings(BENJI_SMS_HASH_KEY=""):
            with self.assertRaises(ImproperlyConfigured):
                phone_hash(E164)

    def test_refuses_when_the_setting_is_missing(self):
        with override_settings():
            from django.conf import settings

            del settings.BENJI_SMS_HASH_KEY
            with self.assertRaises(ImproperlyConfigured):
                phone_hash(E164)

    def test_refuses_a_short_key(self):
        with override_settings(BENJI_SMS_HASH_KEY="k" * (benji_sms_hash.MIN_KEY_LENGTH - 1)):
            with self.assertRaises(ImproperlyConfigured):
                phone_hash(E164)


@override_settings(BENJI_SMS_HASH_KEY=KEY)
class TestInvalidInput(SimpleTestCase):
    def test_rejects_text_that_is_not_a_number(self):
        for value in ["", "hello", "+1", "555"]:
            with self.subTest(value=value), self.assertRaises(InvalidPhoneNumber):
                phone_hash(value)

    def test_the_error_never_carries_the_input(self):
        """Sentry records the message and the chain; neither may hold the number."""
        value = "303555010012345678"
        with self.assertRaises(InvalidPhoneNumber) as caught:
            phone_hash(value)

        self.assertNotIn(value, str(caught.exception))
        self.assertIsNone(caught.exception.__cause__)
        self.assertTrue(caught.exception.__suppress_context__ or caught.exception.__context__ is None)
