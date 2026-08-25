from django.db import migrations


# mo_snap is the only SNAP program that lists `refugee`. Federal SNAP eligibility is limited to
# citizens, lawful permanent residents, Cuban and Haitian entrants, and COFA citizens; refugee and
# asylee status is none of those, so the program claims a population it cannot serve. Every other
# SNAP program already omits it, and Washington covers this group through state-funded FAP rather
# than through Basic Food — a state would not fund that if federal SNAP already reached them.
#
# This is the one change in this series that is not about the five-year bar. It is here because it
# is the same defect the bar corrections address: a program telling someone they qualify for a
# benefit their immigration status excludes them from.
#
# Not to be confused with the bar's exemption for people who *adjusted to LPR* from refugee or
# asylee status. Those people hold a green card now, so they select a green-card option, and
# expressing their exemption needs a filter the screener does not yet have.
PROGRAM = "mo_snap"
STATUS = "refugee"


def drop_refugee(apps, schema_editor):
    Program = apps.get_model("programs", "Program")
    LegalStatus = apps.get_model("programs", "LegalStatus")

    for program in Program.objects.filter(name_abbreviated=PROGRAM):
        program.legal_status_required.remove(*LegalStatus.objects.filter(status=STATUS))
        print(f"✅ {program.white_label.code}/{PROGRAM}: -{STATUS}")


def restore_refugee(apps, schema_editor):
    Program = apps.get_model("programs", "Program")
    LegalStatus = apps.get_model("programs", "LegalStatus")

    # `.get()` rather than get_or_create: `status` has no unique constraint, so creating on a miss
    # would insert a row no frontend filter matches while the migration still reported success.
    status = LegalStatus.objects.get(status=STATUS)
    for program in Program.objects.filter(name_abbreviated=PROGRAM):
        program.legal_status_required.add(status)
        print(f"⏪ {program.white_label.code}/{PROGRAM}: +{STATUS}")


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0168_fix_five_year_bar_legal_statuses"),
    ]

    operations = [
        migrations.RunPython(drop_refugee, restore_refugee),
    ]
