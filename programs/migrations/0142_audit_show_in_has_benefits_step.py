from django.db import migrations
from django.db.models import Q

# Programs with real calculators that should appear on the has-benefits step.
# show_in_has_benefits_step=True means the program appears as a selectable tile
# so users can declare they already have it — used for categorical/presumptive eligibility.
#
# Tracking-only programs (has_calculator=False, created in 0137/0141) are intentionally
# NOT listed here: they exist purely as dependency inputs, not as tiles users select.
# The forward() migration also explicitly resets any has_calculator=False programs
# to show_in_has_benefits_step=False as a safety measure.
PROGRAMS_TO_FLAG = [
    # CO
    ("co", "co_snap"),
    ("co", "co_tanf"),
    ("co", "co_wic"),
    ("co", "andcs"),
    ("co", "leap"),
    ("co", "ssi"),
    ("co", "ssdi"),
    ("co", "chp"),
    ("co", "oap"),
    ("co", "cccap"),
    ("co", "cowap"),
    ("co", "rtdlive"),
    ("co", "section_8"),
    ("co", "co_andso"),
    ("co", "co_care"),
    # IL
    ("il", "il_snap"),
    ("il", "il_tanf"),
    ("il", "il_wic"),
    ("il", "ssi"),
    ("il", "ssdi"),
    ("il", "il_liheap"),
    ("il", "il_ccap"),
    # Note: il_chp excluded — IL CHP+ is captured via member.insurance.chp,
    # not a screen-level tracking program.
    # MA
    ("ma", "ma_snap"),
    ("ma", "ma_wic"),
    ("ma", "ssi"),
    ("ma", "ssdi"),
    ("ma", "ma_heap"),
    ("ma", "section_8"),
    # NC
    ("nc", "nc_snap"),
    ("nc", "nc_tanf"),
    ("nc", "nc_wic"),
    ("nc", "ssi"),
    ("nc", "ssdi"),
    ("nc", "nc_aca"),
    ("nc", "nc_leap"),
    ("nc", "nc_cccap"),
    # TX
    ("tx", "tx_snap"),
    ("tx", "tx_tanf"),
    ("tx", "tx_wic"),
    ("tx", "tx_ssi"),
    ("tx", "tx_ssdi"),
    # CESN
    ("cesn", "cesn_snap"),
    ("cesn", "cesn_tanf"),
    ("cesn", "cesn_wic"),
    ("cesn", "cesn_ssi"),
    ("cesn", "cesn_ssdi"),
    ("cesn", "cesn_chp"),
    ("cesn", "cesn_oap"),
    ("cesn", "cesn_section_8"),
    ("cesn", "cesn_rtdlive"),
    ("cesn", "cesn_andso"),
    ("cesn", "cesn_care"),
    ("cesn", "cesn_medicaid"),
]


def _programs_q():
    q = Q()
    for wl_code, name_abbreviated in PROGRAMS_TO_FLAG:
        q |= Q(white_label__code=wl_code, name_abbreviated=name_abbreviated)
    return q


def forward(apps, schema_editor):
    Program = apps.get_model("programs", "Program")
    # Set show_in_has_benefits_step=True for programs in the explicit allow-list.
    Program.objects.filter(_programs_q()).update(show_in_has_benefits_step=True, active=True)
    # Safety: tracking-only programs must never appear as selectable tiles.
    # Any has_calculator=False program that somehow got flagged True is reset here.
    Program.objects.filter(has_calculator=False).update(show_in_has_benefits_step=False)


def reverse(apps, schema_editor):
    Program = apps.get_model("programs", "Program")
    Program.objects.filter(_programs_q()).update(show_in_has_benefits_step=False)


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0141_create_gap_tracking_programs"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
