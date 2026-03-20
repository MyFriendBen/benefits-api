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

2. **Categorical eligibility: Household automatically income-eligible if any member receives SNAP benefits**
   - Screener fields:
     - `has_snap`
   - Source: 10 CFR 440.22(b)(1); 42 U.S.C. § 6862(7)(A)

3. **Categorical eligibility: Household automatically income-eligible if any member receives SSI (Supplemental Security Income)**
   - Screener fields:
     - `has_ssi`
   - Source: 10 CFR 440.22(b)(1); 42 U.S.C. § 6862(7)(B)

4. **Categorical eligibility: Household automatically income-eligible if any member receives TANF (Temporary Assistance for Needy Families)**
   - Screener fields:
     - `has_tanf`
   - Source: 10 CFR 440.22(b)(1); 42 U.S.C. § 6862(7)(C)

5. **Applicant must reside in the state of Texas**
   - Screener fields:
     - `zipcode`
     - `county`
   - Source: TDHCA WAP page; 10 CFR 440.22 (state-administered program)

6. **Dwelling must be a residential unit (single-family home, multifamily unit, or mobile home)** ⚠️ *data gap*
   - Note: The TX screener does not collect fields to verify dwelling type. This is confirmed during the application and on-site audit process.
   - Source: 10 CFR 440.22; 42 U.S.C. § 6862(6) definition of 'dwelling unit'
   - Impact: Low

7. **Dwelling must not have been previously weatherized with DOE WAP funds (unless 15+ years have passed or exception applies)** ⚠️ *data gap*
   - Note: The screener has no field to capture whether the dwelling has been previously weatherized. This is verified during the application/audit process. The DOE announced in 2024 that the re-weatherization waiting period was reduced from the previous standard to 15 years.
   - Source: 10 CFR 440.18(e)(2); 42 U.S.C. § 6865(c)(2); DOE updated re-weatherization rules in 2024 allowing re-weatherization after 15 years
   - Impact: Medium

8. **Applicant must be a U.S. citizen or meet immigration status requirements**
   - Note: The federal WAP statute (42 U.S.C. § 6861 et seq.) does not contain an explicit citizenship or immigration status requirement, and DOE has historically not required citizenship verification for WAP. This is broader than many federal benefit programs. In Texas, TDHCA follows federal guidelines and does not impose additional immigration status restrictions. As a result, WAP is available to all immigration statuses — citizens, green card holders (regardless of years held), refugees, individuals with work authorization, and undocumented individuals. This criterion is handled by front-end filtering; the `legal_status_required` in the program config should include all statuses.
   - Source: 42 U.S.C. § 6861 et seq. (no citizenship restriction); DOE WAP guidance does not restrict by immigration status; TDHCA WAP follows federal eligibility rules
   - Screener fields: Handled by front-end (`legal_status_required`)

9. **Household must occupy the dwelling as their primary residence** ⚠️ *data gap*
   - Note: The dwelling must be the applicant's primary residence. Vacation homes, investment properties, and unoccupied units are not eligible. The screener does not explicitly capture whether the dwelling is the primary residence, though isHomeOwner/isRenter implies occupancy.
   - Source: 10 CFR 440.22; implicit in program design (weatherization of occupied dwelling units)
   - Impact: Low

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
- ⚠️  Data gaps: 3

6 of 9 total criteria can be evaluated with current screener fields and front-end filtering. The core eligibility requirements — income at or below 200% FPL, categorical eligibility via SNAP/SSI/TANF, Texas residency, and immigration status (via front-end filtering) — are well-covered. The 3 data gaps are dwelling-specific requirements verified during the formal application and on-site audit process.

## Research Sources

