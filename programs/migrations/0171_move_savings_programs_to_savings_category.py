# Moves savings/investment-account programs out of "Cash Assistance" (and, for
# CollegeInvest First Step, out of "Child Care") into a per-white-label "Savings"
# category, for MFB-1706.
#
# Why a migration and not the config importer: the program_category block in each
# config JSON only takes effect the first time a program is created.
# import_program_config skips a program that already exists, and its --reconcile
# path deliberately leaves "Program fields, category and translations" untouched.
# So editing those JSON files (done alongside this migration, to keep fresh
# environments correct) never moves a program that is already live. Re-pointing an
# existing program is a database change, and this is the reviewable way to make it
# in every environment at once instead of hand-editing each program in the admin.
#
# Why the move: these are custodial investment accounts, not spendable income.
# Trump Accounts are locked under traditional IRA rules until the child turns 18
# and carry early-withdrawal penalties; grouping them under Cash Assistance
# implies a household can spend the $1,000 alongside SNAP or TANF. It also
# distorts the category total, which the results page divides by 12 to show a
# monthly figure — a one-time $1,000 deposit was rendering as ~$83/month of
# recurring cash.
#
# Strategy:
#   1. Create the missing per-white-label Savings ProgramCategory rows, reusing
#      ProgramCategoryManager.new_program_category() so they're built the same way
#      as everywhere else, then set the English display name on the translation
#      row it creates.
#   2. Re-point each program at its white label's Savings category.
#
# CO uses unprefixed category external_names ("cash", "housing"), so its row is
# "savings"; every other white label prefixes with its code ("ma_savings").
# ma_savings already exists (BabySteps Savings Plan uses it) and is reused, not
# recreated. The "savings" CategoryIconName is created by 0121_add_savings_icon,
# so the icon exists in every environment, and the frontend already maps
# savings -> piggy-bank in ICON_NAME_MAP.
#
# Unlike 0152, this migration overwrites a non-NULL category, so it cannot use
# category__isnull=True to stay idempotent. It instead only moves a program whose
# category is still one of the known "from" values below, which keeps it re-runnable
# and means a category deliberately changed in the admin afterwards is left alone.

from django.conf import settings
from django.db import migrations

from integrations.clients.google_translate import Translate

WHITE_LABELS = ["co", "il", "ks", "ma", "mo", "nc", "tx", "wa"]

SAVINGS_DISPLAY_NAME = "Savings"
SAVINGS_ICON = "savings"

# (white_label_code, program_name_abbreviated, expected_current_category_external_name).
# The expected current category scopes the update so re-running is a no-op and an
# admin's later re-categorization is never clobbered.
PROGRAM_MOVES = [
    ("co", "trump_account", "cash"),
    ("il", "trump_account", "il_cash"),
    ("ks", "trump_account", "ks_cash"),
    ("ma", "trump_account", "ma_cash"),
    ("mo", "trump_account", "mo_cash"),
    ("nc", "trump_account", "nc_cash"),
    ("tx", "trump_account", "tx_cash"),
    ("wa", "trump_account", "wa_cash"),
    # A 529 college-savings seed deposit with a dollar-for-dollar match, filed
    # under child care. Surfaced by the audit MFB-1706 asks for.
    ("co", "co_collegeinvest_first_step", "child_care"),
]


def savings_external_name(white_label_code):
    """CO uses unprefixed category external_names; every other white label prefixes."""
    return "savings" if white_label_code == "co" else f"{white_label_code}_savings"


