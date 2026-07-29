# Implement Early Head Start (MO) Program

## Program Details

- **Program**: Early Head Start (EHS) — children under age 3, and pregnant women
- **State**: MO
- **White Label**: mo
- **Scope**: Early Head Start only. Head Start Preschool (ages 3–5) is a separate program tracked under a separate ticket (MFB-1278), with its own funding/enrollment parameters and its own spec (`mo_head_start_spec.md`).
- **Implementation**: PolicyEngine (`early_head_start` variable), mirroring `tx_early_head_start` (reference pattern — declares `PregnancyDependency`; `ma_early_head_start` omits it and should not be used as the template).
- **Engine + Tier**: PE Fed (value varies) — see Tier Classification Note below.
- **Research Date**: 2026-07-23
- **Review Date**: 2026-07-27

*Full review history (fifty-six passes) lives in `mo_ehs_review_changelog.md`. This spec contains only current, binding content.*

---

## Tier Classification Note

**Classification: PE / Fed (value varies).**

PE's `is_early_head_start_eligible` formula (`policyengine_us/variables/gov/hhs/head_start/is_early_head_start_eligible.py`) has no `StateCode.{STATE}` branch:

```python
is_age_eligible = (age < p.early_head_start.age_limit) | person("is_pregnant", period)
is_program_eligible = person("is_head_start_categorically_eligible", period)
is_income_eligible = person("is_head_start_income_eligible", period)
return is_age_eligible & (is_income_eligible | is_program_eligible)
```

The benefit-value formula is directly state-keyed. The eligibility formula has no *direct* state branch, but its categorical fallback (`is_head_start_categorically_eligible`: `add(person.spm_unit, period, ["tanf", "ssi", "snap"]) > 0`) can indirectly invoke state-specific SNAP/TANF calculations whenever a household doesn't self-report those benefits.

**Empirical test** (against the locally installed `policyengine-us` package): a household of one adult (age 30, $40,000/year employment income — 185% of the 2026 federal poverty guideline for a household of 2, `tax_unit_fpg = $21,640`) and one child under 3, with SNAP/TANF/SSI all left unreported (`None`, the architecture's designed fallback path):

| State | Calculated `tanf` | Calculated `snap` | Categorically eligible | EHS eligible | EHS value |
|---|---|---|---|---|---|
| MO | $0 | $0 | No | **No** | $0 |
| TX | $0 | $0 | No | **No** | $0 |
| CA | $0 | $0 | No | **No** | $0 |
| MA | $0 | **$288.61** | **Yes** | **Yes** | **$22,947.87** |

An otherwise-identical household is ineligible in Missouri and eligible in Massachusetts, purely because PE's calculated (not self-reported) SNAP benefit is nonzero in MA at this income level, which alone satisfies `is_head_start_categorically_eligible`'s `> 0` test. This confirms EHS eligibility can vary by state through this fallback path — which activates whenever MFB's SNAP/TANF dependencies both resolve to `None` for a household. (MFB's `Snap` dependency sends a flat `1` when self-reported, `None` otherwise; `Tanf` sends the actual reported cash amount when self-reported via `has_base_benefit`, `None` otherwise — the two self-report checks aren't identical, but both converge to `None` in the untested case this finding depends on, so the fallback applies equally to any Head Start/EHS program built on these dependencies, not just Missouri's.)

**Decision:** keep tier as `Fed (value varies)`. None of this ticket's committed scenarios exercise the fallback path — all have income well below the FPL, where the income test alone decides eligibility regardless of state. Reclassifying this one ticket would also pull it into `Fed (elig + value varies)`'s full-spec deliverable requirement while every sibling program sharing the identical fallback architecture remains under the lighter tier, an inconsistency this ticket alone shouldn't create. The empirical divergence above is real and is recorded as a non-blocking systemic finding below, not a per-ticket reclassification.

**Non-blocking systemic follow-up:** every sibling PE-backed Head Start/EHS program (TX/MA Early Head Start, MO/IL Head Start Preschool) shares this exact fallback architecture. Whether the tier convention should account for it — across the whole family, not one ticket — is flagged for the tier-checklist owner, not resolved here.

Missouri has no separate state eligibility rule identified beyond this: 45 CFR § 1302.12 defines EHS eligibility with no state branch, and Missouri DESE's EHS page describes the same federal framework with no MO-specific carve-out.

---

## Federal Eligibility Scope

Early Head Start eligibility is determined by PolicyEngine using the federal eligibility rules (45 CFR § 1302.12: a child under age 3 or a pregnant woman, with family income at/below the federal poverty guideline, categorical eligibility via TANF/SNAP/SSI, homelessness, or foster care). No Missouri-specific eligibility rule was identified — Missouri DESE's EHS page describes the same federal framework with no MO-specific carve-out.

