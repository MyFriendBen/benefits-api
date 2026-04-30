from django.core.management.base import BaseCommand
from programs.models import (
    Program,
    Navigator,
)


class Command(BaseCommand):
    help = "Remove all programs and navigators and their translations"

    def handle(self, *args, **options):
        program_translated_fields = (
            "description_short",
            "name",
            "description",
            "learn_more_link",
            "apply_button_link",
            "estimated_delivery_time",
            "estimated_application_time",
            "warning",
        )

        navigator_translated_fields = (
            "name",
            "email",
            "assistance_link",
            "description",
        )

        navigators = Navigator.objects.all()
        programs = Program.objects.all()

        for navigator in navigators:
            translations_to_delete = []
            for field in navigator_translated_fields:
                translations_to_delete.append(getattr(navigator, field))
            navigator.delete()
            for translation in translations_to_delete:
                translation.delete()

        for program in programs:
            translations_to_delete = []
            for field in program_translated_fields:
                translations_to_delete.append(getattr(program, field))
            program.delete()
            for translation in translations_to_delete:
                translation.delete()

        self.stdout.write(self.style.SUCCESS("Successfully deleted all programs and navigators and their translations"))
