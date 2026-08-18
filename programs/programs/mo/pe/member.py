from programs.programs.federal.pe.member import (
    Wic,
    HeadStart,
    EarlyHeadStart,
    Medicaid,
    Msp,
    Ssi,
)
import programs.framework.pe_dependencies as dependency
from screener.models import HouseholdMember


class MoWic(Wic):
    """
    Missouri WIC — federal ``Wic`` PE calculator + MO state code.

    Missouri has no WIC-specific rules of its own: income limits (185% FPL) and the
    categorical pathways (SNAP / Temporary Assistance / MO HealthNet) are federal, and
    PolicyEngine's WIC tree only branches on AK/HI vs. contiguous-US FPG tables. MO
    falls in the contiguous set, so the federal calculator applies as-is.

    Unlike CO/NC/MA — which override ``wic_categories`` with hardcoded per-category
    monthly amounts — this returns PolicyEngine's own computed benefit amount, the same
    approach ``TxWic`` takes. The federal base class's ``wic_categories`` are all zeros,
    so inheriting ``member_value`` unchanged would value every eligible member at $0 and
    the frontend's ``value > 0`` filter would drop the program from results entirely.
    """

    name_abbreviated = "mo_wic"

    pe_inputs = [
        *Wic.pe_inputs,
        dependency.household.MoStateCodeDependency,
    ]

    def member_value(self, member: HouseholdMember):
        """Return PolicyEngine's calculated WIC benefit for this member."""
        return self.get_member_variable(member.id)


class MoHeadStart(HeadStart):
    """Missouri Head Start (ages 3-5) — federal ``HeadStart`` PE calculator + MO state code."""

    name_abbreviated = "mo_head_start"

    pe_inputs = [
        *HeadStart.pe_inputs,
        dependency.household.MoStateCodeDependency,
    ]


class MoEarlyHeadStart(EarlyHeadStart):
    """Missouri Early Head Start (birth-3 / pregnant) — federal ``EarlyHeadStart`` PE calculator + MO state code."""

    name_abbreviated = "mo_early_head_start"

    pe_inputs = [
        *EarlyHeadStart.pe_inputs,
        dependency.household.MoStateCodeDependency,
    ]


class MoSsi(Ssi):
    """
    Missouri Supplemental Security Income — federal SSI applied to MO residents.

    A thin wrapper on the federal ``Ssi`` PolicyEngine calculator that adds only the MO
    state code, mirroring ``KsSsi`` / ``TxSsi`` / ``WaSsi``. SSI is federal end to end:
    PolicyEngine's ``ssi`` variable reads only ``gov.ssa.ssi.*`` parameters, with no state
    key anywhere in the formula, and PE models SSI *state supplements* for NM, SC, and TX
    only — there is no MO supplement module. So the output is the federal Benefit Rate
    (sourced from PE's parameters at calculation time, so it tracks SSA COLA updates
    automatically) minus PolicyEngine's countable income.

    Missouri's own state cash programs for this population — Blind Pension, Supplemental
    Aid to the Blind, and Supplemental Nursing Care — are deliberately out of scope here
    and tracked as a separate program.

    All eligibility math lives in PolicyEngine: the aged / blind / disabled categorical
    entry, the $20 general + $65 earned + 1/2 remainder exclusion stack, the SGA cutoff,
    in-kind support and maintenance, spousal and parental deeming, and the resource limit.
    The screener contributes only the per-member inputs inherited from ``Ssi.pe_inputs``
    plus the MO state code.

    Two of those inherited inputs are load-bearing rather than boilerplate:

    - ``MeetsSsiDisabilityCriteriaDependency`` — PE 1.715.2+ no longer infers SSI
      disability from ``is_disabled`` or reported receipt, so without it a disabled
      non-aged, non-blind applicant returns ``ssi: 0``. It is version-gated, so it only
      reaches models that define the field.
    - ``SsiCountableResourcesDependency`` — the resource limit is a hard cutoff, and this
      splits reported household assets across adults to approximate the per-person figure.

    Duplicate-enrollment filtering ("not already receiving SSI") happens a layer up via
    ``Screen.has_benefit("mo_ssi")``, which is why the config sets
    ``show_in_has_benefits_step: true``.
    """

    name_abbreviated = "mo_ssi"

    pe_inputs = [
        *Ssi.pe_inputs,
        dependency.household.MoStateCodeDependency,
    ]


class MoMsp(Msp):
    """
    Missouri Medicare Savings Program (QMB / SLMB / QI) — federal ``Msp`` plus the MO state
    code and Medicaid inputs, mirroring ``KsMsp`` / ``TxMsp`` / ``IlMsp``.

    The income tiers are the federal floor in Missouri, so the state code is the only
    MO-keyed input. It resolves the MSP asset-test-applies parameter, which is ``true`` for
    MO — without it the resource test would silently not apply and over-resourced
    households would show as eligible.

    Missouri rules PolicyEngine does not model are recorded in the MO MSP spec.
    """

    pe_inputs = [
        *Msp.pe_inputs,
        dependency.household.MoStateCodeDependency,
        *Medicaid.pe_inputs,
    ]
