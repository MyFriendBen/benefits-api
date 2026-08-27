from django.db import migrations


# The five-year bar applies to lawful permanent residents. `gc_5less` on a bar-subject program
# claims the whole under-five population, which is wrong for every program below: the exemptions
# are either age-based (SNAP exempts LPRs under 18) or not derivable from what the screener
# collects at all (TANF: veteran, COFA, foreign-born Native American, prior exempt status).
#
# Each entry is (name_abbreviated, statuses to add, statuses to remove). Config JSON files carry
# the same lists, but the importer applies `legal_status_required` with `.add()` and skips programs
# that already exist, so it cannot narrow a live program. This migration is what lands the change.
#
# Not every config edited alongside this migration needs an entry here. `il_mpe` and
# `tx_medicaid_for_pregnant_women` dropped `other` and `gc_under5`, labels with no LegalStatus row,
# so they were never applied to a program and there is nothing in the database to correct.
# `mo_snap` is handled by 0169, and `wa_fap` needs nothing: it was created by its config
# import, so the database already matches the config.
#
# `gc_5less` is in a removal list even for programs whose config never declared it. 0127 added
# `gc_5less` to *every* program that held the legacy `green_card` label, so a live row can carry it
# without any config saying so, and a program left un-narrowed keeps showing to barred LPR adults —
# the reported bug. `.remove()` on an absent status is a no-op, so the extra entry costs nothing.
CHANGES = [
    # wa_snap was narrowed in the config file only. No migration ever carried it, and the
    # importer cannot narrow a live program, so the change reached staging by an out-of-band admin
    # edit and did not replicate. Re-stating it here converges every environment, including the one
    # the bug was reported against. `otherWithWorkPermission` comes off because wa_fap already
    # declares it: the two programs resolve the same PolicyEngine `snap` variable, so a status on
    # both double-counts one benefit.
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
    ("tx_snap", ["gc_under18_no5"], ["gc_5less"]),
    ("nc_snap", ["gc_under18_no5"], ["gc_5less"]),
    # NC adopted the ICHIA option and folded CHIP into Medicaid, so lawfully residing children up
    # to 21 are covered without the bar. `otherHealthCareUnder21` is linked only to `gc_5less` and
    # `otherWithWorkPermission`, both lawfully present, so it cannot widen the program beyond them.
    #
    # ICHIA covers pregnant people too, but `otherHealthCarePregnant` is not the label for it here:
    # it is also linked to `non_citizen`, so it would make full-scope nc_medicaid visible to
    # undocumented households with a pregnant member — the same overstatement this migration exists
    # to remove — and nc_emergency_medicaid gates on `program_eligible("nc_medicaid")` with no
    # `excludes_programs` on either side, so both cards would render and Medicaid would land twice
    # in the household total. CO scopes its emergency program to
    # `notPregnantOrUnder19ForEmergencyMedicaid` and so avoids this; NC's is bare `non_citizen`.
    # Covering pregnancy needs a label that excludes `non_citizen`, which is a frontend change.
    ("nc_medicaid", ["otherHealthCareUnder21"], ["gc_5less"]),
]

# The labels this migration is allowed to create. Both are calculated labels, and no migration has
# ever created either one: 0129 seeded only the six user-selected statuses, and the config importer
# resolves labels with `.get()` and merely warns on a miss. Where they exist they were added by
# hand, so on an environment built from migrations alone a bare `.get()` below would raise inside
# `RunPython`, failing the deploy's `migrate` step and rolling back every pending migration — not
# just this one.
SEEDABLE = {"gc_under18_no5", "otherHealthCareUnder21"}


def get_status(LegalStatus, status):
    """
    Look up a label, creating one only where this migration expects to.

    `LegalStatus.status` has no unique constraint, so an unrestricted `get_or_create` on a typo
    inserts a row that no program card and no frontend filter will ever match, and the migration
    still reports success. Gating creation on `SEEDABLE` keeps that protection for every other
    label while removing the deploy-blocking failure mode described above. A test asserts the names
    in `SEEDABLE` and `CHANGES` against the frontend's label set before either can reach a deploy.
    """
    if status in SEEDABLE:
        legal_status, created = LegalStatus.objects.get_or_create(status=status)
        if created:
            print(f"➕ seeded missing legal status '{status}'")
        return legal_status

    try:
        return LegalStatus.objects.get(status=status)
    except LegalStatus.DoesNotExist:
        raise RuntimeError(f"legal status '{status}' does not exist — check the label against citizenshipFilterConfig.tsx")


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
                program.legal_status_required.add(get_status(LegalStatus, status))
            for status in to_remove:
                program.legal_status_required.remove(*LegalStatus.objects.filter(status=status))

            code = program.white_label.code
            changed = ", ".join(
                [f"+{s}" for s in to_add] + [f"-{s}" for s in to_remove],
            )
            print(f"✅ {code}/{name}: {changed}")


def reverse_changes(apps, schema_editor):
    """
    Best-effort reverse, in the same sense as 0127's.

    Forward removals are written to be no-ops where the status is absent, so reversing them re-adds
    `gc_5less` to every program in `CHANGES` — including the ones whose config never declared it.
    Reversing restores the overstated eligibility this migration exists to remove; it is here to
    unblock a rollback, not to reconstruct the prior state exactly.
    """
    apply_changes(apps, schema_editor, reverse=True)


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0167_add_nc_homeless_and_health_care_categories"),
    ]

    operations = [
        migrations.RunPython(apply_changes, reverse_changes),
    ]
