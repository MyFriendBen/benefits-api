"""
Unit tests for the shared federal WIC PolicyEngine calculator.

PolicyEngine decides WIC with::

    is_wic_eligible = demographic_eligible
                      & (meets_wic_income_test | meets_wic_categorical_eligibility)
                      & nutritional_risk

The bug these tests guard is that neither the income term nor anything
downstream of it was fed. ``Wic``'s only income input was
``school_meal_countable_income``, which WIC's tree never reads —
``wic_countable_income`` sums its own parameter list, ``gov.usda.wic.income.sources``.
Given none of its sources PE substitutes an imputation, which also satisfies the
categorical branch, so WIC returned eligible at any reported income. Measured against
the private household API (MO, pregnant adult + 3yo + infant): eligible at $150k/yr
before the fix, $0 after.

Every state WIC program subclasses this calculator, so the mapping is a cross-state
contract. The state assertions below are enumerated from the registry rather than
listed by hand, so a new state WIC is covered the day it is registered.

The eligibility math itself lives in PolicyEngine and is not duplicated here; what is
pinned here is which inputs we send.
"""

from django.test import TestCase

from programs.framework.pe_base import PolicyEngineMembersCalculator
from programs.framework.pe_dependencies import irs_gross_income, member, spm, wic_income
from programs.framework.pe_dependencies.household import StateCode
from integrations.clients.policyengine.registry import all_calculators
from programs.programs.cross_white_label.wic.base import Wic

# PolicyEngine's gov.usda.wic.income.sources, in full (24 variables), so the coverage
# assertions below are measured against WIC's real list rather than a subset of it.
# Note that capital_gains is NOT among them: wic_countable_income is
# ``add(spm_unit, period, sources) + max_(0, capital_gains)``, so it is a separate
# positive-only term. CAPITAL_GAINS_TERM below covers it.
WIC_INCOME_SOURCES = {
    "alimony_income",
    "child_support_received",
    "disability_benefits",
    "dividend_income",
    "educational_assistance",
    "employment_income",
    "financial_assistance",
    "gi_cash_assistance",
    "interest_income",
    "military_service_income",
    "miscellaneous_income",
    "pension_income",
    "railroad_benefits",
    "rental_income",
    "retirement_distributions",
    "self_employment_income",
    "social_security",
    "ssi",
    "strike_benefits",
    "survivor_benefits",
    "tanf",
    "unemployment_compensation",
    "veterans_benefits",
    "workers_compensation",
}

CAPITAL_GAINS_TERM = "capital_gains"

# Several sources are reached through a PE ``adds`` chain rather than by name, so the
# field we send and the source it lands in differ. Verified one field at a time against
# the private API: each moved ``wic_countable_income`` by the amount sent.
SENT_FIELD_TO_SOURCE = {
    "taxable_pension_income": "pension_income",
    "taxable_ira_distributions": "retirement_distributions",
    "long_term_capital_gains": CAPITAL_GAINS_TERM,
}

# The 10 sources we never populate. Grouped by *why*, because "unreachable" alone is
# misleading — for most of these the household's money is still counted, just under a
# different source. See the wic_income comment for the full reasoning.
UNREACHABLE_SOURCES = {
    # Counted elsewhere. PE's social_security adds social_security_disability /
    # _survivors / _dependents / _retirement, so the screener's SSDI, SS survivor and SS
    # dependent income is counted there; PE's standalone disability_benefits and
    # survivor_benefits are the non-Social-Security buckets, additive with it. Veteran
    # income goes out as taxable_pension_income, and investment income through the
    # capital-gains term.
    "disability_benefits",
    "survivor_benefits",
    "veterans_benefits",
    "dividend_income",
    "interest_income",
    # Not collected by the screener at all.
    "educational_assistance",
    "gi_cash_assistance",
    "military_service_income",
    "railroad_benefits",
    "strike_benefits",
}

# Screener income the household reports that reaches no PE income field at all, so WIC
# genuinely undercounts it. The state disability types are what PE's disability_benefits
# holds; boarder arguably belongs in rental_income. Pinned so the gap stays visible.
UNSENT_SCREENER_INCOME_TYPES = {
    "cOSDisability",
    "stateDisability",
    "iLStateDisability",
    "boarder",
}


def _fields(calculator: type) -> set[str]:
    return {dep.field for dep in calculator.pe_inputs if hasattr(dep, "field")}


def _sources_reached(calculator: type) -> set[str]:
    reached = set()
    for field in _fields(calculator):
        source = SENT_FIELD_TO_SOURCE.get(field, field)
        if source in WIC_INCOME_SOURCES:
            reached.add(source)
    return reached


