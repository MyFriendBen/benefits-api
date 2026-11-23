from .base import TaxUnit


class Coeitc(TaxUnit):
    field = "co_eitc"


class Coctc(TaxUnit):
    field = "co_ctc"


class CoCareWorkerCredit(TaxUnit):
    field = "co_care_worker_credit"


class Maeitc(TaxUnit):
    field = "ma_eitc"


class WaWftc(TaxUnit):
    field = "wa_working_families_tax_credit"


class Ileitc(TaxUnit):
    field = "il_eitc"


class MoWftc(TaxUnit):
    field = "mo_wftc"


class Kseitc(TaxUnit):
    field = "ks_total_eitc"


class KsChipPremium(TaxUnit):
    # KanCare CHIP monthly premium per household, returned by PE as an ANNUAL
    # figure (monthly amount x 12). Surfaced for display (divide by 12 for the
    # monthly amount); not netted against the CHIP coverage value.
    field = "ks_chip_premium"


class MoChipPremium(TaxUnit):
    # Missouri's CHIP premium per household. Unlike ks_chip_premium this is a MONTHLY
    # variable (PolicyEngine 1.790.2 made it one so Appendix E's July 1 turnover takes
    # effect), so it must be requested at a month period — see
    # PolicyEngineCalulator.period_for.
    field = "mo_chip_premium"


class Ilctc(TaxUnit):
    field = "il_ctc"


class MaChildFamilyCredit(TaxUnit):
    field = "ma_child_and_family_credit"


class KsCdcc(TaxUnit):
    field = "ks_cdcc"


class Aca(TaxUnit):
    field = "aca_ptc"


class MoPropertyTaxCredit(TaxUnit):
    field = "mo_property_tax_credit"
