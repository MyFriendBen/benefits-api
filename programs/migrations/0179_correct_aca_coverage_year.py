from django.db import migrations

# Programs whose configured edition is wrong, as (white_label code, abbreviation, from, to).
#
# Only rows the vintage map marks CONFIRMED appear here. The map's UNVERIFIED rows are
# recorded as production has them and are deliberately untouched: "behind the newest
# edition" is not evidence of being wrong, and moving a benefit estimate without
# establishing the rule first is the failure this whole effort exists to avoid.
#
# Both rows below are ACA premium tax credit programs sitting a coverage year behind.
# 26 U.S.C. 36B adjudicates a coverage year against the poverty guideline in effect when
# its open enrollment opened -- the prior year's -- and PolicyEngine applies that lag
# itself, which `cross_white_label/aca/specs/ks.md` records: 2026 coverage is scored
# against the 2025 guideline while the program row reads 2026. So `year` names the
# coverage year for these programs, and 2025 means they are modelling last year's
# coverage rather than deliberately holding a lagged guideline.
#
# Kansas, Missouri, North Carolina and Texas already read 2026. These two are the states
# that were missed.
CORRECTIONS = [
    ("il", "il_aca", "2025", "2026"),
    ("ma", "ma_aca", "2025", "2026"),
]


def _repoint(apps, corrections, to_period):
    """Move each program from one FederalPoveryLimit row to another.

    Matched on (white label, abbreviation) rather than primary key: the same program has
    different ids in each environment -- `co/ssi` is 18 in production and 17 locally -- so
    a key-based migration would silently repoint a different program somewhere else.

    A row that is not on `from_period` is left alone and reported. That covers the row
    having been corrected by hand already, and the more important case of it having been
    moved somewhere unexpected, where forcing it would destroy information about what an
    environment actually held.
    """
    Program = apps.get_model("programs", "Program")
    FederalPoveryLimit = apps.get_model("programs", "FederalPoveryLimit")

    # Work out what there is to move BEFORE requiring the destination to exist. A missing
    # target row is only a problem if something needs moving onto it, and migrations also
    # run against an empty database -- every CI test run builds one from scratch, where
    # there are no programs and no FederalPoveryLimit rows because both arrive through
    # config imports rather than migrations. Demanding the row up front turned that empty
    # case into a hard failure and took down the whole test job.
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

    # Matched on year AND period: production carries a row whose year is '2022' and whose
    # period resolves to 2024, so selecting by label alone lands on the wrong edition.
    target = FederalPoveryLimit.objects.filter(year=to_period, period=to_period).first()
    if target is None:
        raise RuntimeError(
            f"{len(pending)} program(s) need moving to edition {to_period!r}, but no "
            f"FederalPoveryLimit row has year=period={to_period!r}. Create it first; "
            "repointing programs at a missing edition makes as_dict() raise inside "
            "eligibility calculation."
        )

    for white_label, abbr, expected, pk in pending:
        # queryset.update() rather than instance.save(): Program is a parler
        # TranslatableModel and the historical model apps.get_model() returns carries no
        # parler metadata, so save() dies in save_translations with a bare TypeError.
        Program.objects.filter(pk=pk).update(year=target)
        print(f"  {white_label}/{abbr}: {expected} -> {to_period}")


def forwards(apps, schema_editor):
    print("Correcting ACA coverage years:")
    _repoint(apps, [(wl, abbr, frm) for wl, abbr, frm, _to in CORRECTIONS], to_period="2026")


def backwards(apps, schema_editor):
    """Reversible, so a bad estimate can be rolled back without a hand-written fix.

    Runs the same repoint in the other direction rather than restoring a snapshot. The
    expected-period guard still applies, so a row somebody moved deliberately after this
    migration ran is left alone instead of being clobbered by the rollback.
    """
    print("Reverting ACA coverage years:")
    _repoint(apps, [(wl, abbr, to) for wl, abbr, _frm, to in CORRECTIONS], to_period="2025")


class Migration(migrations.Migration):
    dependencies = [
        # Sequenced behind the ma_ccdf CCFA migration, which also moves a Program.year
        # row and is landing first. Two migrations numbered 0178 off the same parent
        # produce multiple leaf nodes, which fails `migrate` on deploy rather than
        # conflicting in git -- so this is not something a clean merge would catch.
        ("programs", "0178_ma_ccdf_year_2026"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
