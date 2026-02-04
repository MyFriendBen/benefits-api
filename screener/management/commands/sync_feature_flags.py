from django.core.management.base import BaseCommand
from screener.models import WhiteLabel


class Command(BaseCommand):
    help = "Sync feature_flags JSONField with FEATURE_FLAGS definition for all WhiteLabels"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be changed without making changes",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        valid_keys = set(WhiteLabel.FEATURE_FLAGS.keys())

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no changes will be made\n"))

        self.stdout.write(f"Valid feature flags: {', '.join(sorted(valid_keys))}\n")

        total_updated = 0
        total_added = 0
        total_removed = 0

        for wl in WhiteLabel.objects.all():
            stored_flags = wl.feature_flags or {}
            stored_keys = set(stored_flags.keys())

            removed = stored_keys - valid_keys
            added = valid_keys - stored_keys

            if not removed and not added:
                continue

            self.stdout.write(f"\n{wl.name} ({wl.code}):")

            if removed:
                self.stdout.write(self.style.ERROR(f"  Removing: {', '.join(sorted(removed))}"))
                total_removed += len(removed)

            if added:
                for key in sorted(added):
                    default = WhiteLabel.FEATURE_FLAGS[key].default
                    self.stdout.write(self.style.SUCCESS(f"  Adding: {key} (default: {default})"))
                total_added += len(added)

            if not dry_run:
                synced_flags = {
                    key: stored_flags.get(key, WhiteLabel.FEATURE_FLAGS[key].default)
                    for key in valid_keys
                }
                wl.feature_flags = synced_flags
                wl.save(update_fields=["feature_flags"])

            total_updated += 1

        self.stdout.write("")
        if total_updated == 0:
            self.stdout.write(self.style.SUCCESS("All WhiteLabels are in sync."))
        else:
            action = "Would update" if dry_run else "Updated"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{action} {total_updated} WhiteLabel(s): "
                    f"+{total_added} flag(s) added, -{total_removed} flag(s) removed"
                )
            )