def forward(apps, schema_editor):
    # Use the live model managers (not apps.get_model) because
    # ProgramCategoryManager.new_program_category and
    # TranslationManager.add_translation rely on parler internals that aren't
    # available on historical models. Both managers set use_in_migrations = True,
    # so this is safe. Mirrors what 0152_backfill_has_benefits_categories does.
    # WhiteLabel lives in the screener app, not programs.
    from programs.models import Program, ProgramCategory
    from screener.models import WhiteLabel
    from translations.models import Translation

    wl_by_code = {wl.code: wl for wl in WhiteLabel.objects.all()}
    created_names = []

    # Step 1: create the Savings category for each white label that needs one.
    for code in WHITE_LABELS:
        wl = wl_by_code.get(code)
        if wl is None:
            # White label not present in this environment (e.g. a state that
            # hasn't launched yet). Nothing to do.
            continue

        external_name = savings_external_name(code)

        # external_name is globally unique on ProgramCategory, so check it
        # unscoped — a filter on (white_label, external_name) would miss a
        # colliding row and then fail on create.
        if ProgramCategory.objects.filter(external_name=external_name).exists():
            continue

        category = ProgramCategory.objects.new_program_category(
            white_label=code,
            external_name=external_name,
            icon=SAVINGS_ICON,
        )

        # new_program_category creates the name/description translation rows with a
        # blank placeholder for English. Set the real display name. Description is
        # left blank: the results page renders a category description only when it's
        # non-empty, and there's no product-approved copy for it.
        Translation.objects.add_translation(
            label=category.name.label,
            default_message=SAVINGS_DISPLAY_NAME,
        )
        created_names.append(category.name)

    # add_translation only fills in English and leaves the other languages blank,
    # which would render an empty category heading for non-English users. Machine
    # translate the name the same way import_program_config does, and mark the
    # results unedited so a human translation still overrides them later.
    # Done in one bulk call for every category created above, since the display
    # name is identical.
    if created_names:
        translated = Translate().bulk_translate(Translate.languages, [SAVINGS_DISPLAY_NAME])[SAVINGS_DISPLAY_NAME]
        for name_translation in created_names:
            for lang in Translate.languages:
                if lang == settings.LANGUAGE_CODE:
                    continue
                Translation.objects.edit_translation_by_id(
                    name_translation.id,
                    lang,
                    translated[lang],
                    manual=False,
                )

    # Step 2: re-point the programs.
    category_by_wl_name = {(pc.white_label_id, pc.external_name): pc for pc in ProgramCategory.objects.all()}

    for code, program_name, from_external_name in PROGRAM_MOVES:
        wl = wl_by_code.get(code)
        if wl is None:
            continue

        target = category_by_wl_name.get((wl.id, savings_external_name(code)))
        origin = category_by_wl_name.get((wl.id, from_external_name))
        if target is None or origin is None:
            # Defensive: don't crash a deploy on hand-edited environment state.
            continue

        Program.objects.filter(
            white_label=wl,
            name_abbreviated=program_name,
            category=origin,
        ).update(category=target)


def reverse(apps, schema_editor):
    # Undo only what this migration did:
    #   1. Move each program back, matching on the Savings category we set so a
    #      program re-categorized elsewhere in the meantime is left alone.
    #   2. Delete the Savings categories that are empty afterwards. A pre-existing
    #      row (ma_savings, which BabySteps uses) still has its own programs and so
    #      won't match the emptiness check.
    # Real models rather than apps.get_model, to match forward(). Note WhiteLabel
    # lives in the screener app, not programs — apps.get_model("programs",
    # "WhiteLabel") raises LookupError.
    from programs.models import Program, ProgramCategory
    from screener.models import WhiteLabel

    wl_by_code = {wl.code: wl for wl in WhiteLabel.objects.all()}
    category_by_wl_name = {(pc.white_label_id, pc.external_name): pc for pc in ProgramCategory.objects.all()}

    for code, program_name, from_external_name in PROGRAM_MOVES:
        wl = wl_by_code.get(code)
        if wl is None:
            continue

        target = category_by_wl_name.get((wl.id, savings_external_name(code)))
        origin = category_by_wl_name.get((wl.id, from_external_name))
        if target is None or origin is None:
            continue

        Program.objects.filter(
            white_label=wl,
            name_abbreviated=program_name,
            category=target,
        ).update(category=origin)

    for code in WHITE_LABELS:
        wl = wl_by_code.get(code)
        if wl is None:
            continue
        ProgramCategory.objects.filter(
            white_label=wl,
            external_name=savings_external_name(code),
            programs__isnull=True,
        ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0170_deactivate_il_rent_asst"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
