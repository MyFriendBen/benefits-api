from screener.models import Screen
from programs.framework.pe_base import PolicyEngineCalulator
from programs.framework.base import Eligibility
from typing import Any, Dict, List, Optional, Tuple, TypedDict
from sentry_sdk import capture_exception, capture_message
from .engines import Sim, pe_engines
from programs.framework.pe_dependencies.base import ConflictingDependencyError
from programs.framework.pe_dependencies.payload import (
    PayloadPlan,
    _resolve_comparable_version,
    bucket_payload,
    build_pe_input,
)
from . import versions as pe_versions
from integrations.external_api_status import record_external_api_failure, POLICY_ENGINE
from django.conf import settings


class PEData(TypedDict, total=False):
    request: Optional[Dict[str, Any]]
    response: Optional[Dict[str, Any]]

    #: Present only when the screen's programs disagreed about an input and had to be split
    #: across more than one request. The admin PolicyEngine view reads `request`/`response`,
    #: so the first request keeps those keys and the rest arrive here rather than changing
    #: the shape of a payload every screen returns.
    additional_requests: List[Dict[str, Any]]


class EligibilityPEResult(TypedDict):
    eligibility: Dict[str, Eligibility]
    _pe_data: PEData


def calc_pe_eligibility(
    screen: Screen,
    calculators: dict[str, PolicyEngineCalulator],
    pe_version: Optional[str] = None,
) -> EligibilityPEResult:
    valid_programs: dict[str, PolicyEngineCalulator] = {}

    for name_abbr, calculator in calculators.items():
        if not calculator.can_calc():
            continue
        valid_programs[name_abbr] = calculator

    # Resolve the model version ONCE and thread it through both consumers: independent
    # resolutions can disagree (PolicyEngine promotes a new `current`, or our cached lookup
    # expires or fails between calls), and a disagreement is exactly the failure
    # _drop_unreadable_programs exists to prevent — a program kept because the first
    # resolution supported its output, then its field withheld because the second didn't.
    version = pe_versions.determine_pe_version(pe_version)
    comparable_version = _resolve_comparable_version(list(valid_programs.values()), version)

    valid_programs = _drop_unreadable_programs(valid_programs, comparable_version)

    empty_result: EligibilityPEResult = {
        "eligibility": {},
        "_pe_data": {"request": None, "response": None},
    }

    if not valid_programs or not screen.household_members.all():
        return empty_result

    program_names = list(valid_programs.keys())
    program_list = list(valid_programs.values())

    try:
        plan = build_pe_input(
            screen,
            program_list,
            pe_version=pe_version,
            resolved_version=(version, comparable_version),
        )
    except ConflictingDependencyError as e:
        # Unreachable by design: build_pe_input partitions disagreeing programs into separate
        # requests before writing a value, so this means the partition itself is wrong. It is
        # caught rather than left to propagate because the whole point of splitting is that
        # one program's input disagreement must not take down every program's results — a bug
        # here costs the PolicyEngine programs for this screen, not the response.
        capture_exception(e, level="error")
        capture_message(
            "PolicyEngine: payload assembly could not resolve a dependency conflict; "
            "PolicyEngine programs are unavailable for this screen.",
            level="error",
        )
        return empty_result

    _report_conflicts(plan, program_names)
    for index in plan.dropped_program_indexes:
        valid_programs.pop(program_names[index], None)

    eligibility: Dict[str, Eligibility] = {}
    requests_made: List[Dict[str, Any]] = []

    # One request per bucket. Almost every screen has exactly one: a second appears only when
    # two programs want different values for the same input, and then the alternative is
    # serving one of them a value its rule doesn't mean.
    for bucket in plan.buckets:
        bucket_programs = {program_names[index]: program_list[index] for index in bucket.program_indexes}
        payload = bucket_payload(plan, bucket)

        bucket_eligibility, data = _run_bucket(payload, bucket_programs)
        eligibility.update(bucket_eligibility)
        requests_made.append(data)

    return {"eligibility": eligibility, "_pe_data": _combine_pe_data(requests_made)}


