from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from programs.models import Program
import uuid
from screener.models import WhiteLabel
from configuration.white_labels import white_label_config
from typing import Dict
from translations.models import Translation


class Command(BaseCommand):
    help = "Transfer programs from one white label to another"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "target_white_label",
            type=str,
            help="The white label code to transfer programs to target whilte label",
        )
        parser.add_argument(
            "external_names",
            nargs="+",
            type=str,
            help="External names of programs to transfer",
        )

    def validate_white_label(self, white_label_code) -> bool:
        """Validate white label exists in config and database"""
        if white_label_code not in white_label_config:
            self.stdout.write(
                self.style.ERROR(
                    f"White label '{white_label_code}' not found in configuration. "
                    f"Please run: python manage.py add_config {white_label_code}"
                )
            )
            return False

        try:
            WhiteLabel.objects.get(code=white_label_code)
            return True
        except ObjectDoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f"White label '{white_label_code}' not found in database. "
                    f"Please ensure it's configured properly."
                )
            )
            return False

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        target_code = options["target_white_label"]
        external_names = options["external_names"]

        # Validate white label exists
        if not self.validate_white_label(target_code):
            return

        target_white_label = WhiteLabel.objects.get(code=target_code)

        for external_name in external_names:
            try:
                # Get source program
                source_program = Program.objects.get(external_name=external_name)

                # Store translations before creating new program
                translation_mapping: Dict[str, Translation] = {}

                # Get all translation fields from Program model
                translated_fields = Program.objects.translated_fields

                # Create copies of all translations
                for field in translated_fields:
                    source_translation = getattr(source_program, field)
                    if source_translation:

                        # Create new translation with same text
                        new_translation = Translation.objects.add_translation(
                            label=f"program.{source_program.external_name}_{source_program.id}-{field}-{str(uuid.uuid4())}",
                            default_message=source_translation.default_message,
                            active=source_translation.active,
                            no_auto=source_translation.no_auto,
                        )

                        # Copy translations for all languages
                        for translation in source_translation.translations.all():
                            Translation.objects.edit_translation_by_id(
                                new_translation.id,
                                translation.language_code,
                                translation.text,
                                translation.edited,
                            )

                        translation_mapping[field] = new_translation

                legal_statuses = source_program.legal_status_required.all()

                # Create new program
                new_program = source_program
                new_program.pk = None
                new_program.white_label = target_white_label
                new_program.year = source_program.year
                new_program.external_name = None
                new_program.category = None
                new_program.active = False

                # Set the new translations
                for field, translation in translation_mapping.items():
                    setattr(new_program, field, translation)

                # Save new program
                new_program.save()

                # Then set the many-to-many relationship

                new_program.required_programs.set([])
                new_program.documents.set([])
                new_program.legal_status_required.set(legal_statuses)
                self.stdout.write("Reminder: Please add external names to the transferred programs.")

            except Program.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Error: Program '{external_name}' not found"))
                continue
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error during transfer: {str(e)}"))
                continue
