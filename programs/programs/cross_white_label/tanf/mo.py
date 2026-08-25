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

    ``CashAssetsDependency`` sends the household's reported assets for the resource test. An
    SSI recipient's resources are excluded from it, but their share of the single reported
    total cannot be isolated and the input is shared with every other program on the screen,
    so the exclusion is not applied — see specs/mo.md Criterion 7 and MFB-1696.

    Income goes per person via ``tanf_income``, added here rather than on the base: CO, IL and
    NC send pre-aggregated state countable-income variables and would double-count. Per person
    so PE can run each earner's disregard separately and apply the student exclusions to the
    right member.
    """

    program_code = "mo_tanf"

    pe_name = "mo_tanf"
    pe_inputs = [
        *Tanf.pe_inputs,
        dependency.household.MoStateCodeDependency,
        dependency.member.PregnancyDependency,
        dependency.member.TaxUnitDependentDependency,
        dependency.spm.CashAssetsDependency,
        # mo_tanf_child_care_deduction reads the spm-level childcare total and person-level
        # care_expenses, capped per person; is_incapable_of_self_care selects the adult tier.
        dependency.spm.ChildCareDependency,
        dependency.member.CareExpensesDependency,
        dependency.member.IsIncapableOfSelfCareDependency,
        *dependency.tanf_income,
    ]

    pe_outputs = [dependency.spm.MoTanf]
