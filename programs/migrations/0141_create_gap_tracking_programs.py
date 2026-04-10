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


TRANSLATED_FIELDS = (
    "description_short",
    "name",
    "description",
    "learn_more_link",
    "apply_button_link",
    "apply_button_description",
    "value_type",
    "estimated_delivery_time",
    "estimated_application_time",
    "estimated_value",
    "website_description",
)
NO_AUTO_FIELDS = ("apply_button_link", "learn_more_link")
BLANK_TRANSLATION_PLACEHOLDER = "[PLACEHOLDER]"


def create_gap_tracking_programs(apps, schema_editor):
    from translations.models import Translation

    Program = apps.get_model("programs", "Program")
    WhiteLabel = apps.get_model("screener", "WhiteLabel")

    for p in GAP_TRACKING_PROGRAMS:
        try:
            white_label = WhiteLabel.objects.get(code=p["white_label_code"])
        except WhiteLabel.DoesNotExist:
            continue

        existing = Program.objects.filter(
            white_label__code=p["white_label_code"],
            name_abbreviated=p["name_abbreviated"],
        ).first()

        if existing:
            program = existing
        else:
            name_abbreviated = p["name_abbreviated"]
            translations = {}
            for field in TRANSLATED_FIELDS:
                default_message = "" if field == "apply_button_description" else BLANK_TRANSLATION_PLACEHOLDER
                translations[field] = Translation.objects.add_translation(
                    f"program.{name_abbreviated}_temporary_key-{field}",
                    default_message=default_message,
                    no_auto=(field in NO_AUTO_FIELDS),
                )

            external_name_exists = Program.objects.filter(external_name=name_abbreviated).exists()
            program = Program.objects.create(
                name_abbreviated=name_abbreviated,
                external_name=name_abbreviated if not external_name_exists else None,
                year=None,
                active=True,
                low_confidence=False,
                has_calculator=False,
                show_in_has_benefits_step=True,
                base_program=p.get("base_program"),
                white_label=white_label,
                **translations,
            )

            for field, translation in translations.items():
                translation.label = f"program.{name_abbreviated}_{program.id}-{field}"
                translation.save()

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
