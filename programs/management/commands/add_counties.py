from django.core.management.base import BaseCommand
from programs.models import County
from screener.models import WhiteLabel
from configuration.models import Configuration
from django.core.exceptions import ObjectDoesNotExist


class Command(BaseCommand):
    help = "Adds counties"

    def add_arguments(self, parser):
        parser.add_argument("white_label", type=str, help="The state code for the white label")

    def handle(self, *args, **options):
        try:
            white_label = WhiteLabel.objects.get(code=options["white_label"])
        except ObjectDoesNotExist:
            self.stdout.write(self.style.WARNING(f'White label for "{options["white_label"]}" is not in the database'))
            return
        counties_from_config = Configuration.counties_by_zipcode(white_label)
        if counties_from_config is not None:
            counties = set()

            for value in counties_from_config.values():
                counties.update(value.keys())

            for county in counties:
                County.objects.get_or_create(name=county, white_label=white_label)
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'"counties_by_zipcode" config object for "{options["white_label"]}" is not in the database'
                )
            )