def _registered_state_wic_calculators() -> dict[str, type]:
    """The state WIC programs. The federal ``Wic`` is itself registered under the bare
    slug ``wic``, but it is the base contract rather than a shipped program — it carries
    no state code and its ``wic_categories`` are all zeros — so it is excluded from the
    per-state assertions it defines."""
    return {
        slug: calc
        for slug, calc in all_calculators.items()
        if isinstance(calc, type) and issubclass(calc, Wic) and calc is not Wic
    }


class TestFederalWicWiring(TestCase):
    def test_is_a_member_calculator(self):
        self.assertTrue(issubclass(Wic, PolicyEngineMembersCalculator))

    def test_reads_the_person_level_pe_category(self):
        """WIC is valued per member (a pregnant adult and each child under 5 qualify
        separately), so the value must be read out of PolicyEngine's ``people``
        bucket."""
        self.assertEqual(Wic.pe_category, "people")

    def test_pe_name(self):
        self.assertEqual(Wic.pe_name, "wic")

    def test_outputs_are_the_benefit_and_its_category(self):
        self.assertEqual(Wic.pe_outputs, [member.Wic, member.WicCategory])

    def test_sends_the_demographic_inputs(self):
        """WIC's demographic term needs age plus the pregnancy pair — a pregnant
        applicant qualifies in her own right, and the expected-children count sizes
        the household for the FPG test."""
        for dep in (member.AgeDependency, member.PregnancyDependency, member.ExpectedChildrenPregnancyDependency):
            self.assertIn(dep, Wic.pe_inputs)


class TestFederalWicIncomeMapping(TestCase):
    """The income term: every WIC source the screener collects must be sent."""

    def test_sends_the_wic_income_bundle(self):
        for dep in wic_income:
            self.assertIn(dep, Wic.pe_inputs)

    def test_no_longer_sends_school_meal_countable_income(self):
        """WIC's tree never reads it. Measured: sending $150k as
        ``school_meal_countable_income`` left ``wic_countable_income`` at PE's imputed
        $3,505 and WIC eligible."""
        self.assertNotIn(spm.SchoolMealCountableIncomeDependency, Wic.pe_inputs)
        self.assertNotIn("school_meal_countable_income", _fields(Wic))

    def test_reaches_every_reachable_wic_income_source(self):
        """The whole point of the fix. If a screener field is added for one of the
        UNREACHABLE_SOURCES, this fails until the mapping is added."""
        self.assertEqual(_sources_reached(Wic), WIC_INCOME_SOURCES - UNREACHABLE_SOURCES)

    def test_unreachable_sources_are_a_subset_of_wic_sources(self):
        """Guards the two constants against drifting apart — an entry misspelled into
        UNREACHABLE_SOURCES would otherwise silently shrink the assertion above."""
        self.assertTrue(UNREACHABLE_SOURCES <= WIC_INCOME_SOURCES)

    def test_sends_the_capital_gains_term(self):
        """``capital_gains`` is not in WIC's source list — ``wic_countable_income`` is
        ``add(spm_unit, period, sources) + max_(0, capital_gains)``, so it is a separate
        term. The screener's investment income reaches it via ``long_term_capital_gains``,
        which ``capital_gains`` adds. Negative gains clamp to zero (measured)."""
        self.assertIn(CAPITAL_GAINS_TERM, {SENT_FIELD_TO_SOURCE.get(f, f) for f in _fields(Wic)})
        self.assertNotIn(CAPITAL_GAINS_TERM, WIC_INCOME_SOURCES)

    def test_irs_gross_income_alone_is_not_enough(self):
        """``MoWic`` shipped ``irs_gross_income`` as a partial fix. It reaches 7 of WIC's
        24 sources (plus the capital-gains term), so it makes wage-type income bind, but
        it leaves workers' comp, alimony, gifts, child support, SSI and TANF unmapped.
        That gap is why the bundle exists as its own list."""
        irs_only = {SENT_FIELD_TO_SOURCE.get(dep.field, dep.field) for dep in irs_gross_income}
        self.assertEqual(len(irs_only & WIC_INCOME_SOURCES), 7)
        self.assertLess(irs_only & WIC_INCOME_SOURCES, _sources_reached(Wic))

    def test_ssdi_is_counted_through_social_security(self):
        """The screener's ``sSDisability`` is Social Security Disability, and PE keeps it
        in ``social_security`` (which adds ``social_security_disability``), not in the
        standalone ``disability_benefits`` source. So SSDI *is* counted for WIC even
        though we never send ``disability_benefits``. Measured: the two are additive, not
        overlapping — 40k in each yields 80k of countable income."""
        self.assertIn(member.SocialSecurityIncomeDependency, Wic.pe_inputs)
        self.assertIn("sSDisability", member.SocialSecurityIncomeDependency.income_types)
        self.assertEqual(member.SocialSecurityIncomeDependency.field, "social_security")

    def test_state_disability_income_reaches_no_pe_field(self):
        """The real undercount. ``disability_benefits`` is PE's non-Social-Security
        disability bucket, and the screener's state disability types are exactly what
        belongs in it — but no dependency reads them, so WIC never sees that income. This
        affects CO, IL, MA and TX. Pinned so the gap can't be mistaken for coverage."""
        sent_income_types = set()
        for dep in Wic.pe_inputs:
            sent_income_types.update(getattr(dep, "income_types", []))

        self.assertTrue(UNSENT_SCREENER_INCOME_TYPES.isdisjoint(sent_income_types))
        self.assertIn("disability_benefits", UNREACHABLE_SOURCES)

    def test_child_support_received_is_income_not_the_paid_expense(self):
        """``SnapChildSupportDependency`` sends child support *paid* as an expense. The
        two are separate PE fields and a household can report both; collapsing them
        would count a payer's outflow as their income."""
        self.assertIn(member.ChildSupportReceivedDependency, Wic.pe_inputs)
        self.assertEqual(member.ChildSupportReceivedDependency.field, "child_support_received")
        self.assertEqual(member.SnapChildSupportDependency.field, "child_support_expense")
        self.assertNotIn(member.SnapChildSupportDependency, Wic.pe_inputs)

    def test_both_cash_assistance_types_are_wic_income_sources(self):
        """WIC counts public-assistance payments, and its own self-exclusion does not apply:
        the household's TANF grant is income here. `cashAssistance` reaches WIC via the `tanf`
        input and `cashAssistanceOther` via `financial_assistance`."""
        self.assertIn(member.NonTanfCashAssistanceIncomeDependency, Wic.pe_inputs)
        self.assertEqual(member.NonTanfCashAssistanceIncomeDependency.field, "financial_assistance")
        self.assertEqual(member.NonTanfCashAssistanceIncomeDependency.income_types, ["cashAssistanceOther"])
        self.assertIn("financial_assistance", _sources_reached(Wic))
        self.assertIn(spm.Tanf, Wic.pe_inputs)

    def test_ssi_and_tanf_are_wic_income_sources(self):
        """Both are in WIC's source list and both are dual-role inputs: they send the
        reported amount, or None so PE computes its own. Without them PE imputes — an
        MO household reporting $0 still showed $3,505 of countable income, all of it
        PE's own TANF figure."""
        self.assertIn(member.Ssi, Wic.pe_inputs)
        self.assertIn(spm.Tanf, Wic.pe_inputs)


