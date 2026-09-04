from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max
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
    BaseProgram,
)
from screener.models import WhiteLabel
from configuration.models import Configuration
from integrations.clients.google_translate import Translate
from django.conf import settings
import argparse
import json
from typing import Any, Optional


def truncate(text: str, max_length: int = 50) -> str:
    """Truncate text with ellipsis if it exceeds max_length."""
    return f"{text[:max_length]}..." if len(text) > max_length else text


# Sections a --reconcile pass can apply, in the order they must run.
RECONCILE_SECTIONS = ("warning_messages", "documents", "navigators")


class Command(BaseCommand):
    help = """
    Import a new program from a JSON configuration file.

    Creates programs with automatic translation to all supported languages.
    Supports creating new entities or referencing existing ones.
    All operations run in a transaction (rollback on error).

    Usage:
      python manage.py import_program_config <path/to/config.json>
      python manage.py import_program_config <path/to/config.json> --dry-run
      python manage.py import_program_config <path/to/config.json> --skip-translation
      python manage.py import_program_config <path/to/config.json> --reconcile --dry-run
      python manage.py import_program_config <path/to/config.json> --reconcile

    If the program already exists the import is skipped. Use --reconcile to additively
    apply the config's warning messages, documents and navigators to it, or --override
    to delete and recreate it from scratch.

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
        parser.add_argument(
            "--reconcile",
            action="store_true",
            help="For a program that already exists, additively apply the warning messages, documents "
            "and navigators declared in the config. Creates missing entities and missing links only; "
            "never updates an existing entity, removes a link absent from the config, or touches "
            "program fields or translations. Combine with --dry-run to preview.",
        )
        parser.add_argument(
            "--only",
            action="append",
            choices=list(RECONCILE_SECTIONS),
            help="With --reconcile, limit the pass to these sections. Repeatable. Defaults to all of them.",
        )
        parser.add_argument(
            "--skip-translation",
            action="store_true",
            help="Copy English text to all languages instead of calling Google Translate "
            "(for local dev when GOOGLE_APPLICATION_CREDENTIALS is unavailable)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        config_file = options["config_file"]
        dry_run = options.get("dry_run", False)
        override = options.get("override", False)
        reconcile = options.get("reconcile", False)
        self.skip_translation = bool(options.get("skip_translation", False))

        if override and reconcile:
            raise CommandError(
                "--override and --reconcile are mutually exclusive. "
                "--override recreates the program from scratch; --reconcile only adds what is missing."
            )

        only = options.get("only")
        if only and not reconcile:
            raise CommandError("--only has no effect without --reconcile.")
        sections = tuple(s for s in RECONCILE_SECTIONS if s in (only or RECONCILE_SECTIONS))

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
        overriding = bool(existing_program and override)

        if existing_program and reconcile:
            # Reconcile creates navigators the config declares but the database lacks, and
            # creating one writes its counties — so the county guard has to run here too, or a
            # repair pass becomes a way to reintroduce exactly the mismatch it exists to block.
            # Scoped like the guard itself: only when this pass will touch navigators at all, and
            # with overriding=False, since reconcile never recreates an existing navigator.
            if "navigators" in sections:
                self._validate_counties(config, white_label, existing_program=existing_program, overriding=False)
            self._reconcile_program(existing_program, config, sections=sections, dry_run=dry_run)
            return

        if reconcile:
            # Reconcile repairs existing programs. Refusing to create keeps a repair run
            # from quietly introducing programs nobody asked for.
            self.stdout.write(
                self.style.WARNING(
                    f"\n⊘ Skipped: program '{program_name}' does not exist for white label "
                    f"'{white_label_code}'. --reconcile only repairs existing programs; "
                    f"run without it to create this one.\n"
                )
            )
            return

        if existing_program and not override:
            self.stdout.write(
                self.style.WARNING(
                    f"\nProgram '{program_name}' already exists for white label '{white_label_code}' "
                    f"(ID: {existing_program.id}). Skipping import.\n"
                    f"Use --reconcile to additively apply the config's warning messages, documents and "
                    f"navigators, or --override to delete and recreate the program."
                )
            )
            return

        # Validate navigator county names against this white label's convention BEFORE any
        # writes (now that we know the import will proceed), scoped to the navigators this run
        # will actually (re)create — so a mismatch fails loudly without blocking over counties
        # that the existing-navigator path never writes.
        self._validate_counties(config, white_label, existing_program=existing_program, overriding=overriding)

        if dry_run:
            self._print_dry_run_report(config, white_label_code, program_name)
            return

        # Wrap all creation logic in a transaction for rollback support
        try:
            with transaction.atomic():
                # Delete existing program if overriding (inside transaction for proper rollback)
                if overriding:
                    self._delete_program_and_related(existing_program, config)
                    existing_program = None

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

                # Step 3: Import warning message(s) (after program exists)
                for warning_config in self._warning_message_configs(config):
                    self._import_warning_message(program, warning_config)

                # Step 4: Import documents (after program exists)
                if "documents" in config:
                    self._import_documents(program, config["documents"])

                # Step 5: Import navigators (after program exists)
                if "navigators" in config:
                    self._import_navigators(program, config["navigators"])

                action = "recreated" if overriding else "created"
                self.stdout.write(
                    self.style.SUCCESS(f"\n✓ Successfully {action} program: {program_name} (ID: {program.id})\n")
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\nError during import: {e}\n" f"All changes have been rolled back."))
            raise

    def _get_valid_county_names(self, white_label: WhiteLabel) -> Optional[set]:
        """
        Return the set of valid county-name strings for a white label, taken from its
        `counties_by_zipcode` configuration — the same values the screener stores in
        `Screen.county`. Returns None when no such configuration exists (in which case
        county validation is skipped), read the same way `add_counties` reads it.
        """
        config_obj = (
            Configuration.objects.filter(name="counties_by_zipcode", white_label=white_label, active=True)
            .order_by("-id")
            .first()
        )
        if config_obj is None:
            return None

        data = config_obj.data
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError as e:
                raise CommandError(
                    f"'counties_by_zipcode' config for white label '{white_label.code}' is not valid JSON: {e}"
                ) from e
        if data is None:
            return None
        if not isinstance(data, dict):
            raise CommandError(
                f"'counties_by_zipcode' config for white label '{white_label.code}' must be a JSON object, "
                f"got {type(data).__name__}."
            )
        if not data:
            return None

        valid = set()
        for county_map in data.values():
            if isinstance(county_map, dict):
                valid.update(county_map.keys())
        return valid

    def _navigator_counties_written(self, external_name: str, existing_program, overriding: bool) -> bool:
        """
        Whether `_import_navigators` will persist this navigator's counties on this run.

        Counties are only written when a navigator is created. A brand-new navigator is always
        created. An existing navigator is recreated only in override mode and only when it is
        not shared with another program — mirroring `_delete_program_and_related`'s retention;
        otherwise it is associated as-is and its config `counties` are ignored.
        """
        existing_nav = Navigator.objects.filter(external_name=external_name).first()
        if existing_nav is None:
            return True
        if not overriding:
            return False
        # Both relations, matching the delete guard: a navigator linked through the
        # ProgramNavigator table is shared even though the legacy M2M says nothing.
        shared = any(
            getattr(existing_nav, relation).exclude(id=existing_program.id).exists()
            for relation in ("programs_ordered", "programs")
        )
        return not shared

    def _validate_counties(
        self,
        config: dict[str, Any],
        white_label: WhiteLabel,
        existing_program: Optional[Program] = None,
        overriding: bool = False,
    ) -> None:
        """
        Validate that every navigator `counties` entry exactly matches a county in the white
        label's `counties_by_zipcode` map. Navigator county filters are an exact string match
        against the screener's stored county, so a name in the wrong convention (e.g. bare
        "Jackson" where the map sends "Jackson County") would silently never match and the
        referral would be dropped. Fail loudly instead.

        Only the navigators this run will actually (re)create are validated (see
        `_navigator_counties_written`): counties are written just on the create path, so
        validating an association-only navigator would block the import over a field that path
        never writes.
        """
        valid_names = self._get_valid_county_names(white_label)
        if valid_names is None:
            self.stdout.write(
                self.style.WARNING(
                    f"  Warning: no 'counties_by_zipcode' configuration found for white label "
                    f"'{white_label.code}'; skipping navigator county validation."
                )
            )
            return

        problems = []
        for nav_config in config.get("navigators", []):
            if not isinstance(nav_config, dict):
                continue
            external_name = nav_config.get("external_name", "<unnamed>")

            # Skip navigators whose counties this run won't write.
            if isinstance(external_name, str) and not self._navigator_counties_written(
                external_name, existing_program, overriding
            ):
                continue

            for county_name in nav_config.get("counties", []) or []:
                if not isinstance(county_name, str):
                    problems.append(f"navigator '{external_name}': {county_name!r} is not a string")
                    continue
                if county_name in valid_names:
                    continue
                other = county_name[: -len(" County")] if county_name.endswith(" County") else f"{county_name} County"
                suggestion = f" (did you mean '{other}'?)" if other in valid_names else ""
                problems.append(f"navigator '{external_name}': '{county_name}'{suggestion}")

        if problems:
            joined = "\n  - ".join(problems)
            raise CommandError(
                f"Invalid county name(s) for white label '{white_label.code}' — not found in its "
                f"'counties_by_zipcode' map:\n  - {joined}\n"
                "Each 'counties' entry must exactly match a county the screener sends for this white "
                f"label (see configuration/white_labels/{white_label.code}.py counties_by_zipcode)."
            )

    def _delete_program_and_related(self, program: Program, config: dict[str, Any]) -> None:
        """
        Delete a program and its related navigators/documents defined in the config.

        Only deletes navigators and documents that are specified in the config file,
        preserving any that might be shared with other programs.
        """
        self.stdout.write(self.style.WARNING("\n[Override Mode] Deleting existing program and related entities..."))

        program_name = program.name_abbreviated

        # Delete navigators and documents specified in config
        for entity_type, model, config_key, related_names in [
            # Navigators live in two tables during the EXPAND phase of migration 0126:
            # the app reads `programs_ordered` (the ProgramNavigator through table),
            # while `programs` is the legacy M2M nothing on the import path populates.
            # An entity linked in either table is still in use by another program.
            ("navigator", Navigator, "navigators", ("programs_ordered", "programs")),
            ("document", Document, "documents", ("program_documents",)),
        ]:
            for item_config in config.get(config_key, []):
                external_name = item_config.get("external_name")
                if not external_name:
                    continue
                entity = model.objects.filter(external_name=external_name).first()
                if not entity:
                    continue
                shared = any(getattr(entity, rel).exclude(id=program.id).exists() for rel in related_names)
                if shared:
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

    def _warning_message_configs(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Return the warning messages declared in a config.

        Supports both:
          - "warning_message"  (singular, object)  — original shape
          - "warning_messages" (plural,   array)   — multi-warning shape
        Mutually exclusive; raises if both are present.
        """
        if "warning_message" in config and "warning_messages" in config:
            raise CommandError(
                "Config contains both 'warning_message' (singular) and 'warning_messages' (plural). "
                "Use one or the other, not both."
            )

        if "warning_message" in config:
            return [config["warning_message"]]

        warning_messages = config.get("warning_messages", [])
        if not isinstance(warning_messages, list):
            raise CommandError("'warning_messages' must be an array")
        return warning_messages

    def _reconcile_program(
        self,
        program: Program,
        config: dict[str, Any],
        sections: tuple[str, ...] = RECONCILE_SECTIONS,
        dry_run: bool = False,
    ) -> None:
        """
        Additively apply a config to a program that already exists.

        Creates the entities a config declares but the database lacks, and creates the
        missing program associations. Existing entities are never updated and existing
        associations are never removed, so navigators, documents and warning messages
        added or hand-edited in the admin survive intact. Program fields, category and
        translations are not touched at all.
        """
        header = "[Reconcile — dry run]" if dry_run else "[Reconcile]"
        self.stdout.write(self.style.SUCCESS(f"\n{header} {program.name_abbreviated} (ID: {program.id})"))
        if set(sections) != set(RECONCILE_SECTIONS):
            self.stdout.write(f"Sections: {', '.join(sections)}")

        plan = self._build_reconcile_plan(program, config, sections)
        self._print_reconcile_plan(plan)

        to_apply = [(name, action) for items in plan.values() for name, action in items if action != "linked"]
        if not to_apply:
            self.stdout.write(self.style.SUCCESS("\n✓ Already up to date — nothing to apply.\n"))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("\n[Dry run] No changes applied.\n"))
            return

        try:
            with transaction.atomic():
                if "warning_messages" in sections:
                    for warning_config in self._warning_message_configs(config):
                        self._import_warning_message(program, warning_config)

                if "documents" in sections and "documents" in config:
                    self._import_documents(program, config["documents"])

                if "navigators" in sections and "navigators" in config:
                    # Append after any existing links so reconciling never reshuffles
                    # an ordering someone set in the admin.
                    self._import_navigators(
                        program,
                        config["navigators"],
                        order_offset=self._next_navigator_order(program),
                    )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\nError during reconcile: {e}\nAll changes have been rolled back."))
            raise

        links = sum(1 for _, action in to_apply if action == "link")
        created = sum(1 for _, action in to_apply if action == "create")
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ Reconciled {program.name_abbreviated}: " f"{links} link(s) added, {created} entity(ies) created\n"
            )
        )

    def _build_reconcile_plan(
        self, program: Program, config: dict[str, Any], sections: tuple[str, ...] = RECONCILE_SECTIONS
    ) -> dict[str, list[tuple[str, str]]]:
        """
        Classify every entity a config declares against the program's current state.

        Returns {section title: [(external_name, action)]} where action is "linked" (already
        associated), "link" (entity exists but the association is missing) or "create"
        (no such entity yet).

        Navigators are checked against ProgramNavigator only. A navigator present just in
        the legacy `programs` M2M is invisible to the results endpoint, so it is correctly
        reported as still needing a link.

        A declaration without an external_name raises, matching the validation the import
        path already applies. Skipping it instead would drop it from the plan, and an empty
        plan reads as "already up to date" — so a malformed config would report clean and
        then be recorded as applied without anything having been applied.
        """
        specs = [
            (
                "warning_messages",
                "Warning messages",
                self._warning_message_configs(config),
                WarningMessage,
                lambda entity: entity.programs.filter(id=program.id).exists(),
            ),
            (
                "documents",
                "Documents",
                config.get("documents", []),
                Document,
                lambda entity: program.documents.filter(id=entity.id).exists(),
            ),
            (
                "navigators",
                "Navigators",
                config.get("navigators", []),
                Navigator,
                lambda entity: ProgramNavigator.objects.filter(program=program, navigator=entity).exists(),
            ),
        ]

        plan: dict[str, list[tuple[str, str]]] = {}
        for key, title, item_configs, model, is_linked in specs:
            if key not in sections:
                continue
            items: list[tuple[str, str]] = []
            for i, item_config in enumerate(item_configs):
                external_name = item_config.get("external_name")
                if not external_name:
                    raise CommandError(f"Missing required field 'external_name' in {key}[{i}]")
                entity = model.objects.filter(external_name=external_name).first()
                if entity is None:
                    items.append((external_name, "create"))
                else:
                    items.append((external_name, "linked" if is_linked(entity) else "link"))
            plan[title] = items

        return plan

    def _print_reconcile_plan(self, plan: dict[str, list[tuple[str, str]]]) -> None:
        """Print what reconciling would change, section by section."""
        markers = {
            "linked": ("✓", "already linked"),
            "link": ("+", "link to add"),
            "create": ("★", "entity to create"),
        }

        for section, items in plan.items():
            if not items:
                continue
            self.stdout.write(self.style.SUCCESS(f"\n[{section}]"))
            for external_name, action in items:
                marker, description = markers[action]
                line = f"  {marker} {external_name} ({description})"
                self.stdout.write(line if action == "linked" else self.style.WARNING(line))

    def _next_navigator_order(self, program: Program) -> int:
        """Return the order value new navigator links should start at, appending after existing ones."""
        highest = ProgramNavigator.objects.filter(program=program).aggregate(Max("order"))["order__max"]
        return 0 if highest is None else highest + 1

    def _separate_program_fields(self, program_config: dict[str, Any]) -> tuple[dict[str, str], dict[str, Any]]:
        """
        Separate program fields into translations and configuration.

        Returns (translations_dict, configuration_dict)
        """
        # Fields that belong to Program.objects.translated_fields
        translation_field_names = Program.objects.translated_fields

        # Skip these fields as they're handled elsewhere
        skip_fields = ["name_abbreviated"]

        # Note: learn_more_link and apply_button_link are handled here because
        # they are defined as translated fields in the Program model, even though they contain URLs.

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

        # Warning message(s) — supports singular object or plural array
        if "warning_message" in config:
            warning = config["warning_message"]
            self.stdout.write(f"\n{self.style.SUCCESS('Warning Message:')}")
            self.stdout.write(f"  external_name: {warning.get('external_name', 'N/A')}")
            self.stdout.write(f"  calculator: {warning.get('calculator', '_show')}")
            self.stdout.write(f"  message: {truncate(warning.get('message', ''))}")
        elif "warning_messages" in config:
            warnings = config["warning_messages"]
            self.stdout.write(f"\n{self.style.SUCCESS(f'Warning Messages ({len(warnings)}):')}")
            for i, warning in enumerate(warnings, 1):
                self.stdout.write(f"\n  Warning {i}:")
                self.stdout.write(f"    external_name: {warning.get('external_name', 'N/A')}")
                self.stdout.write(f"    calculator: {warning.get('calculator', '_show')}")
                self.stdout.write(f"    message: {truncate(warning.get('message', ''))}")

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

        # Unscoped: external_name is globally unique, and a shared category has
        # no white label to match on.
        existing_category = ProgramCategory.objects.filter(external_name=external_name).first()

        if existing_category:
            scope = "shared" if existing_category.white_label is None else existing_category.white_label.code
            self.stdout.write(f"  Using existing: {external_name} ({scope}, ID: {existing_category.id})")
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
            self.stdout.write(f"    - {field_name}: {truncate(english_text)}")
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
        if translation_obj.no_auto or getattr(self, "skip_translation", False):
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
                year_obj = FederalPoveryLimit.objects.get(year=year_value)
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
            "show_in_has_benefits_step",
            "has_calculator",
            "value_format",
        ]

        for field_name in simple_config_fields:
            if field_name in configuration:
                setattr(program, field_name, configuration[field_name])
                self.stdout.write(f"  {field_name}: {configuration[field_name]}")

        # Handle base_program with validation against BaseProgram choices
        if "base_program" in configuration:
            base_program_value = configuration["base_program"]
            if base_program_value not in BaseProgram.values:
                valid_choices = ", ".join(BaseProgram.values)
                raise CommandError(f"Invalid base_program '{base_program_value}'. Must be one of: {valid_choices}")
            program.base_program = base_program_value
            self.stdout.write(f"  base_program: {base_program_value}")

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

        self._set_warning_scope(warning, warning_config)

        # Update translations for the warning message
        translated_fields = WarningMessage.objects.translated_fields

        # Map config fields to model fields
        field_values = {
            "message": warning_config.get("message", ""),
            "link_text": warning_config.get("link_text", ""),
            "link_url": warning_config.get("link_url", ""),
        }

        self._bulk_update_entity_translations(warning, field_values, "warning", translated_fields)

    def _set_warning_scope(self, warning: WarningMessage, warning_config: dict[str, Any]) -> None:
        """
        Apply the legal statuses and counties that narrow who sees a warning.

        Both are optional and both mean "no restriction" when absent: the frontend
        shows a warning with no legal statuses to every citizenship, and
        `WarningCalculator.county_eligible` treats an empty county list as all
        counties. A config that omits them therefore gets the same unrestricted
        warning it got before these fields were read.

        An unknown name is a warning rather than an error, matching how
        `legal_status_required` is handled for the program itself. Both are
        reported, since a silently dropped status would widen the audience for a
        message meant for one group.
        """
        statuses = []
        for status_code in warning_config.get("legal_statuses", []):
            try:
                statuses.append(LegalStatus.objects.get(status=status_code))
            except LegalStatus.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  Warning: Legal status '{status_code}' not found"))
        if statuses:
            warning.legal_statuses.set(statuses)
            self.stdout.write(f"  Legal statuses: {', '.join(s.status for s in statuses)}")

        counties = []
        for county_name in warning_config.get("counties", []):
            try:
                counties.append(County.objects.get(name=county_name, white_label=warning.white_label))
            except County.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  Warning: County '{county_name}' not found"))
        if counties:
            warning.counties.set(counties)
            self.stdout.write(f"  Counties: {', '.join(c.name for c in counties)}")

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

    def _import_navigators(
        self, program: Program, navigators_config: list[dict[str, Any]], order_offset: int = 0
    ) -> None:
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
            order_offset: Starting value for the order of newly created links. Defaults to 0
                for a fresh import; reconcile passes the next free order so existing links
                keep their position.
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
                    defaults={"order": order_offset + idx},
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
