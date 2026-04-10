from django.db import migrations

# Programs missing WL-scoped Program rows needed for the screener_current_benefits
# join table. Each WL needs its own program row so Screen→Program links are
# unambiguous.
#
# section_8: CO and MA use screen.has_benefit("co_section_8") / ("ma_section_8") in
# calculators, but no WL-scoped Program row existed for those WLs (only cesn_section_8).
#
# co_andso / co_care: CO-only tracking programs with no calculator.
#
# Note: SSI/SSDI are not listed here — all WLs already have WL-scoped Program rows
# with name_abbreviated="ssi"/"ssdi" created by the import command.
# Note: il_chp is intentionally excluded — IL CHP+ uses member.insurance.chp
# (per-member insurance questions), not a screen-level tracking program.
GAP_TRACKING_PROGRAMS = [
    # Section 8 — WL-scoped copies (CO/MA calculators use screen.has_benefit)
    {
        "white_label_code": "co",
        "name_abbreviated": "co_section_8",
        "name_text": "Housing Choice Voucher (Section 8)",
        "description_text": "Rent subsidy",
        "base_program": "section_8",
    },
    {
        "white_label_code": "ma",
        "name_abbreviated": "ma_section_8",
        "name_text": "Housing Choice Voucher (Section 8)",
        "description_text": "Rent subsidy",
        "base_program": "section_8",
    },
    # CO tracking-only programs
    {
        "white_label_code": "co",
        "name_abbreviated": "co_andso",
        "name_text": "Aid to the Needy Disabled - State Only (AND-SO)",
        "description_text": "State cash assistance for individuals who are disabled and not yet receiving SSI",
        "base_program": "andso",
    },
    {
        "white_label_code": "co",
        "name_abbreviated": "co_care",
        "name_text": "Colorado's Affordable Residential Energy (CARE) via Energy Outreach Colorado",
        "description_text": "Home energy upgrades",
        "base_program": "care",
    },
]


def create_gap_tracking_programs(apps, schema_editor):
    from programs.models import Program
    from screener.models import WhiteLabel
    from translations.models import Translation

    for p in GAP_TRACKING_PROGRAMS:
        if not WhiteLabel.objects.filter(code=p["white_label_code"]).exists():
            continue

        existing = Program.objects.filter(
            white_label__code=p["white_label_code"],
            name_abbreviated=p["name_abbreviated"],
        ).first()

        if existing:
            program = existing
        else:
            program = Program.objects.new_program(
                white_label=p["white_label_code"],
                name_abbreviated=p["name_abbreviated"],
            )
            program.active = True
            program.has_calculator = False
            program.show_in_has_benefits_step = True
            program.base_program = p.get("base_program")
            program.save()

        Translation.objects.add_translation(
            f"program.{p['name_abbreviated']}_{program.id}-name",
            default_message=p["name_text"],
        )
        Translation.objects.add_translation(
            f"program.{p['name_abbreviated']}_{program.id}-description_short",
            default_message=p["description_text"],
        )
        Translation.objects.add_translation(
            f"program.{p['name_abbreviated']}_{program.id}-website_description",
            default_message=p["description_text"],
        )


def delete_gap_tracking_programs(apps, schema_editor):
    Program = apps.get_model("programs", "Program")
    for p in GAP_TRACKING_PROGRAMS:
        Program.objects.filter(
            white_label__code=p["white_label_code"],
            name_abbreviated=p["name_abbreviated"],
            has_calculator=False,
        ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0140_rename_cesn_andso_care"),
    ]

    operations = [
        migrations.RunPython(create_gap_tracking_programs, delete_gap_tracking_programs),
    ]
