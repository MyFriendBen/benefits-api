"""The federal Medicaid base, tested through a stand-in state.

PolicyEngine is stubbed: each test says what PolicyEngine answered about a member and checks
what the base does with it. The rules come from the program-ops federal Medicaid base spec,
named in each class docstring by its criterion slug.
"""

from typing import Optional
from unittest.mock import MagicMock, Mock

from django.test import SimpleTestCase

import programs.framework.pe_dependencies as dependency
from programs.framework.pe_dependencies import member as member_deps
from programs.programs.cross_white_label.medicaid.base import Medicaid
from programs.programs.cross_white_label.medicaid.federal_base import (
    AGED,
    CHILD,
    DISABLED,
    NEW_ADULT,
    OTHER_ADULT,
    FederalMedicaid,
)

# Distinct figures so an assertion names exactly one group.
SPEND = {CHILD: 4_000, NEW_ADULT: 7_000, OTHER_ADULT: 6_000, DISABLED: 30_000, AGED: 20_000}


class StandInState(FederalMedicaid, abstract=True):
    group_spend_per_fye_enrollee = SPEND


class StandInStateWithChildCoverage(StandInState, abstract=True):
    expansion_child_coverage_age = 21
    caretaker_non_relative_option = False


class StandInStateCountingNonRelatives(StandInState, abstract=True):
    expansion_child_coverage_age = 21
    caretaker_non_relative_option = True


def household_member(
    member_id: int,
    age: Optional[int],
    relationship: str = "headOfHousehold",
    ssdi: int = 0,
    uninsured: bool = False,
) -> Mock:
    person = Mock()
    person.id = member_id
    person.age = age
    person.relationship = relationship
    person.calc_age = Mock(return_value=age)
    person.calc_gross_income = Mock(side_effect=lambda freq, types, **kwargs: ssdi if types == ["sSDisability"] else 0)
    person.has_insurance_types = Mock(side_effect=lambda types, strict=True: uninsured and "none" in types)
    return person


class FederalMedicaidTestCase(SimpleTestCase):
    calculator_class: type = StandInState

    def calculator(self, members: Optional[list] = None) -> FederalMedicaid:
        screen = Mock()
        screen.household_members.all = Mock(return_value=members or [])
        calculator = self.calculator_class(screen, Mock(), Mock())
        calculator._sim = MagicMock()
        return calculator

    def policyengine_says(
        self, calculator: FederalMedicaid, medicaid: int = 0, category: str = "NONE", aged_disabled: bool = False
    ) -> FederalMedicaid:
        """Stub PolicyEngine's three answers about a member; all are modelled on every call."""
        calculator.get_member_variable = Mock(return_value=medicaid)

        def dependency_value(dependency_class: type, member_id: int):
            if dependency_class is member_deps.MedicaidCategory:
                return category
            if dependency_class is member_deps.MedicaidSeniorOrDisabled:
                return aged_disabled
            raise AssertionError(f"unexpected dependency read: {dependency_class}")

        calculator.get_member_dependency_value = Mock(side_effect=dependency_value)
        return calculator


class TestRegistration(SimpleTestCase):
    def test_base_backs_no_program(self) -> None:
        self.assertFalse(hasattr(FederalMedicaid, "program_code") and FederalMedicaid.program_code)

    def test_leaves_the_current_base_alone(self) -> None:
        """Live states and the CHIP, ACA and MSP calculators keep ``Medicaid``'s inputs."""
        self.assertIn(dependency.member.PensionIncomeDependency, Medicaid.pe_inputs)
        self.assertIn(dependency.member.IsDisabledDependency, Medicaid.pe_inputs)
        self.assertIn(dependency.member.TakesUpSsiIfEligibleDependency, Medicaid.pe_inputs)
        self.assertNotIn(dependency.member.OwnSsdiDisabilityDependency, Medicaid.pe_inputs)

    def test_unknown_spending_group_is_refused(self) -> None:
        with self.assertRaises(ValueError):

            class Typo(FederalMedicaid, abstract=True):
                group_spend_per_fye_enrollee = {"seniors": 1}

    def test_pregnancy_services_only_without_extension_is_refused(self) -> None:
        with self.assertRaises(NotImplementedError):

            class ServicesOnly(FederalMedicaid, abstract=True):
                pregnancy_services_only_option = True
                postpartum_extension_option = False


