# Deletes the standalone "Education" program categories for KS and WA
# (ks_education / wa_education) after their programs have been reassigned to the
# shared childcare category ("Child Care, Youth, and Education") via the admin.
#
# Defensive: Program.category is on_delete=SET_NULL, so deleting a category that
# still has programs would silently leave those programs uncategorized. This
# migration therefore REFUSES to delete a category that still has programs
# pointing at it — it raises, failing the release, so an operator can finish the
# admin reassignment first and redeploy. It does NOT reassign programs itself
# (that is done manually in each environment's admin).
#
# Also deletes each category's now-orphaned name/description Translation rows.
#
# Idempotent: silently skips a category that is already gone (e.g. deleted in a
# prior environment/run) and skips white labels not present in the environment.
#
# Not reversible — deleted ProgramCategory / Translation rows cannot be safely
# recreated automatically. Restore from a DB snapshot if a rollback is needed.

from django.db import migrations

# (white_label code, education category external_name)
TARGETS = [
    ("ks", "ks_education"),
    ("wa", "wa_education"),
]


def delete_education_categories(apps, schema_editor):
    ProgramCategory = apps.get_model("programs", "ProgramCategory")
    Program = apps.get_model("programs", "Program")
    Translation = apps.get_model("translations", "Translation")
    WhiteLabel = apps.get_model("screener", "WhiteLabel")

    for wl_code, external_name in TARGETS:
        try:
            wl = WhiteLabel.objects.get(code=wl_code)
        except WhiteLabel.DoesNotExist:
            continue  # tenant not present (e.g. test environments)

        category = ProgramCategory.objects.filter(white_label=wl, external_name=external_name).first()
        if category is None:
            continue  # already deleted — idempotent no-op

        linked = sorted(Program.objects.filter(category=category).values_list("name_abbreviated", flat=True))
        if linked:
            raise RuntimeError(
                f"Refusing to delete program category '{external_name}' ({wl_code}): "
                f"{len(linked)} program(s) still reference it: {', '.join(linked)}. "
                f"Program.category is SET_NULL, so deleting now would leave them uncategorized. "
                f"Reassign them to '{wl_code}_child_care' in the admin, then redeploy to re-run this migration."
            )

        # Capture the translation FKs before deleting the category (they are
        # PROTECT-referenced by the category, so they must be deleted after it).
        translation_ids = [tid for tid in (category.name_id, category.description_id) if tid]
        category.delete()
        Translation.objects.filter(id__in=translation_ids).delete()


def reverse(apps, schema_editor):
    raise NotImplementedError(
        "Irreversible: deleted ProgramCategory and Translation rows. Restore from a DB snapshot if needed."
    )


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0162_alter_program_base_program"),
    ]

    operations = [
        migrations.RunPython(delete_education_categories, reverse),
    ]
