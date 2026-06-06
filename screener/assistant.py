"""Benbot assistant proxy views.

These are the Layer 1 (browser-facing) endpoints. They authenticate/resolve the
screen, enforce the `benbot` feature flag, assemble the screen context, and proxy
to mfb-ai-service (Layer 2). The browser never calls mfb-ai-service directly.

See the ai-service repo's docs/ for the full API contract.
"""

import os

import requests
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, views
from rest_framework.response import Response

from .models import Screen

# Where mfb-ai-service lives, and the shared service token (must match the
# service's SERVICE_AUTH_TOKEN). Both come from the environment.
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8080")
AI_SERVICE_TOKEN = os.getenv("AI_SERVICE_TOKEN", "")
AI_SERVICE_TIMEOUT = 60


def _ai_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if AI_SERVICE_TOKEN:
        headers["Authorization"] = f"Bearer {AI_SERVICE_TOKEN}"
    return headers


def _build_context(screen: Screen) -> dict:
    """Assemble the screen context passed to mfb-ai-service.

    NOTE (v0): eligible_programs is left empty for now. Populating it from the
    eligibility calculation is a follow-up; the API contract allows an empty list.
    """
    return {
        "household": {"size": screen.household_size},
        "eligible_programs": [],  # TODO: populate from eligibility results
    }


def _proxy(method: str, path: str, json_body: dict) -> Response:
    """Forward a request to mfb-ai-service and pass its response through."""
    try:
        resp = requests.request(
            method,
            f"{AI_SERVICE_URL}{path}",
            json=json_body,
            headers=_ai_headers(),
            timeout=AI_SERVICE_TIMEOUT,
        )
    except requests.RequestException as e:
        return Response(
            {"error": {"code": "ai_upstream_error", "message": str(e)}},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    try:
        body = resp.json()
    except ValueError:
        body = {"error": {"code": "ai_upstream_error", "message": "Non-JSON response from AI service."}}
        return Response(body, status=status.HTTP_502_BAD_GATEWAY)
    return Response(body, status=resp.status_code)


class AssistantStartView(views.APIView):
    """POST: open (or resume) a Benbot conversation for a screen."""

    permission_classes = [permissions.AllowAny]

    def post(self, request, screen_uuid):
        screen = get_object_or_404(Screen, uuid=screen_uuid)
        if not screen.white_label.has_feature("benbot"):
            return Response({"error": {"code": "assistant_disabled"}}, status=status.HTTP_403_FORBIDDEN)

        payload = {
            "screen_uuid": str(screen.uuid),
            "white_label": screen.white_label.code,
            "locale": request.data.get("locale", "en-US"),
            "context": _build_context(screen),
        }
        return _proxy("POST", "/v1/conversations", payload)


class AssistantMessageView(views.APIView):
    """POST: send a user message to an existing Benbot conversation."""

    permission_classes = [permissions.AllowAny]

    def post(self, request, screen_uuid, conversation_id):
        screen = get_object_or_404(Screen, uuid=screen_uuid)
        if not screen.white_label.has_feature("benbot"):
            return Response({"error": {"code": "assistant_disabled"}}, status=status.HTTP_403_FORBIDDEN)

        payload = {
            "text": request.data.get("text", ""),
            "client_message_id": request.data.get("client_message_id"),
        }
        return _proxy("POST", f"/v1/conversations/{conversation_id}/messages", payload)
