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
| `registry.py` | Builds the `program_code` → calculator mapping by walking `programs.programs` |
| `eligibility_messages.py` | The translatable strings a calculator passes to `Eligibility.condition()` to explain why a household met or missed a rule. Keyed `eligibility_message.*` in the Translation table |
| `tests/` | Tests of framework code and repo-wide invariants — not of any program's behavior |

Naming: an unprefixed name means both engines use it; a `pe_` prefix means the file is
PolicyEngine-specific. That extends to the tests, so `test_pe_*` marks a test as
PolicyEngine-only.

## Not here

**Fixtures program tests import** live in `programs/programs/testing_fixtures/` — the
PolicyEngine household builders, the payload-assertion base, and the received-benefit
fixture. Those are consumed by program tests, so they sit with the programs. This directory
holds the framework's own tests, and `tests/cassettes/` holds the single cassette proving
the harness replays one.

The PolicyEngine **HTTP client** lives in `integrations/clients/policyengine/` —
`engines.py`, `policy_engine.py`, `versions.py`. That's the wire layer: the POST, the auth
token cache, version resolution. This directory is the calculator layer that sits on top of
it, and it reads our own models, so it is not a client concern.

That line also decides where tests go. `test_versions.py` and `test_pe_failure.py` test the
client and live with it; the client holds no cassettes.

**A program's own tests and cassettes live next to the program** —
`cross_white_label/<family>/tests/` for a family member, `white_labels/<wl>/<program>/tests/`
for a standalone program, with `cassettes/` beside them. `conftest.py` derives
`cassette_library_dir` from each test file's directory, so tests and cassettes always travel
together.
