"""The federal Medicaid base, built from the program-ops federal base spec.

Spec: program-ops ``programs/cross_white_label/medicaid/base/medicaid_base_spec.md``, with its
decision record in ``decisions.md`` beside it.

This sits beside ``base.py`` rather than replacing it. The states built on ``Medicaid`` there,
and the CHIP, ACA, Medicare Savings Program and DART calculators that reuse its PolicyEngine
inputs, keep it until each state's spec is backfilled into program-ops; they then move here
together. Until then only a state with a program-ops spec subclasses this one.

PolicyEngine still decides eligibility and the group a member qualifies through
(``medicaid_category``). The spec's rules reach it in two ways: through the inputs sent, and
through checks applied here to its answer.

Where the inputs differ from ``Medicaid.pe_inputs``:

- Income counts boarder payments and all alimony, and leaves out VA benefits (the spec's four
  MAGI income rules).
- A member who reports Medicare is Medicare-eligible (``expansion_no_medicare``).
- The aged/blind/disabled route takes a disability finding only from the member's own Social
  Security Disability Benefits, with no earnings screen (``aged_or_disabled``). The
  self-reported disability checkboxes are not sent.
- Simulated SSI is never treated as received: only a member's own SSI income line counts
  (``receives_ssi``), even when the household ticked the SSI tile without an amount.
- Foster status is not sent. PolicyEngine counts a foster child as a dependent child, so a
  non-relative foster parent passes the parent route in every state; this is an accepted gap.

Checks applied to PolicyEngine's answer:

- The expansion adult group requires a parent's or caretaker's children to have coverage
  (``expansion_parent_child_coverage``), where the state supplies the child's age limit and its
  non-relative caretaker election.
- The value is the state's average spending per full-year enrollee in the member's spending
  group (§7), and the aged/disabled fallback follows ``aged_or_disabled``.

Findings that need a PolicyEngine change (the strict asset limit, counting another pregnant
member) are not worked around here.
"""

from typing import ClassVar, Optional

import programs.framework.pe_dependencies as dependency
from programs.framework.pe_base import PolicyEngineMembersCalculator
from programs.framework.pe_dependencies.member import member_reports_ssdi_amount
from screener.models import HouseholdMember

# §7's spending groups (MACStats Exhibit 22 columns).
CHILD = "child"
NEW_ADULT = "new_adult"
OTHER_ADULT = "other_adult"
DISABLED = "disabled"
AGED = "aged"
SPENDING_GROUPS = (CHILD, NEW_ADULT, OTHER_ADULT, DISABLED, AGED)

# The receipt contract with SSI take-up following only the member's own reported SSI.
_RECEIPT_INPUTS = [
    (
        dependency.member.TakesUpOwnReportedSsiDependency
        if receipt_input is dependency.member.TakesUpSsiIfEligibleDependency
        else receipt_input
    )
    for receipt_input in dependency.receipt_contract
]

# The spec's MAGI income: every taxable stream the screener collects, with boarder income and
# all alimony counted and VA benefits left out.
MAGI_INCOME_INPUTS = [
    dependency.member.EmploymentIncomeDependency,
    dependency.member.SelfEmploymentIncomeDependency,
    dependency.member.RentalAndBoarderIncomeDependency,
    dependency.member.PensionIncomeWithoutVeteranDependency,
    dependency.member.SocialSecurityIncomeDependency,
    dependency.member.UnemploymentIncomeDependency,
    dependency.member.InvestmentIncomeDependency,
    dependency.member.RetirementDistributionsDependency,
    dependency.member.TaxableAlimonyIncomeDependency,
]

# Relationships to the head that make a member the head's child for the child-coverage check.
_HEAD_CHILD_RELATIONSHIPS = frozenset({"child", "stepChild", "grandChild"})


