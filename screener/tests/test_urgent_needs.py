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

from django.test import TestCase

from programs.models import UrgentNeedCategory
from screener.models import Screen, WhiteLabel
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

    def test_unknown_calculator_name_raises_rather_than_silently_dropping(self):
        """A `UrgentNeedFunction` row naming a calculator that no longer exists is a
        config error, and `urgent_need_functions[...]` has always raised on it. Pinned
        so the extraction didn't quietly turn it into a missing resource — that failure
        would show up as an empty tab for real households and nothing in Sentry."""
        need = seed_urgent_need(self.white_label, "pantry", category="food", name="Pantry")
        need.functions.create(name="no_such_calculator")

        with self.assertRaises(KeyError):
            eligible_urgent_needs(self.screen, [])
