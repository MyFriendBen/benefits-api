"""The keyed hash that stands in for a phone number in Benji SMS (MFB-2435).

The phone number is never written to our database; ``BenjiSmsBinding.phone_hash`` and
``BenjiSmsStrangerReply.phone_hash`` hold this instead (MFB-1916 proposal v2, decision
3; privacy companion §2). Inbound routing, STOP, expiry and a deletion request all work
by hashing the number in hand and looking the hash up.

Two properties matter:

1. **The same number always hashes the same way.** The on-ramp form submits whatever
   the person typed ("(303) 555-0100"); Twilio's webhook sends E.164 ("+13035550100").
   Both are parsed and formatted as E.164 before hashing, or a texted reply would never
   find the binding the form created.
2. **Without the key, nothing is hashed.** A keyed hash is still personal data,
   reversible by anyone holding the key and a candidate number, so the key lives in
   config and the password manager. A missing or short key raises rather than falling
   back to a known value, which would make every hash trivially reversible.

The number never appears in an error message, a log line or a chained exception.
"""

import hashlib
import hmac

import phonenumbers
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

SETTING = "BENJI_SMS_HASH_KEY"
DEFAULT_REGION = "US"
# 32 characters: a token_hex(16) at the very least. The documented generator in
# settings.py produces 64.
MIN_KEY_LENGTH = 32


class InvalidPhoneNumber(ValueError):
    """The input is not a phone number. Never carries the input."""

    def __init__(self) -> None:
        super().__init__("Not a phone number")


def normalize(number: str) -> str:
    """The E.164 form of ``number``, reading numbers without a ``+`` as US numbers.

    Checks that the number is a possible length for its country, not that it is
    assigned: that is the on-ramp's job, and a fixed reply to an unassigned number is
    harmless. Raises ``InvalidPhoneNumber``.

    A number that is only possible as a local number is refused: a 7-digit US number
    with no area code ("555-0100") would otherwise format as "+15550100", and every
    such number from every area code would share one hash. ``is_possible_number``
    accepts those, so the reason is checked exactly.
    """
    try:
        parsed = phonenumbers.parse(number, DEFAULT_REGION)
    except phonenumbers.NumberParseException:
        raise InvalidPhoneNumber() from None
    if phonenumbers.is_possible_number_with_reason(parsed) != phonenumbers.ValidationResult.IS_POSSIBLE:
        raise InvalidPhoneNumber()
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def _key() -> bytes:
    key = str(getattr(settings, SETTING, "") or "")
    if len(key) < MIN_KEY_LENGTH:
        raise ImproperlyConfigured(f"{SETTING} is missing or shorter than {MIN_KEY_LENGTH} characters")
    return key.encode()


def phone_hash(number: str) -> str:
    """HMAC-SHA256 of the number's E.164 form, as 64 hex characters.

    Raises ``InvalidPhoneNumber`` for input that is not a phone number and
    ``ImproperlyConfigured`` when ``BENJI_SMS_HASH_KEY`` is unset or too short.
    """
    return hmac.new(_key(), normalize(number).encode(), hashlib.sha256).hexdigest()
