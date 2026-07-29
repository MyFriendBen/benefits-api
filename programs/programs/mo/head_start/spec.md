# Implement Head Start Preschool (MO) Program

## Program Details

- **Program**: Head Start (Preschool)
- **State**: MO
- **White Label**: mo
- **Research Date**: 2026-07-23
- **Calculator Type**: PE / Fed (value varies) — config + light spec.
- **Pinned PE reference**: `policyengine-us` commit `1d80e33cb87286888aa94d29202e434363d6bf2f` — all parameter values, uprating behavior, and file references in this spec are as of this commit. Re-verify against the actual pinned version before execution if the repo has moved on.

Full revision history for this spec lives in `changelog.md`, not in this document. Early Head Start remains a separate ticket (MFB-1335).

## Scope

Eligibility for Head Start Preschool is federal (45 CFR §§1302.12, 1302.14; 1305.2) and is **not** being re-researched or exhaustively tested in this ticket. This ticket exists to isolate and verify Missouri's state-specific **benefit value** only. Any concerns about how completely PolicyEngine's federal Head Start calculator implements federal eligibility law (age-rule delegation, housing-cost adjustment, the 100%-under-130% band, SNAP-as-categorical) are cross-cutting issues that apply to every state's Head Start ticket, not something specific to Missouri — those belong in a separate systemic PE-issue ticket, not here.

**Age-rule note** (context only, not a Missouri eligibility policy): Federal Head Start eligibility uses the public-school eligibility date and compulsory-school age in the community where the program is located. Missouri generally uses an August 1 school-entry boundary (RSMo §160.053), while St. Louis City and Kansas City may select a date up to October 1 (RSMo §§160.054–160.055); Missouri compulsory attendance begins at age 7 (RSMo §167.031). These are shared school-law inputs to the federal rule, not a separate Missouri Head Start eligibility policy, and are not tested with dedicated scenarios in this light spec.

## Benefit Value

**Calculator Type is PE-backed** (`PE / Fed (value varies)`): PolicyEngine's `head_start.py` computes the benefit as state spending ÷ state enrollment (state-keyed, per eligible child). `value_format`: `estimated_annual`. `base_program`: `head_start`.

**Binding value basis**: Missouri uses PolicyEngine's live `head_start` value, following the existing TX/MA implementation pattern. The federal MFB `HeadStart` calculator returns PolicyEngine's per-child value; each state subclass supplies only its own fixed state code (see Implementation Note). PolicyEngine's `spending.yaml` carries `uprating: gov.hhs.uprating` (CPI-U-indexed: 304.7 for 2023 → 328.4 for 2026), while `enrollment.yaml` does not uprate — this is PE's own standard parameter behavior, not an MFB-specific choice, and it's the identical behavior TX and MA already ship in production.

**2026 per-child value = uprated FY2024 state spending ÷ FY2024 state enrollment**

| | Raw FY2024 benchmark (context, not binding) | 2026 per-child value (binding) |
|---|---:|---:|
| Missouri | $139,641,784 ÷ 9,225 = $15,137.32 | **$16,314** (unrounded $16,314.723) |
| Missouri, 2 children | — | **$32,629** — `trunc(16,314.723 + 16,314.723) = 32,629` (see Scenario 2's truncation-order note) |

The raw benchmark is PE's own 2023 parameter-file value before the 2026 uprating factor is applied — kept as the traceable base figure the binding numbers derive from (a run dated to any other year would apply that year's own uprating factor, not this raw figure).

### Methodology precedent

