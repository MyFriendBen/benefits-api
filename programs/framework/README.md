# Calculator framework

The base classes and shared pieces every program calculator builds on.

## What belongs here

Only code that every calculator needs, regardless of white label or engine.

- If all of a file's consumers are in one white label, it belongs to that white label.
- If they span some white labels but not all, it belongs to whatever groups them —
  usually a family under `cross_white_label/`.

## Contents

| File | What it is |
| -- | -- |
| `base.py` | `ProgramCalculator`, `Eligibility`, `MemberEligibility` — the root base every calculator inherits from |
| `pe_base.py` | `PolicyEngineCalulator` and its Spm / TaxUnit / Members variants. Subclasses `ProgramCalculator`, so PE calculators are MFB calculators with a PolicyEngine backend |
| `pe_dependencies/` | The `Screen` → PolicyEngine input translation layer. One module per PE entity (member, spm, household, tax) |
| `eligibility_messages.py` | The translatable strings a calculator passes to `Eligibility.condition()` to explain why a household met or missed a rule. Keyed `eligibility_message.*` in the Translation table |
| `tests/` | Tests of framework code and repo-wide invariants — not of any program's behavior. Also holds `integration_test_helpers.py`, the VCR harness program tests import, and the one cassette that proves the harness replays |

Naming: an unprefixed name means both engines use it; a `pe_` prefix means the file is
PolicyEngine-specific.

## Not here

The PolicyEngine **HTTP client** lives in `integrations/clients/policyengine/` —
`engines.py`, `policy_engine.py`, `versions.py`. That's the wire layer: the POST, the auth
token cache, version resolution. This directory is the calculator layer that sits on top of
it, and it reads our own models, so it is not a client concern.

That line also decides where tests go. `test_versions.py` and `test_pe_failure.py` test the
client and live with it; the client holds **no cassettes**. The VCR harness and its cassette
are here instead, because the harness builds `Screen`s and runs calculators.

**A program's own tests and cassettes live next to the program** —
`programs/programs/{state}/{program}/tests/` with `cassettes/` beside them. `conftest.py`
derives `cassette_library_dir` from each test file's directory, so tests and cassettes always
travel together.

## Temporary residents

`helpers.py`, `mixins.py`, and `tests/test_presumptive_eligibility_resolution.py` violate
the rule above and are annotated in place. They move to their real homes in MFB-1676, once
the `cross_white_label/` and `white_labels/` directories exist to receive them.
