from django.test import TestCase
from screener.models import Screen, HouseholdMember, WhiteLabel, IncomeStream, Insurance
from programs.programs.policyengine.policy_engine import pe_input
from programs.programs.tx.pe.member import TxChip
from programs.programs.policyengine.calculators.constants import MAIN_TAX_UNIT, SECONDARY_TAX_UNIT


class TestMfb307TxChipIntegration(TestCase):
    """MFB-307 regression: Texas family of 4 with a 19-year-old qualifying relative."""

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Texas", code="tx", state_code="TX")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Travis County",
            household_size=4,
            household_assets=0,
            completed=False,
            last_tax_filing_year="2024",
        )
        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=41)
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=43800, frequency="yearly"
        )

        self.spouse = HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=39)
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.spouse, type="wages", amount=18000, frequency="yearly"
        )

        self.child19 = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=19, student=False)

        self.child7 = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=7)
        Insurance.objects.create(household_member=self.child7)

    def test_all_four_members_in_main_tax_unit(self):
        """With the fix, the 19yo stays in the main tax unit so household size is 4."""
        result = pe_input(self.screen, [TxChip])
        tax_units = result["household"]["tax_units"]
        people = result["household"]["people"]

        self.assertIn(MAIN_TAX_UNIT, tax_units)
        main_members = tax_units[MAIN_TAX_UNIT]["members"]
        self.assertEqual(len(main_members), 4)
        self.assertIn(str(self.child19.id), main_members)
        self.assertNotIn(SECONDARY_TAX_UNIT, tax_units)
        self.assertIn(str(self.child19.id), people)

