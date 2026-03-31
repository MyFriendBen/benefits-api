from collections import defaultdict

from django.db import migrations


# Derived from Screen.has_benefit() name_map.
# Maps program name_abbreviated -> has_* field name on Screen model.
# Special cases simplified:
#   - "ssi" / "tx_ssi": uses has_ssi only (skips SSI income check)
#   - "chp": uses has_chp only (skips has_chp_hi)
#   - "ma_mass_health": uses has_medicaid only (skips has_medicaid_hi)
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
    "project_cope": "has_project_cope",
    "cesn_cope": "has_project_cope",
    "cesn_heap": "has_cesn_heap",
    "rtdlive": "has_rtdlive",
    "cccap": "has_ccap",
    "mydenver": "has_mydenver",
    "ccb": "has_ccb",
    "ssi": "has_ssi",
    "tx_ssi": "has_ssi",
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
    "nfp": "has_nfp",
    "co_nfp": "has_nfp",
    "il_nfp": "has_nfp",
    "fatc": "has_fatc",
    "section_8": "has_section_8",
    "ma_cha": "has_section_8",
    "cowap": "has_cowap",
    "cesn_cowap": "has_cowap",
    "ncwap": "has_ncwap",
    "ubp": "has_ubp",
    "cesn_ubp": "has_ubp",
    "medicare": "has_medicare_hi",
    "chp": "has_chp",
    "va": "has_va",
    "aca": "has_aca",
    "nc_aca": "has_aca",
    "ma_aca": "has_aca",
    "tx_aca": "has_aca",
    "ma_mbta": "has_ma_mbta",
    "ma_snap": "has_snap",
    "ma_ccdf": "has_ccdf",
    "ma_wic": "has_wic",
    "ma_eaedc": "has_ma_eaedc",
    "ma_maeitc": "has_ma_maeitc",
    "ma_macfc": "has_ma_macfc",
    "ma_homebridge": "has_ma_homebridge",
    "ma_dhsp_afterschool": "has_ma_dhsp_afterschool",
    "ma_door_to_door": "has_ma_door_to_door",
    "ma_taxi_discount": "has_ma_taxi_discount",
    "ma_cpp": "has_ma_cpp",
    "ma_middle_income_rental": "has_ma_middle_income_rental",
    "ma_cmsp": "has_ma_cmsp",
    "ma_tafdc": "has_tanf",
    "ma_mass_health": "has_medicaid",
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
}


def backfill_current_benefits(apps, schema_editor):
    """
    Populates the screener_current_benefits join table from existing has_* column values
    for all historical Screen records. Uses the has_benefit() name_map as source of truth
    for which name_abbreviated values correspond to which has_* fields.
    """
    Screen = apps.get_model("screener", "Screen")
    Program = apps.get_model("programs", "Program")
    CurrentBenefit = apps.get_model("screener", "CurrentBenefit")

    # Build inverse: has_field_name -> [name_abbreviated, ...]
    field_to_names = defaultdict(list)
    for name, field in NAME_TO_FIELD.items():
        field_to_names[field].append(name)

    # Index existing programs by name_abbreviated
    programs_by_name = {p.name_abbreviated: p.id for p in Program.objects.all()}

    entries_to_create = []

    for field_name, name_abbreviated_list in field_to_names.items():
        # Resolve to program IDs that actually exist in the DB
        program_ids = [programs_by_name[n] for n in name_abbreviated_list if n in programs_by_name]
        if not program_ids:
            continue

        # Find screens where this has_* field is True
        screen_ids = list(Screen.objects.filter(**{field_name: True}).values_list("id", flat=True))
        if not screen_ids:
            continue

        for screen_id in screen_ids:
            for program_id in program_ids:
                entries_to_create.append(CurrentBenefit(screen_id=screen_id, program_id=program_id))

    batch_size = 1000
    created = 0
    for i in range(0, len(entries_to_create), batch_size):
        batch = CurrentBenefit.objects.bulk_create(entries_to_create[i : i + batch_size], ignore_conflicts=True)
        created += len(batch)

    print(f"Backfilled {created} CurrentBenefit rows from has_* columns")


def reverse_backfill(apps, schema_editor):
    CurrentBenefit = apps.get_model("screener", "CurrentBenefit")
    CurrentBenefit.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("screener", "0149_backfill_has_head_start_from_has_chs"),
    ]

    operations = [
        migrations.RunPython(backfill_current_benefits, reverse_backfill),
    ]
