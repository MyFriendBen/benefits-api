"""Which additional resources a screen qualifies for.

The results page and Benji read the same resources, so they read them through the
same function. `screener.views.urgent_need_results` serializes what comes back for
the browser (translation dicts the frontend resolves itself); `screener.assistant`
serializes it for the system prompt (flat text, already in the screen's language).
Only the SELECTION lives here — the two consumers disagree about shape, and forcing
one shape on both is what would make this an abstraction instead of a fact.

Sharing the selection is the point. The list Benji is handed is described to the
model in closed-world terms — "this is the complete set of additional resources this
person has" — so a resource the page shows and Benji doesn't know about makes Benji
wrong in the way its guardrails cannot catch. A second implementation of these
filters would drift, silently, and the drift would only ever be visible to a user
mid-conversation. (Same reasoning as the `order_by("id")` both sides of the document
list now share.)
"""

from typing import Iterable, Optional

from django.conf import settings
from parler.models import TranslationDoesNotExist

from programs.models import UrgentNeed
from programs.urgent_needs import urgent_need_functions
from programs.urgent_needs.base import UrgentNeedFunction
from programs.util import Dependencies

from .models import Screen

# `UrgentNeedCategory.name` -> the `Screen` field that says the household asked to see
# that category. The category names are DB rows written by admins, and the fields are
# columns, so this map is the only thing tying them together — a category whose name is
# not a key here is silently invisible to everyone.
#
# `test_urgent_needs.py` asserts every UrgentNeedCategory in the database resolves to a
# real Screen field, which is what turns "someone added a category and nothing showed
# up" into a failing test instead of an empty tab.
NEED_CATEGORY_FIELDS = {
    "food": "needs_food",
    "baby supplies": "needs_baby_supplies",
    "housing": "needs_housing_help",
    "mental health": "needs_mental_health_help",
    "child dev": "needs_child_dev_help",
    "funeral": "needs_funeral_help",
    "family planning": "needs_family_planning_help",
    "job resources": "needs_job_resources",
    "dental care": "needs_dental_care",
    "legal services": "needs_legal_services",
    "veteran services": "needs_veteran_services",
    "savings": "needs_college_savings",
    "disability resources": "needs_disability_resources",
    "aging resources": "needs_aging_resources",
    "homeless services": "needs_homeless_services",
    "free low cost medical care": "needs_free_low_cost_medical_care",
    "transportation": "needs_transportation",
    "medical expenses and debt": "needs_medical_expenses_and_debt",
}


def selected_need_categories(screen: Screen) -> list[str]:
    """The resource categories this household ticked at the immediate-needs step."""
    return [category for category, field in NEED_CATEGORY_FIELDS.items() if getattr(screen, field, False)]


def _translations_prefetch(prefix: str, fields: Iterable[str]) -> list[str]:
    return [f"{prefix}{f}__translations" for f in fields]


def _english(translation) -> str:
    """A Translation's text in the DEFAULT language, for ordering only.

    English rather than the screen's language on purpose. The results page sorts its
    resource cards by `default_message(need.category_type.name)`, which
    `screener.views.default_message` pins to `settings.LANGUAGE_CODE` — so the page's
    category order is the ENGLISH order whatever language the household is reading in.
    Ordering here by the translated name would put the two lists in different orders on
    every non-English screen.
    """
    if translation is None:
        return ""
    try:
        translation.set_current_language(settings.LANGUAGE_CODE)
        return (translation.text or "").strip().casefold()
    except (TranslationDoesNotExist, AttributeError):
        return ""


def eligible_urgent_needs(
    screen: Screen,
    program_data,
    missing_dependencies: Optional[Dependencies] = None,
) -> list[UrgentNeed]:
    """The additional resources this screen qualifies for, as model instances.

    `program_data` is the eligibility results, and a handful of resource calculators
    read it — each one only ever touches `name_abbreviated` and `eligible` (e.g.
    "show SNAP application help if they're SNAP-eligible"), so a caller that has
    eligibility snapshot rows rather than full serialized results can pass those
    without recomputing anything.

    `missing_dependencies` is accepted because both callers already build it for
    something else (`screen.missing_fields()` walks every member, income stream and
    expense). Left out, it is computed here.
    """
    categories = selected_need_categories(screen)
    if not categories:
        return []

    if missing_dependencies is None:
        missing_dependencies = screen.missing_fields()

    resources = (
        UrgentNeed.objects.prefetch_related(
            "functions",
            "counties",
            "required_expense_types",
            *_translations_prefetch("", UrgentNeed.objects.translated_fields),
            # The category's own name is a Translation too, and both callers render it.
            # Without this the page issued two queries per resource to show a heading it
            # already had the id for.
            "category_type__name__translations",
        )
        .select_related("category_type")
        .filter(
            type_short__name__in=categories,
            category_type__isnull=False,
            active=True,
            white_label=screen.white_label,
        )
        .distinct()
    )

    eligible = []
    for need in resources:
        calculators = [urgent_need_functions[f.name] for f in need.functions.all()]
        if not calculators:
            calculators = [UrgentNeedFunction]

        if all(Calculator(screen, need, missing_dependencies, program_data).calc() for Calculator in calculators):
            eligible.append(need)

    # Ordering is part of what is shared, not a detail each consumer picks.
    #
    # `Needs.tsx` sorts the cards by English category name with `Array.prototype.sort`,
    # which is stable — so within a category the page shows whatever order the API sent,
    # and that order was previously a queryset with no `order_by`, i.e. arbitrary and
    # free to differ between two requests. Sorting here by the same English category key
    # the page uses makes the page's own sort a no-op, so both consumers end up with
    # byte-identical order: "the first one on the list" names the same organization to
    # Benji and to the person reading the tab, in every language.
    #
    # It also makes `MAX_ADDITIONAL_RESOURCES` deterministic. Capping an arbitrarily
    # ordered list would drop an arbitrary subset, so above the cap the two lists would
    # differ in membership rather than merely in order.
    #
    # `id` last so two resources with the same category and name still order stably.
    eligible.sort(key=lambda need: (_english(need.category_type.name), _english(need.name), need.id))
    return eligible
