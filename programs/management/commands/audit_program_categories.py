"""
Snapshot the program-category payload each white label renders.

Run before and after the consolidation migration and diff the two files. Row
counts alone would miss the things most likely to go wrong — a category losing
its programs, a priority value changing the results order, or a curated
translation being replaced with machine output — because none of those change
how many rows exist.

Usage:
    python manage.py audit_program_categories > before.json
    python manage.py migrate
    python manage.py audit_program_categories > after.json
    diff <(jq -S . before.json) <(jq -S . after.json)

Read-only: it writes nothing.
"""

import json

from django.core.management.base import BaseCommand

from programs.models import Program, ProgramCategory
from screener.models import WhiteLabel


class Command(BaseCommand):
    help = "Print the program categories each white label renders, as JSON, for before/after diffing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--white-label",
            dest="white_label",
            help="Limit output to one white label code.",
        )
        parser.add_argument(
            "--languages",
            default="en-us,es",
            help="Comma-separated languages to capture translations for (default: en-us,es).",
        )

    def handle(self, *args, **options):
        languages = [lang.strip() for lang in options["languages"].split(",") if lang.strip()]

        white_labels = WhiteLabel.objects.all().order_by("code")
        if options["white_label"]:
            white_labels = white_labels.filter(code=options["white_label"])

        report = {
            "categories": self._categories(languages),
            "white_labels": {wl.code: self._white_label(wl) for wl in white_labels},
        }

        self.stdout.write(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))

    def _categories(self, languages):
        """Every category row, keyed by external_name, with the fields the API serializes."""
        categories = {}

        for category in ProgramCategory.objects.select_related("white_label", "icon").order_by("external_name"):
            names = {}
            for language in languages:
                try:
                    category.name.set_current_language(language)
                    names[language] = category.name.text
                except Exception:
                    names[language] = None

            categories[category.external_name] = {
                "shared": category.white_label is None,
                "white_label": category.white_label.code if category.white_label else None,
                "icon": category.icon.name if category.icon else None,
                "tax_category": category.tax_category,
                # Both drive the results page: priority overrides value-based
                # ordering, calculator selects the cap applied to the total.
                "priority": category.priority,
                "calculator": category.calculator or None,
                "names": names,
                "program_count": Program.objects.filter(category=category).count(),
                "active_program_count": Program.objects.filter(category=category, active=True).count(),
            }

        return categories

    def _white_label(self, white_label):
        """
        What this white label actually renders: its categories and, under each,
        its own active programs. This is the shape a shared category can get
        wrong, by pulling in another white label's programs.
        """
        programs = (
            Program.objects.filter(white_label=white_label, active=True)
            .select_related("category")
            .order_by("name_abbreviated")
        )

        by_category = {}
        uncategorized = []

        for program in programs:
            if program.category is None:
                uncategorized.append(program.name_abbreviated)
                continue
            by_category.setdefault(program.category.external_name, []).append(program.name_abbreviated)

        return {
            "categories": {name: sorted(names) for name, names in sorted(by_category.items())},
            "category_count": len(by_category),
            "active_program_count": programs.count(),
            "uncategorized_programs": sorted(uncategorized),
        }
