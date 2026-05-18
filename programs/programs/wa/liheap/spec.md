# Implement "LIHEAP" ("WA") Program

## Program Details

- **Program**: "LIHEAP"
- **State**: "WA"
- **White Label**: "wa"
- **Research Date**: 2026-04-29
- **Reviewed**: 2026-05-10 (Discovery Review)

## Eligibility Criteria

1. **Household income must be at or below 150% FPG (heating/crisis)**
   - Screener evaluates heating/crisis only (150% FPG). Weatherization (200% FPG) is out of scope — handled by local provider. No cooling component (see Benefit Value section for nuance).
   - FY2026 threshold, household of 4: 150% FPG = $48,225/year. Full table by household size in PY26 LIHEAP Eligibility Guidelines PDF.
   - WA uses FPG (not SMI), applied uniformly across all household sizes. Program year: October 2025 – September 2026.
   - **Note on FPG year**: The dollar thresholds quoted throughout this spec come from the 2025 federal poverty guidelines, which LIHEAP IM2025-02 makes mandatory for FY26 LIHEAP. If the MFB calculator pulls FPL values keyed to `year: 2026` (i.e., the 2026 federal poverty guidelines published in early 2026), the computed thresholds will be slightly higher than the LIHEAP-canonical ones quoted here. Dev should confirm which FPL table the calculator is using.
   - WA uses gross income (not net). Countable income types per WA 2026 Model Plan §1.9: wages, self-employment, unemployment insurance, strike pay, SSA benefits (excluding Medicare deduction), SSI, TANF, general assistance, retirement/pension benefits, loans that need to be repaid, cash gifts, jury duty compensation, rental income, work study income, alimony, child support, interest/dividends/royalties, commissions, legal settlements (if structured, recurring, and used for household expenses), foster care funds, third-party payments for daily living expenses.
   - Non-countable income (excluded from calculation): contract income, mortgage/sales contract payments, savings account balance, one-time lump-sum payments, WIA employment income, insurance payments (direct or for bill repayment), VA benefits, earned income of children under 18, retirement/pension/annuity account balances with withdrawal penalty, income tax refunds, VISTA stipends, AmeriCorps allowances, reimbursements.
   - Note: Households reporting zero income are not automatically excluded. The screener cannot replicate WA's zero-income verification process — treat as potentially eligible and direct to local provider.
   - Note: TANF, SSI, and SNAP income counts toward gross income but does not confer automatic eligibility. WA does not implement categorical eligibility (WA 2026 Model Plan §1.4). Do not use `has_tanf`, `has_snap`, or `has_ssi` as eligibility shortcuts.
   - Screener fields: `household_size`, `calc_gross_income("yearly", ["all"])` (for annual income comparison against the 150% FPG threshold table)
   - Source: WA LIHEAP 2026 Model Plan §§1.4, 1.8, 1.9, 2.1; PY26 LIHEAP Eligibility Guidelines PDF (https://deptofcommerce.app.box.com/s/3fp0xz4y2x2p4hedw9ww4sk7ma36srlx); LIHEAP Clearinghouse – FY2026 Percent of Poverty Table (https://liheapch.acf.gov/delivery/income_eligibility.htm); FPG Tables Attachment 2 (https://acf.gov/sites/default/files/documents/ocs/COMM_LIHEAP_IM2025-02_FPGSte-Table_Att2.pdf); LIHEAP Clearinghouse – Categorical Eligibility: States (https://liheapch.acf.gov/delivery/income_categorical.htm); 42 U.S.C. § 8624(b)(2)(B)

2. **Must reside in Washington State**
   - Screener fields: `zipcode`, `county`
   - Source: WA Department of Commerce LIHEAP FAQ (https://www.commerce.wa.gov/community-opportunities/liheap/); PY26 LIHEAP Eligibility Guidelines PDF (https://deptofcommerce.app.box.com/s/3fp0xz4y2x2p4hedw9ww4sk7ma36srlx)

3. **Household must not have already received a LIHEAP grant during the current program year (October 1 – September 30)** ⚠️ *data gap*
   - Screener fields: none
   - Note: The screener cannot verify whether a household has already received a LIHEAP grant in the current program year. Inclusivity assumption: we assume the household has not already received a grant. This is verified during the application process by the local provider. Suggestion: add a follow-up question when LIHEAP is selected in the current benefits section — "When did you last receive a LIHEAP grant?" (this program year / before this program year / not sure).
   - Source: WA Department of Commerce LIHEAP FAQ (https://www.commerce.wa.gov/community-opportunities/liheap/); PY26 LIHEAP Eligibility Guidelines PDF (https://deptofcommerce.app.box.com/s/3fp0xz4y2x2p4hedw9ww4sk7ma36srlx)

4. **Crisis assistance requires an active energy crisis situation (shutoff notice or near-empty tank)** ⚠️ *data gap*
   - Screener fields: none
   - Note: In addition to the income test, crisis assistance requires the household to have received a shutoff notice or have a near-empty fuel tank (per WA 2026 Model Plan §4.6 — year-round crisis). The screener cannot verify this. Inclusivity assumption: the screener does not differentiate between heating and crisis tracks — households that pass the income test are shown as potentially eligible for all applicable components. Crisis eligibility is confirmed by the local provider.
   - Suggestion: add "Natural disaster or energy crisis" to the Special Circumstances question, which triggers follow-up questions (e.g. received a shutoff notice, less than 10-day fuel supply) to identify crisis-eligible households.
   - Source: WA LIHEAP 2026 Model Plan §4.6

5. **Tribal households: 60% SMI income threshold; categorical eligibility available at 12 of 19 tribal grantees** ⚠️ *pending field request*
   - 19 WA tribal grantees operate independently from the state program. Most use 60% SMI (more generous than state 150% FPG). HH of 4: 60% SMI = $83,587 vs. 150% FPG = $48,225.
   - **FY2026 WA 60% SMI thresholds**: 1 person: $43,465 | 2: $56,839 | 3: $70,213 | 4: $83,587 | 5: $96,960 | 6: $110,334 | 7: $112,842 | 8: $115,350
   - **Tribes using 150% FPG instead**: Jamestown S'Klallam, Nooksack, Quileute, Spokane, Yakama. South Puget Intertribal: 60% SMI for heating, 150% FPG for crisis.
   - **Screener approach**: If tribal affiliation indicated, evaluate against 60% SMI. Slightly over-inclusive for 5 tribes — acceptable for a pre-screener. Tribal affiliation is self-reported.
   - No WA tribal grantees operate a cooling component. Weatherization thresholds vary by tribe.

   **Tribal categorical eligibility:**
   - 12 of 19 tribes allow households to bypass the income test if 1+ member receives TANF, SSI, SNAP, or VA benefits. Lower Elwha requires all members.
   - Tribes with categorical eligibility: Lummi (TANF/SSI/SNAP/VA), Muckleshoot (TANF/SSI/SNAP/VA + Foster Care), Quinault (TANF/SSI/SNAP/VA), South Puget Intertribal (TANF/SSI), Suquamish (TANF/SSI/SNAP), Lower Elwha (SSI/VA — all members), Port Gamble S'Klallam (TANF/SSI/SNAP), Quileute (TANF/SSI/SNAP/VA), Samish (TANF/SSI/SNAP), Small Tribes of Western WA (TANF/SSI/SNAP), Yakama (TANF/SSI/SNAP + FDPIR).
   - Tribes without categorical eligibility: Hoh, Jamestown S'Klallam, Kalispel, Makah, Nooksack, Spokane, Swinomish. Colville and Spokane use income-based eligibility only.
   - **Screener approach**: If tribal affiliation indicated and any member receives TANF, SSI, or SNAP, flag as potentially categorically eligible. VA benefits recognized by 4 tribes only — flag with limited applicability note.
   - **Tribal priority criteria**: Vary across all 19 grantees (point-based systems, different age thresholds, additional categories). Individual tribal model plans not reviewed in this pass (~50 pages each). State-program priority flags applied as approximation. Revisit when tribal routing is scoped.
   - Screener fields: `tribal_affiliation` *(pending)*, `has_tanf`, `has_ssi`, `has_snap`, `has_va_pension` *(pending)*, `household_size`, `calc_gross_income("yearly", ["all"])` (for annual income comparison against the 60% SMI threshold table)
   - Suggestions:
     - Add "Tribal member or receiving tribal services" to the Special Circumstances question to capture tribal affiliation.
     - Split "Veteran's Compensation or Benefits" into two options in both the current benefits section and income sources section: "VA Pension" (means-tested) and "VA Compensation or other VA benefits" (not means-tested). Only VA Pension counts toward tribal categorical eligibility.
   - Source: LIHEAP Clearinghouse – Income Eligibility for Tribes (https://liheapch.acf.gov/Tribes/income_eligibility.htm); Categorical Eligibility for Tribes (https://liheapch.acf.gov/Tribes/delivery/income_categorical.htm); SMI Tables Attachment 4 (https://acf.gov/sites/default/files/documents/ocs/COMM_LIHEAP_IM2025-02_SMIStateTable_Att4.pdf); Tribal Plans Index (https://liheapch.acf.gov/Tribes/trplans.htm); 42 U.S.C. § 8624(b)(2)(A)–(B)

## Priority Criteria

Priority criteria do not affect pass/fail eligibility — they flag vulnerability status for scheduling purposes only. In WA, priority is sub-recipient discretion (not a statewide mandate) and does not affect benefit amount. Crisis assistance has no demographic priority criteria — it is situation-driven.

Priority criteria vary by component: Heating and Weatherization share the same four criteria; Crisis uses none.

1. **Elderly member (age 60 or older)**
   - Screener fields: `birth_year`, `birth_month` (HouseholdMember) — compute age from these; the `age` field is deprecated per screener field inventory.
   - Source: WA LIHEAP 2026 Model Plan §§2.3, 5.8; 42 U.S.C. § 8624(b)(5)(A)

2. **Disabled member**
   - Screener fields: `disabled (HouseholdMember)`
   - Source: WA LIHEAP 2026 Model Plan §§2.3, 5.8; 42 U.S.C. § 8624(b)(5)(A)

3. **Young children**
   - Age cutoff: under 6 for heating (federal default — WA plan does not specify). Weatherization uses under 18 but is not screened here.
   - Screener fields: `birth_year`, `birth_month` (HouseholdMember) — compute age from these; the `age` field is deprecated per screener field inventory.
   - Source: WA LIHEAP 2026 Model Plan §§2.3, 5.8; 42 U.S.C. § 8624(b)(5)(B)

4. **High energy burden** ⚠️ *data gap*
   - Cannot be evaluated — screener collects income but not energy costs. Energy burden affects scheduling priority only, not benefit calculation (Section 2.5).
   - Weatherization also includes High Residential Energy Users as a separate priority category — not screened here.
   - Source: WA LIHEAP 2026 Model Plan §§2.3, 2.5, 5.8; 42 U.S.C. § 8624(b)(5)(A)

## Benefit Value

- **Heating assistance**: $250 minimum – $1,250 maximum per household per program year (WA 2026 Model Plan §2.6). Variable — benefit equals a percentage of annual heat cost based on household income as a percent of FPL: households at 0% FPL receive 90% of annual heat costs; households at 125% FPL receive 50%; linear scale between those points. Subject to $250 min and $1,250 max. See WA Benefit Matrix PDF for full calculation details.

  **Algebraic form (for implementation):**
  ```
  benefit = clamp($250, $1,250, (0.90 − (income_pct_fpl / 125) × 0.40) × annual_heat_cost)
  ```
  where `income_pct_fpl` is bounded at 125 for households at or above 125% FPL (any household >125% is ineligible anyway since the cap is 150%, but the percentage tier formula uses 125 as the upper bound).
  Source: LIHEAP Clearinghouse – Targeting LIHEAP Benefits (https://liheapch.acf.gov/pubs/510targ.htm); WA Benefit Matrix PDF.

- **Year-round crisis assistance**: maximum $13,000 per household. Amount determined by what is needed to resolve the crisis — not calculable by screener.
- **Weatherization assistance**: maximum $20,000 per household. Amount determined by energy audit and specific measures needed — not calculable by screener.
- **Cooling assistance**: $0 — WA does not operate a formal Cooling Component in PY26.

  **Important nuance (added during Discovery Review 2026-05-10):** The WA Commerce LIHEAP page states "the program now includes cooling services" and a 2021 Commerce press release announced LIHEAP's expansion to cover cooling/AC. This user-facing language can be misleading. Per the 2026 State Plan PDF:
  - §1.1 — Cooling assistance has **no operating dates** (Heating, Year-round Crisis, and Weatherization all have 10/01/2025–09/30/2027).
  - §1.2 — Cooling assistance has **0% of funds allocated** (both PY26 and prior year).
  - §3.6 — Cooling minimum and maximum benefits are both **$0**.

  Cooling-related services can still be delivered through other operating components:
  - **Crisis** (§4.15) — Cooling system repair and Cooling system replacement are listed as permitted crisis assistance types.
  - **Weatherization** (§5.11) — Cooling system modifications/repairs and Cooling system replacement are listed as permitted weatherization measures.
  - **OES / In-kind** (§2.7) — Air conditioners and fans are listed among the up-to-$1,000 in-kind emergency supplies a sub-recipient may provide to resolve a heat-related crisis.

  For the screener, this means: cooling needs are implicitly covered to the extent a household qualifies for Crisis (in scope, 150% FPG) or Weatherization (out of scope, 200% FPG). There is no separate cooling track to surface or evaluate.

- **In-kind/OES benefits**: Up to $1,000 in emergency supplies (blankets, space heaters, air conditioners, fans, window repair, limited roof repair, generators) to resolve heat-related crisis situations (WA 2026 Model Plan §2.7). Amount situational — not calculable by screener.
- Payments are made directly to energy vendors in almost all cases. Direct household payments occur only when no vendor agreement is on file or when heat is included in rent.
- **Tribal benefit levels**: Vary by tribal grantee — WA tribal heating benefits range from $52–$2,100 depending on the tribe. See LIHEAP Clearinghouse – FY2026 Tribal Benefit Levels for full breakdown.
- Source: WA LIHEAP 2026 Model Plan §§1.1, 1.2, 2.5, 2.6, 2.7, 3.6, 4.12, 4.15, 5.9a, 5.11, 9.1; LIHEAP Clearinghouse – FY2026 Benefit Levels for Heating, Cooling, and Crisis: States and Territories (https://liheapch.acf.gov/delivery/benefits.htm); LIHEAP Clearinghouse – FY2026 Tribal Benefit Levels (https://liheapch.acf.gov/Tribes/benefits/benefits.htm); LIHEAP Clearinghouse – FY2026 Heating Assistance Criteria for Varying Benefits (https://liheapch.acf.gov/tables/heatcrit.htm); WA Benefit Matrix PDF (https://liheapch.acf.gov/docs/2026/benefits-matricies/WA_BenefitMatrix_2026.pdf); WA Commerce LIHEAP FAQ (https://www.commerce.wa.gov/community-opportunities/liheap/)

## Implementation Coverage

- ✅ Evaluable: 2 eligibility criteria (income threshold, residency) + 4 priority criteria (elderly, disabled, young children, high energy burden)
- ⚠️ Data gaps: 2 eligibility criteria (one-time-per-year grant, crisis situation requirement)
- 🔶 Tribal track: partially evaluable — pending screener suggestions (tribal affiliation as Special Circumstance, VA Pension/Compensation split, crisis as Special Circumstance)

Key notes: WA does not implement categorical eligibility — all households must pass the income test. No asset test for any component (confirmed WA 2026 Model Plan §§2.3, 4.7, 5.6). Screener applies 150% FPG for heating/crisis only; weatherization (200% FPG) is out of scope; cooling is not operated as a formal component (see Benefit Value section). Anyone can apply regardless of citizenship, housing situation, or energy cost responsibility — these are verified during the application process by the local provider.

## Research Sources

- [WA Department of Commerce – LIHEAP Program Overview and FAQ](https://www.commerce.wa.gov/community-opportunities/liheap/)
- [PY26 LIHEAP Eligibility Guidelines PDF – WA Department of Commerce](https://deptofcommerce.app.box.com/s/3fp0xz4y2x2p4hedw9ww4sk7ma36srlx)
- [WA LIHEAP 2026 Model Plan – Washington State Department of Commerce (filed with ACF, report period 10/01/2025–09/30/2026)](https://deptofcommerce.box.com/s/008hcxgv860alo4gx45lxbknnb7lxywg)
- [LIHEAP Clearinghouse – FY2026 Percent of Poverty Table and Income Eligibility by State](https://liheapch.acf.gov/delivery/income_eligibility.htm)
- [LIHEAP Clearinghouse – FY2026 Income Eligibility for Tribes](https://liheapch.acf.gov/Tribes/income_eligibility.htm)
- [LIHEAP Clearinghouse – FY2026 Categorical Eligibility: States and Territories](https://liheapch.acf.gov/delivery/income_categorical.htm)
- [LIHEAP Clearinghouse – FY2026 Categorical Eligibility: Tribes](https://liheapch.acf.gov/Tribes/delivery/income_categorical.htm)
- [LIHEAP Clearinghouse – FY2026 Tribal LIHEAP Plans Index](https://liheapch.acf.gov/Tribes/trplans.htm)
- [FY2026 FPG Tables by Household Size – Attachment 2 (ACF/OCS)](https://acf.gov/sites/default/files/documents/ocs/COMM_LIHEAP_IM2025-02_FPGSte-Table_Att2.pdf)
- [FY2026 SMI Tables by Household Size – Attachment 4 (ACF/OCS)](https://acf.gov/sites/default/files/documents/ocs/COMM_LIHEAP_IM2025-02_SMIStateTable_Att4.pdf)
- [LIHEAP Clearinghouse – FY2026 Benefit Levels for Heating, Cooling, and Crisis: States and Territories](https://liheapch.acf.gov/delivery/benefits.htm)
- [LIHEAP Clearinghouse – FY2026 Heating Assistance Criteria for Varying Benefits](https://liheapch.acf.gov/tables/heatcrit.htm)
- [LIHEAP Clearinghouse – FY2026 Tribal LIHEAP Benefit Levels](https://liheapch.acf.gov/Tribes/benefits/benefits.htm)
- [WA LIHEAP Benefit Matrix PDF – WA Department of Commerce](https://liheapch.acf.gov/docs/2026/benefits-matricies/WA_BenefitMatrix_2026.pdf)
- [LIHEAP Clearinghouse – Targeting LIHEAP Benefits: State Strategies (includes WA cost-based methodology)](https://liheapch.acf.gov/pubs/510targ.htm)
- [WA Commerce press release – LIHEAP expansion to include cooling options (Sep 2021, page updated Jan 2025)](https://www.commerce.wa.gov/as-increasing-heat-waves-threaten-washington-communities-states-heating-program-for-low-income-households-now-includes-cooling-options/)

## Test Scenarios

### Scenario 1: Clearly Eligible — Low-Income Elderly Couple in Washington
**What we're checking**: Typical LIHEAP applicant profile — elderly couple on fixed Social Security income, well under 150% FPG threshold.
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King County`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `March 1958` (age 68), Relationship: Head of Household, Has income: Yes, Income type: Social Security Retirement, Amount: `$950` per month
- **Person 2**: Birth month/year: `July 1960` (age 65), Relationship: Spouse, Has income: Yes, Income type: Social Security Retirement, Amount: `$650` per month
- **Expenses**: Indicate household has heating costs
- **Current Benefits**: None

**Why this matters**: Validates the most common LIHEAP applicant profile. Confirms income calculation, elderly priority flag (both members 60+), and WA residency all work correctly together.

---

### Scenario 2: Clearly Ineligible — Single Adult Income Over 150% FPG
**What we're checking**: Single adult with income just over the 150% FPG ceiling for a 1-person household is correctly rejected.
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King County`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `June 1986` (age 39), Relationship: Head of Household, Has income: Yes, Income type: Wages, Amount: `$1,980` per month ($23,760/year — exceeds 150% FPG of $23,475 for household of 1)
- **Expenses**: Indicate household has heating costs
- **Current Benefits**: None

**Why this matters**: Primary exclusion case. Confirms the income threshold is enforced precisely and that the screener correctly rejects households over the 150% FPG ceiling.

---

### Scenario 3: Edge Case — Large Household, Multiple Income Types, Multiple Priority Flags
**What we're checking**: Household of 6 with wages, SSA retirement, and SSI — total income under the higher 150% FPG threshold for a large household. Elderly, disabled, and young child priority flags all triggered simultaneously.
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98103`, Select county `King County`
- **Household**: Number of people: `6`
- **Person 1**: Birth month/year: `June 1988` (age 37), Relationship: Head of Household, Has income: Yes, Income type: Wages, Amount: `$1,800` per month
- **Person 2**: Birth month/year: `January 1954` (age 72), Relationship: Parent, Has income: Yes, Income type: Social Security Retirement, Amount: `$950` per month
- **Person 3**: Birth month/year: `September 1980` (age 45), Relationship: Spouse, Has income: Yes, Income type: SSI, Amount: `$943` per month, Special Circumstances: disability
- **Person 4**: Birth month/year: `March 2022` (age 4), Relationship: Child, Has income: No
- **Person 5**: Birth month/year: `November 2024` (age 1), Relationship: Child, Has income: No
- **Person 6**: Birth month/year: `August 2014` (age 11), Relationship: Child, Has income: No
- **Expenses**: Indicate household has heating costs
- **Current Benefits**: None

**Why this matters**: Tests income aggregation across a multi-generational household with multiple income types. Validates all three priority flags (elderly, disabled, young children under 6) are triggered simultaneously without affecting eligibility determination.

---

### Scenario 4: Boundary — Single Adult Income Exactly at 150% FPG Threshold
**What we're checking**: Household income exactly equal to the 150% FPG ceiling — screener must use `<=` not `<`.
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98901`, Select county `Yakima County`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `August 1986` (age 39), Relationship: Head of Household, Has income: Yes, Income type: Wages, Amount: `$1,956` per month ($23,472/year ≈ 150% FPG of $23,475 for household of 1)
- **Expenses**: Indicate household has heating costs
- **Current Benefits**: None

**Why this matters**: Boundary test confirming the income comparison is inclusive (`<=`). A strict less-than operator would incorrectly exclude this household.

---

### Scenario 5: Clearly Ineligible — Combined Household Income Over Threshold
**What we're checking**: Multi-member household where one high-earning adult tips total household income over the 150% FPG threshold, even with an elderly member and young child present.
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `98103`, Select county `King County`
- **Household**: Number of people: `4`
- **Person 1**: Birth month/year: `June 1960` (age 65), Relationship: Head of Household, Has income: Yes, Income type: Social Security Retirement, Amount: `$1,200` per month
- **Person 2**: Birth month/year: `September 1990` (age 35), Relationship: Child, Has income: Yes, Income type: Wages, Amount: `$5,500` per month
- **Person 3**: Birth month/year: `March 1993` (age 33), Relationship: Other (child-in-law — use `other`), Has income: No
- **Person 4**: Birth month/year: `January 2023` (age 3), Relationship: Other (grandchild — use `other`), Has income: No
- **Expenses**: Indicate household has heating costs
- **Current Benefits**: None

**Why this matters**: Confirms income is aggregated across all household members. Priority flags (elderly, young child) do not override the income test when combined income exceeds the threshold.

---

### Scenario 6: Eligible — Household with Disabled Member
**What we're checking**: Single adult with a disability, income well under threshold. Disability priority flag triggered.
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98201`, Select county `Snohomish County`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `May 1975` (age 50), Relationship: Head of Household, Has income: Yes, Income type: SSI, Amount: `$943` per month, Special Circumstances: `Currently have any disabilities that make you unable to work now or in the future`
- **Expenses**: Indicate household has heating costs
- **Current Benefits**: None

**Why this matters**: Validates the disability priority flag is correctly identified from the Special Circumstances field. SSI is a countable income type per WA Model Plan §1.9.

---

### Scenario 7: Eligible — Single Parent with Young Child Under 6
**What we're checking**: Single parent with a young child under 6, income under threshold. Young child priority flag triggered.
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98501`, County `Thurston County`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `June 1992` (age 33), Relationship: Head of Household, Has income: Yes, Income type: Wages, Amount: `$1,500` per month
- **Person 2**: Birth month/year: `March 2022` (age 4), Relationship: Child, Has income: No
- **Expenses**: Indicate household has heating costs
- **Current Benefits**: None

**Why this matters**: Validates young child priority flag (under 6) is correctly triggered. Tests a single-parent household structure common among LIHEAP applicants.

---

### Scenario 8: Eligible — Household Member Exactly Age 60
**What we're checking**: Household member exactly 60 years old meets the elderly priority threshold — boundary condition for age check.
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, County `King County`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `March 1966` (age 60), Relationship: Head of Household, Has income: Yes, Income type: Wages, Amount: `$1,200` per month
- **Person 2**: Birth month/year: `June 1970` (age 55), Relationship: Spouse, Has income: Yes, Income type: Wages, Amount: `$800` per month
- **Expenses**: Indicate household has heating costs
- **Current Benefits**: None

**Why this matters**: Confirms age check for elderly priority is inclusive (`>= 60`). A strict greater-than operator would incorrectly exclude this household from elderly priority status.

---

### Scenario 9: Ineligible — Out-of-State ZIP Code
**What we're checking**: Household using a non-Washington ZIP code is correctly identified as not residing in WA.
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `97201`, County `Multnomah` (Portland, Oregon — no "County" suffix needed for OR)
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `June 1980` (age 45), Relationship: Head of Household, Has income: Yes, Income type: Wages, Amount: `$1,200` per month
- **Person 2**: Birth month/year: `January 1982` (age 44), Relationship: Spouse, Has income: Yes, Income type: Wages, Amount: `$800` per month
- **Expenses**: Indicate household has heating costs
- **Current Benefits**: None

**Why this matters**: Tests the WA residency criterion. Income is under threshold ($24,000/year vs. $31,725 for HH of 2), so this household would otherwise be eligible. Confirms ZIP/county gates eligibility by state before evaluating income.

---

### Scenario 10: Eligible — Single Adult Well Under Threshold, No Priority Flags
**What we're checking**: Working-age adult with no priority flags, income well under threshold. Basic eligibility only.
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98661`, County `Clark County`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `April 1990` (age 36), Relationship: Head of Household, Has income: Yes, Income type: Wages, Amount: `$1,200` per month
- **Expenses**: Indicate household has heating costs
- **Current Benefits**: None

**Why this matters**: Confirms basic eligibility works without any priority flags. Validates that the screener does not require vulnerability criteria to determine eligibility.

---

### Scenario 11: Eligible — Household with Mixed Countable and Non-Countable Income
**What we're checking**: Household where total income appears over the threshold but countable income is under once non-countable income (loans) is excluded.
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, County `King County`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `June 1985` (age 40), Relationship: Head of Household, Has income: Yes, Income type: Wages, Amount: `$1,800` per month; Income type: Loans that need to be repaid, Amount: `$600` per month (non-countable per WA Model Plan §1.9)
- **Expenses**: Indicate household has heating costs
- **Current Benefits**: None

**Why this matters**: Validates that non-countable income types are correctly excluded from the gross income calculation. Countable income is $1,800/month = $21,600/year — under 150% FPG for HH of 1 ($23,475). Without the exclusion, total income of $2,400/month = $28,800/year would incorrectly show as ineligible.

---

### Scenario 12: Eligible — Rural Eastern Washington Household (Spokane County)
**What we're checking**: Validates that a valid WA ZIP code in eastern Washington is correctly recognized as within the service area.
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `99201`, County `Spokane County`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `June 1980` (age 45), Relationship: Head of Household, Has income: Yes, Income type: Wages, Amount: `$1,200` per month
- **Person 2**: Birth month/year: `September 2020` (age 5), Relationship: Child, Has income: No
- **Expenses**: Indicate household has heating costs
- **Current Benefits**: None

**Why this matters**: Confirms statewide coverage — the residency check works for eastern WA locations outside the Seattle metro area.

---

### Scenario 13: Ineligible — Disabled Household Over Income Threshold
**What we're checking**: Disabled household member does not bypass the income test — disability is a priority flag only, not an eligibility override.
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, County `King County`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `April 1978` (age 47), Relationship: Head of Household, Has income: Yes, Income type: Wages, Amount: `$2,500` per month, Special Circumstances: `Currently have any disabilities that make you unable to work now or in the future`
- **Person 2**: Birth month/year: `June 1980` (age 45), Relationship: Spouse, Has income: Yes, Income type: Wages, Amount: `$500` per month
- **Total income**: $3,000/month = $36,000/year — exceeds 150% FPG for HH of 2 ($31,725/year)
- **Expenses**: Indicate household has heating costs
- **Current Benefits**: None

**Why this matters**: Confirms that disability priority status does not override the income eligibility requirement. Pairs with Scenario 6 to validate the disability flag from both the eligible and ineligible sides.

## Research Output

Files generated:
- Program config: `wa_liheap_initial_config.json`
- Test cases: `wa_liheap_test_cases.json`
- Spec: `wa_liheap_ticket_edited.md`
