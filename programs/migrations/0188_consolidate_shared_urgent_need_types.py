# Consolidates UrgentNeedType onto shared rows.
#
# Every white label had its own row for the same semantic category: 100 rows
# across 8 white labels for 19 concepts, none shared. Nothing kept them
# consistent and they had drifted: child development was spelled three ways,
# baby supplies four, and CO had two "Food or groceries" rows. Adding a national
# resource to every white label meant hand-mapping one identifier per state.
#
# After this migration each concept is one row with white_label = NULL, shared by
# urgent needs in every white label. No white-label-scoped type remains.
#
# For each shared type, the first existing row in its SOURCES list becomes the
# shared row; urgent needs on the rest move to it and those rows are deleted. The
# first row is the one whose English name already matches the canonical name
# where one exists (wa_child_development, ks_baby_supplies, CO's unprefixed rows),
# so its curated translations survive instead of being machine-translated again.
#
# Verified safe alongside this change:
#   * The results page reads a type through need.category_type and filters on the
#     urgent need's white label (screener/urgent_needs.py), never the type's.
#   * The current-benefits endpoint scopes by the urgent needs' white label
#     (programs/views.py::UrgentNeedTypeViewSet).
#   * No frontend code reads a type's external_name; types render from icon and
#     translated name.

from typing import TYPE_CHECKING

from django.conf import settings
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps

from integrations.clients.google_translate import Translate, is_auto_translatable

if TYPE_CHECKING:
    from programs.models import UrgentNeedType

# shared external_name -> (icon, canonical English name)
SHARED_TYPES = {
    "food_or_groceries": ("food_groceries", "Food or groceries"),
    "job_resources": ("job_resources", "Job resources"),
    "child_development": ("child_development", "Concern about your child's development"),
    "baby_supplies": ("baby_supplies", "Diapers and other baby supplies"),
    "behavioral_health": ("behavioral_health", "Behavioral health"),
    "civil_legal_needs": ("legal_services", "Civil legal needs"),
    "managing_housing_costs": ("managing_housing", "Managing housing costs"),
    "family_planning": ("family_planning", "Family planning"),
    "low-cost_dental_care": ("dental_care", "Low-cost dental care"),
    "medical_expenses_and_debt": ("medical_expenses_and_debt", "Medical expenses and debt"),
    "aging_resources": ("aging", "Aging community resources"),
    "disability_resources": ("disability", "Disability resources"),
    "transportation": ("transportation", "Transportation"),
    "free_low_cost_health_care": ("free_health_care", "Free or lower cost health care"),
    "education_resources": ("job_resources", "Education and literacy"),
    "savings": ("savings", "Savings"),
    "funeral_burial_or_cremation_costs": ("default", "Funeral, burial, or cremation costs"),
    "veterans_resources": ("veteran_services", "Veterans resources"),
    "homeless_services": ("homeless_services", "Homeless services"),
}