def _run_bucket(
    input_data: Dict[str, Any],
    valid_programs: dict[str, PolicyEngineCalulator],
) -> Tuple[Dict[str, Eligibility], Dict[str, Any]]:
    """Send one payload and read its programs' results.

    Failure is contained to this bucket: the programs in it are absent from the merged
    eligibility (the caller reports them as missing), and any other bucket still returns.
    A screen with one bucket behaves exactly as it did before splitting existed — empty
    eligibility, and the payload preserved for admins to debug.
    """
    # A single engine: the authenticated private household.api. There is deliberately no
    # fallback to the public api.policyengine.org — it ignores the request `version` field
    # (verified against its source) and would silently compute against a different model
    # version than the one we resolve and pin. So any failure here means PolicyEngine
    # programs are unavailable for this screen.
    for Method in pe_engines:
        try:
            method_instance = Method(input_data)
            eligibility = all_eligibility(method_instance, valid_programs)
            result = (
                eligibility,
                {
                    "request": getattr(method_instance, "request_payload", None),
                    "response": getattr(method_instance, "response_json", None),
                },
            )
        except (SystemExit, KeyboardInterrupt) as e:
            # Worker is being torn down: gunicorn's SIGABRT handler (fired when a request
            # exceeds the worker --timeout, e.g. while a PE HTTP call hangs on DNS) calls
            # sys.exit(), raising SystemExit. That is a BaseException, so the `except
            # Exception` below never sees it and the death is invisible in Sentry. Capture
            # it here for visibility, then re-raise so the shutdown proceeds normally.
            capture_exception(e, level="error")
            capture_message(
                f"Worker exited mid-request while calculating eligibility with the " f"{Method.method_name} method",
                level="error",
            )
            raise
        except Exception as e:
            # Any PolicyEngine failure (malformed payload/400, timeout, 5xx, auth, non-JSON):
            # with no fallback endpoint, these programs can't be computed for this screen.
            # Surface it loudly (Sentry error), record it so the frontend can warn the user,
            # and return no eligibility so the caller still computes the non-PolicyEngine
            # (custom) calculators.
            if settings.DEBUG:
                print(repr(e))
            capture_exception(e, level="error")
            capture_message(
                f"Failed to calculate eligibility with the {Method.method_name} method; "
                f"PolicyEngine programs are unavailable for this screen.",
                level="error",
            )
            record_external_api_failure(POLICY_ENGINE)
            # Preserve the payload that triggered the failure so admins can debug it
            # (the exact request is the most useful thing for diagnosing a 400).
            # _pe_data.request is admin-only — already popped for non-admins downstream.
            return {}, {"request": input_data, "response": None}
        else:
            return result

    return {}, {"request": None, "response": None}


def _combine_pe_data(requests_made: List[Dict[str, Any]]) -> PEData:
    """Report the requests as one `_pe_data`, keeping the single-request shape intact."""
    if not requests_made:
        return {"request": None, "response": None}

    data: PEData = dict(requests_made[0])
    if len(requests_made) > 1:
        data["additional_requests"] = requests_made[1:]

    return data


def _report_conflicts(plan: PayloadPlan, program_names: List[str]) -> None:
    """Make a disagreement visible. It is never load-bearing for the response — the split
    already handled it — but it means a program silently wanting a different value than
    everyone else shows up somewhere other than a puzzling extra request."""
    if not plan.conflicts:
        return

    split = " | ".join(", ".join(program_names[index] for index in bucket.program_indexes) for bucket in plan.buckets)
    message = (
        f"PolicyEngine: programs disagreed about {len(plan.conflicts)} payload slot(s), "
        f"split across {len(plan.buckets)} request(s) [{split}]. Conflicts: {plan.conflicts}"
    )

    if plan.dropped_program_indexes:
        dropped = sorted(program_names[index] for index in plan.dropped_program_indexes)
        message = f"{message} Dropped (past the request limit, no result for these): {dropped}"

    capture_message(message, level="warning")


def all_eligibility(method: Sim, valid_programs: dict[str, PolicyEngineCalulator]):
    all_eligibility: dict[str, Eligibility] = {}
    for name_abbr, calculator in valid_programs.items():
        calculator.set_engine(method)

        e = calculator.calc()

        all_eligibility[name_abbr] = e

    return all_eligibility


def _drop_unreadable_programs(
    valid_programs: dict[str, PolicyEngineCalulator],
    comparable_version: Optional[tuple],
) -> dict[str, PolicyEngineCalulator]:
    """Drop programs whose own output variable the resolved model doesn't define.

    Version gating withholds such a field, so PolicyEngine never returns it and `Sim.value`
    raises KeyError on the missing key. `all_eligibility` has no per-program error handling, so
    one unreadable program would empty the PE result for the whole screen.

    Gated *inputs* need no equivalent — withholding one just leaves PolicyEngine to model the
    value itself. Only outputs are load-bearing this way, and the receipt-contract outputs are
    the first gated ones in the codebase.

    Reachable via an exact `PolicyEngineConfig` pin below a floor, or via /versions/us being
    unreachable while /calculate is healthy. `comparable_version` is the request's single
    resolved version; None conservatively drops every program carrying a gated output.
    """
    if not valid_programs:
        return valid_programs

    readable: dict[str, PolicyEngineCalulator] = {}
    dropped: list[str] = []
    for name_abbr, calculator in valid_programs.items():
        unsupported = [
            Data.field
            for Data in calculator.pe_outputs
            if not pe_versions.version_supports(
                comparable_version,
                getattr(Data, "min_pe_version", ()),
                getattr(Data, "max_pe_version", ()),
            )
        ]
        if unsupported:
            dropped.append(f"{name_abbr} ({', '.join(unsupported)})")
            continue
        readable[name_abbr] = calculator

    if dropped:
        # Make the reason visible rather than leaving it inferred from a program's absence.
        capture_message(
            f"PolicyEngine: dropped {len(dropped)} program(s) whose output variable the resolved "
            f"model version does not define: {sorted(dropped)}",
            level="warning",
        )

    return readable
