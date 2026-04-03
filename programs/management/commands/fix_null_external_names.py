from django.core.management.base import BaseCommand
from programs.models import Program
from django.db import transaction


class Command(BaseCommand):
    help = """
    Assign unique external_names to white-label instances of a program that currently have external_name=None.
    
    This fixes the issue where bulk_import fails due to MultipleObjectsReturned on external_name=None.
    It assigns a new name in the format: <name_abbreviated>_<white_label_code>.

    Usage Examples:
      # Dry run (default): safely see what would be changed for 'trump_account' programs
      python manage.py fix_null_external_names

      # Commit changes: actually save the updates to the database
      python manage.py fix_null_external_names --commit

      # Run for a different program name:
      python manage.py fix_null_external_names --name=other_program --commit
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--name",
            type=str,
            default="trump_account",
            help="The name_abbreviated of the program to fix (default: trump_account)",
        )
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Commit the changes to the database (without this flag, it does a dry run).",
        )

    def handle(self, *args, **options):
        name_abbreviated = options["name"]
        commit = options["commit"]

        affected = Program.objects.filter(name_abbreviated=name_abbreviated, external_name__isnull=True)
        count = affected.count()

        if count == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"No programs found with name_abbreviated='{name_abbreviated}' and external_name=None. Nothing to do."
                )
            )
            return

        self.stdout.write(f"Found {count} programs that need fixing.")

        try:
            with transaction.atomic():
                for p in affected:
                    new_external_name = f"{name_abbreviated}_{p.white_label.code}"

                    # Check if the generated external_name already exists to avoid UniqueConstraint exceptions
                    if Program.objects.filter(external_name=new_external_name).exists():
                        self.stderr.write(
                            self.style.ERROR(
                                f"  Cannot assign '{new_external_name}' because a program with that external_name already exists!"
                            )
                        )
                        raise ValueError(f"Duplicate external_name: {new_external_name}")

                    self.stdout.write(
                        f"  id={p.id} | white_label={p.white_label.code} -> changing external_name to '{new_external_name}'"
                    )
                    p.external_name = new_external_name
                    p.save(update_fields=["external_name"])

                if not commit:
                    # Rolling back explicitly since --commit was not provided
                    transaction.set_rollback(True)
                    self.stdout.write(
                        self.style.WARNING("Dry run complete. No changes were saved. Use --commit to apply changes.")
                    )
                    return

                self.stdout.write(self.style.SUCCESS(f"\nSuccessfully updated {count} programs."))

        except ValueError as e:
            self.stderr.write(self.style.ERROR(f"Aborting due to error: {e}"))
