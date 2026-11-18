"""Twilio's request signature: how the Benji SMS webhooks know a request is Twilio's.

Twilio signs each webhook with the account's auth token, over the URL it was told to
post to and the form fields it sends (``X-Twilio-Signature``). The inbound webhook
(MFB-2439), its fallback, and the status callback (MFB-2441) all use this check, and
reject an unsigned request before any lookup.

THE URL IS THE PUBLIC ONE. Behind the Heroku router the dyno sees plain http and an
internal host, so the request as Django sees it is not what Twilio signed. The URL is
rebuilt from ``BACKEND_DOMAIN`` and the request's path and query string, never from the
``Host`` or ``X-Forwarded-*`` headers, which the caller controls. ``BACKEND_DOMAIN``
must therefore be the public https origin configured on the Twilio number, in every
environment (docs/BENJI_SMS_INBOUND.md).

The connection-override fragment on the configured URL (``#rc=2&rp=all``) is not part of
the signature, and never reaches the server, so nothing here handles it.

WITHOUT A TOKEN, NOTHING IS SIGNED. An unset ``TWILIO_TOKEN`` refuses every request
rather than validating against an empty key, which anyone could compute.
"""

from django.conf import settings
from django.http import QueryDict
from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView
from twilio.request_validator import RequestValidator

SIGNATURE_HEADER = "X-Twilio-Signature"


def public_url(request: Request) -> str:
    """The URL Twilio posted to, as Twilio wrote it: public origin, path and query."""
    return str(settings.BACKEND_DOMAIN).rstrip("/") + request.get_full_path()


def is_signed_by_twilio(request: Request) -> bool:
    """Whether the request carries a valid Twilio signature for its URL and form fields."""
    token = str(settings.TWILIO_TOKEN or "")
    signature = request.headers.get(SIGNATURE_HEADER, "")
    if not token or not signature:
        return False
    data = request.data
    # Twilio posts a form. Anything else (a JSON body parses to a plain dict) is not
    # Twilio's, whatever its signature header says.
    if not isinstance(data, QueryDict):
        return False
    return bool(RequestValidator(token).validate(public_url(request), data.dict(), signature))


class SignedByTwilio(permissions.BasePermission):
    """DRF permission: the request is Twilio's. Runs before the view touches the database."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        return is_signed_by_twilio(request)
