"""
`/api/screens/` refuses a relationship, income, expense or frequency value no white label offers,
and still accepts any value a saved screen already holds when it is edited.
"""

from typing import Any

from django.contrib.auth.models import Permission
from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient, APITestCase

from authentication.models import User
from screener.allowed_values import accepted_values, unaccepted_values
from screener.models import Expense, HouseholdMember, IncomeStream, Screen, WhiteLabel
from screener.serializers import ScreenSerializer


def member(relationship: str = "headOfHousehold", **income: Any) -> dict[str, Any]:
    streams = [{"category": "employment", "type": "wages", "amount": 1000, "frequency": "monthly", **income}]
    return {"relationship": relationship, "age": 40, "has_income": True, "income_streams": streams}


def expense(**fields: Any) -> dict[str, Any]:
    return {"type": "rent", "amount": 900, "frequency": "monthly", **fields}


class AcceptedValuesTests(SimpleTestCase):
    def test_values_set_by_code_are_accepted(self) -> None:
        accepted = accepted_values()

        self.assertIn("headOfHousehold", accepted["relationship"])
        self.assertIn("electricity", accepted["expense_type"])

    def test_an_expense_is_never_hourly(self) -> None:
        """Income may be hourly; `Expense.monthly()` can't convert an hourly expense."""
        self.assertIn("hourly", accepted_values()["income_frequency"])
        self.assertEqual(set(unaccepted_values({"expenses": [expense(frequency="hourly")]})), {"expenses[0].frequency"})

    def test_a_value_any_white_label_offers_is_accepted_everywhere(self) -> None:
        # Only Colorado offers these; the Get Ahead apps and test screens have no config of their own.
        self.assertIn("nurturingFutures", accepted_values()["income_type"])
        self.assertEqual(unaccepted_values({"household_members": [member(type="nurturingFutures")]}), {})

    def test_blank_answers_are_left_to_the_calculators(self) -> None:
        attrs = {
            "household_members": [member(relationship="", category=None, type="", frequency=None)],
            "expenses": [expense(type=None, frequency="")],
        }

        self.assertEqual(unaccepted_values(attrs), {})

    def test_each_unknown_answer_is_named_by_its_path(self) -> None:
        attrs = {
            "household_members": [
                member(),
                member(relationship="sibling", category="hasIncome", type="other", frequency="fortnightly"),
            ],
            "expenses": [expense(), expense(type="auto", frequency="daily")],
        }

        errors = unaccepted_values(attrs)

        self.assertEqual(
            set(errors),
            {
                "household_members[1].relationship",
                "household_members[1].income_streams[0].category",
                "household_members[1].income_streams[0].type",
                "household_members[1].income_streams[0].frequency",
                "expenses[1].type",
                "expenses[1].frequency",
            },
        )
        self.assertIn("'sibling' isn't a relationship the screener offers", errors["household_members[1].relationship"])
        self.assertIn("sisterOrBrother", errors["household_members[1].relationship"])


class ScreenApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.white_label = WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")
        cls.user = User.objects.create_user(email_or_cell="values@example.com", password="password")
        cls.user.user_permissions.add(
            Permission.objects.get(codename="add_screen"), Permission.objects.get(codename="change_screen")
        )

    def setUp(self) -> None:
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _body(self, members: list[dict[str, Any]], expenses: list[dict[str, Any]], **fields: Any) -> dict[str, Any]:
        return {
            "white_label": "co",
            "request_language_code": "en-us",
            "household_members": members,
            "expenses": expenses,
            "current_benefits": [],
            **fields,
        }

    def _post(self, members: list[dict[str, Any]], expenses: list[dict[str, Any]], **fields: Any) -> Response:
        return self.client.post("/api/screens/", self._body(members, expenses, **fields), format="json")

    def _put(self, screen: Screen, members: list[dict[str, Any]], expenses: list[dict[str, Any]]) -> Response:
        return self.client.put(f"/api/screens/{screen.uuid}/", self._body(members, expenses), format="json")

    def test_a_screen_of_offered_values_saves(self) -> None:
        response = self._post([member(), member("spouse", type="sSI")], [expense(), expense(type="heating")])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_an_unknown_value_is_refused_and_nothing_saves(self) -> None:
        response = self._post([member(), member("unrelated")], [expense()])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn("household_members[1].relationship", response.data)
        self.assertFalse(Screen.objects.exists())

    def test_the_language_is_not_checked(self) -> None:
        """A returning user's browser can still hold `zh` (now `zh-hans`) and send it on a new screen."""
        response = self._post([member()], [], request_language_code="zh")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def _saved_screen_with_retired_answers(self) -> Screen:
        """A screen from before some options were retired, as tens of thousands are."""
        screen = Screen.objects.create(white_label=self.white_label, completed=True, request_language_code="zh")
        head = HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=40)
        HouseholdMember.objects.create(screen=screen, relationship="unrelated", age=30)
        IncomeStream.objects.create(
            screen=screen, household_member=head, type="disabilityMedicaid", amount=100, frequency="monthly"
        )
        Expense.objects.create(screen=screen, type="auto", amount=300, frequency="monthly")
        return screen

    def test_editing_a_screen_keeps_the_answers_it_already_holds(self) -> None:
        screen = self._saved_screen_with_retired_answers()
        members = [member(type="disabilityMedicaid", category=None), member("unrelated")]

        response = self.client.put(
            f"/api/screens/{screen.uuid}/",
            {**self._body(members, [expense(type="auto")]), "request_language_code": "zh"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(
            set(HouseholdMember.objects.filter(screen=screen).values_list("relationship", flat=True)),
            {"headOfHousehold", "unrelated"},
        )

    def test_editing_a_screen_refuses_a_new_unknown_answer(self) -> None:
        screen = self._saved_screen_with_retired_answers()

        response = self._put(screen, [member(), member("sibling")], [expense(type="creditCard")])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual(set(response.data), {"household_members[1].relationship", "expenses[0].type"})

    def test_a_replayed_screen_skips_the_check(self) -> None:
        """`pull_screen` copies a stored screen as it is."""
        body = self._body([member("unrelated")], [expense(type="auto")])
        serializer = ScreenSerializer(data=body, validate_location=False, validate_values=False)

        self.assertTrue(serializer.is_valid(), serializer.errors)
