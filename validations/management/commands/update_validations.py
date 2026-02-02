import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

import jsonschema
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from screener.models import Screen
from validations.models import Validation


class Command(BaseCommand):
    help = "Update existing Validation records from a JSON file"

    def add_arguments(self, parser):
        parser.add_argument(
            "json_file",
            type=str,
            help="Path to JSON file containing validation updates",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and show what would be updated without making changes",
        )

    def handle(self, *args, **options):
        json_file_path = options["json_file"]
        dry_run = options.get("dry_run", False)

        # Load and parse JSON
        try:
            update_data = self._load_json(json_file_path)
        except FileNotFoundError as e:
            raise CommandError(f"File not found: {json_file_path}") from e
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON: {e.msg} at line {e.lineno}, column {e.colno}") from e

        # Validate against schema
        try:
            self._validate_against_schema(update_data)
        except jsonschema.ValidationError as e:
            raise CommandError(f"JSON validation failed: {e.message}") from e

        self.stdout.write(self.style.SUCCESS("JSON validation passed"))

        # Validate that all referenced validations exist
        self._validate_validations_exist(update_data["updates"])

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDry run - no changes made"))
            self._output_dry_run_summary(update_data)
            return

        # Process updates
        results = self._process_updates(update_data)
        self._output_summary(update_data, results)

    def _load_json(self, file_path: str) -> Dict[str, Any]:
        """Load JSON from file"""
        with open(file_path, "r") as f:
            return json.load(f)

    def _validate_against_schema(self, data: Dict[str, Any]) -> None:
        """Validate data against the update validation schema"""
        schema_path = Path(__file__).parent / "update_validations" / "update_validation_schema.json"
        with open(schema_path, "r") as f:
            schema = json.load(f)

        jsonschema.validate(instance=data, schema=schema)

    def _validate_validations_exist(self, updates: List[Dict[str, Any]]) -> None:
        """Validate that all referenced validations exist in the database"""
        for update in updates:
            screen_uuid = update["screen_uuid"]
            program_name = update["program_name"]

            try:
                screen = Screen.objects.get(uuid=screen_uuid)
            except Screen.DoesNotExist:
                raise CommandError(f"Screen with UUID '{screen_uuid}' does not exist")

            if not Validation.objects.filter(screen=screen, program_name=program_name).exists():
                raise CommandError(f"Validation for screen '{screen_uuid}' and program '{program_name}' does not exist")

    @transaction.atomic
    def _process_updates(self, update_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process all updates and return results"""
        results = []

        for update in update_data["updates"]:
            result = self._update_validation(update)
            results.append(result)

        return results

    def _update_validation(self, update: Dict[str, Any]) -> Dict[str, Any]:
        """Update a single validation record"""
        screen = Screen.objects.get(uuid=update["screen_uuid"])
        validation = Validation.objects.get(screen=screen, program_name=update["program_name"])

        result = {
            "screen_uuid": update["screen_uuid"],
            "program_name": update["program_name"],
            "changes": [],
        }

        # Update eligible if provided
        if "eligible" in update:
            old_value = validation.eligible
            new_value = update["eligible"]
            if old_value != new_value:
                validation.eligible = new_value
                result["changes"].append(f"eligible: {old_value} → {new_value}")

        # Update value if provided
        if "value" in update:
            old_value = validation.value
            new_value = Decimal(str(update["value"]))
            if old_value != new_value:
                validation.value = new_value
                result["changes"].append(f"value: ${old_value} → ${new_value}")

        # Update notes if provided
        if "notes" in update:
            old_value = validation.notes
            new_value = update["notes"]
            if old_value != new_value:
                validation.notes = new_value
                old_preview = old_value[:30] + "..." if len(old_value) > 30 else old_value
                new_preview = new_value[:30] + "..." if len(new_value) > 30 else new_value
                result["changes"].append(f"notes: '{old_preview}' → '{new_preview}'")

        validation.save()
        return result

    def _output_dry_run_summary(self, update_data: Dict[str, Any]) -> None:
        """Output a summary of what would be updated"""
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("DRY RUN SUMMARY"))
        self.stdout.write("=" * 70)

        self.stdout.write(f"\nDescription: {update_data['description']}")
        self.stdout.write(f"Total updates: {len(update_data['updates'])}")

        self.stdout.write("\nValidations that would be updated:")
        for i, update in enumerate(update_data["updates"], 1):
            screen = Screen.objects.get(uuid=update["screen_uuid"])
            validation = Validation.objects.get(screen=screen, program_name=update["program_name"])

            self.stdout.write(f"\n{i}. {update['program_name']} (Screen: {update['screen_uuid'][:8]}...)")

            if "eligible" in update and validation.eligible != update["eligible"]:
                self.stdout.write(f"   eligible: {validation.eligible} → {update['eligible']}")
            if "value" in update and validation.value != Decimal(str(update["value"])):
                self.stdout.write(f"   value: ${validation.value} → ${update['value']}")
            if "notes" in update and validation.notes != update["notes"]:
                self.stdout.write(f"   notes: would be updated")

        self.stdout.write("\n" + "=" * 70)

    def _output_summary(self, update_data: Dict[str, Any], results: List[Dict[str, Any]]) -> None:
        """Output a summary of the updates"""
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("UPDATE SUMMARY"))
        self.stdout.write("=" * 70)

        self.stdout.write(f"\nDescription: {update_data['description']}")

        updates_with_changes = [r for r in results if r["changes"]]
        self.stdout.write(f"Total updates processed: {len(results)}")
        self.stdout.write(f"Validations modified: {len(updates_with_changes)}")

        if updates_with_changes:
            self.stdout.write("\nChanges made:")
            for result in updates_with_changes:
                self.stdout.write(f"\n  {result['program_name']} (Screen: {result['screen_uuid'][:8]}...)")
                for change in result["changes"]:
                    self.stdout.write(f"    - {change}")

        # List programs affected
        programs = set(update["program_name"] for update in update_data["updates"])
        self.stdout.write(f"\nPrograms affected: {', '.join(sorted(programs))}")

        self.stdout.write("\n" + "=" * 70)
