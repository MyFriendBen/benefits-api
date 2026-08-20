"""MO TANF."""

from programs.programs.cross_white_label.tanf.base import Tanf
import programs.framework.pe_dependencies as dependency


class MoTanf(Tanf):
    """
    Missouri Temporary Assistance (TA) — the state's TANF cash grant.

    PolicyEngine's ``mo_tanf`` carries the whole determination. It builds the Missouri
    need unit (``mo_tanf_is_assistance_unit_member``, excluding SSI recipients per
    13 CSR 40-2.310(1)(F)), applies all three of Missouri's income gates — 185% Gross Max,
    Standard of Need, and Percentage of Need — and returns the monthly grant as the
    payment standard less fully-disregarded countable income, floored at Missouri's $10
    minimum payment.

    Both earned-income disregard sequences are PolicyEngine's too, applied per earner
    rather than to combined household earnings (13 CSR 40-2.310(9)(A), (9)(D); DSS Manual
    0210.015.30.10). Which one a member gets turns on whether they were an active TA
    participant when employment began, which PolicyEngine reads from ``is_tanf_enrolled``
    — a variable that defaults to ``receives_tanf``. So the ``receipt_contract`` inherited
    from ``Tanf`` selects the sequence: a household reporting TA gets the two-thirds
    disregard, one that doesn't gets $90 → $30-plus-⅓.

    Inputs beyond the federal base:

    - ``MoStateCodeDependency`` — every ``mo_tanf`` variable is ``defined_for
      StateCode.MO``, and ``pe_input()`` never sends ``state_code`` on its own.
    - ``PregnancyDependency`` — Missouri requires a dependent child and RSMo 208.040
      grants nothing on pregnancy alone, so this does not open eligibility here. It is
      sent because the inherited federal chain reads it, keeping this household's payload
      consistent with the other cash programs computed alongside it.
    - ``*irs_gross_income`` — person-level earned and unearned income, which
      ``mo_tanf_gross_earned_income`` / ``_unearned_income`` sum over unit members. Sent
      per person rather than pre-aggregated so PolicyEngine can run each earner's
      disregard separately and apply the student-child and teen-parent exclusions
      (``is_mo_tanf_earned_income_exempt``) to the right member's earnings.
    - ``NonSsiBankAccountAssetsDependency`` — the $1,000 resource test
      (``mo_tanf_resources_eligible``). Sent per member, not as the
      ``spm_unit_cash_assets`` aggregate, so PolicyEngine's SSI-resource exclusion can
      fire; see that dependency for why the aggregate defeats it.
    - ``ChildCareDependency`` / ``CareExpensesDependency`` /
      ``IsIncapableOfSelfCareDependency`` — the care-cost deduction at Gate 3
      (13 CSR 40-2.310(9)(A)5): $200/month for a child under 2, $175 for a child 2 or
      older, $175 per incapacitated adult. ``mo_tanf_child_care_deduction`` reads
      ``childcare_expenses`` and person-level ``care_expenses``, and caps each at the
      applicable per-person rate; without these the deduction never applies and the grant
      is understated.
    - ``AgeDependency`` (inherited) — drives ``monthly_age`` for the dependent-child test
      and the care-deduction age brackets.
    - ``TaxUnitDependentDependency`` — load-bearing in both directions, because
      ``mo_tanf_dependent_child`` reads ``is_tax_unit_dependent | is_child`` and the
      caretaker test requires a dependent child somewhere in the tax unit. Left to
      PolicyEngine's own inference, an 18-year-old child comes back ``False``, which drops
      both that child *and* their caretaker from the unit, denying the household outright
      (verified against live PE: unit size 0). A 19-year-old goes the other way and is
      counted as a second caretaker, inflating the payment standard by one size band.

    Three Missouri rules PolicyEngine does not model are shipped as disclosed gaps rather
    than corrected here, so that every number this calculator returns is PolicyEngine's:
    the $5,000 IEP resource tier (PE applies a flat $1,000), the new-spouse income
    disregard (PE counts a new spouse's income like any other member's), and the
    non-parent-caretaker neediness/inclusion election (PE evaluates the household as
    reported, with the caretaker included). See specs/mo.md.
    """

    program_code = "mo_tanf"

    pe_name = "mo_tanf"
    pe_inputs = [
        *Tanf.pe_inputs,
        dependency.household.MoStateCodeDependency,
        dependency.member.PregnancyDependency,
        dependency.member.TaxUnitDependentDependency,
        dependency.member.InSecondarySchoolDependency,
        *dependency.irs_gross_income,
        dependency.member.NonSsiBankAccountAssetsDependency,
        dependency.spm.ChildCareDependency,
        dependency.member.CareExpensesDependency,
        dependency.member.IsIncapableOfSelfCareDependency,
    ]

    pe_outputs = [dependency.spm.MoTanf]