class TestInputs(SimpleTestCase):
    """What the base sends PolicyEngine."""

    def test_magi_income_leaves_out_va_benefits(self) -> None:
        """``expansion_income`` and the other MAGI rules exclude ``veteran``."""
        self.assertIn(dependency.member.PensionIncomeWithoutVeteranDependency, FederalMedicaid.pe_inputs)
        self.assertNotIn(dependency.member.PensionIncomeDependency, FederalMedicaid.pe_inputs)
        self.assertNotIn(dependency.member.VeteransBenefitsDependency, FederalMedicaid.pe_inputs)

    def test_magi_income_counts_boarder_income_and_alimony(self) -> None:
        self.assertIn(dependency.member.RentalAndBoarderIncomeDependency, FederalMedicaid.pe_inputs)
        self.assertNotIn(dependency.member.RentalIncomeDependency, FederalMedicaid.pe_inputs)
        self.assertIn(dependency.member.TaxableAlimonyIncomeDependency, FederalMedicaid.pe_inputs)

    def test_reported_medicare_is_sent(self) -> None:
        """``expansion_no_medicare``: a member reporting Medicare is out of the expansion group."""
        self.assertIn(dependency.member.IsMedicareEligibleDependency, FederalMedicaid.pe_inputs)

    def test_disability_comes_only_from_own_ssdi(self) -> None:
        """``aged_or_disabled``: the self-reported checkboxes are not a disability finding."""
        inputs = FederalMedicaid.pe_inputs
        self.assertIn(dependency.member.OwnSsdiDisabilityDependency, inputs)
        self.assertIn(dependency.member.OwnSsdiNotEngagedInSgaDependency, inputs)
        self.assertNotIn(dependency.member.IsDisabledDependency, inputs)
        self.assertNotIn(dependency.member.MeetsSsiDisabilityCriteriaDependency, inputs)
        self.assertNotIn(dependency.member.IsBlindDependency, inputs)

    def test_ssi_take_up_follows_own_reported_ssi(self) -> None:
        """``receives_ssi``: the receipt contract, with take-up from the member's own SSI line."""
        inputs = FederalMedicaid.pe_inputs
        self.assertIn(dependency.member.TakesUpOwnReportedSsiDependency, inputs)
        self.assertNotIn(dependency.member.TakesUpSsiIfEligibleDependency, inputs)
        for receipt_input in dependency.receipt_contract:
            if receipt_input is not dependency.member.TakesUpSsiIfEligibleDependency:
                self.assertIn(receipt_input, inputs)

    def test_foster_status_is_not_sent(self) -> None:
        """An accepted gap: PolicyEngine treats a foster child as a dependent child."""
        self.assertNotIn(dependency.member.FosterCareDependency, FederalMedicaid.pe_inputs)

    def test_no_field_is_sent_twice(self) -> None:
        """Two inputs for one field would make the program disagree with itself and be dropped."""
        fields = [pe_input.field for pe_input in FederalMedicaid.pe_inputs]
        self.assertEqual(len(fields), len(set(fields)))


