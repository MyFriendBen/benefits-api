"""
Discrepancy demonstration, not a fix. CO/IL/NC's production TANF calculators
(co/pe/spm.py, il/pe/spm.py, nc/pe/spm.py) each override PolicyEngine's own
real, state-specific countable-income formula
(co_tanf_countable_gross_unearned_income / il_tanf_countable_gross_earned_income
/ il_tanf_countable_unearned_income / nc_tanf_countable_gross_unearned_income)
with a value independently computed by this codebase's own
Screen.calc_gross_income() -- rather than supplying raw inputs and letting
PolicyEngine compute them. No commit message or spec.md anywhere in this
repo explains why (checked via git log -S/git blame).

Compared directly against PolicyEngine's real, cited source
(github.com/PolicyEngine/policyengine-us) before writing this file: the two
approaches are NOT equivalent, in different ways per state -- and CO's and
NC's overrides are NOT identical to each other either (checked directly,
not assumed): CO's exclude list is only ["cashAssistance"], NC's is
["sSI", "gifts", "cashAssistance", "cOSDisability"] -- so NC's override
already happens to exclude gift income the same way PolicyEngine's real
formula does, coincidentally or not, while CO's doesn't. Each state below
uses its own genuinely divergent case, not a copy-pasted one --

- CO: PolicyEngine's real formula sums a specific, cited, parameter-driven
  list of income types (gov/states/co/cdhs/tanf/income/unearned.yaml, cited to
  9 CCR 2503-6 Section 3.605.3) -- "gifts" income is not on that list at all.
  The override instead counts every screener income type tagged "unearned"
  except a blanket "cashAssistance" exclusion, so gift income IS counted here
  but is invisible to PolicyEngine's real formula entirely.
- NC: PolicyEngine's real formula (gov/states/nc/ncdhhs/tanf/income/unearned.yaml,
  cited to NC's WORK FIRST Change No. 04-2023) omits workers_compensation and
  disability_benefits entirely, unlike CO's list which includes both. NC's
  override doesn't exclude workers' comp either, so it's counted here but
  ignored by PolicyEngine's real formula.
- IL: PolicyEngine's real formula (il_tanf_countable_gross_earned_income/
  il_tanf_countable_unearned_income, cited to Ill. Admin. Code tit. 89
  Section 112.101) counts only the tax-unit head-or-spouse's income
  (is_tax_unit_head_or_spouse). The override sums the *entire household's*
  income via Screen.calc_gross_income with no head/spouse restriction --
  meaning a working child's own earned income is counted here but would be
  excluded by PolicyEngine's real formula.

This file changes nothing in production code. Each *TrustingPolicyEngine
class below is a local, test-only subclass that swaps the override
dependency for the raw dependencies PolicyEngine's own formula actually
needs (all of which already exist generically in this codebase --
EmploymentIncomeDependency, TaxUnitHeadDependency, etc. -- confirmed before
writing this, not assumed), then reads the same real household_value() the
shipped calculator would, through the same real calc_pe_eligibility() entry
point and DockerApiSim VCR convention this repo's own parity harness
(programs/programs/factories/tests/test_snap_parity.py) already uses.

Deciding which behavior is *correct* -- and fixing it -- is left to
MyFriendBen; the two divergence patterns below (CO/NC's missing-income-type
omission and IL's household-vs-head-or-spouse scope) may have been
deliberate simplifications, not necessarily bugs, though no documentation
anywhere states that. This file's job is only to make the divergence
concrete and provable with real numbers, not to argue which side is right.

Run: pytest -m integration <this file>
"""

from unittest.mock import patch

import pytest

from programs.models import FederalPoveryLimit, Program
from programs.programs.co.pe.spm import CoTanf
from programs.programs.il.pe.spm import IlTanf
from programs.programs.nc.pe.spm import NcTanf
from programs.programs.policyengine.calculators.dependencies import member
from programs.programs.policyengine.engines import ApiSim
from programs.programs.policyengine.policy_engine import calc_pe_eligibility
from screener.models import WhiteLabel
from screener.serializers import ScreenSerializer

