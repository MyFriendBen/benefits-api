# Implement Early Head Start (KS) Program

## Program Details

- **Program**: Early Head Start (birth to age 3, and pregnant women)
- **State**: KS
- **White Label**: ks
- **Scope**: Early Head Start only. Head Start (ages 3–5) is a separate, already-implemented program (MFB-1053 / PR #1622).
- **Implementation**: PolicyEngine (`early_head_start` variable), mirroring `tx_early_head_start` / `ma_early_head_start`. Eligibility and benefit value are computed by PolicyEngine; Kansas adds only the state code (the `KsHeadStart` pattern from PR #1622).
- **Engine + Tier**: PE Fed (value varies) — confirmed to match the shipped `ks_head_start` precedent.
- **Research Date**: 2026-06-12
- **Review Date**: 2026-06-19
- **Revision Date**: 2026-07-10

---

## Early Head Start Eligibility Criteria

1. **Child must be under age 3 (birth to 36 months) OR pregnant woman**
   - Screener fields:
     - `household_member.age`
     - `household_member.birth_year_month`
     - `household_member.pregnant`
   - Source: 45 CFR § 1302.12(c) — Early Head Start serves children from birth to age 3 and pregnant women

2. **Family income at or below 100% of Federal Poverty Level (FPL)**
   - Screener fields:
     - `income_stream.amount`
     - `income_stream.frequency`
     - `household_size`
   - Source: 45 CFR § 1302.12(a)(1)(i)
   - Note: 45 CFR § 1302.12(d)(1-2) permits grantees to discretionarily enroll additional children from families between 100–130% FPL (up to 35% of enrollment, subject to grantee slot availability). This over-income band is **not implemented** — KS Early Head Start is a thin wrapper around PolicyEngine's `early_head_start` variable (mirroring the shipped `KsHeadStart` precedent: "no KS-specific variance"), and PolicyEngine's `is_early_head_start_eligible` hard-checks `AGI ≤ 100% FPG` (`tax_unit_fpg`, unmultiplied) with no over-income band. Since MyFriendBen derives eligibility for PolicyEngine-wrapped programs as `value > 0`, any household between 100–130% FPL without categorical/foster/homeless status will compute to $0 and display as ineligible. Supporting the 100–130% band would require custom KS-specific logic that departs from this pattern.
   - ⚠️ **Flag re: shipped HS precedent**: the shipped `ks_head_start` spec (PR #1622) still states "at or below 135% of FPL" verbatim, carried over from the original combined draft — but PolicyEngine's `is_head_start_income_eligible` formula is identically `AGI ≤ tax_unit_fpg` (100%, no multiplier), confirmed by reading the live PolicyEngine source. None of the 6 shipped HS test scenarios actually probe the 100–130% boundary without categorical eligibility, so this inaccuracy went untested. Recommend flagging to a dev so the shipped HS spec/description gets the same correction as this EHS spec, rather than diverging between the two sibling programs.

3. **Child receives or family is eligible for TANF, SSI, or SNAP (categorical eligibility)**
   - Screener fields:
     - `current_benefits` (SNAP/TANF), checked via `screen.has_benefit("snap")` / `has_benefit("tanf")` — if self-reported, PolicyEngine's `Snap`/`Tanf` input dependencies override PE's own calculation and treat the household as receiving that benefit.
     - `household_member.income_streams` (type `sSI`) for SSI — PolicyEngine's `Ssi` dependency reads reported SSI income, not a benefit checkbox; if none is reported, PE calculates SSI eligibility itself.
   - ⚠️ **Flag re: deprecated field names**: `has_tanf`/`has_ssi`/`has_snap` (as used in the original combined draft and in the shipped `ks_head_start` spec/PR #1622) were removed as `Screen` model columns in migration `0157_drop_has_columns.py` (merged 2026-06-22) — **before** PR #1622 was even opened (2026-07-08), so the shipped HS spec already cites a field naming convention that predates its own PR. Recommend correcting the shipped HS spec to match.
   - Source: 45 CFR § 1302.12(a)(1)(ii)(B)

4. **Child is in foster care**
   - Screener fields:
     - `household_member.relationship`
   - Source: 45 CFR § 1302.12(c)(1)(iii)

5. **Child experiencing homelessness (McKinney-Vento definition)** ⚠️ *data gap*
   - Note: Children (and pregnant women) experiencing homelessness are categorically eligible regardless of income. The screener has a `housing_situation` field in the data model but it is not collected from users. The `needs_housing_help` field indicates desire for housing assistance, not current housing status. Cannot evaluate homelessness status. Same accepted gap as WA Head Start.
   - Source: 45 CFR § 1302.12(c)(1)(i)
   - Impact: High

6. **Migrant or Seasonal Early Head Start (agricultural employment)** ⚠️ *data gap*
   - Note: Migrant and Seasonal Head Start (MSHS) programs serve children of agricultural workers — including children from birth to age 3 and pregnant women — under a separate grantee structure. No screener field exists for agricultural employment. Cannot evaluate this pathway. Same accepted gap as WA Head Start.
   - Source: 45 CFR § 1302.12(f); 29 U.S.C. § 1802
   - Impact: Medium

---

## Benefit Value

Per-individual annual value is computed by PolicyEngine's `early_head_start` variable: Kansas ACF program spending ÷ enrollment, uprated to the calculation year. This resolves to **$13,323/eligible individual/year** for Kansas (2026). The value is read from PolicyEngine at calculation time (not a pinned constant), and scales by the number of eligible individuals (e.g., two eligible individuals = $26,646).

**PE delta verification** (per ticket requirement — mirrors the HS delta check from PR #1622): re-derived independently from PolicyEngine's raw KS parameters — `gov.hhs.head_start.early_head_start.spending.KS` ($22,139,720 in FY2023-09-01) ÷ `enrollment.KS` (1,791, held flat — the enrollment parameter has no uprating) — then uprated the spending figure to 2026 using `gov.hhs.uprating` (CPI factor 328.4/304.7 = 1.0778). Result: **$13,323.16/year**, rounding to the draft's **$13,323**. Delta: $0 (draft value confirmed against PE's live methodology, not just carried forward from the original combined spec).

---

## Implementation Coverage

- ✅ Evaluable criteria: 4 (age birth–36mo or pregnancy, income ≤ 100% FPL, categorical via SNAP/TANF/SSI, foster care)
- ⚠️ Data gaps: 2 (homelessness, migrant/seasonal)
- ⚠️ Known limitation: 1 (100–130% FPL over-income enrollment band — not a data gap, but unsupported by the current thin-wrapper architecture; see criterion 2)

Early Head Start eligibility can be substantially evaluated with current screener fields. The core pathways — age (birth to 36 months) or pregnancy, income at or below 100% FPL per 45 CFR § 1302.12(a)(1)(i), categorical eligibility via TANF/SSI/SNAP, and foster care — are all supported. The homelessness gap is the most significant: children and pregnant women experiencing homelessness are categorically eligible regardless of income, but the screener does not collect current housing status. Both the homelessness and migrant/seasonal gaps are accepted with precedent from the WA Head Start implementation. The 100–130% FPL over-income enrollment pathway under 45 CFR § 1302.12(d) is not evaluated: KS Early Head Start is implemented as a thin wrapper around PolicyEngine's `early_head_start` variable (per the `KsHeadStart` precedent), and PolicyEngine's income eligibility check is a hard ≤100% FPG cutoff with no over-income band — MyFriendBen's eligibility flag (`value > 0`) means any household in that band without categorical eligibility will show as ineligible. No Kansas-specific eligibility rules vary from the federal floor.

---

## Research Sources

- [Head Start Act, 42 U.S.C. § 9831 et seq.](https://uscode.house.gov/view.xhtml?path=/prelim@title42/chapter105&edition=prelim)
- [Head Start Program Performance Standards, 45 CFR § 1302.12](https://www.ecfr.gov/current/title-45/subtitle-B/chapter-XIII/subchapter-B/part-1302/subpart-B/section-1302.12)
- [HHS Poverty Guidelines (Annual Update per 42 U.S.C. § 9902)](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines)
- [Head Start Program Facts FY2024](https://headstart.gov/program-data/article/head-start-program-facts-fiscal-year-2024)

---

## Acceptance Criteria

- [ ] Scenario 1 (Low-income family, toddler under 3 — golden path EHS eligible): User should be **eligible** — $13,323/year
- [ ] Scenario 2 (Child age 6, income-eligible — too old for EHS, not pregnant): User should be **ineligible**
- [ ] Scenario 3 (Pregnant mother + toddler + older child — multiple eligible EHS pathways, value scales per eligible individual): User should be **eligible** — $26,646/year (2 eligible individuals × $13,323)
- [ ] Scenario 4 (Family above 100% FPL, receives SNAP — categorical eligibility override): User should be **eligible** — $13,323/year
- [ ] Scenario 5 (Family above 100% FPL, no categorical eligibility — income ineligible): User should be **ineligible**
- [ ] Scenario 6 (Foster child under 3 — categorical eligibility via foster care): User should be **eligible** — $13,323/year

---

## Test Scenarios

> Each eligible scenario asserts the expected **dollar value** ($13,323 per eligible individual), so a scenario breaks if the Kansas per-individual value drifts. Ineligible scenarios carry no value.

### Scenario 1: Low-Income Family with Toddler Under 3 — Clearly Eligible for Early Head Start
**What we're checking**: Typical low-income household with a child under 3 who clearly meets Early Head Start age and income requirements. **This is the primary value-isolation scenario** — if PE's KS spending/enrollment params drift, this expected amount breaks.
**Expected**: Eligible — $13,323/year (1 eligible child)

**Steps**:
- **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Birth month/year: `March 1996` (age 30), Relationship: `Head of Household`, Has income: `Yes`, Employment income: `$1,500` per month, Citizenship: `U.S. Citizen`
- **Person 2 (Child)**: Birth month/year: `April 2025` (age 1), Relationship: `Child`, Has income: `No`
- **Person 3 (Spouse)**: Birth month/year: `July 2000` (age 25), Relationship: `Spouse`, Has income: `No`
- **Current Benefits**: Select no current benefits

**Why this matters**: This is the most common Early Head Start eligibility pathway — a low-income family with a child under 3. At $1,500/month ($18,000/year) for a household of 3, income is ~66% of the 2026 FPL ($27,320/year), well below the 100% threshold. Tests the core income (45 CFR § 1302.12(a)(1)(i)) and age (45 CFR § 1302.12(c)) requirements.

---

### Scenario 2: Child Age 6 — Excluded Due to Being Too Old
**What we're checking**: A child beyond the Early Head Start age range (and not pregnant) is excluded even if the family meets income requirements
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Birth month/year: `March 1990` (age 36), Relationship: `Head of Household`, Has income: `Yes`, Employment income: `$1,200` per month, Citizenship: `U.S. Citizen`
- **Person 2 (Child)**: Birth month/year: `January 2020` (age 6), Relationship: `Child`, Has income: `No`
- **Person 3 (Spouse)**: Birth month/year: `September 1992` (age 33), Relationship: `Spouse`, Has income: `No`
- **Current Benefits**: Select no current benefits

**Why this matters**: Validates that Early Head Start strictly enforces the 36-month maximum age requirement per 45 CFR § 1302.12(c). A 6-year-old is excluded regardless of income, since they exceed the age ceiling and no household member is pregnant.

---

### Scenario 3: Pregnant Mother + Toddler + Older Child — Multiple Eligible EHS Pathways, Value Scales Per Eligible Individual
**What we're checking**: Household with multiple concurrent Early Head Start eligibility pathways — a toddler under 3 and a pregnant household member — while correctly excluding an older, non-pregnant-eligible child. This is also the **value-scaling** check for the "value varies" tier: the per-individual figure must apply once per eligible individual, so two eligible individuals should yield 2× the KS per-individual value.
**Expected**: Eligible — **$26,646/year** (2 eligible individuals × $13,323 = $26,646: 1-year-old + pregnant adult)

**Steps**:
- **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
- **Household**: Number of people: `4`
- **Person 1 (Head of Household)**: Birth month/year: `March 1996` (age 30), Relationship: `Head of Household`, Pregnant: `Yes`, Has income: `Yes`, Employment income: `$1,200` per month
- **Person 2 (Spouse)**: Birth month/year: `September 1994` (age 31), Relationship: `Spouse`, Has income: `Yes`, Employment income: `$800` per month
- **Person 3 (Child — EHS eligible)**: Birth month/year: `April 2025` (age 1), Relationship: `Child`, Has income: `No`
- **Person 4 (Child — too old)**: Birth month/year: `August 2018` (age 7), Relationship: `Child`, Has income: `No`
- **Current Benefits**: Select no current benefits

**Why this matters**: Tests that the screener correctly identifies multiple concurrent Early Head Start pathways — the toddler and the pregnant household member — while correctly excluding the 7-year-old, who is too old and not a pregnancy pathway. Combined household income of $2,000/month ($24,000/year) is ~73% of the 2026 FPL for a household of 4 ($33,000/year).

---

### Scenario 4: Family Above 100% FPL Receiving SNAP — Categorical Eligibility Override
**What we're checking**: A family whose income exceeds the 100% FPL income limit is still eligible because they receive SNAP, which confers categorical eligibility regardless of income
**Expected**: Eligible — $13,323/year

**Steps**:
- **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Birth month/year: `March 1990` (age 36), Relationship: `Head of Household`, Has income: `Yes`, Employment income: `$3,100` per month (~136% of 2026 FPL for HH of 3: $27,320/yr → 100% limit = $2,277/mo; $3,100/mo exceeds that limit), Citizenship: `U.S. Citizen`
- **Person 2 (Spouse)**: Birth month/year: `June 1992` (age 33), Relationship: `Spouse`, Has income: `No`
- **Person 3 (Child)**: Birth month/year: `April 2025` (age 1), Relationship: `Child`, Has income: `No`
- **Current Benefits**: Select `SNAP`

**Why this matters**: Validates that SNAP categorical eligibility (45 CFR § 1302.12(a)(1)(ii)(B)) independently qualifies a family regardless of income. At ~136% FPL, this family is well above the 100% FPL income limit PolicyEngine enforces (`is_early_head_start_eligible` requires `AGI ≤ 100% FPG` or categorical eligibility), so income is not a valid pathway on its own. Eligibility flows solely from SNAP receipt. Tests a distinct code branch from Scenario 1. The same logic applies to TANF and SSI.

**Known limitation** (same as shipped HS, PR #1622): PolicyEngine determines categorical eligibility from *calculated* SNAP/TANF/SSI, not reported receipt. A household that reports receiving SNAP but whose income is above PolicyEngine's calculated SNAP threshold is not caught by this path, so this scenario is not satisfied by the current PolicyEngine implementation unless the household's income also clears PE's own SNAP calculation.

---

### Scenario 5: Family Above 100% FPL, No Categorical Eligibility — Income Ineligible
**What we're checking**: A family with income above 100% FPL and no categorical benefits is not eligible
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Birth month/year: `March 1990` (age 36), Relationship: `Head of Household`, Has income: `Yes`, Employment income: `$3,200` per month (~141% of 2026 FPL for HH of 3: $27,320/yr → $2,277/mo × 1.41 ≈ $3,210/mo), Citizenship: `U.S. Citizen`
- **Person 2 (Spouse)**: Birth month/year: `June 1992` (age 33), Relationship: `Spouse`, Has income: `No`
- **Person 3 (Child)**: Birth month/year: `April 2025` (age 1), Relationship: `Child`, Has income: `No`
- **Current Benefits**: Select no current benefits

**Why this matters**: Validates the 100% FPL income limit with no categorical override. At ~141% FPL, this family is above the limit PolicyEngine enforces for the income pathway. The child is age-eligible and no benefits are selected, so the only remaining question is income. Confirms the calculator correctly returns ineligible ($0 value) for families above the limit when no alternative pathway applies.

---

### Scenario 6: Foster Child Under 3 — Categorical Eligibility via Foster Care
**What we're checking**: A child under 3 in foster care qualifies regardless of household income
**Expected**: Eligible — $13,323/year

**Steps**:
- **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Birth month/year: `March 1985` (age 41), Relationship: `Head of Household`, Has income: `Yes`, Employment income: `$4,000` per month, Citizenship: `U.S. Citizen`
- **Person 2 (Child)**: Birth month/year: `April 2025` (age 1), Relationship: `Foster Child`, Has income: `No`

**Why this matters**: Validates that foster care status (45 CFR § 1302.12(c)(1)(iii)) independently qualifies a child regardless of household income. At $4,000/month for a HH of 2 (~222% FPL, 2026 FPL for HH of 2: $21,640/year), the family is well above any income threshold, so eligibility must flow solely from the foster care relationship. Tests `household_member.relationship = "fosterChild"` as a distinct categorical pathway.
