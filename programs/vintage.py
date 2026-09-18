"""Which edition of a threshold table each program is meant to be evaluated against.

`Program.year` is a foreign key to a `FederalPoveryLimit` row, and that row's `period`
decides two different things depending on the program:

  * for a PolicyEngine program it becomes the request period, so it names the benefit year
    PolicyEngine is asked about;
  * for a custom calculator it selects an edition of the FPL, AMI or SMI table read directly.

Nothing in the codebase recorded which of those a given program meant, or why it was on the
edition it was on. The result was 112 active rows a year or more behind with no way to tell a
deliberate pin from a forgotten one -- SSI paying $6,840 in four states and $7,332 in four
others for the same household, because half the config rows had been rolled forward and half
had not.

This module is that record. It does not change behaviour: the migration that corrects rows
reads from it, and the CI guard and the environment audit both check against it.

BEING BEHIND IS NOT THE SAME AS BEING WRONG. Several programs are deliberately on an older
edition because the agency administering them is:

  * ACA marketplace subsidies are adjudicated against the guideline in effect when open
    enrollment opened -- the prior year's -- under 26 U.S.C. 36B;
  * weatherization follows the Department of Energy's effective-date lag;
  * Illinois' CBRAP used the FY2025 limits for its FY2026 round.

So the question a row answers is never "is this the newest edition", it is "is this the
edition in force for this program right now".

`status` is load-bearing and should be read honestly. Most rows are UNVERIFIED: recorded as
production has them, with nobody having established what they ought to be. That is a
deliberate statement of ignorance rather than an endorsement -- an entry here is not a claim
that a row is correct unless its status says CONFIRMED.
"""

from dataclasses import dataclass
from enum import Enum


class Basis(Enum):
    """What the configured period names for a given program.

    The distinction matters because the two look identical in the database and mean opposite
    things. `il_aca` on 2026 means *coverage year 2026*, which PolicyEngine scores against the
    2025 guideline on its own. `mo_wap` on 2025 means *the 2025 guideline itself*. Reading one
    as the other is how a correct row gets "fixed" into a wrong one.
    """

    #: The benefit or coverage year. Any statutory lag between that year and the guideline it
    #: is scored against is applied downstream -- inside PolicyEngine, or by the calculator.
    COVERAGE_YEAR = "coverage_year"

    #: The edition of the FPL, AMI or SMI table the calculator reads directly. Any lag has
    #: already been applied in choosing this value.
    TABLE_EDITION = "table_edition"


class Status(Enum):
    """How much is actually known about a row's edition."""

    #: Established against a published rule or a validated case, with the citation in `source`.
    CONFIRMED = "confirmed"

    #: Deliberately left alone, for a reason `rule` states. Not an unknown -- a decision.
    DEFERRED = "deferred"

    #: Recorded as production has it. Nobody has established what it should be.
    UNVERIFIED = "unverified"


@dataclass(frozen=True)
class Vintage:
    """The edition one program should be on, and the reasoning behind it."""

    #: The `FederalPoveryLimit.period` this program's `year` should point at.
    edition: str
    basis: Basis
    status: Status
    #: Why this edition, in one line. Required for CONFIRMED and DEFERRED.
    rule: str
    #: Where `rule` comes from: a statute, an agency notice, a validated case, a docstring.
    source: str


