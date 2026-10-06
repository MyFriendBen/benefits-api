"""Support for tests that run a PolicyEngine calculator end to end.

These build a household, call one PolicyEngine calculator, and assert on the eligibility and
value it returns. Because the answer comes from PolicyEngine rather than from our code, such
tests are marked ``@pytest.mark.integration`` and run against a recorded VCR cassette: live
once when the program is implemented, then replayed in CI. See docs/TESTING.md for the
record/replay commands.

Where the assertions come from is up to the caller — today that is usually a program's
``spec.md`` Test Scenarios section, mirrored one test per scenario, but nothing here depends
on that.

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

import json
import math
import os
from typing import Optional

import pytest
from decouple import config
from django.core.cache import cache
from django.test import TestCase

from conftest import vcr_record_mode
from configuration.models import PolicyEngineConfig
from programs.models import Program
from programs.framework.base import Eligibility
from programs.util import Dependencies
from programs.programs.testing_fixtures import households
from programs.programs.testing_fixtures.households import add_income, make_program  # noqa: F401 -- re-exports
from screener.models import HouseholdMember, Screen

from integrations.clients.policyengine.engines import _PE_TOKEN_CACHE_KEY, PrivateApiSim
from programs.framework.pe_dependencies.payload import pe_input

# Placeholder used when replaying. Never sent anywhere real: the recorded response replays
# regardless of the token, and conftest redacts the Authorization header from cassettes.
TEST_PE_TOKEN = "pe-integration-test-token"

# Env var that opts a run in to recording. Recording is explicit rather than inferred from
# VCR_MODE: the default mode ("once") only records when the cassette file is missing, so the
# mode alone can't tell us whether this run needs a real token.
PE_RECORD_ENV_VAR = "PE_RECORD"
_TRUTHY = ("1", "true", "yes")

# The PolicyEngine version every PeIntegrationTestCase records and replays at unless it
# overrides ``pe_version``. Adopting a new version is a bump here plus a re-record of every
# module that doesn't override. Must be one PolicyEngine currently serves (see docs/TESTING.md).
PE_TEST_VERSION = "2.9.0"

# Both used by the record_and_diff management command. The override replaces every test case's
# pe_version for the run, so the whole suite can be recorded at a new version without editing any
# module. The capture directory collects each scenario's outcome (see capture_result).
PE_VERSION_OVERRIDE_ENV_VAR = "PE_VERSION_OVERRIDE"
PE_CAPTURE_DIR_ENV_VAR = "PE_CAPTURE_DIR"


def check_pe_version_pin(test_name: str, pe_version: str, pe_version_reason: str) -> None:
    """Fail a test class whose pin is missing, or departs from the suite pin without saying why.

    A module still on an older version can't simply follow ``PE_TEST_VERSION``: the version is
    part of the request body VCR matches on, so its cassettes replay only at the version they
    were recorded at. Overriding is therefore allowed, but has to carry a reason, so that every
    module behind the suite pin is a deliberate, visible exception rather than a forgotten one.
    """
    if not pe_version:
        raise AssertionError(
            f"{test_name} must set pe_version to the exact PolicyEngine version its cassettes were recorded at."
        )

    if pe_version != PE_TEST_VERSION and not pe_version_reason.strip():
        raise AssertionError(
            f"{test_name} pins PolicyEngine {pe_version} instead of the suite pin {PE_TEST_VERSION}. "
            "Set pe_version_reason to say why, or re-record its cassettes at the suite pin."
        )


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

    return has_credentials and vcr_record_mode() != "none"


def _forces_live_recording() -> bool:
    """Whether VCR_MODE makes replay impossible for this run.

    ``all`` never replays, so it re-runs every scenario against live PolicyEngine. That can't
    work here: these cassettes pin an exact model version, and PolicyEngine serves only what
    ``current``/``frontier`` currently resolve to — once it promotes past the pin, the same
    request returns 422 ``unsupported_version``. Refreshing a cassette is therefore a
    deliberate act (bump ``pe_version``, re-record, review the value diff — see
    docs/TESTING.md), never something a CI run should attempt on its own.
    """
    return vcr_record_mode() == "all"


def seed_pe_token(token: str = TEST_PE_TOKEN) -> None:
    """Make a bearer token available without recording the auth exchange.

    When recording (``PE_RECORD=1``), leave the cache alone so ``PrivateApiSim`` fetches a real
    token — the auth0 host is in VCR's ``ignore_hosts``, so that request passes through and is
    never written to a cassette (its response body is a live token).

    Otherwise seed a placeholder so nothing tries to authenticate at all. ``engines`` reads the
    token from the Django cache, which the autouse ``clear_cache`` fixture empties before every
    test — so this has to be re-seeded per test (``PeIntegrationTestCase.setUp`` does).
    """
    if _can_record():
        return

    # No expiry: the entry only has to outlive this one test, and clear_cache removes it.
    cache.set(_PE_TOKEN_CACHE_KEY, token, timeout=None)


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
    **kwargs,
) -> Screen:
    """`households.make_screen` with an explicit primary key.

    ``screen_id`` is explicit for the same reason member ids are: a cassette is only
    replayable when the household it was recorded from can be rebuilt exactly.
    """
    return households.make_screen(
        white_label_code=white_label_code,
        state_code=state_code,
        household_size=household_size,
        id=screen_id,
        **kwargs,
    )


def add_member(screen: Screen, member_id: int, relationship: str, age: int, **kwargs) -> HouseholdMember:
    """`households.add_member` with an explicit primary key.

    The id becomes the key for this member in both the PolicyEngine request and response, so
    it is part of the cassette's contract — never let it be auto-assigned. Screener defaults are
    off because the committed cassettes were recorded without them.
    """
    return households.add_member(
        screen, relationship=relationship, age=age, id=member_id, screener_defaults=False, **kwargs
    )


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

    try:
        sim = PrivateApiSim(pe_input(screen, [calculator]))
        calculator.set_engine(sim)
        eligibility = calculator.calc()
    except Exception as error:
        capture_result(error=f"{type(error).__name__}: {error}")
        raise

    capture_result(eligible=bool(eligibility.eligible), value=math.trunc(eligibility.value))

    return eligibility


def capture_result(eligible: Optional[bool] = None, value: Optional[int] = None, error: Optional[str] = None) -> None:
    """Append this test's PolicyEngine outcome to the capture directory, when one is set.

    A no-op unless ``PE_CAPTURE_DIR`` is set. ``record_and_diff`` sets it on a replay run and a
    recording run and compares the two, which is how a new PolicyEngine version's effect is
    measured per scenario. Captured before the test asserts, so a changed value is recorded even
    though the test then fails. Each xdist worker writes its own file, so lines never interleave.
    """
    capture_dir = os.getenv(PE_CAPTURE_DIR_ENV_VAR)
    if not capture_dir:
        return

    os.makedirs(capture_dir, exist_ok=True)
    worker = os.getenv("PYTEST_XDIST_WORKER", "main")
    record = {
        # PYTEST_CURRENT_TEST is "<nodeid> (<phase>)".
        "test": os.getenv("PYTEST_CURRENT_TEST", "").rsplit(" ", 1)[0],
        "pe_version": PolicyEngineConfig.current_version(),
        "eligible": eligible,
        "value": value,
        "error": error,
    }
    with open(os.path.join(capture_dir, f"{worker}.jsonl"), "a") as f:
        f.write(json.dumps(record) + "\n")


def screener_value(eligibility: Eligibility) -> int:
    """The whole-dollar value the screener reports for this eligibility.

    PolicyEngine returns fractional dollars (a member value can be 12076.413) and the API
    truncates before serving it (``screener/views.py`` ``clean_program``). Asserting the
    truncated value lets expectations stay in whole dollars — the number a QA run or a user
    actually sees — instead of encoding sub-cent noise into every test.
    """
    return math.trunc(eligibility.value)


class PeIntegrationTestCase(TestCase):
    """Base class for a program's PolicyEngine tests.

    Cassettes are recorded at ``PE_TEST_VERSION`` by default. A subclass whose cassettes were
    recorded at another version overrides ``pe_version`` and says why in
    ``pe_version_reason``; changing either version means re-recording.
    """

    # Applies VCR to every subclass. Carried here rather than left to each subclass to
    # decorate: a class that forgot the marker would get no cassette at all, call PolicyEngine
    # live on every run, pass locally for anyone with credentials, and fail in CI with a 401
    # that looks like a program bug. Subclasses may still decorate themselves — marks compose.
    pytestmark = pytest.mark.integration

    # Exact MAJOR.MINOR.PATCH the cassettes in this module were recorded against.
    pe_version: str = PE_TEST_VERSION

    # Required whenever pe_version differs from PE_TEST_VERSION.
    pe_version_reason: str = ""

    def setUp(self) -> None:
        super().setUp()

        check_pe_version_pin(type(self).__name__, self.pe_version, self.pe_version_reason)

        if _forces_live_recording():
            self.skipTest(
                f"VCR_MODE=all re-records live, but these cassettes pin PolicyEngine "
                f"{self.pe_version}, which PolicyEngine stops serving once it promotes past it "
                "(422 unsupported_version). Refresh cassettes deliberately — see docs/TESTING.md."
            )

        pin_pe_version(os.getenv(PE_VERSION_OVERRIDE_ENV_VAR) or self.pe_version)
        seed_pe_token()
