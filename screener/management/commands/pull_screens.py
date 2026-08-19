from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models import Prefetch
from tqdm import tqdm
from authentication.models import User
from screener.models import (
    EligibilitySnapshot,
    EnergyCalculatorMember,
    EnergyCalculatorScreen,
    Expense,
    HouseholdMember,
    IncomeStream,
    Insurance,
    Message,
    ProgramEligibilitySnapshot,
    Screen,
    WhiteLabel,
)
from django.db import transaction


class Command(BaseCommand):
    MIGRATION_SOURCE_DB = "migration_source"
    PROGRESS_TITLE_WIDTH = 13
    CHUNK_SIZE = 1_000

    help = f"Pull screens from the '{MIGRATION_SOURCE_DB}' database"

    class CheckFailed(Exception):
        pass

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.HAS_MIGRATION_SOURCE_DB:
            self.stdout.write(f"No '{self.MIGRATION_SOURCE_DB}' db set up", self.style.ERROR)
            return

        source_screens: list[Screen] = Screen.objects.using(self.MIGRATION_SOURCE_DB).prefetch_related(
            Prefetch("user", queryset=User.objects.order_by("pk")),
            Prefetch("white_label", queryset=WhiteLabel.objects.order_by("pk")),
            Prefetch("household_members", queryset=HouseholdMember.objects.order_by("pk")),
            Prefetch("household_members__income_streams", queryset=IncomeStream.objects.order_by("pk")),
            Prefetch("household_members__insurance", queryset=Insurance.objects.order_by("pk")),
            Prefetch("household_members__energy_calculator", queryset=EnergyCalculatorMember.objects.order_by("pk")),
            Prefetch("eligibility_snapshots", queryset=EligibilitySnapshot.objects.order_by("pk")),
            Prefetch(
                "eligibility_snapshots__program_snapshots",
                queryset=ProgramEligibilitySnapshot.objects.order_by("pk"),
            ),
            Prefetch("expenses", queryset=Expense.objects.order_by("pk")),
            Prefetch("messages", queryset=Message.objects.order_by("pk")),
            Prefetch("energy_calculator", queryset=EnergyCalculatorScreen.objects.order_by("pk")),
        )
        main_checks = self._key_checks()

        for screen in tqdm(
            source_screens.iterator(chunk_size=self.CHUNK_SIZE),
            desc="Screens".ljust(self.PROGRESS_TITLE_WIDTH),
            total=source_screens.count(),
        ):
            baseline_screen_check = self._screen_key_checks(screen)
            user = screen.user
            if user is not None:
                user.pk = None
                user.save(using="default")

            try:
                white_label = WhiteLabel.objects.get(code=screen.white_label.code)
            except WhiteLabel.DoesNotExist:
                raise Exception(f"White label with code '{screen.white_label.code}' does not exist. Please add it.")

            screen.pk = None
            if user is not None:
                screen.user_id = user.id
            screen.white_label_id = white_label.pk
            screen.save(using="default")

            for expense in screen.expenses.all():
                expense.pk = None
                expense.screen_id = screen.pk
                expense.save(using="default")

            for message in screen.messages.all():
                message.pk = None
                message.screen_id = screen.pk
                message.save(using="default")

            for snapshot in screen.eligibility_snapshots.all():
                snapshot.pk = None
                snapshot.screen_id = screen.pk
                snapshot.save(using="default")

                for program_snapshot in snapshot.program_snapshots.all():
                    program_snapshot.pk = None
                    program_snapshot.eligibility_snapshot_id = snapshot.pk
                    program_snapshot.save(using="default")

            for member in screen.household_members.all():
                member.pk = None
                member.screen_id = screen.pk
                member.save(using="default")

                for income in member.income_streams.all():
                    income.pk = None
                    income.household_member_id = member.pk
                    income.screen_id = screen.pk
                    income.save(using="default")

                if hasattr(member, "insurance"):
                    member.insurance.pk = None
                    member.insurance.household_member_id = member.pk
                    member.insurance.save(using="default")

                if hasattr(member, "energy_calculator"):
                    member.energy_calculator.pk = None
                    member.energy_calculator.household_member_id = member.pk
                    member.energy_calculator.save(using="default")

            if hasattr(screen, "energy_calculator"):
                screen.energy_calculator.pk = None
                screen.energy_calculator.screen_id = screen.pk
                screen.energy_calculator.save(using="default")

            screen.refresh_from_db()
            self._check_screen(baseline_screen_check, self._screen_key_checks(screen))

        self._check_checks(main_checks, self._key_checks())

    # create a bunch of checks to try to alert us if something is wrong
    def _screen_key_checks(self, screen: Screen):
        checks = []

        # check household_members
        checks.append(len(screen.household_members.all()))
        # check expenses
        checks.append(len(screen.expenses.all()))
        # check eligibility_snapshots
        checks.append(len(screen.eligibility_snapshots.all()))
        # check messages
        checks.append(len(screen.messages.all()))
        # check white_label
        checks.append(screen.white_label.code)
        # check user
        checks.append(screen.user.external_id if screen.user is not None else None)
        # check energy_calculator
        checks.append(hasattr(screen, "energy_calculator"))

        household_members = screen.household_members.all().order_by("pk")
        # check the income_streams
        checks.append([len(h.income_streams.all()) for h in household_members])
        # check the screen
        checks.append([h.screen.uuid for h in household_members])
        # check the insurance
        checks.append([hasattr(h, "insurance") for h in household_members])
        # check energy_calculator
        checks.append([hasattr(h, "energy_calculator") for h in household_members])

        snapshots = screen.eligibility_snapshots.all().order_by("pk").prefetch_related("program_snapshots")
        # check the screen
        checks.append([s.screen.uuid for s in snapshots])
        # check the program_snapshots
        checks.append([len(s.program_snapshots.all()) for s in snapshots])

        return checks

    def _key_checks(self):
        checks = []
        screens: list[Screen] = (
            Screen.objects.all()
            .order_by("pk")
            .prefetch_related(
                "household_members",
                "household_members__income_streams",
                "expenses",
                "eligibility_snapshots",
                "eligibility_snapshots__program_snapshots",
            )
        )

        for screen in tqdm(
            screens.iterator(chunk_size=self.CHUNK_SIZE),
            desc="Making Tests".ljust(self.PROGRESS_TITLE_WIDTH),
            total=screens.count(),
        ):
            checks.append(self._screen_key_checks(screen))

        return checks

    def _check_checks(self, baseline_screens: list[list], checking_screens: list[list]):
        if len(baseline_screens) > len(checking_screens):
            print(str(baseline_screens) + "\n" * 2 + str(checking_screens))
            raise self.CheckFailed(f"More past screens than new screens")

        i = 0
        screens = list(zip(baseline_screens, checking_screens))
        for baseline, checking in tqdm(screens, desc="Running Tests".ljust(self.PROGRESS_TITLE_WIDTH)):
            self._check_screen(baseline, checking)
            i += 1

    def _check_screen(self, baseline_screen: list, checking_screen: list):
        i = 0
        for check in zip(baseline_screen, checking_screen, strict=True):
            if check[0] != check[1]:
                raise self.CheckFailed(f"Check failed for check '{i}'. '{check[0]}' != '{check[1]}'")
            i += 1
