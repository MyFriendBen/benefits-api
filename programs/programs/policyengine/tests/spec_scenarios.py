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
   is a real token). Recording fetches one live; replay seeds a placeholder.

These helpers run exactly one POST to household.api per scenario, which is what makes a
cassette hold a single meaningful interaction.
"""

import math
import os
from typing import Optional

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


def _can_record() -> bool:
    """Whether this run may need a real token: credentials configured and a record mode
    that can actually write. ``VCR_MODE=none`` never records, so it never needs one."""
    has_credentials = bool(config("POLICY_ENGINE_CLIENT_ID", default="")) and bool(
        config("POLICY_ENGINE_CLIENT_SECRET", default="")
    )

    return has_credentials and os.getenv("VCR_MODE", "once").lower() != "none"


def seed_pe_token(token: str = TEST_PE_TOKEN) -> None:
    """Make a bearer token available without recording the auth exchange.

    When recording, leave the cache alone so ``PrivateApiSim`` fetches a real token — the
    auth0 host is in VCR's ``ignore_hosts``, so that request passes through and is never
    written to a cassette (its response body is a live token).

    When replaying, seed a placeholder so nothing tries to authenticate at all. The cache is
    an in-process class attribute on ``PrivateApiSim`` (not the Django cache), so this holds
    for the rest of the test process.
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
    sync with the pinned ``PolicyEngineConfig`` version; changing it means re-recording), and
    mark the class ``@pytest.mark.integration`` so the VCR fixture applies.
    """

    # Exact MAJOR.MINOR.PATCH the cassettes in this module were recorded against.
    pe_version: str = ""

    def setUp(self):
        super().setUp()

        if not self.pe_version:
            raise AssertionError(
                f"{type(self).__name__} must set pe_version to the exact PolicyEngine version "
                "its cassettes were recorded at."
            )

        pin_pe_version(self.pe_version)
        seed_pe_token()
