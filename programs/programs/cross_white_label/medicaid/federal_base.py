"""The federal Medicaid base: PolicyEngine's Medicaid, fed the inputs the federal base spec settles.

Spec: program-ops ``programs/cross_white_label/medicaid/base/medicaid_base_spec.md``, with its
decision record in ``decisions.md`` beside it.

This sits beside ``base.py`` rather than replacing it. The states built on ``Medicaid`` there,
and the CHIP, ACA, Medicare Savings Program and DART calculators that reuse its PolicyEngine
inputs, keep it until each state's spec is backfilled into program-ops; they then move here
together. Until then only a state with a program-ops spec subclasses this one.

PolicyEngine decides who is eligible (its ``medicaid`` variable), and MFB sets the value: each
eligible member gets §7's figure for their spending group, the state's average spending per
full-year enrollee in that group, as every Medicaid calculator on ``base.py`` does. The spec's
eligibility rules reach PolicyEngine only through the inputs sent. Where they differ from
``Medicaid.pe_inputs``:

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

Where PolicyEngine's eligibility departs from the spec — the child-coverage condition on the
adult group, the strict asset limit, counting another pregnant member — it is left to PolicyEngine
to fix rather than corrected here.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import ClassVar, Optional

import programs.framework.pe_dependencies as dependency
from programs.framework.pe_base import PolicyEngineMembersCalculator
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


class FederalMedicaid(PolicyEngineMembersCalculator, abstract=True):
    """Medicaid's eligibility as PolicyEngine answers it, valued by §7's spending groups.

    A state subclass sets ``program_code``, adds its state code input and sets
    ``group_spend_per_fye_enrollee``.
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
    pe_outputs = [dependency.member.Medicaid, dependency.member.MedicaidCategory]

    # Annual Medicaid benefit spending per full-year-equivalent full-benefit enrollee, by
    # spending group: the state's row of MACStats Exhibit 22. A group with no entry has no
    # figure, and a member in it is valued at nothing rather than at a guess.
    group_spend_per_fye_enrollee: ClassVar[dict[str, int]] = {}

    aged_min_age = 65
    # Below this age a member on the parent/caretaker route is in the child spending group.
    adult_min_age = 19

    # PolicyEngine's categories, by the spending group §7's route table gives them. PARENT and
    # the two aged/blind/disabled categories split by age, so they are handled in
    # ``spending_group``. A category with no group here (YOUNG_ADULT, MEDICALLY_NEEDY and
    # PolicyEngine's other optional or state categories) has no §7 figure.
    category_groups: ClassVar[dict[str, str]] = {
        "INFANT": CHILD,
        "YOUNG_CHILD": CHILD,
        "OLDER_CHILD": CHILD,
        "ADULT": NEW_ADULT,
        "PREGNANT": OTHER_ADULT,
    }
    aged_disabled_categories = ("SSI_RECIPIENT", "SENIOR_OR_DISABLED")

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        unknown = set(cls.group_spend_per_fye_enrollee) - set(SPENDING_GROUPS)
        if unknown:
            raise ValueError(f"{cls.__name__} prices unknown spending groups: {sorted(unknown)}")

    def member_value(self, member: HouseholdMember) -> int:
        """Annual value for one member PolicyEngine finds eligible: their spending group's monthly
        figure, rounded to the nearest dollar (half up), × 12. 0 if PolicyEngine finds them
        ineligible or the group has no figure."""
        if self.get_member_variable(member.id) <= 0:
            return 0
        category = self.get_member_dependency_value(dependency.member.MedicaidCategory, member.id)
        group = self.spending_group(category, member)
        if group is None or group not in self.group_spend_per_fye_enrollee:
            return 0
        monthly = Decimal(self.group_spend_per_fye_enrollee[group]) / 12
        return int(monthly.quantize(Decimal("1"), rounding=ROUND_HALF_UP)) * 12

    def spending_group(self, category: str, member: HouseholdMember) -> Optional[str]:
        """§7's spending group for the route PolicyEngine placed the member in."""
        if category in self.aged_disabled_categories:
            return self.aged_disabled_group(member)
        if category == "PARENT":
            age = member.calc_age()
            return CHILD if age is not None and age < self.adult_min_age else OTHER_ADULT
        return self.category_groups.get(category)

    def aged_disabled_group(self, member: HouseholdMember) -> str:
        """Aged at 65 and over, disabled under it (§7, MACStats Exhibit 22 notes)."""
        age = member.calc_age()
        return AGED if age is not None and age >= self.aged_min_age else DISABLED
