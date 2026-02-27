import argparse
import json
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from programs.models import (
    CategoryIconName,
    County,
    ExpenseType,
    FederalPoveryLimit,
    UrgentNeed,
    UrgentNeedCategory,
    UrgentNeedFunction,
    UrgentNeedType,
)
from programs.programs.urgent_needs import urgent_need_functions
from screener.models import WhiteLabel
from programs.management.commands._translation_utils import TranslationImportMixin


def truncate(text: str, max_length: int = 50) -> str:
    """Truncate text with ellipsis if it exceeds max_length."""
    return f"{text[:max_length]}..." if len(text) > max_length else text


class Command(TranslationImportMixin, BaseCommand):
    help = """
    Import an Urgent Need from a JSON configuration file.

    This mirrors the import_program_config flow, creating/associating:
    - UrgentNeed with translations
    - UrgentNeedType (category_type) with translation and icon
    - UrgentNeedCategory (type_short)
    - Functions, counties, expense filters, FPL year

        Usage:
            python manage.py import_urgent_need_config <path/to/config.json>
            python manage.py import_urgent_need_config <path/to/config.json> --dry-run
            python manage.py import_urgent_need_config <path/to/config.json> --override
    """

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "config_file",
            type=argparse.FileType("r", encoding="utf-8"),
            help="Path to the JSON configuration file",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be created without making any changes",
        )
        parser.add_argument(
            "--override",
            action="store_true",
            help="Delete and recreate an existing Urgent Need if it already exists",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        config_file = options["config_file"]
        dry_run = options.get("dry_run", False)
        override = options.get("override", False)

        try:
            config = json.load(config_file)
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON file: {e}")

        self._validate_config(config)

        white_label_code = config["white_label"]["code"]
        need_config = config["need"]
        external_name = need_config["external_name"]

        # Verify white label exists
        try:
            white_label = WhiteLabel.objects.get(code=white_label_code)
        except WhiteLabel.DoesNotExist:
            raise CommandError(f"WhiteLabel with code '{white_label_code}' not found") from None

        existing_need = UrgentNeed.objects.filter(external_name=external_name).first()
        overriding = bool(existing_need and override)

        # --- DRY RUN FIRST ---
        if dry_run:
            if existing_need:
                self.stdout.write(
                    self.style.WARNING(
                        f"Urgent Need '{external_name}' already exists (ID: {existing_need.id}). "
                        f"Dry run will show what would be updated."
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Urgent Need '{external_name}' does not exist. " f"Dry run will show what would be created."
                    )
                )

            self._print_dry_run_report(config, white_label_code, external_name)
            return

        # --- REAL EXECUTION VALIDATION ---
        if existing_need and not override:
            self.stdout.write(
                self.style.WARNING(
                    f"Urgent Need '{external_name}' already exists (ID: {existing_need.id}). "
                    f"Use --override to delete and recreate it."
                )
            )
            return

        try:
            with transaction.atomic():
                if overriding and existing_need:
                    self._delete_need(existing_need)
                    existing_need = None

                need = UrgentNeed.objects.new_urgent_need(
                    white_label=white_label_code,
                    name=external_name,
                    phone_number=None,
                )

                self.stdout.write(self.style.SUCCESS(f"\n[Urgent need: {external_name}]"))
                self.stdout.write(f"White Label: {white_label_code}\n")

                self._import_need(need, white_label, need_config)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n✓ Successfully {'recreated' if overriding else 'created'} urgent need: {external_name} "
                        f"(ID: {need.id})\n"
                    )
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\nError during import: {e}\n" f"All changes have been rolled back."))
            raise

    # --------------------------------------------------------------------------------------
    # Validation & Dry Run
    # --------------------------------------------------------------------------------------
    def _validate_config(self, config: dict[str, Any]) -> None:
        required_top = ["white_label", "need"]
        for field in required_top:
            if field not in config:
                raise CommandError(f"Missing required field: {field}")

        if "code" not in config["white_label"]:
            raise CommandError("Missing required field 'white_label.code'")

        need = config["need"]
        required_need = [
            "external_name",
            "category_type",
            "type_short",
            "translations",
        ]
        for field in required_need:
            if field not in need:
                raise CommandError(f"Missing required field 'need.{field}'")

        translations = need["translations"]
        required_translations = [
            "name",
            "description",
            "link",
            "warning",
            "website_description",
        ]
        for field in required_translations:
            if field not in translations:
                raise CommandError(f"Missing required translation 'translations.{field}'")

        if not isinstance(need.get("type_short", []), list) or len(need["type_short"]) == 0:
            raise CommandError("'need.type_short' must be a non-empty array")

        functions = need.get("functions", [])
        if functions and not isinstance(functions, list):
            raise CommandError("'need.functions' must be an array if provided")

        category_type = need["category_type"]
        if "external_name" not in category_type:
            raise CommandError("Missing required field 'need.category_type.external_name'")

    def _print_dry_run_report(self, config: dict[str, Any], white_label_code: str, external_name: str) -> None:
        self.stdout.write(self.style.WARNING("\n=== DRY RUN MODE ==="))
        self.stdout.write("No changes will be made to the database.\n")

        need = config["need"]
        translations = need["translations"]
        category_type = need["category_type"]

        self.stdout.write(self.style.SUCCESS("White Label:"))
        self.stdout.write(f"  code: {white_label_code}\n")

        self.stdout.write(self.style.SUCCESS("Urgent need:"))
        self.stdout.write(f"  external_name: {external_name}")
        self.stdout.write(f"  type_short: {', '.join(need['type_short'])}")
        if need.get("functions"):
            self.stdout.write(f"  functions: {', '.join(need['functions'])}")
        if need.get("counties"):
            self.stdout.write(f"  counties: {', '.join(need['counties'])}")
        if need.get("required_expense_types"):
            self.stdout.write(f"  required_expense_types: {', '.join(need['required_expense_types'])}")
        if need.get("fpl"):
            self.stdout.write(f"  fpl: {need['fpl'].get('year', 'N/A')} ({need['fpl'].get('period', 'N/A')})")
        self.stdout.write(f"  active: {need.get('active', True)}")
        self.stdout.write(f"  low_confidence: {need.get('low_confidence', False)}")
        self.stdout.write(f"  show_on_current_benefits: {need.get('show_on_current_benefits', True)}")

        self.stdout.write(self.style.SUCCESS("\nTranslations:"))
        for key, value in translations.items():
            self.stdout.write(f"  {key}: {truncate(value)}")

        self.stdout.write(self.style.SUCCESS("\nCategory Type:"))
        self.stdout.write(f"  external_name: {category_type['external_name']}")
        if category_type.get("name"):
            self.stdout.write(f"  name: {truncate(category_type['name'])}")
        if category_type.get("icon"):
            self.stdout.write(f"  icon: {category_type['icon']}")

        self.stdout.write(self.style.WARNING("\n=== END DRY RUN ===\n"))

    # --------------------------------------------------------------------------------------
    # Import helpers
    # --------------------------------------------------------------------------------------
    def _delete_need(self, need: UrgentNeed) -> None:
        """Delete an urgent need before re-importing in override mode."""
        name = need.external_name or f"ID {need.id}"
        self.stdout.write(self.style.WARNING("\n[Override Mode] Deleting existing urgent need..."))
        need.delete()
        self.stdout.write(f"  Deleted urgent need: {name}\n")

    def _import_need(self, need: UrgentNeed, white_label: WhiteLabel, config: dict[str, Any]) -> UrgentNeed:
        translations = config.get("translations", {})

        # Basic flags and phone
        for field, default in [
            ("active", True),
            ("low_confidence", False),
            ("show_on_current_benefits", True),
        ]:
            setattr(need, field, config.get(field, default))

        if "phone_number" in config:
            need.phone_number = config.get("phone_number")

        # FPL year
        if fpl_data := config.get("fpl"):
            fpl_year = fpl_data["year"]
            fpl_period = fpl_data.get("period", "annual")
            fpl, created = FederalPoveryLimit.objects.get_or_create(year=fpl_year, defaults={"period": fpl_period})
            if not created and fpl.period != fpl_period:
                self.stdout.write(
                    self.style.WARNING(
                        f"  [FPL] Existing FPL record for year {fpl_year} has period '{fpl.period}', "
                        f"but config specifies '{fpl_period}'. "
                        f"The existing period will be kept to avoid affecting other records."
                    )
                )
            need.year = fpl

        # Category type (UrgentNeedType)
        category_type = self._get_or_create_category_type(white_label, config["category_type"])
        need.category_type = category_type

        # type_short categories
        self._set_categories(need, config["type_short"])

        # Functions
        self._set_functions(need, config.get("functions", []))

        # Counties (optional)
        self._set_counties(need, white_label, config.get("counties", []))

        # Expense filters (optional)
        self._set_expense_filters(need, config.get("required_expense_types", []))

        need.white_label = white_label
        need.save()

        # Translations for need
        self._import_need_translations(need, translations)

        # Optional translation for category type name
        if name := config.get("category_type", {}).get("name"):
            self._bulk_update_entity_translations(
                category_type,
                {"name": name},
                "category_type",
                UrgentNeedType.objects.translated_fields,
            )

        return need

    def _get_or_create_category_type(self, white_label: WhiteLabel, config: dict[str, Any]) -> UrgentNeedType:
        external_name = config["external_name"]
        icon_name = config.get("icon")

        category_type = UrgentNeedType.objects.filter(external_name=external_name).first()
        if not category_type:
            # Ensure icon exists if provided, manager expects string name
            if icon_name:
                CategoryIconName.objects.get_or_create(name=icon_name)

            category_type = UrgentNeedType.objects.new_urgent_need_type(
                white_label=white_label.code,
                external_name=external_name,
                icon=icon_name,  # pass string name
            )
        else:
            # Ensure icon set if provided
            if icon_name:
                icon, _ = CategoryIconName.objects.get_or_create(name=icon_name)
                category_type.icon = icon
            category_type.white_label = white_label

        category_type.save()
        return category_type

    def _set_categories(self, need: UrgentNeed, categories: list[str]) -> None:
        category_objs = []
        for name in categories:
            obj, _ = UrgentNeedCategory.objects.get_or_create(name=name)
            category_objs.append(obj)
        need.type_short.set(category_objs)
        self.stdout.write(f"  Categories: {', '.join([c.name for c in category_objs])}")

    def _set_functions(self, need: UrgentNeed, functions: list[str]) -> None:
        function_objs = []
        for func_name in functions:
            if func_name not in urgent_need_functions:
                raise CommandError(f"Function '{func_name}' is not registered in urgent_need_functions")
            func_obj, _ = UrgentNeedFunction.objects.get_or_create(name=func_name)
            function_objs.append(func_obj)

        if function_objs:
            need.functions.set(function_objs)
            self.stdout.write(f"  Functions: {', '.join([f.name for f in function_objs])}")

    def _set_counties(self, need: UrgentNeed, white_label: WhiteLabel, counties: list[str]) -> None:
        if not counties:
            return
        county_objs = []
        for county_name in counties:
            obj, _ = County.objects.get_or_create(name=county_name, white_label=white_label)
            county_objs.append(obj)
        need.counties.set(county_objs)
        self.stdout.write(f"  Counties: {', '.join([c.name for c in county_objs])}")

    def _set_expense_filters(self, need: UrgentNeed, expense_types: list[str]) -> None:
        if not expense_types:
            return
        expense_objs = []
        for expense in expense_types:
            obj, _ = ExpenseType.objects.get_or_create(name=expense)
            expense_objs.append(obj)
        need.required_expense_types.set(expense_objs)
        self.stdout.write(f"  Required expense types: {', '.join([e.name for e in expense_objs])}")

    def _import_need_translations(self, need: UrgentNeed, translations: dict[str, str]) -> None:
        translated_fields = UrgentNeed.objects.translated_fields

        # Map missing optional translation
        prepared = {field: translations.get(field, "") for field in translated_fields}
        self._bulk_update_entity_translations(need, prepared, "urgent_need", translated_fields)
