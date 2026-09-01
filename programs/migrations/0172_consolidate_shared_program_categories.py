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

from django.db import migrations

# The 9 shared categories, keyed by external_name.
# (icon, display name, tax_category)
SHARED_CATEGORIES = {
    "cash": ("cash", "Cash Assistance", False),
    "food": ("food", "Food and Nutrition", False),
    "health_care": ("health_care", "Health Care", False),
    "housing": ("housing", "Housing and Utilities", False),
    "child_care": ("child_care", "Child Care, Youth, and Education", False),
    "tax_credit": ("tax_credit", "Tax Credits", True),
    "transportation": ("transportation", "Transportation", False),
    "employment": ("job_resources", "Employment", False),
    "savings": ("savings", "Savings", False),
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
        Translation.objects.add_translation(label=cat.name.label, default_message=text)

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

        cat.external_name = target_name
        cat.white_label = None
        cat.save()

    # Step 2: create any shared category that doesn't exist yet, and normalise the
    # icon, display name and tax_category on all of them.
    shared = {}
    for external_name, (icon_name, display_name, tax_category) in SHARED_CATEGORIES.items():
        cat = ProgramCategory.objects.filter(external_name=external_name, white_label__isnull=True).first()

        if cat is None:
            cat = ProgramCategory.objects.new_program_category(
                white_label=None, external_name=external_name, icon=icon_name
            )

        icon = CategoryIconName.objects.filter(name=icon_name).first()
        if icon is None:
            icon = CategoryIconName.objects.create(name=icon_name)

        cat.icon = icon
        cat.tax_category = tax_category
        cat.white_label = None
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
