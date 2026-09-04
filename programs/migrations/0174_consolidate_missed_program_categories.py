"""
Consolidate the per-white-label categories 0172 left behind.

0172's CONSOLIDATE list omitted five rows that exist in production, so their
programs stayed on per-white-label categories instead of moving to the shared
rows. WA kept four of its six categories: the list covered only `wa_cash`,
`wa_food` and `wa_housing`.

Nothing failed loudly because 0172 is written defensively -- CONSOLIDATE skips a
row it cannot find and DELETE_EMPTY refuses to delete a row that still has
programs -- so the migration quietly did less than intended.

`mo_health_care` is listed here as well: staging carries that spelling while
production carries `mo_healthcare`, which 0172 already handled. Whichever exists
is consolidated and the other is skipped, so this runs correctly against both.
"""

from django.db import migrations


# (white_label_code, per-white-label external_name, shared external_name)
CONSOLIDATE = [
    ("mo", "mo_food", "food"),
    # Staging-only spelling; production's `mo_healthcare` was handled by 0172.
    ("mo", "mo_health_care", "health_care"),
    ("wa", "wa_child_care", "child_care"),
    ("wa", "wa_healthcare", "health_care"),
    ("wa", "wa_tax", "tax_credit"),
    ("wa", "wa_transportation", "transportation"),
]


def forward(apps, schema_editor):
    # Real models rather than apps.get_model, matching 0172: the category
    # manager needs parler internals unavailable on historical models.
    from programs.models import Program, ProgramCategory

    shared = {
        cat.external_name: cat for cat in ProgramCategory.objects.filter(white_label__isnull=True)
    }

    for wl_code, from_name, shared_name in CONSOLIDATE:
        cat = ProgramCategory.objects.filter(
            white_label__code=wl_code, external_name=from_name
        ).first()
        if cat is None:
            continue

        target = shared.get(shared_name)
        if target is None:
            # 0172 creates every shared row this list targets. A missing one means
            # 0172 did not run or was altered, and re-pointing programs at nothing
            # would strip their category -- leave the row alone instead.
            continue

        Program.objects.filter(category=cat).update(category=target)
        _delete_category(cat)


def _delete_category(cat):
    """
    Delete a category and the Translation rows it leaves orphaned.

    Same approach as 0172's helper: name and description are PROTECTed FKs so the
    category goes first, and each translation is deleted only if nothing else
    references it. Translation is PROTECTed from ~30 models, so rather than
    enumerate them the delete is attempted inside a savepoint and the row kept if
    anything still points at it -- a ProtectedError must not poison the
    migration's transaction.
    """
    from django.db import transaction
    from django.db.models import ProtectedError

    from translations.models import Translation

    translation_ids = [cat.name_id, cat.description_id]

    cat.delete()

    for translation_id in translation_ids:
        try:
            with transaction.atomic():
                Translation.objects.filter(id=translation_id).delete()
        except ProtectedError:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0173_federal_poverty_limit_value"),
    ]

    operations = [
        # Reverse is a no-op for the same reason as 0172: consolidation is lossy.
        # The per-white-label rows and their Translation rows are gone and cannot
        # be reconstructed -- restore from a backup instead.
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
