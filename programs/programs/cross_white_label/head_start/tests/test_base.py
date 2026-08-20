"""Recovered from pe/pe/tests."""

from django.test import TestCase
from programs.framework.pe_base import PolicyEngineMembersCalculator
from programs.framework.pe_dependencies import irs_gross_income, member, receipt_contract, spm
from integrations.clients.policyengine.registry import all_calculators
from programs.programs.cross_white_label.head_start.base import HeadStart
from programs.programs.cross_white_label.early_head_start.base import EarlyHeadStart
from programs.framework.tests.family_test_helpers import _registered_subclasses, _state_codes


class TestFederalHeadStart(TestCase):
    """Wiring of the shared federal Head Start (ages 3-5) calculator."""

    def test_is_a_member_calculator(self):
        self.assertTrue(issubclass(HeadStart, PolicyEngineMembersCalculator))

    def test_reads_the_person_level_pe_category(self):
        """Head Start is valued per child, so the value must be read out of
        PolicyEngine's ``people`` bucket. A wrong ``pe_category`` looks up the
        variable in the wrong entity and yields no value at all.

        Asserted here rather than only on the base class because this is the
        property that makes a *per-child* program work.
        """
        self.assertEqual(HeadStart.pe_category, "people")

    def test_pe_name_is_head_start(self):
        self.assertEqual(HeadStart.pe_name, "head_start")

    def test_pe_outputs_read_the_head_start_field(self):
        self.assertEqual(HeadStart.pe_outputs, [member.HeadStart])
        self.assertEqual(member.HeadStart.field, "head_start")

    def test_pe_inputs_include_age_and_foster_care(self):
        """Ages 3-5 gate eligibility; foster care is an income-independent pathway."""
        self.assertIn(member.AgeDependency, HeadStart.pe_inputs)
        self.assertIn(member.FosterCareDependency, HeadStart.pe_inputs)

    def test_pe_inputs_include_categorical_benefit_signals(self):
        """
        SNAP / TANF / SSI receipt qualifies a child regardless of income, so all three must
        reach PolicyEngine's categorical-eligibility determination — as *receipt*, not as a
        benefit PolicyEngine simulated the household as eligible for.
        """
        for dep in receipt_contract:
            self.assertIn(dep, HeadStart.pe_inputs)
        self.assertIn(spm.ReceivesSnapDependency, HeadStart.pe_inputs)
        self.assertIn(spm.ReceivesTanfDependency, HeadStart.pe_inputs)
        self.assertIn(member.ReceivesSsiDependency, HeadStart.pe_inputs)

    def test_pe_inputs_include_irs_gross_income(self):
        """Income drives the non-categorical (at-or-below-100%-FPL) pathway."""
        for income_input in irs_gross_income:
            self.assertIn(income_input, HeadStart.pe_inputs)

    def test_federal_class_carries_no_state_code(self):
        """The base is state-agnostic; subclasses add exactly one state code."""
        self.assertEqual(_state_codes(HeadStart), [])

    def test_is_not_registered_directly(self):
        """States register their own subclass, never the shared base — registering the
        base would send no state code and so resolve no state's spending/enrollment."""
        self.assertNotIn(HeadStart, all_calculators.values())

    def test_does_not_reuse_the_early_head_start_variable(self):
        self.assertNotEqual(HeadStart.pe_name, EarlyHeadStart.pe_name)


