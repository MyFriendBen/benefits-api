"""KS tests."""

from unittest.mock import MagicMock, Mock

from django.test import TestCase

import programs.framework.pe_dependencies as dependency
from integrations.clients.policyengine.policy_engine import pe_input
from programs.framework.pe_base import PolicyEngineMembersCalculator
from programs.framework.pe_dependencies import member as member_deps
from programs.framework.pe_dependencies.household import KsStateCodeDependency
from programs.programs.cross_white_label.wic.base import Wic
from programs.programs.cross_white_label.wic.ks import KsWic
from screener.models import HouseholdMember, IncomeStream, Screen, WhiteLabel


class TestKsWicWiring(TestCase):
    """KsWic inherits the federal WIC calculator and adds only the KS state code."""

    def test_subclasses_federal_wic(self):
        self.assertTrue(issubclass(KsWic, Wic))
        self.assertTrue(issubclass(KsWic, PolicyEngineMembersCalculator))

    def test_uses_federal_wic_pe_name(self):
        self.assertEqual(KsWic.pe_name, "wic")

    def test_registers_under_the_ks_wic_program_code(self):
        self.assertEqual(KsWic.program_code, "ks_wic")

    def test_adds_ks_state_code_dependency(self):
        """WIC's FPG table branches on AK/HI vs. contiguous US, so the state code is
        load-bearing rather than decorative."""
        self.assertIn(KsStateCodeDependency, KsWic.pe_inputs)

    def test_inherits_all_federal_pe_inputs(self):
        for dep in Wic.pe_inputs:
            with self.subTest(dep=dep):
                self.assertIn(dep, KsWic.pe_inputs)

    def test_adds_nothing_but_the_state_code(self):
        """A local income subset added here would silently narrow KS's coverage relative to
        every other state — see ``MoWic``, which shipped exactly that."""
        self.assertEqual(
            [dep for dep in KsWic.pe_inputs if dep not in Wic.pe_inputs],
            [KsStateCodeDependency],
        )

    def test_inherits_the_wic_income_bundle(self):
        """
        Regression guard for WIC income-blindness.

        WIC's income term reads ``gov.usda.wic.income.sources``. Supplying none of those
        sources lets PE substitute an imputation that also satisfies the categorical branch,
        returning WIC as eligible at any reported income.
        """
        for dep in dependency.wic_income:
            with self.subTest(dep=dep):
                self.assertIn(dep, KsWic.pe_inputs)

    def test_inherits_the_receipt_contract(self):
        """WIC's adjunctive pathway reads SNAP/TANF receipt."""
        for dep in dependency.receipt_contract:
            with self.subTest(dep=dep):
                self.assertIn(dep, KsWic.pe_inputs)

    def test_keeps_federal_pe_outputs(self):
        self.assertEqual(KsWic.pe_outputs, Wic.pe_outputs)
        self.assertIn(member_deps.Wic, KsWic.pe_outputs)
        self.assertIn(member_deps.WicCategory, KsWic.pe_outputs)


class TestKsWicMemberValue(TestCase):
    """KsWic returns PolicyEngine's computed amount, not the zeroed federal categories."""

    def _make_calculator(self):
        calc = KsWic(Mock(), Mock(), Mock())
        calc._sim = MagicMock()
        return calc

    def _make_member(self, member_id=1):
        member = Mock()
        member.id = member_id
        return member

    def test_returns_policyengine_value(self):
        calc = self._make_calculator()
        calc.get_member_variable = Mock(return_value=1_560)

        self.assertEqual(calc.member_value(self._make_member()), 1_560)

    def test_returns_zero_when_policyengine_finds_member_ineligible(self):
        calc = self._make_calculator()
        calc.get_member_variable = Mock(return_value=0)

        self.assertEqual(calc.member_value(self._make_member()), 0)

    def test_does_not_use_zeroed_federal_wic_categories(self):
        """
        The federal base maps every category to $0. Falling back to that lookup shows
        eligible households $0 and the frontend's ``value > 0`` filter drops the program.
        """
        self.assertTrue(all(amount == 0 for amount in Wic.wic_categories.values()))

        calc = self._make_calculator()
        calc.get_member_variable = Mock(return_value=1_200)
        calc.get_member_dependency_value = Mock(return_value="INFANT")

        self.assertEqual(calc.member_value(self._make_member()), 1_200)


class TestKsWicPeInput(TestCase):
    """KsWic's dependencies land in the pe_input payload sent to PolicyEngine."""

    PERIOD = "2026"

    @classmethod
    def setUpTestData(cls):
        cls.white_label = WhiteLabel.objects.create(name="Kansas", code="ks", state_code="KS")

    def _calculator(self):
        """
        A KsWic *instance*, as the real request path builds it (screener/views.py).

        pe_input() reads ``program.year.period`` off each entry, so passing the class instead
        of an instance keys every value by the unbound ``pe_period`` property.
        """
        program = Mock()
        program.year.period = self.PERIOD
        return KsWic(self.screen, program, self.screen.missing_fields())

    def setUp(self):
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="67202",
            county="Sedgwick County",
            household_size=3,
            household_assets=0,
            completed=False,
        )
        self.head = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=29,
            pregnant=True,
        )
        self.child = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="child",
            age=3,
        )
        self.infant = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="child",
            age=0,
        )

    def test_sends_ks_state_code(self):
        result = pe_input(self.screen, [self._calculator()])
        household = result["household"]["households"]["household"]

        self.assertIn("state_code", household)
        self.assertIn("KS", household["state_code"].values())

    def test_includes_all_pe_input_fields(self):
        result = pe_input(self.screen, [self._calculator()])
        household = result["household"]
        spm_unit = household["spm_units"]["spm_unit"]
        people = household["people"]

        # SPM-level dependency: TANF, a WIC income source in its own right
        self.assertIn("tanf", spm_unit)

        head_id = str(self.head.id)
        self.assertIn("is_pregnant", people[head_id])
        self.assertIn("current_pregnancies", people[head_id])
        self.assertIn("age", people[head_id])

    def test_wic_alone_carries_every_income_source(self):
        """
        The payload is built from the WIC calculator *alone*. With siblings present this
        passes either way, which is how the income-blindness bug survived on states whose
        other programs happened to send ``irs_gross_income``.
        """
        result = pe_input(self.screen, [self._calculator()])
        head = result["household"]["people"][str(self.head.id)]
        spm_unit = result["household"]["spm_units"]["spm_unit"]

        for dep in dependency.wic_income:
            with self.subTest(field=dep.field):
                unit = spm_unit if dep in (dependency.spm.Tanf,) else head
                self.assertIn(dep.field, unit)

    def test_sends_reported_income_to_policyengine(self):
        """Reported income must reach PE as ``employment_income`` — what the 185% FPG test
        and the Medicaid/categorical chain read."""
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="wages",
            amount=1_500,
            frequency="monthly",
        )

        people = pe_input(self.screen, [self._calculator()])["household"]["people"]
        head = people[str(self.head.id)]

        self.assertIn("employment_income", head)
        self.assertEqual(head["employment_income"], {self.PERIOD: 18_000.0})

    def test_includes_pe_output_fields_for_every_member(self):
        result = pe_input(self.screen, [self._calculator()])
        people = result["household"]["people"]

        for member in (self.head, self.child, self.infant):
            with self.subTest(member=member.relationship):
                member_id = str(member.id)
                self.assertIn("wic", people[member_id])
                self.assertIn("wic_category", people[member_id])
