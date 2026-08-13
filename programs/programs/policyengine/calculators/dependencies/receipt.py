"""
Who actually receives SSI, TANF and SNAP — the input side of PolicyEngine's actual-receipt
contract.

PolicyEngine used to feed *simulated* (would-be-eligible) SSI/TANF/SNAP into other programs'
calculations, both as countable income and to confer categorical eligibility, over-stating
both. It now keys off receipt, which we drive with two inputs per program:

  receives_X              the household reports receiving X. Confers categorical eligibility
                          even where PolicyEngine computes the amount as $0 — the case a
                          reported amount alone cannot express.
  takes_up_X_if_eligible  False for a household that reports *not* receiving X: zeroes
                          PolicyEngine's simulated X and the eligibility it would confer.

Reported amounts are separate inputs (``member.Ssi``, ``spm.Tanf``) and win over the take-up
flag, which only suppresses PolicyEngine's own computed value. SNAP has no amount capture, so
its receipt is a boolean only.

"Not receiving" is not the same as "no signal": these helpers read both the Current Benefits
tiles and the income streams, and lower the take-up flag only when neither says anything.
"""

from screener.models import HouseholdMember, Screen

# The income options that carry these benefits' dollar amounts. Note the `sSI` casing,
# and that TANF is captured as `cashAssistance` rather than a `tanf` income type.
SSI_INCOME_TYPE = "sSI"
TANF_INCOME_TYPE = "cashAssistance"

# SSI's aged pathway (42 U.S.C. § 1382(a)); the blind/disabled pathways have no age floor.
SSI_AGED_MIN_AGE = 65


def screen_reports_snap(screen: Screen) -> bool:
    """Whether the household reports receiving SNAP. The Current Benefits tile is the only
    signal, since the screener captures no SNAP amount. ``has_base_benefit`` covers every
    white-label variant; ``has_benefit`` matches a bare name no white label ships."""
    return screen.has_base_benefit("snap")


def screen_reports_tanf(screen: Screen) -> bool:
    """
    Whether the household reports receiving TANF — the tile, or a reported cash-assistance
    amount.

    Read here rather than derived into the CurrentBenefit table on purpose: that would feed
    the results layer's ``already_has`` filter, and "Cash Assistance Grant" is a broader label
    than TANF, so mislabelling it would drop the state's TANF program from their results.
    """
    return screen.has_base_benefit("tanf") or screen.calc_gross_income("yearly", [TANF_INCOME_TYPE]) > 0


def member_reports_ssi_amount(member: HouseholdMember) -> bool:
    """Whether this member reports an SSI dollar amount of their own."""
    return member.calc_gross_income("yearly", [SSI_INCOME_TYPE]) > 0


def _could_receive_ssi(member: HouseholdMember) -> bool:
    """Whether this member could be the SSI recipient in a household reporting SSI: SSI is
    only payable to someone aged, blind or disabled (42 U.S.C. § 1382(a)). Used to attribute a
    household-level report, never to decide eligibility."""
    age = member.calc_age()
    if age is not None and age >= SSI_AGED_MIN_AGE:
        return True

    return bool(member.disabled or member.long_term_disability or member.visually_impaired)


def member_receives_ssi(screen: Screen, member: HouseholdMember) -> bool:
    """
    Whether this member reports receiving SSI, from either signal: their own reported amount,
    or the household's Current Benefits tile.

    ``receives_ssi`` is person-level and PolicyEngine treats it as conclusive — measured, the
    flag alone confers the SSI-recipient Medicaid pathway with no demographic or income test.
    So a household-level tile is attributed, not broadcast: a member reporting their own amount
    receives SSI, and otherwise a ticked tile with no amount anywhere credits only the members
    who could plausibly be the recipient. A reported amount explains the tile, leaving the
    others as non-recipients.
    """
    if member_reports_ssi_amount(member):
        return True

    if not screen.has_base_benefit("ssi"):
        return False

    if screen.calc_gross_income("yearly", [SSI_INCOME_TYPE]) > 0:
        # Somebody's amount already accounts for the tile.
        return False

    return _could_receive_ssi(member)


def screen_reports_unidentifiable_ssi(screen: Screen) -> bool:
    """
    Whether the household reports SSI receipt we can't pin on anyone: tile ticked, no amount
    reported, and nobody aged, blind or disabled.

    The signal is real, so suppressing simulated SSI across the household would zero out a
    genuine recipient's benefit — but there is no defensible member to credit. Callers leave
    PolicyEngine's default take-up alone, which is the pre-contract behavior.
    """
    if not screen.has_base_benefit("ssi"):
        return False

    if screen.calc_gross_income("yearly", [SSI_INCOME_TYPE]) > 0:
        return False

    return not any(_could_receive_ssi(member) for member in screen.household_members.all())
