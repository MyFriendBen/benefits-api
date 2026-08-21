import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.core.management import call_command
from django.core.management.base import BaseCommand

from programs.models import UrgentNeed


@dataclass
class ImportResults:
    successful: int = 0
    failed: int = 0
    skipped: int = 0


class Command(BaseCommand):
    help = """
    Import every urgent need configuration in import_urgent_need_config_data/data/ that
    does not already exist in the database.

    Unlike import_all_program_configs there is no tracking table: an urgent need counts as
    imported when an UrgentNeed row with the config's external_name exists.

    --override deletes and recreates urgent needs that already exist, discarding any edits
    made through the Django admin. It must be scoped with --white-label or --file so a bare
    run can never recreate every urgent need in the database.

    Usage:
      python manage.py import_all_urgent_need_configs
      python manage.py import_all_urgent_need_configs --dry-run
      python manage.py import_all_urgent_need_configs --list
      python manage.py import_all_urgent_need_configs --white-label ks
      python manage.py import_all_urgent_need_configs --override --white-label ks
      python manage.py import_all_urgent_need_configs --override --file ks_harvesters.json
    """

    DATA_DIR = Path(__file__).parent / "import_urgent_need_config_data" / "data"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be imported without making any changes",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            dest="list_status",
            help="List all config files and whether the urgent need already exists",
        )
        parser.add_argument(
            "--white-label",
            type=str,
            dest="white_label",
            help="Only process configs for this white label code",
        )
        parser.add_argument(
            "--file",
            type=str,
            action="append",
            dest="files",
            help="Only process this config filename; repeatable",
        )
        parser.add_argument(
            "--override",
            action="store_true",
            help=(
                "Recreate urgent needs that already exist instead of skipping them. "
                "Requires --white-label or --file."
            ),
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if not self.DATA_DIR.exists():
            self.stderr.write(self.style.ERROR(f"Data directory not found: {self.DATA_DIR}"))
            return

        override = options["override"]
        if override and not (options.get("white_label") or options.get("files")):
            self.stderr.write(
                self.style.ERROR("--override discards admin edits, so it must be scoped with --white-label or --file.")
            )
            return

        configs = self._discover_configs(options.get("white_label"), options.get("files"))
        if not configs:
            self.stdout.write(self.style.WARNING("No matching JSON configuration files found."))
            return

        existing = set(UrgentNeed.objects.exclude(external_name=None).values_list("external_name", flat=True))

        if options["list_status"]:
            return self._show_status(configs, existing)

        pending = [c for c in configs if override or c["external_name"] not in existing]
        if not pending:
            self.stdout.write(self.style.SUCCESS("\n✓ All urgent need configurations already exist.\n"))
            return

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(f"\n[Dry run] {len(pending)} config(s) would be imported:\n"))
            for config in pending:
                self.stdout.write(f"  • {config['path'].name} ({config['white_label']}/{config['external_name']})")
            self.stdout.write("")
            return

        results = self._execute_imports(pending, existing, override)
        self.stdout.write(self.style.WARNING(f"\n{'=' * 60}"))
        self.stdout.write(self.style.SUCCESS("Import Complete"))
        self.stdout.write(self.style.WARNING(f"{'=' * 60}"))
        self.stdout.write(f"  Successful: {results.successful}")
        self.stdout.write(f"  Skipped:    {results.skipped}")
        self.stdout.write(f"  Failed:     {results.failed}\n")

    def _discover_configs(self, white_label: str | None, files: list[str] | None = None) -> list[dict[str, Any]]:
        wanted = set(files) if files else None
        configs = []
        for path in sorted(self.DATA_DIR.glob("*.json")):
            if wanted is not None and path.name not in wanted:
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                config = {
                    "path": path,
                    "white_label": data["white_label"]["code"],
                    "external_name": data["need"]["external_name"],
                }
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                self.stdout.write(self.style.ERROR(f"✗ Unreadable config {path.name}: {e}"))
                continue
            if white_label and config["white_label"] != white_label:
                continue
            configs.append(config)
        return configs

    def _execute_imports(self, pending: list[dict[str, Any]], existing: set[str], override: bool) -> ImportResults:
        results = ImportResults()
        self.stdout.write(f"\nImporting {len(pending)} urgent need config(s)...\n")

        for config in pending:
            name = config["path"].name
            self.stdout.write(self.style.WARNING(f"\n{'─' * 60}"))
            self.stdout.write(f"Importing: {name} ({config['white_label']}/{config['external_name']})")
            self.stdout.write(self.style.WARNING(f"{'─' * 60}"))

            args = [str(config["path"])]
            if override and config["external_name"] in existing:
                args.append("--override")

            try:
                call_command("import_urgent_need_config", *args)
            except Exception as e:
                results.failed += 1
                self.stdout.write(self.style.ERROR(f"✗ Failed: {name} - {e}"))
                continue

            if UrgentNeed.objects.filter(external_name=config["external_name"]).exists():
                results.successful += 1
            else:
                # import_urgent_need_config returns without raising when the need already
                # exists and --override was not passed.
                results.skipped += 1

        return results

    def _show_status(self, configs: list[dict[str, Any]], existing: set[str]) -> None:
        self.stdout.write(self.style.WARNING(f"\n{'=' * 60}"))
        self.stdout.write("Urgent Need Config Import Status")
        self.stdout.write(self.style.WARNING(f"{'=' * 60}\n"))

        imported = pending = 0
        for config in configs:
            if config["external_name"] in existing:
                imported += 1
                marker = self.style.SUCCESS("✓ exists ")
            else:
                pending += 1
                marker = self.style.WARNING("• pending")
            self.stdout.write(f"  {marker} {config['path'].name} ({config['white_label']})")

        self.stdout.write(f"\n  Existing: {imported}    Pending: {pending}    Total: {len(configs)}\n")
