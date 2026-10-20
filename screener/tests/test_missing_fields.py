"""`missing_fields()` gates on values a calculator can't compute with, not just on nulls.

A null is an unanswered question: the program that needs it is skipped quietly. A value that
is present but unusable used to clear the gate and then either crash mid-calculation (an
unrecognized frequency leaves `monthly()`/`yearly()` with nothing assigned) or compute a
wrong answer silently (a blank income type counts as unearned income). Those now gate like a
null and are recorded in `Dependencies.malformed`, which `eligibility_results` reports.
"""

from django.test import SimpleTestCase, TestCase

from programs.programs.testing_fixtures.households import add_expense, add_income, add_member, make_screen
from programs.util import Dependencies, MalformedValue
from screener.models import Expense, IncomeStream


class TestIncomeStreamMissingFields(SimpleTestCase):
    def missing(self, **fields) -> Dependencies:
        values = {"type": "wages", "amount": 100, "frequency": "monthly", "hours_worked": None, **fields}
        return IncomeStream(**values).missing_fields()

    def test_a_complete_row_is_not_missing_anything(self):
        deps = self.missing()

        self.assertEqual(deps, set())
        self.assertEqual(deps.malformed, [])

    def test_every_frequency_the_screener_offers_is_supported(self):
        for frequency in ("monthly", "weekly", "biweekly", "semimonthly", "yearly"):
            with self.subTest(frequency=frequency):
                self.assertEqual(self.missing(frequency=frequency), set())
        self.assertEqual(self.missing(frequency="hourly", hours_worked=40), set())

    def test_nulls_are_missing_but_not_malformed(self):
        deps = self.missing(type=None, amount=None, frequency=None)

        self.assertEqual(deps, {"income_type", "income_amount", "income_frequency"})
        self.assertEqual(deps.malformed, [], "an unanswered field is not a defect")

    def test_an_unsupported_frequency_is_malformed(self):
        for frequency in ("", "fortnightly"):
            with self.subTest(frequency=frequency):
                deps = self.missing(frequency=frequency)

                self.assertEqual(deps, {"income_frequency"})
                self.assertEqual(
                    deps.malformed, [MalformedValue("income_frequency", frequency, deps.malformed[0].detail)]
                )

    def test_a_blank_type_is_malformed_rather_than_unearned(self):
        for income_type in ("", "   "):
            with self.subTest(income_type=income_type):
                deps = self.missing(type=income_type)

                self.assertEqual(deps, {"income_type"})
                self.assertEqual([m.field for m in deps.malformed], ["income_type"])

    def test_hourly_income_without_hours_gates_the_amount(self):
        """`_hour_to_month` multiplies by `hours_worked`; a null raised TypeError."""
        deps = self.missing(frequency="hourly", hours_worked=None)

        self.assertEqual(deps, {"income_amount"})
        self.assertEqual([m.field for m in deps.malformed], ["income_hours_worked"])


class TestExpenseMissingFields(SimpleTestCase):
    def missing(self, **fields) -> Dependencies:
        values = {"type": "rent", "amount": 100, "frequency": "monthly", **fields}
        return Expense(**values).missing_fields()

    def test_a_complete_row_is_not_missing_anything(self):
        self.assertEqual(self.missing(), set())

    def test_a_null_frequency_is_reported(self):
        """Expense never emitted a frequency token, so a null reached `yearly()`."""
        deps = self.missing(frequency=None)

        self.assertEqual(deps, {"expense_frequency"})
        self.assertEqual(deps.malformed, [])

    def test_hourly_is_not_an_expense_frequency(self):
        """Expense's `monthly()`/`yearly()` have no hourly branch."""
        deps = self.missing(frequency="hourly")

        self.assertEqual(deps, {"expense_frequency"})
        self.assertEqual([m.field for m in deps.malformed], ["expense_frequency"])

    def test_a_blank_type_is_malformed(self):
        deps = self.missing(type="")

        self.assertEqual(deps, {"expense_type"})
        self.assertEqual([m.field for m in deps.malformed], ["expense_type"])


class TestScreenMissingFieldsCarriesTheDetail(TestCase):
    def test_malformed_detail_survives_the_aggregation(self):
        """Screen and member aggregate their rows with `update()`; the detail has to come
        along or `eligibility_results` has nothing to report."""
        screen = make_screen(household_size=1)
        member = add_member(screen, age=30)
        add_income(member, 1_000, frequency="fortnightly")
        add_expense(member, 500, frequency="hourly")

        deps = screen.missing_fields()

        self.assertIn("income_frequency", deps)
        self.assertIn("expense_frequency", deps)
        self.assertEqual(sorted(m.field for m in deps.malformed), ["expense_frequency", "income_frequency"])


class TestDependencies(SimpleTestCase):
    def test_update_carries_malformed_detail_from_every_source(self):
        a, b = Dependencies(), Dependencies()
        a.add("income_type")
        a.report_malformed("income_type", "", "blank")
        b.add("expense_type")
        b.report_malformed("expense_type", "", "blank")

        deps = Dependencies()
        deps.update(a, b)

        self.assertEqual(deps, {"income_type", "expense_type"})
        self.assertEqual([m.field for m in deps.malformed], ["income_type", "expense_type"])

    def test_update_accepts_plain_iterables(self):
        deps = Dependencies()
        deps.update({"county"}, ["zipcode"])

        self.assertEqual(deps, {"county", "zipcode"})
        self.assertEqual(deps.malformed, [])

    def test_describe_names_the_field_and_value(self):
        self.assertEqual(
            MalformedValue("income_frequency", "fortnightly", "unsupported").describe(),
            "income_frequency='fortnightly' (unsupported)",
        )