# shared external_name -> the existing rows it absorbs, by external_name. The
# first row that exists becomes the shared row. external_name is globally
# unique, so no white label is needed to find a row.
SOURCES = {
    "food_or_groceries": [
        "food_or_groceries",
        "co_food_or_groceries",
        "il_food_or_groceries",
        "ks_food_or_groceries",
        "ma_food_or_groceries",
        "mo_food_or_groceries",
        "nc_food_or_groceries",
        "tx_food_or_groceries",
        "wa_food_or_groceries",
    ],
    "job_resources": [
        "job_resources",
        "il_job_resources",
        "ks_job_resources",
        "ma_job_resources",
        "mo_job_resources",
        "nc_job_resources",
        "tx_job_resources",
        "wa_job_resources",
    ],
    "child_development": [
        "wa_child_development",
        "childs_development",
        "il_child_development",
        "ks_child_development",
        "ma_childs_development",
        "mo_child_development",
        "nc_childs_development",
        "tx_child_development",
    ],
    "baby_supplies": [
        "ks_baby_supplies",
        "mo_baby_supplies",
        "wa_diapers_and_baby_supplies",
        "baby_supplies",
        "il_baby_supplies",
        "ma_baby_supplies",
        "nc_baby_supplies",
        "diapers_and_baby_supplies",
        "tx_baby_supplies",
    ],
    "behavioral_health": [
        "behavioral_health",
        "il_behavioral_health",
        "ks_behavioral_health",
        "ma_behavioral_health",
        "mo_behavioral_health",
        "nc_behavioral_health",
        "tx_behavioral_health",
        "wa_behavioral_health",
    ],
    "civil_legal_needs": [
        "civil_legal_needs",
        "il_civil_legal_needs",
        "ks_civil_legal_needs",
        "ma_civil_legal_needs",
        "mo_civil_legal_needs",
        "nc_civil_legal_needs",
        "tx_civil_legal_needs",
        "wa_legal_services",
    ],
    "managing_housing_costs": [
        "managing_housing_costs",
        "il_managing_housing_costs",
        "ks_managing_housing_costs",
        "ma_managing_housing_costs",
        "mo_managing_housing_costs",
        "nc_managing_housing_costs",
        "tx_managing_housing_cost",
        "wa_housing_rent_utilities",
    ],
    "family_planning": [
        "family_planning",
        "family_planning_or_birth_control",
        "il_family_planning",
        "ks_family_planning",
        "ma_family_planning",
        "mo_family_planning",
        "nc_family_planning",
        "tx_family_planning",
    ],
    "low-cost_dental_care": [
        "low-cost_dental_care",
        "il_low-cost_dental_care",
        "ma_low-cost_dental_care",
        "nc_low-cost_dental_care",
        "tx_low-cost_dental_care",
    ],
    "medical_expenses_and_debt": [
        "co_medical_expenses_and_debt",
        "il_medical_expenses_and_debt",
        "ks_medical_expenses_and_debt",
        "ma_medical_expenses_and_debt",
        "mo_medical_expenses_and_debt",
        "nc_medical_expenses_and_debt",
        "tx_medical_expenses_and_debt",
        "wa_medical_expenses_and_debt",
    ],
    "aging_resources": [
        "il_aging_resources",
        "ma_aging_resources",
        "tx_aging_resources",
        "wa_aging_resources",
    ],
    "disability_resources": [
        "il_disability_resources",
        "tx_disability_resources",
        "ma_disability_resources",
    ],
    "transportation": [
        "ks_transportation",
        "il_transportation",
        "mo_transportation",
    ],
    "free_low_cost_health_care": [
        "ks_free_low_cost_medical_care",
        "mo_free_low_cost_medical_care",
        "nc_free_low_cost_medical_care",
        # Present in some local databases with no urgent needs; not in staging or production.
        "fqhc_statewide_locator",
    ],
    "education_resources": [
        "ks_education_resources",
        "mo_education_resources",
    ],
    # CO's "Saving for college" and KS/MO's "Savings to improve financial
    # stability" deliberately merge under the plain "Savings".
    "savings": [
        "savings",
        "ks_savings",
        "mo_savings",
    ],
    "funeral_burial_or_cremation_costs": ["funeral_burial_or_cremation_costs"],
    "veterans_resources": ["ma_veterans_resources"],
    "homeless_services": ["nc_homeless_services"],
}

# An icon row that only a drifted type used. Deleted once nothing references it.
RETIRED_ICONS = ["Baby_supplies"]


