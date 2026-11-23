from django.db import migrations

# Kansas has no energy-assistance tile on the has-benefits step, so no
# CurrentBenefit row for LIEAP can ever be written and `has_base_benefit("liheap")`
# is false on every Kansas screen. ks_wap admits a LIEAP household regardless of
# income — Kansas's most prominently advertised categorical route — so without
# this flag that route is unreachable.
#
# The config file carries the same value for a fresh import; this migration is
# what moves the rows that already exist. Every other white label with a LIHEAP
# program (co, il, ma, nc, mo) already has its tile.
WHITE_LABEL_CODE = "ks"
NAME_ABBREVIATED = "ks_lieap"


def forward(apps, schema_editor):
    Program = apps.get_model("programs", "Program")
    Program.objects.filter(white_label__code=WHITE_LABEL_CODE, name_abbreviated=NAME_ABBREVIATED).update(
        show_in_has_benefits_step=True
    )


def reverse(apps, schema_editor):
    Program = apps.get_model("programs", "Program")
    Program.objects.filter(white_label__code=WHITE_LABEL_CODE, name_abbreviated=NAME_ABBREVIATED).update(
        show_in_has_benefits_step=False
    )


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0174_consolidate_missed_program_categories"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
