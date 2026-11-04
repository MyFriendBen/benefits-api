from django.db import migrations

# CONFIRMED programs in vintage.py whose rule is _PRIOR_TAX_YEAR. These move to
# year_type="prior_tax_year" with year_offset=-1 and a concrete FPL FK so
# roll_program_years can advance them each January without a per-program migration.
PROGRAMS = [
    ("federal", "federal_ctc"),
    ("mo", "mo_pts"),
    ("mo", "mo_wftc"),
]


def forwards(apps, schema_editor):
    Program = apps.get_model("programs", "Program")
    FederalPoveryLimit = apps.get_model("programs", "FederalPoveryLimit")

    fpl_2025 = FederalPoveryLimit.objects.filter(year="2025", period="2025").first()
    if fpl_2025 is None:
        raise RuntimeError("No FederalPoveryLimit row for 2025 — seed _FPL_DEFAULTS first.")

    print("Moving confirmed tax credits to prior_tax_year:")
    for white_label, abbr in PROGRAMS:
        updated = Program.objects.filter(
            white_label__code=white_label,
            name_abbreviated=abbr,
        ).update(year=fpl_2025, year_type="prior_tax_year", year_offset=-1)
        status = "done" if updated else "not found, skipping"
        print(f"  {white_label}/{abbr}: {status}")


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0202_add_flip_month_and_year_offset"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
