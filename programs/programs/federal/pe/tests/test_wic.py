"""
Unit tests for the federal ``Wic`` PolicyEngine calculator and the ``wic_income`` bundle.

Background (MFB-1571): PolicyEngine decides WIC with

    is_wic_eligible = demographic_eligible & (meets_income_test | meets_categorical_test)
                      & nutritional_risk

and both inner branches were starved of inputs. ``Wic`` sent only
``school_meal_countable_income``, which WIC's tree never reads — ``wic_countable_income``
sums its own parameter list, ``gov.usda.wic.income.sources`` — so PE fell back to an
imputation and returned WIC as eligible at any reported income. The categorical branch's
reported-receipt inputs (``receives_snap`` / ``receives_tanf``) had no dependency at all.

The coverage test below is the important one: it pins our mapping against PE's actual
source list, so a WIC calculator can never again go out with none of them.

Values referenced here were measured against the private household.api on 2026-08-04 with a
pregnant adult + 3yo + infant in MO; each field named in ``test_income_bundle_covers_every_...``
moved ``wic_countable_income`` by the amount sent.
"""

from django.test import TestCase

import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.federal.pe.member import Wic
from programs.programs.policyengine.calculators.dependencies import member as member_deps
from programs.programs.policyengine.calculators.dependencies import spm as spm_deps

