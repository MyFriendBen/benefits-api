"""Tests for the shared additional-resources selection (`screener.urgent_needs`).

This function is the single filter behind both the results page's Additional Resources
tab and the list Benji is handed. The reason it is shared is that Benji's prompt
describes its output as the COMPLETE set of resources this person has — so a resource
the page shows and Benji doesn't know about (or the reverse) is a wrong answer that
none of the assistant's guardrails can catch, because nothing downstream knows what the
other side rendered.

`test_assistant_context.py` covers the assistant's *serialization* of this list. What
is covered here is the selection itself, plus the mapping that ties the category rows
admins create to the Screen columns the immediate-needs step writes.
"""

from unittest.mock import patch

from django.test import TestCase

from programs.models import UrgentNeedCategory
from screener.assistant import CONTEXT_PREFETCH, _build_context
from screener.models import Screen, WhiteLabel
from screener.views import urgent_need_results
from screener.tests.helpers import seed_urgent_need
from screener.urgent_needs import (
    NEED_CATEGORY_FIELDS,
    eligible_urgent_needs,
    selected_need_categories,
)


class SelectedNeedCategoriesTests(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", household_size=1, completed=True
        )

    def test_nothing_ticked_selects_nothing(self):
        self.assertEqual(selected_need_categories(self.screen), [])

    def test_ticked_categories_are_returned(self):
        self.screen.needs_food = True
        self.screen.needs_legal_services = True

        self.assertEqual(sorted(selected_need_categories(self.screen)), ["food", "legal services"])

    def test_every_category_name_maps_to_a_real_screen_field(self):
        """The map is the only thing tying `UrgentNeedCategory.name` (admin-written DB
        rows) to the `needs_*` columns (a migration). A typo on either side makes a
        category invisible on both the results page and in Benji's context, with no
        error anywhere — this is what turns that into a failure."""
        for category, field in NEED_CATEGORY_FIELDS.items():
            with self.subTest(category=category):
                self.assertTrue(hasattr(self.screen, field), f"Screen has no field {field} (for {category!r})")

    def test_every_category_in_the_database_is_mapped(self):
        """Categories are created through the Django admin, so this is the drift guard
        that fires when someone adds one without a Screen column to select it by."""
        unmapped = sorted(
            UrgentNeedCategory.objects.exclude(name__in=NEED_CATEGORY_FIELDS).values_list("name", flat=True)
        )

        self.assertEqual(unmapped, [], f"UrgentNeedCategory rows with no NEED_CATEGORY_FIELDS entry: {unmapped}")


class EligibleUrgentNeedsTests(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            household_size=2,
            completed=True,
            needs_food=True,
        )

    def names(self, program_data=None) -> list[str]:
        return [n.external_name for n in eligible_urgent_needs(self.screen, program_data or [])]

    def test_no_categories_ticked_short_circuits(self):
        """Returns before touching the database or building `missing_fields()`, which is
        the common case: half of completed screens tick two categories or fewer."""
        self.screen.needs_food = False
        self.screen.save()
        seed_urgent_need(self.white_label, "pantry", category="food", name="Pantry")

        with self.assertNumQueries(0):
            self.assertEqual(eligible_urgent_needs(self.screen, []), [])

    def test_selects_resources_in_a_ticked_category(self):
        seed_urgent_need(self.white_label, "pantry", category="food", name="Pantry")
        seed_urgent_need(self.white_label, "shelter", category="housing", name="Shelter")

        self.assertEqual(self.names(), ["pantry"])

    def test_a_resource_in_two_categories_appears_once(self):
        """`type_short` is many-to-many and the filter is an `__in`, so a resource listed
        under two ticked categories would join twice without the `distinct()`."""
        self.screen.needs_housing_help = True
        self.screen.save()
        need = seed_urgent_need(self.white_label, "both", category="food", name="Food and Shelter")
        housing, _ = UrgentNeedCategory.objects.get_or_create(name="housing")
        need.type_short.add(housing)

        self.assertEqual(self.names(), ["both"])

    def test_resource_without_a_category_type_is_excluded(self):
        """`category_type` supplies the heading and the icon the card renders, and the
        results page has always required it (`category_type__isnull=False`)."""
        need = seed_urgent_need(self.white_label, "pantry", category="food", name="Pantry")
        need.category_type = None
        need.save()

        self.assertEqual(self.names(), [])

    def test_expense_gated_resource_is_excluded_without_that_expense(self):
        seed_urgent_need(
            self.white_label,
            "rent_help",
            category="food",
            name="Rent Help",
            expense_types=("rent",),
        )

        self.assertEqual(self.names(), [])

    def test_unknown_calculator_name_drops_the_resource_and_reports_it(self):
        """A `UrgentNeedFunction` row naming a calculator that no longer exists is a
        config error. It used to raise `KeyError`, which was pinned here on the grounds
        that silently dropping the resource would surface as an empty tab "and nothing
        in Sentry".

        The reporting is now the thing that carries that concern, so the failure mode no
        longer has to. Raising took down the whole Additional Resources tab AND every
        assistant start for the entire white label over one stale admin row; dropping the
        single affected resource keeps the two consumers in agreement — which is the
        invariant this module exists to hold — and `_report_missing_calculator` makes the
        typo visible. Same shape as `screener.assistant._warning_messages`.
        """
        need = seed_urgent_need(self.white_label, "pantry", category="food", name="Pantry")
        need.functions.create(name="no_such_calculator")

        with patch("screener.urgent_needs.capture_message") as capture:
            self.assertEqual(self.names(), [])

        capture.assert_called_once()
        message = capture.call_args.args[0]
        self.assertIn("no_such_calculator", message)
        self.assertIn(str(need.pk), message)

    def test_a_broken_calculator_does_not_take_the_other_resources_with_it(self):
        """The reason dropping beats raising: one stale row is not an outage."""
        broken = seed_urgent_need(self.white_label, "pantry", category="food", name="Pantry")
        broken.functions.create(name="no_such_calculator")
        seed_urgent_need(self.white_label, "hot_meals", category="food", name="Hot Meals")

        with patch("screener.urgent_needs.capture_message"):
            self.assertEqual(self.names(), ["hot_meals"])

    def test_a_resource_with_no_calculators_is_still_always_shown(self):
        """ "No gates declared" is a real configuration and must stay distinct from
        "gates we could not resolve" — the fix must not collapse the two."""
        seed_urgent_need(self.white_label, "hot_meals", category="food", name="Hot Meals")

        self.assertEqual(self.names(), ["hot_meals"])


