from django.db import migrations
from django.db.models import Q

# Source of truth: state["name"] in each configuration/white_labels/{code}.py.
# _default and co_tax_calculator are intentionally excluded — they aren't tied
# to a single real-world state, so state_code is expected to stay blank for them.
STATE_CODES = {
    "co": "CO",
    "il": "IL",
    "wa": "WA",
    "tx": "TX",
    "ma": "MA",
    "nc": "NC",
    "ks": "KS",
    "mo": "MO",
    "cesn": "CO",  # Colorado Energy Savings Navigator
}


def backfill_state_code(apps, schema_editor):
    WhiteLabel = apps.get_model("screener", "WhiteLabel")

    for code, state_code in STATE_CODES.items():
        # SQL's IN never matches NULL, so this can't be state_code__in=["", None] —
        # that silently matches zero rows against a NULL column (learned the hard
        # way testing this migration locally).
        WhiteLabel.objects.filter(Q(code=code) & (Q(state_code="") | Q(state_code__isnull=True))).update(
            state_code=state_code
        )


def reverse_backfill(apps, schema_editor):
    # No-op: state_code may have been set correctly by hand (e.g. via admin)
    # since this migration ran, so blindly nulling it back out would be
    # destructive rather than a true rollback.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("screener", "0164_householdmember_was_in_foster_care"),
    ]

    operations = [
        migrations.RunPython(backfill_state_code, reverse_backfill),
    ]
