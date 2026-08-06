# Head Start (IL)

## Program Details

- **Program**: Head Start (ages 3–5)
- **State**: IL
- **White Label**: il
- **Scope**: Head Start only. Early Head Start (birth to age 3, and pregnant women) is a separate program tracked as its own ticket, matching the KS precedent (MFB-1053 Head Start / MFB-1250 Early Head Start) and the existing TX split (`tx_head_start` / `tx_early_head_start`).
- **Implementation**: PolicyEngine (`head_start` variable), mirroring `ks_head_start` / `tx_head_start` / `ma_head_start`. Eligibility and benefit value are computed by PolicyEngine; Illinois adds only the state code (the thin-wrapper pattern).
- **Engine + Tier**: PE, Fed (value varies)

---

## Eligibility

All eligibility is computed by PolicyEngine's `is_head_start_eligible`:

```
is_age_eligible & (is_income_eligible | is_categorically_eligible)
```

- **Age** — ages 3–5 (`gov.hhs.head_start.age_range`), per 45 CFR § 1302.12(c).
- **Income** — household income at or below 100% FPL.
- **Categorical** — SNAP, TANF, or SSI receipt, or foster care status, qualifies regardless of income (45 CFR § 1302.12(a)(1)(ii)(B), (c)(1)(iii)).

Illinois sets no eligibility parameters of its own — hence the `Fed (value varies)` tier rather than `Fed (elig varies)`.

---

## Benefit Value

Per-child annual value comes from PolicyEngine's `head_start` variable: Illinois ACF Head Start spending ÷ Illinois enrollment, with spending uprated to the calculation year.

For 2026 this resolves to **$17,227 per eligible child per year**, derived from PolicyEngine's IL parameters:

| Input | Value | Source |
|---|---|---|
| `gov.hhs.head_start.spending.IL` (2023-09-01) | $254,239,437 | `parameters/gov/hhs/head_start/spending.yaml` |
| `gov.hhs.head_start.enrollment.IL` (2023-09-01) | 15,906 | `parameters/gov/hhs/head_start/enrollment.yaml` |
| `gov.hhs.uprating` 2023 → 2026 | 304.7 → 328.4 | `parameters/gov/hhs/uprating.yaml` |

```
254,239,437 × (328.4 / 304.7) / 15,906 = $17,227
```

Note that `spending` carries `uprating: gov.hhs.uprating` while `enrollment` does not, so only the numerator is indexed. The value is read from PolicyEngine at calculation time (not a pinned constant) and scales by the number of eligible children — two eligible children yield $34,454.

This is an estimated annual value of Head Start services, not cash paid to the household.

---

## Research Sources