RESOLVED_COMPARABLE_VERSION = (1, 755, 0)  # same cited constant as this repo's own SNAP parity-style tests


class DockerApiSim(ApiSim):
    """Test-only Sim pointed at a local self-hosted PolicyEngine Docker
    container instead of the real hosted API -- avoids depending on any
    hosted PolicyEngine credentials for this demonstration. engines.py is
    not touched; this is a local, test-only subclass."""

    pe_url = "http://localhost:8080/us/calculate"


class CoTanfTrustingPolicyEngine(CoTanf):
    """Drops CO's two countable-income override dependencies; adds nothing
    else, since this test's household has only gift income, which maps to
    no PolicyEngine input variable in CO's real unearned.yaml list at all --
    PolicyEngine's own formula legitimately computes $0 countable unearned
    income for it without any additional raw input."""

    pe_inputs = [
        dep
        for dep in CoTanf.pe_inputs
        if dep.field not in ("co_tanf_countable_gross_earned_income", "co_tanf_countable_gross_unearned_income")
    ]


class NcTanfTrustingPolicyEngine(NcTanf):
    """NOT the same list as CO's, checked directly rather than assumed:
    NC's override excludes ["sSI", "gifts", "cashAssistance",
    "cOSDisability"] (dependencies/spm.py), already coincidentally matching
    PolicyEngine's real NC unearned.yaml on gift income specifically. NC's
    real parameter list also omits workers_compensation and
    disability_benefits (unlike CO's list, which includes both) -- a real,
    NC-specific divergence, not one copied from CO's. Adds
    WorkersCompensationDependency explicitly so PolicyEngine actively
    receives and then ignores it (per NC's real formula), rather than the
    weaker demonstration of it being absent from the request entirely."""

    pe_inputs = [
        dep
        for dep in NcTanf.pe_inputs
        if dep.field not in ("nc_tanf_countable_earned_income", "nc_tanf_countable_gross_unearned_income")
    ] + [member.WorkersCompensationDependency]


class IlTanfTrustingPolicyEngine(IlTanf):
    """Drops IL's two countable-income override dependencies; adds the raw
    per-person dependencies PolicyEngine's real formula needs instead --
    EmploymentIncomeDependency (so it sees each member's own wages) and
    TaxUnitHeadDependency/TaxUnitSpouseDependency/TaxUnitDependentDependency
    (so it can derive is_tax_unit_head_or_spouse and correctly exclude a
    dependent child's income) -- all pre-existing, generic dependencies,
    confirmed before writing this, not new Python.

    TaxUnitDependentDependency specifically was added after a first version
    of this test produced a nonsensical result (the "trusting" variant's
    household_value going to $0, when correctly excluding the child's
    income should only ever raise or hold the benefit, never zero it) --
    inspecting the actual recorded request body directly (not trusting the
    number) showed the child, with no dependent-status input, defaulted to
    being placed in its own separate tax unit and became that unit's "head"
    by definition, rather than a dependent of the real head's tax unit. A
    real bug in this test's own household construction, not in
    PolicyEngine -- caught by checking the request body, not the output
    number alone, before writing this file's numbers into a PR."""

    pe_inputs = [
        dep
        for dep in IlTanf.pe_inputs
        if dep.field not in ("il_tanf_countable_gross_earned_income", "il_tanf_countable_unearned_income")
    ] + [
        member.EmploymentIncomeDependency,
        member.TaxUnitHeadDependency,
        member.TaxUnitSpouseDependency,
        member.TaxUnitDependentDependency,
    ]


@pytest.fixture(autouse=True)
def _mock_pe_version_resolution():
    with patch(
        "programs.programs.policyengine.policy_engine.pe_versions.resolve_unpinned_comparable_version",
        return_value=RESOLVED_COMPARABLE_VERSION,
    ):
        yield


