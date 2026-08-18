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

3. **Income reaches PolicyEngine** — WIC's income sources now come from the federal
   ``Wic``'s ``wic_income`` bundle, which every state inherits. ``MoWic`` briefly carried a
   partial ``irs_gross_income`` fix of its own; that is superseded and must not come back.
   Which sources the bundle covers, and why, is pinned once in
   ``federal/pe/tests/test_wic.py``; the assertions here only check that MO inherits it and
   that a reported wage actually lands in the payload.

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

MO SSI:

``MoSsi`` is the same shape — federal ``Ssi`` plus the MO state code, mirroring
``KsSsi`` / ``TxSsi`` / ``WaSsi``. SSI has no MO-specific variance (PE's ``ssi`` reads only
``gov.ssa.ssi.*``, and PE models state supplements for NM/SC/TX only), so the tests here pin
the wiring and the two inherited inputs that are load-bearing rather than boilerplate:
``MeetsSsiDisabilityCriteriaDependency`` (without it, disabled non-aged/non-blind applicants
get ``ssi: 0``) and ``SsiCountableResourcesDependency`` (the resource limit is a
hard cutoff). The dependency values themselves are covered in
``policyengine/calculators/dependencies/tests/test_member.py``.

MO MSP:

``MoMsp`` wraps the federal ``Msp`` calculator and adds the MO state code plus the state's
Medicaid inputs, mirroring ``KsMsp`` / ``TxMsp`` / ``IlMsp``. Missouri's MSP delta is
eligibility-only and reduces to one thing PE can act on: the state code resolves the
asset-test-applies parameter, which is ``true`` for MO. The income tiers are the federal
floor. Tests here pin that wiring and the inputs each spec scenario depends on; the tier
and dollar outcomes are PolicyEngine's and were verified live at the pinned model version
1.786.5 — see ``programs/programs/mo/msp/spec.md``.
"""

from unittest.mock import MagicMock, Mock

from django.test import TestCase
from screener.models import HouseholdMember, IncomeStream, Screen, WhiteLabel

import programs.framework.pe_dependencies as dependency
from programs.programs.federal.pe.member import (
    Wic,
    HeadStart,
    EarlyHeadStart,
    Medicaid,
    Msp,
    Ssi as FederalSsi,
)
from programs.programs.mo.pe import mo_member_calculators, mo_pe_calculators
from programs.programs.mo.pe.member import MoWic, MoHeadStart, MoEarlyHeadStart, MoMsp, MoSsi
from programs.framework.pe_base import PolicyEngineMembersCalculator
from programs.framework.pe_dependencies import member as member_deps
from programs.framework.pe_dependencies.household import MoStateCodeDependency
from programs.framework.pe_dependencies.member import (
    IsBlindDependency,
    MeetsSsiDisabilityCriteriaDependency,
    Ssi,
    SsiCountableResourcesDependency,
    SsiEarnedIncomeDependency,
    SsiIfTakesUp,
    SsiUnearnedIncomeDependency,
)
from integrations.clients.policyengine.registry import all_calculators, all_member_calculators
from integrations.clients.policyengine.policy_engine import pe_input


class TestMoWicWiring(TestCase):
    """MoWic inherits the federal WIC calculator and adds only the MO state code."""

    def test_subclasses_federal_wic(self):
        self.assertTrue(issubclass(MoWic, Wic))
        self.assertTrue(issubclass(MoWic, PolicyEngineMembersCalculator))

    def test_uses_federal_wic_pe_name(self):
        """Inherited from the federal calculator, which stays on the ungated ``wic`` — see
        ``Wic``."""
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


class TestMoHeadStartWiring(TestCase):
    """
    MO-specific wiring for Head Start (ages 3-5) and Early Head Start (birth-3 /
    pregnant). Both are thin wrappers on the federal calculators, adding only the
    MO state code.

    The shared contract (pe_name, pe_outputs, no federal input dropped, exactly one
    state code matching the slug, no ``member_value`` override) is asserted once for
    all registered subclasses in ``federal/pe/tests/test_head_start.py``.
    """

    def test_head_start_is_registered_as_mo_head_start(self):
        self.assertIs(mo_member_calculators["mo_head_start"], MoHeadStart)
        self.assertIs(mo_pe_calculators["mo_head_start"], MoHeadStart)

    def test_head_start_pe_inputs_includes_mo_state_code(self):
        self.assertTrue(issubclass(MoHeadStart, HeadStart))
        self.assertIn(MoStateCodeDependency, MoHeadStart.pe_inputs)

    def test_early_head_start_is_registered_as_mo_early_head_start(self):
        self.assertIs(mo_member_calculators["mo_early_head_start"], MoEarlyHeadStart)

    def test_early_head_start_pe_inputs_includes_mo_state_code(self):
        self.assertTrue(issubclass(MoEarlyHeadStart, EarlyHeadStart))
        self.assertIn(MoStateCodeDependency, MoEarlyHeadStart.pe_inputs)


class TestMoSsiWiring(TestCase):
    """MoSsi inherits the federal SSI calculator and adds only the MO state code."""

    def test_is_subclass_of_federal_ssi(self):
        self.assertTrue(issubclass(MoSsi, FederalSsi))
        self.assertTrue(issubclass(MoSsi, PolicyEngineMembersCalculator))

    def test_pe_name_is_the_would_be_ssi_variable(self):
        self.assertEqual(MoSsi.pe_name, "ssi_if_takes_up")

    def test_is_registered_as_mo_ssi(self):
        self.assertIs(mo_member_calculators["mo_ssi"], MoSsi)
        self.assertIs(mo_pe_calculators["mo_ssi"], MoSsi)

    def test_is_registered_in_global_registry(self):
        """A calculator missing from the registry never runs — screener/views.py iterates it."""
        self.assertIs(all_member_calculators["mo_ssi"], MoSsi)
        self.assertIs(all_calculators["mo_ssi"], MoSsi)

    def test_pe_inputs_includes_mo_state_code(self):
        self.assertIn(MoStateCodeDependency, MoSsi.pe_inputs)

    def test_pe_inputs_preserve_federal_ssi_inputs(self):
        """The MO wrapper only appends the state code; it must not drop any federal input."""
        for dep in FederalSsi.pe_inputs:
            self.assertIn(dep, MoSsi.pe_inputs)

    def test_adds_nothing_but_the_state_code(self):
        """
        Pins "Δ for MO: None". PE's ``ssi`` reads only ``gov.ssa.ssi.*`` params and PE models
        SSI state supplements for NM/SC/TX only, so any extra MO input here would be a new
        claim about state variance that needs its own justification.
        """
        self.assertEqual(set(MoSsi.pe_inputs) - set(FederalSsi.pe_inputs), {MoStateCodeDependency})

    def test_pe_inputs_include_disability_criteria(self):
        """
        Regression guard. PE 1.715.2+ stopped inferring SSI disability from
        ``is_disabled`` / reported receipt, so dropping this input returns ``ssi: 0`` for a
        disabled non-aged, non-blind applicant.
        """
        self.assertIn(MeetsSsiDisabilityCriteriaDependency, MoSsi.pe_inputs)
        self.assertIn(IsBlindDependency, MoSsi.pe_inputs)

    def test_pe_inputs_include_resource_and_income_tests(self):
        """The resource limit is a hard cutoff, and earned/unearned split drives the exclusion stack."""
        self.assertIn(SsiCountableResourcesDependency, MoSsi.pe_inputs)
        self.assertIn(SsiEarnedIncomeDependency, MoSsi.pe_inputs)
        self.assertIn(SsiUnearnedIncomeDependency, MoSsi.pe_inputs)
        self.assertIn(Ssi, MoSsi.pe_inputs)

    def test_pe_outputs_is_the_would_be_ssi_variable(self):
        """
        ssi_if_takes_up, not ssi: takes_up_ssi_if_eligible is False for anyone not
        reporting SSI, which zeroes ``ssi`` for exactly the people mo_ssi is for.
        """
        self.assertEqual(MoSsi.pe_outputs, [SsiIfTakesUp])

    def test_does_not_override_member_value(self):
        """
        MoSsi returns PolicyEngine's computed dollar amount via the inherited
        ``member_value``. Unlike WIC, there is no zeroed category table to work around,
        so an override here would mean hardcoding an FBR that stops tracking SSA COLAs.
        """
        self.assertIs(MoSsi.member_value, PolicyEngineMembersCalculator.member_value)


class TestMoSsiPeInput(TestCase):
    """MoSsi's dependencies land in the pe_input payload sent to PolicyEngine."""

    PERIOD = "2026"

    @classmethod
    def setUpTestData(cls):
        cls.white_label = WhiteLabel.objects.create(name="Missouri", code="mo", state_code="MO")

    def setUp(self):
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="65101",
            county="Cole County",
            household_size=1,
            household_assets=1_500,
            completed=False,
        )
        self.head = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=67,
            disabled=True,
        )

    def _calculator(self):
        program = Mock()
        program.year.period = self.PERIOD
        return MoSsi(self.screen, program, self.screen.missing_fields())

    def test_sends_mo_state_code(self):
        household = pe_input(self.screen, [self._calculator()])["household"]["households"]["household"]

        self.assertIn("state_code", household)
        self.assertIn("MO", household["state_code"].values())

    def test_sends_ssi_eligibility_inputs_for_the_member(self):
        people = pe_input(self.screen, [self._calculator()])["household"]["people"]
        head = people[str(self.head.id)]

        for field in ("age", "is_blind", "is_disabled", "ssi_countable_resources", "ssi"):
            self.assertIn(field, head)

    def test_splits_household_assets_into_countable_resources(self):
        people = pe_input(self.screen, [self._calculator()])["household"]["people"]
        head = people[str(self.head.id)]

        self.assertEqual(head["ssi_countable_resources"], {self.PERIOD: 1_500})

    def test_sends_earned_and_unearned_income_separately(self):
        """
        SSI's exclusion stack treats the two differently ($20 general, then $65 + 1/2 of
        remaining earned), so collapsing them would understate the benefit.
        """
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="wages",
            amount=500,
            frequency="monthly",
        )
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="sSA",
            amount=300,
            frequency="monthly",
        )

        people = pe_input(self.screen, [self._calculator()])["household"]["people"]
        head = people[str(self.head.id)]

        self.assertEqual(head["ssi_earned_income"], {self.PERIOD: 6_000})
        self.assertEqual(head["ssi_unearned_income"], {self.PERIOD: 3_600})

    def test_requests_ssi_output_for_the_member(self):
        people = pe_input(self.screen, [self._calculator()])["household"]["people"]

        self.assertIn("ssi", people[str(self.head.id)])


