from django.db import migrations

# Same list as 0141_create_gap_tracking_programs.py's GAP_TRACKING_PROGRAMS.
# That migration skips creating a program when its white label doesn't exist
# yet (WhiteLabel.DoesNotExist: continue) — true on a fresh database, since
# these white labels didn't exist when 0141 first ran. This migration runs
# after 0176_create_state_white_labels, which guarantees they now do, so it
# can finish the job 0141 couldn't. It also corrects has_calculator on any
# row that already exists with the wrong value (from 0141's own "existing
# row" branch, or from bulk_import creating it fresh — bulk_import's
# ProgramDataController never syncs has_calculator on create or update, so a
# row created here with the flag set correctly stays correct even after a
# later bulk_import run touches its other fields).
GAP_TRACKING_PROGRAMS = [
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
    "estimated_delivery_time",
    "estimated_application_time",
    "estimated_value",
    "website_description",
)
NO_AUTO_FIELDS = ("apply_button_link", "learn_more_link")
BLANK_TRANSLATION_PLACEHOLDER = "[PLACEHOLDER]"


def create_or_fix_gap_tracking_programs(apps, schema_editor):
    from translations.models import Translation

    Program = apps.get_model("programs", "Program")
    WhiteLabel = apps.get_model("screener", "WhiteLabel")
    db = schema_editor.connection

    for p in GAP_TRACKING_PROGRAMS:
        # code has no unique constraint at the DB level (screener/models.py),
        # so .get() could raise MultipleObjectsReturned on a drifted database.
        # Match the same defensive read configuration/views.py:46 and
        # 0176_create_state_white_labels.py use.
        white_label = WhiteLabel.objects.filter(code=p["white_label_code"]).order_by("id").first()
        if white_label is None:
            continue

        existing = Program.objects.filter(
            white_label=white_label,
            name_abbreviated=p["name_abbreviated"],
        ).first()

        if existing:
            # Plain ORM filter/update is safe on the historical model here —
            # it's only .create()/instantiation that crashes on parler's
            # missing _parler_meta (see the raw-SQL branch below).
            Program.objects.filter(pk=existing.pk, has_calculator=True).update(has_calculator=False)
            continue

        name_abbreviated = p["name_abbreviated"]
        translations = {}
        for field in TRANSLATED_FIELDS:
            default_message = "" if field == "apply_button_description" else BLANK_TRANSLATION_PLACEHOLDER
            translations[field] = Translation.objects.add_translation(
                f"program.{name_abbreviated}_temporary_key-{field}",
                default_message=default_message,
                no_auto=(field in NO_AUTO_FIELDS),
            )

        # external_name is required and unique (0148_alter_program_external_name)
        # — unlike when 0141 was written, None is no longer a legal fallback
        # here. Mirror ProgramManager.new_program()'s collision convention
        # (programs/models.py:529-543) instead: namespace by white label, and
        # raise rather than silently insert a non-unique value.
        if not Program.objects.filter(external_name=name_abbreviated).exists():
            external_name = name_abbreviated
        else:
            external_name = f"{p['white_label_code']}_{name_abbreviated}"
            if Program.objects.filter(external_name=external_name).exists():
                raise ValueError(f"Cannot generate unique external_name. Conflict on '{external_name}'")
        base_program = p.get("base_program")

        # Raw SQL, not the ORM: apps.get_model() returns a frozen historical
        # model that parler never registers _parler_meta on, so
        # Program.objects.create() raises AttributeError: 'NoneType'.get_all_fields()
        # (see 0141_create_gap_tracking_programs.py, which hit the same issue).
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
                    apply_button_description_id,
                    estimated_delivery_time_id, estimated_application_time_id,
                    estimated_value_id, website_description_id
                ) VALUES (
                    %s, %s, NULL,
                    TRUE, FALSE, FALSE,
                    TRUE, FALSE,
                    %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s,
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
                    translations["estimated_delivery_time"].id,
                    translations["estimated_application_time"].id,
                    translations["estimated_value"].id,
                    translations["website_description"].id,
                ],
            )
            program_id = cursor.fetchone()[0]

        for field, translation in translations.items():
            translation.label = f"program.{name_abbreviated}_{program_id}-{field}"
            translation.save()

        Translation.objects.add_translation(
            f"program.{name_abbreviated}_{program_id}-name",
            default_message=p["name_text"],
        )
        Translation.objects.add_translation(
            f"program.{name_abbreviated}_{program_id}-description_short",
            default_message=p["description_text"],
        )
        Translation.objects.add_translation(
            f"program.{name_abbreviated}_{program_id}-website_description",
            default_message=p["description_text"],
        )


def reverse_create(apps, schema_editor):
    # No-op — matches 0141's own reverse: don't delete rows that may have
    # since picked up real operational data (has_benefit checks, etc.).
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0176_create_state_white_labels"),
    ]

    operations = [
        migrations.RunPython(create_or_fix_gap_tracking_programs, reverse_create),
    ]
