from django.db import migrations
from django.db.models import Q

# Programs audited as categorical/presumptive eligibility inputs — either:
#   - their presence grants automatic eligibility for another program (positive has_benefit check)
#   - their presence excludes eligibility for a different program (cross-program not has_benefit check)
#
# Organized as (white_label_code, name_abbreviated) pairs.
# Gap tracking programs created in 0141 already have show_in_has_benefits_step=True;
# included here for completeness and idempotency.
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
    # CO gap programs (created in 0141)
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
    # IL gap program (created in 0141)
    ("il", "il_chp"),
    # MA
    ("ma", "ma_snap"),
    ("ma", "ma_wic"),
    ("ma", "ssi"),
    ("ma", "ssdi"),
    ("ma", "ma_heap"),
    # MA gap program (created in 0141)
    ("ma", "section_8"),
    # NC
    ("nc", "nc_snap"),
    ("nc", "nc_tanf"),
    ("nc", "nc_wic"),
    ("nc", "ssi"),
    ("nc", "ssdi"),
    ("nc", "nc_aca"),
    # TX
    ("tx", "tx_snap"),
    ("tx", "tx_tanf"),
    ("tx", "tx_wic"),
    ("tx", "tx_ssi"),
    ("tx", "tx_ssdi"),
]

# Tracking-only programs (has_calculator=False) that were set active=False in 0137
# as a workaround to prevent calculator runs. Now that views.py gates on has_calculator,
# these can be active=True so they appear in the Program API and current benefits step.
TRACKING_PROGRAM_NAMES = [
    # cesn (from 0137, renamed in 0140)
    "cesn_snap",
    "cesn_tanf",
    "cesn_wic",
    "cesn_ssi",
    "cesn_ssdi",
    "cesn_chp",
    "cesn_oap",
    "cesn_section_8",
    "cesn_rtdlive",
    "cesn_andso",
    "cesn_medicaid",
    # nc (from 0137)
    "nc_leap",
    "nc_cccap",
]


def _programs_q():
    q = Q()
    for wl_code, name_abbreviated in PROGRAMS_TO_FLAG:
        q |= Q(white_label__code=wl_code, name_abbreviated=name_abbreviated)
    return q


def forward(apps, schema_editor):
    Program = apps.get_model("programs", "Program")

    Program.objects.filter(_programs_q()).update(show_in_has_benefits_step=True, active=True)

    # Activate tracking-only programs now that has_calculator gates calculator runs.
    # Filter by has_calculator=False to avoid touching any real calculator programs.
    Program.objects.filter(
        name_abbreviated__in=TRACKING_PROGRAM_NAMES,
        has_calculator=False,
    ).update(active=True)


def reverse(apps, schema_editor):
    Program = apps.get_model("programs", "Program")

    Program.objects.filter(_programs_q()).update(show_in_has_benefits_step=False)

    Program.objects.filter(
        name_abbreviated__in=TRACKING_PROGRAM_NAMES,
        has_calculator=False,
    ).update(active=False)


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0141_create_gap_tracking_programs"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
