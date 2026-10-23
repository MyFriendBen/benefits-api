"""MO CHIP."""

from programs.framework.base import Eligibility
from programs.framework.pe_base import PolicyEngineMembersCalculator
from programs.framework.pe_dependencies.constants import ALL_TAX_UNITS
from programs.programs.cross_white_label.medicaid.base import Medicaid
from screener.models import HouseholdMember
import programs.framework.pe_dependencies as dependency


class MoChip(PolicyEngineMembersCalculator):
    """
    MO HealthNet for Kids (CHIP), premium groups 73/74/75, via PolicyEngine.

    Eligibility, the per-child gross value and the household premium are all PolicyEngine's;
    see specs/mo.md. Nothing here re-derives Missouri's Appendix A income boundaries or
    Appendix E premium table — those are what PolicyEngine's own parameters implement, and
    reading them back out of PE is the whole point. Notes below cover only the wiring.

    ``value = max(1, sum(chip_gross for each PE-eligible child) - mo_chip_premium * 12)``.
    The premium is a household charge, so it lands on ``household_value`` once no matter how
    many children qualify, while each child's gross value stays on that child. Gross is
    summed unrounded and the API truncates once at the end: six children at $2,911.851 come
    to $17,471.106, where six times the rounded $2,911.85 would be a cent short.

    Two things that look like they could be simplified, and can't:

    ``chip_gross``, not ``chip``. ``chip`` is PolicyEngine's figure net of its own
    cost-sharing offsets; subtracting Missouri's premium from it as well would count
    cost-sharing twice. Gross minus premium is the number Missouri actually leaves a family.

    ``mo_chip_premium`` is read at a month, not the year. PolicyEngine made it a monthly
    variable in 1.790.2 so that Appendix E's July 1 turnover takes effect, which means the
    annual period returns six months of each schedule and matches neither: a household of
    three in tier 1 reads $804/yr, i.e. 6 x $102 + 6 x $32, against a true $32/mo. See
    ``PolicyEngineCalulator.period_for``.

    Insurance does not gate. The screener's coarse ``private``/``employer`` answers cannot
    tell genuinely comprehensive, disqualifying coverage from Missouri's own "still
    uninsured" exceptions (DSS 1840.010.10) or from limited-benefit plans, so per specs/mo.md
    Criterion 3 that stays an inclusive data gap rather than an eligibility test — unlike the
    other state CHIP calculators beside this file. Reported *Medicaid* enrollment does gate,
    but as an input: ``ReceivesMedicaidDependency`` feeds PolicyEngine, whose own
    ``is_chip_eligible_child`` excludes the child.
    """

    program_code = "mo_chip"

    pe_name = "chip_gross"
    pe_inputs = [
        # PE gates CHIP on ~is_medicaid_eligible, so CHIP needs whatever Medicaid needs to
        # compute that. Same reason KsChip reuses KsKanCare's inputs.
        *Medicaid.pe_inputs,
        # 42 CFR 457.350(d): a child already on Medicaid is not CHIP-eligible. The screener's
        # `medicaid` answer is an input to PE's determination, not a check of our own.
        dependency.member.ReceivesMedicaidDependency,
        dependency.household.MoStateCodeDependency,
    ]
    pe_outputs = [
        dependency.member.ChipGross,
        dependency.tax.MoChipPremium,
    ]
    pe_monthly_outputs = [dependency.tax.MoChipPremium]
    # Appendix E's rates turn over July 1, so any month from July on reads the schedule the
    # program year's expected values are stated against. January would read the prior one.
    pe_period_month = "07"

    #: The netted value floors here rather than at $0. A household whose premium exceeds the
    #: gross value still has a CHIP-eligible child who would get coverage, but a $0 program is
    #: reported ineligible (`eligible = value > 0`) and dropped by the frontend's own
    #: `programValue(program) > 0` filter, so flooring at $0 would hide the program from
    #: exactly the families it applies to. specs/mo.md Scenario 10.
    min_value = 1

    def member_value(self, member: HouseholdMember):
        # PE returns 0 for anyone it does not mark a CHIP-eligible child, so member
        # eligibility falls out of its own value — is_chip_eligible_child multiplied by
        # Missouri's per-capita gross. No separate flag to read.
        return self.get_member_variable(member.id)

    def household_eligible(self, e: Eligibility):
        # Runs after member eligibility, which is what makes the household premium
        # expressible: it is charged once, and capped so the netted total never falls below
        # min_value. Written as a negative household value rather than by adjusting the
        # children's values, so each child keeps the gross value PE gave them.
        gross = sum(member.value for member in e.eligible_members if member.eligible)

        if gross <= 0:
            return

        e.household_value = -min(self.annual_premium(), gross - self.min_value)

    def annual_premium(self):
        """Missouri's monthly CHIP premium, annualized.

        Summed over tax units for the same reason ``PolicyEngineTaxUnitCalulator`` does it:
        ``mo_chip_premium`` is a tax-unit variable and a household can split into two. The
        secondary unit is omitted from the payload when empty, hence the KeyError.
        """
        monthly = 0
        for unit in ALL_TAX_UNITS:
            try:
                monthly += self.get_tax_dependency_value(dependency.tax.MoChipPremium, unit)
            except KeyError:
                continue

        return monthly * 12
