# Implement eitc (KS) Program

## Program Details

- **Program**: eitc
- **State**: KS
- **White Label**: ks
- **Research Date**: 2026-06-03

## Eligibility Criteria

1. **Must have earned income (wages, salaries, self-employment income, etc.)**
   - Screener fields:
     - `IncomeStream.type`
     - `IncomeStream.amount`
   - Source: 26 U.S.C. § 32(a)(1), (c)(2); Kansas Individual Income Tax Booklet Tax Year 2025; Kansas WebFile Help - Earned Income Credit

2. **Adjusted Gross Income (AGI) must be below the income threshold based on number of qualifying children and filing status**
   - Screener fields:
     - `IncomeStream.amount`
     - `IncomeStream.frequency`
     - `household_size`
     - `HouseholdMember.birth_year`
     - `HouseholdMember.birth_month`
     - `HouseholdMember.relationship`
   - Source: 26 U.S.C. § 32(a)(2), (b); IRS Rev. Proc. for Tax Year 2025 inflation adjustments

3. **Number of qualifying children determines credit amount tier (0, 1, 2, or 3+)**
   - Screener fields:
     - `HouseholdMember.birth_year`
     - `HouseholdMember.birth_month`
     - `HouseholdMember.relationship`
   - Source: 26 U.S.C. § 32(b)(1), (c)(3)

4. **If claiming EITC with no qualifying children, taxpayer must be at least age 25 and under age 65**
   - Screener fields:
     - `HouseholdMember.birth_year`
     - `HouseholdMember.birth_month`
     - `HouseholdMember.relationship`
   - Source: 26 U.S.C. § 32(c)(1)(A)(ii)(II)
   - Note: The ARPA (2021) temporarily removed the upper age limit for TY2021 only. For TY2022 onward (including TY2025), the upper age limit of 65 applies and the minimum age remains 25.

5. **Filing status cannot be Married Filing Separately**
   - Screener fields:
     - `screen.is_joint()`
   - Source: 26 U.S.C. § 32(d)

6. **Must file a Kansas individual income tax return (Form K-40)** ⚠️ *data gap*
   - Note: The screener collects `last_tax_filing_year` as a proxy, but cannot confirm Kansas-specific filing. Treat as satisfied if `last_tax_filing_year` is present.
   - Screener fields:
     - `last_tax_filing_year`
   - Source: K.S.A. 79-32,205; Kansas Individual Income Tax Booklet Tax Year 2025

7. **Must be a Kansas resident (full-year or part-year) or have Kansas-source income**
   - Screener fields:
     - `zipcode`
     - `county`
   - Source: K.S.A. 79-32,205; Kansas Individual Income Tax Booklet Tax Year 2025 - General Information

8. **Must have a valid Social Security Number (SSN) for the taxpayer, spouse (if filing jointly), and each qualifying child** ⚠️ *data gap*
   - Note: The screener does not collect SSN information. ITINs do not qualify. This is a critical requirement that excludes undocumented immigrants and certain nonresident aliens.
   - Source: 26 U.S.C. § 32(c)(1)(E), (c)(3)(D)
   - Impact: ImpactLevel.HIGH

9. **Must be a U.S. citizen or resident alien for the entire tax year (or married to one and filing jointly)** ⚠️ *data gap*
   - Note: The screener does not collect citizenship or immigration status. Nonresident aliens are generally ineligible unless married to a U.S. citizen/resident and filing jointly.
   - Source: 26 U.S.C. § 32(c)(1)(D)
   - Impact: ImpactLevel.HIGH

10. **Investment income must not exceed the threshold ($11,600 for TY2024, indexed for TY2025)** ⚠️ *data gap*
    - Note: Investment income includes interest, dividends, capital gains, rental income, and royalties. While the screener collects some income types, it may not separately identify all investment income categories with sufficient granularity to apply this test precisely. The threshold is indexed annually.
    - Source: 26 U.S.C. § 32(i)
    - Impact: ImpactLevel.MEDIUM

11. **Cannot be a qualifying child of another taxpayer** ⚠️ *data gap*
    - Note: The screener cannot determine if the head of household is claimed as a dependent on another person's tax return. This primarily affects young adults (under 24) who may still be dependents of their parents.
    - Source: 26 U.S.C. § 32(c)(1)(A)(ii)(I)
    - Impact: ImpactLevel.MEDIUM

