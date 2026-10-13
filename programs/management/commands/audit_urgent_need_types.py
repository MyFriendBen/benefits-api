"""
Snapshot the section label and icon each urgent need renders under.

Run before and after the consolidation migration and compare. Type external
names change in that migration, so the comparison is keyed by urgent need: for
each one, which label and icon it shows. Row counts alone would miss a resource
moving to the wrong section, an icon change, or a curated translation being
replaced with machine output.

Usage:
    python manage.py audit_urgent_need_types > before.json
    python manage.py migrate
    python manage.py audit_urgent_need_types --compare before.json

    # Snapshots taken elsewhere (e.g. on Heroku), compared without a database read:
    python manage.py audit_urgent_need_types --compare before.json --after after.json

Read-only: it writes nothing.
"""

import argparse
import json
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from programs.models import UrgentNeed, UrgentNeedType
from translations.models import Translation


class Command(BaseCommand):
    help = "Print the label and icon each urgent need renders under, as JSON, or compare against a snapshot."

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--languages",
            default="en-us,es",
            help="Comma-separated languages to capture labels for (default: en-us,es).",
        )
        parser.add_argument(
            "--compare",
            dest="compare",
            type=argparse.FileType("r", encoding="utf-8"),
            help="A snapshot from an earlier run. Prints what changed per urgent need instead of a snapshot.",
        )
        parser.add_argument(
            "--after",
            dest="after",
            type=argparse.FileType("r", encoding="utf-8"),
            help="With --compare, a second snapshot to compare against instead of the current database.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if options["after"] and not options["compare"]:
            raise CommandError("--after needs --compare")

        if options["after"]:
            self._compare(json.load(options["compare"]), json.load(options["after"]))
            return

        languages = [lang.strip() for lang in options["languages"].split(",") if lang.strip()]
        report = {"types": self._types(languages), "urgent_needs": self._urgent_needs(languages)}

        if options["compare"]:
            self._compare(json.load(options["compare"]), report)
            return

        self.stdout.write(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))

    def _names(self, translation: Translation, languages: list[str]) -> dict[str, str | None]:
        names = {}
        for language in languages:
            row = translation.get_lang(language)
            names[language] = row.text if row else None
        return names

    def _types(self, languages: list[str]) -> dict[str, dict[str, Any]]:
        """Every type row, keyed by external_name."""
        return {
            urgent_need_type.external_name: {
                "shared": urgent_need_type.white_label is None,
                "white_label": urgent_need_type.white_label.code if urgent_need_type.white_label else None,
                "icon": urgent_need_type.icon_name,
                "names": self._names(urgent_need_type.name, languages),
                "urgent_need_count": urgent_need_type.urgent_needs.count(),
            }
            for urgent_need_type in UrgentNeedType.objects.select_related("white_label", "icon", "name").order_by(
                "external_name"
            )
        }

    def _urgent_needs(self, languages: list[str]) -> dict[str, dict[str, Any]]:
        """Every urgent need, keyed by "<white label>:<external_name>", with the section it renders under."""
        needs = UrgentNeed.objects.select_related("white_label", "category_type__icon", "category_type__name")

        report = {}
        for need in needs.order_by("white_label__code", "external_name", "id"):
            key = f"{need.white_label.code if need.white_label else None}:{need.external_name or need.id}"
            category_type = need.category_type
            report[key] = {
                "type": category_type.external_name if category_type else None,
                "icon": category_type.icon_name if category_type else None,
                "names": self._names(category_type.name, languages) if category_type else None,
                "active": need.active,
                "show_on_current_benefits": need.show_on_current_benefits,
            }
        return report

    def _compare(self, before: dict[str, Any], after: dict[str, Any]) -> None:
        english = settings.LANGUAGE_CODE
        before_needs = before["urgent_needs"]
        after_needs = after["urgent_needs"]

        relabelled, icon_only, unchanged, lost_type, missing = [], [], [], [], []

        for key, old in sorted(before_needs.items()):
            new = after_needs.get(key)
            if new is None:
                missing.append(key)
                continue
            if old["type"] is not None and new["type"] is None:
                lost_type.append(key)
                continue

            old_label = (old["names"] or {}).get(english)
            new_label = (new["names"] or {}).get(english)
            if old_label != new_label:
                relabelled.append(f"{key}: {old_label!r} -> {new_label!r}")
            elif old["icon"] != new["icon"]:
                icon_only.append(f"{key}: icon {old['icon']} -> {new['icon']}")
            else:
                unchanged.append(key)

        added = sorted(set(after_needs) - set(before_needs))
        scoped = sorted(name for name, row in after["types"].items() if not row["shared"])

        self.stdout.write(f"Types: {len(before['types'])} -> {len(after['types'])} ({len(scoped)} white-label-scoped)")
        self.stdout.write(f"Urgent needs: {len(before_needs)} -> {len(after_needs)}")
        self.stdout.write(f"  relabelled: {len(relabelled)}")
        self.stdout.write(f"  icon only:  {len(icon_only)}")
        self.stdout.write(f"  unchanged:  {len(unchanged)}")
        self.stdout.write(f"  lost type:  {len(lost_type)}")
        self.stdout.write(f"  missing:    {len(missing)}")
        self.stdout.write(f"  added:      {len(added)}")

        for title, rows in (
            ("Relabelled", relabelled),
            ("Icon only", icon_only),
            ("Lost type", lost_type),
            ("Missing", missing),
            ("Added", added),
            ("White-label-scoped types", scoped),
        ):
            if rows:
                self.stdout.write(f"\n{title}:")
                for row in rows:
                    self.stdout.write(f"  {row}")
