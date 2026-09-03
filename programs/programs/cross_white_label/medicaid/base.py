"""Medicaid."""

from screener.models import HouseholdMember
from programs.framework.pe_base import PolicyEngineMembersCalculator
import programs.framework.pe_dependencies as dependency


class Medicaid(PolicyEngineMembersCalculator, abstract=True):
    pe_name = "medicaid"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.PregnancyDependency,
        dependency.member.SsiCountableResourcesDependency,
        dependency.member.IsDisabledDependency,
        *dependency.irs_gross_income,
        # medicaid_category has an SSI-recipient pathway, which must not fire off
        # simulated SSI.
        *dependency.receipt_contract,
    ]
    pe_outputs = [
        dependency.member.AgeDependency,
        dependency.member.Medicaid,
        dependency.member.MedicaidCategory,
        dependency.member.MedicaidSeniorOrDisabled,
    ]

    # NOTE: Monthly
    medicaid_categories = {
        "NONE": 0,
        "ADULT": 0,
        "INFANT": 0,
        "YOUNG_CHILD": 0,
        "OLDER_CHILD": 0,
        "PREGNANT": 0,
        "YOUNG_ADULT": 0,
        "PARENT": 0,
        "SSI_RECIPIENT": 0,
        "AGED": 0,
        "DISABLED": 0,
    }

    aged_min_age = 65

    # PolicyEngine categories that mean "eligible on an age or disability basis". Neither
    # distinguishes aged from disabled - SENIOR_OR_DISABLED names both in one value, and
    # SSI_RECIPIENT says only that SSI receipt is the route - so the value tier for these has
    # to come from the member's own age and disability flags. See ``abd_value``.
    abd_categories = ("SENIOR_OR_DISABLED", "SSI_RECIPIENT")

    # ACA expansion is a 19-64 group (42 CFR 435.119), so a member past ``aged_min_age`` must
    # never be valued at an expansion rate even if PolicyEngine hands one back. Other MAGI
    # categories have no upper age bound - a 66-year-old can genuinely be a Sec. 1931
    # parent/caretaker - so only the expansion groups are excluded.
    expansion_categories = ("ADULT", "YOUNG_ADULT")

    # How to value a member who is both 65+ and disability-eligible.
    #
    # False (the default) keeps the disabled rate, which is what the per-enrollee spending
    # tables the earlier states were built from assume: they publish "age 65 and older" and
    # "with a disability" as disjoint groups with disability taking precedence, and
    # specs/ks.md commits to that reading.
    #
    # States whose own spec says age wins - KFF publishes Seniors as 65+ regardless of
    # disability - set this True. Left per-state rather than made uniform because the two
    # committed specs disagree and each is right about its own source table.
    senior_value_takes_precedence = False

    def abd_value(self, is_senior: bool, is_disabled: bool):
        """Annual value for a member eligible on the aged/blind/disabled basis.

        The aged rate belongs to seniors; everyone else on this pathway takes the disabled
        rate, including a member PolicyEngine reports as an SSI recipient who set no
        disability flag on the screener - SSI receipt is itself the disability signal there.
        """
        if is_senior and (self.senior_value_takes_precedence or not is_disabled):
            return self.medicaid_categories["AGED"] * 12
        return self.medicaid_categories["DISABLED"] * 12

    def member_value(self, member: HouseholdMember):
        # PolicyEngine answers Medicaid over two pathways, and a member can clear either:
        #
        # 1. ``medicaid`` - the ordinary MAGI pathways (expansion, parent/caretaker,
        #    pregnant, children), with ``medicaid_category`` naming which group applied.
        # 2. ``is_optional_senior_or_disabled_for_medicaid`` - the optional aged/disabled
        #    pathway, at state-specific thresholds (typically 74-100% FPL).
        #
        # PolicyEngine's own routing decides the group. Reading the ABD pathway first would
        # discard it: a disabled adult whom PE placed in ADULT would be valued at the disabled
        # rate, and one who failed ABD would be dropped entirely despite PE finding them
        # eligible under expansion. So the ordinary pathway is consulted first, and the ABD
        # pathway is the fallback for the members it does not reach.
        age = member.calc_age()
        is_senior = age is not None and age >= self.aged_min_age
        is_disabled = member.has_disability()

        if self.get_member_variable(member.id) > 0:
            medicaid_category = self.get_member_dependency_value(dependency.member.MedicaidCategory, member.id)

            if medicaid_category in self.abd_categories:
                return self.abd_value(is_senior, is_disabled)

            if not (is_senior and medicaid_category in self.expansion_categories):
                # .get rather than [] because medicaid_categories covers only the categories we
                # price. PolicyEngine's enum is larger and grows: MEDICALLY_NEEDY,
                # WORKING_DISABLED_BUY_IN and SECTION_1115_MEC_ADULT have no key here, and a
                # state whose covered-category list includes one would raise KeyError out of
                # member_value - which fails the whole eligibility request, not just this
                # program.
                value = self.medicaid_categories.get(medicaid_category, 0) * 12
                if value > 0:
                    return value

        # Fallback, reached when the ordinary pathway found nothing this state prices: an
        # unrecognised category, a category priced at 0, or a senior PE routed to expansion.
        # A member eligible on the aged/disabled basis is still eligible.
        if is_senior or is_disabled:
            qualifies_via_aged_disabled_pathway = self.get_member_dependency_value(
                dependency.member.MedicaidSeniorOrDisabled, member.id
            )
            if qualifies_via_aged_disabled_pathway:
                return self.abd_value(is_senior, is_disabled)

        return 0
