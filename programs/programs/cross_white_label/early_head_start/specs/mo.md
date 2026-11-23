# Implement Early Head Start (MO) Program

## Program Details

- **Program**: Early Head Start (EHS) — children under age 3, and pregnant women
- **State**: MO
- **White Label**: mo
- **Scope**: Early Head Start only.
- **Implementation**: PolicyEngine (`early_head_start` variable), mirroring `tx_early_head_start` (reference pattern — declares `PregnancyDependency`; `ma_early_head_start` omits it and should not be used as the template).
- **Engine + Tier**: PE Fed (value varies).
- **Research Date**: 2026-07-23
- **Review Date**: 2026-07-27

---

## Federal Eligibility Scope

Early Head Start eligibility is determined by PolicyEngine using the federal eligibility rules (45 CFR § 1302.12: a child under age 3 or a pregnant woman, with family income at/below the federal poverty guideline, categorical eligibility via TANF/SNAP/SSI, homelessness, or foster care). No Missouri-specific eligibility rule was identified — Missouri DESE's EHS page describes the same federal framework with no MO-specific carve-out.

This light spec does not reimplement or exhaustively test federal eligibility. Its scenarios isolate Missouri's state-specific benefit value, person-level calculation, and MFB's aggregation behavior, plus the one piece of eligibility that is MFB's own wiring rather than PE's rule — the actual-receipt categorical contract below. See Implementation Coverage.

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
| SSI | `HouseholdMember.income_streams` row of type `"sSI"` — no dedicated `receivesSsi` field. Also auto-written into `Screen.current_benefits` (`_write_current_benefits()` OR's in an SSI-implied benefit name whenever an `"sSI"` income stream is present, independent of whether the SSI tile was ticked) | The `Ssi` PE dependency (`programs/framework/pe_dependencies/member.py`) reads the income stream directly, not `current_benefits`. |

One federal pathway — homelessness — cannot currently be evaluated by MFB's PE integration; see Implementation Coverage below for the limitation and its scope.

### Categorical Eligibility Is Actual Receipt, Not Simulated Eligibility (verified)

The SNAP/TANF/SSI categorical pathway keys off **reported receipt** (`receives_snap`, `receives_tanf`, `receives_ssi`, each with its take-up flag), not off a benefit PolicyEngine simulated the household as eligible for. `EarlyHeadStart.pe_inputs` carries the full `receipt_contract` bundle, so MFB sends the distinction. Verified in both directions at PolicyEngine **1.821.2**:

| PolicyEngine / MFB result | No SNAP reported | SNAP reported |
|---|---:|---:|
| `is_snap_eligible` | True | True |
| `snap_if_takes_up` | $2,765.17 | $2,765.17 |
| `snap` | **$0** | **$2,765.17** |
| `mo_early_head_start` | **$0** | **$19,616.668** |

Stripping the receipt/take-up inputs from the payload — the pre-#1685 request shape — makes the non-reporter eligible for $19,616.668 again, which is the false positive this pathway corrects.

**Scenario-design constraint.** The negative case only tests receipt-versus-simulation while the household sits in a narrow income band: **above** the EHS income test (`spm_unit_fpg` = $27,320 for a household of three) so the ordinary pathway is closed, and **below** Missouri SNAP's simulated-eligibility ceiling so PolicyEngine still returns a would-be SNAP benefit to suppress. Raise the income and PolicyEngine stops simulating SNAP at all — the scenario then returns $0 under both the old and new contracts and passes for the wrong reason. Any future edit to Scenarios 4 and 5 has to keep them inside that band.

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

**Re-verified 2026-09-09 at PolicyEngine 1.821.2**: the per-participant figure is unchanged at **$19,616.668**. No benefit-value edit was required.

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

- ✅ Evaluable criteria: age (under 3) or pregnancy, income at/below FPL, categorical via TANF/SNAP/SSI (self-report), foster care (from `relationship == "fosterChild"` or the per-member `was_in_foster_care` tile).
- ⚠️ Data gap: homelessness. The screener doesn't collect current housing status, and PE's `is_homeless` variable defaults to `false` when not provided — the same as every shipped Head Start/EHS sibling. A household that qualifies *solely* through the homelessness pathway will not be found eligible by this integration; a household that qualifies through any other pathway is unaffected. This is a shared PE/MFB limitation across the whole Head Start/EHS program family, not a Missouri-specific gap.
- This is a **light spec**: eligibility is federal and trusted to PolicyEngine, so Scenarios 1-3 isolate Missouri's state-specific *value* and its aggregation rather than re-testing every federal eligibility branch. The one exception is the actual-receipt contract (Scenarios 4 and 5): that is MFB's own input wiring rather than PE's rule, it has regressed once, and no wiring test can catch it — so it is asserted behaviorally. Beyond that, no negative federal-eligibility scenario is included; a household with no child under 3 and no pregnancy isn't a Missouri state-value isolation test.

---

## Research Sources

- [45 CFR § 1302.12 — Determining, verifying, and documenting eligibility](https://www.law.cornell.edu/cfr/text/45/1302.12)
- [Head Start Program Facts – Fiscal Year 2024](https://headstart.gov/program-data/article/head-start-program-facts-fiscal-year-2024) — source of the $73,004,094 / 4,011 Missouri EHS figures
- [Missouri DESE — Early Head Start Program Overview](https://dese.mo.gov/childhood/quality-programs/preschool-programs/early-head-start)
- [How to Apply for Head Start & Early Head Start](https://www.headstart.gov/how-apply)

---

## Acceptance Criteria

- [x] Scenario 1 (Missouri, single participant — golden path): User should be **eligible** — $19,616/year
- [x] Scenario 2 (Missouri, two eligible participants — aggregation test): User should be **eligible** — $39,233/year
- [x] Scenario 3 (Missouri, pregnant-only applicant — `PregnancyDependency` integration check): User should be **eligible** — $19,616/year
- [x] Scenario 4 (SNAP not reported, income above the test): User should be **not eligible** — $0
- [x] Scenario 5 (SNAP reported, same household): User should be **eligible** — $19,616/year

---

## Test Scenarios

> Each eligible scenario asserts the expected **dollar value**, so a scenario breaks if Missouri's per-person value drifts. Scenario 1 pins Missouri's per-person value; Scenario 2 tests that value together with multi-person aggregation; Scenario 3 is a separate Implementation Integration Check, not a value-drift test.

### Scenario 1: Missouri Golden Path
**What we're checking**: A single-child household clearly eligible under the federal rule (income well below poverty), residing in Missouri.

**Why this matters**: Missouri's spending/enrollment parameters are the only thing this ticket adds — eligibility itself is entirely federal. If a future PE parameter update changes Missouri's EHS spending or enrollment figures, this is what catches it: a passing scenario with a wrong dollar amount would mean MO's value has silently drifted from its source, decoupled from any change in eligibility logic.

- **Location**: ZIP `65101`, County `Cole County`, State `MO`
- **Household**: 2 people
- **Person 1**: Head of household, birth_year 1996, birth_month 3 (age 30), employment income $1,000/month, citizen, no current benefits
- **Person 2**: Child, birth_year 2025, birth_month 3 (age 1), no income
- **Expected**: Eligible. Value = **$19,616** (raw $19,616.668, truncated at MFB serialization; integrated MFB-to-PE path — see `mo_ehs_pe_delta_report.md`).

---

### Scenario 2: Two EHS-Eligible Participants — Aggregation Test
**What we're checking**: A household with two age-eligible children (both under 3), income well below poverty. Tests both Missouri's per-person value and whether MFB's aggregation layer correctly sums multiple PE person-level amounts into one household total.
**Expected**: Eligible. Value = **$39,233** (MFB sums the raw per-person floats, $19,616.668 × 2 = $39,233.336, and truncates once at serialization; integrated MFB-to-PE path — see `mo_ehs_pe_delta_report.md`).

**Steps**:
- **Location**: ZIP `65101`, County `Cole County`
- **Household**: 4 people
- **Person 1**: Head of household, birth_year 1996, birth_month 3 (age 30), employment income $1,200/month, citizen, no current benefits
- **Person 2**: Spouse, birth_year 1998, birth_month 3 (age 28), no income
- **Person 3**: Child, birth_year 2025, birth_month 3 (age 1), no income
- **Person 4**: Child, birth_year 2025, birth_month 3 (age 1), no income

**Why this matters**: 4-person household (2 adults, 2 age-eligible children) with income far below the 100% FPL threshold for a household of 4, so the income gate is not in question — only the per-participant value and aggregation are being tested.

---

### Scenario 4: SNAP Not Reported, Income Above the Test
**What we're checking**: A household PolicyEngine would pay SNAP to, that reports no SNAP, with income above the EHS income test. The receipt contract has to suppress the would-be SNAP benefit so it confers no categorical eligibility.
**Expected**: **Not eligible**. Value = **$0**.

**Steps**:
- **Location**: ZIP `65101`, County `Cole County`
- **Household**: 3 people
- **Person 1**: Head of household, age 30, employment income $2,600/month ($31,200/year)
- **Person 2**: Child, age 4 (Head Start's participant, not EHS's; present so one household serves this spec and Head Start's)
- **Person 3**: Child, age 1 (the only possible EHS participant here)
- **Current Benefits**: none

**Why this matters**: Before #1685 this household was found eligible for $19,616 on the strength of a SNAP benefit it was not receiving. The income pathway is closed at $31,200, so categorical eligibility is the only way in and reported receipt is the only thing that should open it.

---

### Scenario 5: SNAP Reported, Same Household
**What we're checking**: The positive half of the contract, and — since exactly one participant qualifies — Missouri's per-participant value at income above the test.
**Expected**: Eligible. Value = **$19,616** (raw $19,616.668, truncated at MFB serialization).

**Steps**: identical to Scenario 4, plus **Current Benefits**: SNAP.

**Why this matters**: Asserted alongside Scenario 4 so a change that simply denies everyone cannot pass both. One participant, so the expected figure is the single-participant value rather than an aggregate.

---

## Implementation Integration Checks

*(MFB product/display behavior, not part of the Missouri state-value drift suite above — these exercise integration paths rather than isolating a state-specific value.)*

### Scenario 3 — Pregnant-Only Applicant
**What we're checking**: A pregnant applicant with no existing children. Validates that MFB correctly passes and displays the pregnant-person result and its availability caveat (not every EHS grantee is required to enroll pregnant applicants), and that MO's real calculator implements `PregnancyDependency` (TX's pattern) rather than omitting it (MA's pattern).
**Expected**: Eligible (federal financial/categorical eligibility). Value = **$19,616** (same single-person figure as Scenario 1; integrated MFB-to-PE path). Display copy should note this reflects federal eligibility only — local prenatal-service availability should be confirmed with the specific grantee.

**Steps**:
- **Location**: ZIP `65101`, County `Cole County`
- **Household**: 1 person
- **Person 1**: Head of household, birth_year 1996, birth_month 3 (age 30), pregnant, employment income $1,000/month (clearly below the 100% FPL threshold for a household of 1), no current benefits

**Why this matters**: `PregnancyDependency` is easy to omit without symptoms — MA's shipped calculator does, and no other scenario in this suite would catch it, since every other household already has an age-eligible child driving eligibility. Only a pregnant-only household with no child under 3 forces PE to evaluate eligibility purely through the pregnancy branch; this is the one scenario that would fail if MO's calculator followed MA's thinner pattern instead of TX's.

---

## Program Configuration
File: `mo_early_head_start_initial_config.json` (same directory)
