import argparse
from dataclasses import dataclass
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.template import Template, Context
from django.shortcuts import loader
from screener.models import WhiteLabel
import pathlib


@dataclass
class FileTemplate:
    template_name: str
    output_path: Template


class Command(BaseCommand):
    help = """
    Create new white label and add template files for white labels
    """

    dry_run: bool

    TEMPLATES = [
        FileTemplate("config", Template("configuration/white_labels/{{code}}.py")),
        FileTemplate("program", Template("programs/programs/{{code}}/example_program/calculator.py")),
        FileTemplate("empty_init_file", Template("programs/programs/{{code}}/example_program/__init__.py")),
        FileTemplate("program_init", Template("programs/programs/{{code}}/__init__.py")),
        FileTemplate("pe_program_spm", Template("programs/programs/{{code}}/pe/spm.py")),
        FileTemplate("pe_program_tax", Template("programs/programs/{{code}}/pe/tax.py")),
        FileTemplate("pe_program_member", Template("programs/programs/{{code}}/pe/member.py")),
        FileTemplate("pe_program_init", Template("programs/programs/{{code}}/pe/__init__.py")),
        FileTemplate("urgent_need", Template("programs/urgent_needs/{{code}}/example_urgent_need.py")),
        FileTemplate("urgent_need_init", Template("programs/urgent_needs/{{code}}/__init__.py")),
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "code",
            nargs=None,
            help="The code of the new white label",
        )
        parser.add_argument(
            "name",
            nargs=None,
            help="The name of the new white label",
        )
        parser.add_argument(
            "--dry-run",
            action=argparse.BooleanOptionalAction,
            help="Don't actually create anything",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if str(settings.BASE_DIR) != os.getcwd():
            self.stdout.write(self.style.ERROR(f"Please run this command from the root directory of this project"))
            return

        code = options["code"]
        name = options["name"]
        self.dry_run = options["dry_run"]

        if WhiteLabel.objects.filter(code=code).count() > 0:
            self.stdout.write(self.style.ERROR(f"\nWhite label with code of '{code}' already exists"))
            return

        white_label = WhiteLabel.objects.create(code=code, name=name)
        self._message(f"White label created with code: '{code}' and Name: '{name}'")

        for template in self.TEMPLATES:
            self._build_template(white_label, template)

        if self.dry_run:
            white_label.delete()

    def _build_template(self, white_label: WhiteLabel, template: FileTemplate):
        context = {"code": white_label.code, "name": white_label.name, "code_capitalize": white_label.code.capitalize()}
        contents = loader.render_to_string(f"new_white_label/{template.template_name}.py", context=context)
        path = template.output_path.render(Context(context))

        self._message(f"Creating new file at: {path}")

        if self.dry_run:
            return

        output_file = pathlib.Path(path)
        output_file.parent.mkdir(exist_ok=True, parents=True)
        output_file.write_text(contents)

    def _message(self, message: str):
        self.stdout.write(self.style.SUCCESS(message))
