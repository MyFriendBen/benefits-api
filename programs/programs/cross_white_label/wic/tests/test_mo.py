"""MO tests."""

from screener.models import HouseholdMember
from screener.models import IncomeStream
from unittest.mock import MagicMock
from programs.framework.pe_dependencies.household import MoStateCodeDependency
from programs.programs.cross_white_label.wic.mo import MoWic
from unittest.mock import Mock
from programs.framework.pe_base import PolicyEngineMembersCalculator
from screener.models import Screen
from django.test import TestCase
from screener.models import WhiteLabel
from programs.programs.cross_white_label.wic.base import Wic
import programs.framework.pe_dependencies as dependency
from programs.framework.pe_dependencies import member as member_deps
from integrations.clients.policyengine.policy_engine import pe_input
from programs.framework.pe_dependencies import household
from programs.framework.pe_dependencies import member


class TestMoWicWiring(TestCase):
    """MoWic inherits the federal WIC calculator and adds only the MO state code."""

    def test_subclasses_federal_wic(self):
        self.assertTrue(issubclass(MoWic, Wic))
        self.assertTrue(issubclass(MoWic, PolicyEngineMembersCalculator))

    def test_uses_federal_wic_pe_name(self):
        """Inherited from the federal calculator, which stays on the ungated ``wic`` — see
        ``Wic``."""
        self.assertEqual(MoWic.pe_name, "wic")

    def test_adds_mo_state_code_dependency(self):
        self.assertIn(MoStateCodeDependency, MoWic.pe_inputs)

    def test_inherits_all_federal_pe_inputs(self):
        for dep in Wic.pe_inputs:
            self.assertIn(dep, MoWic.pe_inputs)

    def test_inherits_the_wic_income_bundle(self):
        """
        Regression guard for WIC income-blindness.

        WIC's income term reads ``gov.usda.wic.income.sources``, not the school-meals
        aggregate the federal calculator used to send. Supplying none of those sources let PE
        substitute an imputation and find the household categorically (adjunct) eligible, and
        since ``is_wic_eligible`` is ``demographic & (income_test | categorical) &
        nutritional_risk`` that alone returned WIC as eligible at any reported income.

        What the bundle covers is asserted in ``federal/pe/tests/test_wic.py``; this only pins
        that MO gets it.
        """
        for dep in dependency.wic_income:
            self.assertIn(dep, MoWic.pe_inputs)

    def test_does_not_re_add_a_local_income_fix(self):
        """
        ``MoWic`` shipped ``irs_gross_income`` as a partial fix while the federal calculator
        was still blind. The federal bundle supersedes it, and re-adding a local subset here
        would silently narrow MO's coverage relative to every other state.
        """
        self.assertEqual(
            [dep for dep in MoWic.pe_inputs if dep not in Wic.pe_inputs],
            [MoStateCodeDependency],
        )

    def test_keeps_federal_pe_outputs(self):
        self.assertEqual(MoWic.pe_outputs, Wic.pe_outputs)
        self.assertIn(member_deps.Wic, MoWic.pe_outputs)
        self.assertIn(member_deps.WicCategory, MoWic.pe_outputs)


class TestMoWicMemberValue(TestCase):
    """MoWic returns PolicyEngine's computed amount, not the zeroed federal categories."""

    def _make_calculator(self):
        calc = MoWic(Mock(), Mock(), Mock())
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
        The federal base class maps every category to $0. If MoWic ever falls back to that
        lookup, eligible households silently show $0 and get filtered out of results.
        """
        self.assertTrue(all(amount == 0 for amount in Wic.wic_categories.values()))

        calc = self._make_calculator()
        calc.get_member_variable = Mock(return_value=1_200)
        calc.get_member_dependency_value = Mock(return_value="INFANT")

        self.assertEqual(calc.member_value(self._make_member()), 1_200)


class TestMoWicPeInput(TestCase):
    """MoWic's dependencies land in the pe_input payload sent to PolicyEngine."""

    PERIOD = "2026"

    @classmethod
    def setUpTestData(cls):
        cls.white_label = WhiteLabel.objects.create(name="Missouri", code="mo", state_code="MO")

    def _calculator(self):
        """
        A MoWic *instance*, as the real request path builds it (screener/views.py).

        pe_input() reads ``program.year.period`` off each entry, so passing the class instead
        of an instance silently keys every value by the unbound ``pe_period`` property rather
        than the period string.
        """
        program = Mock()
        program.year.period = self.PERIOD
        return MoWic(self.screen, program, self.screen.missing_fields())

    def setUp(self):
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="65101",
            county="Cole County",
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

    def test_sends_mo_state_code(self):
        result = pe_input(self.screen, [self._calculator()])
        household = result["household"]["households"]["household"]

        self.assertIn("state_code", household)
        self.assertIn("MO", household["state_code"].values())

    def test_includes_all_pe_input_fields(self):
        result = pe_input(self.screen, [self._calculator()])
        household = result["household"]
        spm_unit = household["spm_units"]["spm_unit"]
        people = household["people"]

        # SPM-level dependency: TANF, a WIC income source in its own right
        self.assertIn("tanf", spm_unit)

        # Member-level dependencies
        head_id = str(self.head.id)
        self.assertIn("is_pregnant", people[head_id])
        self.assertIn("current_pregnancies", people[head_id])
        self.assertIn("age", people[head_id])

    def test_wic_alone_carries_every_income_source(self):
        """
        The payload is built from the WIC calculator *alone*, which is the only assertion
        that catches this regression. With siblings present it passes either way — and that
        is precisely why the bug survived: CO/MA/NC/TX screens run Medicaid and Head Start,
        both of which send ``irs_gross_income``, so WIC borrowed their inputs. MO shipped WIC
        as its only program and the omission became visible immediately.
        """
        result = pe_input(self.screen, [self._calculator()])
        head = result["household"]["people"][str(self.head.id)]
        spm_unit = result["household"]["spm_units"]["spm_unit"]

        for dep in dependency.wic_income:
            with self.subTest(field=dep.field):
                unit = spm_unit if dep in (dependency.spm.Tanf,) else head
                self.assertIn(dep.field, unit)

    def test_sends_reported_income_to_policyengine(self):
        """
        Reported income must reach PE as ``employment_income``, not just as the school-meals
        aggregate. This is what the 185% FPL test and the Medicaid/categorical chain read.
        """
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
            member_id = str(member.id)
            self.assertIn("wic", people[member_id])
            self.assertIn("wic_category", people[member_id])
