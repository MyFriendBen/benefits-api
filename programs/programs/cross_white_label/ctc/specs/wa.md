# Implement Child Tax Credit (CTC) (WA) Program

## Program Details

- **Program**: Child Tax Credit (CTC)
- **State**: WA (federal program surfaced on WA white label)
- **White Label**: wa
- **Research Date**: 2026-03-31

## Eligibility Criteria

1. **Must have at least one qualifying child under age 17 at end of tax year**
   - Screener fields:
     - `household_members.age`
     - `household_members.relationship`
   - Source: 26 U.S.C. § 24(c)(1); IRS Publication 5811, p.1; IRS CTC Overview

2. **Income phase-out: Credit reduced for MAGI above $200,000 (single/HOH) or $400,000 (married filing jointly). Credit reduced by $50 per $1,000 over threshold. Fully eliminated at $240,000 single / $440,000 MFJ for one child; higher thresholds for more children.**
   - Screener fields:
     - `income (all types via calc_gross_income)`
     - `screen.is_joint()`
   - Source: 26 U.S.C. § 24(b)(1)-(2); IRS Schedule 8812 Instructions, Line 5-14 worksheet; IRS CTC Overview

3. **Must have earned income exceeding $2,500 to receive the refundable portion (Additional Child Tax Credit / ACTC, up to $1,700 per child for TY2025)**
   - Screener fields:
     - `income_streams (category: 'earned')`
   - Source: 26 U.S.C. § 24(d)(1)(B)(i); IRS Schedule 8812 Instructions; IRS Publication 5811

4. **Qualifying child must have lived with the taxpayer for more than half the tax year**
   - Screener fields:
     - `household_members (presence in household)`
   - Source: 26 U.S.C. § 152(c)(1)(B); IRS Publication 5811; IRS CTC Overview

5. **Must file a federal income tax return (Form 1040) with Schedule 8812**
   - Screener fields:
     - `last_tax_filing_year`
   - Source: 26 U.S.C. § 24(a); IRS CTC Overview; IRS Schedule 8812 Instructions

6. **Filing status determines phase-out threshold: $400,000 for Married Filing Jointly; $200,000 for all other filing statuses (Single, Head of Household, Married Filing Separately, Qualifying Surviving Spouse)**
   - Screener fields:
     - `screen.is_joint()`
     - `household_members.relationship`
   - Source: 26 U.S.C. § 24(b)(2); IRS Schedule 8812 Instructions

7. **Qualifying child must have a valid Social Security number (SSN) issued before the due date of the tax return (including extensions)** ⚠️ *data gap*
   - Note: The screener does not collect SSN information for any household member. An ITIN is NOT sufficient for the child — the child must have an SSN valid for employment. Children without SSNs may qualify for the $500 Credit for Other Dependents instead.
   - Source: 26 U.S.C. § 24(h)(7); IRS Publication 5811; IRS CTC Overview
   - Impact: High

8. **Taxpayer must have a valid Social Security number (SSN)** ⚠️ *data gap*
   - Note: **CORRECTION FROM REVIEW** — ITIN is no longer accepted for the taxpayer (parent/filer); an SSN is required. For the refundable ACTC portion, at least one spouse (if MFJ) must have an SSN. The screener does not collect taxpayer identification numbers.
   - Source: 26 U.S.C. § 24(h)(7); IRS Schedule 8812 Instructions
   - Impact: Medium

9. **Qualifying child must be a U.S. citizen, U.S. national, or U.S. resident alien** ⚠️ *data gap*
   - Note: The screener does not collect citizenship or immigration status for household members. Children who are nonresident aliens do not qualify. Primarily affects mixed-status families.
   - Source: 26 U.S.C. § 24(c)(2); 26 U.S.C. § 152(b)(3); IRS Publication 5811
   - Impact: Medium

