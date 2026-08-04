"""
Unit tests for the MO member-level PolicyEngine calculators.

Covers ``MoWic`` / ``mo_wic``, ``MoHeadStart`` / ``mo_head_start``, and
``MoEarlyHeadStart`` / ``mo_early_head_start`` — all "Fed (as-is / value varies)"
programs that wrap a federal PolicyEngine calculator and add only the MO state code.

MO WIC layers:

1. **Wiring** — ``MoWic`` subclasses the federal ``Wic`` calculator, is registered as
   ``mo_wic``, keeps ``pe_name = "wic"``, inherits every federal ``pe_input``, and adds
   ``MoStateCodeDependency`` so PolicyEngine resolves MO parameters.

2. **Value behavior** — ``MoWic.member_value`` returns PolicyEngine's computed WIC amount
   rather than the federal base class's ``wic_categories`` lookup. This is the regression
   guard that matters: ``Wic.wic_categories`` is all zeros, so inheriting ``member_value``
   unchanged would value every eligible member at $0 and the frontend's ``value > 0``
   filter would drop the program from results entirely.

3. **Income reaches PolicyEngine** — WIC needs its own income sources sent or PE substitutes an
   imputation and returns WIC as eligible at any reported income (verified live: $108k/yr came
   back eligible). MO carried a partial fix for this; MFB-1571 moved the complete ``wic_income``
   bundle onto the federal ``Wic``, which also fixed co_wic / nc_wic / ma_wic / tx_wic / il_wic.
   MO now adds only its state code, and the tests here assert that inheritance rather than a
   local copy.

MO Head Start / Early Head Start:

``MoHeadStart`` and ``MoEarlyHeadStart`` are thin wrappers on the federal ``HeadStart`` /
``EarlyHeadStart`` PE calculators that add only the MO state code — all eligibility and the
per-individual value come from PolicyEngine's ``head_start`` / ``early_head_start`` variables
with no MO-specific variance (mirrors ``TxHeadStart`` / ``KsHeadStart`` / ``MaHeadStart``).
The federal dependency logic is covered in
``policyengine/calculators/dependencies/tests/test_member.py`` and the MO state code in
``policyengine/calculators/dependencies/tests/test_household.py``; here we assert only the MO
wiring. The spec's dollar-value scenarios (Head Start: $16,314 per eligible child, $32,629 for
two children) are verified end-to-end against the live PolicyEngine API — see
``programs/programs/mo/head_start/spec.md``.
"""

from unittest.mock import MagicMock, Mock

from django.test import TestCase
from screener.models import HouseholdMember, IncomeStream, Screen, WhiteLabel

import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.federal.pe.member import Wic, HeadStart, EarlyHeadStart
from programs.programs.mo.pe import mo_member_calculators, mo_pe_calculators
from programs.programs.mo.pe.member import MoWic, MoHeadStart, MoEarlyHeadStart
from programs.programs.policyengine.calculators.base import PolicyEngineMembersCalculator
from programs.programs.policyengine.calculators.dependencies import member as member_deps
from programs.programs.policyengine.calculators.dependencies.household import MoStateCodeDependency
from programs.programs.policyengine.calculators.dependencies.member import (
    AgeDependency,
    PregnancyDependency,
    FosterCareDependency,
    Ssi,
    HeadStart as HeadStartOutput,
    EarlyHeadStart as EarlyHeadStartOutput,
)
from programs.programs.policyengine.calculators.registry import all_calculators, all_member_calculators
from programs.programs.policyengine.policy_engine import pe_input
from screener.serializers import _write_current_benefits
from screener.tests.helpers import seed_program


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

        MoWic used to carry ``irs_gross_income`` itself, as a partial fix while the federal
        base was still sending only ``school_meal_countable_income`` — a variable PolicyEngine's
        WIC tree never reads (``wic_countable_income`` sums ``gov.usda.wic.income.sources``
        instead). MFB-1571 moved the full bundle onto ``Wic``, so MO inherits it; the assertion
        is unchanged because what matters is that the inputs arrive, not which class declares
        them. Authoritative coverage lives in ``federal/pe/tests/test_wic.py``.
        """
        for dep in dependency.irs_gross_income:
            self.assertIn(dep, MoWic.pe_inputs)

    def test_inherits_full_wic_income_bundle(self):
        """MO adds only a state code now — every income source comes from the federal base."""
        for dep in dependency.wic_income:
            self.assertIn(dep, MoWic.pe_inputs)

    def test_declares_only_the_state_code_itself(self):
        """
        The inverse of the above: MO must not re-declare income inputs locally.

        A state subclass that keeps its own copy is how the CO/NC/MA/TX/IL gap survived — the
        fix lands on one class and the others silently keep the old set.
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

        # SPM-level dependencies: the WIC income sources that live on the SPM unit, plus the
        # reported-receipt flags the categorical test reads. school_meal_countable_income is
        # deliberately absent — PolicyEngine's WIC tree never reads it (MFB-1571).
        self.assertNotIn("school_meal_countable_income", spm_unit)
        self.assertIn("tanf", spm_unit)
        self.assertIn("receives_snap", spm_unit)
        self.assertIn("receives_tanf", spm_unit)

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

    def test_wic_alone_carries_every_income_source(self):
        """
        WIC must be self-sufficient in a request where it is the only program.

        PolicyEngine gets one merged household per screen, not one per program, so a
        calculator missing an input is masked whenever some sibling program happens to send
        the same field. That is why this bug hid for so long: CO/TX/MA/NC screens run Medicaid
        and Head Start, which both send irs_gross_income, while MO shipped WIC as its only
        program and the omission became visible immediately.

        Building the payload from the WIC calculator alone is the only way to assert real
        coverage — with siblings present, this passes either way.
        """
        result = pe_input(self.screen, [self._calculator()])
        household = result["household"]
        head = household["people"][str(self.head.id)]
        spm_unit = household["spm_units"]["spm_unit"]

        for dep in dependency.wic_income:
            field = dep.field
            unit = spm_unit if field in ("tanf",) else head
            self.assertIn(field, unit, f"{field} is missing from a WIC-only payload")

    def test_reported_snap_receipt_reaches_the_categorical_inputs(self):
        """
        Reported SNAP with no dollar amount — the common case — still has to reach PE.

        It travels as ``receives_snap``, not as a ``snap`` amount: PolicyEngine hands back
        whatever we put in the ``snap`` slot as this household's benefit, so inventing a
        figure there would corrupt the SNAP result for every program in the request.
        """
        seed_program(self.white_label, "mo_snap", base_program="snap")
        _write_current_benefits(self.screen, ["mo_snap"])

        spm_unit = pe_input(self.screen, [self._calculator()])["household"]["spm_units"]["spm_unit"]

        self.assertEqual(spm_unit["receives_snap"], {self.PERIOD: True})
        # WIC doesn't send the `snap` amount input at all — SNAP is not a WIC income source,
        # and the receipt flag is all the categorical test needs.
        self.assertNotIn("snap", spm_unit)


