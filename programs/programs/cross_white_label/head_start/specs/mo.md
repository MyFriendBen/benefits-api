# Implement Head Start Preschool (MO) Program

## Program Details

- **Program**: Head Start (Preschool)
- **State**: MO
- **White Label**: mo
- **Research Date**: 2026-07-23
- **Calculator Type**: PE / Fed (value varies) — config + light spec.
- **Pinned PE reference**: `policyengine-us` commit `1d80e33cb87286888aa94d29202e434363d6bf2f` — all parameter values in this spec are as of this commit.

## Scope

Eligibility for Head Start Preschool is federal and is not re-researched here. This spec covers two things: Missouri's state-specific **benefit value**, and the **actual-receipt categorical pathway** — the one federal behavior Missouri has already regressed on, verified end to end below.

## Categorical Eligibility — Actual Receipt, Not Simulated Eligibility

Head Start is categorically eligible for a household receiving **SNAP, TANF or SSI**, regardless of income. PolicyEngine keys that off **reported receipt** (`receives_snap`, `receives_tanf`, `receives_ssi`, each alongside its take-up flag), not off a benefit PolicyEngine simulated the household as eligible for. `HeadStart.pe_inputs` carries the full `receipt_contract` bundle, so MFB sends the distinction.

This is verified in both directions, measured at PolicyEngine **1.821.2**:

| PolicyEngine / MFB result | No SNAP reported | SNAP reported |
|---|---:|---:|
| `is_snap_eligible` | True | True |
| `snap_if_takes_up` | $2,765.17 | $2,765.17 |
| `snap` | **$0** | **$2,765.17** |
| `mo_head_start` | **$0** | **$16,314.723** |

Stripping the receipt/take-up inputs from the payload — the pre-#1685 request shape — makes the non-reporter eligible for $16,314.723 again, which is the false positive this pathway corrects.

**Scenario-design constraint.** The negative case only tests receipt-versus-simulation while the household sits in a narrow income band: **above** Head Start's income test (`spm_unit_fpg` = $27,320 for a household of three) so the ordinary pathway is closed, and **below** Missouri SNAP's simulated-eligibility ceiling so PolicyEngine still returns a would-be SNAP benefit to suppress. Raise the income and PolicyEngine stops simulating SNAP at all — the scenario then returns $0 under both the old and new contracts and passes for the wrong reason. Any future edit to Scenarios 3 and 4 has to keep them inside that band.

## Benefit Value

**Calculator Type is PE-backed** (`PE / Fed (value varies)`): PolicyEngine computes the benefit as state spending ÷ state enrollment (state-keyed, per eligible child). Spending is CPI-U-uprated (304.7 for 2023 → 328.4 for 2026); enrollment is not uprated — PolicyEngine's standard parameter behavior.

**2026 per-child value = uprated FY2024 state spending ÷ FY2024 state enrollment**

| | Raw FY2024 benchmark (context, not binding) | 2026 per-child value (binding) |
|---|---:|---:|
| Missouri | $139,641,784 ÷ 9,225 = $15,137.32 | **$16,314** (unrounded $16,314.723) |
| Missouri, 2 children | — | **$32,629** — sum-then-truncate: `trunc(16,314.723 + 16,314.723) = 32,629` |

The raw benchmark is PolicyEngine's own 2023 parameter-file value before the 2026 uprating factor is applied.

**Whole-dollar convention**: MFB sums the raw per-child values and then truncates the household total to a whole dollar. Therefore, two eligible children produce $32,629, not $32,628.

**Source**: HeadStart.gov's "Head Start Program Facts — Fiscal Year 2024" reports Missouri's Head Start Preschool Funded Enrollment as 9,225 and Annual Operations Funded Amount as $139,641,784 — matching PolicyEngine's parameter file exactly. See Research Sources below.

## Test Scenarios

Scenarios 1 and 2 are both eligible, so the expected dollar amount changes if Missouri's state-specific value drifts — they feed clearly-eligible households directly to isolate the value calculation. Scenarios 3 and 4 are the receipt-contract regression guards and are the only scenarios here that test eligibility.

