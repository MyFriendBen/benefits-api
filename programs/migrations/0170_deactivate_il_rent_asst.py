from django.db import migrations


def deactivate_il_rent_asst(apps, schema_editor):
    """
    Deactivate the `il_rent_asst` urgent need, which the `il_cbrap` program replaces.

    Both represent CBRAP — same program, same apply URL — so leaving the urgent need active
    would show Illinois renters CBRAP twice under different eligibility logic: the urgent
    need adds a `needs_housing_help` gate the program does not have. The results path filters
    urgent needs on `active` alone, so `show_on_current_benefits` would not hide it, and
    `import_program_config` never touches `UrgentNeed` rows.

    Matched through `functions` rather than `external_name`: the function name is what binds
    the row to its calculator, and the row predates the urgent-need config importer, so it
    has no config file to match against.
    """
    UrgentNeed = apps.get_model("programs", "UrgentNeed")
    UrgentNeed.objects.filter(functions__name="il_rent_asst").update(active=False)


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0169_drop_refugee_from_mo_snap"),
    ]
    operations = [
        # noop reverse: rolling back il_cbrap should not put a second CBRAP result back in
        # front of Illinois renters. Reactivation is a deliberate act, done separately.
        migrations.RunPython(deactivate_il_rent_asst, migrations.RunPython.noop),
    ]