class TestMoHeadStartWiring(TestCase):
    """MoHeadStart (ages 3-5) registration and MO-specific pe_inputs handling."""

    def test_is_subclass_of_head_start(self):
        self.assertTrue(issubclass(MoHeadStart, HeadStart))

    def test_is_registered_in_mo_member_calculators(self):
        self.assertIn("mo_head_start", mo_member_calculators)
        self.assertEqual(mo_member_calculators["mo_head_start"], MoHeadStart)

    def test_is_registered_in_mo_pe_calculators(self):
        self.assertIn("mo_head_start", mo_pe_calculators)
        self.assertEqual(mo_pe_calculators["mo_head_start"], MoHeadStart)

    def test_pe_name_is_head_start(self):
        self.assertEqual(MoHeadStart.pe_name, "head_start")

    def test_pe_inputs_includes_mo_state_code(self):
        self.assertIn(MoStateCodeDependency, MoHeadStart.pe_inputs)

    def test_pe_inputs_preserve_federal_head_start_inputs(self):
        """The MO wrapper only appends the state code; it must not drop any federal input."""
        for dep in HeadStart.pe_inputs:
            self.assertIn(dep, MoHeadStart.pe_inputs)

    def test_pe_inputs_include_age_and_foster_pathways(self):
        """Ages 3-5 (age) and the foster-care categorical pathway per the spec."""
        self.assertIn(AgeDependency, MoHeadStart.pe_inputs)
        self.assertIn(FosterCareDependency, MoHeadStart.pe_inputs)

    def test_pe_inputs_include_categorical_benefit_signals(self):
        """SNAP / TANF / SSI feed PolicyEngine's categorical-eligibility determination."""
        self.assertIn(Ssi, MoHeadStart.pe_inputs)

    def test_pe_outputs_is_head_start_variable(self):
        self.assertEqual(MoHeadStart.pe_outputs, [HeadStartOutput])

    def test_mo_state_code_dependency_configured(self):
        self.assertEqual(MoStateCodeDependency.state, "MO")
        self.assertEqual(MoStateCodeDependency.field, "state_code")


class TestMoEarlyHeadStartWiring(TestCase):
    """MoEarlyHeadStart (birth-3 / pregnant) registration and MO-specific pe_inputs handling."""

    def test_is_subclass_of_early_head_start(self):
        self.assertTrue(issubclass(MoEarlyHeadStart, EarlyHeadStart))

    def test_is_registered_in_mo_member_calculators(self):
        self.assertIn("mo_early_head_start", mo_member_calculators)
        self.assertEqual(mo_member_calculators["mo_early_head_start"], MoEarlyHeadStart)

    def test_pe_name_is_early_head_start(self):
        self.assertEqual(MoEarlyHeadStart.pe_name, "early_head_start")

    def test_pe_inputs_includes_mo_state_code(self):
        self.assertIn(MoStateCodeDependency, MoEarlyHeadStart.pe_inputs)

    def test_pe_inputs_preserve_federal_early_head_start_inputs(self):
        for dep in EarlyHeadStart.pe_inputs:
            self.assertIn(dep, MoEarlyHeadStart.pe_inputs)

    def test_pe_inputs_include_age_pregnancy_and_foster_pathways(self):
        self.assertIn(AgeDependency, MoEarlyHeadStart.pe_inputs)
        self.assertIn(PregnancyDependency, MoEarlyHeadStart.pe_inputs)
        self.assertIn(FosterCareDependency, MoEarlyHeadStart.pe_inputs)

    def test_pe_outputs_is_early_head_start_variable(self):
        self.assertEqual(MoEarlyHeadStart.pe_outputs, [EarlyHeadStartOutput])

    def test_does_not_reuse_head_start_variable(self):
        """EHS must resolve PE's ``early_head_start`` variable, not the ``head_start`` one."""
        self.assertNotEqual(MoEarlyHeadStart.pe_name, "head_start")
