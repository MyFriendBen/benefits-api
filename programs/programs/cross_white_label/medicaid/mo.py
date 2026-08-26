"""MO Medicaid."""

from programs.programs.cross_white_label.medicaid.base import Medicaid
import programs.framework.pe_dependencies as dependency


class MoHealthNet(Medicaid):
    """MO HealthNet is Missouri's Medicaid program (subclass of the federal ``medicaid`` calculator).

    Missouri adopted ACA adult expansion, so PE covers adults 19-64 up to 138% FPL
    (``adult/income_limit.yaml[MO] = 2021-10-01: 1.38``, current). Children, pregnant
    people, parents/caretakers, and the aged/blind/disabled route through their own
    PE categories.

    PE's income limits were measured against Missouri's published standards by bisecting
    each pathway's ceiling on a live screener. They agree - the boundaries below are PE's,
    and each matches the corresponding MO DSS figure once you account for DSS publishing
    the *monthly* equivalent rounded up to the whole dollar:

    - Adult expansion: 138% FPL. HH1 boundary $1,835/mo (1.38 * $15,960 = $22,024.80/yr,
      i.e. $1,835.40/mo); DSS Appendix A publishes $1,836.
    - Children 1-18: 153% FPL, matching Missouri's 148% nominal plus the 5% MAGI
      disregard. HH2 boundary $2,759/mo (1.53 * $21,640 = $33,109.20/yr); DSS publishes
      $2,760.
    - Infants under 1 and pregnant people: 201% FPL, which is Missouri's 196% nominal
      plus the 5% disregard. HH2 boundary $3,624/mo (2.01 * $21,640 = $43,496.40/yr);
      DSS publishes $3,625. The pregnant boundary equals the HH2 infant boundary, which
      confirms PE counts the unborn child in the pregnant applicant's own unit.
    - MHABD aged/disabled: 85% FPG, $13,566/yr = $1,130.50/mo; DSS publishes $1,131.
    - MHABD blind: 100% FPG, $15,960/yr = $1,330/mo, matching DSS exactly. PE does have a
      blind-specific standard distinct from the aged/disabled one.

    Because DSS rounds the monthly figure up while eligibility is tested on annualized
    income, entering a DSS-published monthly limit exactly lands a few dollars above the
    annual limit. That is a units artifact, not an off-by-one in the comparator.

    Known divergences from Missouri's standards, deliberately not patched here so that
    PolicyEngine stays the single source of the eligibility decision:

    - MHABD applies the $20 general income exclusion before halving earned income
      (SSI ordering, ``(earned - 65 - 20) / 2``) rather than after, as Missouri's own
      sequence does (``(earned - 65) / 2 - 20``). Worth $10/mo of countable income, so a
      wage earner's MHABD ceiling sits about $21/mo of gross earnings below Missouri's.
      Requested upstream.
    - The parent/caretaker limit is stored as a percent of FPL rather than Missouri's flat
      1996-AFDC dollar standard, which is not FPL-indexed. Not isolated by measurement:
      the adult-expansion ceiling is far higher, so a parent failing the flat standard is
      still found eligible through expansion.
    - No Substantial Gainful Activity test gates the disability pathways. Not measured.

    Two behaviours that are ours rather than PolicyEngine's, both in
    ``Medicaid.member_value`` and shared by every Medicaid state, so neither is worked
    around here:

    - A member who reports any disability and fails the PE aged/disabled pathway returns
      $0 without being evaluated for adult expansion, even when their income is under the
      expansion ceiling.
    - A member who is both 65+ and reports a disability is valued at the disabled rate
      rather than the senior rate, because the disability branch is tested first.
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

    # KFF Medicaid Spending per Full-Benefit Enrollee by Enrollment Group, MO, 2023
    # preliminary - the Full-Benefit table, because this calculator represents full-scope
    # MO HealthNet coverage. KFF's groups are mutually exclusive by age, disability
    # eligibility, and expansion status. These are the published *annual* figures.
    KFF_CHILDREN = 4_576  # age 18 and under, not disability-eligible
    KFF_ADULTS = 6_379  # 19-64, not disability-eligible, not expansion
    KFF_EXPANSION_ADULTS = 7_445  # 19-64, newly eligible via ACA expansion
    KFF_SENIORS = 21_857  # 65+, regardless of disability
    KFF_DISABLED = 30_410  # under 65, disability-eligible

    # NOTE: Monthly - Medicaid.member_value multiplies by 12. Stored as annual/12 rather
    # than a rounded whole-dollar monthly rate: rounding the monthly figure moves the
    # annual value we report by up to $5 away from KFF's published number.
    medicaid_categories = {
        "NONE": 0,
        # Missouri expanded, so PE's ADULT category is the expansion group and carries
        # KFF's higher expansion rate. PARENT and PREGNANT are mandatory pre-expansion
        # categories and take precedence over it, so they keep the non-expansion rate -
        # which is also what makes a parent found through MHF distinguishable from one
        # found through expansion.
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
