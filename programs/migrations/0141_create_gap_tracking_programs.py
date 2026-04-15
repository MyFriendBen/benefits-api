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
    },
    {
        "white_label_code": "co",
        "name_abbreviated": "co_care",
        "name_text": "Colorado's Affordable Residential Energy (CARE) via Energy Outreach Colorado",
        "description_text": "Home energy upgrades",
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
    db = schema_editor.connection

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
            external_name = name_abbreviated if not external_name_exists else None
            base_program = p.get("base_program")

            # Use raw SQL to avoid django-parler crash on historical ORM models.
            # apps.get_model() returns a frozen historical model that parler never
            # registers _parler_meta on, so Program.objects.create() with translated
            # field kwargs raises AttributeError: 'NoneType'.get_all_fields().
            with db.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO programs_program (
                        name_abbreviated, external_name, year_id,
                        active, low_confidence, has_calculator,
                        show_in_has_benefits_step, show_on_current_benefits,
                        base_program, white_label_id,
                        name_id, description_short_id, description_id,
                        learn_more_link_id, apply_button_link_id,
                        apply_button_description_id, value_type_id,
                        estimated_delivery_time_id, estimated_application_time_id,
                        estimated_value_id, website_description_id
                    ) VALUES (
                        %s, %s, NULL,
                        TRUE, FALSE, FALSE,
                        TRUE, FALSE,
                        %s, %s,
                        %s, %s, %s,
                        %s, %s,
                        %s, %s,
                        %s, %s,
                        %s, %s
                    ) RETURNING id
                    """,
                    [
                        name_abbreviated,
                        external_name,
                        base_program,
                        white_label.id,
                        translations["name"].id,
                        translations["description_short"].id,
                        translations["description"].id,
                        translations["learn_more_link"].id,
                        translations["apply_button_link"].id,
                        translations["apply_button_description"].id,
                        translations["value_type"].id,
                        translations["estimated_delivery_time"].id,
                        translations["estimated_application_time"].id,
                        translations["estimated_value"].id,
                        translations["website_description"].id,
                    ],
                )
                program_id = cursor.fetchone()[0]

            # Wrap in a simple object so the label-update loop below can use program.id
            class _Program:
                id = program_id

            program = _Program()

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