12. **Cannot file Form 2555 (Foreign Earned Income Exclusion)** ⚠️ *data gap*
    - Note: The screener does not collect information about foreign earned income or Form 2555 filing. This affects U.S. citizens/residents working abroad.
    - Source: 26 U.S.C. § 32(c)(1)(A)(i)
    - Impact: ImpactLevel.LOW

13. **Qualifying child must have lived with the taxpayer in the U.S. for more than half the year** ⚠️ *data gap*
    - Note: The screener collects household members but cannot verify residency duration or whether the child lived with the taxpayer for more than half the year. The screener assumes current household composition reflects the tax year.
    - Source: 26 U.S.C. § 32(c)(3)(A) referencing § 152(c)(1)(B); 26 U.S.C. § 32(c)(3)(C)
    - Impact: ImpactLevel.MEDIUM

14. **Qualifying child cannot file a joint return (unless only to claim a refund)** ⚠️ *data gap*
    - Note: The screener cannot determine if a qualifying child filed a joint return with their spouse.
    - Source: 26 U.S.C. § 152(c)(1)(E)
    - Impact: ImpactLevel.LOW

15. **If claiming without qualifying children, taxpayer's principal place of abode must be in the United States for more than half the tax year** ⚠️ *data gap*
    - Note: While the screener collects a current zipcode, it cannot verify that the taxpayer lived in the U.S. for more than half the year. For Kansas residents this is generally satisfied but cannot be confirmed.
    - Source: 26 U.S.C. § 32(c)(1)(A)(ii)(II)
    - Impact: ImpactLevel.LOW

## Benefit Value

The Kansas EITC equals **17% of the federal EITC amount** for tax year 2025, per K.S.A. § 79-32,205 (effective tax year 2013 and all tax years thereafter).

> ⚠️ **Rate correction:** The original discovery artifact stated 25%. The correct statutory rate is **17%** per K.S.A. § 79-32,205(a). No legislation has changed this rate since 2013. The 25% figure is likely a confusion with the Kansas Child and Dependent Care Credit (CDCC), which is 25% of the federal CDCC.

The credit has two components:
- **Refundable portion**: If the credit exceeds the taxpayer's Kansas income tax liability, the excess is refunded per K.S.A. § 79-32,205(b).
- **Non-refundable portion**: The remaining credit reduces Kansas income tax owed to zero.

The PE calculator computes both components (`ks_refundable_eitc`, `ks_nonrefundable_eitc`, `ks_total_eitc`). The annual benefit value is the total KS EITC — the sum of refundable and non-refundable portions.

For reference, the federal EITC maximums for TY2025 (on which the KS credit is based) are approximately:
- 0 qualifying children: ~$632
- 1 qualifying child: ~$4,213
- 2 qualifying children: ~$6,960
- 3+ qualifying children: ~$7,830

KS EITC = 17% of federal EITC = approximately:
- 0 qualifying children: ~$107
- 1 qualifying child: ~$716
- 2 qualifying children: ~$1,183
- 3+ qualifying children: ~$1,331

All values should be expressed as **annual** amounts. The PE calculator will compute exact values based on each household's specific income and family composition.

Source: K.S.A. § 79-32,205 (Justia, verified current to Jan 1 2025); ITEP State EITC report (Sept 2025)

## Implementation Coverage

- ✅ Evaluable criteria: 6
- ⚠️  Data gaps: 9

6 criteria can be at least partially evaluated with current screener fields (criteria 1–5, 7), and 9 criteria cannot be evaluated (criteria 6, 8–15). The core eligibility determination (earned income, income thresholds, number of qualifying children, age requirements, filing status, Kansas residency) can be reasonably approximated using available screener fields. The most significant gaps are citizenship/immigration status and qualifying child residency, which are high-impact requirements that cannot be assessed. The Kansas EITC is fundamentally a piggyback credit on the federal EITC (17% of federal amount per K.S.A. § 79-32,205), so all federal EITC eligibility criteria apply in addition to Kansas filing requirements.

## Research Sources

