from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

# State copies of national organisations, each available in every state, move to `federal`.
# A navigator belongs to whichever white label imported it first, so each state's
# config made its own copy. Each copy keeps its links: navigators on a state program aren't
# filtered by white label, so the state programs that show them still do. On `federal`,
# partner admins can view them but not change them.
#
# Found by matching names that look alike and share a phone number or website. Kept on their
# state, since each has its own contact details: `ks_aarp_tax_aide` (a Kansas chapter site),
# `wa_lifeline_support_center` (a Washington phone number), and New Jersey's two VITA and TCE
# copies (a New Jersey phone number). `headstart_national_hotline` stays on `il` for now.
#
# The copies aren't merged: some are owned by program-ops records and some carry
# program-specific text. Deduplicating them is a separate cleanup.
NAVIGATORS = (
    # AARP Foundation Tax-Aide
    "co_aarp_tax_aide",
    "co_tax_calculator_aarp_tax_aide",
    "il_aarp_tax_aide",
    "ma_aarp_tax_aide",
    "mo_aarp_tax_aide",
    "mo_ctc_aarp_tax_aide",
    "mo_eitc_aarp_tax_aide",
    "nc_aarp_tax_aide",
    "tx_aarp_tax_aide",
    "wa_aarp_tax_aide",
    # GetYourRefund
    "co_get_your_refund",
    "co_tax_calculator_get_your_refund",
    "il_get_your_refund",
    "ks_eitc_federal_get_your_refund",
    "ma_get_your_refund",
    "mo_eitc_get_your_refund",
    "nc_get_your_refund",
    "nc_getyourrefund.org",
    "tx_get_your_refund",
    "wa_get_your_refund",
    # VITA Free Tax Preparation (IRS Volunteer Income Tax Assistance)
    "co_vita_free_tax_prep",
    "co_tax_calculator_vita_free_tax_prep",
    "il_vita_free_tax_prep",
    "ma_vita_free_tax_prep",
    "mo_ctc_vita_free_tax_prep",
    "mo_eitc_vita_free_tax_prep",
    "nc_vita_free_tax_prep",
    "tx_vita_free_tax_prep",
    "wa_vita_free_tax_prep",
    # Universal Service Administrative Co - Lifeline Support Center, on the shared number
    "ks_lifeline_support_center",
    "ma_lifeline_support_center",
    "mo_lifeline_support_center",
    "nc_lifeline_support_center",
    "tx_lifeline_support_center",
    # USDA National Hunger Hotline
    "mo_csfp_hunger_hotline",
)


def forwards(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    Navigator = apps.get_model("programs", "Navigator")
    WhiteLabel = apps.get_model("screener", "WhiteLabel")

    federal = WhiteLabel.objects.filter(code="federal").first()
    if federal is None:
        print("  no federal white label in this environment; nothing to move")
        return

    moved = Navigator.objects.filter(external_name__in=NAVIGATORS).exclude(white_label=federal).update(
        white_label=federal
    )
    print(f"  moved {moved} national navigator copies to the federal white label")


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0203_move_national_hunger_hotline_to_federal"),
    ]

    operations = [
        # No reverse: the white label each came from differs by environment.
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
