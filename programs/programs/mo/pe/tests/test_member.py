"""
Unit tests for the MO member-level PolicyEngine calculators (``MoWic`` / ``mo_wic``).

MO WIC is a "Fed (as-is)" program: PolicyEngine's WIC tree has no MO-specific branching
(the only state-conditional logic picks AK/HI vs. contiguous-US FPG tables, and MO is
contiguous), so the coverage here is wiring plus the one MFB-side behavior MoWic changes
relative to its federal parent.

Three layers:

1. **Wiring** — ``MoWic`` subclasses the federal ``Wic`` calculator, is registered as
   ``mo_wic``, keeps ``pe_name = "wic"``, inherits every federal ``pe_input``, and adds
   ``MoStateCodeDependency`` so PolicyEngine resolves MO parameters.

2. **Value behavior** — ``MoWic.member_value`` returns PolicyEngine's computed WIC amount
   rather than the federal base class's ``wic_categories`` lookup. This is the regression
   guard that matters: ``Wic.wic_categories`` is all zeros, so inheriting ``member_value``
   unchanged would value every eligible member at $0 and the frontend's ``value > 0``
   filter would drop the program from results entirely.

3. **Income reaches PolicyEngine** — ``MoWic`` adds the ``irs_gross_income`` bundle the federal
   inputs omit. Without it PE supplies none of WIC's own income sources, substitutes an
   imputation, and returns WIC as eligible at any reported income (verified live: $108k/yr came
   back eligible). This is a *partial* fix covering wage-type income only — see the gap note on
   ``MoWic.pe_inputs``. co_wic / nc_wic / ma_wic / tx_wic remain affected and are tracked
   separately.
"""

from unittest.mock import MagicMock, Mock

from django.test import TestCase
from screener.models import HouseholdMember, IncomeStream, Screen, WhiteLabel

import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.federal.pe.member import Wic
from programs.programs.mo.pe import mo_member_calculators, mo_pe_calculators
from programs.programs.mo.pe.member import MoWic
from programs.programs.policyengine.calculators.base import PolicyEngineMembersCalculator
from programs.programs.policyengine.calculators.dependencies import member as member_deps
from programs.programs.policyengine.calculators.dependencies.household import MoStateCodeDependency
from programs.programs.policyengine.calculators.registry import all_calculators, all_member_calculators
from programs.programs.policyengine.policy_engine import pe_input


class TestMoWicWiring(TestCase):
    """MoWic inherits the federal WIC calculator and adds only the MO state code."""

    def test_subclasses_federal_wic(self):
        self.assertTrue(issubclass(MoWic, Wic))
        self.assertTrue(issubclass(MoWic, PolicyEngineMembersCalculator))

    def test_uses_federal_wic_pe_name(self):
        self.assertEqual(MoWic.pe_name, "wic")

    def test_registered_as_mo_wic(self):
        self.assertIs(mo_member_calculators["mo_wic"], MoWic)
        self.assertIs(mo_pe_calculators["mo_wic"], MoWic)

    def test_registered_in_global_registry(self):
        """A calculator missing from the registry never runs — screener/views.py iterates it."""
        self.assertIs(all_member_calculators["mo_wic"], MoWic)
        self.assertIs(all_calculators["mo_wic"], MoWic)

    def test_adds_mo_state_code_dependency(self):
        self.assertIn(MoStateCodeDependency, MoWic.pe_inputs)

    def test_inherits_all_federal_pe_inputs(self):
        for dep in Wic.pe_inputs:
            self.assertIn(dep, MoWic.pe_inputs)

    def test_sends_gross_income_so_wage_income_binds(self):
        """
        Regression guard for WIC income-blindness.

        The federal inputs carry only ``school_meal_countable_income``, which PolicyEngine's WIC
        tree never reads — ``wic_countable_income`` sums ``gov.usda.wic.income.sources`` instead.
        Supplying none of those sources lets PE substitute its own imputation and find the
        household categorically (adjunct) eligible, and since ``is_wic_eligible`` is
        ``demographic & (income_test | categorical) & nutritional_risk`` that alone returns WIC as
        eligible at any reported income.
        """
        for dep in dependency.irs_gross_income:
            self.assertIn(dep, MoWic.pe_inputs)

    def test_wic_income_source_coverage_is_partial(self):
        """
        Pins the known gap so it can't drift unnoticed.

        ``irs_gross_income`` supplies 5 of the 24 variables in PE's ``gov.usda.wic.income.sources``.
        If this starts failing, either the bundle or WIC's source list changed — re-check the gap
        note on ``MoWic.pe_inputs`` before adjusting the number.
        """
        wic_income_sources = {
            "employment_income",
            "self_employment_income",
            "military_service_income",
            "dividend_income",
            "interest_income",
            "gi_cash_assistance",
            "social_security",
            "ssi",
            "tanf",
            "pension_income",
            "survivor_benefits",
            "financial_assistance",
            "miscellaneous_income",
            "veterans_benefits",
            "unemployment_compensation",
            "strike_benefits",
            "rental_income",
            "retirement_distributions",
            "alimony_income",
            "child_support_received",
            "disability_benefits",
            "workers_compensation",
            "educational_assistance",
            "railroad_benefits",
        }
        sent = {dep.field for dep in MoWic.pe_inputs if hasattr(dep, "field")}

        self.assertEqual(
            sent & wic_income_sources,
            {
                "employment_income",
                "self_employment_income",
                "social_security",
                "unemployment_compensation",
                "rental_income",
            },
        )

    def test_federal_wic_alone_would_not_send_gross_income(self):
        """Pins *why* the bundle is added here: the federal parent omits it (unlike ``Medicaid``)."""
        self.assertFalse(
            any(dep in Wic.pe_inputs for dep in dependency.irs_gross_income),
            "federal Wic now sends gross income — MoWic's override and its comment are redundant",
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

        # SPM-level dependency
        self.assertIn("school_meal_countable_income", spm_unit)

        # Member-level dependencies
        head_id = str(self.head.id)
        self.assertIn("is_pregnant", people[head_id])
        self.assertIn("current_pregnancies", people[head_id])
        self.assertIn("age", people[head_id])

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
