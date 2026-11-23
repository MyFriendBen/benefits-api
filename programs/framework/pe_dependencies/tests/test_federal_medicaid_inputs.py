"""The PolicyEngine inputs only the federal Medicaid base sends.

Each one carries a rule from the program-ops federal Medicaid base spec into PolicyEngine, so
each test names the household the rule is about.
"""

from django.test import TestCase

from programs.framework.pe_dependencies import member
from programs.models import Program
from screener.models import HouseholdMember, IncomeStream, Screen, WhiteLabel
from screener.serializers import _write_current_benefits
from screener.tests.helpers import seed_program


class FederalMedicaidInputsTestCase(TestCase):
    def setUp(self) -> None:
        self.white_label = WhiteLabel.objects.create(name="New Jersey", code="nj_test", state_code="NJ")
        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="07102", county="Essex County", household_size=1, completed=False
        )
        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=40)

    def income(self, member_row: HouseholdMember, income_type: str, monthly: int) -> None:
        IncomeStream.objects.create(
            screen=self.screen, household_member=member_row, type=income_type, amount=monthly, frequency="monthly"
        )

    def value(self, dependency_class: type, member_row: HouseholdMember):
        return dependency_class(self.screen, member_row, {}).value()


class TestRentalAndBoarderIncomeDependency(FederalMedicaidInputsTestCase):
    def test_boarder_payments_count_as_rental_income(self) -> None:
        """A household taking in a $900/month boarder has $10,800 a year of rental income."""
        self.income(self.head, "boarder", 900)
        self.assertEqual(self.value(member.RentalAndBoarderIncomeDependency, self.head), 10_800)

    def test_rental_and_boarder_income_add_up(self) -> None:
        self.income(self.head, "boarder", 900)
        self.income(self.head, "rental", 100)
        self.assertEqual(self.value(member.RentalAndBoarderIncomeDependency, self.head), 12_000)

    def test_fills_the_field_the_rental_input_fills(self) -> None:
        self.assertEqual(member.RentalAndBoarderIncomeDependency.field, member.RentalIncomeDependency.field)


class TestTaxableAlimonyIncomeDependency(FederalMedicaidInputsTestCase):
    def test_all_alimony_is_sent_as_taxable(self) -> None:
        """The spec counts all alimony, since the screener has no divorce date."""
        self.income(self.head, "alimony", 500)
        self.assertEqual(self.value(member.TaxableAlimonyIncomeDependency, self.head), 6_000)
        self.assertEqual(member.TaxableAlimonyIncomeDependency.field, "taxable_alimony_income")


class TestOwnSsdiDisabilityDependency(FederalMedicaidInputsTestCase):
    def test_own_ssdi_is_a_disability_finding(self) -> None:
        self.income(self.head, "sSDisability", 1_200)
        self.assertTrue(self.value(member.OwnSsdiDisabilityDependency, self.head))

    def test_disability_checkboxes_alone_are_not(self) -> None:
        """A 40-year-old who ticks every disability box, with no SSDI, is not found disabled."""
        self.head.disabled = True
        self.head.long_term_disability = True
        self.head.visually_impaired = True
        self.head.save()
        self.assertFalse(self.value(member.OwnSsdiDisabilityDependency, self.head))

    def test_other_social_security_benefits_are_not(self) -> None:
        for income_type in ("sSDependent", "sSSurvivor", "sSRetirement"):
            self.income(self.head, income_type, 800)
        self.assertFalse(self.value(member.OwnSsdiDisabilityDependency, self.head))

    def test_another_members_ssdi_is_not(self) -> None:
        spouse = HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=45)
        self.income(spouse, "sSDisability", 1_200)
        self.assertFalse(self.value(member.OwnSsdiDisabilityDependency, self.head))
        self.assertTrue(self.value(member.OwnSsdiDisabilityDependency, spouse))


class TestOwnSsdiNotEngagedInSgaDependency(FederalMedicaidInputsTestCase):
    def test_ssdi_recipient_is_kept_out_of_the_earnings_screen(self) -> None:
        """An SSDI recipient earning $2,500/month still has their disability finding."""
        self.income(self.head, "sSDisability", 1_200)
        self.income(self.head, "wages", 2_500)
        self.assertIs(self.value(member.OwnSsdiNotEngagedInSgaDependency, self.head), False)

    def test_everyone_else_is_left_to_policyengine(self) -> None:
        self.income(self.head, "wages", 2_500)
        self.assertIsNone(self.value(member.OwnSsdiNotEngagedInSgaDependency, self.head))


class TestTakesUpOwnReportedSsiDependency(FederalMedicaidInputsTestCase):
    def test_member_with_an_ssi_amount_takes_it_up(self) -> None:
        self.income(self.head, "sSI", 943)
        self.assertTrue(self.value(member.TakesUpOwnReportedSsiDependency, self.head))

    def test_member_without_an_ssi_amount_does_not(self) -> None:
        self.assertFalse(self.value(member.TakesUpOwnReportedSsiDependency, self.head))

    def test_ssi_tile_without_an_amount_is_not_receipt(self) -> None:
        """Where the shared input holds take-up open for the tile, this one doesn't."""
        seed_program(self.white_label, "nj_test_ssi")
        Program.objects.filter(white_label=self.white_label, name_abbreviated="nj_test_ssi").update(base_program="ssi")
        _write_current_benefits(self.screen, ["nj_test_ssi"])
        self.assertTrue(self.value(member.TakesUpSsiIfEligibleDependency, self.head))
        self.assertFalse(self.value(member.TakesUpOwnReportedSsiDependency, self.head))

    def test_fills_the_shared_take_up_field(self) -> None:
        self.assertEqual(member.TakesUpOwnReportedSsiDependency.field, member.TakesUpSsiIfEligibleDependency.field)
        self.assertEqual(
            member.TakesUpOwnReportedSsiDependency.min_pe_version,
            member.TakesUpSsiIfEligibleDependency.min_pe_version,
        )