def forward(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    # Real models rather than apps.get_model: new_urgent_need_type and
    # add_translation need parler internals unavailable on historical models.
    from programs.models import CategoryIconName, ProgramCategory, UrgentNeed, UrgentNeedType

    for shared_name, (icon_name, display_name) in SHARED_TYPES.items():
        rows = [
            row
            for row in (
                UrgentNeedType.objects.filter(external_name=external_name).first()
                for external_name in SOURCES[shared_name]
            )
            if row is not None
        ]

        if rows:
            shared, absorbed = rows[0], rows[1:]
        else:
            # A fresh database has no rows to promote; create the shared type so
            # urgent need configs naming it can import.
            shared = UrgentNeedType.objects.new_urgent_need_type(None, shared_name, None)
            absorbed = []

        # Absorbed rows go first: one of them may hold the shared external_name
        # (CO's baby_supplies when ks_baby_supplies is promoted), and the rename
        # below needs it free.
        for row in absorbed:
            UrgentNeed.objects.filter(category_type=row).update(category_type=shared)
            _delete_type(row)

        icon = CategoryIconName.objects.filter(name=icon_name).first()
        if icon is None:
            icon = CategoryIconName.objects.create(name=icon_name)

        shared.external_name = shared_name
        shared.white_label = None
        shared.icon = icon
        shared.save()

        _set_name(shared, display_name)

    # A row this migration didn't map would stay scoped to one white label and
    # silently keep its drifted name. Fail loudly instead, so the mapping is
    # extended rather than quietly incomplete.
    leftover = list(
        UrgentNeedType.objects.filter(white_label__isnull=False).values_list("white_label__code", "external_name")
    )
    if leftover:
        raise RuntimeError(
            "White-label-scoped urgent need types remain after consolidation; add them to SOURCES: "
            + ", ".join(f"{code}:{name}" for code, name in leftover)
        )

    for icon_name in RETIRED_ICONS:
        icon = CategoryIconName.objects.filter(name=icon_name).first()
        if icon is None:
            continue
        if UrgentNeedType.objects.filter(icon=icon).exists() or ProgramCategory.objects.filter(icon=icon).exists():
            continue
        icon.delete()


def _set_name(urgent_need_type: "UrgentNeedType", text: str) -> None:
    """
    Set the English display name and machine-translate the rest.

    Only touches a type whose English text actually differs. Rewriting a name in
    place replaces every other language with machine output: add_translation
    always marks English edited, and edit_translation_by_id's manual=False guard
    only spares a row that is both no_auto and edited, which these are not. For
    a type whose text is unchanged that would discard curated copy for nothing.
    """
    from translations.models import Translation

    name = urgent_need_type.name
    name.set_current_language(settings.LANGUAGE_CODE)
    if (name.text or "").strip() == text:
        return

    translation = Translation.objects.add_translation(label=name.label, default_message=text)

    if not is_auto_translatable(text):
        return

    try:
        translated = Translate().bulk_translate(Translate.languages, [text], strict=False).get(text, {})
    except Exception:
        # A translation outage must not fail the migration; English is already
        # saved and the rest can be filled in from the admin.
        return

    for lang, translated_text in translated.items():
        if lang == settings.LANGUAGE_CODE:
            continue
        Translation.objects.edit_translation_by_id(translation.id, lang, translated_text, manual=False)


def _delete_type(urgent_need_type: "UrgentNeedType") -> None:
    """
    Delete a type and the name Translation it leaves orphaned.

    name is a PROTECTed FK, so the type has to go first. The translation is then
    deleted only if nothing else references it: Translation is referenced by
    PROTECT from many models, so rather than enumerate them let the database
    decide. The savepoint keeps a ProtectedError from poisoning the migration's
    transaction.
    """
    from django.db import transaction
    from django.db.models import ProtectedError

    from translations.models import Translation

    translation_id = urgent_need_type.name_id

    urgent_need_type.delete()

    try:
        with transaction.atomic():
            Translation.objects.filter(id=translation_id).delete()
    except ProtectedError:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0187_alter_urgentneedtype_white_label"),
    ]

    operations = [
        # Reverse is a no-op rather than an inverse: consolidation is lossy. Many
        # rows collapse into one and their Translation rows are deleted, so the
        # per-white-label names, ids and any admin edits they carried cannot be
        # reconstructed — restore from a backup instead. A no-op (not a raise)
        # keeps the schema migration below it rollback-able.
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
