"""The household payment unit's rule, checked on every scenario test's result."""

from programs.framework.base import Eligibility, PaymentUnit


def assert_household_members_unpriced(eligibility: Eligibility, calculator_name: str) -> None:
    """Fail when a household-paid program gives a member a value.

    A household program's whole value is its `household_value` (see `PaymentUnit`). The
    registry check in `test_eligibility_protocol.py` catches a household calculator that sets
    `member_amount` or overrides `member_value`; this catches a value written anywhere else,
    such as inside `member_eligible` or a replaced `value()`. Both scenario fixtures run it
    after `calc()`.
    """
    if eligibility.payment_unit != PaymentUnit.HOUSEHOLD:
        return

    priced = [member.value for member in eligibility.eligible_members if member.value]
    if priced:
        raise AssertionError(
            f"{calculator_name} is household-paid but gave members values {priced}; a household "
            "program's whole value belongs in household_value."
        )