10. **Qualifying child relationship test: Must be the taxpayer's son, daughter, stepchild, eligible foster child, sibling, or a descendant of any of them (e.g., grandchild, niece, nephew)** ⚠️ *data gap*
    - Note: The screener uses broad relationship categories. A child listed with a 'child' relationship is assumed qualifying, but the screener cannot verify specific biological/legal relationships. Unrelated children (e.g., a friend's child) do NOT qualify.
    - Source: 26 U.S.C. § 152(c)(2); IRS Publication 5811
    - Impact: Medium

11. **Modified Adjusted Gross Income (MAGI) calculation requires specific tax adjustments beyond gross income** ⚠️ *data gap*
    - Note: MAGI equals AGI plus amounts excluded under 26 U.S.C. § 911 (foreign earned income). The screener uses gross income as a proxy, which is a reasonable approximation for most WA filers without significant above-the-line deductions.
    - Source: 26 U.S.C. § 24(b); IRS Schedule 8812 Instructions, Line 5
    - Impact: Medium

12. **Qualifying child must not have provided more than half of their own support during the tax year** ⚠️ *data gap*
    - Note: Not collected by screener. Primarily relevant for older teenagers (15–16) with significant income. Easily met for most children under 17.
    - Source: 26 U.S.C. § 152(c)(1)(D); IRS Publication 5811
    - Impact: Low

13. **Qualifying child must not file a joint return for the tax year** ⚠️ *data gap*
    - Note: Not collected by screener. A rare scenario — would only apply to a married minor filing jointly with their spouse.
    - Source: 26 U.S.C. § 152(c)(1)(E); IRS Publication 5811
    - Impact: Low

14. **Taxpayer must not be excluded from claiming the credit due to prior fraud or reckless disregard of CTC rules (2-year or 10-year ban)** ⚠️ *data gap*
    - Note: Cannot be determined from screener data. Affects a very small number of filers.
    - Source: 26 U.S.C. § 24(g); IRS Publication 4298
    - Impact: Low

## Benefit Value

- **Non-refundable CTC**: Up to **$2,200** per qualifying child (TY2026)
- **Refundable ACTC**: Up to **$1,700** per qualifying child (TY2025/2026)
- Value scales with the number of qualifying children in the household.
- Note: Washington state has no state-level CTC supplement; only the federal credit applies.

## Program Config Corrections (from review)

- `estimated_value`: Use **"Up to $2,200 per child per year"** (not $2,000)
- Document for taxpayer proof of identity: Remove ITIN — **only SSN is accepted** for the taxpayer (filer). Update text to: "Social Security number for the taxpayer"
- Child SSN document remains correct: "Social Security number for each qualifying child"

## Implementation Coverage

- ✅ Evaluable criteria: 6
- ⚠️  Data gaps: 9

The screener can evaluate the core income and age requirements with reasonable accuracy. Child age (under 17) and household composition are well-supported. Income-based criteria use gross income as a proxy for MAGI — an acceptable approximation for most WA filers without significant above-the-line deductions. The most significant gap is the inability to verify the child's SSN (a hard eligibility requirement). Citizenship, relationship type, and taxpayer SSN requirements cannot be verified from screener data. Washington has no state-level CTC, so only federal criteria apply.

## Research Sources

- [IRS Child Tax Credit (CTC) Overview – 26 U.S.C. § 24](https://www.irs.gov/credits-deductions/individuals/child-tax-credit)
- [IRS Schedule 8812 Instructions](https://www.irs.gov/forms-pubs/about-schedule-8812-form-1040)
- [IRS Publication 5811 – Child Tax Credit and Credit for Other Dependents](https://www.irs.gov/pub/irs-pdf/p5811.pdf)
- [IRS Credits for Family, Dependents, and Students – Portal Page](https://www.irs.gov/credits-deductions/family-dependents-and-students-credits)

## Acceptance Criteria

Pat identified these four as the key scenarios to run:

- [ ] Scenario 1 (Married Filing Jointly with Two Young Children - Clearly Eligible): User should be **eligible**
- [ ] Scenario 5 (Single Filer with Income Just Above $200,000 Phase-Out Threshold): User should be **ineligible**
- [ ] Scenario 6 (Child Born in 2026 - Age 0 Newborn): User should be **eligible**
- [ ] Scenario 12 (Mixed Household - Two Qualifying Children, One 17-Year-Old, One Adult Dependent): User should be **eligible**

## Test Scenarios

### Scenario 1: Married Filing Jointly with Two Young Children — Clearly Eligible
**What we're checking**: Typical happy path — married couple with two qualifying children under 17, moderate earned income well below the $400,000 MFJ phase-out threshold, eligible for full CTC of $2,200 per child

**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98103`, Select county `King`
- **Household**: Number of people: `4`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `June 1990` (age 35), Filing status: `Married Filing Jointly`, Has income: Yes, Employment income: `$4,500` per month ($54,000/year)
- **Person 2 (Spouse)**: Relationship: `Spouse`, Birth month/year: `September 1991` (age 34), Has income: Yes, Employment income: `$3,000` per month ($36,000/year)
- **Person 3 (Child)**: Relationship: `Child`, Birth month/year: `January 2018` (age 8), Has income: No
- **Person 4 (Child)**: Relationship: `Child`, Birth month/year: `April 2021` (age 4), Has income: No
- **Current Benefits**: Select `None`

**Why this matters**: The most common CTC scenario. Validates that the screener correctly identifies qualifying children, applies the MFJ phase-out threshold of $400,000, calculates $2,200 per qualifying child, and confirms earned income exceeds the $2,500 minimum for the refundable ACTC.

---

### Scenario 2: Single Filer with One Child Barely Meeting Income and Age Thresholds
**What we're checking**: Minimally eligible scenario — single filer with earned income just above $2,500, one child who is 16 at end of tax year, and income well below the $200,000 phase-out

**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Birth month/year: `June 1990` (age 35), Relationship: `Head of Household`, Has income: Yes, Earned income: `$220` monthly (approximately $2,640/year, just above the $2,500 threshold), Citizenship: US Citizen
- **Person 2 (Child)**: Birth month/year: `December 2009` (age 16, turns 17 in December 2026 — still 16 at end of tax year 2025), Relationship: `Child`, Has income: No
- **Current Benefits**: Select `None`

**Why this matters**: Tests the minimum boundaries simultaneously — earned income barely exceeds the $2,500 refundable threshold, and the child is at the oldest qualifying age (16). Ensures the screener handles edge cases at the lower income bound and upper child age bound.

---

### Scenario 3: Single Filer with Income Just Below $200,000 Phase-Out Threshold
**What we're checking**: Validates that a single filer with MAGI just below $200,000 receives the full CTC without any reduction

**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98103`, Select county `King`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Birth month/year: `June 1988` (age 37), Relationship: `Head of Household`, Has income: Yes, Employment income: `$16,625` per month ($199,500/year), Citizenship: US Citizen
- **Person 2 (Child)**: Birth month/year: `September 2017` (age 8), Relationship: `Child`, Has income: No
- **Current Benefits**: Select `None`

**Why this matters**: Tests the critical boundary just below the $200,000 single-filer phase-out per 26 U.S.C. § 24(b)(2). At $199,500 MAGI the filer should receive the full $2,200 CTC with no reduction.

---

### Scenario 4: Single Filer with Income Exactly at $200,000 Phase-Out Threshold
**What we're checking**: Validates that a single filer with MAGI exactly at $200,000 still receives the full CTC (phase-out starts above the threshold, not at it)

**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Birth month/year: `June 1988` (age 37), Relationship: `Head of Household`, Has income: Yes, Employment income: `$16,667` per month (approximately $200,004/year), Filing status: `Single`
- **Person 2 (Child)**: Birth month/year: `September 2016` (age 9), Relationship: `Child`, Has income: No
- **Current Benefits**: Select `None`

**Why this matters**: Confirms the screener treats $200,000 as the point where reduction starts (not where it has already begun), ensuring the full credit is still available at exactly $200,000.

---

### Scenario 5: Single Filer with Income Just Above $200,000 Phase-Out Threshold — Full Credit Eliminated
**What we're checking**: Validates that a single filer with MAGI of $250,000 has the CTC fully phased out. At $250,000, the $50,000 excess above threshold × 5% = $2,500 reduction, which exceeds the $2,200 credit for one child.

**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Birth month/year: `June 1988` (age 37), Relationship: `Head of Household`, Has income: Yes, Employment income: `$250,000` annually, Citizenship: US Citizen
- **Person 2 (Child)**: Birth month/year: `January 2018` (age 8), Relationship: `Child`, Has income: No
- **Current Benefits**: Select `None`

**Why this matters**: Confirms the phase-out calculation correctly eliminates the CTC. The $50,000 excess × 5% = $2,500 reduction exceeds the $2,200 credit for one child, so the credit phases out to $0.

---

### Scenario 6: Child Born in 2026 — Age 0 (Newborn) at Minimum Age Threshold
**What we're checking**: Validates that a newborn (age 0) is counted as a qualifying child under age 17

**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Birth month/year: `June 1990` (age 35), Relationship: `Head of Household`, Has income: Yes, Earned income: `$4,500` monthly (~$54,000/year), Citizenship: US Citizen
- **Person 2 (Child)**: Birth month/year: `January 2026` (age 0 — newborn), Relationship: `Child`, Has income: No
- **Current Benefits**: Select `None`

**Why this matters**: Confirms that the youngest possible qualifying child (a newborn at age 0) is correctly recognized. Ensures the system does not incorrectly exclude infants born in the current tax year.

---

### Scenario 7: Household with Only a 17-Year-Old Child — ODC Eligible, CTC Ineligible
**What we're checking**: Validates that a 17-year-old does NOT qualify for the $2,200 CTC (must be under 17), but DOES qualify for the $500 Credit for Other Dependents (ODC). The `wa_ctc` program encompasses both the CTC and the ODC, so the household is eligible for $500.

**Expected**: Eligible ($500 — Credit for Other Dependents)

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Birth month/year: `June 1985` (age 40), Relationship: `Head of Household`, Has income: Yes, Earned income: `$55,000` annually, Citizenship: US Citizen
- **Person 2 (Child)**: Birth month/year: `January 2009` (age 17), Relationship: `Child`, Has income: No
- **Current Benefits**: Select `None`

**Why this matters**: The `wa_ctc` program includes the Credit for Other Dependents (ODC) in addition to the CTC. A 17-year-old does not qualify for the $2,200 CTC (26 U.S.C. § 24(c)(1)), but does qualify for the $500 ODC. PolicyEngine correctly returns eligible/$500 for this case. Scenario 12 corroborates this: its $4,900 total = (2 children under 17 × $2,200) + (1 age-17 × $500 ODC).

---

### Scenario 8: Single Filer with 10-Year-Old Child — Age Well Within Qualifying Range
**What we're checking**: Validates that a child squarely in the middle of the qualifying age range (age 10) correctly qualifies

**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98103`, Select county `King`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Birth month/year: `June 1988` (age 37), Relationship: `Head of Household`, Has income: Yes, Employment income: `$55,000` annually, Citizenship: US Citizen
- **Person 2 (Child)**: Birth month/year: `August 2015` (age 10), Relationship: `Child`, Has income: No
- **Current Benefits**: Select `None`

**Why this matters**: Confirms the age logic works for typical school-age children, not only edge cases near the age boundaries.

---

### Scenario 9: Single Filer Already Receiving Child Tax Credit — Exclusion Check
**What we're checking**: Whether the screener correctly handles a household already receiving CTC (should show ineligible or an informational message)

**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `98103`, Select county `King`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Birth month/year: `June 1990` (age 35), Relationship: `Head of Household`, Has income: Yes, Employment income: `$4,500` per month ($54,000/year), Citizenship: US Citizen
- **Person 2 (Child)**: Birth month/year: `September 2018` (age 7), Relationship: `Child`, Has income: No
- **Current Benefits**: Select `Child Tax Credit (CTC)` — indicate the household currently claims CTC on their federal return

**Why this matters**: Users who already receive CTC should not be told to apply again. Tests the exclusion logic for current benefit recipients.

---

### Scenario 10: Single Filer Receiving SNAP — No CTC Exclusion Based on Other Program Participation
**What we're checking**: Validates that receiving SNAP or other assistance does NOT exclude a household from CTC eligibility (CTC has no cross-program exclusion)

**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98103`, Select county `King`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Birth month/year: `June 1990` (age 35), Relationship: `Head of Household`, Has income: Yes, Employment income: `$3,200` per month (~$38,400/year), Citizenship: US Citizen
- **Person 2 (Child)**: Birth month/year: `September 2017` (age 8), Relationship: `Child`, Has income: No
- **Current Benefits**: Select `SNAP`

**Why this matters**: Some programs exclude SNAP recipients; CTC does not. Confirms the screener does not incorrectly apply cross-program exclusion logic to CTC.

---

### Scenario 11: Single Filer with Earned Income Exactly at $2,500 Threshold — No Tax Liability, Not Eligible
**What we're checking**: Tests the boundary condition where earned income is exactly $2,500. At this income level, the refundable ACTC is $0 (15% × ($2,500 − $2,500) = $0) and the standard deduction wipes out all taxable income, so there is no federal tax liability for the non-refundable CTC to offset. The total credit is $0.

**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Birth month/year: `June 1990` (age 35), Relationship: `Head of Household`, Has income: Yes, Earned income: `$2,500` annually ($208.33/month), No other income
- **Person 2 (Child)**: Birth month/year: `January 2018` (age 8), Relationship: `Child`, Has income: No
- **Current Benefits**: Select `None`

**Why this matters**: While $2,500 is the statutory minimum for any refundable ACTC, at exactly $2,500 the refundable portion is $0 and there is no tax liability (the standard deduction of ~$15,700 zeroes out taxable income at this income level). PolicyEngine correctly returns not eligible/$0. To test a scenario where a low-income filer does receive ACTC, use income closer to $20,000/year.

---

### Scenario 12: Mixed Household — Two Qualifying Children, One 17-Year-Old, and One Adult Dependent
**What we're checking**: Validates that in a multi-member household, only children under age 17 qualify for CTC while a 17-year-old and an adult dependent do not

**Expected**: Eligible (two qualifying children under 17 present)

**Steps**:
- **Location**: Enter ZIP code `98103`, Select county `King`
- **Household**: Number of people: `5`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `June 1985` (age 40), Has income: Yes, Earned income: `$5,500` per month ($66,000/year), Citizenship: US Citizen
- **Person 2 (Child — qualifies)**: Relationship: `Child`, Birth month/year: `September 2016` (age 9), Has income: No, Citizenship: US Citizen
- **Person 3 (Child — qualifies)**: Relationship: `Child`, Birth month/year: `January 2022` (age 4), Has income: No, Citizenship: US Citizen
- **Person 4 (Child — does NOT qualify for CTC, qualifies for ODC)**: Relationship: `Child`, Birth month/year: `February 2009` (age 17), Has income: No, Citizenship: US Citizen — 17-year-olds are above the CTC age cutoff but generate a $500 ODC
- **Person 5 (Adult dependent — does NOT qualify)**: Relationship: `Child`, Birth month/year: `November 2005` (age 20), Has income: No, Citizenship: US Citizen — adult, not a qualifying child for CTC
- **Current Benefits**: Select `None`

**Why this matters**: Tests the screener's ability to differentiate between qualifying and non-qualifying household members in a mixed household. Expected value is $4,900 = (2 children under 17 × $2,200) + (1 age-17 × $500 ODC). The 20-year-old generates no credit.

---

### Scenario 13: Large Household with Four Qualifying Children of Varying Ages — All Eligible
**What we're checking**: Validates that multiple qualifying children (ages 2, 6, 10, and 15) each generate a CTC credit, and that the total credit reflects all four qualifying children

**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98103`, Select county `King`
- **Household**: Number of people: `6`
- **Person 1 (Head of Household)**: Birth month/year: `June 1988` (age 37), Relationship: `Head of Household`, Has income: Yes, Gross income: `$5,500` per month (wages), Citizenship: US Citizen
- **Person 2 (Child)**: Birth month/year: `January 2024` (age 2), Relationship: `Child`, Has income: No, Citizenship: US Citizen
- **Person 3 (Child)**: Birth month/year: `August 2019` (age 6), Relationship: `Child`, Has income: No, Citizenship: US Citizen
- **Person 4 (Child)**: Birth month/year: `November 2015` (age 10), Relationship: `Child`, Has income: No, Citizenship: US Citizen
- **Person 5 (Child)**: Birth month/year: `February 2011` (age 15), Relationship: `Child`, Has income: No, Citizenship: US Citizen
- **Person 6 (Grandparent)**: Birth month/year: `September 1960` (age 65), Relationship: `Parent`, Has income: Yes, Gross income: `$1,400` per month (Social Security Retirement), Citizenship: US Citizen
- **Current Benefits**: Select `None`

**Why this matters**: Tests that the screener correctly identifies and counts multiple qualifying children of varying ages while excluding non-qualifying adult members. Ensures the credit amount scales correctly with the number of eligible children.

---

## Source Documentation

- https://www.irs.gov/credits-deductions/individuals/child-tax-credit
- https://www.irs.gov/forms-pubs/about-schedule-8812-form-1040

## JSON Test Cases
File: `validations/management/commands/import_validations/data/wa_ctc.json`

## Generated Program Configuration
File: `programs/management/commands/import_program_config_data/data/wa_ctc_initial_config.json`
