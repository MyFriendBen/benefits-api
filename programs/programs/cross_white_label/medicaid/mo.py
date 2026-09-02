"""MO Medicaid."""

from programs.programs.cross_white_label.medicaid.base import Medicaid
import programs.framework.pe_dependencies as dependency


class MoHealthNet(Medicaid):
    """MO HealthNet is Missouri's Medicaid program (subclass of the federal ``medicaid`` calculator).

    Missouri adopted ACA adult expansion, so PE covers adults 19-64 up to 138% FPL
    (``adult/income_limit.yaml[MO] = 2021-10-01: 1.38``, current). Children, pregnant
    people, parents/caretakers, and the aged/blind/disabled route through their own
    PE categories.

    Each pathway's income ceiling was verified against Missouri's published standards by
    bisecting it on a live screener, and they agree - including a blind MHABD standard
    distinct from the aged/disabled one. Missouri publishes *monthly* limits rounded up to
    the whole dollar while eligibility is tested on annualized income, so entering a
    published monthly limit exactly lands just above the annual limit; that is a units
    artifact rather than an off-by-one comparator.

    Known divergences from Missouri's standards, deliberately not patched here so that
    PolicyEngine stays the single source of the eligibility decision:

    - MHABD subtracts the general income exclusion before halving earned income (SSI
      ordering) rather than after, as Missouri's own sequence does, which lowers a wage
      earner's MHABD ceiling. Requested upstream.
    - The parent/caretaker limit is stored as a percent of FPL rather than Missouri's flat
      1996-AFDC dollar standard, which is not FPL-indexed. Not isolated by measurement:
      the adult-expansion ceiling is far higher, so a parent failing the flat standard is
      still found eligible through expansion.
    - No Substantial Gainful Activity test gates the disability pathways. Not measured.

    Two behaviours are ours rather than PolicyEngine's, both in ``Medicaid.member_value``
    and shared by every Medicaid state, so neither is worked around here: a member who
    reports a disability and fails the aged/disabled pathway is not then evaluated for
    adult expansion, and a member who is both 65+ and disabled is valued at the disabled
    rather than the senior rate.
    """

    program_code = "mo_medicaid"

    pe_inputs = [
        *Medicaid.pe_inputs,
        # PolicyEngine needs these to classify a member as SSI-disabled or blind, which is what
        # gates the aged/disabled (MHABD) pathway. Declared here rather than relied on from a
        # sibling program: PolicyEngine inputs are pooled per request, so while mo_ssi happens to
        # send both today, a request without it would resolve
        # is_optional_senior_or_disabled_for_medicaid to False and return $0 for a disabled
        # applicant. Mirrors KsKanCare. Both only ever widen eligibility - they feed an OR.
        dependency.member.MeetsSsiDisabilityCriteriaDependency,
        dependency.member.IsBlindDependency,
        dependency.household.MoStateCodeDependency,
    ]

    # KFF's published annual spend per full-benefit MO enrollee, whose groups are mutually
    # exclusive by age, disability eligibility, and expansion status.
    KFF_CHILDREN = 4_576  # age 18 and under, not disability-eligible
    KFF_ADULTS = 6_379  # 19-64, not disability-eligible, not expansion
    KFF_EXPANSION_ADULTS = 7_445  # 19-64, newly eligible via ACA expansion
    KFF_SENIORS = 21_857  # 65+, regardless of disability
    KFF_DISABLED = 30_410  # under 65, disability-eligible

    # NOTE: Monthly - stored as annual/12 so member_value's * 12 restores the published
    # figure exactly, which a rounded whole-dollar rate would not.
    medicaid_categories = {
        "NONE": 0,
        # ADULT is the expansion group, while the mandatory pre-expansion categories take
        # precedence over it and so keep the lower non-expansion rate.
        "ADULT": KFF_EXPANSION_ADULTS / 12,
        "YOUNG_ADULT": KFF_ADULTS / 12,
        "PARENT": KFF_ADULTS / 12,
        "PREGNANT": KFF_ADULTS / 12,
        "INFANT": KFF_CHILDREN / 12,
        "YOUNG_CHILD": KFF_CHILDREN / 12,
        "OLDER_CHILD": KFF_CHILDREN / 12,
        "SSI_RECIPIENT": KFF_DISABLED / 12,
        "AGED": KFF_SENIORS / 12,
        "DISABLED": KFF_DISABLED / 12,
    }
