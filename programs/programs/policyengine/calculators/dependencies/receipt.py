"""
Who actually receives SSI, TANF and SNAP — the input side of PolicyEngine's
actual-receipt contract (policyengine-us 1.779.3).

PolicyEngine used to feed *simulated* (would-be-eligible) SSI/TANF/SNAP into other
programs' calculations, both as countable income and to confer categorical eligibility
(SNAP categorical via SSI/TANF, WIC adjunctive, Head Start categorical, Medicaid's SSI
category). Being eligible for a benefit is not the same as receiving it, so that
over-stated downstream eligibility and income. Since 1.779.3 both key off receipt, which
we drive with two inputs per program:

  receives_X              the household reports receiving X. Confers categorical
                          eligibility even where PE computes the amount as $0 — the case
                          a reported amount alone cannot express.
  takes_up_X_if_eligible  False for a household that reports *not* receiving X: zeroes
                          PE's simulated X and switches off the categorical eligibility
                          it would otherwise confer.

Reported *amounts* are separate inputs (``member.Ssi``, ``spm.Tanf``) and win over the
take-up flag — the flag only suppresses PE's own computed value. SNAP has no amount
capture in the screener, so its receipt is a boolean only.

"Not receiving" is not the same as "no signal". Every helper here reads receipt from both
the Current Benefits tiles and the income streams, and the take-up flag is lowered only
when neither says anything. Where a signal is real but unattributable — a household that
ticks SSI without any member reporting an amount — we leave PE's default take-up alone
rather than zero out a real recipient's benefit.
"""

from screener.models import HouseholdMember, Screen

# The income options that carry these benefits' dollar amounts. Note the `sSI` casing,
# and that TANF is captured as `cashAssistance` rather than a `tanf` income type.
SSI_INCOME_TYPE = "sSI"
TANF_INCOME_TYPE = "cashAssistance"

# SSI's aged pathway (42 U.S.C. § 1382(a)); the blind/disabled pathways have no age floor.
SSI_AGED_MIN_AGE = 65


def screen_reports_snap(screen: Screen) -> bool:
    """
    Whether the household reports receiving SNAP.

    The Current Benefits tile is the only signal: the screener captures no SNAP dollar
    amount. ``has_base_benefit`` covers every white-label variant (co_snap, ks_snap,
    wa_snap, …); ``has_benefit`` is an exact match on the bare name, which no white label
    ships.
    """
    return screen.has_base_benefit("snap")


def screen_reports_tanf(screen: Screen) -> bool:
    """
    Whether the household reports receiving TANF.

    Either the tile or a reported cash-assistance income stream — the same amount
    ``spm.Tanf`` sends PolicyEngine as the ``tanf`` input. Reading the income stream here
    (rather than deriving TANF receipt into the CurrentBenefit join table) keeps this out
    of the results layer's ``already_has`` filter: "Cash Assistance Grant" is a broader
    label than TANF, and mislabelling it would drop the state's TANF program from a
    household's results.
    """
    return screen.has_base_benefit("tanf") or screen.calc_gross_income("yearly", [TANF_INCOME_TYPE]) > 0


def member_reports_ssi_amount(member: HouseholdMember) -> bool:
    """Whether this member reports an SSI dollar amount of their own."""
    return member.calc_gross_income("yearly", [SSI_INCOME_TYPE]) > 0


def _could_receive_ssi(member: HouseholdMember) -> bool:
    """
    Whether this member could be the SSI recipient in a household reporting SSI.

    SSI is only payable to someone aged, blind or disabled (42 U.S.C. § 1382(a)), which is
    also the screener data we have. Used only to decide *who* to attribute a household-level
    report to — never to decide eligibility.
    """
    age = member.calc_age()
    if age is not None and age >= SSI_AGED_MIN_AGE:
        return True

    return bool(member.disabled or member.long_term_disability or member.visually_impaired)


def member_receives_ssi(screen: Screen, member: HouseholdMember) -> bool:
    """
    Whether this member reports receiving SSI, from either signal: their own reported
    amount, or the household's Current Benefits tile.

    `ssi` and `receives_ssi` are person-level in PolicyEngine, so a household-level tile has
    to be attributed to somebody — and PolicyEngine treats `receives_ssi` as conclusive.
    Measured against the live API: the flag alone flips `medicaid_category` to
    SSI_RECIPIENT with no demographic or income test, worth $15,167 to a non-disabled
    30-year-old at $90k and $10,222 to a 3-year-old. So we attribute rather than broadcast:

    - a member reporting their own amount receives SSI, full stop;
    - otherwise, if the tile is ticked and *nobody* reports an amount, the members who could
      plausibly be the recipient (aged/blind/disabled) are credited. One is enough for the
      cross-program signal — SNAP's categorical eligibility fires off a single member.

    A reported amount explains the tile, so when any member reports one the others are
    non-recipients rather than additional recipients.
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
    Whether the household reports SSI receipt we can't pin on anyone: the tile is ticked,
    no member reports an amount, and no member is aged, blind or disabled.

    The signal is real — so suppressing simulated SSI across the household would zero out a
    genuine recipient's benefit — but there is no defensible member to credit. Callers leave
    PolicyEngine's default take-up in place for everyone, which is the pre-contract
    behavior rather than a silent zeroing.
    """
    if not screen.has_base_benefit("ssi"):
        return False

    if screen.calc_gross_income("yearly", [SSI_INCOME_TYPE]) > 0:
        return False

    return not any(_could_receive_ssi(member) for member in screen.household_members.all())
