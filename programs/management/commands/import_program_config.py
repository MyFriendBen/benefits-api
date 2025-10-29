from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from translations.models import Translation
from programs.models import Program, WarningMessage, FederalPoveryLimit, ProgramCategory
from screener.models import WhiteLabel
from integrations.services.google_translate.integration import Translate
from django.conf import settings
import argparse
import json


class Command(BaseCommand):
    help = """
    Create a new program from a JSON configuration file.

    This command creates a new program, translations, program category, and
    optionally a warning message. If the program already exists, it will skip the
    import and display a message. All English translations are automatically
    translated to all supported languages.

    The JSON file should contain:
    - white_label: REQUIRED - The white label for all entities
        - code: REQUIRED - white label code (e.g., "tx", "co")
    - program_category: REQUIRED - The program category configuration (flat structure)
        - external_name: REQUIRED - category identifier
        - For existing categories: only external_name is needed
        - For new categories: must also include icon and name (at top level)
        - tax_category: optional (defaults to false)
    - program: REQUIRED - The program configuration (flat structure)
        - name_abbreviated: REQUIRED
        - All translatable fields (name, description, etc.)
        - All configuration fields (year, legal_status_required, etc.)
    - warning_message: OPTIONAL - Single warning message configuration
        - external_name: REQUIRED
        - calculator: defaults to "_show"
        - message: The warning text

    Example usage:
      python manage.py import_program_config path/to/config.json
    """

    def add_arguments(self, parser):
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

    def handle(self, *args, **options):
        config_file = options["config_file"]
        dry_run = options.get("dry_run", False)

        try:
            config = json.load(config_file)
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON file: {e}")

        # Validate required top-level fields
        required_fields = ["white_label", "program_category", "program"]
        for field in required_fields:
            if field not in config:
                raise CommandError(f"Missing required field: {field}")

        # Validate white_label section
        white_label_config = config["white_label"]
        if "code" not in white_label_config:
            raise CommandError("Missing required field 'white_label.code'")

        white_label_code = white_label_config["code"]

        # Validate program section
        program_config = config["program"]
        required_program_fields = ["name_abbreviated"]
        for field in required_program_fields:
            if field not in program_config:
                raise CommandError(f"Missing required field 'program.{field}'")

        program_name = program_config["name_abbreviated"]

        # Verify white label exists
        try:
            white_label = WhiteLabel.objects.get(code=white_label_code)
        except WhiteLabel.DoesNotExist:
            raise CommandError(f"WhiteLabel with code '{white_label_code}' not found")

        # Check if program already exists
        existing_program = Program.objects.filter(name_abbreviated=program_name, white_label=white_label).first()

        if existing_program:
            self.stdout.write(
                self.style.WARNING(
                    f"\nProgram '{program_name}' already exists for white label '{white_label_code}' "
                    f"(ID: {existing_program.id}). Skipping import.\n"
                    f"This command only creates new programs and does not update existing data."
                )
            )
            return

        if dry_run:
            self._print_dry_run_report(config, white_label_code, program_name)
            return

        # Wrap all creation logic in a transaction for rollback support
        try:
            with transaction.atomic():
                self.stdout.write(self.style.SUCCESS(f"\n[Program: {program_name}]"))
                self.stdout.write(f"White Label: {white_label_code}\n")

                # Step 1: Import program category (find or create) before program
                category = self._import_program_category(white_label, config["program_category"])

                # Step 2: Create program with all data consolidated
                # Separate translation fields from configuration fields
                translations, configuration = self._separate_program_fields(program_config)

                program = self._import_program(
                    white_label=white_label,
                    program_name=program_name,
                    category=category,
                    translations=translations,
                    configuration=configuration,
                )

                # Step 3: Import warning message (after program exists)
                if "warning_message" in config:
                    self._import_warning_message(program, config["warning_message"])

                self.stdout.write(
                    self.style.SUCCESS(f"\n✓ Successfully created program: {program_name} (ID: {program.id})\n")
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\nError during import: {e}\n" f"All changes have been rolled back."))
            raise

    def _separate_program_fields(self, program_config):
        """
        Separate program fields into translations and configuration.

        Returns (translations_dict, configuration_dict)
        """
        # Fields that belong to Program.objects.translated_fields
        translation_field_names = Program.objects.translated_fields

        # Skip these fields as they're handled elsewhere
        skip_fields = ["name_abbreviated"]

        translations = {}
        configuration = {}

        for key, value in program_config.items():
            if key in skip_fields:
                continue
            elif key in translation_field_names:
                translations[key] = value
            else:
                # Any field not in translations or skip_fields is configuration
                configuration[key] = value

        return translations, configuration

    def _print_dry_run_report(self, config, white_label_code, program_name):
        """Print a report of what would be created without making changes."""
        self.stdout.write(self.style.WARNING("\n=== DRY RUN MODE ==="))
        self.stdout.write("No changes will be made to the database.\n")

        # White Label
        self.stdout.write(self.style.SUCCESS(f"\nWhite Label:"))
        self.stdout.write(f"  code: {white_label_code}")

        # Program category (required)
        category_config = config["program_category"]
        self.stdout.write(f"\n{self.style.SUCCESS('Program Category:')}")
        self.stdout.write(f"  external_name: {category_config.get('external_name', 'N/A')}")
        self.stdout.write(f"  icon: {category_config.get('icon', 'N/A')}")
        if "name" in category_config:
            name_value = category_config["name"]
            preview = name_value[:50] + "..." if len(name_value) > 50 else name_value
            self.stdout.write(f"  name: {preview}")

        # Program section - separate into translations and configuration
        program_config = config["program"]
        translations, configuration = self._separate_program_fields(program_config)

        # Program section - show all fields together
        self.stdout.write(f"\n{self.style.SUCCESS('Program:')}")
        self.stdout.write(f"  name_abbreviated: {program_name}")

        # Show configuration fields
        if configuration:
            for key, value in configuration.items():
                self.stdout.write(f"  {key}: {value}")

        # Show translations
        if translations:
            for field_name, english_text in translations.items():
                preview = english_text[:50] + "..." if len(english_text) > 50 else english_text
                self.stdout.write(f"  {field_name}: {preview}")

        # Warning message
        if "warning_message" in config:
            warning = config["warning_message"]
            self.stdout.write(f"\n{self.style.SUCCESS('Warning Message:')}")
            external_name = warning.get("external_name", "N/A")
            calculator = warning.get("calculator", "_show")
            message = warning.get("message", "")
            preview = message[:50] + "..." if len(message) > 50 else message
            self.stdout.write(f"  external_name: {external_name}")
            self.stdout.write(f"  calculator: {calculator}")
            self.stdout.write(f"  message: {preview}")

        self.stdout.write(self.style.WARNING("\n=== END DRY RUN ===\n"))

    def _import_program(self, white_label, program_name, category, translations, configuration):
        """
        Create a new program with all data consolidated.

        This method creates the program entity and sets all its fields in one place,
        including translations and configuration.
        """
        self.stdout.write(self.style.SUCCESS("\n[Program Details]"))

        # Create base program with translations
        program = Program.objects.new_program(white_label=white_label.code, name_abbreviated=program_name)
        self.stdout.write(f"  Created: {program_name} (ID: {program.id})")

        # Set category if provided
        if category:
            program.category = category

        # Import configuration
        if configuration:
            self._import_program_configuration(program, configuration)

        # Import translations
        if translations:
            self._import_program_translations(program, translations)

        return program

    def _import_program_category(self, white_label, category_config):
        """
        Find or create a program category.

        For existing categories, only external_name is required.
        For new categories, external_name, name (at top level), and icon are required.
        tax_category is optional (defaults to False).

        Returns the ProgramCategory instance.
        """
        self.stdout.write(self.style.SUCCESS("\n[Category]"))

        external_name = category_config.get("external_name")
        if not external_name:
            raise CommandError("Missing required field 'external_name' in program_category")

        # Try to find existing category by external_name
        existing_category = ProgramCategory.objects.filter(external_name=external_name, white_label=white_label).first()

        if existing_category:
            self.stdout.write(f"  Using existing: {external_name} (ID: {existing_category.id})")
            return existing_category
        else:
            # For new categories, validate required fields
            missing_fields = []

            # Check for icon in main config (required)
            if "icon" not in category_config:
                missing_fields.append("icon")

            # Check for name (required)
            if "name" not in category_config:
                missing_fields.append("name")

            if missing_fields:
                raise CommandError(
                    f"Program category '{external_name}' does not exist. "
                    f"To create a new category, provide: {', '.join(missing_fields)}"
                )

            icon = category_config.get("icon", "")

            # Create new category
            category = ProgramCategory.objects.new_program_category(
                white_label=white_label.code, external_name=external_name, icon=icon
            )

            # Set tax_category
            category.tax_category = category_config.get("tax_category", False)
            category.save()

            self.stdout.write(f"  Created: {external_name} (ID: {category.id})")

            # Import category translations if provided
            # Build translations dict from flat structure
            translations = {}
            if "name" in category_config:
                translations["name"] = category_config["name"]
            # Default description to empty string if not provided
            translations["description"] = category_config.get("description", "")

            if translations:
                self._import_program_category_translations(category, translations)

            return category

    def _bulk_update_entity_translations(self, entity, translations, entity_type, translated_fields):
        """
        Reusable method for bulk translation updates across different entity types.

        This method handles the common workflow of:
        1. Validating translation fields against model's translated_fields
        2. Collecting English texts for bulk translation
        3. Updating Translation objects with English text
        4. Auto-translating to all supported languages
        5. Applying translations to all Translation objects

        Args:
            entity: The model instance (Program, ProgramCategory, or WarningMessage)
            translations: Dict mapping field_name -> english_text
            entity_type: String for logging (e.g., "program", "category", "warning")
            translated_fields: List of valid translatable field names for this entity

        The entity is saved after all translations are applied.
        """
        texts_to_translate = []
        translation_objects = {}

        for field_name, english_text in translations.items():
            if field_name not in translated_fields:
                self.stdout.write(self.style.WARNING(f"  Warning: Unknown {entity_type} field '{field_name}'"))
                continue

            # Get the existing translation object
            translation_obj = getattr(entity, field_name)

            # Update translation
            self._update_translation_all_languages(
                translation_obj, english_text, texts_to_translate, translation_objects
            )

        # Bulk translate
        if texts_to_translate:
            self.stdout.write(f"  Translating {len(texts_to_translate)} field(s) to all languages...")

            bulk_translations = Translate().bulk_translate(Translate.languages, texts_to_translate)

            for english_text, translation_obj_list in translation_objects.items():
                auto_translations = bulk_translations[english_text]
                for translation_obj in translation_obj_list:
                    for lang in Translate.languages:
                        if lang != settings.LANGUAGE_CODE:
                            Translation.objects.edit_translation_by_id(
                                translation_obj.id,
                                lang,
                                auto_translations[lang],
                                manual=False,
                            )

        entity.save()

    def _import_program_category_translations(self, category, translations):
        """
        Update translatable fields for a program category.

        The category was created by ProgramCategory.objects.new_program_category() which already
        created Translation objects with proper labels (program_category.{external_name}_{category.id}-{field}).
        This method updates those existing translations with the provided English text
        and auto-translates to all supported languages.
        """
        translated_fields = ProgramCategory.objects.translated_fields
        self._bulk_update_entity_translations(category, translations, "category", translated_fields)

    def _import_program_translations(self, program, translations):
        """
        Update translatable fields for a program.

        The program was created by Program.objects.new_program() which already
        created Translation objects with proper labels (program.{name_abbreviated}_{program.id}-{field}).
        This method updates those existing translations with the provided English text
        and auto-translates to all supported languages.
        """
        translated_fields = Program.objects.translated_fields
        self._bulk_update_entity_translations(program, translations, "program", translated_fields)

    def _update_translation_all_languages(self, translation_obj, text, texts_to_translate, translation_objects):
        """
        Update a translation for all languages.

        Uses the same logic as views.py edit_translation() when lang==settings.LANGUAGE_CODE
        and auto_translate_check is True (lines 257-269).
        """
        # Update English translation (manual=True)
        Translation.objects.edit_translation_by_id(translation_obj.id, settings.LANGUAGE_CODE, text, manual=True)

        # Handle no_auto fields (copy English to all languages)
        if translation_obj.no_auto:
            for lang in Translate.languages:
                Translation.objects.edit_translation_by_id(translation_obj.id, lang, text, manual=False)
        else:
            # Store for batch translation (same as views.py logic)
            if text:
                # Add to unique texts list only if not already present
                if text not in translation_objects:
                    texts_to_translate.append(text)
                    translation_objects[text] = []
                # Append this translation object to the list for this text
                translation_objects[text].append(translation_obj)

    def _import_program_configuration(self, program, configuration):
        """Import non-translatable configuration for a program."""
        # Handle year
        if "year" in configuration:
            year_value = configuration["year"]
            try:
                year_obj = FederalPoveryLimit.objects.get(period=year_value)
                program.year = year_obj
                self.stdout.write(f"  Year: {year_value}")
            except FederalPoveryLimit.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  Warning: Year '{year_value}' not found"))

        # Handle legal_status_required
        if "legal_status_required" in configuration:
            legal_statuses = configuration["legal_status_required"]
            from programs.models import LegalStatus

            for status_code in legal_statuses:
                try:
                    status = LegalStatus.objects.get(status=status_code)
                    program.legal_status_required.add(status)
                except LegalStatus.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"  Warning: Legal status '{status_code}' not found"))
            self.stdout.write(f"  Legal statuses: {', '.join(legal_statuses)}")

        # Handle other simple configuration fields
        simple_config_fields = [
            "external_name",
            "active",
            "low_confidence",
            "show_on_current_benefits",
            "value_format",
        ]

        for field_name in simple_config_fields:
            if field_name in configuration:
                setattr(program, field_name, configuration[field_name])
                self.stdout.write(f"  {field_name}: {configuration[field_name]}")

        program.save()

    def _import_warning_message(self, program, warning_config):
        """
        Import a warning message for a new program.

        Accepts English text and auto-translates to all supported languages.
        Uses WarningMessage.objects.new_warning() to create the warning with proper
        translation labels (warning.{calculator}_{warning.id}-{field}).
        Checks for duplicate warning messages and associates existing ones if found.

        Validates that external_name and white_label are present for the warning message.
        """
        self.stdout.write(self.style.SUCCESS("\n[Warning Message]"))

        # Validate required fields
        if "external_name" not in warning_config:
            raise CommandError("Missing required field 'external_name' in warning_messages configuration")

        external_name = warning_config.get("external_name")

        # Validate white_label if provided matches program's white_label
        if "white_label" in warning_config:
            white_label_code = warning_config.get("white_label")
            if white_label_code != program.white_label.code:
                raise CommandError(
                    f"Warning message white_label '{white_label_code}' does not match "
                    f"program white_label '{program.white_label.code}'"
                )

        calculator = warning_config.get("calculator", "_show")

        # Check if warning message already exists for this calculator and white label
        existing_warning = WarningMessage.objects.filter(calculator=calculator, white_label=program.white_label).first()

        if existing_warning:
            # Check if this program is already associated
            if existing_warning.programs.filter(id=program.id).exists():
                self.stdout.write(f"  Using existing: {external_name} (already associated)")
                return
            else:
                # Associate existing warning with this program
                existing_warning.programs.add(program)
                self.stdout.write(f"  Associated existing: {external_name} (ID: {existing_warning.id})")
                return

        # Create warning message using manager method (creates proper translation labels)
        warning = WarningMessage.objects.new_warning(
            white_label=program.white_label.code,
            calculator=calculator,
            external_name=external_name,
        )

        self.stdout.write(f"  Created: {external_name} (ID: {warning.id})")

        # Associate the created program with this warning message
        warning.programs.add(program)

        # Update translations for the warning message
        translated_fields = WarningMessage.objects.translated_fields

        # Map config fields to model fields
        # Only "message" is expected from config; other fields get empty defaults
        field_values = {
            "message": warning_config.get("message", ""),
            "link_text": "",
            "link_url": "",
        }

        self._bulk_update_entity_translations(warning, field_values, "warning", translated_fields)
