from collections import defaultdict

from django.db import migrations
from django.db.models import Q

# Derived from Screen.has_benefit() name_map.
# Maps program name_abbreviated -> has_* field name on Screen model.
# Three entries are intentionally omitted here and handled separately below
# because their enrollment condition is a compound expression in has_benefit():
#   "ssi" / "tx_ssi"  → has_ssi=True OR SSI income stream exists
#   "chp"              → has_chp=True OR has_chp_hi=True
#   "ma_mass_health"   → has_medicaid=True OR has_medicaid_hi=True
NAME_TO_FIELD = {
    "tanf": "has_tanf",
    "nc_tanf": "has_tanf",
    "co_tanf": "has_tanf",
    "il_tanf": "has_tanf",
    "tx_tanf": "has_tanf",
    "wic": "has_wic",
    "co_wic": "has_wic",
    "il_wic": "has_wic",
    "nc_wic": "has_wic",
    "tx_wic": "has_wic",
    "snap": "has_snap",
    "sunbucks": "has_sunbucks",
    "co_snap": "has_snap",
    "nc_snap": "has_snap",
    "il_snap": "has_snap",
    "tx_snap": "has_snap",
    "lifeline": "has_lifeline",
    "acp": "has_acp",
    "eitc": "has_eitc",
    "tx_eitc": "has_eitc",
    "coeitc": "has_coeitc",
    "il_eitc": "has_il_eitc",
    "nslp": "has_nslp",
    "tx_nslp": "has_nslp",
    "ctc": "has_ctc",
    "tx_ctc": "has_ctc",
    "il_ctc": "has_il_ctc",
    "il_transit_reduced_fare": "has_il_transit_reduced_fare",
    "il_bap": "has_il_bap",
    "il_csfp": "has_csfp",
    "il_hbwd": "has_il_hbwd",
    "il_ccap": "has_ccap",
    "cesn_cope": "has_project_cope",
    "cesn_heap": "has_cesn_heap",
    "rtdlive": "has_rtdlive",
    "cccap": "has_ccap",
    "mydenver": "has_mydenver",
    "tx_csfp": "has_csfp",
    "tx_harris_rides": "has_harris_county_rides",
    "andcs": "has_andcs",
    "co_head_start": "has_head_start",
    "cpcr": "has_cpcr",
    "cesn_cpcr": "has_cpcr",
    "cdhcs": "has_cdhcs",
    "dpp": "has_dpp",
    "ede": "has_ede",
    "erc": "has_erc",
    "leap": "has_leap",
    "cesn_leap": "has_leap",
    "ma_heap": "has_ma_heap",
    "il_liheap": "has_il_liheap",
    "nc_lieap": "has_nc_lieap",
    "oap": "has_oap",
    "nccip": "has_nccip",
    "nc_scca": "has_ncscca",
    "nc_head_start": "has_head_start",
    "coctc": "has_coctc",
    "upk": "has_upk",
    "ssdi": "has_ssdi",
    "pell_grant": "has_pell_grant",
    "rag": "has_rag",
    "co_nfp": "has_nfp",
    "il_nfp": "has_nfp",
    "fatc": "has_fatc",
    "ma_cha": "has_section_8",
    "cowap": "has_cowap",
    "cesn_cowap": "has_cowap",
    "ncwap": "has_ncwap",
    "ubp": "has_ubp",
    "cesn_ubp": "has_ubp",
    "nfp": "has_nfp",
    "section_8": "has_section_8",
    "aca": "has_aca",
    "medicaid": "has_medicaid",
    "nc_aca": "has_aca",
    "ma_aca": "has_aca",
    "tx_aca": "has_aca",
    "ma_mbta": "has_ma_mbta",
    "ma_snap": "has_snap",
    "ma_ccdf": "has_ccdf",
    "ma_wic": "has_wic",
    "ma_eaedc": "has_ma_eaedc",
    "ma_maeitc": "has_ma_maeitc",
    "ma_cfc": "has_ma_cfc",
    "ma_homebridge": "has_ma_homebridge",
    "ma_dhsp_afterschool": "has_ma_dhsp_afterschool",
    "ma_door_to_door": "has_ma_door_to_door",
    "ma_taxi_discount": "has_ma_taxi_discount",
    "ma_cpp": "has_ma_cpp",
    "ma_middle_income_rental": "has_ma_middle_income_rental",
    "ma_cmsp": "has_ma_cmsp",
    "ma_tafdc": "has_tanf",
    "ma_head_start": "has_head_start",
    "ma_csfp": "has_csfp",
    "ma_early_head_start": "has_early_head_start",
    "co_andso": "has_co_andso",
    "co_care": "has_co_care",
    "cfhc": "has_cfhc",
    "shitc": "has_shitc",
    "nc_medicare_savings": "has_nc_medicare_savings",
    "tx_dart": "has_tx_dart",
    "ccs": "has_ccs",
    "tx_ccs": "has_ccs",
    "tx_ssdi": "has_ssdi",
    "ma_ssp": "has_ma_ssp",
    "cesn_snap": "has_snap",
    "cesn_tanf": "has_tanf",
    "cesn_wic": "has_wic",
    "cesn_ssdi": "has_ssdi",
    "cesn_oap": "has_oap",
    "cesn_section_8": "has_section_8",
    "cesn_rtdlive": "has_rtdlive",
    "cesn_andcs": "has_andcs",
    "cesn_medicaid": "has_medicaid",
    "nc_leap": "has_leap",
    "nc_cccap": "has_ccap",
}


