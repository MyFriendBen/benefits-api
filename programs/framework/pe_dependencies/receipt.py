"""
Who receives SSI, TANF and SNAP — the input side of PolicyEngine's actual-receipt contract.

PolicyEngine keys SSI/TANF/SNAP off actual receipt rather than simulated eligibility, both for
countable income and for the categorical eligibility they confer. Two inputs per program drive
it:

  receives_X              the household reports receiving X. Confers categorical eligibility
                          even where PolicyEngine computes the amount as $0 — the case a
                          reported amount alone cannot express.
  takes_up_X_if_eligible  False for a household that reports *not* receiving X: zeroes
                          PolicyEngine's simulated X and the eligibility it would confer.

Reported amounts are separate inputs (``member.Ssi``, ``spm.Tanf``) and win over the take-up
flag, which only suppresses PolicyEngine's own computed value. SNAP has no amount capture, so
its receipt is a boolean only.

Entity scope is why the three are not read the same way
-------------------------------------------------------
``receives_snap`` and ``receives_tanf`` are **spm_unit**-level, matching the household scope of
a Current Benefits tile, so the tile maps onto them directly.

``receives_ssi`` is **person**-level. The screener captures the tile per household, so a ticked
SSI tile with no dollar amount names no recipient — and with more than one plausible member,
nothing in the data distinguishes which of them receives it. Guessing is not free:
PolicyEngine treats ``receives_ssi`` as conclusive, so crediting the wrong member confers the
SSI-recipient Medicaid pathway on them with no demographic or income test. So SSI receipt is
read from a reported amount only, which is per-member and unambiguous.

The tile still counts for take-up: ``screen_reports_ssi_without_amount`` holds it at
PolicyEngine's default for such a household, so a real recipient's SSI is never zeroed. The
tile just isn't asserted as any particular member's receipt.

Little rides on that narrower read, because ``ssi`` and ``receives_ssi`` are consumed as a
pair — every consumer tests ``(ssi > 0) | receives_ssi`` (SNAP's
``meets_snap_categorical_eligibility``, Medicaid's ``is_ssi_recipient_for_medicaid`` and its
209(b) variant). A tile-only household keeps ``takes_up_ssi_if_eligible`` True, so PolicyEngine
models their SSI, ``ssi > 0``, and those tests fire anyway. The boolean decides only the case
where PolicyEngine computes the amount as $0, which is the one receipt a tile-only household
does not get credited for.
"""

from screener.models import HouseholdMember, Screen

# The income options that carry these benefits' dollar amounts. Note the `sSI` casing, and
# that TANF is captured as `cashAssistance` rather than a `tanf` income type. Cash aid from
# any other program is a separate option, `cashAssistanceOther`, and is not TANF receipt.
SSI_INCOME_TYPE = "sSI"
TANF_INCOME_TYPE = "cashAssistance"


def screen_reports_snap(screen: Screen) -> bool:
    """Whether the household reports receiving SNAP. The Current Benefits tile is the only
    signal, since the screener captures no SNAP amount. ``has_base_benefit`` covers every
    white-label variant; ``has_benefit`` matches a bare name no white label ships."""
    return screen.has_base_benefit("snap")


def screen_reports_tanf(screen: Screen) -> bool:
    """
    Whether the household reports receiving TANF — the tile, or a reported cash-assistance
    amount.

    Read here rather than derived into the CurrentBenefit table on purpose: that would feed the
    results layer's ``already_has`` filter, so a household whose only cash aid is non-TANF would
    lose the state's TANF program from their results.
    """
    return screen.has_base_benefit("tanf") or screen.calc_gross_income("yearly", [TANF_INCOME_TYPE]) > 0


def member_reports_ssi_amount(member: HouseholdMember) -> bool:
    """
    Whether this member reports an SSI dollar amount of their own — the only per-member SSI
    receipt signal the screener captures, and so the sole basis for ``receives_ssi``.

    The Current Benefits tile is deliberately not read here: it is household-scoped, so it
    names no recipient, and with more than one plausible member the screener holds nothing to
    tell them apart. See ``screen_reports_ssi_without_amount`` for what the tile does drive.
    """
    return member.calc_gross_income("yearly", [SSI_INCOME_TYPE]) > 0


def screen_reports_ssi_without_amount(screen: Screen) -> bool:
    """
    Whether the household ticked the SSI tile but reported no SSI amount for anyone.

    Somebody here receives SSI, but nothing identifies who, so no member is asserted as a
    recipient. Lowering ``takes_up_ssi_if_eligible`` would zero the simulated SSI of whoever
    that is, so callers leave take-up at PolicyEngine's default for the whole household —
    unknown stays unknown rather than becoming a denial.

    Once any member reports an amount, that member accounts for the tile and the rest of the
    household is suppressed normally.
    """
    if not screen.has_base_benefit("ssi"):
        return False

    return screen.calc_gross_income("yearly", [SSI_INCOME_TYPE]) == 0
