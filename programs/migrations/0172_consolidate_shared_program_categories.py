# Consolidates ProgramCategory onto shared rows for MFB-1601.
#
# Every white label had its own row for the same semantic category — 64 rows
# across 10 white labels, 8 of them "Cash Assistance". Nothing kept them
# consistent and they had drifted: health_care was spelled "Health Care" /
# "Healthcare" / "Health Coverage", and child_care was "Child Care" in TX and KS
# but "Child Care, Youth, and Education" elsewhere.
#
# After this migration each semantic category is one row with white_label = NULL,
# shared by programs in every white label, so drift is impossible rather than
# merely discouraged. Categories that genuinely belong to a single white label
# (CESN's own four, the CO tax calculator) keep their white_label set.
#
# CO already held the unprefixed names, so its 7 rows are promoted to shared by
# nulling white_label. That preserves their ids and Translation labels instead of
# creating new rows and re-pointing every CO program.
#
# Also folds in MFB-1706: trump_account moves from cash to savings in all 8 white
# labels, and co_collegeinvest_first_step (a 529 seed deposit) moves from
# child_care to savings. Trump Accounts is a custodial investment account locked
# under IRA rules until the child turns 18; because the results page divides a
# category total by 12 to show a monthly figure, the one-time $1,000 was
# rendering as ~$83/month of recurring cash inside Cash Assistance.
#
# Verified safe alongside this change:
#   * Cap calculators key off program names, not categories
#     (programs/categories/co/caps.py), and all 7 capped programs are CO-only.
#     The cap logic skips programs absent from a screen's eligibility, so CO's
#     caps are a no-op on a shared row for other states.
#   * No frontend code reads a category external_name; categories render from
#     icon + translated name.

from django.conf import settings
from django.db import migrations

from integrations.clients.google_translate import Translate, is_auto_translatable

# The 10 shared categories, keyed by external_name.
# (icon, display name, tax_category, priority)
#
# priority is set explicitly, not inherited from the promoted row. It is
# serialized to the frontend, which sorts categories by it ahead of value
# (Programs.tsx) — so a value carried over from CO would silently reorder the
# results page for every white label. null means "no override", i.e. sort by
# total value, which is the behaviour every white label has today.
SHARED_CATEGORIES = {
    "cash": ("cash", "Cash Assistance", False, None),
    "food": ("food", "Food and Nutrition", False, None),
    "health_care": ("health_care", "Health Care", False, None),
    "housing": ("housing", "Housing and Utilities", False, None),
    "child_care": ("child_care", "Child Care and Youth", False, None),
    "tax_credit": ("tax_credit", "Tax Credits", True, None),
    "transportation": ("transportation", "Transportation", False, None),
    "employment": ("job_resources", "Employment", False, None),
    "savings": ("savings", "Savings", False, None),
    # Post-secondary and adult education: scholarships, tuition aid and
    # workforce training. Distinct from child_care, which covers early
    # childhood and K-12 programs.
    "education": ("education", "Education and Training", False, None),
}

# CO holds the unprefixed names already; promote these rows to shared rather than
# creating duplicates. MA supplies employment and savings.
PROMOTE_TO_SHARED = [
    ("co", "cash"),
    ("co", "food"),
    ("co", "health_care"),
    ("co", "housing"),
    ("co", "child_care"),
    ("co", "tax_credit"),
    ("co", "transportation"),
    ("ma", "ma_employment", "employment"),
    ("ma", "ma_savings", "savings"),
]

