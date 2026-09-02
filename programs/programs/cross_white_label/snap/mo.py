"""MO SNAP."""

from programs.programs.cross_white_label.snap.base import Snap
import programs.framework.pe_dependencies as dependency


class MoSnap(Snap):
    """
    Missouri Food Assistance (SNAP).

    PolicyEngine's federal SNAP calculator carries eligibility and the benefit amount.
    Missouri's variance is entirely state-keyed parameters inside that tree, so the state
    code is the only input this class adds — the same shape as the other seven states.

    What the state code turns on, and why none of it is ours to compute:

    - Child-support gross-income exclusion, elected (2021-10-01+). Feeds ``snap_gross_income``,
      so it moves the gross-income test. ``SnapChildSupportDependency`` on the base already
      sends the amount it reads.
    - Expense-based self-employment deduction, with the simplified deduction rate at 0%.
      Changes net self-employment income, so it moves the net-income test.
    - No BBCE. Missouri did not adopt broad-based categorical eligibility, so the ordinary
      gross/net/asset tests apply rather than a categorical bypass. Absence of an election is
      still keyed off the state code.
    - State utility allowances (SUA/LUA/IUA), the $135 standard medical deduction for
      elderly/disabled households, and the homeless standard shelter deduction. All three
      feed the excess-shelter deduction and the benefit amount; the base already sends the
      expense inputs each one reads.
    """

    program_code = "mo_snap"

    pe_inputs = [
        *Snap.pe_inputs,
        dependency.household.MoStateCodeDependency,
    ]