# gov/usda/wic/income/sources.yaml, effective 2009-01-01. 7 CFR 246.7(d)(2)(ii)(A).
WIC_INCOME_SOURCES = {
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

# Sources we reach through a PolicyEngine `adds` chain rather than by name. Sending the
# left-hand field moves the right-hand WIC source, so a plain name-intersection test
# understates coverage — which is exactly how the old MO test came to claim "5 of 24".
SOURCES_REACHED_VIA_ADDS = {
    # taxable_pension_income -> pension_income (pension_income adds it directly)
    "taxable_pension_income": "pension_income",
    # taxable_ira_distributions -> taxable_retirement_distributions -> retirement_distributions
    "taxable_ira_distributions": "retirement_distributions",
}

# Not in the sources list at all, but wic_countable_income adds positive capital_gains as a
# separate term, and capital_gains adds long_term_capital_gains.
CAPITAL_GAINS_FIELD = "long_term_capital_gains"

# WIC sources with no screener field behind them. veterans_benefits and survivor_benefits are
# collected but reach PE folded into taxable_pension_income / social_security respectively.
UNREACHABLE_SOURCES = {
    "military_service_income",
    "dividend_income",
    "interest_income",
    "gi_cash_assistance",
    "financial_assistance",
    "strike_benefits",
    "disability_benefits",
    "educational_assistance",
    "railroad_benefits",
    "survivor_benefits",
    "veterans_benefits",
}


def sent_fields(calculator):
    return {dep.field for dep in calculator.pe_inputs if getattr(dep, "field", None)}


class TestWicIncomeBundle(TestCase):
    """``wic_income`` maps every WIC income source the screener actually collects."""

    def test_income_bundle_covers_every_reachable_wic_source(self):
        sent = {dep.field for dep in dependency.wic_income}
        reached = (sent & WIC_INCOME_SOURCES) | {
            source for field, source in SOURCES_REACHED_VIA_ADDS.items() if field in sent
        }

        self.assertEqual(
            reached,
            WIC_INCOME_SOURCES - UNREACHABLE_SOURCES,
            "the wic_income bundle no longer covers every WIC source the screener collects",
        )

    def test_capital_gains_reaches_wic_as_its_own_term(self):
        """
        ``long_term_capital_gains`` is not in the sources list, so a name-only audit reads it as
        inert. It isn't: ``wic_countable_income`` adds positive ``capital_gains`` separately.
        """
        self.assertIn(CAPITAL_GAINS_FIELD, {dep.field for dep in dependency.wic_income})

    def test_unreachable_sources_are_not_claimed(self):
        """Guard against someone "covering" a source with a dependency the screener can't fill."""
        sent = {dep.field for dep in dependency.wic_income}

        self.assertEqual(sent & UNREACHABLE_SOURCES, set())

    def test_bundle_includes_irs_gross_income(self):
        for dep in dependency.irs_gross_income:
            self.assertIn(dep, dependency.wic_income)

    def test_bundle_has_no_duplicate_fields(self):
        fields = [dep.field for dep in dependency.wic_income]

        self.assertEqual(len(fields), len(set(fields)))

    def test_snap_is_not_treated_as_wic_income(self):
        """
        SNAP is deliberately absent from PE's WIC source list — benefits aren't countable
        income — so the bundle must not send it. Reported SNAP reaches WIC through
        ``receives_snap`` (categorical), not through income.
        """
        self.assertNotIn("snap", {dep.field for dep in dependency.wic_income})


class TestFederalWicInputs(TestCase):
    """The federal calculator wires both branches of ``is_wic_eligible``."""

    def test_sends_the_wic_income_bundle(self):
        for dep in dependency.wic_income:
            self.assertIn(dep, Wic.pe_inputs)

    def test_sends_reported_receipt_for_the_categorical_branch(self):
        """
        ``meets_wic_categorical_eligibility`` reads ``receives_snap`` / ``receives_tanf`` for
        reported enrollment. Measured live: a household at $108k/yr flips from $0 back to
        eligible when either is True — the adjunctive pathway of 42 U.S.C. § 1786(d)(2)(A).
        """
        self.assertIn(spm_deps.ReceivesSnapDependency, Wic.pe_inputs)
        self.assertIn(spm_deps.ReceivesTanfDependency, Wic.pe_inputs)

    def test_no_longer_sends_school_meal_countable_income(self):
        """
        The one income input WIC used to get, and the one PolicyEngine's WIC tree ignores.
        Kept out so nobody reads it as WIC income coverage; SchoolMeals and CSFP still send it
        for their own use.
        """
        self.assertNotIn(spm_deps.SchoolMealCountableIncomeDependency, Wic.pe_inputs)

    def test_keeps_demographic_inputs(self):
        """Category (pregnant / infant / child) drives demographic_eligible and the benefit."""
        self.assertIn(member_deps.AgeDependency, Wic.pe_inputs)
        self.assertIn(member_deps.PregnancyDependency, Wic.pe_inputs)
        self.assertIn(member_deps.ExpectedChildrenPregnancyDependency, Wic.pe_inputs)

    def test_outputs_unchanged(self):
        self.assertEqual(Wic.pe_outputs, [member_deps.Wic, member_deps.WicCategory])

    def test_pe_name(self):
        self.assertEqual(Wic.pe_name, "wic")


class TestStateWicCalculatorsInherit(TestCase):
    """
    Every state WIC calculator must inherit the bundle.

    This is the regression that MFB-1571 is about: the fix originally landed on one subclass
    (MO) and the other five kept the old inputs. Enumerated from the registry rather than
    hardcoded, so a new state WIC program is covered the day it's added.
    """

    def state_wic_calculators(self):
        from programs.programs.policyengine.calculators.registry import all_calculators

        return {
            name: calc
            for name, calc in all_calculators.items()
            if isinstance(calc, type) and issubclass(calc, Wic) and calc is not Wic
        }

    def test_registry_finds_the_expected_states(self):
        self.assertEqual(
            set(self.state_wic_calculators()),
            {"co_wic", "nc_wic", "ma_wic", "tx_wic", "il_wic", "mo_wic"},
        )

    def test_every_state_wic_sends_the_income_bundle(self):
        for name, calc in self.state_wic_calculators().items():
            with self.subTest(program=name):
                for dep in dependency.wic_income:
                    self.assertIn(dep, calc.pe_inputs, f"{name} is missing {dep.field}")

    def test_every_state_wic_sends_a_state_code(self):
        """
        WIC's FPG table branches on AK/HI vs. contiguous US, so state is load-bearing. MA used
        to send none and worked only because a sibling MA program put the state in the shared
        payload — PolicyEngine gets one merged household per screen, not one per program.
        """
        for name, calc in self.state_wic_calculators().items():
            with self.subTest(program=name):
                self.assertTrue(
                    any(dep.field == "state_code" for dep in calc.pe_inputs),
                    f"{name} sends no state code",
                )
