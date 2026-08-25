from django.db import migrations


# Refugees and asylees are exempt from the five-year bar for SNAP, Medicaid/CHIP, TANF and SSI
# alike, so a bar-subject program that omits `refugee` understates eligibility for them.
#
# Every SNAP program except mo_snap omitted it, as did the TX cash and health programs and
# nc_medicaid. Only wa_snap's omission had a stated rationale: it read the July 2025 federal
# changes as removing refugees and asylees from SNAP entirely and routed them to state-funded FAP
# instead. This restores the exemption across the board.
ADD_REFUGEE = [
    "co_snap",
    "il_snap",
    "ks_snap",
    "ma_snap",
    "nc_snap",
    "tx_snap",
    "wa_snap",
    "tx_chip",
    "tx_ssi",
    "tx_tanf",
    "nc_medicaid",
]

# wa_snap and wa_fap must stay disjoint: WaFap subclasses Snap and resolves the same PolicyEngine
# `snap` variable, so a status on both programs double-counts one benefit in the household total.
# `refugee` moving onto wa_snap therefore requires it to come off wa_fap in the same operation.
# Pending-asylum applicants, whom FAP still serves, select `otherWithWorkPermission`.
REMOVE_REFUGEE = ["wa_fap"]


def set_refugee(apps, add, remove):
    Program = apps.get_model("programs", "Program")
    LegalStatus = apps.get_model("programs", "LegalStatus")

    refugee, _ = LegalStatus.objects.get_or_create(status="refugee")

    for names, attach in ((add, True), (remove, False)):
        for name in names:
            programs = Program.objects.filter(name_abbreviated=name)
            if not programs:
                print(f"⚠️  {name}: no such program, skipping")
                continue

            for program in programs:
                if attach:
                    program.legal_status_required.add(refugee)
                else:
                    program.legal_status_required.remove(refugee)
                sign = "+" if attach else "-"
                print(f"✅ {program.white_label.code}/{name}: {sign}refugee")


def apply_changes(apps, schema_editor):
    set_refugee(apps, ADD_REFUGEE, REMOVE_REFUGEE)


def reverse_changes(apps, schema_editor):
    set_refugee(apps, REMOVE_REFUGEE, ADD_REFUGEE)


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0168_fix_five_year_bar_legal_statuses"),
    ]

    operations = [
        migrations.RunPython(apply_changes, reverse_changes),
    ]