TX (MFB-677) and MA (MFB-270) both ship the identical architecture this spec proposes for Missouri — a shared federal `HeadStart` calculator that returns PolicyEngine's per-child `spending ÷ enrollment` value, with each state subclass supplying only its own state code via a `StateCodeDependency` subclass. `git log` confirms `tx/pe/member.py` and `ma/pe/member.py` are committed production code on `origin/main`. Neither ticket's Linear history contains a distinct "Product approves this valuation methodology" comment; Discovery Review, the PE Delta Report, and Staging/Prod QA served as the approval path each time, with the actual review gate being *parameter freshness and PE-value verification* (exactly what this spec's scenarios do), not a fresh methodology decision. WA (MFB-926) and CO instead use a flat externally-sourced dollar figure, but for a documented eligibility-semantics reason unrelated to the value-methodology question. Given this is established MFB precedent rather than a new Product decision, no separate Product approval comment is required for this ticket.

### Whole-dollar display convention

✅ Confirmed against the actual production route — traced the exact call chain the frontend hits:

1. `screener/urls.py:13` routes `path("eligibility/<id>", views.EligibilityTranslationView.as_view())` — this is the live results endpoint (the alternate `EligibilityView` class at `views.py:132`, which *does* run a DRF serializer, has no registered route and is dead code).
2. `EligibilityTranslationView.get()` (`screener/views.py:139-164`) calls `all_results(screen, is_admin)` → `eligibility_results(screen, batch)` → `Response(results)` (line 164) — a **raw dict**, never passed through `EligibilitySerializer`/`ResultsSerializer`'s `.data`. `ResultsSerializer` exists solely for the `@swagger_auto_schema` docs annotation and provides no runtime coercion.
3. Inside `eligibility_results()` (`screener/views.py:258-525`), the household-level total **is** truncated on the real path: `screener/views.py:522`, `clean_program["estimated_value"] = math.trunc(clean_program["estimated_value"])`, runs on every program immediately before `eligible_programs` is returned, and that value flows unmodified into `results["programs"]` — the actual JSON the frontend receives.
4. **Per-member values are not guaranteed truncated on this same path.** `member_data` (`screener/views.py:432-440`) sets `"value": member_eligibility.value` with no `math.trunc()` nearby, and for a PE-backed person-level program this traces to `PolicyEngineMembersCalculator.member_value()` (`programs/programs/policyengine/calculators/base.py:124-125`), which returns `self.sim.value(...)` raw and uncast — `MemberEligibility.value: int` in `calc.py` is a type *annotation*, not a runtime conversion. The per-child `members[].value` field in the actual production response for a two-child Missouri household will very likely be the raw float `16314.723`, not `16314`.

Net: **the whole-dollar guarantee is confirmed for the top-level `estimated_value` field only** (the "Eligible, $X" figure this spec's Acceptance Criteria are written against) — not for the per-member breakdown. This is **truncation, not rounding-to-nearest** — e.g. $16,314.723 → $16,314, not $16,315.

### Source provenance

PolicyEngine's `spending.yaml` metadata `reference` list explicitly cites "Head Start Program Facts Fiscal Year 2022," "...Fiscal Year 2023," and "...Fiscal Year 2024" — one reference per dated entry — which is the strongest evidence that the entry dated **2023-09-01** corresponds to **FY2024**.

✅ **Independently confirmed, quotation attached**: the live HeadStart.gov page was fetched and verified. A Wayback Machine snapshot (`http://web.archive.org/web/20260718194043/https://headstart.gov/program-data/article/head-start-program-facts-fiscal-year-2024`, captured 2026-07-18) is retained as backup evidence and is the source of the quotation below. The page states:

> "The tables in this section present the total annual federal funding and funded enrollment of Head Start programs in each state and territory, listed by program type. ... Funded enrollment refers to the capacity or number of children and pregnant women supported by federal Head Start funds."

Table header: **"Federal Funded Enrollment and Amounts by State, Excluding AIAN and MSHS Programs"** — columns `State | Head Start Preschool Funded Enrollment | EHS Funded Enrollment | Head Start Preschool Annual Operations Funded Amount | EHS Annual Operations Funded Amount`. The exact rows:

> Missouri 9,225 4,011 $139,641,784 $73,004,094

Reading the Preschool-labeled column: **Missouri: 9,225 / $139,641,784** — matching PE's parameter file exactly.

## Implementation Note: State Input Wiring

Three distinct fields are involved in getting the household's state to PolicyEngine's `head_start` calculation, and they are easy to conflate:

| Field | Where it lives | Value |
|---|---|---|
| `state_name` | Raw public PolicyEngine API request payload (used in this ticket's ad-hoc verification calls) | e.g. `"MO"` |
| `state_code_str` | PE's own resolved diagnostic variable, returned in the API response | e.g. `"MO"` |
| `state_code` | The outbound field name declared by MFB's `StateCode` dependency base class (`programs/programs/policyengine/calculators/dependencies/household.py:7`) | e.g. `"MO"` |

**`MoStateCodeDependency` and `MoCountyDependency` do not exist as committed code.** Checked directly against `origin/main`: they exist solely as uncommitted local scratch edits. There is nothing to "promote" for Missouri — Dev must **create** `MoStateCodeDependency`, following the shipped pattern already used by `TxStateCodeDependency`/`MaStateCodeDependency` (subclass `StateCode`, inherit `field = "state_code"`, set `state = "MO"` as a literal). `MoCountyDependency` is not required for Head Start unless a separate Missouri calculator needs county input — do not build it as part of this ticket unless another MO program calls for it.

## Light Value Scenarios

Both scenarios are eligible, so the expected dollar amount changes if Missouri's state-specific value drifts. Eligibility itself is not being tested — feed clearly-eligible households directly to isolate the value calculation.

- **PE state input**: the household's state resolves to `"MO"` via `MoStateCodeDependency` — a fixed literal constant, not derived from ZIP/county (that class must be created by Dev; see Implementation Note).
- **`birth_month`**: written below as the plain integer MFB's serializer actually expects (1–12), matching `ScreenSerializer`'s real schema (e.g. `validations/.../data/ma_head_start.json` uses `"birth_month": 6` for June) — no name-to-number conversion needed when running these through MFB's integrated path.

### Scenario 1: One Eligible Missouri Child
**Expected**: Eligible, $16,314 (unrounded PE output $16,314.723, truncated per MFB's whole-dollar convention)

**Steps**:
- **Location**: ZIP `65101`, County `Cole`
- **Household**: 2 people
- **Person 1**: Head of Household, `birth_year` 1990, `birth_month` 3, income $1,000/mo ($12,000/yr, clearly under the 100% FPL threshold for HH2), US citizen
- **Person 2**: Child, `birth_year` 2021, `birth_month` 8 (age 4), no income

**Why this matters**: Tests the Missouri per-child value parameter in isolation, using a clearly, unambiguously eligible household so no eligibility-boundary logic is being exercised.

---

### Scenario 2: Two Eligible Missouri Children
**Expected**: Eligible, $32,629 — `trunc(16,314.723 + 16,314.723) = trunc(32,629.446) = 32,629`.

**Truncation-order note**: `benefits-api`'s `Eligibility.value` property (`programs/programs/calc.py`) sums `household_value` plus every member's raw value *before* any truncation occurs, and only `screener/views.py:522`'s `math.trunc()` truncates — once, on that summed total, on the production `EligibilityTranslationView` path. So the binding expected **top-level total** is `trunc($16,314.723 + $16,314.723)` = **$32,629**, not `$16,314 + $16,314 = $32,628` (truncating each child first). This applies to the household-level `estimated_value` field only — the per-member `value` field (in `programs[].members[]`) is *not* independently coerced to a whole dollar on this endpoint and will most likely still carry the raw float (`16314.723`) per child. Dev/QA should verify this directly against the implemented Missouri calculator; this spec does not commit to a per-member whole-dollar figure, only to the household total.

**Steps**:
- **Location**: ZIP `65101`, County `Cole`
- **Household**: 3 people
- **Person 1**: Head of Household, `birth_year` 1990, `birth_month` 3, income $1,200/mo ($14,400/yr, clearly under the 100% FPL threshold for HH3), US citizen
- **Person 2**: Child, `birth_year` 2022, `birth_month` 1 (age 4), no income
- **Person 3**: Child, `birth_year` 2023, `birth_month` 6 (age 3), no income

**Why this matters**: Confirms the value is computed per eligible person (not a flat household amount) — since PE's `head_start` variable is defined per `Person`, two eligible children should produce exactly double the single-child value.

---

*(An ineligible or no-take-up `$0` scenario is optional as a general PE sanity check, but doesn't isolate Missouri's state-specific value and isn't required by this tier.)*

Full PE verification results — diagnostics, precision notes, and execution-environment caveats — are posted on MFB-1278 as a "PE Delta Report" comment, not duplicated in this spec.

## Note on Scope

Federal Head Start eligibility concerns identified during research (age-cutoff mechanics, family/income definitions, housing-cost adjustment, categorical pathways, the over-income allowances, and related PolicyEngine calculator gaps) are tracked separately as a cross-state PolicyEngine issue, not in this state-value spec.

## Research Sources

- [45 CFR § 1302.12 — Determining, Verifying, and Documenting Eligibility](https://www.law.cornell.edu/cfr/text/45/1302.12)
- [45 CFR § 1302.14 — Selection Process](https://www.law.cornell.edu/cfr/text/45/1302.14)
- [45 CFR § 1305.2 — Definitions (age range: three years to compulsory school age)](https://www.law.cornell.edu/cfr/text/45/1305.2)
- [Missouri Revised Statutes § 160.053 — Kindergarten Entry Age](https://revisor.mo.gov/main/OneSection.aspx?section=160.053)
- [Missouri Revised Statutes § 160.054 — St. Louis City Kindergarten Entry Date Discretion](https://revisor.mo.gov/main/OneSection.aspx?section=160.054)
- [Missouri Revised Statutes § 160.055 — Kansas City Kindergarten Entry Date Discretion](https://revisor.mo.gov/main/OneSection.aspx?section=160.055)
- [Missouri Revised Statutes § 167.031 — Compulsory Attendance (age 7)](https://revisor.mo.gov/main/OneSection.aspx?section=167.031)
- [Head Start Program Facts — Fiscal Year 2024 (Missouri Preschool benchmark: $139,641,784 / 9,225)](https://headstart.gov/program-data/article/head-start-program-facts-fiscal-year-2024) — live page fetched and verified; quoted directly in this spec (see Benefit Value) from the [Wayback Machine snapshot](http://web.archive.org/web/20260718194043/https://headstart.gov/program-data/article/head-start-program-facts-fiscal-year-2024) captured 2026-07-18, retained as backup evidence
- [PolicyEngine US — `head_start.py` variable, pinned commit `1d80e33cb87286888aa94d29202e434363d6bf2f`](https://github.com/PolicyEngine/policyengine-us/blob/1d80e33cb87286888aa94d29202e434363d6bf2f/policyengine_us/variables/gov/hhs/head_start/head_start.py) — the `spending ÷ enrollment` formula
- [PolicyEngine US — `spending.yaml` parameter, pinned commit `1d80e33cb87286888aa94d29202e434363d6bf2f`](https://github.com/PolicyEngine/policyengine-us/blob/1d80e33cb87286888aa94d29202e434363d6bf2f/policyengine_us/parameters/gov/hhs/head_start/spending.yaml) — Missouri's FY2024 spending figure and the `gov.hhs.uprating` instruction
- [PolicyEngine US — `enrollment.yaml` parameter, pinned commit `1d80e33cb87286888aa94d29202e434363d6bf2f`](https://github.com/PolicyEngine/policyengine-us/blob/1d80e33cb87286888aa94d29202e434363d6bf2f/policyengine_us/parameters/gov/hhs/head_start/enrollment.yaml) — Missouri's FY2024 enrollment figure (not uprated; a `master` link for any of these three would drift as the repo moves on)
- [How to Apply | HeadStart.gov](https://www.headstart.gov/how-apply) — describes a locally administered application process (local program provides forms, document requirements, and next steps); does not state a national or Missouri-wide application-time estimate. Per MFB convention this field must always be populated rather than left blank, so the config's `estimated_application_time` is set to **"30 minutes,"** the same estimate already shipped on the MA Head Start ticket, used here as the best available approximation in the absence of a Missouri-specific figure.

## Research Output

Local path: `/app/output/mo_head_start_20260723_173129`

PE verification results and diagnostics are posted on MFB-1278 as a "PE Delta Report" comment.

Note: the separate `[program].json` validation-scenarios file is deprecated. Test scenarios live only in this spec's Light Value Scenarios section.

## Acceptance Criteria

[ ] Scenario 1 (One Eligible Missouri Child): Eligible, $16,314
[ ] Scenario 2 (Two Eligible Missouri Children): Eligible, $32,629

## Dev Implementation Acceptance Criteria

Missouri's calculator and dispatch infrastructure don't exist yet — this is what Dev builds and QA verifies during implementation, not Discovery.

### 1. Build (from scratch — no existing committed code to promote)

- [ ] **`MoStateCodeDependency`** — new class in `programs/programs/policyengine/calculators/dependencies/household.py`:
  ```python
  class MoStateCodeDependency(StateCode):
      state = "MO"
  ```
  Follows the identical `TxStateCodeDependency`/`MaStateCodeDependency` pattern, both committed on `origin/main`.
- [ ] **`MoHeadStart(HeadStart)`** — new calculator class, following the identical `TxHeadStart`/`MaHeadStart` pattern. Include `MoStateCodeDependency` among its `pe_inputs`.
- [ ] **Registry wiring** — Missouri currently has no entry in the top-level `calculators` dispatch dict; add one, plus calculator exports and the `mo` `WhiteLabel`/program import path.
- [ ] **Do not build `MoCountyDependency`** for this ticket — only add it if a separate Missouri calculator needs county input.

### 2. Verify

Run **both scenarios** through MFB's integrated screener path (`/eligibility/<id>`, i.e. `EligibilityTranslationView`) — every scenario in this spec is a Missouri household, verifiable end-to-end through PE's raw API, MFB's `MoHeadStart` calculator in isolation, and the full integrated screener path.

For Scenarios 1 and 2, confirm:

- [ ] `MoHeadStart` sends the literal `"MO"` to PolicyEngine via `state_code` — a one-line hardcoded constant, not a ZIP/county-derived mapping.
- [ ] Birth-month and income serialization work correctly, with no skipped result.
- [ ] Two-child aggregation and truncation match the committed household-level `estimated_value`:
  - Scenario 1 → **$16,314**
  - Scenario 2 → **$32,629** (sum-then-truncate). If the integrated calculator instead produces **$32,628**, the per-member values are being truncated individually before aggregation — that's a real bug to fix, not an acceptable rounding variance.
- [ ] What the **per-member `members[].value` field** actually renders for each child — this spec does not commit to that field being a whole dollar (see Benefit Value). If Product/Design want the per-child breakdown to also read as a whole dollar in the UI, raise that as a new requirement with Dev/frontend, not an assumption already satisfied by existing code.

## Program Configuration
File: `/app/output/mo_head_start_20260723_173129/ticket_content/mo_head_start_initial_config.json`
