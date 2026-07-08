# Implement Head Start (KS) Program

## Program Details

- **Program**: Head Start (ages 3–5)
- **State**: KS
- **White Label**: ks
- **Research Date**: 2026-06-12
- **Review Date**: 2026-06-19
- **Scope note**: This ticket (MFB-1053) covers **Head Start only** (ages 3–5). Early Head Start (birth–3 and pregnant women) is a separate program tracked under its own ticket and is out of scope here. EHS content from the original combined research has been removed from this spec.
- **Implementation**: PolicyEngine (`head_start` variable), mirroring `tx_head_start` / `ma_head_start`. Eligibility and benefit value are computed by PolicyEngine; Kansas adds only the state code. Benefit value is PE's per-child `head_start` output (derived from ACF spending/enrollment parameters, currently FY2024), not a pinned constant.

---

## Head Start Eligibility Criteria

1. **Child must be between ages 3 and 5 (not yet in kindergarten)**
   - Screener fields:
     - `household_member.age`
     - `household_member.birth_year_month`
   - Source: 45 CFR § 1302.12(c)(1) — Head Start Program Performance Standards

2. **Family income at or below 135% of Federal Poverty Level (FPL)**
   - Primary eligibility at or below 100% FPL per 45 CFR § 1302.12(a)(1)(i)
   - Over-income eligibility between 100–130% FPL per 45 CFR § 1302.12(d)(1-2) (up to 35% of enrollment; discretionary, grantee-specific slot availability)
   - The screener uses 135% as a conservative ceiling to surface both groups; the program description notes that families between 100–130% FPL depend on grantee slot availability
   - Screener fields:
     - `income_stream.amount`
     - `income_stream.frequency`
     - `household_size`
   - Source: 45 CFR § 1302.12(a)(1)(i) and § 1302.12(d)(1-2)

3. **Child receives or family is eligible for TANF, SSI, or SNAP (categorical eligibility)**
   - Screener fields:
     - `has_tanf`
     - `has_ssi`
     - `has_snap`
   - Note: PolicyEngine's `is_head_start_categorically_eligible` keys off *calculated* TANF/SSI/SNAP eligibility (summed at the SPM unit), consistent with the tx/ma PE approach.
   - Source: 45 CFR § 1302.12(a)(1)(ii)(B)

4. **Child is in foster care**
   - Screener fields:
     - `household_member.relationship`
   - Source: 45 CFR § 1302.12(c)(1)(iii)

5. **Child experiencing homelessness (McKinney-Vento definition)** ⚠️ *data gap*
   - Note: Children experiencing homelessness are categorically eligible regardless of income. The screener has a `housing_situation` field in the data model but it is not collected from users. Cannot evaluate homelessness status. Same accepted gap as WA/TX Head Start.
   - Source: 45 CFR § 1302.12(c)(1)(i)
   - Impact: High

6. **Migrant or Seasonal Head Start (agricultural employment)** ⚠️ *data gap*
   - Note: Migrant and Seasonal Head Start programs serve children of agricultural workers under a separate grantee structure. No screener field exists for agricultural employment. Cannot evaluate this pathway. Same accepted gap as WA/TX Head Start.
   - Source: 45 CFR § 1302.12(f); 29 U.S.C. § 1802
   - Impact: Medium

7. **Fully discretionary enrollment (no income criterion, up to 10% of enrollment)** ⚠️ *data gap*
   - Note: Under 45 CFR § 1302.12(c)(2), a program may enroll children who do not meet any (c)(1) criterion at its sole discretion, subject to a 10% cap. No income threshold — cannot be evaluated without grantee-specific capacity data.
   - Source: 45 CFR § 1302.12(c)(2)
   - Impact: Low

---

## Benefit Value

- Per-child annual value is computed by PolicyEngine's `head_start` variable from ACF program spending ÷ enrollment (currently FY2024: $66,709,446 ÷ 4,590 ≈ **$14,534/child/year** for Kansas). Because the value is read from PolicyEngine at calculation time, it tracks the latest federal-year figures PE carries rather than a pinned constant. Value scales with the number of eligible children in the household.
- *Note for QA:* the discovery config/spec draft carried $15,664/child, which does not match the FY2024 (or FY2023 $14,020) ACF-derived figure and appears to be a stale number. Using the PE approach avoids hardcoding it.

---

## Implementation Coverage

- ✅ Evaluable criteria: 4 (age, income ≤ 135% FPL, categorical via SNAP/TANF/SSI, foster care)
- ⚠️ Data gaps: 3 (homelessness, migrant/seasonal, fully discretionary enrollment)

Head Start eligibility can be substantially evaluated with current screener fields. The core pathways — age, income (covering both the primary 100% FPL threshold and the 100–130% FPL over-income band under 45 CFR § 1302.12(d)), categorical eligibility via TANF/SSI/SNAP, and foster care — are all supported. The homelessness gap is the most significant: homeless children are categorically eligible regardless of income, but the screener does not collect current housing status. Both the homelessness and migrant/seasonal gaps are accepted with precedent from the WA/TX Head Start implementations. No Kansas-specific eligibility rules vary from the federal floor.

---

## Research Sources