# (white_label_code, from_external_name, shared_external_name).
# Programs move to the shared row and the old row is deleted.
CONSOLIDATE = [
    ("il", "il_cash", "cash"),
    ("il", "il_child_care", "child_care"),
    ("il", "il_food", "food"),
    ("il", "il_health", "health_care"),
    ("il", "il_housing", "housing"),
    ("il", "il_tax_credit", "tax_credit"),
    ("il", "il_transportation", "transportation"),
    ("ks", "ks_cash", "cash"),
    ("ks", "ks_child_care", "child_care"),
    ("ks", "ks_food", "food"),
    ("ks", "ks_health_care", "health_care"),
    ("ks", "ks_healthcare", "health_care"),
    ("ks", "ks_housing", "housing"),
    ("ks", "ks_tax", "tax_credit"),
    ("ks", "ks_tax_credit", "tax_credit"),
    ("ma", "ma_cash", "cash"),
    ("ma", "ma_child_care", "child_care"),
    # Listed here as well as in PROMOTE_TO_SHARED: promotion renames the row in
    # place, but is skipped if the target name is already taken (e.g. a re-run
    # after partial failure). These entries make sure the programs consolidate
    # either way.
    ("ma", "ma_employment", "employment"),
    ("ma", "ma_savings", "savings"),
    ("ma", "ma_food", "food"),
    ("ma", "ma_health_care", "health_care"),
    ("ma", "ma_housing", "housing"),
    ("ma", "ma_tax_credit", "tax_credit"),
    ("ma", "ma_transportation", "transportation"),
    ("mo", "mo_cash", "cash"),
    ("mo", "mo_child_care", "child_care"),
    ("mo", "mo_healthcare", "health_care"),
    ("mo", "mo_housing", "housing"),
    ("mo", "mo_tax", "tax_credit"),
    ("nc", "nc_cash", "cash"),
    ("nc", "nc_childcare", "child_care"),
    ("nc", "nc_food", "food"),
    # A category named after a single program; its Head Start row belongs in child care.
    ("nc", "nc_head_start", "child_care"),
    ("nc", "nc_healthcare", "health_care"),
    ("nc", "nc_housing", "housing"),
    ("nc", "taxCredits", "tax_credit"),
    ("tx", "tx_cash", "cash"),
    ("tx", "tx_child_care", "child_care"),
    ("tx", "tx_food", "food"),
    ("tx", "tx_healthcare", "health_care"),
    ("tx", "tx_housing", "housing"),
    ("tx", "tx_tax_credits", "tax_credit"),
    ("tx", "tx_transportation", "transportation"),
    ("wa", "wa_cash", "cash"),
    ("wa", "wa_food", "food"),
    ("wa", "wa_housing", "housing"),
    # CESN keeps its four CESN-specific categories but shares the generic ones.
    ("cesn", "cesn_cash", "cash"),
    ("cesn", "cesn_food", "food"),
]

# Rows with zero programs. Deleted outright.
DELETE_EMPTY = [
    ("co", "co_cash"),
    ("il", "il_health_care"),
    ("tx", "tx_health"),
    ("nc", "nc taxCredits"),
    ("cesn", "cesn_housing"),
    ("cesn", "cesn_transportation"),
]

# MFB-1706: (white_label_code, program_name_abbreviated, target shared category).
MOVE_PROGRAMS = [
    *[(wl, "trump_account", "savings") for wl in ("co", "il", "ks", "ma", "mo", "nc", "tx", "wa")],
    ("co", "co_collegeinvest_first_step", "savings"),
    # Post-secondary education and training, previously filed under child care
    # because no education category existed. All four are scholarships or
    # tuition aid for adult learners, not child care.
    ("wa", "wa_wsos_bas", "education"),  # STEM/health care undergraduate scholarship
    ("wa", "wa_wsos_cts", "education"),  # associate degree, certificate, apprenticeship
    ("wa", "wa_wsos_grd", "education"),  # nurse practitioner graduate scholarship
    ("ks", "ks_promise_act", "education"),  # community/technical college tuition, fees, books
]