class TestMoMspWiring(TestCase):
    """
    ``MoMsp`` inherits the federal ``Msp`` calculator and adds the MO state code plus the
    state's Medicaid inputs, mirroring ``KsMsp`` / ``TxMsp`` / ``IlMsp``.

    MSP's income tiers are the federal floor in Missouri, so the state code is the only
    MO-keyed input. It is load-bearing rather than boilerplate: it resolves PolicyEngine's
    ``...eligibility.asset.applies`` parameter, which is ``true`` for MO. Dropping it would
    silently stop applying the resource test and report over-resourced households as
    eligible — the exact failure Scenario 4 guards.
    """

    def test_is_subclass_of_federal_msp(self):
        self.assertTrue(issubclass(MoMsp, Msp))
        self.assertTrue(issubclass(MoMsp, PolicyEngineMembersCalculator))

    def test_pe_name_is_msp(self):
        self.assertEqual(MoMsp.pe_name, "msp")

    def test_is_registered_as_mo_medicare_savings(self):
        self.assertIs(mo_member_calculators["mo_medicare_savings"], MoMsp)
        self.assertIs(mo_pe_calculators["mo_medicare_savings"], MoMsp)

    def test_is_registered_in_global_registry(self):
        """A calculator missing from the registry never runs — screener/views.py iterates it."""
        self.assertIs(all_member_calculators["mo_medicare_savings"], MoMsp)
        self.assertIs(all_calculators["mo_medicare_savings"], MoMsp)

    def test_pe_inputs_includes_mo_state_code(self):
        """Resolves the MO asset-test-applies parameter — the one genuine MO delta."""
        self.assertIn(MoStateCodeDependency, MoMsp.pe_inputs)

    def test_pe_inputs_preserve_federal_msp_inputs(self):
        """The MO wrapper only appends; it must not drop any federal input."""
        for dep in Msp.pe_inputs:
            self.assertIn(dep, MoMsp.pe_inputs)

    def test_pe_inputs_include_medicaid_inputs(self):
        """
        QI eligibility requires the applicant NOT be Medicaid-eligible, and the asset test
        reads ``ssi_countable_resources`` supplied by the Medicaid input set. Without these,
        QI would never exclude Medicaid-eligible applicants (Scenario 7) and the asset test
        would see $0 resources (Scenario 4).
        """
        for dep in Medicaid.pe_inputs:
            self.assertIn(dep, MoMsp.pe_inputs)

    def test_adds_nothing_but_state_code_and_medicaid_inputs(self):
        """Pins "Δ for MO: eligibility only" — any further input is a new state-variance claim."""
        extra = set(MoMsp.pe_inputs) - set(Msp.pe_inputs) - set(Medicaid.pe_inputs)
        self.assertEqual(extra, {MoStateCodeDependency})

    def test_pe_inputs_include_quarters_of_coverage(self):
        """
        Regression guard for the value. Without it PolicyEngine does not assume premium-free
        Part A and returns a Part A premium on top of Part B, inflating the yearly figure
        well past the $2,434.80 every eligible scenario asserts.
        """
        self.assertIn(member_deps.MedicareQuartersOfCoverageDependency, MoMsp.pe_inputs)

    def test_pe_outputs_request_category_and_value(self):
        """The category drives QMB/SLMB/QI tiering; the value is the displayed dollar amount."""
        self.assertIn(member_deps.MspCategory, MoMsp.pe_outputs)
        self.assertIn(member_deps.Msp, MoMsp.pe_outputs)

    def test_does_not_override_member_value(self):
        """MO displays PolicyEngine's computed premium value with no state adjustment."""
        self.assertIs(MoMsp.member_value, PolicyEngineMembersCalculator.member_value)