def _build_screen(household_dict):
    screen = ScreenSerializer(data={**household_dict, "is_test": True})
    screen.is_valid(raise_exception=True)
    return screen.save()


def _run_shipped_vs_trusting(
    state_code, state_name, postal_code, program_key, household_dict, shipped_cls, trusting_cls
):
    fpl_year = FederalPoveryLimit.objects.create(year="2024", period="2024")
    WhiteLabel.objects.create(name=state_name, code=state_code, state_code=postal_code)

    screen = _build_screen(household_dict)
    program = Program.objects.new_program(white_label=state_code, name_abbreviated=program_key)
    program.year = fpl_year
    program.save()

    missing_dependencies = screen.missing_fields()
    shipped = shipped_cls(screen, program, missing_dependencies)
    trusting = trusting_cls(screen, program, missing_dependencies)

    # Two SEPARATE calc_pe_eligibility() calls, not one combined call with
    # both calculators together -- calc_pe_eligibility() merges every
    # calculator passed to it into one shared household request (D-014's
    # "one Sim" precondition, correct for the parity harness, where old and
    # new are supposed to compute the *same* thing from the *same* inputs).
    # Here the two variants deliberately send DIFFERENT inputs for the same
    # PolicyEngine variable -- combining them into one request would let
    # whichever calculator provides an override value win for both reads,
    # silently hiding the exact divergence this test exists to show
    # (caught by an initial 0-vs-0 failure before this was split out).
    with patch("programs.programs.policyengine.policy_engine.pe_engines", [DockerApiSim]):
        shipped_result = calc_pe_eligibility(screen, {"shipped": shipped})
        trusting_result = calc_pe_eligibility(screen, {"trusting_pe": trusting})
    return (
        shipped_result["eligibility"]["shipped"].household_value,
        trusting_result["eligibility"]["trusting_pe"].household_value,
    )


def _parent_with_qualifying_child_household(state_code, income_type, amount):
    """TANF (its AFDC heritage) requires a dependent child in the household
    to be eligible for any benefit at all, regardless of income -- a single
    childless adult gets $0 both ways, which would look like agreement but
    is really just "both sides fail the categorical test before income ever
    matters," not a real demonstration of anything. Confirmed directly
    (a first version of this test used a single childless adult and got
    0 == 0 for both CO and NC) -- caught before trusting a false "match"."""
    return {
        "white_label": state_code,
        "household_size": 2,
        "zipcode": "00000",
        "county": "Test County",
        "household_assets": 0.0,
        "agree_to_tos": True,
        "is_13_or_older": True,
        "household_members": [
            {
                "relationship": "headOfHousehold",
                "birth_month": 6,
                "birth_year": 1990,
                "age": 35,
                "has_income": True,
                "income_streams": [{"type": income_type, "amount": amount, "frequency": "monthly"}],
                "insurance": {"none": True},
            },
            {
                "relationship": "child",
                "birth_month": 4,
                "birth_year": 2018,
                "age": 8,
                "has_income": False,
                "income_streams": [],
                "insurance": {"none": True},
            },
        ],
        "expenses": [],
    }


@pytest.mark.integration
@pytest.mark.django_db
def test_co_gift_income_counted_by_shipped_calculator_not_by_policyengine():
    """CO: a household whose only income is gift income. The shipped
    calculator counts it as countable unearned income (screener tags
    'gifts' as unearned, and it's not on CO's blanket 'cashAssistance'
    exclusion); PolicyEngine's real formula does not, since 'gifts' isn't on
    CO's cited countable-income parameter list at all."""
    shipped_value, trusting_value = _run_shipped_vs_trusting(
        "co",
        "Colorado",
        "CO",
        "co_tanf",
        _parent_with_qualifying_child_household("co", "gifts", 1000.0),
        CoTanf,
        CoTanfTrustingPolicyEngine,
    )
    assert shipped_value != trusting_value, (
        "Expected CO's shipped TANF calculator and the PolicyEngine-trusting "
        "variant to diverge on a gift-income-only household (D-020) -- if they "
        "match, either PolicyEngine's real unearned.yaml list has since added a "
        "gift-income variable, or this household stopped exercising the "
        "divergence; re-check before assuming the finding is stale."
    )


