# Implement Weatherization Assistance Program (TX) Program

## Program Details

- **Program**: Weatherization Assistance Program
- **State**: TX
- **White Label**: tx
- **Research Date**: 2026-03-19

## Eligibility Criteria

1. **Household income must be at or below 200% of the Federal Poverty Level (FPL)**
   - Screener fields:
     - `household_size`
     - `incomeStreams (all types)`
   - Source: 42 U.S.C. § 6862(7); 10 CFR 440.22(a); DOE WPN 24-1 (updated income guidelines); TDHCA WAP page states income eligibility based on federal poverty guidelines

2. **Categorical eligibility: Household automatically income-eligible if any member receives SSI (Supplemental Security Income)**
   - Screener fields:
     - `has_ssi`
   - Source: 10 CFR 440.22(a)(2); 42 U.S.C. § 1381 et seq. (SSA Title XVI)

3. **Categorical eligibility: Household automatically income-eligible if any member receives TANF (Temporary Assistance for Needy Families)**
   - Screener fields:
     - `has_tanf`
   - Source: 10 CFR 440.22(a)(2); 42 U.S.C. § 601 et seq. (SSA Title IV)

4. **Categorical eligibility: Household automatically income-eligible if any member receives SNAP (Supplemental Nutrition Assistance Program)**
   - Screener fields:
     - `has_snap`
   - Source: 10 CFR 440.22(a)(2); 7 U.S.C. § 2011 et seq. (Food and Nutrition Act of 2008)

5. **Categorical eligibility: Household automatically income-eligible if eligible for LIHEAP (Low-Income Home Energy Assistance Program)**
   - Screener fields:
     - `has_liheap` *(field needs to be added to screener)*
   - Note: The screener currently has `has_il_liheap` (Illinois-specific) but no generic LIHEAP field. A `has_liheap` field will need to be added.
   - Source: 10 CFR 440.22(a)(3); 42 U.S.C. § 8621 et seq.

6. **Applicant must reside in the state of Texas**
   - Screener fields:
     - `zipcode`
     - `county`
   - Source: TDHCA WAP page; 10 CFR 440.22 (state-administered program)

7. **Dwelling must be a residential unit (single-family home, multifamily unit, or mobile home)** ⚠️ *data gap*
   - Note: The TX screener does not collect fields to verify dwelling type. This is confirmed during the application and on-site audit process.
   - Source: 10 CFR 440.22; 42 U.S.C. § 6862(6) definition of 'dwelling unit'
   - Impact: Low

8. **Dwelling must not have been previously weatherized with DOE WAP funds (unless 15+ years have passed or exception applies)** ⚠️ *data gap*
   - Note: The screener has no field to capture whether the dwelling has been previously weatherized. This is verified during the application/audit process. The DOE announced in 2024 that the re-weatherization waiting period was reduced from the previous standard to 15 years.
   - Source: 10 CFR 440.18(e)(2); 42 U.S.C. § 6865(c)(2); DOE updated re-weatherization rules in 2024 allowing re-weatherization after 15 years
   - Impact: Medium

## Benefit Value

- **Single value estimate**: $372/year

**Methodology**: WAP is a one-time weatherization service, but the benefit is expressed as the average annual energy savings delivered to the household post-weatherization. The DOE reports that WAP recipients save an average of $372 or more every year in energy costs.

TX-specific note: Texas households tend to have above-average cooling loads (hot climate, larger homes), so the national average of $372/year is a reasonable and conservative estimate for TX. Comparable WAP implementations in this codebase use $300–$350/year (NC and CO respectively).