def _resources_for(screen: Screen) -> list[dict]:
    reloaded = Screen.objects.prefetch_related(*CONTEXT_PREFETCH).get(pk=screen.pk)
    return _build_context(reloaded)["additional_resources"]


class OrderMatchesTheResultsPageTests(TestCase):
    """The two consumers must hand out the same order, in every language.

    This is the assertion behind the docstring claim that "the first one on the list"
    means the same organization to Benji and to the person reading the tab. It is tested
    across the seam rather than on either side, because both sides looked individually
    correct while disagreeing: `Needs.tsx` sorts ONLY by the English category name, with
    a stable sort, so it preserves whatever order the API sent within a category — and an
    assistant-side sort by `(translated category, name)` therefore diverged twice over,
    within a category always and between categories on any non-English screen.
    """

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            household_size=2,
            completed=True,
            needs_food=True,
            needs_housing_help=True,
        )
        # Two resources in one category, deliberately seeded Zebra-then-Alpha so that
        # insertion order and alphabetical order disagree — that gap is where a
        # within-category sort on one side and a stable sort on the other diverge.
        # The categories are "Food" and "Shelter", translated below to "Verduras" and
        # "Refugio", which invert their relative order in Spanish. That inversion is what
        # catches an assistant-side sort keyed on the translated name.
        self.food = seed_urgent_need(
            self.white_label, "pantry_z", category="food", category_type="Food", name="Zebra Pantry"
        )
        self.food_a = seed_urgent_need(
            self.white_label, "pantry_a", category="food", category_type="Food", name="Alpha Pantry"
        )
        self.shelter = seed_urgent_need(
            self.white_label, "shelter", category="housing", category_type="Shelter", name="Night Shelter"
        )

    def page_order(self) -> list[str]:
        """What `Needs.tsx` would render: the API's order, stably sorted by English
        category. Reproduced here rather than asserted against the component, because the
        component lives in another repo."""
        screen = Screen.objects.get(pk=self.screen.pk)
        needs = urgent_need_results(screen, [])
        return [
            n["name"]["default_message"] for n in sorted(needs, key=lambda n: n["category_type"]["default_message"])
        ]

    def assistant_order(self) -> list[str]:
        screen = Screen.objects.prefetch_related(*CONTEXT_PREFETCH).get(pk=self.screen.pk)
        return [r["name"] for r in _build_context(screen)["additional_resources"]]

    def test_orders_match_in_english(self):
        self.assertEqual(self.assistant_order(), self.page_order())

    def test_within_a_category_the_api_order_is_what_both_sides_use(self):
        """The page cannot re-order inside a category, so the API's order IS the page's
        order — which is why the shared function has to be the one that decides it."""
        order = self.page_order()

        self.assertEqual(order.index("Alpha Pantry"), order.index("Zebra Pantry") - 1)
        self.assertEqual(self.assistant_order(), order)

    def test_orders_match_on_a_non_english_screen(self):
        """The page sorts by `default_message`, which `screener.views.default_message`
        pins to LANGUAGE_CODE — so category order stays ENGLISH whatever the household
        reads in. Ordering the assistant's list by the translated name put the two in
        different orders outright."""
        for need, spanish in (
            (self.food, "Despensa Zebra"),
            (self.food_a, "Despensa Alpha"),
            (self.shelter, "Refugio"),
        ):
            need.name.set_current_language("es")
            need.name.text = spanish
            need.name.save()
        # "Vivienda" < "Comida" is false, but "Alimentos" < "Vivienda" is true in both —
        # so translate the CATEGORIES to invert their relative order against English
        # ("Food" < "Shelter", but "Refugio" < "Verduras").
        self.food.category_type.name.set_current_language("es")
        self.food.category_type.name.text = "Verduras"
        self.food.category_type.name.save()
        self.shelter.category_type.name.set_current_language("es")
        self.shelter.category_type.name.text = "Refugio"
        self.shelter.category_type.name.save()
        self.screen.request_language_code = "es"
        self.screen.save()

        assistant = self.assistant_order()

        # Spanish names, but ENGLISH category order — Food before Shelter.
        self.assertEqual(assistant, ["Despensa Alpha", "Despensa Zebra", "Refugio"])
        # And the page agrees: its category key is English too, so it groups Food
        # before Shelter exactly as the assistant does.
        self.assertEqual([r["name"] for r in _resources_for(self.screen)], assistant)
