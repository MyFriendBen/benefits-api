"""Tests for the dependency gate's value validation (Screen/HouseholdMember/
IncomeStream/Expense `missing_fields`).

The gate historically only asked `is None`, so a present-but-unusable value — a blank
income type, a frequency `monthly()`/`yearly()` can't convert, an hourly row with no
hours — passed straight through to the calculators, where it either raised mid-calculation
(500ing the whole eligibility response) or silently produced a wrong number. These tests
pin the stricter behavior: such fields are treated as missing AND recorded in
`Dependencies.malformed` so the results view can report them and flag `missing_programs`.
"""

from django.test import TestCase

from screener.models import Screen, HouseholdMember, WhiteLabel, IncomeStream, Expense


class MissingFieldsTestBase(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Test County",
            household_size=1,
            household_assets=0,
            completed=False,
        )
        self.head = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=35,
            student=False,
            pregnant=False,
            visually_impaired=False,
            disabled=False,
            long_term_disability=False,
        )


class TestIncomeStreamMissingFields(MissingFieldsTestBase):
    def test_complete_row_reports_nothing(self):
        income = IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=2000, frequency="monthly"
        )

        missing = income.missing_fields()

        self.assertEqual(set(missing), set())
        self.assertEqual(missing.malformed, [])

    def test_null_values_are_missing_but_not_malformed(self):
        """An unanswered question is ordinary partial input — gated, but reported quietly."""
        income = IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type=None, amount=None, frequency=None
        )

        missing = income.missing_fields()

        self.assertEqual(set(missing), {"income_type", "income_amount", "income_frequency"})
        self.assertEqual(missing.malformed, [])

    def test_blank_type_is_missing_and_malformed(self):
        """A blank type cleared the old `is None` gate, then fell through to the unearned
        catch-all in calc_gross_income — counted as unearned income, no error."""
        income = IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="   ", amount=100, frequency="monthly"
        )

        missing = income.missing_fields()

        self.assertIn("income_type", missing)
        self.assertEqual([m.field for m in missing.malformed], ["income_type"])

    def test_unsupported_frequency_is_missing_and_malformed(self):
        """yearly() matches no branch for this value and raises UnboundLocalError."""
        income = IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=100, frequency="fortnightly"
        )

        missing = income.missing_fields()

        self.assertIn("income_frequency", missing)
        self.assertEqual([m.field for m in missing.malformed], ["income_frequency"])
        self.assertEqual(missing.malformed[0].value, "fortnightly")

    def test_every_supported_frequency_is_accepted(self):
        for frequency in IncomeStream.SUPPORTED_FREQUENCIES:
            with self.subTest(frequency=frequency):
                income = IncomeStream(
                    screen=self.screen,
                    household_member=self.head,
                    type="wages",
                    amount=100,
                    frequency=frequency,
                    hours_worked=40,
                )
                self.assertNotIn("income_frequency", income.missing_fields())

    def test_hourly_without_hours_worked_is_gated(self):
        """_hour_to_month multiplies by hours_worked, which is nullable and was never part
        of the dependency vocabulary — an hourly row with no hours raised TypeError."""
        income = IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="wages",
            amount=20,
            frequency="hourly",
            hours_worked=None,
        )

        missing = income.missing_fields()

        self.assertIn("income_amount", missing)
        self.assertEqual([m.field for m in missing.malformed], ["income_hours_worked"])

    def test_hourly_with_hours_worked_is_fine(self):
        income = IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="wages",
            amount=20,
            frequency="hourly",
            hours_worked=40,
        )

        missing = income.missing_fields()

        self.assertEqual(set(missing), set())
        self.assertEqual(missing.malformed, [])


class TestExpenseMissingFields(MissingFieldsTestBase):
    def test_complete_row_reports_nothing(self):
        expense = Expense.objects.create(
            screen=self.screen, household_member=self.head, type="rent", amount=1200, frequency="monthly"
        )

        missing = expense.missing_fields()

        self.assertEqual(set(missing), set())
        self.assertEqual(missing.malformed, [])

    def test_null_frequency_is_now_reported(self):
        """frequency was absent from Expense's field list entirely, so a null reached
        Expense.yearly() and raised UnboundLocalError."""
        expense = Expense.objects.create(
            screen=self.screen, household_member=self.head, type="rent", amount=1200, frequency=None
        )

        missing = expense.missing_fields()

        self.assertIn("expense_frequency", missing)
        self.assertEqual(missing.malformed, [])

    def test_hourly_is_not_a_valid_expense_frequency(self):
        """Expense.monthly()/yearly() have no hourly branch, unlike IncomeStream's."""
        expense = Expense.objects.create(
            screen=self.screen, household_member=self.head, type="rent", amount=1200, frequency="hourly"
        )

        missing = expense.missing_fields()

        self.assertIn("expense_frequency", missing)
        self.assertEqual([m.field for m in missing.malformed], ["expense_frequency"])

    def test_blank_type_is_missing_and_malformed(self):
        expense = Expense.objects.create(
            screen=self.screen, household_member=self.head, type="", amount=1200, frequency="monthly"
        )

        missing = expense.missing_fields()

        self.assertIn("expense_type", missing)
        self.assertEqual([m.field for m in missing.malformed], ["expense_type"])


class TestScreenMissingFieldsAggregation(MissingFieldsTestBase):
    def test_malformed_detail_propagates_from_nested_rows(self):
        """Screen.missing_fields merges through HouseholdMember -> IncomeStream and
        Screen -> Expense; the malformed detail must survive both hops."""
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=100, frequency="fortnightly"
        )
        Expense.objects.create(
            screen=self.screen, household_member=self.head, type="rent", amount=1200, frequency="hourly"
        )

        missing = self.screen.missing_fields()

        self.assertIn("income_frequency", missing)
        self.assertIn("expense_frequency", missing)
        self.assertEqual(sorted(m.field for m in missing.malformed), ["expense_frequency", "income_frequency"])

    def test_clean_screen_has_no_malformed_detail(self):
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=2000, frequency="monthly"
        )

        missing = self.screen.missing_fields()

        self.assertEqual(missing.malformed, [])