- [Kansas Senate Assessment & Taxation Committee Testimony on EITC (March 17, 2017)](https://kslegislature.gov/li_2018/b2017_18/committees/ctte_s_assess_tax_1/documents/testimony/20170317_30.pdf)
- [Kansas Department of Revenue WebFile Help - Earned Income Credit Entry Instructions](https://www.kansas.gov/kdor/webfile/help/modal-earned-income-credit.html)
- [Kansas Individual Income Tax Booklet - Tax Year 2025 (K.S.A. 79-32,100 et seq.)](https://www.ksrevenue.gov/incomebook25.html)
- [Kansas Individual Income Tax Booklet - Tax Year 2025 (PDF Version)](https://www.ksrevenue.gov/pdf/ip25.pdf)
- [Kansas 2025 Income Tax Booklet - Important Information (What's New for Tax Year 2025)](https://www.ksrevenue.gov/incomebook25.html#0)
- [Kansas 2025 Income Tax Booklet - General Information (Filing Requirements & Residency)](https://www.ksrevenue.gov/incomebook25.html#1)
- [Kansas Form K-40 - Individual Income Tax Return (Tax Year 2025)](https://www.ksrevenue.gov/pdf/k-4025.pdf)
- [Kansas Form K-40 Line-by-Line Instructions (Tax Year 2025) - Including EITC at Line 11](https://www.ksrevenue.gov/incomebook25.html#2)
- [Kansas Schedule S - Supplemental Schedule (Tax Year 2025)](https://www.ksrevenue.gov/pdf/schs25.pdf)
- [Kansas Schedule S Instructions (Tax Year 2025) - Income Modifications & Credits](https://www.ksrevenue.gov/incomebook25.html#3)

## Test Scenarios

### Scenario 1: Single Parent with Two Qualifying Children - Clearly Eligible
**What we're checking**: Verifies that a typical Kansas resident with earned income, two qualifying children, and income well below the EITC threshold qualifies for the Kansas EITC (17% of federal EITC)
**Expected**: Eligible — $1,050/year (federal EITC $6,173.55 × 17%)

**Steps**:
- **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
- **Household**: Number of people: `3`
- **Person 1**: Birth month/year: `March 1991` (age 35), Relationship: Head of Household, Has earned income: Yes, Annual wages/salary: `$28,000`, Filed Kansas tax return last year: Yes (last_tax_filing_year: 2025)
- **Person 2**: Birth month/year: `September 2016` (age 9), Relationship: Child
- **Person 3**: Birth month/year: `January 2020` (age 6), Relationship: Child

**Why this matters**: Golden path eligible case — working single parent, two qualifying children, moderate earned income, clear of all evaluable criteria. Establishes the baseline before testing boundaries.

---

### Scenario 2: Married Couple Filing Separately - Not Eligible Due to Filing Status
**What we're checking**: Validates that a married couple who files separately (not jointly) is excluded from EITC regardless of income or qualifying children
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
- **Household**: Number of people: `4`
- **Person 1**: Birth month/year: `June 1988` (age 37), Relationship: Head of Household, Has earned income: Yes, Annual wages/salary: `$32,000`, Filed Kansas tax return last year: Yes
- **Person 2**: Birth month/year: `March 1989` (age 36), Relationship: Spouse, Has earned income: No
- **Person 3**: Birth month/year: `May 2016` (age 9), Relationship: Child
- **Person 4**: Birth month/year: `October 2019` (age 6), Relationship: Child
- **Filing status**: Married Filing Separately (`screen.is_joint()` = false)

**Why this matters**: 26 U.S.C. § 32(d) is a hard categorical exclusion — MFS filers cannot claim EITC regardless of income, children, or residency. This is the only ineligible case for criterion 5.

---

### Scenario 3: Married Couple with Four Qualifying Children - Income Just Below MFJ AGI Limit
**What we're checking**: Validates that a married-filing-jointly household with income just below the MFJ AGI limit for 3+ qualifying children is correctly identified as eligible
**Expected**: Eligible — $4/year (boundary test; income is $100 below limit, federal EITC $21.09, KS EITC $3.58 → $4 — this scenario tests eligibility determination, not calculator value)

**Steps**:
- **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
- **Household**: Number of people: `6`
- **Person 1**: Birth month/year: `January 1988` (age 38), Relationship: Head of Household, Has earned income: Yes, Annual wages/salary: `$68,575` (monthly ~$5,715), Filed Kansas tax return last year: Yes
- **Person 2**: Birth month/year: `April 1990` (age 36), Relationship: Spouse, Has earned income: No
- **Person 3**: Birth month/year: `September 2012` (age 13), Relationship: Child
- **Person 4**: Birth month/year: `March 2015` (age 11), Relationship: Child
- **Person 5**: Birth month/year: `November 2018` (age 7), Relationship: Child
- **Person 6**: Birth month/year: `June 2022` (age 4), Relationship: Child

**Why this matters**: Tests the upper income boundary for the 3+ children tier on a MFJ return. The TY2025 MFJ limit for 3+ qualifying children is approximately $68,675 (verify against IRS Rev. Proc. 2024-61). At $68,575 the household is just $100 below that threshold.

---

### Scenario 4: Single Filer with One Qualifying Child - Income Exactly at AGI Limit
**What we're checking**: Validates that a household with income exactly at the EITC AGI threshold for one qualifying child is still eligible (boundary is inclusive)
**Expected**: Eligible — ~$0 (the AGI limit is the point where the phase-out reaches zero; this scenario tests that the screener uses "does not exceed" logic, not calculator output — expected value is $0 at exactly the limit)

**Steps**:
- **Location**: Enter ZIP code `66604`, Select county `Shawnee`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `September 1990` (age 35), Relationship: Head of Household, Has earned income: Yes, Annual wages/salary: `$50,434`, Income frequency: Yearly, Filed Kansas tax return last year: Yes
- **Person 2**: Birth month/year: `January 2016` (age 10), Relationship: Child, Has income: No

**Why this matters**: The TY2025 single/HOH AGI limit for 1 qualifying child is approximately $50,434 (verify against IRS Rev. Proc. 2024-61; TY2024 was $49,084). Confirms the screener uses "at or below" logic per 26 U.S.C. § 32(a)(2).

---

### Scenario 5: Single Filer with No Qualifying Children - Income Just Above AGI Limit
**What we're checking**: Validates that a single childless filer whose income exceeds the 0-children AGI threshold is correctly denied eligibility
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1986` (age 40), Relationship: `headOfHousehold`, Has earned income: Yes, Annual wages/salary: `$19,200` (equivalent to `$1,600` monthly), Filed Kansas tax return last year: Yes (last_tax_filing_year: 2025)

**Why this matters**: The 0-children AGI limit is the lowest of all tiers — approximately $19,104 for single/HOH filers in TY2025 (verify against IRS Rev. Proc. 2024-61). At $19,200, the household is $96 over the limit.

---

### Scenario 6: Single Filer, No Qualifying Children, Age Exactly 25 - Meets Minimum Age Requirement
**What we're checking**: Validates that a taxpayer exactly at the minimum age for childless EITC (25) is eligible
**Expected**: Eligible — $53/year (federal EITC $313.93 × 17% at $15k income, 0 children)

**Steps**:
- **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 2001` (age 25), Relationship: `headOfHousehold`, Has earned income: Yes, Annual wages/salary: `$15,000`, Filed Kansas tax return last year: Yes

**Why this matters**: Confirms the age check uses `>= 25` (not `> 25`) for childless filers per 26 U.S.C. § 32(c)(1)(A)(ii)(II).

---

### Scenario 7: Single Filer, No Qualifying Children, Age 24 - Below Minimum Age Requirement
**What we're checking**: Validates that a taxpayer aged 24 with no qualifying children is not eligible
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `September 2001` (age 24), Relationship: `headOfHousehold`, Has earned income: Yes, Annual wages/salary: `$15,000`, Filed Kansas tax return last year: Yes

**Why this matters**: One year below the minimum age floor — confirms the age criterion is enforced and the boundary is at 25, not 24.

---

### Scenario 8: Single Parent with No Earned Income - Excluded Due to SSI-Only Income
**What we're checking**: Verifies that a household with no earned income (SSI only) is excluded from EITC
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `66604`, Select county `Shawnee`
- **Household**: Number of people: `3`
- **Person 1**: Birth month/year: `February 1988` (age 38), Relationship: Head of Household, Has income: Yes, Income type: SSI only, SSI amount: `$900` monthly, No wages/salaries/self-employment income, Filed Kansas tax return last year: Yes (last_tax_filing_year: 2025)
- **Person 2**: Birth month/year: `September 2016` (age 9), Relationship: Child
- **Person 3**: Birth month/year: `April 2019` (age 7), Relationship: Child

**Why this matters**: EITC requires earned income per 26 U.S.C. § 32(a)(1) and (c)(2). Unearned income (SSI) does not qualify regardless of household size or children.

---

### Scenario 9: Mixed Household - Adult Child Does Not Count Toward Qualifying Child Tier
**What we're checking**: Validates that a 20-year-old household member is not counted as a qualifying child, placing the household in the 1-child tier rather than 2-child tier
**Expected**: Eligible — $314/year (federal EITC $1,846.31 × 17% at $32k income, 1 qualifying child tier)

**Steps**:
- **Location**: Enter ZIP code `66502`, Select county `Riley`
- **Household**: Number of people: `3`
- **Person 1**: Birth month/year: `February 1984` (age 42), Relationship: Head of Household, Has earned income: Yes, Annual wages/salary: `$32,000`, Filed Kansas tax return last year: Yes
- **Person 2**: Birth month/year: `September 2005` (age 20), Relationship: Child, Has earned income: Yes, Annual wages/salary: `$14,000`
- **Person 3**: Birth month/year: `November 2012` (age 13), Relationship: Child, Has earned income: No

**Why this matters**: The 20-year-old does not meet the qualifying child definition under 26 U.S.C. § 32(c)(3) (over 18 and not a full-time student). This tests that the screener assigns the correct child tier based on qualifying children only.

---

### Scenario 10: Two-Adult Household with Both Adults Having Earned Income and Two Qualifying Children
**What we're checking**: Validates that combined household income from two earners is correctly aggregated for AGI eligibility
**Expected**: Eligible — $889/year (federal EITC $5,229.22 × 17% at $39,600 combined income, 2 children, MFJ)

**Steps**:
- **Location**: Enter ZIP code `66502`, Select county `Riley`
- **Household**: Number of people: `4`
- **Person 1**: Birth month/year: `February 1990` (age 36), Relationship: Head of Household, Has earned income: Yes, Monthly wages/salary: `$1,800`, Filed Kansas tax return last year: Yes
- **Person 2**: Birth month/year: `September 1991` (age 34), Relationship: Spouse/Partner, Has earned income: Yes, Monthly wages/salary: `$1,500`
- **Person 3**: Birth month/year: `March 2018` (age 8), Relationship: Child, Has earned income: No
- **Person 4**: Birth month/year: `November 2020` (age 5), Relationship: Child, Has earned income: No

**Why this matters**: Combined income ~$39,600/year, well below the 2-child MFJ threshold. Confirms the screener correctly aggregates income across household members and counts two qualifying children.

---

### Scenario 11: Single Filer, No Qualifying Children, Age Exactly 64 - At Upper Age Boundary
**What we're checking**: Validates that a childless filer at age 64 (one year below the upper limit) is eligible
**Expected**: Eligible — $1/year (federal EITC $7.65 × 17% at $100 income, KS EITC $1.30 → $1; this scenario tests age eligibility, not calculator value)

**Steps**:
- **Location**: Enter ZIP code `66502`, Select county `Riley`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `September 1961` (age 64), Relationship: `headOfHousehold`, Has earned income: Yes, Annual wages/salary: `$100` (minimal), Filed Kansas tax return last year: Yes (last_tax_filing_year: 2025)

**Why this matters**: For TY2025, the upper age limit for childless filers is under 65 (ARPA's removal of this limit expired after TY2021). A 64-year-old is just inside the limit. Confirms the ceiling is enforced as `< 65`, not `<= 65`.

---


## Source Documentation

- https://kslegislature.gov/li_2018/b2017_18/committees/ctte_s_assess_tax_1/documents/testimony/20170317_30.pdf
- https://www.kansas.gov/kdor/webfile/help/modal-earned-income-credit.html
- https://www.ksrevenue.gov/incomebook25.html
