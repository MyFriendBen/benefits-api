from django.db import migrations


#: The FederalPoveryLimit row supplying `Program.year.period`, which is the period every
#: PolicyEngine input and output for this program is requested at.
NEW_YEAR = "2026"
OLD_YEAR = "2025"


def _ma_ccdf_on(apps, period):
    """The `ma_ccdf` rows running at `period`.

    Selects on `period`, not `year`. `period` is what `pe_period` reads, and the two are
    allowed to differ: `year` is unique while `period` is free text, and `from_model_data`
    rewrites the `period` of an existing `year` row.
    """
    Program = apps.get_model("programs", "Program")

    return Program.objects.filter(name_abbreviated="ma_ccdf", year__period=period)


def _ma_ccdf_off(apps, period):
    """The `ma_ccdf` rows sitting on a period earlier than `period`.

    Selects everything staler than the target rather than everything that is not the
    target, so a row already moved forward is left where it is instead of being pulled
    back. Periods are the four-digit years `FederalPoveryLimit` indexes its figures by,
    so they order lexicographically. A null `year` is left alone: `pe_period` raises on
    it, and cannot silently apply the wrong limit.
    """
    Program = apps.get_model("programs", "Program")

    return Program.objects.filter(name_abbreviated="ma_ccdf", year__period__lt=period)


def _fpl(apps, period):
    """The FederalPoveryLimit row running at `period`, or None if it has not been imported.

    Matches on `period`, since that is what the program will read. Prefers the row whose
    `year` label agrees -- the one every config import creates -- but takes any row at the
    right period rather than failing a deploy over a label, ordering so the choice is
    stable when more than one exists.
    """
    FederalPoveryLimit = apps.get_model("programs", "FederalPoveryLimit")

    rows = FederalPoveryLimit.objects.filter(period=period)

    return rows.filter(year=period).first() or rows.order_by("year").first()


def set_ma_ccdf_year_2026(apps, schema_editor):
    """
    Move `ma_ccdf` to the 2026 period.

    Massachusetts CCFA reads one of two income limits: 85% of state median income for a
    household already enrolled, and a new-applicant limit that PolicyEngine holds at 50%
    before 2026-01-01 and 85% from it. Screening asks the new-applicant question, so at the
    2025 period the program applies the 50% limit, well under half the ceiling it should.

    The federal CCDF variables this program used to read had a single 85% limit at any
    period, so the 2025 period cost nothing while they were in use and costs a large share
    of eligible Massachusetts families now. There is no config file for this program --
    `year` is set through the admin -- so the bump ships here rather than as an import that
    could lag the deploy.

    Fails the deploy if the program is on an earlier period and the 2026 row is missing.
    Landing the calculator while the program still reads an earlier period is the one worth
    stopping for: it is silent, and it applies the 50% limit to every Massachusetts
    family screening for childcare. A database that has never imported a config has
    neither the program nor any FederalPoveryLimit row, so there is nothing to move and
    nothing to raise about -- `migrate` on a fresh checkout is unaffected.
    """
    programs = _ma_ccdf_off(apps, NEW_YEAR)
    if not programs.exists():
        return

    fpl = _fpl(apps, NEW_YEAR)
    if fpl is None:
        raise RuntimeError(
            f"ma_ccdf is on a period before {NEW_YEAR} and no FederalPoveryLimit row exists for "
            f"{NEW_YEAR}. Import the {NEW_YEAR} config first: leaving the program on {OLD_YEAR} "
            "applies CCFA's 50%-of-SMI new-applicant limit instead of 85%."
        )

    programs.update(year=fpl)


def revert_ma_ccdf_year(apps, schema_editor):
    """Move `ma_ccdf` back to the 2025 period.

    Does not raise when the 2025 row is missing, unlike the forward direction. Being
    left on 2026 is the correct limit rather than the wrong one, so it is not worth
    failing an unapply -- which tends to happen under pressure -- over.
    """
    fpl = _fpl(apps, OLD_YEAR)
    if fpl is None:
        print(f"ma_ccdf: no FederalPoveryLimit for {OLD_YEAR}; leaving the program on {NEW_YEAR}")
        return

    _ma_ccdf_on(apps, NEW_YEAR).update(year=fpl)


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0177_create_gap_tracking_programs_with_calculator_flag"),
    ]
    operations = [
        migrations.RunPython(set_ma_ccdf_year_2026, revert_ma_ccdf_year),
    ]
