import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

import jsonschema
from decouple import config
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from programs.models import Program
from screener.models import Screen
from screener.serializers import ScreenSerializer
from validations.models import Validation


class Command(BaseCommand):
    help = "Import validation test cases from a JSON file"

    def add_arguments(self, parser):
        parser.add_argument(
            "json_file",
            type=str,
            help="Path to JSON file containing test cases",
        )

    def handle(self, *args, **options):
        json_file_path = options["json_file"]

        # Load test cases from JSON file
        try:
            test_cases = self._load_test_cases(json_file_path)
        except FileNotFoundError:
            raise CommandError(f"File not found: {json_file_path}")
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON file: {e}")

        # Validate JSON against schema
        try:
            self._validate_against_schema(test_cases)
        except jsonschema.ValidationError as e:
            raise CommandError(f"JSON validation failed: {e.message}")

        # Validate that all programs exist
        self._validate_programs_exist(test_cases)

        # Process test cases
        results = self._process_test_cases(test_cases)

        # Output summary
        self._output_summary(results)

    def _load_test_cases(self, file_path: str) -> List[Dict[str, Any]]:
        """Load test cases from JSON file"""
        with open(file_path, "r") as f:
            data = json.load(f)

        # Handle both array and single object
        if isinstance(data, list):
            return data
        else:
            return [data]

    def _validate_against_schema(self, test_cases: List[Dict[str, Any]]) -> None:
        """Validate test cases against JSON schema"""
        # Load schema from the same directory as the command
        schema_path = Path(__file__).parent / "test_case_schema.json"
        with open(schema_path, "r") as f:
            schema = json.load(f)

        # Validate each test case
        for test_case in test_cases:
            jsonschema.validate(instance=test_case, schema=schema)

    def _validate_programs_exist(self, test_cases: List[Dict[str, Any]]) -> None:
        """Validate that all referenced programs exist in the database"""
        for test_case in test_cases:
            expected_results = test_case["expected_results"]

            # Handle both single object and array format
            if isinstance(expected_results, dict):
                results_list = [expected_results]
            else:
                results_list = expected_results

            for result in results_list:
                program_name = result["program_name"]
                if not Program.objects.filter(name_abbreviated=program_name).exists():
                    raise CommandError(
                        f"Program with name_abbreviated '{program_name}' does not exist. "
                        f"Test case: {test_case['notes']}"
                    )

    @transaction.atomic
    def _process_test_cases(self, test_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process all test cases and create screens/validations"""
        results = []

        for test_case in test_cases:
            result = {
                "notes": test_case["notes"],
                "success": False,
                "screen_uuid": None,
                "screen_url": None,
                "validations_created": [],
                "errors": [],
            }

            try:
                # Create screen
                screen = self._create_screen(test_case["household"])
                result["screen_uuid"] = str(screen.uuid)

                # Generate screen URL
                white_label = screen.white_label.code
                frontend_domain = config("FRONTEND_DOMAIN", default="http://localhost:3000")
                result["screen_url"] = (
                    f"{frontend_domain}/{white_label}/{screen.uuid}/results/benefits"
                )

                # Create validations
                expected_results = test_case["expected_results"]
                if isinstance(expected_results, dict):
                    results_list = [expected_results]
                else:
                    results_list = expected_results

                for expected in results_list:
                    try:
                        validation = self._create_validation(
                            screen=screen,
                            program_name=expected["program_name"],
                            eligible=expected["eligible"],
                            value=expected.get("value", 0),
                            notes=test_case["notes"],
                        )
                        result["validations_created"].append(
                            {
                                "program_name": validation.program_name,
                                "eligible": validation.eligible,
                                "value": str(validation.value),
                            }
                        )
                    except Exception as e:
                        result["errors"].append(f"Failed to create validation: {str(e)}")

                result["success"] = len(result["errors"]) == 0

            except Exception as e:
                result["errors"].append(f"Failed to process test case: {str(e)}")

            results.append(result)

        return results

    def _create_screen(self, household_data: Dict[str, Any]) -> Screen:
        """Create a screen from household data."""
        # Ensure is_test is set to True
        household_data["is_test"] = True

        # Create new screen
        serializer = ScreenSerializer(data=household_data)
        serializer.is_valid(raise_exception=True)
        screen = serializer.save()

        self.stdout.write(self.style.SUCCESS(f"Created new screen: {screen.uuid}"))
        return screen

    def _create_validation(
        self,
        screen: Screen,
        program_name: str,
        eligible: bool,
        value: float,
        notes: str,
    ) -> Validation:
        """Create a validation record"""
        # Check if validation already exists with matching values
        existing = Validation.objects.filter(
            screen=screen,
            program_name=program_name,
            eligible=eligible,
            value=Decimal(str(value)),
        ).first()

        if existing:
            # Skip - validation already exists with same values
            self.stdout.write(
                self.style.WARNING(f"Skipped existing validation for {program_name} (already exists with same values)")
            )
            return existing

        # Create new validation
        validation = Validation.objects.create(
            screen=screen,
            program_name=program_name,
            eligible=eligible,
            value=Decimal(str(value)),
            notes=notes,
        )
        self.stdout.write(self.style.SUCCESS(f"Created validation for {program_name}"))
        return validation

    def _output_summary(self, results: List[Dict[str, Any]]) -> None:
        """Output a summary of the import results"""
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("IMPORT SUMMARY"))
        self.stdout.write("=" * 80 + "\n")

        total = len(results)
        successful = sum(1 for r in results if r["success"])
        failed = total - successful

        self.stdout.write(f"Total test cases: {total}")
        self.stdout.write(self.style.SUCCESS(f"Successful: {successful}"))
        if failed > 0:
            self.stdout.write(self.style.ERROR(f"Failed: {failed}"))
        self.stdout.write(f"Screens created: {total}")
        self.stdout.write("")

        # Detail each test case
        for i, result in enumerate(results, 1):
            self.stdout.write(f"\n{i}. {result['notes']}")
            self.stdout.write("-" * 80)

            if result["success"]:
                self.stdout.write(self.style.SUCCESS("✓ SUCCESS"))
            else:
                self.stdout.write(self.style.ERROR("✗ FAILED"))

            if result["screen_uuid"]:
                self.stdout.write(f"Screen UUID: {result['screen_uuid']}")

            if result["screen_url"]:
                self.stdout.write(f"Screen URL: {result['screen_url']}")

            if result["validations_created"]:
                self.stdout.write(f"Validations created: {len(result['validations_created'])}")
                for validation in result["validations_created"]:
                    eligible_str = "✓ Eligible" if validation["eligible"] else "✗ Not Eligible"
                    self.stdout.write(
                        f"  - {validation['program_name']}: {eligible_str} "
                        f"(Value: ${validation['value']})"
                    )

            if result["errors"]:
                self.stdout.write(self.style.ERROR("Errors:"))
                for error in result["errors"]:
                    self.stdout.write(self.style.ERROR(f"  - {error}"))

        self.stdout.write("\n" + "=" * 80)
