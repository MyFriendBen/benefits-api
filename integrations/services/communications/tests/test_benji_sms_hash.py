"""The phone hash that stands in for a number in Benji SMS (MFB-2435).

The two things that must never break: every spelling of one number hashes the same
(or a texted reply never finds the binding the form created), and nothing is hashed
without the key.
"""

import hashlib
import hmac

import pytest
from django.core.exceptions import ImproperlyConfigured
from pytest_django.fixtures import SettingsWrapper

from integrations.services.communications import benji_sms_hash
from integrations.services.communications.benji_sms_hash import InvalidPhoneNumber, normalize, phone_hash

KEY = "k" * 64
OTHER_KEY = "j" * 64
E164 = "+13035550100"


@pytest.fixture
def keyed(settings: SettingsWrapper) -> SettingsWrapper:
    settings.BENJI_SMS_HASH_KEY = KEY
    return settings


def test_is_hmac_sha256_of_the_e164_number_under_the_key(keyed: SettingsWrapper) -> None:
    """Pins the algorithm. Changing it orphans every binding, like rotating the key."""
    expected = hmac.new(KEY.encode(), E164.encode(), hashlib.sha256).hexdigest()

    assert phone_hash(E164) == expected
    assert len(phone_hash(E164)) == 64


def test_every_spelling_of_one_number_hashes_the_same(keyed: SettingsWrapper) -> None:
    """The on-ramp form takes what the person typed; Twilio's `From` is E.164."""
    spellings = ["+13035550100", "(303) 555-0100", "303-555-0100", "303.555.0100", "+1 303 555 0100", "3035550100"]

    assert {phone_hash(s) for s in spellings} == {phone_hash(E164)}


def test_different_numbers_hash_differently(keyed: SettingsWrapper) -> None:
    assert phone_hash("+13035550100") != phone_hash("+13035550101")


def test_the_key_changes_the_hash(keyed: SettingsWrapper) -> None:
    first = phone_hash(E164)
    keyed.BENJI_SMS_HASH_KEY = OTHER_KEY

    assert phone_hash(E164) != first


def test_a_number_with_a_country_code_keeps_it() -> None:
    assert normalize("+44 20 7946 0958") == "+442079460958"


@pytest.mark.parametrize("value", ["555-0100", "5550100", "+1 555 0100"])
def test_a_local_only_number_is_refused(value: str) -> None:
    """No area code: these would all format as +15550100 and share one hash."""
    with pytest.raises(InvalidPhoneNumber):
        normalize(value)


def test_refuses_without_a_key(settings: SettingsWrapper) -> None:
    settings.BENJI_SMS_HASH_KEY = ""

    with pytest.raises(ImproperlyConfigured):
        phone_hash(E164)


def test_refuses_when_the_setting_is_missing(settings: SettingsWrapper) -> None:
    del settings.BENJI_SMS_HASH_KEY

    with pytest.raises(ImproperlyConfigured):
        phone_hash(E164)


def test_refuses_a_short_key(settings: SettingsWrapper) -> None:
    settings.BENJI_SMS_HASH_KEY = "k" * (benji_sms_hash.MIN_KEY_LENGTH - 1)

    with pytest.raises(ImproperlyConfigured):
        phone_hash(E164)


@pytest.mark.parametrize("value", ["", "hello", "+1", "555"])
def test_rejects_text_that_is_not_a_number(keyed: SettingsWrapper, value: str) -> None:
    with pytest.raises(InvalidPhoneNumber):
        phone_hash(value)


def test_the_error_never_carries_the_input(keyed: SettingsWrapper) -> None:
    """Sentry records the message and the chain; neither may hold the number."""
    value = "303555010012345678"
    with pytest.raises(InvalidPhoneNumber) as caught:
        phone_hash(value)

    assert value not in str(caught.value)
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ or caught.value.__context__ is None