class TestMoMspPeInput(TestCase):
    """
    ``MoMsp``'s dependencies land in the pe_input payload sent to PolicyEngine.

    These assert the inputs each spec scenario depends on actually reach PE. The
    eligibility and dollar outcomes themselves are computed by PolicyEngine and were
    verified live at the pinned model version 1.786.5 — see
    ``programs/programs/mo/msp/spec.md``.
    """

    PERIOD = "2026"

    @classmethod
    def setUpTestData(cls):
        cls.white_label = WhiteLabel.objects.create(name="Missouri", code="mo", state_code="MO")

    def setUp(self):
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="65101",
            county="Cole County",
            household_size=1,
            household_assets=3_000,
            completed=False,
        )
        self.head = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=71,
        )

    def _calculator(self):
        program = Mock()
        program.year.period = self.PERIOD
        return MoMsp(self.screen, program, self.screen.missing_fields())

    def test_sends_mo_state_code(self):
        household = pe_input(self.screen, [self._calculator()])["household"]["households"]["household"]

        self.assertIn("state_code", household)
        self.assertIn("MO", household["state_code"].values())

    def test_sends_msp_eligibility_inputs_for_the_member(self):
        people = pe_input(self.screen, [self._calculator()])["household"]["people"]
        head = people[str(self.head.id)]

        for field in (
            "age",
            "is_medicare_eligible",
            "ssi_earned_income",
            "ssi_unearned_income",
            "ssi_countable_resources",
            "medicare_quarters_of_coverage",
        ):
            self.assertIn(field, head)

    def test_sends_household_assets_for_the_asset_test(self):
        """
        MO does not waive the MSP resource test, so the reported assets must reach PE.
        Scenario 4 ($15,000, over the $9,950 individual limit) turns on this input.
        """
        spm_unit = pe_input(self.screen, [self._calculator()])["household"]["spm_units"]["spm_unit"]

        self.assertEqual(spm_unit["spm_unit_cash_assets"], {self.PERIOD: 3_000})

    def test_assumes_premium_free_part_a(self):
        """40 quarters — ~99% of beneficiaries — which zeroes the Part A premium."""
        people = pe_input(self.screen, [self._calculator()])["household"]["people"]

        self.assertEqual(people[str(self.head.id)]["medicare_quarters_of_coverage"], {self.PERIOD: 40})

    def test_sends_social_security_as_ssi_unearned_income(self):
        """
        MSP's income test uses SSI methodology, so retirement income must arrive as
        ``ssi_unearned_income`` — this is what places a household in the QMB/SLMB/QI tiers.
        """
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="sSRetirement",
            amount=1_000,
            frequency="monthly",
        )

        people = pe_input(self.screen, [self._calculator()])["household"]["people"]

        self.assertEqual(people[str(self.head.id)]["ssi_unearned_income"], {self.PERIOD: 12_000})

    def test_requests_msp_output_for_the_member(self):
        people = pe_input(self.screen, [self._calculator()])["household"]["people"]

        self.assertIn("msp", people[str(self.head.id)])

    def test_sends_medicaid_determination_inputs(self):
        """
        QI is barred for anyone eligible for full MO HealthNet — ``is_qi_eligible`` excludes
        ``is_medicaid_eligible``. PolicyEngine *derives* that flag rather than accepting a
        reported value: it appears in the payload as a requested output (``None``), not as an
        input we set. What ``MoMsp`` must supply is the evidence behind it, which is why it
        carries ``Medicaid.pe_inputs`` — the income, resource, and categorical facts PE needs
        to make the determination. Without them the QI exclusion could not bind. Scenario 7
        exercises the outcome; this pins the inputs that make it reachable.
        """
        people = pe_input(self.screen, [self._calculator()])["household"]["people"]
        head = people[str(self.head.id)]

        for field in (
            "is_pregnant",
            "is_disabled",
            "employment_income",
            "self_employment_income",
            "rental_income",
            "social_security",
            "taxable_pension_income",
            "unemployment_compensation",
            "ssi",
            "receives_ssi",
            "takes_up_ssi_if_eligible",
            "ssi_countable_resources",
        ):
            self.assertIn(field, head)

        # Derived by PolicyEngine, not reported by us: requested as an output so the QI
        # exclusion is evaluated, and left unset so PE computes it from the inputs above.
        self.assertEqual(head["is_medicaid_eligible"], {self.PERIOD: None})
