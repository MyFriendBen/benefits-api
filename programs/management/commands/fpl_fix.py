from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Deprecated (MFB-564): used to force every program onto one shared "
        "'THIS YEAR' row. That would now corrupt year_type classification, use "
        "set_year_type instead."
    )

    def handle(self, *args, **options):
        raise CommandError(
            "fpl_fix is deprecated: it force-updates every program's year regardless of "
            "year_type, which would silently reassign fiscal_year and hardcoded programs "
            "onto the calendar sentinel row. Use `set_year_type` to reclassify specific "
            "programs instead."
        )
