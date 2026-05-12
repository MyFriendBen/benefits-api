# Backfills Program.category for every program flagged for the has-benefits
# step that's currently NULL. Lets the AlreadyHasBenefits screener step group
# tiles by category instead of dropping them into the synthetic "Other" bucket.
#
# Strategy:
#   1. Create the missing WL-scoped ProgramCategory rows CESN needs
#      (cesn_cash / cesn_food / cesn_transportation / cesn_housing). Reuses
#      the existing ProgramCategoryManager.new_program_category() helper so
#      new categories are created the same way the rest of the codebase does.
#   2. Set the English text on each new category's translations
#      (new_program_category creates blank translation rows).
#   3. Link existing has-benefits-step programs to categories — only where
#      category_id IS NULL, so this migration is idempotent and never
#      clobbers an admin-set category.
#
# Scope notes (post-audit, MFB-1001):
#   * The CESN tiles linked here are scheduled to be flipped off the step
#     once MFB-871 ships. Their category links remain harmless after that.
#   * co_care is intentionally NOT linked — it's a dead tracking-only
#     Program row scheduled for deletion. We also don't create a
#     co_efficiency_upgrades category since nothing in CO would use it.

from django.db import migrations


# New (WL_code, external_name, display_name) tuples. We create these only if
# they don't already exist. Display name matches the other WLs' phrasing for
# consistency across the platform.
# NOTE on scope: post-audit (MFB-1001), most CESN tiles in PROGRAM_CATEGORY_LINKS
# below will be flipped OFF the has-benefits step once MFB-871 (results-page
# "already have this" toggle) ships. The categories we create here will then
# have zero visible programs and can be cleaned up. We still create them now
# so the new tile UI from MFB-862 renders grouped (not "Other") during the
# transition window. The co_efficiency_upgrades category is intentionally NOT
# created — its only intended link (co_care) is a dead Program row scheduled
# for deletion (see MFB-1001 follow-up).
NEW_CATEGORIES = [
    ("cesn", "cesn_cash", "Cash Assistance"),
    ("cesn", "cesn_food", "Food and Nutrition"),
    ("cesn", "cesn_transportation", "Transportation"),
    ("cesn", "cesn_housing", "Housing and Utilities"),
]


# (WL_code, program_name_abbreviated, target_category_external_name).
# Only the programs flagged for the has-benefits step that currently have
# category=NULL in prod (audited 2026-05-12).
PROGRAM_CATEGORY_LINKS = [
    # CESN — all linked to the new cesn_* categories created above
    ("cesn", "cesn_oap", "cesn_cash"),
    ("cesn", "cesn_ssdi", "cesn_cash"),
    ("cesn", "cesn_ssi", "cesn_cash"),
    ("cesn", "cesn_tanf", "cesn_cash"),
    ("cesn", "cesn_andso", "cesn_cash"),
    ("cesn", "cesn_snap", "cesn_food"),
    ("cesn", "cesn_wic", "cesn_food"),
    ("cesn", "cesn_care", "cesn_efficiency_upgrades"),  # category already existed
    # CO — link to existing categories. Note: co_care intentionally absent —
    # it's a dead tracking-only Program row scheduled for deletion (see
    # MFB-1001 follow-up). Linking it here would create work to undo later.
    ("co", "co_andso", "cash"),
    ("co", "co_section_8", "housing"),
    # MA — link to existing category
    ("ma", "ma_section_8", "ma_housing"),
    # NC — link to existing categories. Note: NC has two near-duplicate
    # 'Cash Assistance' categories ('nc cash' and 'nc_cash'). NC's existing
    # cash programs (SSI/SSDI/TANF) point at 'nc cash' (with space), so we
    # don't need that one here. Cleanup of the dupe tracked in MFB-997.
    ("nc", "nc_cccap", "nc childcare"),
    ("nc", "nc_leap", "nc_housing"),
]


def forward(apps, schema_editor):
    # Use the live model managers (not apps.get_model) because the
    # ProgramCategoryManager.new_program_category and
    # TranslationManager.add_translation helpers rely on parler internals
    # that aren't available on historical models. Both managers set
    # use_in_migrations = True, so this is safe.
    from programs.models import Program, ProgramCategory, WhiteLabel
    from translations.models import Translation

    # Step 1: create missing categories.
    for wl_code, external_name, display_name in NEW_CATEGORIES:
        if ProgramCategory.objects.filter(external_name=external_name).exists():
            continue

        category = ProgramCategory.objects.new_program_category(
            white_label=wl_code,
            external_name=external_name,
            icon=None,
        )

        # new_program_category creates placeholder translations with a
        # BLANK_TRANSLATION_PLACEHOLDER as the English text. Overwrite the
        # name with the actual display text. Leave description blank —
        # description isn't surfaced on the has-benefits step and we don't
        # have product-approved copy for it; admin can fill in later.
        Translation.objects.add_translation(
            label=category.name.label,
            default_message=display_name,
        )

    # Step 2: link programs to categories, but only where currently NULL,
    # so this migration can re-run safely and won't clobber admin edits
    # made between deploy and migrate.
    category_by_name = {pc.external_name: pc for pc in ProgramCategory.objects.all()}
    wl_by_code = {wl.code: wl for wl in WhiteLabel.objects.all()}

    for wl_code, program_name, category_external_name in PROGRAM_CATEGORY_LINKS:
        wl = wl_by_code.get(wl_code)
        category = category_by_name.get(category_external_name)
        if wl is None or category is None:
            # Defensive: should never happen given the lists above, but
            # don't crash a deploy if someone hand-edits prod state.
            continue

        Program.objects.filter(
            white_label=wl,
            name_abbreviated=program_name,
            category__isnull=True,
        ).update(category=category)


def reverse(apps, schema_editor):
    # Only reverse what *this* migration set: clear category for the linked
    # programs (matching on both WL and name_abbreviated to avoid touching
    # unrelated programs), and delete the categories we created.
    Program = apps.get_model("programs", "Program")
    ProgramCategory = apps.get_model("programs", "ProgramCategory")
    WhiteLabel = apps.get_model("programs", "WhiteLabel")

    wl_by_code = {wl.code: wl for wl in WhiteLabel.objects.all()}
    new_category_names = {ext for _, ext, _ in NEW_CATEGORIES}
    category_by_name = {
        pc.external_name: pc
        for pc in ProgramCategory.objects.filter(external_name__in={c[2] for c in PROGRAM_CATEGORY_LINKS})
    }

    for wl_code, program_name, category_external_name in PROGRAM_CATEGORY_LINKS:
        wl = wl_by_code.get(wl_code)
        category = category_by_name.get(category_external_name)
        if wl is None or category is None:
            continue
        Program.objects.filter(
            white_label=wl,
            name_abbreviated=program_name,
            category=category,
        ).update(category=None)

    ProgramCategory.objects.filter(external_name__in=new_category_names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0150_backfill_program_value_type"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
