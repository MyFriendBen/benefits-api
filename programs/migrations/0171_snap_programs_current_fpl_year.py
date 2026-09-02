from django.db import migrations

# The SNAP rows that were left on an older FederalPoveryLimit row than their siblings.
# Every SNAP program follows the same federal fiscal-year schedule, so they should all
# read the same guidelines; these four differed only in when they were last updated by
# hand. Named explicitly rather than matched on a pattern so this cannot reach a program
# that is on an older year deliberately.
STALE_SNAP_PROGRAMS = ("co_snap", "il_snap", "ma_snap", "tx_snap")

CURRENT_PERIOD = "2026"
PREVIOUS_PERIOD = "2025"


def _repoint(apps, from_period, to_period):
    Program = apps.get_model("programs", "Program")
    FederalPoveryLimit = apps.get_model("programs", "FederalPoveryLimit")

    try:
        target = FederalPoveryLimit.objects.get(period=to_period)
    except FederalPoveryLimit.DoesNotExist:
        # Nothing to point at: leave the rows alone rather than guess at a period whose
        # dollar figures _FPL_DEFAULTS may not define, which would raise a bare KeyError
        # inside eligibility calculation for every program on the row.
        return
    except FederalPoveryLimit.MultipleObjectsReturned:
        target = FederalPoveryLimit.objects.filter(period=to_period).order_by("id").first()

    Program.objects.filter(
        name_abbreviated__in=STALE_SNAP_PROGRAMS,
        year__period=from_period,
    ).update(year=target)


def forward(apps, schema_editor):
    _repoint(apps, PREVIOUS_PERIOD, CURRENT_PERIOD)


def backward(apps, schema_editor):
    _repoint(apps, CURRENT_PERIOD, PREVIOUS_PERIOD)


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0170_deactivate_il_rent_asst"),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
