from django.db import migrations

# Every state SSDI row, by name. `ssdi` is the bare name CO, IL, MA and NC share; `cesn_ssdi` is
# CESN's current-benefits tile, which has no calculator.
STATE_SSDI_NAMES = ["ssdi", "cesn_ssdi", "ks_ssdi", "mo_ssdi", "tx_ssdi", "wa_ssdi"]


def deactivate_state_ssdi(apps, schema_editor) -> None:
    """
    Deactivate the state SSDI rows, which the federal `federal_ssdi` row replaces.

    Every white label sees the federal row, so a state row left active would show SSDI twice.
    The calculators behind these rows are deleted in the same release, and `Program.eligibility()`
    looks a calculator up by name without a fallback, so an active row would 500 the results page.

    Matched by name in every white label except `federal`, rather than as a fixed list of
    (white label, name) pairs, so a row admin created somewhere unexpected is caught too.
    Deactivated, not deleted: `CurrentBenefit.program` cascades on delete, and screens still
    holding these rows are moved to the federal row separately.
    """
    Program = apps.get_model("programs", "Program")
    Program.objects.filter(name_abbreviated__in=STATE_SSDI_NAMES).exclude(white_label__code="federal").update(
        active=False
    )


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0189_add_211ks_211mo_referrers"),
    ]
    operations = [
        # noop reverse: rolling back should not put a second SSDI result in front of every
        # white label. Reactivation is a deliberate act, done separately.
        migrations.RunPython(deactivate_state_ssdi, migrations.RunPython.noop),
    ]
