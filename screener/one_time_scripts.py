from tqdm import trange
from integrations.services.hubspot.integration import Hubspot, upsert_user_hubspot
from .models import (
    Screen,
    EligibilitySnapshot,
    HouseholdMember,
    IncomeStream,
    Expense,
    Insurance,
)
import json
import uuid
import time


def generate_bwf_snapshots() -> None:
    bwf_ids = [
        "123",
        "121001",
        "119201",
        "119151",
        "118901",
        "119001",
        "118751",
        "118301",
        "118001",
        "117651",
        "117501",
        "117451",
        "116601",
        "116551",
        "116351",
        "116151",
        "115851",
        "115801",
        "114751",
        "114501",
        "114401",
        "114201",
        "114001",
        "113901",
        "113651",
        "113501",
        "113451",
        "111301",
        "108751",
        "108151",
        "107101",
        "106551",
        "106201",
        "101901",
        "101701",
        "100451",
        "100201",
        "95051",
        "93801",
        "82751",
        "82701",
        "77151",
        "71851",
        "71051",
        "70851",
        "70751",
        "70701",
        "70351",
        "70301",
        "70201",
        "68651",
        "67401",
        "67001",
        "66651",
        "66601",
        "66301",
        "65851",
        "65101",
        "65001",
        "64951",
        "64801",
        "64751",
        "62951",
        "59051",
        "59001",
        "58801",
        "58201",
        "57851",
        "57651",
        "57601",
        "56801",
        "56351",
        "56101",
        "55901",
        "55801",
        "55501",
        "55451",
        "55051",
        "54951",
        "54801",
        "54751",
        "54551",
        "76501",
        "54151",
        "53351",
        "53051",
        "52701",
        "52351",
        "52301",
        "52151",
        "51601",
        "51151",
        "51001",
        "49901",
        "49851",
        "49551",
        "49251",
        "48901",
        "48701",
        "48551",
        "48501",
        "48401",
        "47751",
        "46951",
        "46751",
        "46151",
        "46001",
        "41201",
        "40701",
        "40101",
    ]
    screens = Screen.objects.filter(external_id__in=bwf_ids).order_by("-submission_date")
    total_screens = screens.count()
    print("Total BWF Screens found: " + str(total_screens))

    screens_without_snapshots = []
    screen_eids = []
    for screen in screens:
        existing_snapshots = EligibilitySnapshot.objects.filter(screen=screen)
        if len(existing_snapshots) <= 0 and screen.external_id not in screen_eids:
            screens_without_snapshots.append(screen)
            screen_eids.append(screen.external_id)

    total_screens_without_snapshots = len(screens_without_snapshots)
    print("Total BWF screens without snapshots found: " + str(total_screens_without_snapshots))
    count = 0
    for screen in screens_without_snapshots:
        eligibility_snapshot = EligibilitySnapshot(screen=screen)
        eligibility_snapshot.save()
        eligibility_snapshot.generate_program_snapshots()
        count += 1
        print(
            "Snapshot "
            + str(count)
            + "/"
            + str(total_screens_without_snapshots)
            + " generated for "
            + str(screen.external_id)
        )


def generate_nav_snapshots() -> None:
    nav_ids = [
        "3171",
        "3183",
        "3200",
        "3230",
        "3233",
        "3243",
        "3245",
        "3248",
        "3260",
        "3373",
        "3374",
        "3375",
        "3376",
        "3377",
        "3300",
        "3301",
        "3310",
        "3312",
        "3313",
        "3316",
        "3343",
        "3363",
        "3364",
        "3365",
        "3368",
        "3397",
        "3398",
        "3399",
        "2686",
        "2693",
        "2690",
        "2688",
        "2694",
        "2707",
        "2715",
        "2710",
        "2711",
        "2709",
        "2713",
    ]
    screens = Screen.objects.filter(id__in=nav_ids)
    total_screens = screens.count()

    count = 0
    for screen in screens:
        eligibility_snapshot = EligibilitySnapshot(screen=screen)
        eligibility_snapshot.save()
        eligibility_snapshot.generate_program_snapshots()
        count += 1
        print("Snapshot " + str(count) + "/" + str(total_screens) + " generated for " + str(screen.id))


