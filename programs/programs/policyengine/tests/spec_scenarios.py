"""Support for PolicyEngine spec-scenario tests.

A spec-scenario test mirrors one entry in a program's ``spec.md`` Test Scenarios section
1:1 and asserts both eligibility and benefit value. Because the answer comes from
PolicyEngine rather than from our code, these tests are marked ``@pytest.mark.integration``
and run against a recorded VCR cassette: live once when the program is implemented, then
replayed in CI. See docs/TESTING.md for the record/replay commands.

Three things have to hold for a PolicyEngine call to be replayable from a cassette, and all
three are handled here:

1. **Explicit primary keys.** ``pe_input`` keys ``household.people`` by ``str(member.id)``
   and ``PrivateApiSim.value`` reads the response back by that same key. A cassette recorded
   under different auto-increment pks neither matches the request nor can be read, so
   ``make_screen``/``add_member`` require ids.
2. **A pinned model version.** ``determine_pe_version`` falls back to the floating "current"
   alias when nothing is pinned, which makes the recorded body non-reproducible; an unpinned
   request carrying a version-gated input also fires a second HTTP call (GET /versions/us).
   ``pin_pe_version`` removes both.
3. **A bearer token that isn't fetched during replay.** The auth0 host is in VCR's
   ``ignore_hosts`` so the token exchange is never written to a cassette (its response body
   is a real token). ``PE_RECORD=1`` fetches one live; every other run seeds a placeholder
   and touches no network at all.

These helpers run exactly one POST to household.api per scenario, which is what makes a
cassette hold a single meaningful interaction.

A pinned version and ``VCR_MODE=all`` are incompatible by construction — PolicyEngine only
serves what ``current``/``frontier`` currently resolve to — so these tests skip under ``all``
rather than fail a release. Re-recording is always also the act of adopting a new version.
"""

import math
import os
from typing import Optional

import pytest
from decouple import config
from django.test import TestCase
from django.utils import timezone

from configuration.models import PolicyEngineConfig
from programs.models import FederalPoveryLimit, Program
from programs.programs.calc import Eligibility
from programs.util import Dependencies
from screener.models import HouseholdMember, IncomeStream, Screen, WhiteLabel

from ..engines import PrivateApiSim
from ..policy_engine import pe_input

# Placeholder used when replaying. Never sent anywhere real: the recorded response replays
# regardless of the token, and conftest redacts the Authorization header from cassettes.
TEST_PE_TOKEN = "pe-spec-scenario-token"

# Env var that opts a run in to recording. Recording is explicit rather than inferred from
# VCR_MODE: the default mode ("once") only records when the cassette file is missing, so the
# mode alone can't tell us whether this run needs a real token.
PE_RECORD_ENV_VAR = "PE_RECORD"
_TRUTHY = ("1", "true", "yes")


def _can_record() -> bool:
    """Whether this run intends to record live, and so needs a real bearer token.

    Opt-in via ``PE_RECORD=1``. Without it an ordinary replay run never touches auth0 — which
    matters because ``ignore_hosts`` lets the token exchange through to the network, so
    inferring "might record" from the presence of credentials made every local run of a
    fully-recorded suite fire a live auth call for no benefit.
    """
    if os.getenv(PE_RECORD_ENV_VAR, "").lower() not in _TRUTHY:
        return False

    has_credentials = bool(config("POLICY_ENGINE_CLIENT_ID", default="")) and bool(
        config("POLICY_ENGINE_CLIENT_SECRET", default="")
    )

    return has_credentials and os.getenv("VCR_MODE", "once").lower() != "none"


def _forces_live_recording() -> bool:
    """Whether VCR_MODE makes replay impossible for this run.

    ``all`` never replays, so it re-runs every scenario against live PolicyEngine. That can't
    work here: these cassettes pin an exact model version, and PolicyEngine serves only what
    ``current``/``frontier`` currently resolve to — once it promotes past the pin, the same
    request returns 422 ``unsupported_version``. Refreshing a cassette is therefore a
    deliberate act (bump ``pe_version``, re-record, review the value diff — see
    docs/TESTING.md), never something a CI run should attempt on its own.
    """
    return os.getenv("VCR_MODE", "once").lower() == "all"


def seed_pe_token(token: str = TEST_PE_TOKEN) -> None:
    """Make a bearer token available without recording the auth exchange.

    When recording (``PE_RECORD=1``), leave the cache alone so ``PrivateApiSim`` fetches a real
    token — the auth0 host is in VCR's ``ignore_hosts``, so that request passes through and is
    never written to a cassette (its response body is a live token).

    Otherwise seed a placeholder so nothing tries to authenticate at all. The cache is an
    in-process class attribute on ``PrivateApiSim`` (not the Django cache), so this holds for
    the rest of the test process.
    """
    if _can_record():
        return

    token_cache = PrivateApiSim.token
    token_cache.save(token)
    token_cache.last_update = timezone.now()
    token_cache.invalid = False


def pin_pe_version(version: str) -> None:
    """Pin the PolicyEngine model version sent in the request body.

    Must be an exact MAJOR.MINOR.PATCH version — the floating aliases are rejected by
    ``PolicyEngineConfig.clean``, and pinning is what makes the recorded body stable.
    """
    PolicyEngineConfig.objects.create(policyengine_version=version)


