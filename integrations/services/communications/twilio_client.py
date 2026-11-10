"""The Twilio client every SMS sender in benefits-api uses.

One client per thread, so each thread reuses its own HTTP session and connections
(a ``requests.Session`` is not guaranteed thread-safe), rebuilt if the credentials
in settings change. Every request has a timeout: a stalled Twilio call must not hold
a web request past the Heroku router's 30 s, or a worker task forever.
"""

import threading

from django.conf import settings
from twilio.http.http_client import TwilioHttpClient
from twilio.rest import Client

TIMEOUT_SECONDS = 10

_local = threading.local()


def twilio_client() -> Client:
    credentials = (str(settings.TWILIO_SID), str(settings.TWILIO_TOKEN))
    cached = getattr(_local, "cached", None)
    if cached is None or cached[0] != credentials:
        client = Client(*credentials, http_client=TwilioHttpClient(timeout=TIMEOUT_SECONDS))
        _local.cached = (credentials, client)
    return _local.cached[1]
