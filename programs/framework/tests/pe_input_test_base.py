"""Shared base for tests that assert the PolicyEngine payload."""

from django.test import TestCase
from screener.models import Screen, HouseholdMember, WhiteLabel, Expense, IncomeStream
from integrations.clients.policyengine.policy_engine import pe_input
from programs.framework.pe_dependencies.constants import MAIN_TAX_UNIT, SECONDARY_TAX_UNIT
from programs.programs.cross_white_label.eitc.base import Eitc
from programs.programs.cross_white_label.lifeline.tx import TxLifeline
from programs.programs.cross_white_label.snap.tx import TxSnap
from programs.programs.cross_white_label.tanf.tx import TxTanf
from programs.programs.cross_white_label.wic.tx import TxWic
from programs.programs.cross_white_label.ssi.tx import TxSsi
from programs.programs.cross_white_label.aca.tx import TxAca
from programs.programs.cross_white_label.csfp.tx import TxCsfp
from programs.programs.cross_white_label.medicaid.chip.tx import TxChip


class TxPeInputTestBase(TestCase):
    """Base class with shared test fixtures for TX pe_input tests."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data that doesn't change between tests."""
        cls.white_label = WhiteLabel.objects.create(name="Texas", code="tx", state_code="TX")

    def setUp(self):
        """Set up test screen with household members."""
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Travis County",
            household_size=3,
            household_assets=5000.00,
            completed=False,
        )

        # Head of household - 35 year old, disabled
        self.head = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=35,
            disabled=True,
            student=False,
        )

        # Spouse - 32 year old
        self.spouse = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="spouse",
            age=32,
            disabled=False,
            student=False,
        )

        # Child - 8 year old
        self.child = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="child",
            age=8,
            disabled=False,
            student=True,
        )

        # Add income streams
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="wages",
            amount=30000,
            frequency="yearly",
        )
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="selfEmployment",
            amount=5000,
            frequency="yearly",
        )
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="rental",
            amount=12000,
            frequency="yearly",
        )
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.spouse,
            type="pension",
            amount=8000,
            frequency="yearly",
        )
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.spouse,
            type="sSRetirement",
            amount=6000,
            frequency="yearly",
        )

        # Add expenses
        Expense.objects.create(screen=self.screen, type="childSupport", amount=500, frequency="monthly")
        Expense.objects.create(screen=self.screen, type="medical", amount=200, frequency="monthly")
