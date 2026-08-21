"""MO TANF."""

from programs.programs.cross_white_label.tanf.base import Tanf
import programs.framework.pe_dependencies as dependency


class MoTanf(Tanf):
    """
    Missouri Temporary Assistance (TA), via PolicyEngine's ``mo_tanf``.

    Eligibility and the grant are PolicyEngine's; see specs/mo.md for the rules and the
    three it does not model. Notes here cover only why each input is sent.

    ``TaxUnitDependentDependency`` is load-bearing and easy to lose:
    ``mo_tanf_dependent_child`` reads ``is_tax_unit_dependent``, and PolicyEngine's own
    inference gets it wrong at both ends of Missouri's age range. An 18-year-old comes back
    not-a-dependent, which drops the child *and* their caretaker from the unit and denies
    the household; a 19-year-old comes back a second caretaker, raising the payment standard
    a size band. (``is_in_secondary_school`` matters here too and is inherited from
    ``Tanf``.)

    ``NonSsiBankAccountAssetsDependency`` replaces ``spm.CashAssetsDependency``: PE's
    SSI-resource exclusion subtracts person-level assets, so the unit aggregate leaves it
    nothing to subtract. Never send both — they write two halves of the same total.

    ``tanf_income`` rather than ``irs_gross_income``, so child support reaches the gates.
    Income goes per person so PE can run each earner's disregard separately and apply the
    student exclusions to the right member.
    """

    program_code = "mo_tanf"

    pe_name = "mo_tanf"
    pe_inputs = [
        *Tanf.pe_inputs,
        dependency.household.MoStateCodeDependency,
        dependency.member.PregnancyDependency,
        dependency.member.TaxUnitDependentDependency,
        dependency.member.NonSsiBankAccountAssetsDependency,
        *dependency.tanf_income,
        # mo_tanf_child_care_deduction reads the spm-level childcare total and person-level
        # care_expenses, capped per person; is_incapable_of_self_care selects the adult tier.
        dependency.spm.ChildCareDependency,
        dependency.member.CareExpensesDependency,
        dependency.member.IsIncapableOfSelfCareDependency,
    ]

    pe_outputs = [dependency.spm.MoTanf]
