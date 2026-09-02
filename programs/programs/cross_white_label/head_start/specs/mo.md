# Implement Head Start Preschool (MO) Program

## Program Details

- **Program**: Head Start (Preschool)
- **State**: MO
- **White Label**: mo
- **Research Date**: 2026-07-23
- **Calculator Type**: PE / Fed (value varies) — config + light spec.
- **Pinned PE reference**: `policyengine-us` commit `1d80e33cb87286888aa94d29202e434363d6bf2f` — all parameter values in this spec are as of this commit.

## Scope

Eligibility for Head Start Preschool is federal and is **not** being re-researched or tested here. This spec isolates and verifies Missouri's state-specific **benefit value** only.

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

## Light Value Scenarios

Both scenarios are eligible, so the expected dollar amount changes if Missouri's state-specific value drifts. Eligibility itself is not being tested — feed clearly-eligible households directly to isolate the value calculation.

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

**Steps**:
- **Location**: ZIP `65101`, County `Cole`
- **Household**: 3 people
- **Person 1**: Head of Household, `birth_year` 1990, `birth_month` 3, income $1,200/mo ($14,400/yr, clearly under the 100% FPL threshold for HH3), US citizen
- **Person 2**: Child, `birth_year` 2022, `birth_month` 1 (age 4), no income
- **Person 3**: Child, `birth_year` 2023, `birth_month` 6 (age 3), no income

**Why this matters**: Confirms the value is computed per eligible person (not a flat household amount) — since PolicyEngine's `head_start` variable is defined per person, two eligible children should produce exactly double the single-child value.

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

## Program Configuration
File: `mo_head_start_initial_config.json`