def forward(apps, schema_editor):
    # Real models rather than apps.get_model: new_program_category and
    # add_translation need parler internals unavailable on historical models.
    # Both managers set use_in_migrations = True. WhiteLabel lives in screener.
    from programs.models import CategoryIconName, Program, ProgramCategory
    from translations.models import Translation

    def category(white_label_code, external_name):
        return ProgramCategory.objects.filter(
            white_label__code=white_label_code, external_name=external_name
        ).first()

    def set_name(cat, text):
        """
        Set the English display name and machine-translate the rest.

        Only touches a category whose English text actually differs. Rewriting a
        name in place would replace every other language with machine output:
        add_translation always marks English edited, and edit_translation_by_id's
        manual=False guard only spares a row that is both no_auto and edited,
        which categories are not. For the five categories whose text is
        unchanged that would discard curated copy for nothing.
        """
        cat.name.set_current_language(settings.LANGUAGE_CODE)
        if (cat.name.text or "").strip() == text:
            return

        translation = Translation.objects.add_translation(label=cat.name.label, default_message=text)

        if not is_auto_translatable(text):
            return

        try:
            translated = Translate().bulk_translate(Translate.languages, [text], strict=False).get(text, {})
        except Exception:
            # A translation outage must not fail the migration; English is
            # already saved and the rest can be filled in from the admin.
            return

        for lang, translated_text in translated.items():
            if lang == settings.LANGUAGE_CODE:
                continue
            Translation.objects.edit_translation_by_id(translation.id, lang, translated_text, manual=False)

    # Step 1: promote existing rows to shared, renaming where needed.
    for entry in PROMOTE_TO_SHARED:
        if len(entry) == 2:
            wl_code, external_name = entry
            target_name = external_name
        else:
            wl_code, external_name, target_name = entry

        cat = category(wl_code, external_name)
        if cat is None:
            continue

        # A row already holding the target name means a previous run promoted it,
        # or the name is in use elsewhere. Renaming into it would violate the
        # unique constraint, so leave this row for step 3 to consolidate.
        if target_name != external_name and ProgramCategory.objects.filter(external_name=target_name).exists():
            continue

        cat.external_name = target_name
        cat.white_label = None
        cat.save()

    # Step 2: create any shared category that doesn't exist yet, and normalise the
    # icon, display name and tax_category on all of them.
    shared = {}
    for external_name, (icon_name, display_name, tax_category, priority) in SHARED_CATEGORIES.items():
        # Look the row up by external_name alone, not scoped to white_label__isnull.
        # external_name is globally unique, so a row that already carries this name
        # while still scoped to a white label must be adopted and promoted — trying
        # to create a second one violates the unique constraint. This is what makes
        # the migration re-runnable after a partial failure.
        cat = ProgramCategory.objects.filter(external_name=external_name).first()

        if cat is None:
            cat = ProgramCategory.objects.new_program_category(
                white_label=None, external_name=external_name, icon=icon_name
            )

        icon = CategoryIconName.objects.filter(name=icon_name).first()
        if icon is None:
            icon = CategoryIconName.objects.create(name=icon_name)

        cat.icon = icon
        cat.tax_category = tax_category
        cat.priority = priority
        cat.white_label = None
        # calculator is carried over from the promoted row rather than reset.
        # child_care and health_care inherit CO's cap calculators (co_preschool,
        # co_health_care), which CO's active programs still depend on. They list
        # CO-only program names and the cap logic drops any program missing from
        # a screen's eligibility, so on another state's screen they produce an
        # empty cap.
        cat.save()

        # One shared row carries one name. This applies the canonical spelling,
        # which changes user-visible copy where a state had drifted (TX
        # "Healthcare", TX "Child Care", IL "Health Coverage").
        set_name(cat, display_name)

        shared[external_name] = cat

    # Step 3: move programs off the per-white-label rows, then delete them.
    for wl_code, from_name, shared_name in CONSOLIDATE:
        cat = category(wl_code, from_name)
        if cat is None:
            continue

        target = shared[shared_name]
        Program.objects.filter(category=cat).update(category=target)
        _delete_category(cat)

    # Step 4: delete the empty rows. Guarded on actually being empty so a row
    # that gained a program since the audit is left alone rather than silently
    # orphaning it.
    for wl_code, external_name in DELETE_EMPTY:
        cat = category(wl_code, external_name)
        if cat is None:
            continue
        if Program.objects.filter(category=cat).exists():
            continue
        _delete_category(cat)

    # Step 5: MFB-1706 — move the savings/investment-account programs.
    for wl_code, program_name, shared_name in MOVE_PROGRAMS:
        Program.objects.filter(white_label__code=wl_code, name_abbreviated=program_name).update(
            category=shared[shared_name]
        )


def _delete_category(cat):
    """
    Delete a category and the Translation rows it leaves orphaned.

    name and description are PROTECTed FKs, so the category has to go first.
    Afterwards each translation is deleted only if nothing else references it —
    two categories can point at the same Translation row (NC's `taxCredits` and
    `nc taxCredits` do), and deleting a still-referenced row raises
    ProtectedError and would take the whole migration down.
    """
    from django.db import transaction
    from django.db.models import ProtectedError

    from translations.models import Translation

    translation_ids = [cat.name_id, cat.description_id]

    cat.delete()

    for translation_id in translation_ids:
        # Translation is referenced by PROTECT from ~30 models, so rather than
        # enumerate them let the database decide: try the delete and keep the row
        # if anything still points at it. The savepoint keeps a ProtectedError
        # from poisoning the migration's transaction.
        try:
            with transaction.atomic():
                Translation.objects.filter(id=translation_id).delete()
        except ProtectedError:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0171_alter_programcategory_white_label"),
    ]

    operations = [
        # Reverse is a no-op rather than an inverse: consolidation is lossy.
        # Many rows collapse into one and their Translation rows are deleted, so
        # the per-white-label names, ids and any admin edits they carried cannot
        # be reconstructed — restore from a backup instead. A no-op (not a
        # raise) keeps the schema migration below it rollback-able.
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
