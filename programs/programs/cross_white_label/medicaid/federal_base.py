"""The federal Medicaid base: PolicyEngine's Medicaid, fed the inputs the federal base spec settles.

Spec: program-ops ``programs/cross_white_label/medicaid/base/medicaid_base_spec.md``, with its
decision record in ``decisions.md`` beside it.

This sits beside ``base.py`` rather than replacing it. The states built on ``Medicaid`` there,
and the CHIP, ACA, Medicare Savings Program and DART calculators that reuse its PolicyEngine
inputs, keep it until each state's spec is backfilled into program-ops; they then move here
together. Until then only a state with a program-ops spec subclasses this one.

A pure PolicyEngine calculator: PolicyEngine decides who is eligible and what each member's
coverage is worth (its ``medicaid`` variable), and nothing is layered on its answer. The spec's
rules reach it only through the inputs sent. Where they differ from ``Medicaid.pe_inputs``:

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

Where PolicyEngine's answer departs from the spec — the child-coverage condition on the adult
group, the strict asset limit, counting another pregnant member, its own valuation method — it
is left to PolicyEngine to fix rather than corrected here.
"""

import programs.framework.pe_dependencies as dependency
from programs.framework.pe_base import PolicyEngineMembersCalculator

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
    """Medicaid as PolicyEngine answers it. Each member's value is PolicyEngine's ``medicaid``.

    A state subclass sets ``program_code`` and adds its state code and county inputs (the county
    sets the rating area PolicyEngine prices coverage against).
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
    pe_outputs = [dependency.member.Medicaid]