@pytest.mark.integration
@pytest.mark.django_db
def test_nc_workers_comp_income_counted_by_shipped_calculator_not_by_policyengine():
    """NC: a household whose only unearned income is workers' compensation.
    NC's real countable-income parameter list omits workers_compensation
    entirely (unlike CO's, which includes it) -- checked directly, not
    assumed identical to CO's case. The shipped calculator counts it anyway
    (not on NC's own exclude list), while PolicyEngine's real formula does
    not."""
    shipped_value, trusting_value = _run_shipped_vs_trusting(
        "nc",
        "North Carolina",
        "NC",
        "nc_tanf",
        _parent_with_qualifying_child_household("nc", "workersComp", 1000.0),
        NcTanf,
        NcTanfTrustingPolicyEngine,
    )
    assert shipped_value != trusting_value, (
        "Expected NC's shipped TANF calculator and the PolicyEngine-trusting "
        "variant to diverge on a workers'-compensation-only household "
        "(D-020) -- if they match, either PolicyEngine's real NC parameter "
        "list has since added workers_compensation, or this household "
        "stopped exercising the divergence; re-check before assuming the "
        "finding is stale."
    )


@pytest.mark.integration
@pytest.mark.django_db
def test_il_child_earned_income_counted_by_shipped_calculator_not_by_policyengine():
    """IL: a household where a dependent child (not head-of-household or
    spouse) has their own wages. The shipped calculator sums earned income
    across the whole household, including the child's wages; PolicyEngine's
    real formula counts only the tax-unit head-or-spouse's income, excluding
    the child's wages entirely.

    The head is given real wages too, not $0 -- an earlier version of this
    test gave the head $0 income, which made the child's wages exceed half
    the household's total, and this codebase's own HouseholdMember.is_dependent()
    correctly stops treating a child as a tax dependent once their income
    exceeds that threshold (screener/models.py's qualifying-child test).
    That's a real, separate finding about is_dependent()'s own income
    threshold, not the head-or-spouse-scope divergence this test exists to
    show -- caught by inspecting the actual request body (the child showed
    up as its own tax unit's "head", not a dependent) rather than trusting
    a $0 result at face value. Giving the head some income avoids that
    confound entirely."""
    household_dict = {
        "white_label": "il",
        "household_size": 2,
        "zipcode": "00000",
        "county": "Test County",
        "household_assets": 0.0,
        "agree_to_tos": True,
        "is_13_or_older": True,
        "household_members": [
            {
                "relationship": "headOfHousehold",
                "birth_month": 3,
                "birth_year": 1985,
                "age": 40,
                "has_income": True,
                "income_streams": [{"type": "wages", "amount": 600.0, "frequency": "monthly"}],
                "insurance": {"none": True},
            },
            {
                "relationship": "child",
                "birth_month": 5,
                "birth_year": 2009,
                "age": 16,
                "has_income": True,
                "income_streams": [{"type": "wages", "amount": 300.0, "frequency": "monthly"}],
                "insurance": {"none": True},
            },
        ],
        "expenses": [],
    }
    shipped_value, trusting_value = _run_shipped_vs_trusting(
        "il", "Illinois", "IL", "il_tanf", household_dict, IlTanf, IlTanfTrustingPolicyEngine
    )
    assert shipped_value != trusting_value, (
        "Expected IL's shipped TANF calculator and the PolicyEngine-trusting "
        "variant to diverge when a dependent child has their own earned income "
        "(D-020) -- if they match, re-check before assuming the finding is stale."
    )
