from django.core.management.base import BaseCommand, CommandError

from configuration.models import PolicyEngineConfig
from integrations.clients.policyengine.versions import CURRENT, FRONTIER, _fetch_pe_versions


class Command(BaseCommand):
    help = (
        "Exit non-zero if the pinned PolicyEngineConfig version is not one PolicyEngine serves. PE serves "
        "exactly two versions, `current` and `frontier`; anything else (including an older `current` that PE "
        "has since moved past) gets a 422 unsupported_version. A pin at `frontier` passes with a warning, an "
        "empty pin rides `current` and passes, and an unreachable or malformed /versions/us warns and passes, "
        "so PE being down never blocks a deploy."
    )

    def handle(self, *args, **options):
        pin = PolicyEngineConfig.current_version()
        if not pin:
            self.stdout.write("PolicyEngine version is unpinned (rides current): OK")
            return

        # Bypass the cache: a copy up to an hour old would hide the drift we are checking for.
        data = _fetch_pe_versions(use_cache=False)
        if not data:
            self.stderr.write(self.style.WARNING("Could not reach PolicyEngine /versions/us; skipping pin check."))
            return

        current = data.get(CURRENT)
        frontier = data.get(FRONTIER)
        if not isinstance(current, str) or not current:
            self.stderr.write(
                self.style.WARNING(f"Unexpected PolicyEngine /versions/us payload ({data!r}); skipping pin check.")
            )
            return

        if pin == current:
            self.stdout.write(f"Pinned PolicyEngine version {pin} matches PE current: OK")
            return

        if pin == frontier:
            self.stderr.write(
                self.style.WARNING(
                    f"Pinned PolicyEngine version {pin} is PE frontier, not current ({current}). "
                    "PolicyEngine serves it, but prod should stay on current."
                )
            )
            return

        raise CommandError(
            f"Pinned PolicyEngine version {pin} is not served by PolicyEngine "
            f"(current {current}, frontier {frontier}); every screen will get 422 unsupported_version. "
            "Set the pin to current (Django admin > PolicyEngine Version) or clear it."
        )
