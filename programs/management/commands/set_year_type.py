from django.core.management.base import BaseCommand
from programs.models import Program


class Command(BaseCommand):
    help = "Assign year_type to programs"

    def add_arguments(self, parser):
        parser.add_argument("year_type", choices=["calendar_year", "fiscal_year", "hardcoded"])
        parser.add_argument("--programs", nargs="+", help="Name abbreviations to target (e.g. co_snap il_medicaid)")
        parser.add_argument("--all", action="store_true", help="Apply to all programs")

    def handle(self, *args, **options):
        year_type = options["year_type"]

        if options["all"]:
            programs = Program.objects.all()
        elif options["programs"]:
            requested = set(options["programs"])
            programs = Program.objects.filter(name_abbreviated__in=requested)
            found = set(programs.values_list("name_abbreviated", flat=True))
            missing = requested - found
            if missing:
                self.stdout.write(self.style.WARNING(f"Not found: {', '.join(missing)}"))
        else:
            self.stdout.write(self.style.ERROR("Provide --all or --programs <name_abbreviated ...>"))
            return

        updated = programs.update(year_type=year_type)
        self.stdout.write(self.style.SUCCESS(f"Updated {updated} program(s) to year_type='{year_type}'"))