- [Head Start Act, 42 U.S.C. § 9831 et seq.](https://uscode.house.gov/view.xhtml?path=/prelim@title42/chapter105&edition=prelim)
- [Head Start Program Performance Standards, 45 CFR § 1302.12](https://www.ecfr.gov/current/title-45/subtitle-B/chapter-XIII/subchapter-B/part-1302/subpart-B/section-1302.12)
- PolicyEngine parameters `gov.hhs.head_start.spending.IL`, `gov.hhs.head_start.enrollment.IL`, `gov.hhs.uprating`

---

## Test Scenarios

> Each eligible scenario asserts the expected **dollar value** ($17,227 per eligible child), so a scenario breaks if PolicyEngine's Illinois spending/enrollment parameters drift. Ineligible scenarios carry no value.

All six verified locally against live PolicyEngine (model 1.784.3), 6/6 matching:

| # | Scenario | Expected | Result |
|---|----------|----------|--------|
| 1 | Low-income, one child age 4 | Eligible $17,227 | Eligible **$17,227** |
| 2 | Child age 7 — too old | Not eligible | Not eligible |
| 3 | Two children ages 3 + 5 | Eligible $34,454 | Eligible **$34,454** |
| 4 | Over-income + SNAP — categorical | Eligible $17,227 | Eligible **$17,227** |
| 5 | Over-income, no categorical | Not eligible | Not eligible |
| 6 | Foster child, over-income | Eligible $17,227 | Eligible **$17,227** |

### Scenario 1: Low-Income Family with One Eligible Child — Eligible, Value-Isolation
**What we're checking**: Typical low-income household with a child age 3–5 who clearly meets Head Start age and income requirements. **This is the primary value-isolation scenario** — if PE's IL spending/enrollment params drift, this expected amount breaks.
**Expected**: Eligible — $17,227/year (1 eligible child)

**Steps**:
- **Location**: ZIP code `60629`, county `Cook`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Birth month/year `March 1996` (age 30), Relationship `Head of Household`, Has income `Yes`, Employment income `$1,500`/month, Citizenship `U.S. Citizen`
- **Person 2 (Child)**: Birth month/year `March 2022` (age 4), Relationship `Child`, Has income `No`
- **Person 3 (Spouse)**: Birth month/year `July 2000` (age 25), Relationship `Spouse`, Has income `No`
- **Current Benefits**: none

**Why this matters**: The most common Head Start pathway. At $1,500/month ($18,000/year) for a household of 3, income is below 100% FPL.

---

### Scenario 2: Child Age 7 — Excluded, Too Old
**What we're checking**: A child beyond the Head Start age range is excluded even when the family meets income requirements.
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP code `60629`, county `Cook`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Birth month/year `March 1990` (age 36), Relationship `Head of Household`, Has income `Yes`, Employment income `$1,200`/month, Citizenship `U.S. Citizen`
- **Person 2 (Child)**: Birth month/year `January 2019` (age 7), Relationship `Child`, Has income `No`

**Why this matters**: Validates the age ceiling per 45 CFR § 1302.12(c). A 7-year-old is excluded regardless of income.

---

### Scenario 3: Two Eligible Children — Value Scales Per Eligible Child
**What we're checking**: A household with two children ages 3–5. This is the **value-scaling** check for the "value varies" tier: the per-child figure must apply once per eligible child.
**Expected**: Eligible — **$34,454/year** (2 × $17,227)

**Steps**:
- **Location**: ZIP code `60629`, county `Cook`
- **Household**: Number of people: `4`
- **Person 1 (Head of Household)**: Birth month/year `March 1996` (age 30), Relationship `Head of Household`, Has income `Yes`, Employment income `$1,400`/month
- **Person 2 (Spouse)**: Birth month/year `September 1994` (age 31), Relationship `Spouse`, Has income `No`
- **Person 3 (Child — eligible)**: Birth month/year `March 2023` (age 3), Relationship `Child`, Has income `No`
- **Person 4 (Child — eligible)**: Birth month/year `January 2021` (age 5), Relationship `Child`, Has income `No`
- **Current Benefits**: none

**Why this matters**: Confirms the value is per eligible child, not a flat per-household amount.

---

### Scenario 4: Above Income Limit, Receiving SNAP — Categorical Eligibility Override
**What we're checking**: A family over the income limit is still eligible because SNAP receipt confers categorical eligibility.
**Expected**: Eligible — $17,227/year

**Steps**:
- **Location**: ZIP code `60629`, county `Cook`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Birth month/year `March 1990` (age 36), Relationship `Head of Household`, Has income `Yes`, Employment income `$4,167`/month ($50,000/year), Citizenship `U.S. Citizen`
- **Person 2 (Spouse)**: Birth month/year `June 1992` (age 33), Relationship `Spouse`, Has income `No`
- **Person 3 (Child)**: Birth month/year `March 2022` (age 4), Relationship `Child`, Has income `No`
- **Current Benefits**: `SNAP`

**Why this matters**: Validates that SNAP categorical eligibility independently qualifies a family regardless of income — a distinct code branch from Scenario 1. The same logic applies to TANF and SSI. The $50,000 figure is a test input chosen to clear the income limit, not Head Start's official threshold.

Reaching this branch required fixing the `Snap` PE input dependency, which gated on `screen.has_benefit("snap")` — an exact match on a bare name no white label uses, so reported SNAP never reached PolicyEngine. It now reads `has_base_benefit("snap")`, matching the sibling `Tanf` dependency. KS shipped its Head Start with this scenario documented as a known limitation; it is now fixed for every state.

---

### Scenario 5: Above Income Limit, No Categorical Eligibility — Income Ineligible
**What we're checking**: A family over the income limit with no categorical benefits is not eligible.
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP code `60629`, county `Cook`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Birth month/year `March 1990` (age 36), Relationship `Head of Household`, Has income `Yes`, Employment income `$4,167`/month ($50,000/year), Citizenship `U.S. Citizen`
- **Person 2 (Spouse)**: Birth month/year `June 1992` (age 33), Relationship `Spouse`, Has income `No`
- **Person 3 (Child)**: Birth month/year `March 2022` (age 4), Relationship `Child`, Has income `No`
- **Current Benefits**: none

**Why this matters**: This is the control for Scenario 4 — same household, same income, no SNAP. Together the pair is a true A/B on categorical receipt: eligible at $17,227 with SNAP reported, ineligible without it, so eligibility there is demonstrably flowing from the categorical branch rather than from income.

---

### Scenario 6: Foster Child, Over-Income Family — Categorical Eligibility via Foster Care
**What we're checking**: A child age 3–5 in foster care qualifies regardless of household income.
**Expected**: Eligible — $17,227/year

**Steps**:
- **Location**: ZIP code `60629`, county `Cook`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Birth month/year `March 1985` (age 41), Relationship `Head of Household`, Has income `Yes`, Employment income `$5,000`/month, Citizenship `U.S. Citizen`
- **Person 2 (Child)**: Birth month/year `March 2022` (age 4), Relationship `Foster Child`, Has income `No`

**Why this matters**: Validates the foster care pathway (45 CFR § 1302.12(c)(1)(iii)). At $5,000/month for a household of 2 the family is well above any income threshold, so eligibility must flow solely from foster care status.

---

## Notes

`show_in_has_benefits_step` is `false`, matching the KS and MO precedent, so "Head Start" is not offered as a selectable current benefit on the has-benefits step. The research draft carried a seventh scenario checking that an existing Head Start recipient isn't redundantly recommended the program; that scenario is dropped because the flag it depended on is off — with the option absent from the step, there is no input by which a household could report current Head Start receipt.

Head Start receipt does **not** confer categorical eligibility on any other program we model. The categorical arrow points inward only: SNAP, TANF, SSI, and foster care qualify a child *for* Head Start, but Head Start enrollment does not qualify a household for anything else. PolicyEngine models enrollment as a separate input variable (`is_enrolled_in_head_start`) that we do not send, and it has no formula linking it to the `head_start` eligibility this program computes.

---

## Program Configuration

File: `programs/management/commands/import_program_config_data/data/il_head_start_initial_config.json`
