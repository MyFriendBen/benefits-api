"""Unit tests for the shared Medicaid calculator's value routing.

PolicyEngine answers Medicaid over two pathways and a member can clear either: the ordinary
MAGI pathway (``medicaid`` plus ``medicaid_category``, naming the group that applied) and the
optional aged/blind/disabled pathway (``is_optional_senior_or_disabled_for_medicaid``). These
tests pin which of the two decides a member's value, and which rate that produces.

PolicyEngine's own routing wins wherever it has an answer. The ABD pathway is the fallback for
the members it does not reach, not an override applied ahead of it — reading it first is what
produced the production failures the regression tests at the bottom of this file cover.
"""

from django.test import TestCase
from unittest.mock import MagicMock, Mock

from programs.framework.pe_dependencies import member as member_deps
from programs.programs.cross_white_label.medicaid.base import Medicaid


class MedicaidValueTestCase(TestCase):
    """Shared setup: one calculator, one member, and a stand-in for PolicyEngine."""

    # Distinct rates so an assertion names exactly one category.
    RATES = {
        "NONE": 0,
        "ADULT": 400,
        "YOUNG_ADULT": 410,
        "PARENT": 420,
        "PREGNANT": 430,
        "INFANT": 440,
        "YOUNG_CHILD": 450,
        "OLDER_CHILD": 460,
        "SSI_RECIPIENT": 470,
        "AGED": 480,
        "DISABLED": 490,
    }

    def calculator(self, senior_value_takes_precedence=False):
        calculator = Medicaid(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.medicaid_categories = dict(self.RATES)
        calculator.senior_value_takes_precedence = senior_value_takes_precedence
        return calculator

    def member(self, age, is_disabled=False):
        member = Mock()
        member.id = 1
        member.age = age
        member.calc_age = Mock(return_value=age)
        member.has_disability = Mock(return_value=is_disabled)
        return member

    def policyengine_says(self, calculator, medicaid=0, category="NONE", abd=False):
        """Stand in for PolicyEngine's answer about one member.

        Both variables are modelled on every call, not just the one a test is about: they are
        read together, and stubbing only one lets a test pass against a combination
        PolicyEngine would never return.
        """
        calculator.get_member_variable = Mock(return_value=medicaid)

        def dependency_value(dependency, member_id):
            if dependency is member_deps.MedicaidSeniorOrDisabled:
                return abd
            if dependency is member_deps.MedicaidCategory:
                return category
            raise AssertionError(f"unexpected dependency read: {dependency}")

        calculator.get_member_dependency_value = Mock(side_effect=dependency_value)
        return calculator

    def annual(self, category):
        return self.RATES[category] * 12


class TestOrdinaryPathway(MedicaidValueTestCase):
    """A member PolicyEngine prices through ``medicaid_category``."""

    def test_adult_is_valued_at_the_adult_rate(self):
        calculator = self.policyengine_says(self.calculator(), medicaid=500, category="ADULT")

        self.assertEqual(calculator.member_value(self.member(age=35)), self.annual("ADULT"))

    def test_parent_is_valued_at_the_parent_rate_not_the_adult_rate(self):
        calculator = self.policyengine_says(self.calculator(), medicaid=500, category="PARENT")

        self.assertEqual(calculator.member_value(self.member(age=35)), self.annual("PARENT"))

    def test_pregnant_member_is_valued_at_the_pregnant_rate(self):
        calculator = self.policyengine_says(self.calculator(), medicaid=500, category="PREGNANT")

        self.assertEqual(calculator.member_value(self.member(age=30)), self.annual("PREGNANT"))

    def test_each_child_category_is_valued_at_its_own_rate(self):
        for category, age in (("INFANT", 0), ("YOUNG_CHILD", 4), ("OLDER_CHILD", 12)):
            with self.subTest(category=category):
                calculator = self.policyengine_says(self.calculator(), medicaid=500, category=category)

                self.assertEqual(calculator.member_value(self.member(age=age)), self.annual(category))

    def test_young_adult_is_valued_at_the_young_adult_rate(self):
        calculator = self.policyengine_says(self.calculator(), medicaid=500, category="YOUNG_ADULT")

        self.assertEqual(calculator.member_value(self.member(age=20)), self.annual("YOUNG_ADULT"))

    def test_member_with_unknown_age_is_treated_as_non_senior(self):
        """``calc_age`` returns None when birth date is missing; it must not crash or age them up."""
        calculator = self.policyengine_says(self.calculator(), medicaid=500, category="ADULT")

        self.assertEqual(calculator.member_value(self.member(age=None)), self.annual("ADULT"))

    def test_ineligible_member_is_worth_nothing(self):
        calculator = self.policyengine_says(self.calculator(), medicaid=0, category="NONE")

        self.assertEqual(calculator.member_value(self.member(age=50)), 0)

    def test_none_category_is_worth_nothing(self):
        calculator = self.policyengine_says(self.calculator(), medicaid=500, category="NONE")

        self.assertEqual(calculator.member_value(self.member(age=35)), 0)

    def test_unpriced_category_is_worth_nothing_rather_than_raising(self):
        """PolicyEngine's enum is larger than any state prices and grows over time.

        A KeyError here would fail the whole eligibility request for the household, not just
        this program, so an unrecognised category has to read as $0 like any other ineligible
        answer.
        """
        calculator = self.policyengine_says(self.calculator(), medicaid=500, category="MEDICALLY_NEEDY")

        self.assertEqual(calculator.member_value(self.member(age=35)), 0)


class TestAbdPathway(MedicaidValueTestCase):
    """Members eligible on an age or disability basis."""

    def test_senior_on_the_abd_pathway_is_valued_at_the_aged_rate(self):
        calculator = self.policyengine_says(self.calculator(), medicaid=0, category="NONE", abd=True)

        self.assertEqual(calculator.member_value(self.member(age=66)), self.annual("AGED"))

    def test_age_65_is_the_senior_boundary(self):
        calculator = self.policyengine_says(self.calculator(), medicaid=0, category="NONE", abd=True)

        self.assertEqual(calculator.member_value(self.member(age=65)), self.annual("AGED"))

    def test_age_64_is_not_a_senior(self):
        """One year under the boundary, the ABD pathway pays the disabled rate, not the aged one."""
        calculator = self.policyengine_says(self.calculator(), medicaid=0, category="NONE", abd=True)

        self.assertEqual(calculator.member_value(self.member(age=64, is_disabled=True)), self.annual("DISABLED"))

    def test_disabled_adult_on_the_abd_pathway_is_valued_at_the_disabled_rate(self):
        calculator = self.policyengine_says(self.calculator(), medicaid=0, category="NONE", abd=True)

        self.assertEqual(calculator.member_value(self.member(age=45, is_disabled=True)), self.annual("DISABLED"))

    def test_disabled_child_on_the_abd_pathway_is_valued_at_the_disabled_rate(self):
        """The disabled rate, not the child rate — the child's own facts decide the tier."""
        calculator = self.policyengine_says(self.calculator(), medicaid=0, category="NONE", abd=True)

        self.assertEqual(calculator.member_value(self.member(age=10, is_disabled=True)), self.annual("DISABLED"))

    def test_senior_who_fails_the_abd_pathway_is_worth_nothing(self):
        calculator = self.policyengine_says(self.calculator(), medicaid=0, category="NONE", abd=False)

        self.assertEqual(calculator.member_value(self.member(age=71)), 0)

    def test_disabled_adult_who_fails_the_abd_pathway_is_worth_nothing(self):
        """Failing ABD with nothing on the ordinary pathway either leaves them ineligible."""
        calculator = self.policyengine_says(self.calculator(), medicaid=0, category="NONE", abd=False)

        self.assertEqual(calculator.member_value(self.member(age=45, is_disabled=True)), 0)

    def test_neither_senior_nor_disabled_never_reads_the_abd_pathway(self):
        calculator = self.policyengine_says(self.calculator(), medicaid=0, category="NONE", abd=True)

        self.assertEqual(calculator.member_value(self.member(age=35)), 0)


class TestAbdCategories(MedicaidValueTestCase):
    """``SENIOR_OR_DISABLED`` and ``SSI_RECIPIENT`` carry no aged/disabled distinction.

    PolicyEngine reports both for members it found eligible on an age or disability basis
    without saying which, so the value tier comes from the member's own age and disability
    flags rather than from a rate keyed on the category name.
    """

    def test_senior_or_disabled_category_for_a_senior_is_the_aged_rate(self):
        calculator = self.policyengine_says(self.calculator(), medicaid=500, category="SENIOR_OR_DISABLED")

        self.assertEqual(calculator.member_value(self.member(age=70)), self.annual("AGED"))

    def test_senior_or_disabled_category_for_a_disabled_child_is_the_disabled_rate(self):
        calculator = self.policyengine_says(self.calculator(), medicaid=500, category="SENIOR_OR_DISABLED")

        self.assertEqual(calculator.member_value(self.member(age=11, is_disabled=True)), self.annual("DISABLED"))

    def test_ssi_recipient_category_for_a_disabled_adult_is_the_disabled_rate(self):
        calculator = self.policyengine_says(self.calculator(), medicaid=500, category="SSI_RECIPIENT")

        self.assertEqual(calculator.member_value(self.member(age=41, is_disabled=True)), self.annual("DISABLED"))

    def test_ssi_recipient_category_with_no_disability_flag_is_the_disabled_rate(self):
        """SSI receipt is itself the disability signal, so a working-age recipient who set no
        screener flag must not fall to the aged rate."""
        calculator = self.policyengine_says(self.calculator(), medicaid=500, category="SSI_RECIPIENT")

        self.assertEqual(calculator.member_value(self.member(age=41)), self.annual("DISABLED"))

    def test_ssi_recipient_category_for_a_senior_is_the_aged_rate(self):
        """A 66-year-old on SSI is a senior enrollee, not a disabled one, whatever the route in."""
        calculator = self.policyengine_says(self.calculator(), medicaid=500, category="SSI_RECIPIENT")

        self.assertEqual(calculator.member_value(self.member(age=66)), self.annual("AGED"))

    def test_abd_category_for_a_child_with_no_disability_flag_is_the_disabled_rate(self):
        """Neither senior nor flagged: the aged rate would be plainly wrong for a minor."""
        calculator = self.policyengine_says(self.calculator(), medicaid=500, category="SENIOR_OR_DISABLED")

        self.assertEqual(calculator.member_value(self.member(age=11)), self.annual("DISABLED"))

    def test_abd_category_is_not_read_off_the_rate_table(self):
        """The category names have no key of their own; pricing them would be dead config."""
        self.assertNotIn("SENIOR_OR_DISABLED", Medicaid.medicaid_categories)
        self.assertEqual(Medicaid.abd_categories, ("SENIOR_OR_DISABLED", "SSI_RECIPIENT"))


class TestSeniorAndDisabledPrecedence(MedicaidValueTestCase):
    """Which rate a member who is both 65+ and disability-eligible gets.

    The two committed specs disagree and each is right about its own source table, so this is
    per-state rather than uniform: specs/ks.md reads its per-enrollee groups as disjoint with
    disability taking precedence, while MO follows KFF's Seniors definition of 65+ regardless
    of disability.
    """

    def test_disability_wins_by_default(self):
        calculator = self.policyengine_says(self.calculator(), medicaid=0, category="NONE", abd=True)

        value = calculator.member_value(self.member(age=68, is_disabled=True))

        self.assertEqual(value, self.annual("DISABLED"))
        self.assertNotEqual(value, self.annual("AGED"))

    def test_age_wins_when_the_state_opts_in(self):
        calculator = self.calculator(senior_value_takes_precedence=True)
        self.policyengine_says(calculator, medicaid=0, category="NONE", abd=True)

        value = calculator.member_value(self.member(age=68, is_disabled=True))

        self.assertEqual(value, self.annual("AGED"))
        self.assertNotEqual(value, self.annual("DISABLED"))

    def test_the_flag_only_affects_members_who_are_both(self):
        """A senior who is not disabled, and a disabled member who is not a senior, are unmoved."""
        for takes_precedence in (False, True):
            calculator = self.calculator(senior_value_takes_precedence=takes_precedence)
            self.policyengine_says(calculator, medicaid=0, category="NONE", abd=True)

            with self.subTest(senior_value_takes_precedence=takes_precedence):
                self.assertEqual(calculator.member_value(self.member(age=70)), self.annual("AGED"))
                self.assertEqual(
                    calculator.member_value(self.member(age=40, is_disabled=True)), self.annual("DISABLED")
                )

    def test_default_is_disability_first(self):
        self.assertFalse(Medicaid.senior_value_takes_precedence)


class TestExpansionIsNotForSeniors(MedicaidValueTestCase):
    """ACA expansion is a 19-64 group (42 CFR 435.119)."""

    def test_senior_is_never_valued_at_an_expansion_rate(self):
        """Even if PolicyEngine hands back an expansion category for a 65+ member."""
        calculator = self.policyengine_says(self.calculator(), medicaid=500, category="ADULT", abd=False)

        self.assertEqual(calculator.member_value(self.member(age=71)), 0)

    def test_senior_routed_to_expansion_still_gets_the_abd_pathway(self):
        calculator = self.policyengine_says(self.calculator(), medicaid=500, category="ADULT", abd=True)

        self.assertEqual(calculator.member_value(self.member(age=71)), self.annual("AGED"))

    def test_senior_may_still_hold_a_magi_category_with_no_age_ceiling(self):
        """Sec. 1931 parent/caretaker has no upper age bound, so it is not excluded."""
        calculator = self.policyengine_says(self.calculator(), medicaid=500, category="PARENT")

        self.assertEqual(calculator.member_value(self.member(age=66)), self.annual("PARENT"))

    def test_adult_just_under_the_boundary_is_valued_at_the_expansion_rate(self):
        calculator = self.policyengine_says(self.calculator(), medicaid=500, category="ADULT")

        self.assertEqual(calculator.member_value(self.member(age=64)), self.annual("ADULT"))


class TestProductionRegressions(MedicaidValueTestCase):
    """Four routing failures found in production QA, as the shapes PolicyEngine returned.

    Each combination below was read off a production PolicyEngine payload for a Missouri screen,
    so these fail against the routing that shipped and pass against this one. Scenario numbers
    refer to the Test Scenarios in ``specs/mo.md``.
    """

    def test_disabled_adult_who_fails_abd_falls_through_to_expansion(self):
        """Scenario 6. PE: ADULT, ABD false. Shipped $0 — the program vanished from results."""
        calculator = self.policyengine_says(self.calculator(), medicaid=12_559, category="ADULT", abd=False)

        self.assertEqual(calculator.member_value(self.member(age=40, is_disabled=True)), self.annual("ADULT"))

    def test_disabled_adult_routed_to_expansion_is_not_repriced_as_disabled(self):
        """Scenario 19. PE: ADULT, ABD true. Shipped the disabled rate over PE's own routing."""
        calculator = self.policyengine_says(self.calculator(), medicaid=12_559, category="ADULT", abd=True)

        self.assertEqual(calculator.member_value(self.member(age=40, is_disabled=True)), self.annual("ADULT"))

    def test_blind_adult_routed_to_expansion_is_not_repriced_as_disabled(self):
        """Scenario 21. Same shape as 19, reached through the blindness flag."""
        calculator = self.policyengine_says(self.calculator(), medicaid=12_559, category="ADULT", abd=True)

        self.assertEqual(calculator.member_value(self.member(age=46, is_disabled=True)), self.annual("ADULT"))

    def test_disabled_senior_takes_the_aged_rate_where_the_state_says_age_wins(self):
        """Scenario 24. PE: SENIOR_OR_DISABLED, ABD true. Shipped the under-65 disabled rate."""
        calculator = self.calculator(senior_value_takes_precedence=True)
        self.policyengine_says(calculator, medicaid=12_559, category="SENIOR_OR_DISABLED", abd=True)

        self.assertEqual(calculator.member_value(self.member(age=70, is_disabled=True)), self.annual("AGED"))
