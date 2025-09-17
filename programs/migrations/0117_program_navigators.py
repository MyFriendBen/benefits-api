# Add Program.navigators_sorted and backfill ordered values
from django.db import migrations
import sortedm2m.fields


def backfill_program_navigator_order(apps, schema_editor):
    Program = apps.get_model("programs", "Program")
    Navigator = apps.get_model("programs", "Navigator")

    # Build canonical order per white_label: order Navigators by id within WL
    wl_to_order = {}
    for wl_id in Navigator.objects.values_list("white_label_id", flat=True).distinct():
        ids = list(Navigator.objects.filter(white_label_id=wl_id).order_by("id").values_list("id", flat=True))
        wl_to_order[wl_id] = {nav_id: idx for idx, nav_id in enumerate(ids)}

    # For each Program, set navigators_sorted to the Program's existing Navigator membership,
    # ordered by the canonical WL order (stable fallback by id)
    for program in Program.objects.all().iterator():
        wl_id = program.white_label_id
        order_map = wl_to_order.get(wl_id, {})

        # Existing membership via old M2M (Navigator.programs)
        existing_ids = list(Navigator.objects.filter(programs=program).values_list("id", flat=True))
        if not existing_ids:
            continue

        # Sort by canonical WL order, then by id for stability
        existing_ids.sort(key=lambda _id: (order_map.get(_id, 10**9), _id))

        # Assign in order; SortedM2M will store sort_value accordingly
        program.navigators_sorted.set(existing_ids)


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0116_update_category_icon_names"),
    ]

    operations = [
        migrations.AddField(
            model_name="program",
            name="navigators_sorted",
            field=sortedm2m.fields.SortedManyToManyField(
                blank=True, related_name="programs_sorted", to="programs.Navigator"
            ),
        ),
        migrations.RunPython(backfill_program_navigator_order, migrations.RunPython.noop),
    ]
