import sys

from django.core.management.base import BaseCommand

from configuration.models import PolicyEngineConfig
from integrations.clients.policyengine.versions import CURRENT, _fetch_pe_versions, to_comparable_pe_version


class Command(BaseCommand):
    help = (
        "Exit non-zero if the pinned PolicyEngineConfig version is below PolicyEngine's `current`. "
        "PE retires versions older than `current` and 400s requests that pin one. An empty pin rides "
        "`current` and passes; an unreachable /versions/us warns and passes, so PE being down never "
        "blocks a deploy."
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

        current = data[CURRENT]
        pin_version = to_comparable_pe_version(pin)
        current_version = to_comparable_pe_version(current)
        if pin_version is None or current_version is None:
            self.stderr.write(
                self.style.WARNING(f"Could not compare pin {pin!r} with PE current {current!r}; skipping pin check.")
            )
            return

        if pin_version < current_version:
            self.stderr.write(
                self.style.ERROR(
                    f"Pinned PolicyEngine version {pin} is below PE current {current}. PolicyEngine may stop "
                    "serving it and return 400s on every screen. Bump the pin (Django admin > PolicyEngine "
                    "Version) or clear it to ride current."
                )
            )
            sys.exit(1)

        self.stdout.write(f"Pinned PolicyEngine version {pin} is at or above PE current {current}: OK")