def backfill_current_benefits(apps, schema_editor):
    """
    Populates the screener_current_benefits join table from existing has_* column values
    for all historical Screen records. Uses the has_benefit() name_map as source of truth
    for which name_abbreviated values correspond to which has_* fields.

    Programs are scoped per white label so a CO screen never gets linked to IL/TX/etc.
    programs that share the same has_* field mapping.
    """
    Screen = apps.get_model("screener", "Screen")
    Program = apps.get_model("programs", "Program")
    CurrentBenefit = apps.get_model("screener", "CurrentBenefit")

    # Build inverse: has_field_name -> [name_abbreviated, ...]
    field_to_names = defaultdict(list)
    for name, field in NAME_TO_FIELD.items():
        field_to_names[field].append(name)

    # Group programs by white_label_id so lookups are scoped per white label.
    # A name_abbreviated is unique per (white_label, name_abbreviated), not globally.
    programs_by_wl: dict[int, dict[str, int]] = defaultdict(dict)
    for p in Program.objects.values("id", "name_abbreviated", "white_label_id"):
        programs_by_wl[p["white_label_id"]][p["name_abbreviated"]] = p["id"]

    batch_size = 1000
    pending = []

    def flush():
        if pending:
            CurrentBenefit.objects.bulk_create(pending, ignore_conflicts=True)
            pending.clear()

    def enqueue(screen_id, program_ids):
        for program_id in program_ids:
            pending.append(CurrentBenefit(screen_id=screen_id, program_id=program_id))
        if len(pending) >= batch_size:
            flush()

    for white_label_id, programs_by_name in programs_by_wl.items():

        # --- Simple field-based cases ---
        for field_name, name_abbreviated_list in field_to_names.items():
            program_ids = [programs_by_name[n] for n in name_abbreviated_list if n in programs_by_name]
            if not program_ids:
                continue

            for screen_id in Screen.objects.filter(white_label_id=white_label_id, **{field_name: True}).values_list(
                "id", flat=True
            ):
                enqueue(screen_id, program_ids)

        # --- Compound cases: mirror Screen.has_benefit() exactly ---

        # SSI: has_ssi=True OR any income stream with type="sSI" and amount > 0
        ssi_program_ids = [programs_by_name[n] for n in ("ssi", "tx_ssi", "cesn_ssi") if n in programs_by_name]
        if ssi_program_ids:
            for screen_id in (
                Screen.objects.filter(white_label_id=white_label_id)
                .filter(
                    Q(has_ssi=True)
                    | Q(
                        household_members__income_streams__type="sSI",
                        household_members__income_streams__amount__gt=0,
                    )
                )
                .distinct()
                .values_list("id", flat=True)
            ):
                enqueue(screen_id, ssi_program_ids)

        # CHP: has_chp=True OR has_chp_hi=True
        chp_program_ids = [programs_by_name[n] for n in ("chp", "cesn_chp") if n in programs_by_name]
        if chp_program_ids:
            for screen_id in (
                Screen.objects.filter(white_label_id=white_label_id)
                .filter(Q(has_chp=True) | Q(has_chp_hi=True))
                .values_list("id", flat=True)
            ):
                enqueue(screen_id, chp_program_ids)

        # MA Mass Health: has_medicaid=True OR has_medicaid_hi=True
        mass_health_program_ids = [programs_by_name["ma_mass_health"]] if "ma_mass_health" in programs_by_name else []
        if mass_health_program_ids:
            for screen_id in (
                Screen.objects.filter(white_label_id=white_label_id)
                .filter(Q(has_medicaid=True) | Q(has_medicaid_hi=True))
                .values_list("id", flat=True)
            ):
                enqueue(screen_id, mass_health_program_ids)

    flush()
    print("Backfilled CurrentBenefit rows from has_* columns")


class Migration(migrations.Migration):

    dependencies = [
        ("screener", "0149_backfill_has_head_start_from_has_chs"),
        ("programs", "0139_delete_cocb_program"),
    ]

    operations = [
        migrations.RunPython(backfill_current_benefits, migrations.RunPython.noop),
    ]
