from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from translations.models import Translation
from programs.models import (
    Program,
    ProgramNavigator,
    WarningMessage,
    FederalPoveryLimit,
    ProgramCategory,
    Document,
    Navigator,
    County,
    NavigatorLanguage,
    LegalStatus,
)
from screener.models import WhiteLabel
from integrations.clients.google_translate import Translate
from django.conf import settings
import argparse
import json
from typing import Any


def truncate(text: str, max_length: int = 50) -> str:
    """Truncate text with ellipsis if it exceeds max_length."""
    return f"{text[:max_length]}..." if len(text) > max_length else text


class Command(BaseCommand):
    help = """
    Import a new program from a JSON configuration file.

    Creates programs with automatic translation to all supported languages.
    Supports creating new entities or referencing existing ones.
    All operations run in a transaction (rollback on error).

    Usage:
      python manage.py import_program_config <path/to/config.json>
      python manage.py import_program_config <path/to/config.json> --dry-run

    For detailed documentation on JSON configuration format and examples,
    see: programs/management/commands/import_program_config_data/README.md
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
            help="Delete existing program and its navigators/documents before importing",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        config_file = options["config_file"]
        dry_run = options.get("dry_run", False)
        override = options.get("override", False)

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
        if "name_abbreviated" not in program_config:
            raise CommandError("Missing required field 'program.name_abbreviated'")

        program_name = program_config["name_abbreviated"]

        # Verify white label exists
        try:
            white_label = WhiteLabel.objects.get(code=white_label_code)
        except WhiteLabel.DoesNotExist:
            raise CommandError(f"WhiteLabel with code '{white_label_code}' not found")

        # Check if program already exists
        existing_program = Program.objects.filter(name_abbreviated=program_name, white_label=white_label).first()

        if existing_program:
            if override:
                self._delete_program_and_related(existing_program, config)
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"\nProgram '{program_name}' already exists for white label '{white_label_code}' "
                        f"(ID: {existing_program.id}). Skipping import.\n"
                        f"Use --override to delete and recreate the program."
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

                # Step 4: Import documents (after program exists)
                if "documents" in config:
                    self._import_documents(program, config["documents"])

                # Step 5: Import navigators (after program exists)
                if "navigators" in config:
                    self._import_navigators(program, config["navigators"])

                self.stdout.write(
                    self.style.SUCCESS(f"\n✓ Successfully created program: {program_name} (ID: {program.id})\n")
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\nError during import: {e}\n" f"All changes have been rolled back."))
            raise

    def _delete_program_and_related(self, program: Program, config: dict[str, Any]) -> None:
        """
        Delete a program and its related navigators/documents defined in the config.

        Only deletes navigators and documents that are specified in the config file,
        preserving any that might be shared with other programs.
        """
        self.stdout.write(self.style.WARNING("\n[Override Mode] Deleting existing program and related entities..."))

        program_name = program.name_abbreviated

        # Delete navigators and documents specified in config
        for entity_type, model, config_key, related_name in [
            ("navigator", Navigator, "navigators", "programs"),
            ("document", Document, "documents", "program_documents"),
        ]:
            for item_config in config.get(config_key, []):
                external_name = item_config.get("external_name")
                if not external_name:
                    continue
                entity = model.objects.filter(external_name=external_name).first()
                if not entity:
                    continue
                if getattr(entity, related_name).exclude(id=program.id).exists():
                    self.stdout.write(f"  Keeping {entity_type} '{external_name}' (used by other programs)")
                else:
                    entity.delete()
                    self.stdout.write(f"  Deleted {entity_type}: {external_name}")

        # Delete warning messages associated only with this program
        for warning in program.warning_messages.all():
            if warning.programs.count() == 1:
                warning.delete()
                self.stdout.write(f"  Deleted warning message: {warning.external_name}")

        # Delete the program
        program.delete()
        self.stdout.write(f"  Deleted program: {program_name}\n")

    def _separate_program_fields(self, program_config: dict[str, Any]) -> tuple[dict[str, str], dict[str, Any]]:
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

    def _print_dry_run_report(self, config: dict[str, Any], white_label_code: str, program_name: str) -> None:
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
            self.stdout.write(f"  name: {truncate(category_config['name'])}")

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
                self.stdout.write(f"  {field_name}: {truncate(english_text)}")

        # Warning message
        if "warning_message" in config:
            warning = config["warning_message"]
            self.stdout.write(f"\n{self.style.SUCCESS('Warning Message:')}")
            self.stdout.write(f"  external_name: {warning.get('external_name', 'N/A')}")
            self.stdout.write(f"  calculator: {warning.get('calculator', '_show')}")
            self.stdout.write(f"  message: {truncate(warning.get('message', ''))}")

        # Documents
        if "documents" in config:
            documents = config["documents"]
            self.stdout.write(f"\n{self.style.SUCCESS('Documents:')}")
            for i, doc in enumerate(documents, 1):
                self.stdout.write(f"\n  Document {i}:")
                external_name = doc.get("external_name", "N/A")
                text = doc.get("text", "")

                self.stdout.write(f"    external_name: {external_name}")
                if not text:
                    self.stdout.write("    (will use existing document if found)")
                else:
                    self.stdout.write(f"    text: {truncate(text)}")
                    if link_url := doc.get("link_url"):
                        self.stdout.write(f"    link_url: {link_url}")
                    if link_text := doc.get("link_text"):
                        self.stdout.write(f"    link_text: {truncate(link_text)}")

        # Navigators
        if "navigators" in config:
            navigators = config["navigators"]
            self.stdout.write(f"\n{self.style.SUCCESS('Navigators:')}")
            for i, nav in enumerate(navigators, 1):
                self.stdout.write(f"\n  Navigator {i}:")
                external_name = nav.get("external_name", "N/A")
                name = nav.get("name", "")

                self.stdout.write(f"    external_name: {external_name}")
                if not name:
                    self.stdout.write("    (will use existing navigator if found)")
                else:
                    self.stdout.write(f"    name: {truncate(name)}")
                    if email := nav.get("email"):
                        self.stdout.write(f"    email: {email}")
                    if description := nav.get("description"):
                        self.stdout.write(f"    description: {truncate(description)}")
                    if assistance_link := nav.get("assistance_link"):
                        self.stdout.write(f"    assistance_link: {assistance_link}")
                    if phone_number := nav.get("phone_number"):
                        self.stdout.write(f"    phone_number: {phone_number}")
                    if counties := nav.get("counties"):
                        self.stdout.write(f"    counties: {', '.join(counties)}")
                    if languages := nav.get("languages"):
                        self.stdout.write(f"    languages: {', '.join(languages)}")

        self.stdout.write(self.style.WARNING("\n=== END DRY RUN ===\n"))

    def _import_program(
        self,
        white_label: WhiteLabel,
        program_name: str,
        category: ProgramCategory,
        translations: dict[str, str],
        configuration: dict[str, Any],
    ) -> Program:
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

    def _import_program_category(self, white_label: WhiteLabel, category_config: dict[str, Any]) -> ProgramCategory:
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

    def _bulk_update_entity_translations(
        self,
        entity: Any,
        translations: dict[str, str],
        entity_type: str,
        translated_fields: list[str],
    ) -> None:
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

    def _import_program_category_translations(self, category: ProgramCategory, translations: dict[str, str]) -> None:
        """
        Update translatable fields for a program category.

        The category was created by ProgramCategory.objects.new_program_category() which already
        created Translation objects with proper labels (program_category.{external_name}_{category.id}-{field}).
        This method updates those existing translations with the provided English text
        and auto-translates to all supported languages.
        """
        translated_fields = ProgramCategory.objects.translated_fields
        self._bulk_update_entity_translations(category, translations, "category", translated_fields)

    def _import_program_translations(self, program: Program, translations: dict[str, str]) -> None:
        """
        Update translatable fields for a program.

        The program was created by Program.objects.new_program() which already
        created Translation objects with proper labels (program.{name_abbreviated}_{program.id}-{field}).
        This method updates those existing translations with the provided English text
        and auto-translates to all supported languages.
        """
        translated_fields = Program.objects.translated_fields
        self._bulk_update_entity_translations(program, translations, "program", translated_fields)

    def _update_translation_all_languages(
        self,
        translation_obj: Translation,
        text: str,
        texts_to_translate: list[str],
        translation_objects: dict[str, list[Translation]],
    ) -> None:
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

    def _import_program_configuration(self, program: Program, configuration: dict[str, Any]) -> None:
        """Import non-translatable configuration for a program."""
        # Handle year
        if "year" in configuration:
            year_value = configuration["year"]
            try:
                year_obj = FederalPoveryLimit.objects.get(year=year_value, period=year_value)
                program.year = year_obj
                self.stdout.write(f"  Year: {year_value}")
            except FederalPoveryLimit.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  Warning: Year '{year_value}' not found"))

        # Handle legal_status_required
        if "legal_status_required" in configuration:
            legal_statuses = configuration["legal_status_required"]
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

    def _import_warning_message(self, program: Program, warning_config: dict[str, Any]) -> None:
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

        external_name = warning_config["external_name"]

        # Validate white_label if provided matches program's white_label
        if "white_label" in warning_config:
            white_label_code = warning_config["white_label"]
            if white_label_code != program.white_label.code:
                raise CommandError(
                    f"Warning message white_label '{white_label_code}' does not match "
                    f"program white_label '{program.white_label.code}'"
                )

        calculator = warning_config.get("calculator", "_show")

        # Check if warning message already exists by external_name
        existing_warning = WarningMessage.objects.filter(external_name=external_name).first()

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
        field_values = {
            "message": warning_config.get("message", ""),
            "link_text": warning_config.get("link_text", ""),
            "link_url": warning_config.get("link_url", ""),
        }

        self._bulk_update_entity_translations(warning, field_values, "warning", translated_fields)

    def _import_documents(self, program: Program, documents_config: list[dict[str, Any]]) -> None:
        """
        Import documents for a program.

        For each document:
        - If a document with the given external_name exists, use it and do not update
          (only external_name is required for existing documents)
        - Otherwise, create a new document with translations
          (external_name and text are required for new documents)

        Associates all documents with the program using the many-to-many relationship.

        Args:
            program: The Program instance to associate documents with
            documents_config: List of document configurations from JSON
        """
        self.stdout.write(self.style.SUCCESS("\n[Documents]"))

        if not isinstance(documents_config, list):
            raise CommandError("'documents' must be an array")

        documents_to_associate = []

        for i, doc_config in enumerate(documents_config, 1):
            # Validate required fields
            if "external_name" not in doc_config:
                raise CommandError(f"Missing required field 'external_name' in documents[{i-1}]")

            external_name = doc_config["external_name"]

            # Check if document already exists
            existing_document = Document.objects.filter(external_name=external_name).first()

            if existing_document:
                self.stdout.write(f"  {i}. Using existing: {external_name} (ID: {existing_document.id})")
                documents_to_associate.append(existing_document)
            else:
                # For new documents, validate that 'text' field is present
                if "text" not in doc_config:
                    raise CommandError(
                        f"Missing required field 'text' in documents[{i-1}] ({external_name}). "
                        f"New documents require 'text' field. If document already exists, only 'external_name' is needed."
                    )

                # Create new document
                document = Document.objects.new_document(
                    white_label=program.white_label.code,
                    external_name=external_name,
                )

                self.stdout.write(f"  {i}. Created: {external_name} (ID: {document.id})")

                # Prepare translations
                translations = {
                    "text": doc_config["text"],
                    "link_url": doc_config.get("link_url", ""),
                    "link_text": doc_config.get("link_text", ""),
                }

                # Import translations using the standard method
                self._import_document_translations(document, translations)

                documents_to_associate.append(document)

        # Associate all documents with the program
        if documents_to_associate:
            program.documents.add(*documents_to_associate)
            self.stdout.write(f"  Associated {len(documents_to_associate)} document(s) with program")

    def _import_document_translations(self, document: Document, translations: dict[str, str]) -> None:
        """
        Update translatable fields for a document.

        The document was created by Document.objects.new_document() which already
        created Translation objects with proper labels (document.{external_name}_{document.id}-{field}).
        This method updates those existing translations with the provided English text
        and auto-translates to all supported languages.

        Note: link_url is marked as no_auto, so it will be copied to all languages
        without machine translation.
        """
        translated_fields = Document.objects.translated_fields
        self._bulk_update_entity_translations(document, translations, "document", translated_fields)

    def _import_navigators(self, program: Program, navigators_config: list[dict[str, Any]]) -> None:
        """
        Import navigators for a program.

        For each navigator:
        - If a navigator with the given external_name exists, use it and do not update
          (only external_name is required for existing navigators)
        - Otherwise, create a new navigator with translations
          (external_name, name, email, description, and assistance_link are required for new navigators)

        Associates all navigators with the program using the many-to-many relationship.

        Args:
            program: The Program instance to associate navigators with
            navigators_config: List of navigator configurations from JSON
        """
        self.stdout.write(self.style.SUCCESS("\n[Navigators]"))

        if not isinstance(navigators_config, list):
            raise CommandError("'navigators' must be an array")

        navigators_to_associate = []

        for i, nav_config in enumerate(navigators_config, 1):
            # Validate required fields
            if "external_name" not in nav_config:
                raise CommandError(f"Missing required field 'external_name' in navigators[{i-1}]")

            external_name = nav_config["external_name"]

            # Check if navigator already exists
            existing_navigator = Navigator.objects.filter(external_name=external_name).first()

            if existing_navigator:
                self.stdout.write(f"  {i}. Using existing: {external_name} (ID: {existing_navigator.id})")
                navigators_to_associate.append(existing_navigator)
            else:
                # For new navigators, validate that required fields are present
                required_fields = ["name", "email", "description", "assistance_link"]
                missing_fields = [field for field in required_fields if field not in nav_config]

                if missing_fields:
                    raise CommandError(
                        f"Missing required fields in navigators[{i-1}] ({external_name}): {', '.join(missing_fields)}. "
                        f"New navigators require these fields. If navigator already exists, only 'external_name' is needed."
                    )

                # Get phone number (optional)
                phone_number = nav_config.get("phone_number")

                # Create new navigator - use external_name as the label parameter
                navigator = Navigator.objects.new_navigator(
                    white_label=program.white_label.code,
                    name=external_name,
                    phone_number=phone_number,
                )

                self.stdout.write(f"  {i}. Created: {external_name} (ID: {navigator.id})")

                # Set external_name if it doesn't conflict
                if not Navigator.objects.filter(external_name=external_name).exclude(id=navigator.id).exists():
                    navigator.external_name = external_name
                    navigator.save()

                # Handle counties (optional)
                if "counties" in nav_config and nav_config["counties"]:
                    counties_to_add = []
                    for county_name in nav_config["counties"]:
                        county, created = County.objects.get_or_create(
                            name=county_name,
                            white_label=program.white_label,
                        )
                        counties_to_add.append(county)
                    navigator.counties.set(counties_to_add)
                    self.stdout.write(f"     Counties: {', '.join(nav_config['counties'])}")

                # Handle languages (optional)
                if "languages" in nav_config and nav_config["languages"]:
                    languages_to_add = []
                    for lang_code in nav_config["languages"]:
                        language, created = NavigatorLanguage.objects.get_or_create(code=lang_code)
                        languages_to_add.append(language)
                    navigator.languages.set(languages_to_add)
                    self.stdout.write(f"     Languages: {', '.join(nav_config['languages'])}")

                # Prepare translations
                translations = {
                    "name": nav_config["name"],
                    "email": nav_config["email"],
                    "description": nav_config["description"],
                    "assistance_link": nav_config["assistance_link"],
                }

                # Import translations using the standard method
                self._import_navigator_translations(navigator, translations)

                navigators_to_associate.append(navigator)

        # Associate all navigators with the program using through model
        if navigators_to_associate:
            for idx, navigator in enumerate(navigators_to_associate):
                ProgramNavigator.objects.get_or_create(
                    program=program,
                    navigator=navigator,
                    defaults={"order": idx},
                )
            self.stdout.write(f"  Associated {len(navigators_to_associate)} navigator(s) with program")

    def _import_navigator_translations(self, navigator: Navigator, translations: dict[str, str]) -> None:
        """
        Update translatable fields for a navigator.

        The navigator was created by Navigator.objects.new_navigator() which already
        created Translation objects with proper labels (navigator.{name}_{navigator.id}-{field}).
        This method updates those existing translations with the provided English text
        and auto-translates to all supported languages.

        Note: assistance_link is marked as no_auto, so it will be copied to all languages
        without machine translation.
        """
        translated_fields = Navigator.objects.translated_fields
        self._bulk_update_entity_translations(navigator, translations, "navigator", translated_fields)
