from django.core.management.base import BaseCommand
from programs.models import (
    Program,
    Navigator,
    FederalPoveryLimit,
    UrgentNeedCategory,
    LegalStatus,
)
import random


class Command(BaseCommand):
    help = "Add back programs and navigators"
    programs = [
        {"abbr": "cwd_medicaid", "external": "cwd_medicaid"},
        {"abbr": "awd_medicaid", "external": "awd_medivaid"},
        {"abbr": "emergency_medicaid", "external": "emergency_medicaid"},
        {"abbr": "medicare_savings", "external": "medicare_savings"},
        {"abbr": "ssi", "external": "ssi"},
        {"abbr": "trua", "external": "trua"},
        {"abbr": "rhc", "external": "rhc"},
        {"abbr": "wic", "external": "wic"},
        {"abbr": "omnisalud", "external": "omnisalud"},
        {"abbr": "dpp", "external": "dpp"},
        {"abbr": "lwcr", "external": "lwcr"},
        {"abbr": "lifeline", "external": "lifeline"},
        {"abbr": "fps", "external": "fps"},
        {"abbr": "leap", "external": "leap"},
        {"abbr": "pell_grant", "external": "pell_grant"},
        {"abbr": "mydenver", "external": "mydenver"},
        {"abbr": "nccip", "external": "nccip"},
        {"abbr": "ede", "external": "ede"},
        {"abbr": "cdhcs", "external": "cdhcs"},
        {"abbr": "nslp", "external": "nslp"},
        {"abbr": "erc", "external": "erc"},
        {"abbr": "co_head_start", "external": "co_head_start"},
        {"abbr": "cccap", "external": "cccap"},
        {"abbr": "chp", "external": "chp"},
        {"abbr": "coeitc", "external": "coexeitc"},
        {"abbr": "acp", "external": "acp"},
        {"abbr": "rtdlive", "external": "rtdlive"},
        {"abbr": "coctc", "external": "coctc"},
        {"abbr": "ssdi", "external": "ssdi"},
        {"abbr": "tanf", "external": "tanf"},
        {"abbr": "coeitc", "external": "coeitc"},
        {"abbr": "cpcr", "external": "cpcr"},
        {"abbr": "eitc", "external": "eitc"},
        {"abbr": "cfhc", "external": "cfhc"},
        {"abbr": "myspark", "external": "myspark"},
        {"abbr": "snap", "external": "snap"},
        {"abbr": "ctc", "external": "ctc"},
        {"abbr": "medicaid", "external": "medicaid"},
        {"abbr": "andcs", "external": "andcs"},
        {"abbr": "oap", "external": "oap"},
        {"abbr": "upk", "external": "upk"},
    ]
    navigators = [
        "gac",
        "bia",
        "bdt",
        "acc",
        "mhuw",
        "dpp",
        "uph",
        "cowicc",
    ]

    def handle(self, *args, **options):
        fpl = FederalPoveryLimit.objects.get(year="THIS YEAR")

        # create legal statuses
        statuses = []
        for status in LegalStatus.objects.all():
            statuses.append(status)

        # create urgent need categories
        categories = []
        for category in UrgentNeedCategory.objects.all():
            categories.append(category)

        # create programs
        programs = []
        for program in self.programs:
            new_program = Program.objects.new_program(program["abbr"])
            new_program.external_name = program["external"]
            new_program.year = fpl
            for status in statuses:
                # set all legal statuses for each program
                new_program.legal_status_required.add(status)
            new_program.save()
            programs.append(new_program)

        # create navigators
        for navigator in self.navigators:
            new_nav = Navigator.objects.new_navigator(navigator, None)
            new_nav.external_name = navigator
            # give each navigator a random program
            new_nav.program.add(random.choice(programs))
            new_nav.save()

        self.stdout.write(self.style.SUCCESS("Successfully created programs and navigators"))