class TestRegisteredHeadStartSubclassContract(TestCase):
    """
    The cross-state contract, asserted against every registered subclass of
    ``HeadStart`` and ``EarlyHeadStart``.

    These are the assertions that were previously copy-pasted into each state's
    ``test_member.py``. Holding them here means a new state is covered as soon as it
    is registered, and a state that quietly drops a federal input fails here rather
    than passing because nobody wrote that state's copy of the test.
    """

    def setUp(self):
        self.head_start = _registered_subclasses(HeadStart)
        self.early_head_start = _registered_subclasses(EarlyHeadStart)
        # EarlyHeadStart is a sibling of HeadStart, not a subclass, so the two
        # groups are disjoint; assert that rather than assuming it.
        self.assertFalse(set(self.head_start) & set(self.early_head_start))
        self.all = {**self.head_start, **self.early_head_start}

    def test_states_are_registered(self):
        """A guard on the discovery itself: if the registry stopped exposing these,
        every other test in this class would vacuously pass over an empty dict."""
        self.assertGreaterEqual(len(self.head_start), 1)
        self.assertGreaterEqual(len(self.early_head_start), 1)

    def test_slug_matches_the_base_program(self):
        """``*_early_head_start`` slugs must resolve the EHS calculator and plain
        ``*_head_start`` slugs the HS one — the two are easy to cross-wire, and doing
        so silently returns the wrong program's value."""
        for slug in self.head_start:
            self.assertFalse(slug.endswith("early_head_start"), f"{slug} resolves HeadStart")
        for slug in self.early_head_start:
            self.assertTrue(slug.endswith("early_head_start"), f"{slug} resolves EarlyHeadStart")

    def test_pe_category_is_inherited_unchanged(self):
        """Every state reads its per-child value from the ``people`` bucket."""
        for slug, calc in self.all.items():
            with self.subTest(slug=slug):
                self.assertEqual(calc.pe_category, "people")

    def test_pe_name_is_inherited_unchanged(self):
        for slug, calc in self.head_start.items():
            with self.subTest(slug=slug):
                self.assertEqual(calc.pe_name, "head_start")
        for slug, calc in self.early_head_start.items():
            with self.subTest(slug=slug):
                self.assertEqual(calc.pe_name, "early_head_start")

    def test_pe_outputs_are_inherited_unchanged(self):
        for slug, calc in self.head_start.items():
            with self.subTest(slug=slug):
                self.assertEqual(calc.pe_outputs, [member.HeadStart])
        for slug, calc in self.early_head_start.items():
            with self.subTest(slug=slug):
                self.assertEqual(calc.pe_outputs, [member.EarlyHeadStart])

    def test_no_federal_input_is_dropped(self):
        """Subclasses only append a state code. Dropping an inherited input silently
        changes eligibility — e.g. losing ``Snap`` would deny every household that
        qualifies categorically rather than on income."""
        for slug, calc in self.head_start.items():
            with self.subTest(slug=slug):
                for dep in HeadStart.pe_inputs:
                    self.assertIn(dep, calc.pe_inputs, f"{slug} dropped {dep.__name__}")
        for slug, calc in self.early_head_start.items():
            with self.subTest(slug=slug):
                for dep in EarlyHeadStart.pe_inputs:
                    self.assertIn(dep, calc.pe_inputs, f"{slug} dropped {dep.__name__}")

    def test_sends_exactly_one_state_code(self):
        """The state code selects the state's spending/enrollment parameters. Sending
        none leaves the value unresolved; sending two is ambiguous."""
        for slug, calc in self.all.items():
            with self.subTest(slug=slug):
                self.assertEqual(len(_state_codes(calc)), 1, f"{slug} state codes: {_state_codes(calc)}")

    def test_state_code_matches_the_slug(self):
        """Guards the copy-paste failure this pattern invites: a new state cloned from
        another and left sending the source state's code would resolve the wrong
        state's per-child value while looking correctly registered."""
        for slug, calc in self.all.items():
            with self.subTest(slug=slug):
                self.assertEqual(_state_codes(calc)[0].state.lower(), slug.split("_", 1)[0])

    def test_adds_nothing_beyond_the_state_code(self):
        """A subclass's inputs are exactly the federal set plus its state code. An
        extra input is either dead weight PolicyEngine ignores or a sign the state is
        modelling variance the ``Fed (value varies)`` tier says does not exist.

        Expressed as a set difference rather than a hardcoded count so that adding a
        federal input updates every state at once instead of failing N state tests.
        """
        for slug, calc in self.head_start.items():
            with self.subTest(slug=slug):
                extra = set(calc.pe_inputs) - set(HeadStart.pe_inputs) - set(_state_codes(calc))
                self.assertEqual(extra, set(), f"{slug} adds {[d.__name__ for d in extra]}")
        for slug, calc in self.early_head_start.items():
            with self.subTest(slug=slug):
                extra = set(calc.pe_inputs) - set(EarlyHeadStart.pe_inputs) - set(_state_codes(calc))
                self.assertEqual(extra, set(), f"{slug} adds {[d.__name__ for d in extra]}")

    def test_no_subclass_overrides_member_value(self):
        """The value is PolicyEngine's per-child figure, taken as-is. A state
        overriding ``member_value`` would be introducing state variance that the
        ``Fed (value varies)`` tier says does not exist — and that its spec's dollar
        scenarios would not catch, since they assert the PE value.
        """
        for slug, calc in self.all.items():
            with self.subTest(slug=slug):
                self.assertIs(
                    calc.member_value,
                    PolicyEngineMembersCalculator.member_value,
                    f"{slug} overrides member_value",
                )