### Scenario 1: One Eligible Missouri Child
**Expected**: Eligible, $16,314 (unrounded PE output $16,314.723, truncated per MFB's whole-dollar convention)

**Steps**:
- **Location**: ZIP `65101`, County `Cole County`
- **Household**: 2 people
- **Person 1**: Head of Household, `birth_year` 1990, `birth_month` 3, income $1,000/mo ($12,000/yr, clearly under the 100% FPL threshold for HH2), US citizen
- **Person 2**: Child, `birth_year` 2021, `birth_month` 8 (age 4), no income

**Why this matters**: Tests the Missouri per-child value parameter in isolation, using a clearly, unambiguously eligible household so no eligibility-boundary logic is being exercised.

---

### Scenario 2: Two Eligible Missouri Children
**Expected**: Eligible, $32,629 — `trunc(16,314.723 + 16,314.723) = trunc(32,629.446) = 32,629`.

**Steps**:
- **Location**: ZIP `65101`, County `Cole County`
- **Household**: 3 people
- **Person 1**: Head of Household, `birth_year` 1990, `birth_month` 3, income $1,200/mo ($14,400/yr, clearly under the 100% FPL threshold for HH3), US citizen
- **Person 2**: Child, `birth_year` 2022, `birth_month` 1 (age 4), no income
- **Person 3**: Child, `birth_year` 2023, `birth_month` 6 (age 3), no income

**Why this matters**: Confirms the value is computed per eligible person (not a flat household amount) — since PolicyEngine's `head_start` variable is defined per person, two eligible children should produce exactly double the single-child value.

---

### Scenario 3: SNAP Not Reported, Income Above the Test
**Expected**: **Not eligible**, $0

**Steps**:
- **Location**: ZIP `65101`, County `Cole County`
- **Household**: 3 people
- **Person 1**: Head of Household, age 30, employment income $2,600/mo ($31,200/yr)
- **Person 2**: Child, age 4 (Head Start band)
- **Person 3**: Child, age 1 (not Head Start eligible at any income; present so one household serves this spec and Early Head Start's)
- **Current Benefits**: none

**Why this matters**: PolicyEngine finds this household SNAP-eligible and would pay it $2,765/year, but it reports no SNAP. Under the actual-receipt contract that would-be benefit is suppressed, so nothing satisfies the categorical test and the income pathway is already closed at $31,200. Before #1685 the same household was told it qualified for $16,314 of Head Start on the strength of a SNAP benefit it was not receiving.

---

### Scenario 4: SNAP Reported, Same Household
**Expected**: Eligible, $16,314 (unrounded PE output $16,314.723)

**Steps**: identical to Scenario 3, plus **Current Benefits**: SNAP.

**Why this matters**: The positive half of the contract. Reported receipt satisfies the categorical test on its own, so the age-eligible child qualifies despite income above `spm_unit_fpg`. Asserted alongside Scenario 3 so a change that simply denies everyone cannot pass both.

---

## Research Sources

- [PolicyEngine US — `head_start.py` variable, pinned commit `1d80e33cb87286888aa94d29202e434363d6bf2f`](https://github.com/PolicyEngine/policyengine-us/blob/1d80e33cb87286888aa94d29202e434363d6bf2f/policyengine_us/variables/gov/hhs/head_start/head_start.py) — the `spending ÷ enrollment` formula
- [PolicyEngine US — `spending.yaml` parameter, pinned commit `1d80e33cb87286888aa94d29202e434363d6bf2f`](https://github.com/PolicyEngine/policyengine-us/blob/1d80e33cb87286888aa94d29202e434363d6bf2f/policyengine_us/parameters/gov/hhs/head_start/spending.yaml) — Missouri's FY2024 spending figure and uprating
- [PolicyEngine US — `enrollment.yaml` parameter, pinned commit `1d80e33cb87286888aa94d29202e434363d6bf2f`](https://github.com/PolicyEngine/policyengine-us/blob/1d80e33cb87286888aa94d29202e434363d6bf2f/policyengine_us/parameters/gov/hhs/head_start/enrollment.yaml) — Missouri's FY2024 enrollment figure
- [Head Start Program Facts — Fiscal Year 2024 (Missouri Preschool benchmark: $139,641,784 / 9,225)](https://headstart.gov/program-data/article/head-start-program-facts-fiscal-year-2024)
- [45 CFR § 1302.12 — Determining, Verifying, and Documenting Eligibility](https://www.law.cornell.edu/cfr/text/45/1302.12)
- [45 CFR § 1302.14 — Selection Process](https://www.law.cornell.edu/cfr/text/45/1302.14)
- [45 CFR § 1305.2 — Definitions (age range: three years to compulsory school age)](https://www.law.cornell.edu/cfr/text/45/1305.2)

## Acceptance Criteria

[ ] Scenario 1 (One Eligible Missouri Child): Eligible, $16,314
[ ] Scenario 2 (Two Eligible Missouri Children): Eligible, $32,629
[ ] Scenario 3 (SNAP Not Reported, Income Above the Test): Not eligible, $0
[ ] Scenario 4 (SNAP Reported, Same Household): Eligible, $16,314

## Program Configuration
File: `mo_head_start_initial_config.json`
