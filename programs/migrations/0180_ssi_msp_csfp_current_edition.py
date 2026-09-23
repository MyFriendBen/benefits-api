from django.db import migrations

# Programs moving onto the current poverty-guideline edition, as
# (white_label code, abbreviation, from, to).
#
# Three families, established three different ways:
#
#   SSI  -- the federal benefit rate is adjusted by COLA each January and SSI is federally
#           administered, so there is no state adoption step to lag behind. The program's
#           own spec prices the 2026 rate outright ($994 individual / $1,491 couple).
#
#   MSP  -- established by probing PolicyEngine, because the spec states the thresholds as
#           percentages and never says which edition they apply against. At request period
#           2026 the outer eligibility boundary is 135% of the 2026 guideline plus SSI's
#           $240/year general exclusion; no 2025 threshold fits. The data gap is recorded
#           in msp/specs/tx.md for the next maintenance pass.
#
#   CSFP -- same method, same answer for the edition. Note the spec and the engine disagree
#           about the PERCENTAGE: the spec records USDA revising the limit to 150% while
#           PolicyEngine applies 130%, a $3,192 difference in who qualifies. That is
#           unresolved and recorded in csfp/specs/wa.md. This migration settles the edition
#           only and does not depend on which percentage turns out to be right.
#
# ma_csfp and il_csfp did not move enough in the evidence harness to clear the materiality
# threshold on their own, but a family-wide rule applies to the whole family -- materiality
# decides what gets researched, not what the conclusion covers.
CORRECTIONS = [
    ("co", "ssi", "2025", "2026"),
    ("il", "ssi", "2025", "2026"),
    ("ma", "ssi", "2025", "2026"),
    ("tx", "tx_ssi", "2025", "2026"),
    ("il", "il_msp", "2025", "2026"),
    ("tx", "tx_medicare_savings_program", "2025", "2026"),
    ("tx", "tx_csfp", "2025", "2026"),
    ("ma", "ma_csfp", "2025", "2026"),
    ("il", "il_csfp", "2025", "2026"),
]


def _repoint(apps, corrections, to_period):
    """Move each program onto the FederalPoveryLimit row for `to_period`.

    Matched on (white label, abbreviation) rather than primary key: the same program has
    different ids in each environment, so a key-based migration would repoint a different
    program somewhere else. A row not on its expected period is reported and left alone,
    which covers both the already-corrected case and the more important one where a row has
    been moved somewhere unexpected and forcing it would destroy that information.
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
    print("Moving SSI, MSP and CSFP onto the current edition:")
    _repoint(apps, [(wl, abbr, frm) for wl, abbr, frm, _to in CORRECTIONS], to_period="2026")


def backwards(apps, schema_editor):
    print("Reverting SSI, MSP and CSFP:")
    _repoint(apps, [(wl, abbr, to) for wl, abbr, _frm, to in CORRECTIONS], to_period="2025")


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0179_correct_aca_coverage_year"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