class TestStateWicCalculators(TestCase):
    """Asserted across every registered WIC program rather than per state, so a newly
    added state inherits the contract the moment it is registered."""

    def test_states_are_registered(self):
        """A sanity floor: if the registry lookup silently returned nothing, every
        assertion below would vacuously pass."""
        self.assertGreaterEqual(len(_registered_state_wic_calculators()), 6)

    def test_every_state_inherits_the_income_bundle(self):
        for slug, calculator in _registered_state_wic_calculators().items():
            with self.subTest(program=slug):
                for dep in wic_income:
                    self.assertIn(dep, calculator.pe_inputs)

    def test_every_state_sends_a_state_code(self):
        """WIC's FPG table branches on AK/HI vs. contiguous US. A subclass with no state
        code only works when a sibling program happens to put the state in the shared
        payload, which is luck, not wiring."""
        for slug, calculator in _registered_state_wic_calculators().items():
            with self.subTest(program=slug):
                state_codes = [
                    dep for dep in calculator.pe_inputs if isinstance(dep, type) and issubclass(dep, StateCode)
                ]
                self.assertEqual(len(state_codes), 1)

    def test_every_state_keeps_the_federal_pe_name(self):
        for slug, calculator in _registered_state_wic_calculators().items():
            with self.subTest(program=slug):
                self.assertEqual(calculator.pe_name, "wic")

    def test_every_state_yields_a_nonzero_value_for_an_eligible_member(self):
        """A state either overrides ``wic_categories`` with per-category dollar amounts
        or overrides ``member_value`` to return PE's computed benefit. Inheriting the
        federal base unchanged gives every eligible member $0, and the frontend's
        ``value > 0`` filter then drops the program from results entirely."""
        for slug, calculator in _registered_state_wic_calculators().items():
            with self.subTest(program=slug):
                overrides_value = calculator.member_value is not Wic.member_value
                has_amounts = any(amount > 0 for amount in calculator.wic_categories.values())
                self.assertTrue(overrides_value or has_amounts)
