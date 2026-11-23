from django.http import HttpResponseForbidden, HttpResponseBadRequest
from sentry_sdk import capture_message
from rest_framework.exceptions import Throttled
from rest_framework.views import exception_handler


def catch_403_view(*args, **kwargs):
    capture_message("Unauthorized", level="warning")

    return HttpResponseForbidden("Forbidden")


def catch_400_view(*args, **kwargs):
    capture_message("Bad Request", level="warning")

    return HttpResponseBadRequest("Bad Request")


def drf_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        return None

    # A throttle refusing a request is the throttle working, and the volume it
    # absorbs would use up Sentry's event quota and bury real errors. Django's
    # request log still records each 429, and the Save My Results throttle logs
    # which limit fired.
    if isinstance(exc, Throttled):
        return response

    capture_message(
        response.reason_phrase,
        level="warning",
    )

    return response
