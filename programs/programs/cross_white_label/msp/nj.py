"""NJ Medicare Savings Programs."""

from programs.programs.cross_white_label.msp.federal_base import MspFederalBase


class NjMedicareSavings(MspFederalBase):
    """
    New Jersey's Medicare Savings Programs. NJ inherits every federal rule from
    ``MspFederalBase`` and screens QMB, SLMB and QI; QDWI is held.

    NJ's state-only exclusions (DMAHS fraud-tip rewards, Census wages, refunds after an MSP
    enrollment error) have no screener field and are not evaluated.

    NJ hasn't stated its family-size method; it is open with DMAHS. ``individual_or_couple``
    is the SSI default the federal family-size memo lets a state keep, and N.J.A.C. 10:72-3.5
    states it for SLMB. The two methods differ only for a household with dependents.

    The spec is ``programs/cross_white_label/msp/nj/msp_nj_spec.md`` in program-ops.
    """

    program_code = "nj_medicare_savings"

    family_size_method = "individual_or_couple"
