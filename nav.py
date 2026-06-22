import re

from django.conf import settings
from django.db import transaction
from programs.models import Navigator, Program, ProgramNavigator, NavigatorLanguage
from screener.models import County
from translations.models import Translation


def write_navs(counties: list[str], phone: str, url: str, name: str) -> None:
    WL = "il"

    # Snakecase the agency name for the external_name: lowercase, collapse any run
    # of non-alphanumeric chars (spaces, commas, periods) to "_", then trim stray "_".
    # e.g. "BCMW Community Services, Inc." -> "il_bcmw_community_services_inc"
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    EXTERNAL_NAME = f"il_{slug}"

    # Idempotency guard: skip if this navigator already exists, so re-runs (and
    # re-runs across environments) don't create duplicates.
    if Navigator.objects.filter(external_name=EXTERNAL_NAME).exists():
        print("skip (exists)", EXTERNAL_NAME)
        return

    # No telephone parsed -> store nothing rather than an invalid empty value.
    phone = (phone or "").strip() or None

    description = (
        f"{name} can help you with energy bills, rent, food, job training, and "
        "finding a place to stay. If they can't help you directly, they'll "
        "connect you with someone who can."
    )

    with transaction.atomic():
        # Resolve every county up front so a bad/unmatched name fails before we
        # create the navigator or any translation rows.
        county_objs = [County.objects.get(name__iexact=c.strip(), white_label__code=WL) for c in counties]

        nav = Navigator.objects.new_navigator(WL, EXTERNAL_NAME, phone)
        en = settings.LANGUAGE_CODE
        Translation.objects.edit_translation_by_id(nav.name_id, en, name)
        Translation.objects.edit_translation_by_id(nav.assistance_link_id, en, url)
        Translation.objects.edit_translation_by_id(nav.description_id, en, description)
        Translation.objects.edit_translation_by_id(nav.email_id, en, "")

        nav.languages.set([NavigatorLanguage.objects.get_or_create(code="en-us")[0]])
        nav.counties.set(county_objs)

        liheap = Program.objects.get(external_name="il_liheap", white_label__code=WL)
        ProgramNavigator.objects.update_or_create(program=liheap, navigator=nav, defaults={"order": 0})

        nav.save()
        print("created", nav.id, nav.external_name, "->", [c.name for c in county_objs])