class TestSpendingGroups(FederalMedicaidTestCase):
    """§7: the member's value is their spending group's figure."""

    def value(self, category: str, age: Optional[int], ssdi: int = 0) -> int:
        person = household_member(1, age, ssdi=ssdi)
        calculator = self.policyengine_says(self.calculator([person]), medicaid=1, category=category)
        return calculator.member_value(person)

    def test_children_are_in_the_child_group(self) -> None:
        for category in ("INFANT", "YOUNG_CHILD", "OLDER_CHILD"):
            self.assertEqual(self.value(category, 5), SPEND[CHILD], category)

    def test_expansion_adult_is_in_the_new_adult_group(self) -> None:
        self.assertEqual(self.value("ADULT", 40), SPEND[NEW_ADULT])

    def test_pregnant_woman_is_in_the_other_adult_group(self) -> None:
        self.assertEqual(self.value("PREGNANT", 28), SPEND[OTHER_ADULT])

    def test_parent_route_splits_at_19(self) -> None:
        """Code 01: child group under 19, other adult at 19 and over."""
        self.assertEqual(self.value("PARENT", 18), SPEND[CHILD])
        self.assertEqual(self.value("PARENT", 19), SPEND[OTHER_ADULT])

    def test_aged_disabled_routes_split_at_65(self) -> None:
        for category in ("SSI_RECIPIENT", "SENIOR_OR_DISABLED"):
            self.assertEqual(self.value(category, 64, ssdi=1_200), SPEND[DISABLED], category)
            self.assertEqual(self.value(category, 65), SPEND[AGED], category)

    def test_disabled_senior_is_in_the_aged_group(self) -> None:
        """MACStats puts anyone 65+ on an aged, blind or disabled route in the aged group."""
        self.assertEqual(self.value("SENIOR_OR_DISABLED", 70, ssdi=1_200), SPEND[AGED])

    def test_senior_is_never_in_the_expansion_group(self) -> None:
        """``expansion_age_19_to_64``."""
        self.assertEqual(self.value("ADULT", 65), 0)
        self.assertEqual(self.value("ADULT", 64), SPEND[NEW_ADULT])

    def test_routes_the_base_does_not_evaluate_have_no_figure(self) -> None:
        for category in ("YOUNG_ADULT", "MEDICALLY_NEEDY", "NONE"):
            self.assertEqual(self.value(category, 20), 0, category)

    def test_unknown_age_is_not_a_senior(self) -> None:
        self.assertEqual(self.value("SENIOR_OR_DISABLED", None, ssdi=1_200), SPEND[DISABLED])

    def test_ineligible_member_is_worth_nothing(self) -> None:
        person = household_member(1, 40)
        calculator = self.policyengine_says(self.calculator([person]), medicaid=0, category="ADULT")
        self.assertEqual(calculator.member_value(person), 0)

    def test_group_the_state_has_no_figure_for_is_worth_nothing(self) -> None:
        class NoAgedFigure(FederalMedicaid, abstract=True):
            group_spend_per_fye_enrollee = {CHILD: 1}

        person = household_member(1, 70)
        calculator = NoAgedFigure(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()
        self.policyengine_says(calculator, medicaid=1, category="SENIOR_OR_DISABLED")
        self.assertEqual(calculator.member_value(person), 0)


class TestAgedOrDisabled(FederalMedicaidTestCase):
    """``aged_or_disabled``: 65 or older, or the member's own SSDI, on the fallback too."""

    def value(self, age: Optional[int], ssdi: int = 0, aged_disabled: bool = True) -> int:
        person = household_member(1, age, ssdi=ssdi)
        calculator = self.policyengine_says(self.calculator([person]), aged_disabled=aged_disabled)
        return calculator.member_value(person)

    def test_senior_on_the_aged_disabled_route(self) -> None:
        self.assertEqual(self.value(65), SPEND[AGED])

    def test_64_year_old_without_ssdi_does_not_qualify(self) -> None:
        self.assertEqual(self.value(64), 0)

    def test_ssdi_recipient_under_65_qualifies(self) -> None:
        """No age floor: a 30-year-old on their own SSDI is disabled for this route."""
        self.assertEqual(self.value(30, ssdi=1_200), SPEND[DISABLED])

    def test_self_reported_disability_without_ssdi_does_not_qualify(self) -> None:
        """The checkboxes aren't read; only SSDI is. A member with neither fails."""
        person = household_member(1, 40)
        person.has_disability = Mock(return_value=True)
        calculator = self.policyengine_says(self.calculator([person]), aged_disabled=True)
        self.assertEqual(calculator.member_value(person), 0)

    def test_policyengine_finding_the_route_failed_is_respected(self) -> None:
        """Over the income or asset limit, the route fails whatever the age."""
        self.assertEqual(self.value(70, aged_disabled=False), 0)

    def test_fallback_after_a_route_with_no_figure(self) -> None:
        """A senior PolicyEngine placed in the expansion group still has the aged route."""
        person = household_member(1, 66)
        calculator = self.policyengine_says(self.calculator([person]), medicaid=1, category="ADULT", aged_disabled=True)
        self.assertEqual(calculator.member_value(person), SPEND[AGED])


class TestExpansionChildCoverage(FederalMedicaidTestCase):
    """``expansion_parent_child_coverage``, with the state's age 21 and no non-relative option."""

    calculator_class = StandInStateWithChildCoverage

    def adult_value(self, parent: Mock, household: list) -> int:
        calculator = self.policyengine_says(self.calculator(household), medicaid=1, category="ADULT")
        return calculator.member_value(parent)

    def test_parent_of_an_uninsured_child_under_the_age_fails(self) -> None:
        """A parent at 120% FPL whose 10-year-old has no insurance."""
        parent = household_member(1, 35)
        child = household_member(2, 10, relationship="child", uninsured=True)
        self.assertEqual(self.adult_value(parent, [parent, child]), 0)

    def test_parent_of_an_insured_child_passes(self) -> None:
        parent = household_member(1, 35)
        child = household_member(2, 10, relationship="child")
        self.assertEqual(self.adult_value(parent, [parent, child]), SPEND[NEW_ADULT])

    def test_the_state_age_is_exclusive(self) -> None:
        """Under 21 counts; 21 doesn't."""
        parent = household_member(1, 45)
        twenty = household_member(2, 20, relationship="child", uninsured=True)
        twenty_one = household_member(3, 21, relationship="child", uninsured=True)
        self.assertEqual(self.adult_value(parent, [parent, twenty]), 0)
        self.assertEqual(self.adult_value(parent, [parent, twenty_one]), SPEND[NEW_ADULT])

    def test_head_spouse_is_held_to_the_check(self) -> None:
        head = household_member(1, 35)
        spouse = household_member(2, 35, relationship="spouse")
        stepchild = household_member(3, 8, relationship="stepChild", uninsured=True)
        self.assertEqual(self.adult_value(spouse, [head, spouse, stepchild]), 0)

    def test_grandchild_counts(self) -> None:
        grandparent = household_member(1, 55)
        grandchild = household_member(2, 4, relationship="grandChild", uninsured=True)
        self.assertEqual(self.adult_value(grandparent, [grandparent, grandchild]), 0)

    def test_other_members_skip_the_check(self) -> None:
        """Relationships are recorded only to the head, so a sibling isn't tested."""
        head = household_member(1, 35)
        sibling = household_member(2, 30, relationship="sisterOrBrother")
        child = household_member(3, 6, relationship="child", uninsured=True)
        self.assertEqual(self.adult_value(sibling, [head, sibling, child]), SPEND[NEW_ADULT])

    def test_foster_child_is_skipped_without_the_non_relative_option(self) -> None:
        parent = household_member(1, 35)
        foster = household_member(2, 9, relationship="fosterChild", uninsured=True)
        self.assertEqual(self.adult_value(parent, [parent, foster]), SPEND[NEW_ADULT])

    def test_child_with_unknown_age_is_skipped(self) -> None:
        parent = household_member(1, 35)
        child = household_member(2, None, relationship="child", uninsured=True)
        self.assertEqual(self.adult_value(parent, [parent, child]), SPEND[NEW_ADULT])

    def test_only_the_expansion_group_is_checked(self) -> None:
        """The parent/caretaker group has no child-coverage condition."""
        parent = household_member(1, 35)
        child = household_member(2, 10, relationship="child", uninsured=True)
        calculator = self.policyengine_says(self.calculator([parent, child]), medicaid=1, category="PARENT")
        self.assertEqual(calculator.member_value(parent), SPEND[OTHER_ADULT])

    def test_reads_insurance_relationship_and_age(self) -> None:
        for field in ("insurance", "relationship", "age"):
            self.assertIn(field, StandInStateWithChildCoverage.dependencies)


class TestExpansionChildCoverageNonRelatives(FederalMedicaidTestCase):
    calculator_class = StandInStateCountingNonRelatives

    def test_foster_child_counts_with_the_non_relative_option(self) -> None:
        parent = household_member(1, 35)
        foster = household_member(2, 9, relationship="fosterChild", uninsured=True)
        calculator = self.policyengine_says(self.calculator([parent, foster]), medicaid=1, category="ADULT")
        self.assertEqual(calculator.member_value(parent), 0)


class TestExpansionChildCoverageOff(FederalMedicaidTestCase):
    """A state whose spec doesn't supply the age leaves the check off."""

    def test_uninsured_child_does_not_matter(self) -> None:
        parent = household_member(1, 35)
        child = household_member(2, 10, relationship="child", uninsured=True)
        calculator = self.policyengine_says(self.calculator([parent, child]), medicaid=1, category="ADULT")
        self.assertEqual(calculator.member_value(parent), SPEND[NEW_ADULT])
        self.assertNotIn("insurance", StandInState.dependencies)
