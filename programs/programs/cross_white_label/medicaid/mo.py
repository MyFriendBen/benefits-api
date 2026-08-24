"""MO Medicaid."""

from programs.programs.cross_white_label.medicaid.base import Medicaid
import programs.framework.pe_dependencies as dependency


class MoHealthNet(Medicaid):
    """MO HealthNet is Missouri's Medicaid program (subclass of the federal ``medicaid`` calculator).

    Missouri adopted ACA adult expansion, so PE covers adults 19-64 up to 138% FPL
    (``adult/income_limit.yaml[MO] = 2021-10-01: 1.38``, current). Children, pregnant
    people, parents/caretakers, and the aged/blind/disabled route through their own
    PE categories.

    Known PE divergences from Missouri's current FSD standards, all upstream parameter
    issues rather than wiring gaps here. They affect band edges and specific
    sub-populations, not the mainline MAGI pathways:

    - The children's ceiling is frozen at 155% FPL; Missouri's current standard is 153%
      (148% nominal + 5% MAGI disregard), so PE reports eligible slightly above the line.
    - The parent/caretaker limit is stored as a percent of FPL (frozen at 23%), but
      Missouri's standard is a flat 1996-AFDC dollar figure that isn't FPL-indexed.
    - The pregnant/infant limit is frozen at 201%; the current MPW line is 196%.
    - There is no blind-specific MHABD standard - one flat ~85% FPG rate covers both
      blind and non-blind applicants.
    - Adult-expansion eligibility carries no Medicare-enrollment or SSI-receipt
      exclusion, and no Substantial Gainful Activity test gates the disability
      pathways.

    Fixes for these have been requested upstream. They are deliberately not patched
    here: this calculator stays a wiring-only PE subclass, so PolicyEngine remains the
    single source of the eligibility decision.
    """

    program_code = "mo_medicaid"

    pe_inputs = [
        *Medicaid.pe_inputs,
        dependency.household.MoStateCodeDependency,
    ]

    # KFF Medicaid Spending per Full-Benefit Enrollee by Enrollment Group, MO, 2023,
    # converted to monthly (the annual figure returned = value * 12):
    #   children (18 and under) -> $4,576/yr  -> $381/mo
    #   adults (19-64)          -> $6,379/yr  -> $532/mo
    #   seniors (65+)           -> $21,857/yr -> $1,821/mo
    #   people with disabilities -> $30,410/yr -> $2,534/mo
    medicaid_categories = {
        "NONE": 0,
        "ADULT": 532,
        "INFANT": 381,
        "YOUNG_CHILD": 381,
        "OLDER_CHILD": 381,
        "PREGNANT": 532,
        "YOUNG_ADULT": 532,
        "PARENT": 532,
        "SSI_RECIPIENT": 2_534,
        "AGED": 1_821,
        "DISABLED": 2_534,
    }
