"""The program-gate graph: which calculators read another program's result.

A *gate* is a calculator asking whether the household qualifies for a **different** program.
The graph is declared rather than discovered: `ProgramCalculator.gates_on` names the
upstreams read through the raising accessors (`program_eligible`,
`member_program_eligible`), and `gates_on_any` names those read through the tolerant one
(`any_program_eligible`).

Declaring is what lets production code use the graph at all — the previous source of truth
was an `ast` walk living in `screener/tests/test_calc_order.py`, which production cannot
import. Three consumers now read it:

- `ProgramCalculator.can_calc` requires a strict upstream's own screener fields, so a
  dependent can never be calculable on a screen where its upstream is not.
- `screener.views` calculates the custom upstreams regardless of configuration.
- `screener.views.CALC_ORDER` is checked against it.

`test_calc_order.py` still walks the source, but only to assert the declarations match the
calls — a consistency check rather than the graph itself.
"""

from functools import lru_cache


@lru_cache(maxsize=1)
def all_calculator_classes() -> dict:
    """Both engines' registries merged, so an upstream is found whichever backs it.

    Imported lazily: the registries are built by walking every calculator, and the
    PolicyEngine base imports `Program`, so at module-import time the cycle is unresolvable.
    """
    from integrations.clients.policyengine.registry import all_calculators as pe_calculators
    from programs.programs import calculators as custom_calculators

    return {**custom_calculators, **pe_calculators}


@lru_cache(maxsize=None)
def strict_upstream_fields(codes: tuple) -> frozenset:
    """The screener fields `codes` need before they can be calculated.

    Read off `pe_inputs` for a PolicyEngine upstream and `dependencies` for a custom one.
    PolicyEngine calculators carry no class-level `dependencies` — each `pe_input` declares
    its own and `PolicyEngineCalulator.can_calc` unions them — so subtracting the class
    attribute (as this used to) is always a no-op for them.

    Transitive: a custom upstream's own strict upstreams are followed, because
    `il_aca_adults` gates on `il_family_care`, which gates in turn on `il_medicaid`. The
    walk is iterative and tracks what it has seen, so a cycle terminates instead of
    recursing forever.
    """
    fields: set = set()
    seen: set = set()
    queue = list(codes)

    while queue:
        code = queue.pop()
        if code in seen:
            continue
        seen.add(code)

        Calculator = all_calculator_classes().get(code)
        if Calculator is None:
            continue

        pe_inputs = getattr(Calculator, "pe_inputs", None)
        if pe_inputs is None:
            fields.update(Calculator.dependencies)
            # Only strict upstreams propagate: a tolerant gate reads an absent upstream as
            # "no", so it does not need that upstream to be calculable.
            queue.extend(Calculator.gates_on)
        else:
            fields.update(field for pe_input in pe_inputs for field in pe_input.dependencies)

    return frozenset(fields)


@lru_cache(maxsize=1)
def gated_upstream_codes() -> frozenset:
    """Every program code read through a gate, strict or tolerant, across both engines."""
    codes: set = set()
    for Calculator in all_calculator_classes().values():
        codes.update(Calculator.gates_on)
        codes.update(Calculator.gates_on_any)

    return frozenset(codes)


@lru_cache(maxsize=1)
def force_calculated_codes() -> frozenset:
    """Gated upstreams to calculate regardless of how their `Program` row is configured.

    Custom calculators only. A gate is starved whenever its upstream is absent from the
    eligibility loop's program list, and `active=False`, a NULL category,
    `has_calculator=False` and `Referrer.remove_programs` all put it there — none of which
    is a statement about the household. Calculating the upstream anyway (and withholding it
    from the response) decouples the gate from display configuration.

    PolicyEngine upstreams are deliberately excluded. Adding one means adding it to the
    batched `calc_pe_eligibility` request, where every program's `pe_inputs` are merged into
    one household payload: it could change an unrelated active program's result, split the
    payload into an extra request, or be dropped by the partitioner regardless. And it would
    not buy the guarantee — the failure these gates actually die from is the PolicyEngine
    call itself, which no ordering or configuration change can prevent.
    """
    from integrations.clients.policyengine.registry import all_calculators as pe_calculators

    return frozenset(code for code in gated_upstream_codes() if code not in pe_calculators)