**Value Estimate Sources**:
- [DOE WAP Overview — "an average of $372 or more every year"](https://www.energy.gov/scep/wap/weatherization-assistance-program)
- CO WAP: `amount = 350` (`programs/programs/co/weatherization_assistance/calculator.py`)
- NC WAP: `amount = 300` (`programs/programs/nc/nc_weatherization/calculator.py`)

## Implementation Coverage

- ✅ Evaluable criteria: 6
- ⚠️  Data gaps: 2

6 of 8 total criteria can be evaluated with current screener fields. The core eligibility requirements — income at or below 200% FPL, categorical eligibility via SSI/TANF/SNAP/LIHEAP, and Texas residency — are well-covered (`has_snap` already exists in the screener; LIHEAP requires a new `has_liheap` screener field). The 2 data gaps are dwelling-specific requirements verified during the formal application and on-site audit process.

## Research Sources

- [DOE Weatherization Assistance Program (WAP) Overview – 42 U.S.C. § 6861 et seq. (Energy Conservation in Existing Buildings Act of 1976)](https://www.energy.gov/scep/wap/weatherization-assistance-program)
- [Texas Weatherization Assistance Program (WAP) – Texas Department of Housing and Community Affairs (TDHCA) – 10 TAC Chapter 6](https://www.tdhca.texas.gov/weatherization-assistance-program)
- [DOE Weatherization Assistance Program (WAP) Overview – Main Content Anchor](https://www.energy.gov/scep/wap/weatherization-assistance-program#main-content)
- [How to Apply for Weatherization Assistance – DOE WAP Application Guide](https://www.energy.gov/scep/wap/how-apply-weatherization-assistance)
- [DOE Weatherization Program Notices (WPNs) and Memorandums – Official Policy Guidance](https://www.energy.gov/scep/wap/weatherization-program-notices-and-memorandums)
- [DOE Weatherization Assistance Program Resource Hub – Training, Tools, and Technical Resources](https://www.energy.gov/scep/wap/weatherization-assistance-program-resource-hub)
- [DOE Weatherization Assistance Program Successes and Solutions Center – Case Studies and Best Practices](https://www.energy.gov/scep/wap/successes-solutions-center)
- [DOE Announces Over $400 Million in WAP Funding and Policy Changes (2025) – Press Release](https://www.energy.gov/cmei/scep/articles/energy-department-announces-over-400-million-funding-and-removes-burdensome)

## Acceptance Criteria

[ ] Scenario 1 (Single Adult with Income Just Below 200% FPL): User should be **eligible** with $372/year
[ ] Scenario 2 (Family of 4 with Income Exactly at 200% FPL Boundary): User should be **eligible** with $372/year
[ ] Scenario 3 (Family of 3 with Income Just Above 200% FPL): User should be **ineligible**
[ ] Scenario 4 (Household Over Income Limit with Categorical Eligibility via SNAP Only): User should be **eligible** with $372/year
[ ] Scenario 5 (Mixed Household with Priority Traits and Income Above 200% FPL): User should be **ineligible**

## Test Scenarios

### Scenario 1: Single Adult with Income Just Below 200% FPL
**What we're checking**: Single-person household with income just below the 200% FPL threshold, no categorical eligibility — confirms the income floor is correctly applied for a 1-person household
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `79901`, Select county `El Paso`
- **Household**: Number of people: `1`, Renter
- **Person 1**: Birth month/year: `June 1986` (age 39), Relationship: Head of Household, Not disabled, Employment income: `$2,600` per month ($31,200/year — just below 200% FPL for 1-person household in 2026: $15,960 × 2 = $31,920)
- **Current Benefits**: Do NOT select SNAP, SSI, or TANF

**Why this matters**: Confirms the 200% FPL income ceiling for a 1-person household. With no priority characteristics and no categorical eligibility, this is a clean test of the income check alone.

---

### Scenario 2: Family of 4 with Income Exactly at 200% FPL Boundary
**What we're checking**: 4-person household with income exactly equal to 200% FPL — confirms the threshold is inclusive (≤, not <) and that the FPL table scales correctly to a larger household size
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `77001`, Select county `Harris`
- **Household**: Number of people: `4`
- **Person 1**: Birth month/year: `June 1988` (age 37), Relationship: Head of Household, Employment income: `$2,750` per `semi-monthly` (twice per month, $66,000/year — exactly at 200% FPL for a 4-person household in 2026: $33,000 × 2 = $66,000)
- **Person 2**: Birth month/year: `September 1990` (age 35), Relationship: Spouse, No income
- **Person 3**: Birth month/year: `January 2016` (age 10), Relationship: Child, No income
- **Person 4**: Birth month/year: `April 2019` (age 6), Relationship: Child, No income
- **Current Benefits**: Do not select any current benefits

**Why this matters**: Validates that the income threshold is evaluated as ≤ 200% FPL (not strictly <), and that the FPL lookup correctly applies the 4-person threshold. Pairing this with Scenario 1 (1-person household) confirms the FPL table scales across household sizes.

---

### Scenario 3: Family of 3 with Income Just Above 200% FPL
**What we're checking**: 3-person household with income slightly above the 200% FPL threshold and no categorical eligibility — confirms the income ceiling is enforced
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78745`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1**: Birth month/year: `June 1988` (age 37), Relationship: Head of Household, Employment income: `$3,000` per month, Not disabled
- **Person 2**: Birth month/year: `September 1990` (age 35), Relationship: Spouse, Employment income: `$1,600` per month, Not disabled
- **Person 3**: Birth month/year: `January 2019` (age 7), Relationship: Child, No income, Not disabled
- **Current Benefits**: Do not select any current benefits (no SNAP, SSI, or TANF)

**Why this matters**: A family of 3 earning $55,200/year ($560 above the $54,640 200% FPL limit for 3 people in 2026: $27,320 × 2) should be denied. This confirms the ceiling is a hard gate, not a soft threshold.

---

### Scenario 4: Household Over Income Limit with Categorical Eligibility via SNAP Only
**What we're checking**: A household whose gross income exceeds 200% FPL but qualifies solely through SNAP categorical eligibility — no SSI, no TANF — isolating SNAP as the trigger
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `77001`, Select county `Harris`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `June 1985` (age 40), Relationship: Head of Household, Employment income: `$3,700` per month ($44,400/year — above the 200% FPL of ~$43,280 for a 2-person household in 2026: $21,640 × 2), Not disabled
- **Person 2**: Birth month/year: `March 2015` (age 11), Relationship: Child, No income, Not disabled
- **Current Benefits**: Select `SNAP (food stamps)` — do NOT select SSI or TANF
- **Housing**: Renter

**Why this matters**: Confirms SNAP is independently recognized as a categorical eligibility trigger per 10 CFR 440.22(a)(2). With income above 200% FPL, this household would be ineligible on income alone — SNAP is the only qualifying factor.

---

### Scenario 5: Mixed Household with Priority Traits and Income Above 200% FPL
**What we're checking**: Multi-member household with elderly, disabled, and child members where total income exceeds 200% FPL and no categorical benefits are received — confirms priority traits do NOT override the income ceiling
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78745`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1**: Relationship: `Head of Household`, Birth month/year: `June 1985` (age 40), Employment income: `$4,500` per month, Not disabled
- **Person 2**: Relationship: `Grandparent`, Birth month/year: `January 1954` (age 72), Social Security Retirement income: `$1,200` per month, Disabled: Yes
- **Person 3**: Relationship: `Child`, Birth month/year: `September 2017` (age 8), No income, Not disabled
- **Current Benefits**: Do NOT select SNAP, SSI, or TANF
- **Housing**: Homeowner

**Why this matters**: Priority characteristics (elderly, disabled, children) affect which applicants get served first, but they are NOT eligibility gates. This scenario confirms the screener correctly enforces the income ceiling even when priority-qualifying members are present.

---


## Source Documentation

- https://www.energy.gov/scep/wap/weatherization-assistance-program
- https://www.tdhca.texas.gov/weatherization-assistance-program
