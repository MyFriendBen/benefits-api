import logging

from programs.framework.base import MemberEligibility, ProgramCalculator, Eligibility
import programs.framework.eligibility_messages as messages
from integrations.services.sheets.cache import GoogleSheetsCache
from programs.models import FederalPoveryLimit
from screener.models import HouseholdMember
from sentry_sdk import capture_message

logger = logging.getLogger(__name__)


class ACACache(GoogleSheetsCache):
    CACHE_KEY = "nc_aca_data"
    sheet_id = "1tk8zfO_Ou96UvGrIwZoI3Pv8TvPZZipg7YfzGMT2o3c"
    range_name = "'current report'!A2:B101"

    def _process(self, raw_data):
        result = {}
        for d in raw_data:
            if len(d) < 2:
                continue
            try:
                county_key = d[0].strip() + " County"
                premium_value = float(d[1].replace(",", ""))
                result[county_key] = premium_value
            except (IndexError, ValueError, AttributeError):
                continue  # Skip malformed rows
        return result


class ACASubsidiesNC(ProgramCalculator):
    program_code = "nc_aca_mfb_version"
    percent_of_fpl = 4
    dependencies = ["insurance", "income_amount", "income_frequency", "county", "household_size"]
    eligible_insurance_types = ["none", "private"]
    ineligible_insurance_types = ["va"]
    county_values = ACACache()

    #: A coverage year is adjudicated against the poverty guideline in effect when its open
    #: enrollment opened, which is the prior year's edition -- 26 U.S.C. 36B. So 2026
    #: coverage uses the 2025 guideline ($15,650 for a household of one, 90 FR 5917), not
    #: the 2026 one.
    COVERAGE_YEAR_FPL_LAG = 1

    def _fpl_edition(self) -> FederalPoveryLimit:
        """The poverty guideline edition this coverage year is judged against.

        `program.year` names the COVERAGE year here, the same as it does for the
        PolicyEngine-backed ACA programs (`cross_white_label/aca`). Those get the statutory
        lag applied inside PolicyEngine -- see `aca/specs/ks.md`, which records that 2026
        coverage is scored against the 2025 guideline. This calculator reads the table
        directly instead of going through PolicyEngine, so it has to apply the same lag
        itself or it bands households a year too generously.

        Returns an unsaved row: only `period` matters, `as_dict()` keys the constant off it,
        and constructing one avoids depending on a FederalPoveryLimit row existing for the
        prior year.

        Falls back to the configured edition if the prior one cannot be resolved. A guideline
        one year too new is a slightly wrong income band; raising here would mean North
        Carolina shows no ACA estimate at all.
        """
        configured = self.program.year

        try:
            coverage_year = int(configured.period)
        except (TypeError, ValueError):
            logger.warning(
                "ACASubsidiesNC: non-numeric FederalPoveryLimit period %r; "
                "banding against it directly rather than the prior year's guideline.",
                getattr(configured, "period", None),
            )
            return configured

        prior = str(coverage_year - self.COVERAGE_YEAR_FPL_LAG)
        edition = FederalPoveryLimit(year=prior, period=prior)

        try:
            edition.as_dict()
        except KeyError:
            logger.warning(
                "ACASubsidiesNC: no poverty guideline defined for %s, the edition %s "
                "coverage should be judged against; banding against %s instead.",
                prior,
                coverage_year,
                configured.period,
            )
            return configured

        return edition

    def household_eligible(self, e: Eligibility):
        # Medicade eligibility
        e.condition(not self.program_eligible("nc_medicaid"), messages.must_not_have_benefit("Medicaid"))

        # Income. get_limit() rather than as_dict()[size]: the raw dict stops at size 8 and
        # raises KeyError past it, where get_limit() extrapolates with the per-additional-
        # person amount. Unreachable while the screener caps households at 8, but a bare
        # KeyError here would take out the whole results response if that cap ever moves.
        income_band = int(self._fpl_edition().get_limit(self.screen.household_size) * ACASubsidiesNC.percent_of_fpl)
        gross_income = int(self.screen.calc_gross_income("yearly", ("all",)))
        e.condition(gross_income < income_band, messages.income(gross_income, income_band))

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # no or private insurance
        e.condition(member.insurance.has_insurance_types(ACASubsidiesNC.eligible_insurance_types))

        # no va insurance
        e.condition(not member.insurance.has_insurance_types(ACASubsidiesNC.ineligible_insurance_types))

    def member_value(self, member: HouseholdMember):
        values = self.county_values.get_data()
        county = self.screen.county
        if county not in values:
            # A $0 value is filtered out by the frontend's `value > 0` check, so the
            # program silently vanishes from results rather than erroring. Report it,
            # otherwise a renamed county or an empty sheet fetch is undetectable.
            capture_message(
                f"ACASubsidiesNC: no premium value for county {county!r} of {len(values)} cached",
                level="warning",
            )
            return 0
        return values[county] * 12
