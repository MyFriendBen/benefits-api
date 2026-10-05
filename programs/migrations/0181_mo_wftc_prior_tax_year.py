from django.db import migrations

# Programs moving onto the prior tax year, as (white_label code, abbreviation, from, to).
#
# For a tax credit `Program.year` is the tax year being claimed, and the tax year a household
# screening now files is the calendar year just ended. mo_wftc was configured on 2026, so it
# showed a household the credit for a year it cannot file yet. Its spec and tests are
# validated at TY2025.
#
# Only mo_wftc moves. The other Missouri credits it sits beside -- mo_eitc, mo_ctc,
# mo_cdcc_federal, mo_pts -- stay where production has them until each is verified at the
# prior year.
CORRECTIONS = [
    ("mo", "mo_wftc", "2026", "2025"),
]


def _repoint(apps, corrections, to_period):
    """Move each program onto the FederalPoveryLimit row for `to_period`.

    Matched on (white label, abbreviation) rather than primary key, since ids differ by
    environment. A row not on its expected period is reported and left alone. The target row
    is required only once something needs moving: migrations also run against an empty
    database, where programs and FederalPoveryLimit rows both arrive through config imports.
    """
    Program = apps.get_model("programs", "Program")
    FederalPoveryLimit = apps.get_model("programs", "FederalPoveryLimit")

    pending = []
    for white_label, abbr, expected in corrections:
        program = (
            Program.objects.filter(white_label__code=white_label, name_abbreviated=abbr)
            .select_related("year")
            .first()
        )

        if program is None:
            print(f"  {white_label}/{abbr}: not in this environment, skipping")
            continue

        current = program.year.period if program.year else None
        if current != expected:
            print(f"  {white_label}/{abbr}: on {current!r}, expected {expected!r} — leaving it alone")
            continue

        pending.append((white_label, abbr, expected, program.pk))

    if not pending:
        print("  nothing to move")
        return

    # Matched on year AND period: production carries a row whose year label and period differ.
    target = FederalPoveryLimit.objects.filter(year=to_period, period=to_period).first()
    if target is None:
        raise RuntimeError(
            f"{len(pending)} program(s) need moving to {to_period!r}, but no FederalPoveryLimit "
            f"row has year=period={to_period!r}. Create it first."
        )

    for white_label, abbr, expected, pk in pending:
        # update() rather than save(): the historical Program model carries no parler metadata.
        Program.objects.filter(pk=pk).update(year=target)
        print(f"  {white_label}/{abbr}: {expected} -> {to_period}")


def forwards(apps, schema_editor):
    print("Moving mo_wftc onto the prior tax year:")
    _repoint(apps, [(wl, abbr, frm) for wl, abbr, frm, _to in CORRECTIONS], to_period="2025")


def backwards(apps, schema_editor):
    print("Reverting mo_wftc:")
    _repoint(apps, [(wl, abbr, to) for wl, abbr, _frm, to in CORRECTIONS], to_period="2026")


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0180_ssi_msp_csfp_current_edition"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
