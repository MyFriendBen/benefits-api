from programs.programs.federal.pe.member import Medicaid
from programs.programs.policyengine.calculators.base import (
    PolicyEngineMembersCalculator,
)
import programs.programs.policyengine.calculators.dependencies as dependency
from screener.models import HouseholdMember


class KsChip(PolicyEngineMembersCalculator):
    """
    Kansas CHIP (Children's Health Insurance Program) calculator.

    Composes PolicyEngine's federal ``chip`` eligibility/value output with the
    Kansas-specific ``ks_chip_premium``. Mirrors the TxChip precedent:

    - ``chip`` (the per-child coverage value, ~``per_capita_chip``) is the member
      value. All CHIP eligibility logic (under 19, income at/below the 255% FPL
      effective cap, ~Medicaid-eligible) is already baked into PE's ``chip`` output.
    - The "uninsured children only" rule is enforced via MFB's hybrid zero-out:
      a child's CHIP value is surfaced only when their insurance is exactly
      ``none``; any other coverage type zeroes it out.

    KS-specific: additionally outputs ``ks_chip_premium`` (a TaxUnit-level PE
    variable returned as an ANNUAL figure = monthly premium x 12). It is surfaced
    for display alongside the coverage value (divide by 12 for the monthly amount)
    and is NOT netted against the coverage value.
    """

    pe_name = "chip"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.PregnancyDependency,
        *Medicaid.pe_inputs,
        dependency.household.KsStateCodeDependency,
    ]
    pe_outputs = [
        dependency.member.Chip,
        dependency.tax.KsChipPremium,
    ]

    def member_value(self, member: HouseholdMember):
        """
        Returns the CHIP coverage value for this member, applying the
        uninsured-only rule.
        """
        pe_value = self.get_member_variable(member.id)

        # CHIP is only for children with no other health coverage. Any insurance
        # type other than "none" disqualifies the child.
        if member.has_insurance_types(("none",)):
            return pe_value

        return 0