class FederalMedicaid(PolicyEngineMembersCalculator, abstract=True):
    """Medicaid's core eligibility groups, valued by the state's spending per enrollee.

    A state subclass sets ``program_code``, its state code input, its
    ``group_spend_per_fye_enrollee`` and the elections the spec leaves to the state.
    """

    pe_name = "medicaid"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.PregnancyDependency,
        dependency.member.SsiCountableResourcesDependency,
        *MAGI_INCOME_INPUTS,
        dependency.member.IsMedicareEligibleDependency,
        dependency.member.OwnSsdiDisabilityDependency,
        dependency.member.OwnSsdiNotEngagedInSgaDependency,
        *_RECEIPT_INPUTS,
    ]
    pe_outputs = [
        dependency.member.AgeDependency,
        dependency.member.Medicaid,
        dependency.member.MedicaidCategory,
        dependency.member.MedicaidSeniorOrDisabled,
    ]

    # Annual Medicaid benefit spending per full-year-equivalent full-benefit enrollee, by
    # spending group: the state's row of MACStats Exhibit 22. A group with no entry has no
    # figure, and a member in it is valued at nothing rather than at a guess.
    group_spend_per_fye_enrollee: ClassVar[dict[str, int]] = {}

    aged_min_age = 65
    # Below this age a member on the parent/caretaker route is in the child spending group.
    adult_min_age = 19

    # {expansion_child_coverage_age}: a parent or caretaker in the expansion group needs every
    # child under this age to have coverage. None leaves the check off, for a state whose spec
    # does not supply it.
    expansion_child_coverage_age: ClassVar[Optional[int]] = None
    # {caretaker_non_relative_option}: whether the state counts a non-relative caring for a
    # child as a caretaker, which brings the head's foster child into the check.
    caretaker_non_relative_option: ClassVar[bool] = False

    # {pregnancy_services_only_option} and {postpartum_extension_option}. §7 gives a pregnant
    # woman no figure where the state limits coverage above an income line to pregnancy-related
    # services and has no postpartum extension. Telling those women apart needs that income line,
    # which no state on this base supplies yet, so such a state is refused rather than priced.
    pregnancy_services_only_option: ClassVar[bool] = False
    postpartum_extension_option: ClassVar[bool] = True

    # PolicyEngine's categories, by the spending group §7's route table gives them. PARENT and
    # the two aged/blind/disabled categories split by age, so they are handled in
    # ``spending_group``. A category with no group here (YOUNG_ADULT, MEDICALLY_NEEDY and
    # PolicyEngine's other optional or state categories) is not a route this base evaluates.
    category_groups: ClassVar[dict[str, str]] = {
        "INFANT": CHILD,
        "YOUNG_CHILD": CHILD,
        "OLDER_CHILD": CHILD,
        "ADULT": NEW_ADULT,
        "PREGNANT": OTHER_ADULT,
    }
    aged_disabled_categories = ("SSI_RECIPIENT", "SENIOR_OR_DISABLED")
    expansion_category = "ADULT"

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        unknown = set(cls.group_spend_per_fye_enrollee) - set(SPENDING_GROUPS)
        if unknown:
            raise ValueError(f"{cls.__name__} prices unknown spending groups: {sorted(unknown)}")
        if cls.pregnancy_services_only_option and not cls.postpartum_extension_option:
            raise NotImplementedError(
                f"{cls.__name__}: pregnancy-related-services-only coverage without a postpartum "
                "extension has no figure above the full-coverage income limit, which this base "
                "does not yet compare against"
            )
        if cls.expansion_child_coverage_age is not None:
            # The child-coverage check reads each child's insurance and relationship, so a screen
            # without them can't be answered.
            cls.dependencies = tuple(sorted(set(cls.dependencies) | {"insurance", "relationship", "age"}))

    def member_value(self, member: HouseholdMember) -> int:
        """Annual value for one member: their spending group's figure, or 0 if not eligible."""
        group = None
        if self.get_member_variable(member.id) > 0:
            category = self.get_member_dependency_value(dependency.member.MedicaidCategory, member.id)
            if category != self.expansion_category or self.expansion_child_coverage_met(member):
                group = self.spending_group(category, member)

        # The route PolicyEngine picked gave no figure: a category this base doesn't price, a
        # senior PolicyEngine placed in the expansion group, or a parent who failed the
        # child-coverage check. A member who meets ``aged_or_disabled`` and passes PolicyEngine's
        # aged/disabled income and asset tests is still eligible through that route.
        if group is None and self.meets_aged_or_disabled(member):
            if self.get_member_dependency_value(dependency.member.MedicaidSeniorOrDisabled, member.id):
                group = self.aged_disabled_group(member)

        if group is None:
            return 0
        return self.group_spend_per_fye_enrollee.get(group, 0)

    def spending_group(self, category: str, member: HouseholdMember) -> Optional[str]:
        """§7's spending group for the route PolicyEngine placed the member in."""
        age = member.calc_age()

        if category == self.expansion_category and age is not None and age >= self.aged_min_age:
            # The expansion group is 19–64 (``expansion_age_19_to_64``).
            return None
        if category in self.aged_disabled_categories:
            return self.aged_disabled_group(member)
        if category == "PARENT":
            return CHILD if age is not None and age < self.adult_min_age else OTHER_ADULT
        return self.category_groups.get(category)

    def aged_disabled_group(self, member: HouseholdMember) -> str:
        """Aged at 65 and over, disabled under it (§7, MACStats Exhibit 22 notes)."""
        age = member.calc_age()
        return AGED if age is not None and age >= self.aged_min_age else DISABLED

    def meets_aged_or_disabled(self, member: HouseholdMember) -> bool:
        """``aged_or_disabled``: 65 or older, or the member's own Social Security Disability Benefits."""
        age = member.calc_age()
        return (age is not None and age >= self.aged_min_age) or member_reports_ssdi_amount(member)

    def expansion_child_coverage_met(self, member: HouseholdMember) -> bool:
        """``expansion_parent_child_coverage``.

        A head of household or the head's spouse fails when a child of the head under the
        state's age has no coverage, or doesn't know. The head's foster child counts where the
        state counts non-relative caretakers. Everyone else passes: relationships are recorded
        only to the head.
        """
        if self.expansion_child_coverage_age is None:
            return True
        if member.relationship not in ("headOfHousehold", "spouse"):
            return True

        child_relationships = set(_HEAD_CHILD_RELATIONSHIPS)
        if self.caretaker_non_relative_option:
            child_relationships.add("fosterChild")

        for other in self.screen.household_members.all():
            if other.id == member.id or other.relationship not in child_relationships:
                continue
            age = other.calc_age()
            if age is None or age >= self.expansion_child_coverage_age:
                continue
            # ``none`` matches ``dont_know`` too (``Insurance.has_insurance_types``).
            if other.has_insurance_types(("none",), strict=False):
                return False
        return True
