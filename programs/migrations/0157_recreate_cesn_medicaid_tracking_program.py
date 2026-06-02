from django.db import migrations


# Re-create the CESN Medicaid tracking-only program.
#
# History: cesn_medicaid was created in 0137_create_tracking_programs, then
# removed — audited out of the has-benefits step in 0142 and deleted in
# 0143_delete_cesn_chp_medicaid (alongside cesn_chp). cesn_chp stays removed
# because CHP+ is captured per-member via member.insurance.chp; CESN Medicaid,
# however, has no insurance step (CESN does not collect health insurance), so it
# must be captured at the household level via the "already has benefits" step.
#
# This program is tracking-only (has_calculator=False). It exists so a CESN user
# can declare they already receive Medicaid; that declaration sets Screen.has_medicaid,
# which drives presumptive eligibility for Utility Bill Pay (cesn_ubp) — see MFB-1110.
#
# NOTE: cesn_chp is intentionally NOT re-added.

PROGRAM = {
    "white_label_code": "cesn",
    "name_abbreviated": "cesn_medicaid",
    "name_text": "Health First Colorado (Medicaid)",
    "description_text": "Free / low-cost public health insurance",
    "base_program": "medicaid",
}


def create_cesn_medicaid(apps, schema_editor):
    """
    Mirrors programs/migrations/0137_create_tracking_programs.py. Uses real model
    imports because Program.objects.new_program() handles the Translation FK
    creation that historical models can't support.
    """
    from programs.models import Program
    from screener.models import WhiteLabel
    from translations.models import Translation

    p = PROGRAM

    # Skip if white label doesn't exist (e.g. in CI test databases).
    if not WhiteLabel.objects.filter(code=p["white_label_code"]).exists():
        return

    existing = Program.objects.filter(
        white_label__code=p["white_label_code"],
        name_abbreviated=p["name_abbreviated"],
    ).first()

    if existing:
        program = existing
        program.active = False
        program.has_calculator = False
        program.show_in_has_benefits_step = True
        program.base_program = p.get("base_program")
        program.save()
    else:
        program = Program.objects.new_program(
            white_label=p["white_label_code"],
            name_abbreviated=p["name_abbreviated"],
        )
        program.active = False
        program.has_calculator = False
        program.show_in_has_benefits_step = True
        program.base_program = p.get("base_program")
        program.save()

    # add_translation calls set_current_language() before saving, which is required
    # for parler to write to the correct language row in a migration context.
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


def delete_cesn_medicaid(apps, schema_editor):
    Program = apps.get_model("programs", "Program")
    Program.objects.filter(
        white_label__code=PROGRAM["white_label_code"],
        name_abbreviated=PROGRAM["name_abbreviated"],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0156_deactivate_co_my_spark"),
    ]

    operations = [
        migrations.RunPython(create_cesn_medicaid, delete_cesn_medicaid),
    ]
