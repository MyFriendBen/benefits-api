# Implement Weatherization Assistance Program (WA) Program

## Program Details

- **Program**: Weatherization Assistance Program
- **State**: WA
- **White Label**: wa
- **Research Date**: 2026-05-15
- **Reviewer Date**: 2026-05-25

## Eligibility Criteria

1. **Household income must be at or below 200% of the Federal Poverty Level (FPL), 60% of State Median Income (SMI), or 80% of Area Median Income (AMI)** — whichever is most generous
   - Screener fields:
     - `household_size`
     - `calc_gross_income("yearly", ["all"])`
   - Source: WA Department of Commerce Weatherization page (https://www.commerce.wa.gov/weatherization/); 10 CFR 440.22(a) as amended by DOE guidance allowing states up to 200% FPL; Snohomish County Weatherization Program page; OIC of Washington Weatherization page
   - Note: WA Commerce explicitly lists 200% FPL OR 60% SMI OR 80% AMI as the income standard. Screener currently can compute 200% FPL via `calc_gross_income`; SMI/AMI fallbacks may not be evaluable. See data gap #6 (Seattle HomeWise 80% AMI variation) for the related AMI handling note.

2. **Categorical eligibility (federal): Households receiving TANF, SSI, or SNAP are automatically income-eligible**
   - Screener fields:
     - `has_tanf`
     - `has_ssi`
     - `has_snap`
   - Source: 42 U.S.C. § 6862(7); 10 CFR 440.22(b)

3. **Categorical eligibility (WA state-level expansion): Households receiving Section 8 / HUD housing assistance or Medicaid (Apple Health) are also categorically income-eligible**
   - Screener fields:
     - `has_section_8`
     - `has_medicaid`
   - Source: OIC of Washington Weatherization page; local WA agency pages referencing Section 8 and Medicaid/Apple Health as qualifying benefits
   - Note: This is a state/local extension of federal WAP categorical eligibility. While the federal statute (42 U.S.C. § 6862(7)) lists only TANF/SSI/SNAP, multiple Washington sub-grantees (OIC of Washington and others) accept Section 8 and Medicaid as automatically qualifying. Implementing both gives broader screener accuracy for WA applicants but may overstate eligibility at agencies that don't accept these pathways; document this in the program description so applicants verify with their local agency.

4. **Applicant must reside in Washington State**
   - Screener fields:
     - `zipcode`
     - `county`
   - Source: WA Department of Commerce Weatherization page; program is state-administered

5. **Both homeowners and renters are eligible**
   - Screener fields:
     - `isHomeOwner`
     - `isRenter`
     - `housing_situation`
   - Source: 42 U.S.C. § 6863; WA Commerce Weatherization page; OIC of Washington Weatherization page; Snohomish County Weatherization page

## Priority Criteria

The following are priority categories — they do not affect base eligibility but are used by local agencies to prioritize service order. They should be flagged for priority but not treated as hard eligibility gates.

1. **Priority given to households with elderly members (age 60+)**
   - Screener fields:
     - `birth_year` and `birth_month` (per household member; compute age >= 60)
   - Source: 42 U.S.C. § 6862(7); 10 CFR 440.16(b)(1); WA Commerce Weatherization page; Snohomish County Weatherization page; Pierce County Weatherization page

2. **Priority given to households with persons with disabilities**
   - Screener fields:
     - `disabled` (per household member)
   - Source: 42 U.S.C. § 6862(7); 10 CFR 440.16(b)(2); WA Commerce Weatherization page; Snohomish County Weatherization page; Pierce County Weatherization page

3. **Priority given to households with children (under 18)**
   - Screener fields:
     - `birth_year` and `birth_month` (per household member; compute age < 18)
     - `household_size`
   - Source: 42 U.S.C. § 6862(7); 10 CFR 440.16(b)(3); WA Commerce Weatherization page; Snohomish County Weatherization page; Pierce County Weatherization page

4. **Priority given to households with high energy burden / high energy costs relative to income**
   - Screener fields:
     - `calc_gross_income`
     - `expenses` (utility/energy type if available)
   - Source: 10 CFR 440.16(b)(4); WA Commerce Weatherization page; Snohomish County Weatherization page

## Data Gaps (Administrative / Unverifiable Criteria)

The following criteria exist in federal/state program rules but cannot be evaluated at the screener stage. They are documentation, location, or post-application administrative requirements. The screener should assume inclusivity (treat as met for screening purposes) and rely on the formal application to verify.

1. **Dwelling must not have been previously weatherized under WAP (unless re-weatherization criteria are met, typically 15+ years since last service)** ⚠️ *data gap*
   - Note: Federal rules generally prohibit re-weatherization of a dwelling that has already received WAP services, unless at least 15 years have passed or the dwelling has been damaged by fire, flood, or act of God. No screener field captures prior weatherization history.
   - Source: 10 CFR 440.18(e)(2); WA Commerce Weatherization page
   - Impact: ImpactLevel.MEDIUM

2. **Dwelling must be a residential unit (single-family home, mobile/manufactured home, or qualifying multifamily unit)** ⚠️ *data gap*
   - Note: The program serves residential dwellings including single-family homes, mobile homes, and multifamily buildings (where 66% or more of units are income-eligible or 50% in buildings with 2-4 units). The screener does not capture dwelling type. However, most applicants will live in qualifying dwelling types, so this is a relatively low-impact gap for screening purposes.
   - Source: 10 CFR 440.22; WA Commerce Weatherization page; Snohomish County Weatherization page
   - Impact: ImpactLevel.LOW

3. **Dwelling must be located in Washington State and within the service area of a participating local agency (Community Action Agency or similar sub-grantee)** ⚠️ *data gap*
   - Note: While we can verify Washington State residency via zipcode/county, we cannot verify that the specific address falls within a participating local agency's service area. In practice, the entire state is covered by WAP sub-grantees, so this is a very low-impact gap. The WA Commerce website lists agencies covering all regions of the state.
   - Source: WA Commerce Weatherization page; local agency service area maps
   - Impact: ImpactLevel.LOW

4. **For multifamily buildings (5+ units), at least 66% of units must be occupied by income-eligible households; for 2-4 unit buildings, at least 50% must be income-eligible** ⚠️ *data gap*
   - Note: This criterion applies to the building level for multifamily weatherization and cannot be evaluated at the individual household screener level. Individual tenants in multifamily buildings may still apply and the agency will assess building-level eligibility.
   - Source: 10 CFR 440.22(b)(2); 42 U.S.C. § 6863(b)(1)
   - Impact: ImpactLevel.LOW

5. **Dwelling must pass an energy audit / home assessment to determine cost-effective weatherization measures** ⚠️ *data gap*
   - Note: After eligibility is confirmed, a home energy audit is conducted to determine what weatherization measures are cost-effective. This is a post-eligibility program step, not a screening criterion. However, if no cost-effective measures are identified, the home may not receive services.
   - Source: 10 CFR 440.21; WA Commerce Weatherization page; Snohomish County Weatherization page
   - Impact: ImpactLevel.LOW

6. **Seattle HomeWise program uses 80% Area Median Income (AMI) threshold instead of 200% FPL** ⚠️ *data gap*
   - Note: Seattle's HomeWise program, which combines federal WAP funds with city funds, uses 80% AMI as its income threshold. AMI varies by geographic area and is updated annually by HUD. The screener does not have AMI lookup capability. For the statewide WAP program, 200% FPL is the standard. Seattle residents may qualify under either threshold. Since this is a local variation and 80% AMI for Seattle is generally higher than 200% FPL for most household sizes, using 200% FPL as the screener threshold is conservative and appropriate.
   - Source: City of Seattle Office of Housing – HomeWise Weatherization page
   - Impact: ImpactLevel.LOW

## Benefit Value

The benefit is delivered as in-kind weatherization services (insulation, air sealing, heating-system repair/replacement, etc.) rather than as a cash transfer. Per WA Commerce, the average per-home spending is up to approximately $7,669 (one-time lump-sum value to the household; varies by audit findings and local agency cost limits).

For screener purposes:
- `value_format`: `"lump_sum"` (one-time service per dwelling)
- `value_type`: `"benefit"`
- `estimated_value`: `"Up to $7,669 per home"`
- `has_calculator`: `false` (no calculation; eligibility only)

Validation scenarios assert `value: 7669` (the per-home upper estimate per WA Commerce) on eligible cases as a standard reference value. The actual benefit delivered to a household will vary based on the home energy audit, but the test value represents the configured maximum.

## Implementation Coverage

- ✅ Evaluable criteria: 5 base eligibility + 4 priority = 9
- ⚠️  Data gaps: 6 (property-level or post-application requirements verified at application stage)

The highest-impact criteria (income at or below 200% FPL, federal categorical eligibility via TANF/SSI/SNAP, WA state-level categorical eligibility via Section 8 / Medicaid, and Washington State residency) are all evaluable. The calculator enforces only the 200% FPL income standard; the alternative 60% SMI and 80% AMI thresholds (including the Seattle HomeWise 80% AMI variation) are data gaps not implemented in the calculator and are verified at the formal application stage. Priority criteria for elderly, disabled, and families with children are also evaluable. The 6 criteria that cannot be evaluated are primarily property-level or post-application requirements (prior weatherization history, dwelling type, local-agency service area, multifamily building composition, energy audit pass, Seattle HomeWise AMI variation) that are appropriately handled during the formal application process rather than at the screening stage. No critical eligibility gaps exist that would significantly impact screening accuracy.

## Research Sources

- [WA Department of Commerce – Weatherization Assistance Program Overview (42 U.S.C. § 6861 et seq.)](https://www.commerce.wa.gov/weatherization/)
- [WA Department of Commerce – Washington's Weatherization Assistance Program (funding page)](https://www.commerce.wa.gov/funding/washingtons-weatherization-assistance-program/)
- [OIC of Washington – Weatherization Program (Local WAP Service Provider)](https://oicofwa.org/programs/support/weatherization/)
- [Pierce County, WA – Home Weatherization Assistance Program (Local WAP Implementation)](https://www.piercecountywa.gov/1290/Home-Weatherization)
- [Snohomish County, WA – Weatherization Program (Local WAP Implementation)](https://snohomishcountywa.gov/600/Weatherization-Program)
- [City of Seattle Office of Housing – HomeWise Weatherization Program (Local WAP Implementation)](https://www.seattle.gov/housing/homeowners/weatherization)
- [WA Department of Commerce – Housing Division Overview](https://www.commerce.wa.gov/housing/)
- [WA Department of Commerce – Community Services and Facilities Division](https://www.commerce.wa.gov/community-services/)
- [WA Department of Commerce – Energy Division (State Energy Program Administration)](https://www.commerce.wa.gov/energy/)
- [U.S. DOE – How to Apply for Weatherization Assistance](https://www.energy.gov/cmei/scep/wap/how-apply-weatherization-assistance)

## Acceptance Criteria

[ ] Scenario 1 (Low-Income Senior Homeowner on SSI - Clearly Eligible): User should be **eligible**, value: $7,669
[ ] Scenario 2 (Single Adult Renter at Exactly 200% FPL - Barely Eligible): User should be **eligible**, value: $7,669
[ ] Scenario 3 (Family of Four with Income Just Below 200% FPL - Barely Eligible): User should be **eligible**, value: $7,669
[ ] Scenario 4 (Single Adult with Income Just Above 200% FPL - Not Eligible): User should be **ineligible**
[ ] Scenario 5 (Person Exactly Age 60 - Meets Elderly Priority Threshold): User should be **eligible**, value: $7,669
[ ] Scenario 6 (Person Age 59 - Just Below Elderly Priority Threshold): User should be **ineligible**
[ ] Scenario 7 (Washington State Resident in Spokane County - Eligible Location): User should be **eligible**, value: $7,669
[ ] Scenario 8 (Household Already Receiving Weatherization Assistance - Exclusion): User should be **ineligible**
[ ] Scenario 9 (Mixed Household - High-Earning Adult with Elderly Disabled Parent and Young Child): User should be **eligible**, value: $7,669
[ ] Scenario 10 (Five-Member Multi-Generational Household with TANF/SSI and Disabled Members): User should be **eligible**, value: $7,669
[ ] Scenario 11 (Zero Income Household with No Current Benefits - Eligible by Income Only): User should be **eligible**, value: $7,669
[ ] Scenario 12 (Apple Health (Medicaid) Recipient Above 200% FPL - State Categorical Eligibility): User should be **eligible**, value: $7,669
[ ] Scenario 13 (High Energy Burden Priority - Household with Disproportionate Utility Costs): User should be **eligible**, value: $7,669

## Test Scenarios

### Scenario 1: Low-Income Senior Homeowner on SSI - Clearly Eligible
**What we're checking**: Typical clearly eligible applicant: income well below 200% FPL, elderly (60+), receiving SSI (categorical eligibility), homeowner in Washington State
**Expected**: Eligible, value: $7,669

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King County`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1958` (age 68), Relationship: `Head of Household`, Has income: Yes, Income type: SSI, SSI amount: `943` per month, Homeowner: Yes, Disabled: Yes
- **Current Benefits**: Select `SSI` as a current benefit
- **Expenses**: Enter high energy costs if prompted (e.g., `250` per month for heating)

**Why this matters**: This is the most straightforward eligible case: a low-income senior on SSI who owns their home. They qualify through both income-based eligibility (well under 200% FPL) and categorical eligibility (SSI recipient), and receive priority as an elderly person with a disability. This validates the core happy path for the program.

---

### Scenario 2: Single Adult Renter at Exactly 200% FPL - Barely Eligible
**What we're checking**: Verifies eligibility when household income is exactly at the 200% FPL threshold with no categorical eligibility, no priority flags, and minimal qualifying factors
**Expected**: Eligible, value: $7,669

**Steps**:
- **Location**: Enter ZIP code `98901`, Select county `Yakima County`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `August 1991` (age 34), Relationship: Head of Household, Not disabled, Has income: Yes, Employment income: `2,660` per month, No other income sources
- **Housing**: Select `Renter`
- **Current Benefits**: Select no current benefits (no TANF, SSI, SNAP, Section 8, or Medicaid)

**Why this matters**: Tests the boundary condition where a single adult with no categorical eligibility and no priority characteristics barely qualifies based solely on income at exactly 200% FPL. The 2026 FPL for a 1-person household is $15,960, so 200% FPL = $31,920/year. Monthly income of $2,660 = $31,920/year, which is exactly at the threshold. This ensures the program does not require categorical eligibility or priority status as a hard requirement and that "at or below" is enforced inclusively at the boundary.

---

### Scenario 3: Family of Four with Income Just Below 200% FPL - Barely Eligible
**What we're checking**: Validates that a household with gross annual income slightly below the 200% FPL threshold for their household size qualifies for WAP
**Expected**: Eligible, value: $7,669

**Steps**:
- **Location**: Enter ZIP code `98103`, Select county `King County`
- **Household**: Number of people: `4`
- **Person 1**: Birth month/year: `August 1988` (age 37), Relationship: Head of Household, Has income: Yes, Employment income: `$2,850` per month, No disability, Citizenship: US Citizen
- **Person 2**: Birth month/year: `November 1990` (age 35), Relationship: Spouse, Has income: Yes, Employment income: `$1,300` per month, No disability, Citizenship: US Citizen
- **Person 3**: Birth month/year: `March 2018` (age 8), Relationship: Child, Has income: No, No disability
- **Person 4**: Birth month/year: `January 2021` (age 5), Relationship: Child, Has income: No, No disability
- **Housing**: Select homeowner
- **Current Benefits**: Do not select any current benefits (no TANF, SSI, LIHEAP, Section 8, or Medicaid)

**Why this matters**: Tests that a family of four with combined income just under the 200% FPL threshold for their household size is correctly determined eligible. The 2026 FPL for a household of 4 is $33,000, so 200% = $66,000. Combined annual income is $2,850 + $1,300 = $4,150/month = $49,800/year, which is well within the threshold. This validates multi-member income aggregation and the income-only pathway without any categorical eligibility.

---

### Scenario 4: Single Adult with Income Just Above 200% FPL - Not Eligible
**What we're checking**: Verifies that a single-person household with gross annual income slightly exceeding 200% FPL is correctly determined ineligible when no categorical benefits apply
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `98103`, Select county `King County`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `August 1986` (age 39), Relationship: `Head of Household`, Do NOT select any disability, Has income: Yes, Employment income: `$2,700` per month, No other income sources
- **Current Benefits**: Do NOT select any current benefits (no TANF, SSI, SNAP, Section 8, Medicaid, etc.)
- **Housing**: Select `Renter`

**Why this matters**: This test confirms the income ceiling is enforced correctly. A single adult earning $2,700/month ($32,400/year) exceeds the 2026 200% FPL threshold for a 1-person household ($31,920). Without any categorical eligibility through TANF, SSI, SNAP, Section 8, or Medicaid, the applicant should be denied. This is the complement to Scenario 2 which tested the exact boundary.

---

### Scenario 5: Person Exactly Age 60 - Meets Elderly Priority Threshold
**What we're checking**: Validates that a household member who is exactly 60 years old qualifies for the elderly priority designation (age 60+), testing the minimum age boundary for priority consideration
**Expected**: Eligible, value: $7,669

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King County`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1966` (age 60), Relationship: `Head of Household`, Has income: Yes, Income type: Employment / wages, Income amount: `1800` per month, Not disabled, Homeowner: Yes
- **Current Benefits**: Select: No current benefits

**Why this matters**: The Weatherization Assistance Program gives priority to households with elderly members defined as age 60 or older per 42 U.S.C. § 6862(7) and 10 CFR 440.16(b)(1). Testing the exact boundary age of 60 ensures the system correctly identifies someone at the minimum elderly threshold as qualifying for priority, rather than requiring age 61 or older. This is a critical boundary test for the age-based priority logic.

---

### Scenario 6: Person Age 59 - Just Below Elderly Priority Threshold
**What we're checking**: Validates that a person aged 59 (one year below the 60+ elderly priority threshold) does NOT receive elderly priority designation, and that with income above 200% FPL and no categorical eligibility, they are not eligible
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King County`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `August 1966` (age 59), Relationship: `Head of Household`, Has income: Yes, Employment income: `$3,200` per month ($38,400/year), No disability, No current benefits (no TANF, SSI, SNAP, Section 8, or Medicaid)
- **Housing**: Select homeowner or renter: `Renter`
- **Current Benefits**: Do not select any current benefits

**Why this matters**: This tests the boundary just below the elderly priority age threshold of 60. A person who is 59 should not receive the elderly priority flag. Combined with income above 200% FPL (2026 threshold is $31,920/year for HH=1; this household's $38,400/year is well above) and no categorical benefits, this person should not be eligible, confirming the age threshold does not incorrectly round up or include age 59.

---

### Scenario 7: Washington State Resident in Spokane County - Eligible Location
**What we're checking**: Verifies that a household located within Washington State (Spokane County) is recognized as being within the WAP service area and meets the geographic residency requirement
**Expected**: Eligible, value: $7,669

**Steps**:
- **Location**: Enter ZIP code `99201`, Select county `Spokane County`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `March 1980` (age 46), Relationship: Head of Household, Has income: Yes, Employment income: `$1,800` per month, Citizenship: US Citizen
- **Person 2**: Birth month/year: `July 2014` (age 11), Relationship: Child, Has income: No
- **Housing**: Select housing type: Renter
- **Current Benefits**: Select: None

**Why this matters**: This test confirms that a valid Washington State ZIP code and county (Spokane County, eastern WA) is properly recognized as within the WAP service area. It validates the geographic residency criterion (Criterion 4) using a location outside the Seattle metro area to ensure statewide coverage is correctly implemented, not just western WA locations.

---

### Scenario 8: Household Already Receiving Weatherization Assistance - Exclusion
**What we're checking**: Whether a household that already receives the Weatherization Assistance Program benefit is flagged as ineligible or shown a different message, since the program typically weatherizes a home only once
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `98103`, Select county `King County`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `March 1980` (age 46), Relationship: Head of Household, Has income: Yes, Employment income: `$1,500` per month, Citizenship: US Citizen
- **Person 2**: Birth month/year: `July 1982` (age 43), Relationship: Spouse, Has income: Yes, Employment income: `$1,200` per month
- **Current Benefits**: Select that the household currently receives **Weatherization Assistance Program** (WAP) benefits, If the screener lists WAP or similar energy assistance weatherization benefit, check/select it
- **Housing**: Select homeowner

**Why this matters**: The Weatherization Assistance Program is typically a one-time service per dwelling. A household that has already received weatherization should not be directed to apply again. This tests that the screener correctly handles the exclusion case where the applicant already has the benefit, preventing duplicate referrals and ensuring accurate program recommendations.

---

### Scenario 9: Mixed Household - High-Earning Adult with Elderly Disabled Parent and Young Child
**What we're checking**: Validates that household-level income eligibility is assessed collectively (total household income vs. household size FPL), even when individual members have varying characteristics - one high-earning adult, one elderly disabled member on SSI, and one child
**Expected**: Eligible, value: $7,669

**Steps**:
- **Location**: Enter ZIP code `98103`, Select county `King County`
- **Household**: Number of people: `3`
- **Person 1**: Relationship: `Head of Household`, Birth month/year: `March 1991` (age 35), Has income: Yes, Employment income: `$2,400` per month, Not disabled, No current benefits
- **Person 2**: Relationship: `Parent`, Birth month/year: `January 1958` (age 68), Has income: Yes, SSI income: `$943` per month, Disabled: Yes, Current benefits: SSI
- **Person 3**: Relationship: `Child`, Birth month/year: `September 2021` (age 4), Has income: No, Not disabled
- **Housing**: Housing situation: `Renter`
- **Current Benefits**: Select `SSI` as a current benefit for the household

**Why this matters**: This tests a realistic mixed household where one member earns moderate wages, another is an elderly disabled SSI recipient, and a young child is present. It validates that the screener correctly aggregates household income across all members, applies the correct FPL threshold for household size 3, recognizes categorical eligibility through SSI, and triggers all three priority categories (elderly, disabled, children) simultaneously. This is a common real-world scenario where a working adult cares for an aging parent and a young child.

---

### Scenario 10: Five-Member Multi-Generational Household with TANF/SSI and Disabled Members
**What we're checking**: Validates that a multi-member household where multiple members independently trigger eligibility criteria (categorical eligibility via TANF/SSI, disability priority, child priority, elderly priority) is correctly identified as eligible with all priority flags
**Expected**: Eligible, value: $7,669

**Steps**:
- **Location**: Enter ZIP code `98103`, Select county `King County`
- **Household**: Number of people: `5`
- **Person 1**: Birth month/year: `March 1964` (age 62), Relationship: Head of Household, Has a disability: Yes, Has income: Yes - SSI of `$900` per month
- **Person 2**: Birth month/year: `August 1990` (age 35), Relationship: Child (adult child of head), Has a disability: No, Has income: Yes - Wages of `$1,200` per month
- **Person 3**: Birth month/year: `November 2012` (age 13), Relationship: Grandchild of head, Has a disability: Yes, Has income: No
- **Person 4**: Birth month/year: `January 2023` (age 3), Relationship: Grandchild of head, Has a disability: No, Has income: No
- **Person 5**: Birth month/year: `June 1960` (age 65), Relationship: Spouse, Has a disability: No, Has income: Yes - SS Retirement of `$750` per month
- **Current Benefits**: Select TANF as a current benefit, Select SSI as a current benefit
- **Housing**: Select homeowner

**Why this matters**: This scenario tests that the system correctly evaluates a complex multi-member household where multiple individuals each independently satisfy different eligibility and priority criteria. It ensures the screener aggregates income across all earners, recognizes categorical eligibility from current benefits, and identifies all applicable priority categories (elderly, disabled, children) across different household members rather than only checking the head of household.

---

### Scenario 11: Zero Income Household with No Current Benefits - Eligible by Income Only
**What we're checking**: Tests whether a household reporting exactly $0 income (an edge case boundary) qualifies based on income alone without any categorical eligibility from benefits, and verifies the system handles zero income correctly
**Expected**: Eligible, value: $7,669

**Steps**:
- **Location**: Enter ZIP code `98225`, Select county `Whatcom County`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `September 1991` (age 34), Relationship: Head of Household, Do NOT select any disability, No income of any kind — select no income or enter `0` for all income fields, No current benefits (no TANF, SSI, SNAP, Section 8, Medicaid, or any other benefit), Housing: Select renter

**Why this matters**: Zero income is a valid but unusual edge case. Some systems may mishandle $0 income (e.g., treating it as missing data, triggering validation errors, or incorrectly flagging the application). This test ensures the system properly evaluates a household with no income and no categorical eligibility — relying purely on the income-based pathway at the extreme low boundary of $0. It also confirms that the absence of all priority categories and all current benefits does not prevent eligibility.

---

### Scenario 12: Apple Health (Medicaid) Recipient Above 200% FPL - State Categorical Eligibility
**What we're checking**: Validates that a household enrolled in Apple Health (Medicaid) qualifies via WA state-level categorical eligibility expansion (Criterion 3) even when income exceeds 200% FPL and no federal categorical benefit (TANF/SSI/SNAP) applies
**Expected**: Eligible, value: $7,669

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King County`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `May 1985` (age 40), Relationship: `Head of Household`, Has income: Yes, Employment income: `$3,500` per month ($42,000/year — well above 2026 200% FPL of $31,920 for HH=1), No disability, Housing: Renter
- **Insurance**: Select `Medicaid` (Apple Health)
- **Current Benefits**: Do NOT select any federal categorical benefit (no TANF, SSI, or SNAP)

**Why this matters**: This test isolates the WA state-level categorical eligibility pathway. The federal income test fails ($42,000/year > $31,920 threshold), and the household has no federal categorical benefit. Only WA's state-level expansion via Medicaid/Apple Health (Criterion 3) should mark them eligible. This is a clean unit test for the state categorical pathway and confirms that the screener treats Apple Health enrollment as automatic income-eligibility regardless of actual reported income.

---

### Scenario 13: High Energy Burden Priority - Household with Disproportionate Utility Costs
**What we're checking**: Validates that a household with income at or below 200% FPL AND high energy costs relative to income triggers the high energy burden priority flag (Priority Criterion 4)
**Expected**: Eligible, value: $7,669

**Steps**:
- **Location**: Enter ZIP code `99201`, Select county `Spokane County` (eastern WA, where heating costs tend to be high)
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `June 1981` (age 44), Relationship: `Head of Household`, Has income: Yes, Employment income: `$1,500` per month ($18,000/year, well under 2026 200% FPL of $31,920 for HH=1), No disability, Housing: Renter
- **Expenses**:
  - Heating: `$400` per month
  - Electricity: `$150` per month
  - (Combined energy expenses ≈ $6,600/year, or ~37% of gross annual income — well above the typical high-energy-burden threshold of 6–10% of income)
- **Current Benefits**: Do not select any current benefits

**Why this matters**: High energy burden is a federal WAP priority criterion (10 CFR 440.16(b)(4)). When energy costs consume a disproportionate share of household income, the household is prioritized for service ahead of similarly-income-eligible households with lower energy costs. This scenario tests that the screener correctly identifies and flags households with high energy expenses relative to income for priority consideration. It also exercises the `expenses` screener field path that other scenarios don't.

---


## Source Documentation

- https://www.commerce.wa.gov/weatherization/
- https://www.commerce.wa.gov/funding/washingtons-weatherization-assistance-program/
- https://oicofwa.org/programs/support/weatherization/
- https://www.piercecountywa.gov/1290/Home-Weatherization
- https://snohomishcountywa.gov/600/Weatherization-Program
- https://www.seattle.gov/housing/homeowners/weatherization
- https://www.energy.gov/cmei/scep/wap/how-apply-weatherization-assistance

## JSON Test Cases
File: `wa_wap.json`

## Program Configuration
File: `wa_wap_initial_config.json`
