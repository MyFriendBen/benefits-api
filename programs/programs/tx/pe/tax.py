from programs.programs.federal.pe.tax import Aca, Ctc, Eitc
import programs.framework.pe_dependencies as dependency


class TxAca(Aca):
    pe_name = "aca_ptc"
    pe_inputs = [
        *Aca.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]


class TxCtc(Ctc):
    """
    Federal Child Tax Credit surfaced to Texas users as ``tx_ctc``.

    Texas has no state CTC and no state income tax, so this reads PolicyEngine's
    federal ``ctc_value`` unchanged. See ``MoCtc`` for why no state code is sent.
    """


class TxEitc(Eitc):
    """
    Federal EITC surfaced to Texas users as ``tx_eitc``.

    Texas has no state EITC. PolicyEngine's ``eitc`` is federal.
    """