def make_screen(
    screen_id: int,
    white_label_code: str,
    state_code: str,
    household_size: int,
    zipcode: str = "",
    county: str = "",
    household_assets: int = 0,
    **kwargs,
) -> Screen:
    """Create a Screen with an explicit primary key.

    ``screen_id`` is explicit for the same reason member ids are: a cassette is only
    replayable when the household it was recorded from can be rebuilt exactly.
    """
    white_label, _ = WhiteLabel.objects.get_or_create(
        code=white_label_code,
        defaults={"name": white_label_code.upper(), "state_code": state_code},
    )

    return Screen.objects.create(
        id=screen_id,
        white_label=white_label,
        zipcode=zipcode,
        county=county,
        household_size=household_size,
        household_assets=household_assets,
        completed=False,
        **kwargs,
    )


def add_member(screen: Screen, member_id: int, relationship: str, age: int, **kwargs) -> HouseholdMember:
    """Add a household member with an explicit primary key.

    The id becomes the key for this member in both the PolicyEngine request and response, so
    it is part of the cassette's contract — never let it be auto-assigned.
    """
    return HouseholdMember.objects.create(
        id=member_id,
        screen=screen,
        relationship=relationship,
        age=age,
        **kwargs,
    )


def add_income(
    member: HouseholdMember,
    amount: int,
    income_type: str = "wages",
    frequency: str = "monthly",
) -> IncomeStream:
    """Give a member an income stream, as stated by the scenario.

    Amount and frequency are recorded verbatim from the spec — PolicyEngine annualizes them,
    so converting to a yearly figure in the test would obscure what the scenario says.
    """
    return IncomeStream.objects.create(
        screen=member.screen,
        household_member=member,
        type=income_type,
        amount=amount,
        frequency=frequency,
    )


def make_program(white_label_code: str, name_abbreviated: str, year: str) -> Program:
    """Create the Program row a PolicyEngine calculator needs.

    ``year`` supplies ``program.year.period``, which is the period every PolicyEngine input
    and output is requested for — it appears in the request body, so it is part of what the
    cassette pins down.
    """
    fpl, _ = FederalPoveryLimit.objects.get_or_create(year=year, defaults={"period": year})

    program = Program.objects.new_program(white_label=white_label_code, name_abbreviated=name_abbreviated)
    program.year = fpl
    program.save()

    return program


def calc_pe_program(
    screen: Screen,
    calculator_class: type,
    program: Program,
    missing_dependencies: Optional[Dependencies] = None,
) -> Eligibility:
    """Run one PolicyEngine calculator end to end and return its Eligibility.

    Deliberately does not go through ``calc_pe_eligibility``: that function catches every
    exception, reports it to Sentry and returns an empty result, which would turn a cassette
    miss into a confusing empty-dict failure instead of VCR's own error. Everything else
    matches the production path — build the payload, POST once, hand the sim to the
    calculator, calc.

    Note the calculator *instance* (not the class) is passed to ``pe_input``: ``pe_period``
    is a property that reads ``self.program.year``, so a class would yield a property object
    as the period key rather than the period.
    """
    calculator = calculator_class(screen, program, missing_dependencies or Dependencies())

    # The one production step we can't skip silently. calc_pe_eligibility drops a calculator
    # that can't calc *before* building a payload, so the program never reaches the screener
    # at all — a scenario asserting on calc() output when can_calc() is False would be
    # asserting against a path production never takes.
    if not calculator.can_calc():
        raise AssertionError(
            f"{calculator_class.__name__} cannot calc for this screen (missing dependencies), so "
            "production would omit this program entirely rather than calling PolicyEngine. Assert "
            "on the program's absence instead of on an Eligibility."
        )

    sim = PrivateApiSim(pe_input(screen, [calculator]))
    calculator.set_engine(sim)

    return calculator.calc()


def screener_value(eligibility: Eligibility) -> int:
    """The whole-dollar value the screener reports for this eligibility.

    PolicyEngine returns fractional dollars (a member value can be 12076.413) and the API
    truncates before serving it (``screener/views.py`` ``clean_program``). Asserting the
    truncated value keeps spec.md expectations in whole dollars — the number a QA run or a
    user actually sees — instead of encoding sub-cent noise into every test.
    """
    return math.trunc(eligibility.value)


class PeSpecScenarioTestCase(TestCase):
    """Base class for a program's spec-scenario tests.

    Subclasses set ``pe_version`` to the version the cassettes were recorded at (keep it in
    sync with the pinned ``PolicyEngineConfig`` version; changing it means re-recording).
    """

    # Applies VCR to every subclass. Carried here rather than left to each subclass to
    # decorate: a class that forgot the marker would get no cassette at all, call PolicyEngine
    # live on every run, pass locally for anyone with credentials, and fail in CI with a 401
    # that looks like a program bug. Subclasses may still decorate themselves — marks compose.
    pytestmark = pytest.mark.integration

    # Exact MAJOR.MINOR.PATCH the cassettes in this module were recorded against.
    pe_version: str = ""

    def setUp(self):
        super().setUp()

        if not self.pe_version:
            raise AssertionError(
                f"{type(self).__name__} must set pe_version to the exact PolicyEngine version "
                "its cassettes were recorded at."
            )

        if _forces_live_recording():
            self.skipTest(
                f"VCR_MODE=all re-records live, but these cassettes pin PolicyEngine "
                f"{self.pe_version}, which PolicyEngine stops serving once it promotes past it "
                "(422 unsupported_version). Refresh cassettes deliberately — see docs/TESTING.md."
            )

        pin_pe_version(self.pe_version)
        seed_pe_token()
