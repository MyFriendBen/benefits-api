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

from programs.models import Program
from translations.models import BLANK_TRANSLATION_PLACEHOLDER

from .models import EligibilitySnapshot, Screen

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


def _latest_snapshot(screen: Screen):
    """Most recent successful, non-batch eligibility snapshot for this screen.

    The results page computes one of these on load, so by the time the user
    opens the assistant there is normally a fresh snapshot to read — far cheaper
    than recomputing eligibility (which calls PolicyEngine).
    """
    try:
        return (
            EligibilitySnapshot.objects.filter(screen=screen, is_batch=False, had_error=False)
            .prefetch_related("program_snapshots")
            .latest("submission_date")
        )
    except EligibilitySnapshot.DoesNotExist:
        return None


def _apply_urls_by_name(screen: Screen, name_abbreviations: list[str]) -> dict[str, str]:
    """Map name_abbreviated -> apply link for the given programs (one query).

    apply_button_link is a translated field; `.text` resolves it the same way
    eligibility_results resolves program.name.text. Blank/placeholder links are
    skipped so the assistant never receives an empty or placeholder URL.
    """
    if not name_abbreviations:
        return {}

    programs = Program.objects.filter(
        white_label=screen.white_label,
        name_abbreviated__in=name_abbreviations,
    ).select_related("apply_button_link")

    urls: dict[str, str] = {}
    for program in programs:
        try:
            link = (program.apply_button_link.text or "").strip()
        except Exception:
            link = ""
        if link and link != BLANK_TRANSLATION_PLACEHOLDER:
            urls[program.name_abbreviated] = link
    return urls


def _build_context(screen: Screen) -> dict:
    """Assemble the screen context passed to mfb-ai-service.

    Pulls the eligible programs from the latest snapshot, highest-value first,
    so the assistant can prioritize and explain them. Returns an empty list if
    no snapshot exists yet (the contract allows this).
    """
    eligible_programs = []
    snapshot = _latest_snapshot(screen)
    if snapshot is not None:
        rows = [p for p in snapshot.program_snapshots.all() if p.eligible]
        rows.sort(key=lambda p: p.estimated_value or 0, reverse=True)
        apply_urls = _apply_urls_by_name(screen, [p.name_abbreviated for p in rows])
        for p in rows:
            program = {
                "external_name": p.name_abbreviated,
                "name": p.name,
                # Whole dollars. Frequency is governed by value_type; see the
                # API contract's open question on units.
                "estimated_value": int(p.estimated_value) if p.estimated_value is not None else None,
                "estimated_application_time": p.estimated_application_time,
            }
            apply_url = apply_urls.get(p.name_abbreviated)
            if apply_url:
                program["apply_url"] = apply_url
            eligible_programs.append(program)

    return {
        "household": {"size": screen.household_size},
        "eligible_programs": eligible_programs,
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
