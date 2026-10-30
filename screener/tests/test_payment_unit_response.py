"""The results API carries each program's payment unit beside its member verdicts, so the
frontend can name the household as the eligible party without inferring it from an empty
member list."""

from unittest.mock import patch

from django.test import TestCase

from programs.framework.base import HOUSEHOLD, MEMBER
from programs.models import FederalPoveryLimit, Program, ProgramCategory
from programs.programs.testing_fixtures.households import add_income, add_member
from screener.models import Screen, WhiteLabel
from screener.views import eligibility_results


class TestPaymentUnitInResponse(TestCase):
    def setUp(self) -> None:
        self.co, _ = WhiteLabel.objects.get_or_create(code="co", defaults={"name": "Colorado", "state_code": "CO"})
        category = ProgramCategory.objects.new_program_category(
            white_label=None, external_name="payment_unit_response_test", icon=""
        )
        fpl = FederalPoveryLimit.objects.create(year="2025", period="2025")
        for name in ("federal_trump_account", "federal_ctc"):
            program = Program.objects.new_program("co", name)
            program.active = True
            program.has_calculator = True
            program.category = category
            program.year = fpl
            program.save()

        self.screen = Screen.objects.create(white_label=self.co, zipcode="80202", household_size=2, completed=False)
        add_income(add_member(self.screen, "headOfHousehold", age=30), 30_000, "wages", "yearly")
        add_member(self.screen, "child", age=1)

    def results(self) -> dict[str, dict]:
        with patch("screener.views.calc_pe_eligibility", return_value={"eligibility": {}, "_pe_data": {}}):
            data, _, _, _ = eligibility_results(self.screen)

        return {p["name_abbreviated"]: p for p in data}

    def test_a_member_unit_program_reports_the_unit_and_pays_its_members(self) -> None:
        trump_account = self.results()["federal_trump_account"]

        self.assertTrue(trump_account["eligible"])
        self.assertEqual(trump_account["payment_unit"], MEMBER)
        self.assertEqual([m["eligible"] for m in trump_account["members"]], [False, True])
        self.assertGreater(trump_account["members"][1]["value"], 0)

    def test_a_household_unit_program_reports_the_unit_and_keeps_its_verdicts(self) -> None:
        ctc = self.results()["federal_ctc"]

        self.assertTrue(ctc["eligible"])
        self.assertEqual(ctc["payment_unit"], HOUSEHOLD)
        self.assertEqual([m["eligible"] for m in ctc["members"]], [False, True])
        self.assertEqual([m["value"] for m in ctc["members"]], [0, 0])
        self.assertEqual(ctc["estimated_value"], ctc["household_value"])
