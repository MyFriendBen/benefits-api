"""Post a Twilio-signed inbound SMS to a local benefits-api, for Benji SMS work without Twilio.

Builds the form fields Twilio sends for an incoming message, signs them the way Twilio
does (X-Twilio-Signature over the URL and the sorted fields, keyed by the auth token),
and POSTs them. Local only: refuses unless DEBUG is on and the URL is on this machine.

    python manage.py fake_benji_sms_inbound "what is snap"
    python manage.py fake_benji_sms_inbound STOP --from +15555550123
    python manage.py fake_benji_sms_inbound "" --media 1
    python manage.py fake_benji_sms_inbound hi --sid SMaaaa...   # replay a SID
"""

import uuid
from typing import Any, Optional
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from twilio.request_validator import RequestValidator

# The inbound webhook arrives with MFB-2439; it should live at this path.
DEFAULT_PATH = "/api/assistant/sms/inbound/"
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "0.0.0.0"})
# 555-01xx numbers are reserved for fiction, so a fake sender is never a real person.
DEFAULT_FROM = "+15555550100"
DEFAULT_TO = "+15555550199"
# Long enough for a Celery-eager turn that calls ai-service inline.
POST_TIMEOUT_SECONDS = 60


def build_params(body: str, from_: str, to: str, sid: str, num_media: int) -> dict[str, str]:
    """The fields Twilio posts for one incoming message."""
    params = {
        "MessageSid": sid,
        "SmsSid": sid,
        "SmsMessageSid": sid,
        "AccountSid": "AC" + "0" * 32,
        "From": from_,
        "To": to,
        "Body": body,
        "NumMedia": str(num_media),
        "NumSegments": "1",
        "SmsStatus": "received",
        "ApiVersion": "2010-04-01",
    }
    for i in range(num_media):
        params[f"MediaUrl{i}"] = f"https://api.twilio.com/fake-media/{sid}/{i}"
        params[f"MediaContentType{i}"] = "image/jpeg"
    return params


def sign(token: str, url: str, params: dict[str, str]) -> str:
    return RequestValidator(token).compute_signature(url, params)


class Command(BaseCommand):
    help = "Post a Twilio-signed fake inbound SMS to the local Benji SMS webhook. Local only."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("body", help="Message text, as the person would type it")
        parser.add_argument("--from", dest="from_", default=DEFAULT_FROM, help=f"Sender (default {DEFAULT_FROM})")
        parser.add_argument("--to", default=None, help="Our number (default TWILIO_PHONE_NUMBER, else a fake one)")
        parser.add_argument("--sid", default=None, help="MessageSid; reuse one to test replay handling")
        parser.add_argument("--media", type=int, default=0, help="Number of fake attachments (NumMedia)")
        parser.add_argument("--url", default=None, help=f"Webhook URL (default BACKEND_DOMAIN + {DEFAULT_PATH})")
        parser.add_argument("--token", default=None, help="Signing token (default TWILIO_TOKEN)")

    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG:
            raise CommandError("Refusing to run: fake_benji_sms_inbound is for local work and needs DEBUG on.")

        url = options["url"] or settings.BACKEND_DOMAIN.rstrip("/") + DEFAULT_PATH
        host = urlparse(url).hostname
        if host not in LOCAL_HOSTS:
            raise CommandError(f"Refusing to post to {host!r}: only local URLs are allowed.")

        token = options["token"] or str(settings.TWILIO_TOKEN)
        if not token:
            raise CommandError("No signing token: set TWILIO_TOKEN or pass --token (any string the server also uses).")

        if options["media"] < 0:
            raise CommandError("--media cannot be negative.")

        sid = options["sid"] or "SM" + uuid.uuid4().hex
        to = options["to"] or str(settings.TWILIO_PHONE_NUMBER) or DEFAULT_TO
        params = build_params(options["body"], options["from_"], to, sid, options["media"])

        response = self._post(url, params, sign(token, url, params))

        self.stdout.write(f"POST {url}  MessageSid={sid}")
        self.stdout.write(f"{response.status_code}  {self._preview(response.text)}")

    def _post(self, url: str, params: dict[str, str], signature: str) -> requests.Response:
        try:
            return requests.post(
                url, data=params, headers={"X-Twilio-Signature": signature}, timeout=POST_TIMEOUT_SECONDS
            )
        except requests.ConnectTimeout as e:
            raise CommandError(f"Could not reach {url}: is the dev server running?") from e
        except requests.Timeout as e:
            raise CommandError(f"{url} took longer than {POST_TIMEOUT_SECONDS} s to answer.") from e
        except requests.ConnectionError as e:
            raise CommandError(f"Could not reach {url}: is the dev server running?") from e

    @staticmethod
    def _preview(text: Optional[str], limit: int = 500) -> str:
        text = text or ""
        return text if len(text) <= limit else text[:limit] + "…"
