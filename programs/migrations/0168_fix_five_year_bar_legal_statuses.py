from django.db import migrations


# The five-year bar applies to lawful permanent residents. `gc_5less` on a bar-subject program
# claims the whole under-five population, which is wrong for every program below: the exemptions
# are either age-based (SNAP exempts LPRs under 18) or not derivable from what the screener
# collects at all (TANF: veteran, COFA, foreign-born Native American, prior exempt status).
#
# Each entry is (name_abbreviated, statuses to add, statuses to remove). Config JSON files carry
# the same lists, but the importer applies `legal_status_required` with `.add()` and skips programs
# that already exist, so it cannot narrow a live program. This migration is what lands the change.
CHANGES = [
    # wa_snap was narrowed in the config file only. No migration ever carried it, and the
    # importer cannot narrow a live program, so the change reached staging by an out-of-band admin
    # edit and did not replicate. Re-stating it here converges every environment, including the one
    # the bug was reported against. `otherWithWorkPermission` moves to wa_fap for the same reason
    # `refugee` does in 0169: the two programs resolve the same PolicyEngine `snap` variable, so a
    # status on both double-counts one benefit.
    ("wa_snap", ["gc_under18_no5"], ["gc_5less", "otherWithWorkPermission"]),
    # Full-scope Medicaid is barred for LPRs under five years. Children are already served by
    # wa_apple_health_for_kids, which covers every status. Adults have no WA program to fall back
    # to yet — Alien Emergency Medical is not modeled.
    ("wa_apple_health_medicaid", [], ["gc_5less"]),
    # TANF's exemptions are prior exempt status, veteran/active-duty, COFA citizen and certain
    # foreign-born Native Americans. None is derivable, and none is age-based.
    ("wa_tanf", [], ["gc_5less"]),
    ("ks_tanf", [], ["gc_5less"]),
    ("mo_tanf", [], ["gc_5less"]),
    # SNAP exempts LPRs under 18 regardless of the status they adjusted from (8 USC 1613(c)).
    # Neither state has a state-funded analogue of WA's FAP, so barred adults get nothing.
    ("ks_snap", ["gc_under18_no5"], ["gc_5less"]),
    ("tx_snap", ["gc_under18_no5"], []),
    ("nc_snap", ["gc_under18_no5"], []),
    # NC adopted the ICHIA option and folded CHIP into Medicaid, so lawfully residing children up
    # to 21 and pregnant people are covered without the bar.
    ("nc_medicaid", ["otherHealthCarePregnant", "otherHealthCareUnder21"], []),
]


def apply_changes(apps, schema_editor, reverse=False):
    Program = apps.get_model("programs", "Program")
    LegalStatus = apps.get_model("programs", "LegalStatus")

    for name, to_add, to_remove in CHANGES:
        if reverse:
            to_add, to_remove = to_remove, to_add

        programs = Program.objects.filter(name_abbreviated=name)
        if not programs:
            print(f"⚠️  {name}: no such program, skipping")
            continue

        for program in programs:
            for status in to_add:
                program.legal_status_required.add(LegalStatus.objects.get_or_create(status=status)[0])
            for status in to_remove:
                program.legal_status_required.remove(*LegalStatus.objects.filter(status=status))

            code = program.white_label.code
            changed = ", ".join(
                [f"+{s}" for s in to_add] + [f"-{s}" for s in to_remove],
            )
            print(f"✅ {code}/{name}: {changed}")


def reverse_changes(apps, schema_editor):
    apply_changes(apps, schema_editor, reverse=True)


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0167_add_nc_homeless_and_health_care_categories"),
    ]

    operations = [
        migrations.RunPython(apply_changes, reverse_changes),
    ]