#: Keyed by ``(white_label.code, Program.name_abbreviated)``.
#:
#: Covers every active program whose answer depends on the period -- every PolicyEngine
#: program, plus every custom calculator that reads `program.year`. Programs that never read
#: it are deliberately absent; their `year` has no effect and recording one would imply a
#: decision nobody needs to make.
#:
#: UrgentNeed carries the same foreign key and nine active needs read it, but it is out of
#: scope here and wants its own pass.
PROGRAM_VINTAGE: dict[tuple[str, str], Vintage] = {
    # --- CONFIRMED ---------------------------------------------------------------------
    ("co", "co_snap"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.CONFIRMED,
        rule="current benefit year; PolicyEngine re-bases the BBCE limit within the year off fpg_year_start_month, so the month carries the schedule, not the year",
        source="cross_white_label/snap/base.py",
    ),
    ("co", "co_tanf"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.CONFIRMED,
        rule="validated against a real Colorado Works award to the dollar",
        source="partner case review, 2026-09",
    ),
    ("il", "il_aca"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.CONFIRMED,
        rule="coverage year; PolicyEngine applies the prior-year poverty guideline internally",
        source="26 U.S.C. 36B; cross_white_label/aca/specs/ks.md",
    ),
    ("il", "il_cbrap"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.CONFIRMED,
        rule="per-round parameter: IHDA used the FY2025 limits for the FY2026 round",
        source="il/cbrap/calculator.py docstring",
    ),
    ("il", "il_snap"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.CONFIRMED,
        rule="current benefit year; PolicyEngine re-bases the BBCE limit within the year off fpg_year_start_month, so the month carries the schedule, not the year",
        source="cross_white_label/snap/base.py",
    ),
    ("ks", "ks_aca_ptc"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.CONFIRMED,
        rule="coverage year; PolicyEngine applies the prior-year poverty guideline internally",
        source="26 U.S.C. 36B; cross_white_label/aca/specs/ks.md",
    ),
    ("ks", "ks_snap"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.CONFIRMED,
        rule="current benefit year; PolicyEngine re-bases the BBCE limit within the year off fpg_year_start_month, so the month carries the schedule, not the year",
        source="cross_white_label/snap/base.py",
    ),
    ("ma", "ma_aca"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.CONFIRMED,
        rule="coverage year; PolicyEngine applies the prior-year poverty guideline internally",
        source="26 U.S.C. 36B; cross_white_label/aca/specs/ks.md",
    ),
    ("ma", "ma_snap"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.CONFIRMED,
        rule="current benefit year; PolicyEngine re-bases the BBCE limit within the year off fpg_year_start_month, so the month carries the schedule, not the year",
        source="cross_white_label/snap/base.py",
    ),
    ("mo", "mo_aca_ptc"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.CONFIRMED,
        rule="coverage year; PolicyEngine applies the prior-year poverty guideline internally",
        source="26 U.S.C. 36B; cross_white_label/aca/specs/ks.md",
    ),
    ("mo", "mo_snap"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.CONFIRMED,
        rule="current benefit year; PolicyEngine re-bases the BBCE limit within the year off fpg_year_start_month, so the month carries the schedule, not the year",
        source="cross_white_label/snap/base.py",
    ),
    ("mo", "mo_wap"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.CONFIRMED,
        rule="DOE effective-date lag: the 200% column in force is the prior year's guideline",
        source="DOE Weatherization Program Notice 25-3",
    ),
    ("nc", "nc_aca"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.CONFIRMED,
        rule="coverage year; PolicyEngine applies the prior-year poverty guideline internally",
        source="26 U.S.C. 36B; cross_white_label/aca/specs/ks.md",
    ),
    ("nc", "nc_snap"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.CONFIRMED,
        rule="current benefit year; PolicyEngine re-bases the BBCE limit within the year off fpg_year_start_month, so the month carries the schedule, not the year",
        source="cross_white_label/snap/base.py",
    ),
    ("tx", "tx_aca"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.CONFIRMED,
        rule="coverage year; PolicyEngine applies the prior-year poverty guideline internally",
        source="26 U.S.C. 36B; cross_white_label/aca/specs/ks.md",
    ),
    ("tx", "tx_snap"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.CONFIRMED,
        rule="current benefit year; PolicyEngine re-bases the BBCE limit within the year off fpg_year_start_month, so the month carries the schedule, not the year",
        source="cross_white_label/snap/base.py",
    ),
    ("wa", "wa_snap"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.CONFIRMED,
        rule="current benefit year; PolicyEngine re-bases the BBCE limit within the year off fpg_year_start_month, so the month carries the schedule, not the year",
        source="cross_white_label/snap/base.py",
    ),

    # --- DEFERRED ----------------------------------------------------------------------
    ("cesn", "cesn_care"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.DEFERRED,
        rule="the AMI table carries no 2026 edition; rolling forward raises KeyError at calculation time",
        source="integrations/services/income_limits.py",
    ),
    ("cesn", "cesn_eoc"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.DEFERRED,
        rule="the AMI table carries no 2026 edition; rolling forward raises KeyError at calculation time",
        source="integrations/services/income_limits.py",
    ),
    ("cesn", "cesn_eocs"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.DEFERRED,
        rule="the AMI table carries no 2026 edition; rolling forward raises KeyError at calculation time",
        source="integrations/services/income_limits.py",
    ),
    ("co", "co_expanded_eitc"): Vintage(
        edition="2024",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("co", "coctc"): Vintage(
        edition="2024",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("co", "coeitc"): Vintage(
        edition="2024",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("co", "ctc"): Vintage(
        edition="2024",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("co", "dptr"): Vintage(
        edition="2024",
        basis=Basis.TABLE_EDITION,
        status=Status.DEFERRED,
        rule="the AMI table carries no 2026 edition; rolling forward raises KeyError at calculation time",
        source="integrations/services/income_limits.py",
    ),
    ("co", "dsr"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.DEFERRED,
        rule="the AMI table carries no 2026 edition; rolling forward raises KeyError at calculation time",
        source="integrations/services/income_limits.py",
    ),
    ("co", "dtr"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.DEFERRED,
        rule="the AMI table carries no 2026 edition; rolling forward raises KeyError at calculation time",
        source="integrations/services/income_limits.py",
    ),
    ("co", "eitc"): Vintage(
        edition="2024",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("co", "fatc"): Vintage(
        edition="2024",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("co_tax_calculator", "co_tax_credit_care_worker"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("co_tax_calculator", "coctc"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("co_tax_calculator", "coeitc"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("co_tax_calculator", "ctc"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("co_tax_calculator", "eitc"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("co_tax_calculator", "fatc"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("il", "ctc"): Vintage(
        edition="2024",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("il", "eitc"): Vintage(
        edition="2024",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("il", "il_ctc"): Vintage(
        edition="2024",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("il", "il_eitc"): Vintage(
        edition="2024",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("il", "il_hcv"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.DEFERRED,
        rule="the AMI table carries no 2026 edition; rolling forward raises KeyError at calculation time",
        source="integrations/services/income_limits.py",
    ),
    ("ks", "ks_ctc"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("ks", "ks_eitc"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("ma", "ctc"): Vintage(
        edition="2024",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("ma", "eitc"): Vintage(
        edition="2024",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("ma", "ma_cfc"): Vintage(
        edition="2024",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("ma", "ma_cha"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.DEFERRED,
        rule="the AMI table carries no 2026 edition; rolling forward raises KeyError at calculation time",
        source="integrations/services/income_limits.py",
    ),
    ("ma", "ma_maeitc"): Vintage(
        edition="2024",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("mo", "mo_ctc"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("mo", "mo_eitc"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("mo", "mo_wftc"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("nc", "ctc"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("nc", "eitc"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("tx", "tx_ctc"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("tx", "tx_eitc"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("tx", "tx_hcv"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.DEFERRED,
        rule="the AMI table carries no 2026 edition; rolling forward raises KeyError at calculation time",
        source="integrations/services/income_limits.py",
    ),
    ("wa", "wa_ctc"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("wa", "wa_eitc"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),
    ("wa", "wa_hcv"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.DEFERRED,
        rule="the AMI table carries no 2026 edition; rolling forward raises KeyError at calculation time",
        source="integrations/services/income_limits.py",
    ),
    ("wa", "wa_seattle_fresh_bucks"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.DEFERRED,
        rule="the AMI table carries no 2026 edition; rolling forward raises KeyError at calculation time",
        source="integrations/services/income_limits.py",
    ),
    ("wa", "wa_wftc"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        rule="tax year, not calendar year; which filing year the screener should model is a product decision, tracked separately",
        source="",
    ),

    # --- UNVERIFIED --------------------------------------------------------------------
    ("cesn", "cesn_energy_mep"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("cesn", "cesn_heap"): Vintage(
        edition="2026",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("cesn", "cesn_leap"): Vintage(
        edition="2026",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("co", "andcs"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("co", "awd_medicaid"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("co", "cccap"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("co", "cdhcs"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("co", "cfhc"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("co", "chp"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("co", "co_head_start"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("co", "co_medicaid"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("co", "co_nfp"): Vintage(
        edition="2026",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("co", "co_wic"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("co", "cwd_medicaid"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("co", "ede"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("co", "fps"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("co", "leap"): Vintage(
        edition="2026",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("co", "lifeline"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("co", "medicare_savings"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("co", "nslp"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("co", "oap"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("co", "omnisalud"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("co", "rtdlive"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("co", "ssi"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("co", "upk"): Vintage(
        edition="2024",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("il", "il_aabd"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("il", "il_aca_adults"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("il", "il_access_dupage"): Vintage(
        edition="2026",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("il", "il_all_kids"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("il", "il_ccap"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("il", "il_csfp"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("il", "il_family_care"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("il", "il_fppe"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("il", "il_hbwd"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("il", "il_head_start"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("il", "il_hfs_fpp"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("il", "il_ibccp"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("il", "il_liheap"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("il", "il_medicaid"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("il", "il_moms_and_babies"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("il", "il_mpe"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("il", "il_msp"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("il", "il_nfp"): Vintage(
        edition="2026",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("il", "il_nslp"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("il", "il_silver_access"): Vintage(
        edition="2026",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("il", "il_tanf"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("il", "il_wic"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("il", "lifeline"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("il", "ssi"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ks", "ks_cdcc"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ks", "ks_cdcc_federal"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ks", "ks_chip"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ks", "ks_early_head_start"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ks", "ks_head_start"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ks", "ks_k40h"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.DEFERRED,
        # Production has no `year` row at all, which looks like drift and is not. The
        # calculator is pinned to the 2025 K-40H booklet in four places -- income_limit
        # 43,389, the whole refund-percentage table, the senior age test, and claim_year's
        # own fallback -- so the unset row lands it on 2025 consistently with the rest.
        # Claim year 2025 is what Kansans file during 2026, so that is also the live claim
        # year today. Setting `year` to 2026 in isolation would be actively wrong: the age
        # tests would move while the income limit and refund table stayed behind.
        rule="tax claim year, hardcoded consistently across the calculator; moving it "
        "requires the 2026 K-40H booklet's income limit and refund table together",
        source="K.S.A. 79-4501 et seq.; 2025 K-40H booklet",
    ),
    ("ks", "ks_lieap"): Vintage(
        edition="2026",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ks", "ks_lifeline"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ks", "ks_medicaid"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ks", "ks_medicare_savings"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ks", "ks_nslp"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ks", "ks_nurse_family_partnership"): Vintage(
        edition="2026",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ks", "ks_ssi"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ks", "ks_tanf"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ks", "ks_working_healthy"): Vintage(
        edition="2026",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ma", "lifeline"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ma", "ma_ccdf"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ma", "ma_cpp"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ma", "ma_csfp"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ma", "ma_eaedc"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ma", "ma_early_head_start"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ma", "ma_head_start"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ma", "ma_heap"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ma", "ma_mass_health"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ma", "ma_mass_health_limited"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ma", "ma_mbta"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ma", "ma_ssp"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ma", "ma_tafdc"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ma", "ma_wic"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ma", "ma_youthworks"): Vintage(
        edition="2025",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ma", "nslp"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("ma", "ssi"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("mo", "mo_cdcc_federal"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("mo", "mo_chip"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("mo", "mo_early_head_start"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("mo", "mo_head_start"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("mo", "mo_lifeline"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("mo", "mo_medicaid"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("mo", "mo_medicare_savings"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("mo", "mo_nfp"): Vintage(
        edition="2026",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("mo", "mo_nslp"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("mo", "mo_ssi"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("mo", "mo_tanf"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("mo", "mo_wic"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("nc", "lifeline"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("nc", "nc_emergency_medicaid"): Vintage(
        edition="2026",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("nc", "nc_fps"): Vintage(
        edition="2026",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("nc", "nc_head_start"): Vintage(
        edition="2026",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("nc", "nc_lieap"): Vintage(
        edition="2026",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("nc", "nc_medicaid"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("nc", "nc_medicare_savings"): Vintage(
        edition="2026",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("nc", "nc_scca"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("nc", "nc_tanf"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("nc", "nc_wic"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("nc", "nccip"): Vintage(
        edition="2026",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("nc", "ncwap"): Vintage(
        edition="2026",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("nc", "nslp"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("nc", "ssi"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("nc", "sunbucks"): Vintage(
        edition="2026",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("tx", "tx_ccad"): Vintage(
        edition="2026",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("tx", "tx_ccs"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("tx", "tx_chip"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("tx", "tx_csfp"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("tx", "tx_dart"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("tx", "tx_early_head_start"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("tx", "tx_emergency_medicaid"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("tx", "tx_fpp"): Vintage(
        edition="2026",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("tx", "tx_harris_rides"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("tx", "tx_head_start"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("tx", "tx_htw"): Vintage(
        edition="2026",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("tx", "tx_lifeline"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("tx", "tx_liheap"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("tx", "tx_medicaid_for_children"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("tx", "tx_medicaid_for_parents_and_caretakers"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("tx", "tx_medicaid_for_pregnant_women"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("tx", "tx_medicare_savings_program"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("tx", "tx_nslp"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("tx", "tx_ssi"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("tx", "tx_tanf"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("tx", "tx_wap"): Vintage(
        edition="2026",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("tx", "tx_wic"): Vintage(
        edition="2025",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("wa", "wa_apple_health_for_kids"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("wa", "wa_apple_health_medicaid"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("wa", "wa_csfp"): Vintage(
        edition="2026",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("wa", "wa_fap"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("wa", "wa_head_start"): Vintage(
        edition="2026",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("wa", "wa_lifeline"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("wa", "wa_liheap"): Vintage(
        edition="2026",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("wa", "wa_orca_lift"): Vintage(
        edition="2026",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("wa", "wa_ssi"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("wa", "wa_tanf"): Vintage(
        edition="2026",
        basis=Basis.COVERAGE_YEAR,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("wa", "wa_wap"): Vintage(
        edition="2026",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
    ("wa", "wa_wic"): Vintage(
        edition="2026",
        basis=Basis.TABLE_EDITION,
        status=Status.UNVERIFIED,
        rule="not researched; recorded as production has it",
        source="",
    ),
}