def generate_bia_sample_snapshot() -> None:
    nav_ids = ["4097", "4147", "4148", "4149"]
    screens = Screen.objects.filter(id__in=nav_ids)
    total_screens = screens.count()

    count = 0
    for screen in screens:
        eligibility_snapshot = EligibilitySnapshot(screen=screen)
        eligibility_snapshot.save()
        eligibility_snapshot.generate_program_snapshots()
        count += 1
        print("Snapshot " + str(count) + "/" + str(total_screens) + " generated for " + str(screen.id))


def add_from_json(new_json_str) -> None:
    """
    Add json string from screen endpoint as parameter. Use triple quotes if in shell
    """
    new_json = json.loads(new_json_str)

    screen = Screen.objects.create(
        **{k: v for k, v in new_json.items() if k not in ("household_members", "id", "uuid", "user", "expenses")},
    )

    members = []
    incomes = []
    expenses = []
    for member in new_json["household_members"]:
        household_member = {k: v for k, v in member.items() if k not in ("income_streams", "expenses", "screen", "id")}
        member_model = HouseholdMember(**household_member, screen=screen)
        members.append(member_model)

        for income in member["income_streams"]:
            income = {k: v for k, v in income.items() if k not in ("household_member", "screen", "id")}
            incomes.append(IncomeStream(**income, screen=screen, household_member=member_model))
    for expense in new_json["expenses"]:
        expense = {k: v for k, v in expense.items() if k not in ("household_member", "screen", "id")}
        expenses.append(Expense(**expense, screen=screen, household_member=member_model))

    HouseholdMember.objects.bulk_create(members)
    IncomeStream.objects.bulk_create(incomes)
    Expense.objects.bulk_create(expenses)

    print("id:", screen.id)
    print("uuid:", screen.uuid)


def uniqueUUIDs() -> None:
    screens = Screen.objects.all()

    currentUUIDs = []
    for screen in screens:
        if screen.uuid in currentUUIDs:
            print(screen.uuid, "was replaced")
            screen.uuid = uuid.uuid4()
            screen.save()
        currentUUIDs.append(screen.uuid)

    print("done")


def update_is_test_data() -> None:
    screens = Screen.objects.all()

    for screen in screens:
        screen.set_screen_is_test()

    print("done")


def fix_insurance() -> None:
    screens = Screen.objects.all()

    for screen in screens:
        members = screen.household_members.all()

        for member in members:
            try:
                member.insurance
            except Insurance.DoesNotExist:
                member.insurance = Insurance.objects.create(household_member=member)
                member.save()

    print("done")


def update_hubspot_extra_fields():
    raise Exception("Do not run in production. Will overide some contact info.")
    screens = list(Screen.objects.filter(user__isnull=False))
    hubspot = Hubspot()

    failed = []

    for i in trange(len(screens), desc="Contacts"):
        screen = screens[i]
        user = screen.user
        if user.external_id is None or user.external_id == "":
            continue

        try:
            hubspot.update_contact(user.external_id, hubspot.mfb_user_to_hubspot_contact(user, screen))
        except Exception as e:
            failed.append(f"failed to update user with id: {user.id} and external id: {user.external_id}")
        time.sleep(0.2)

    print("\n".join(failed))
    print("done")


def backfill_hubspot_annual_income_field() -> None:
    screens = list(Screen.objects.filter(user__isnull=False))
    hubspot = Hubspot()

    failed = []

    for i in trange(len(screens), desc="Contacts"):
        screen = screens[i]
        user = screen.user
        if user.external_id is None or user.external_id == "":
            continue

        try:
            data = {"ab01___mfb_annual_income": int(screen.calc_gross_income("yearly", ["all"]))}
            hubspot.update_contact(user.external_id, data)
        except Exception:
            failed.append(f"failed to update user with id: {user.id} and external id: {user.external_id}")
        time.sleep(0.11)

    print("\n".join(failed))