This light spec does not reimplement or exhaustively test federal eligibility. Its scenarios isolate Missouri's state-specific benefit value, person-level calculation, and MFB's aggregation behavior — see Implementation Coverage below.

**Screener-to-PE field mapping** (verified against `screener/models.py` and `screener/serializers.py` on `benefits-api`'s `origin/main`):

| Federal criterion | Current screener field(s) | Notes |
|---|---|---|
| Age under 3 | `HouseholdMember.age` (stored `PositiveIntegerField`, directly submittable) **or** `birth_year`/`birth_month` (serializer-only fields, converted to `birth_year_month` and used to derive `age` if not separately submitted) | Both paths are legitimate inputs — `age` is not merely derived. `calc_age()` prefers `birth_year_month` when present, falling back to the stored `age` field otherwise. |
| Pregnancy | `HouseholdMember.pregnant` (boolean) | |
| Household composition | `HouseholdMember.relationship` | Used to derive tax unit/family/SPM unit structure, not read directly by the EHS calculator. |
| Household size | `Screen.household_size` | |
| Income | `HouseholdMember.income_streams` (`IncomeStreamSerializer`, one row per income type) | Feeds `calc_gross_income`/`calc_expenses`; there is no single flat "income" field. |
| SNAP self-report | `Screen.current_benefits` (via `has_benefit("snap")`), written by `_write_current_benefits()` | Not a field literally named `has_benefits`/`benefits`. `has_benefit` is an exact-name match. |
| TANF self-report | `Screen.current_benefits` (via `has_base_benefit("tanf")`, which matches every white-label TANF variant — `ks_tanf`, `co_tanf`, `ma_tafdc`, etc.), written by `_write_current_benefits()` | `has_base_benefit` (prefix-aware) is a different check than SNAP's `has_benefit` (exact match) — the two self-report checks aren't interchangeable. |
| SSI | `HouseholdMember.income_streams` row of type `"sSI"` — no dedicated `receivesSsi` field. Also auto-written into `Screen.current_benefits` (`_write_current_benefits()` OR's in an SSI-implied benefit name whenever an `"sSI"` income stream is present, independent of whether the SSI tile was ticked) | The `Ssi` PE dependency (`programs/programs/policyengine/calculators/dependencies/member.py`) reads the income stream directly, not `current_benefits`. |

One federal pathway — homelessness — cannot currently be evaluated by MFB's PE integration; see Implementation Coverage below for the limitation and its scope.

---

## Benefit Value

**Methodology**: PolicyEngine computes EHS value per eligible person as Missouri EHS spending ÷ Missouri EHS enrollment, using state-keyed parameters, uprated to the calculation year. MFB does not reimplement this calculation — it reads PE's output at calculation time.

**Calculation chain** (confirmed against PE's current parameter files and live source):
1. Missouri spending: **$73,004,094**, effective 2023-09-01 (Head Start Program Facts, Fiscal Year 2024, EHS-specific row — excludes Head Start Preschool, AIAN, and MSHS):

   > Missouri — EHS funded enrollment: 4,011; EHS annual operations funded amount: $73,004,094.

2. Spending is uprated using `gov.hhs.uprating`, from a 2023 HHS index of 304.7 to a 2026 index of 328.4.
3. Missouri enrollment: **4,011** (not uprated).
4. Uprated spending ÷ enrollment → the per-eligible-person value: $73,004,094 × (328.4 ÷ 304.7) ÷ 4,011 = **$19,616.668/year** (raw PE float, live-confirmed).
5. The result applies to each PE-eligible person who takes up EHS (take-up defaults true).
6. PE does not round in the `early_head_start` variable — it returns the raw, uprated, unrounded float. MFB sums PE's raw person-level outputs and truncates the aggregated value once at serialization ($19,616.668 + $19,616.668 = $39,233.336 → truncate once to $39,233, for a two-participant household), confirmed through source inspection (`rest_framework/fields.py`'s `int()` truncation, `programs/calc.py`'s float summation with no intermediate rounding) and the live integrated run.

**Person-level values (live-confirmed, 2026-07-27)**:
- Missouri, single participant: **$19,616** (raw $19,616.668, truncated)
- Missouri, two participants: **$39,233** (raw $19,616.668 × 2 = $39,233.336, summed then truncated once)

**A state-published figure doesn't exist for this program** the way it might for a state-administered benefit — EHS funding is federally awarded, and OHS's Program Facts table is the authoritative source for state-by-state figures. This is the correct primary source for that reason, not a substitute for a state agency publication. The official OHS FY2024 table's Missouri figures ($73,004,094 / 4,011) match PE's parameter files exactly — no PE-versus-source discrepancy in the underlying inputs.

**Caveats**:
- **Reproducibility anchor**: the live public API doesn't expose its serving package version. Results were independently reproduced with pinned local `policyengine-us` 1.755.5, which serves as the reproducible version anchor. Identifying the live API's internal version is a non-blocking production-parity follow-up — see `mo_ehs_pe_delta_report.md`.
- **Zero-delta ≠ permanently correct**: a PE run matching this spec's expected values confirms PE's *current* parameters agree with this spec — it doesn't independently prove PE's parameters remain aligned with OHS's federal award data going forward, since OHS updates its Program Facts tables periodically. Separately, PE's `early_head_start` variable's own `reference` metadata still points to an older (FY2022) fact sheet, while its spending parameter's metadata carries the FY2024 figures this spec uses — future reviews should cite the parameter metadata and the current OHS table, not the variable's `reference` field.
- **Person-count**: PE evaluates EHS eligibility and value at the **person** level — each child under 3, and independently a pregnant woman, satisfies "under 3 or pregnant" + income/categorical. A household with a pregnant mother and two children under 3 would have PE compute **three** person-level eligible participants.

---

## Implementation Coverage

- ✅ Evaluable criteria: age (under 3) or pregnancy, income at/below FPL, categorical via TANF/SNAP/SSI (self-report), foster care.
- ⚠️ Data gap: homelessness. The screener doesn't collect current housing status, and PE's `is_homeless` variable defaults to `false` when not provided — the same as every shipped Head Start/EHS sibling. A household that qualifies *solely* through the homelessness pathway will not be found eligible by this integration; a household that qualifies through any other pathway is unaffected. This is a shared PE/MFB limitation across the whole Head Start/EHS program family, not a Missouri-specific gap or a decision this ticket makes — see `mo_ehs_review_changelog.md` for the systemic discussion.
- This is a **light spec**: eligibility is federal and trusted to PolicyEngine, so the scenario suite below isolates Missouri's state-specific *value* and its aggregation rather than re-testing every federal eligibility branch. No negative federal-eligibility scenario is included — a household with no child under 3 and no pregnancy isn't a Missouri state-value isolation test, and federal eligibility branch coverage is PE's responsibility, not this spec's.

---

## Research Sources

- [45 CFR § 1302.12 — Determining, verifying, and documenting eligibility](https://www.law.cornell.edu/cfr/text/45/1302.12)
- [Head Start Program Facts – Fiscal Year 2024](https://headstart.gov/program-data/article/head-start-program-facts-fiscal-year-2024) — source of the $73,004,094 / 4,011 Missouri EHS figures
- [Missouri DESE — Early Head Start Program Overview](https://dese.mo.gov/childhood/quality-programs/preschool-programs/early-head-start)
- [How to Apply for Head Start & Early Head Start](https://www.headstart.gov/how-apply)
- Full prior citation set (ACF-IM-HS-22-03, ACF-OHS-PI-24-04, 45 CFR § 1305.2, 42 U.S.C. § 9835(d)(1), 45 CFR § 1302.11(a), etc.) preserved in `mo_ehs_review_changelog.md` — not reproduced here per the light-spec conversion.

---

## Acceptance Criteria

- [x] Scenario 1 (Missouri, single participant — golden path): User should be **eligible** — $19,616/year
- [x] Scenario 2 (Missouri, two eligible participants — aggregation test): User should be **eligible** — $39,233/year
- [x] Scenario 3 (Missouri, pregnant-only applicant — `PregnancyDependency` integration check): User should be **eligible** — $19,616/year

---

## Test Scenarios

> Each eligible scenario asserts the expected **dollar value**, so a scenario breaks if Missouri's per-person value drifts. Scenario 1 pins Missouri's per-person value; Scenario 2 tests that value together with multi-person aggregation; Scenario 3 is a separate Implementation Integration Check, not a value-drift test.

### Scenario 1: Missouri Golden Path
**What we're checking**: A single-child household clearly eligible under the federal rule (income well below poverty), residing in Missouri.

**Why this matters**: Missouri's spending/enrollment parameters are the only thing this ticket adds — eligibility itself is entirely federal (see Tier Classification Note). If a future PE parameter update changes Missouri's EHS spending or enrollment figures, this is what catches it: a passing scenario with a wrong dollar amount would mean MO's value has silently drifted from its source, decoupled from any change in eligibility logic.

- **Location**: ZIP `65101`, County `Cole`, State `MO`
- **Household**: 2 people
- **Person 1**: Head of household, birth_year 1996, birth_month 3 (age 30), employment income $1,000/month, citizen, no current benefits
- **Person 2**: Child, birth_year 2025, birth_month 3 (age 1), no income
- **Expected**: Eligible. Value = **$19,616** (raw $19,616.668, truncated at MFB serialization; integrated MFB-to-PE path — see `mo_ehs_pe_delta_report.md`).

---

### Scenario 2: Two EHS-Eligible Participants — Aggregation Test
**What we're checking**: A household with two age-eligible children (both under 3), income well below poverty. Tests both Missouri's per-person value and whether MFB's aggregation layer correctly sums multiple PE person-level amounts into one household total.
**Expected**: Eligible. Value = **$39,233** (MFB sums the raw per-person floats, $19,616.668 × 2 = $39,233.336, and truncates once at serialization; integrated MFB-to-PE path — see `mo_ehs_pe_delta_report.md`).

**Steps**:
- **Location**: ZIP `65101`, County `Cole`
- **Household**: 4 people
- **Person 1**: Head of household, birth_year 1996, birth_month 3 (age 30), employment income $1,200/month, citizen, no current benefits
- **Person 2**: Spouse, birth_year 1998, birth_month 3 (age 28), no income
- **Person 3**: Child, birth_year 2025, birth_month 3 (age 1), no income
- **Person 4**: Child, birth_year 2025, birth_month 3 (age 1), no income

**Why this matters**: 4-person household (2 adults, 2 age-eligible children) with income far below the 100% FPL threshold for a household of 4, so the income gate is not in question — only the per-participant value and aggregation are being tested.

---

## Implementation Integration Checks

*(MFB product/display behavior, not part of the Missouri state-value drift suite above — these exercise integration paths rather than isolating a state-specific value.)*

### Scenario 3 — Pregnant-Only Applicant
**What we're checking**: A pregnant applicant with no existing children. Validates that MFB correctly passes and displays the pregnant-person result and its availability caveat (not every EHS grantee is required to enroll pregnant applicants), and that MO's real calculator implements `PregnancyDependency` (TX's pattern) rather than omitting it (MA's pattern).
**Expected**: Eligible (federal financial/categorical eligibility). Value = **$19,616** (same single-person figure as Scenario 1; integrated MFB-to-PE path). Display copy should note this reflects federal eligibility only — local prenatal-service availability should be confirmed with the specific grantee.

**Steps**:
- **Location**: ZIP `65101`, County `Cole`
- **Household**: 1 person
- **Person 1**: Head of household, birth_year 1996, birth_month 3 (age 30), pregnant, employment income $1,000/month (clearly below the 100% FPL threshold for a household of 1), no current benefits

**Why this matters**: `PregnancyDependency` is easy to omit without symptoms — MA's shipped calculator does, and no other scenario in this suite would catch it, since every other household already has an age-eligible child driving eligibility. Only a pregnant-only household with no child under 3 forces PE to evaluate eligibility purely through the pregnancy branch; this is the one scenario that would fail if MO's calculator followed MA's thinner pattern instead of TX's.

---

## Implementation Requirements for Coding Agent

Resolved design requirements, not Discovery blockers — dependencies are already known; what remains is implementation, verified during code review and the corresponding test scenarios.

**Calculator**
- Implement a Missouri-specific EHS calculator using TX's pattern as the reference (not MA's — see below).
- Hardcode `state = "MO"` as a class attribute. MFB's state-specific calculators each hardcode their own state; there's no shared code path where state varies per request.
- Include `PregnancyDependency` so pregnant-only applicants serialize correctly and Scenario 3 passes. MA's calculator omits this dependency — don't follow that pattern.
- Aggregate all eligible persons' raw `early_head_start` values before the final whole-dollar serialization step (sum first, truncate once — see Benefit Value).
- Use the screener mappings for age (`age` or `birth_year`/`birth_month`), `pregnant`, `relationship`, household size, income streams, current benefits, and SSI receipt — see Federal Eligibility Scope for the exact field paths.

**Config** (`mo_early_head_start_initial_config.json`)
- `id_proof`: removed. 45 CFR § 1302.12(h) requires programs to verify age under their own procedures but prohibits requiring age-confirming documents when that would create an enrollment barrier — it does not establish a parent/guardian identity-document requirement, and neither it nor Missouri DESE's EHS page confirms one for Missouri specifically. TX's shipped config sharing this key is precedent only that the *entity name* is shared, not that Missouri's application requires it. Re-add only with a direct MO grantee/application source.
- `program_category`: `mo_child_care`, matching the `{state}_child_care` convention (TX/MA/IL/WA). Confirmed absent from both `benefits-api`'s import data and the External Names reference spreadsheet — this is a new category. Add it to the reference spreadsheet; this is not a reuse of an existing row.

---

## Program Configuration
File: `mo_early_head_start_initial_config.json` (same directory)