- [DOE Weatherization Assistance Program (WAP) Overview – 42 U.S.C. § 6861 et seq. (Energy Conservation in Existing Buildings Act of 1976)](https://www.energy.gov/scep/wap/weatherization-assistance-program)
- [Texas Weatherization Assistance Program (WAP) – Texas Department of Housing and Community Affairs (TDHCA) – 10 TAC Chapter 6](https://www.tdhca.state.tx.us/energy/wap/)
- [DOE Weatherization Assistance Program (WAP) Overview – Main Content Anchor](https://www.energy.gov/scep/wap/weatherization-assistance-program#main-content)
- [How to Apply for Weatherization Assistance – DOE WAP Application Guide](https://www.energy.gov/scep/wap/how-apply-weatherization-assistance)
- [DOE Weatherization Program Notices (WPNs) and Memorandums – Official Policy Guidance](https://www.energy.gov/scep/wap/weatherization-program-notices-and-memorandums)
- [DOE Weatherization Assistance Program Resource Hub – Training, Tools, and Technical Resources](https://www.energy.gov/scep/wap/weatherization-assistance-program-resource-hub)
- [DOE Weatherization Assistance Program Successes and Solutions Center – Case Studies and Best Practices](https://www.energy.gov/scep/wap/successes-solutions-center)
- [DOE Announces Over $400 Million in WAP Funding and Policy Changes (2025) – Press Release](https://www.energy.gov/cmei/scep/articles/energy-department-announces-over-400-million-funding-and-removes-burdensome)

## Acceptance Criteria

[ ] Scenario 1 (Clearly Eligible Low-Income Senior Homeowner in Texas): User should be **eligible** with $372/year
[ ] Scenario 2 (Minimally Eligible Single Adult Renter at Income Threshold): User should be **eligible** with $372/year
[ ] Scenario 3 (Family of 4 with Income Just Below 200% FPL Threshold): User should be **eligible** with $372/year
[ ] Scenario 4 (Single Person with Income Exactly at 200% FPL Boundary): User should be **eligible** with $372/year
[ ] Scenario 5 (Family of 3 with Income Just Above 200% FPL - Should Be Ineligible): User should be **ineligible**
[ ] Scenario 6 (Person Exactly Age 60 - Meets Elderly Priority Threshold): User should be **eligible** with $372/year
[ ] Scenario 7 (Eligible Texas Resident in Rural West Texas ZIP Code): User should be **eligible** with $372/year
[ ] Scenario 8 (Mixed Household - Elderly Disabled Grandparent, Working-Age Adult, and Child with Income Above 200% FPL): User should be **ineligible**
[ ] Scenario 9 (Multiple Eligible Members - Elderly Couple with Disabled Adult Child and Grandchild, SNAP Recipient): User should be **eligible** with $372/year
[ ] Scenario 10 (Household of 1 with Income Exactly $0 - Zero Income Edge Case with Categorical Eligibility via SSI): User should be **eligible** with $372/year

## Test Scenarios

### Scenario 1: Clearly Eligible Low-Income Senior Homeowner in Texas
**What we're checking**: Typical applicant who meets all core eligibility criteria: income below 200% FPL, Texas residency, homeowner, and has elderly priority status
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78702`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `June 1958` (age 67), Relationship: Head of Household, Has income: Yes, Income type: Social Security Retirement, Amount: `$1,100` per month, Disabled: No, Homeowner: Yes
- **Person 2**: Birth month/year: `September 1960` (age 65), Relationship: Spouse, Has income: Yes, Income type: Social Security Retirement, Amount: `$750` per month, Disabled: No
- **Current Benefits**: Select: None currently receiving
- **Citizenship**: Select: US Citizen

**Why this matters**: This is the most straightforward happy path: a low-income senior couple who own their home in Texas, with income clearly below the 200% FPL threshold. Both members are over 60, triggering elderly priority. This validates that the screener correctly identifies a textbook WAP-eligible household without relying on categorical eligibility from other benefits.

---

### Scenario 2: Minimally Eligible Single Adult Renter at Income Threshold
**What we're checking**: Household with income just below 200% FPL for a single-person household, no priority categories, renter, no categorical eligibility - tests the income boundary
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `79901`, Select county `El Paso`
- **Household**: Number of people: `1`, Indicate that you are a renter
- **Person 1**: Birth month/year: `June 1986` (age 39), Relationship: Head of Household, Not disabled, No elderly status (under 60), Has employment income
- **Income**: Enter employment income of `$2,600` per month, This equals $31,200/year, which is just below 200% FPL for a 1-person household in 2025 ($15,650 × 2 = $31,300)
- **Current Benefits**: Do NOT select SNAP, SSI, or TANF - no current benefits
- **Housing**: Indicate renter status, Confirm residential dwelling unit

**Why this matters**: This tests the absolute income boundary for a single-person household with no categorical eligibility and no priority characteristics. It confirms the screener correctly includes households at exactly 200% FPL without requiring SNAP/SSI/TANF enrollment, and validates that renters (not just homeowners) qualify.

---

### Scenario 3: Family of 4 with Income Just Below 200% FPL Threshold
**What we're checking**: Validates that a household of 4 with gross annual income just below the 200% FPL limit ($62,400 for 2025 guidelines) is determined eligible for WAP
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `77001`, Select county `Harris`
- **Household**: Number of people: `4`
- **Person 1**: Birth month/year: `June 1988` (age 37), Relationship: Head of Household, Enter employment income of `$2,575` per `semi-monthly` (twice per month), This yields approximately $61,800/year, which is just below the 200% FPL of ~$62,400 for a household of 4
- **Person 2**: Birth month/year: `September 1990` (age 35), Relationship: Spouse, No income
- **Person 3**: Birth month/year: `January 2016` (age 10), Relationship: Child, No income
- **Person 4**: Birth month/year: `April 2019` (age 6), Relationship: Child, No income
- **Current Benefits**: Do not select any current benefits (SNAP, SSI, TANF)
- **Housing**: Select that the household rents or owns their home

**Why this matters**: This tests the critical income boundary for a larger household. A family of 4 earning just under the 200% FPL threshold (~$62,400) should qualify. This ensures the screener correctly applies the FPL table for household size 4 and does not incorrectly reject households that are marginally below the limit. It also differs from previous scenarios by testing a multi-person household without categorical eligibility.

---

### Scenario 4: Single Person with Income Exactly at 200% FPL Boundary
**What we're checking**: Validates that a household with gross annual income exactly equal to 200% of the Federal Poverty Level for a household of 1 is still eligible for WAP
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `79901`, Select county `El Paso`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `June 1981` (age 44), Relationship: `Head of Household`, Has income: Yes, Employment income: `$2,608` per month (this equals $31,296/year, which is at 200% FPL for a 1-person household in 2025 guidelines: $15,650 × 2 = $31,300), Not disabled, No current benefits (SNAP, SSI, TANF)
- **Housing**: Indicate applicant is a renter

**Why this matters**: Boundary testing is critical to ensure the screener correctly implements the 'at or below 200% FPL' income threshold using a less-than-or-equal comparison rather than strictly less-than. A single person earning exactly 200% FPL must qualify. This also differs from previous scenarios by testing a household size of 1 at the exact limit without any categorical eligibility or priority factors.

---

### Scenario 5: Family of 3 with Income Just Above 200% FPL - Should Be Ineligible
**What we're checking**: Verifies that a household of 3 with gross annual income slightly exceeding the 200% FPL threshold ($41,640 for 2025 guidelines) is correctly identified as NOT eligible for WAP
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78745`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1**: Birth month/year: `June 1988` (age 37), Relationship: Head of Household, Has income: Yes, Employment income: `$2,500` per month, No disability
- **Person 2**: Birth month/year: `September 1990` (age 35), Relationship: Spouse, Has income: Yes, Employment income: `$1,050` per month, No disability
- **Person 3**: Birth month/year: `January 2019` (age 7), Relationship: Child, Has income: No, No disability
- **Current Benefits**: Do not select any current benefits (no SNAP, SSI, or TANF)
- **Housing**: Select homeowner or renter as applicable

**Why this matters**: This test confirms the income ceiling is properly enforced. A family of 3 earning $42,600/year ($960 above the ~$41,640 200% FPL limit) without any categorically qualifying benefits should be denied. This validates the screener correctly rejects applicants who are just over the income threshold for a multi-person household.

---

### Scenario 6: Person Exactly Age 60 - Meets Elderly Priority Threshold
**What we're checking**: Validates that a household member who is exactly 60 years old qualifies for the elderly priority designation under 42 U.S.C. § 6863(b)(1)(B) and 10 CFR 440.16(b)(1), which define elderly as age 60 or older
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1966` (age exactly 60), Relationship: `Head of Household`, Has income: Yes, Income type: Employment / wages, Income amount: `1800` per month, Not disabled, Citizen
- **Housing**: Housing situation: Homeowner or Renter (select `Renter`), Confirm residential dwelling
- **Current Benefits**: No current benefits selected

**Why this matters**: The WAP regulations at 10 CFR 440.16(b)(1) define elderly as age 60 or older, creating a priority category. This test verifies the system correctly recognizes someone at exactly the age boundary (60) as meeting the elderly threshold, rather than requiring age 61 or older. Boundary testing at exact thresholds catches off-by-one errors in age comparison logic.

---

### Scenario 7: Eligible Texas Resident in Rural West Texas ZIP Code
**What we're checking**: Validates that a household located within a valid Texas ZIP code and county is recognized as residing in the state of Texas and eligible for the Weatherization Assistance Program service area
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `79901`, Select county `El Paso`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `June 1980` (age 45), Relationship: Head of Household, Has income: Yes, Employment income: `$1,200` per month, Homeowner or renter: Renter, Citizenship: US Citizen
- **Person 2**: Birth month/year: `September 2015` (age 10), Relationship: Child, Has income: No
- **Current Benefits**: Select: None

**Why this matters**: This test confirms that a valid Texas location (El Paso, a major city in far West Texas) is correctly recognized as within the WAP service area. Geographic eligibility is a fundamental requirement per 10 CFR 440.22 and TDHCA's state-administered program boundaries. Testing a geographically distant but still in-state location ensures the system doesn't inadvertently exclude valid Texas ZIP codes outside the central/eastern population centers.

---

### Scenario 8: Mixed Household - Elderly Disabled Grandparent, Working-Age Adult, and Child with Income Above 200% FPL
**What we're checking**: Tests a multi-member household with diverse characteristics (elderly member age 72 with disability, working-age adult age 40, and child age 8) where total household income exceeds 200% FPL for a 3-person household, making them income-ineligible despite having priority-qualifying members (elderly, disabled, child). Also verifies that no categorical eligibility override applies since no qualifying benefits are received.
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78745`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1**: Relationship: `Head of Household`, Birth month/year: `June 1985` (age 40), Has income: Yes, Employment income: `$4,500` per month, Not disabled, No current benefits (SNAP, SSI, TANF)
- **Person 2**: Relationship: `Parent` or `Grandparent`, Birth month/year: `January 1954` (age 72), Has income: Yes, Social Security Retirement income: `$1,200` per month, Disabled: Yes
- **Person 3**: Relationship: `Child`, Birth month/year: `September 2017` (age 8), Has income: No, Not disabled
- **Housing**: Housing type: Homeowner or Renter (select `Homeowner`), Confirm Texas residency
- **Current Benefits**: Do NOT select SNAP, SSI, or TANF, No categorical eligibility benefits

**Why this matters**: This scenario validates that priority characteristics (elderly, disabled, children) do NOT override the income eligibility requirement. A mixed household with members who would qualify for priority treatment must still meet the 200% FPL income threshold or receive a categorically qualifying benefit. This ensures the screener correctly distinguishes between priority scoring factors and hard eligibility gates.

---

### Scenario 9: Multiple Eligible Members - Elderly Couple with Disabled Adult Child and Grandchild, SNAP Recipient
**What we're checking**: Validates that a multi-member household with multiple priority categories (elderly, disabled, children) and categorical eligibility via SNAP is correctly identified as eligible with all priority flags
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78501`, Select county `Hidalgo`
- **Household**: Number of people: `4`
- **Person 1**: Birth month/year: `June 1958` (age 67), Relationship: Head of Household, Has income: Yes, Social Security Retirement income: `$1,100` per month, Not disabled, Citizenship: US Citizen
- **Person 2**: Birth month/year: `September 1960` (age 65), Relationship: Spouse, Has income: Yes, Social Security Retirement income: `$850` per month, Not disabled, Citizenship: US Citizen
- **Person 3**: Birth month/year: `January 1990` (age 36), Relationship: Child (adult child), Has income: Yes, SSI income: `$943` per month, Disabled: Yes, Citizenship: US Citizen
- **Person 4**: Birth month/year: `August 2018` (age 7), Relationship: Grandchild, Has income: No, Not disabled, Citizenship: US Citizen
- **Current Benefits**: Select SNAP (food stamps), Select SSI
- **Housing**: Housing situation: Homeowner or Renter (select Homeowner)

**Why this matters**: This scenario tests a complex multi-member household where every priority category (elderly, disabled, children, high-energy burden) is represented across different members. It also tests that categorical eligibility via both SNAP and SSI is recognized, and that the screener correctly handles four members with diverse ages, income sources, and characteristics. This ensures the system doesn't miss any priority flags when multiple eligible conditions coexist in the same household.

---

### Scenario 10: Household of 1 with Income Exactly $0 - Zero Income Edge Case with Categorical Eligibility via SSI
**What we're checking**: Tests edge case where household has absolutely zero income but qualifies through SSI categorical eligibility, verifying the system handles $0 income correctly and still processes categorical eligibility and priority flags (disabled)
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78501`, Select county `Hidalgo`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `June 1980` (age 45), Relationship: `Head of Household`, Mark as `disabled`, Has income: `No` (no income of any type), Do NOT select homeowner or renter if possible, or select `renter` to confirm dwelling unit eligibility
- **Current Benefits**: Select `SSI (Supplemental Security Income)` as a current benefit
- **Citizenship**: Select `US Citizen`

**Why this matters**: Zero-income households are a real edge case that can cause division-by-zero errors or unexpected behavior in income calculations. This tests that the system properly handles $0 income, correctly applies SSI categorical eligibility (10 CFR 440.22(b)(1)), and assigns disability priority (10 CFR 440.16(b)(2)). It also validates that a person who is a renter (not just homeowner) qualifies under the dwelling unit requirement.

---


## Source Documentation

- https://www.energy.gov/scep/wap/weatherization-assistance-program
- https://www.tdhca.state.tx.us/energy/wap/