- [Head Start Act, 42 U.S.C. § 9831 et seq.](https://uscode.house.gov/view.xhtml?path=/prelim@title42/chapter105&edition=prelim)
- [Head Start Program Performance Standards, 45 CFR § 1302.12](https://www.ecfr.gov/current/title-45/subtitle-B/chapter-XIII/subchapter-B/part-1302/subpart-B/section-1302.12)
- [HHS Poverty Guidelines (Annual Update per 42 U.S.C. § 9902)](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines)
- [Head Start Program Facts FY2024](https://headstart.gov/program-data/article/head-start-program-facts-fiscal-year-2024)
- [Kansas Head Start Program Locations](https://www.ksheadstart.org/locations)

---

## Test Scenarios

> These scenarios document expected behavior. Because Head Start is implemented as a PolicyEngine program (Fed as-is), eligibility/value correctness is verified against PolicyEngine and covered by the shared federal `head_start` calculator's tests; these scenarios are the source of truth for QA.

### Scenario 1: Low-Income Family with 3-Year-Old Child — Clearly Eligible for Head Start
**What we're checking**: Typical low-income household with a preschool-age child who clearly meets Head Start age and income requirements
**Expected**: Eligible (PolicyEngine `head_start` value for one eligible child)

**Steps**:
- **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Birth month/year: `March 1996` (age 30), Relationship: `Head of Household`, Has income: `Yes`, Employment income: `$1,500` per month, Citizenship: `U.S. Citizen`
- **Person 2 (Child)**: Birth month/year: `September 2022` (age 3), Relationship: `Child`, Has income: `No`
- **Person 3 (Spouse)**: Birth month/year: `July 2000` (age 25), Relationship: `Spouse`, Has income: `No`
- **Current Benefits**: Select no current benefits

**Why this matters**: This is the most common Head Start eligibility pathway — a low-income family with a preschool-age child. At $1,500/month ($18,000/year) for a household of 3, income is ~66% of the 2026 FPL ($27,320/year), well below the 100% threshold. Tests the core income (45 CFR § 1302.12(a)(1)(i)) and age (45 CFR § 1302.12(c)(1)) requirements.

---

### Scenario 2: Child Age 6 — Excluded Due to Being Too Old
**What we're checking**: A child beyond the Head Start age range is excluded even if the family meets income requirements
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Birth month/year: `March 1990` (age 36), Relationship: `Head of Household`, Has income: `Yes`, Employment income: `$1,200` per month, Citizenship: `U.S. Citizen`
- **Person 2 (Child)**: Birth month/year: `January 2020` (age 6), Relationship: `Child`, Has income: `No`
- **Person 3 (Spouse)**: Birth month/year: `September 1992` (age 33), Relationship: `Spouse`, Has income: `No`
- **Current Benefits**: Select no current benefits

**Why this matters**: Validates that Head Start strictly enforces the maximum age requirement per 45 CFR § 1302.12(c)(1). A 6-year-old is excluded regardless of income.

---

### Scenario 3: Family Above 135% FPL Receiving SNAP — Categorical Eligibility Override
**What we're checking**: A family whose income exceeds the 135% FPL ceiling is still eligible because they receive SNAP, which confers categorical eligibility regardless of income
**Expected**: Eligible (one eligible child)

**Steps**:
- **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Birth month/year: `March 1990` (age 36), Relationship: `Head of Household`, Has income: `Yes`, Employment income: `$3,100` per month, Citizenship: `U.S. Citizen`
- **Person 2 (Spouse)**: Birth month/year: `June 1992` (age 33), Relationship: `Spouse`, Has income: `No`
- **Person 3 (Child)**: Birth month/year: `September 2022` (age 3), Relationship: `Child`, Has income: `No`
- **Current Benefits**: Select `SNAP`

**Why this matters**: Validates that SNAP categorical eligibility (45 CFR § 1302.12(a)(1)(ii)(B)) independently qualifies a family regardless of income. The same logic applies to TANF and SSI.

---

### Scenario 4: Family Above 135% FPL, No Categorical Eligibility — Income Ineligible
**What we're checking**: A family with income above 135% FPL and no categorical benefits is not eligible
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Birth month/year: `March 1990` (age 36), Relationship: `Head of Household`, Has income: `Yes`, Employment income: `$3,200` per month, Citizenship: `U.S. Citizen`
- **Person 2 (Spouse)**: Birth month/year: `June 1992` (age 33), Relationship: `Spouse`, Has income: `No`
- **Person 3 (Child)**: Birth month/year: `September 2022` (age 3), Relationship: `Child`, Has income: `No`
- **Current Benefits**: Select no current benefits

**Why this matters**: Validates the income ceiling with no categorical override. Confirms the screener correctly blocks families above the ceiling when no alternative pathway applies.

---

### Scenario 5: Foster Child — Categorical Eligibility via Foster Care
**What we're checking**: A child in foster care qualifies regardless of household income
**Expected**: Eligible (one eligible child)

**Steps**:
- **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Birth month/year: `March 1985` (age 41), Relationship: `Head of Household`, Has income: `Yes`, Employment income: `$4,000` per month, Citizenship: `U.S. Citizen`
- **Person 2 (Child)**: Birth month/year: `May 2022` (age 4), Relationship: `Foster Child`, Has income: `No`
- **Current Benefits**: Select no current benefits

**Why this matters**: Validates that foster care status (45 CFR § 1302.12(c)(1)(iii)) independently qualifies a child regardless of household income.
