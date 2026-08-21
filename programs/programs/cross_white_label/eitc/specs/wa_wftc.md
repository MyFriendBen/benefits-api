# Washington Working Families Tax Credit (WFTC) — Implementation Spec

**Program:** `wa_wftc`
**State:** Washington
**White Label:** `wa`
**Research Date:** 2026-04-26

---
## Eligibility Criteria

1. **Have a Washington State home address at the time of screening.**
- Screener fields: `zipcode`, `county` 
- Note: For Married Filing Jointly, only the primary applicant must meet this requirement.
- Source: RCW 82.08.0206(2)(g); workingfamiliescredit.wa.gov/eligibility

2. **Have at least $1 of earned income during the tax year.**
- Screener fields: `has_income`, `income_streams`
- Note: Must have non-zero earned income (wages, tips, or net self-employment earnings). Interest, dividends, social security, pensions, unemployment, or alimony do not count as earned income. Investment income cannot exceed $11,600 for the tax year. 
- Source: RCW 82.08.0206; IRS: Earned Income and EITC Tables 

3. **Income within EITC/WFTC Limits (2025/2026 Tax Year)**
- Screener fields: `household_size`, `filing_status`,`IncomeStream`
- Note: Thresholds vary by filing status and number of qualifying children. Thresholds for tax year 2025 (Single/HoH → Married Filing Jointly): 0 children: $19,104 → $26,214; 1 child: $50,434 → $57,554; 2 children: $57,310 → $64,430; 3+ children: $61,555 → $68,675. Married Filing Separately is not eligible for EITC/WFTC unless IRS separated-spouse exceptions apply. 
- Source: RCW 82.08.0206(1)(b); IRS Rev. Proc. 2024-40; workingfamiliescredit.wa.gov/eligibility 

4. **Must be between ages 25 and 64 (inclusive) OR have at least one qualifying child (under 19, or under 24 if a full-time student).**
- Screener: `HouseholdMember.age`,`HouseholdMember.relationship` 
- Note: Qualifying child definition per EITC rules is that the relationship must be; son, daughter, adopted child, foster child, sibling, or descendant of any of these. The child must also be under the age of 19 at the end of the year; OR under 24 and a full-time student; OR permanently and totally disabled (any age)
- Source: RCW 82.08.0206; workingfamiliescredit.wa.gov/eligibility — Who is eligible?; IRS: Qualifying Child Rules 

5. **Filed (or be eligible to file) a federal tax return for the applicable tax year.⚠️ data gap**
- Screener: `last_tax_filing_year`
- Note: The screener has 'last_tax_filing_year' field but this captures when they last filed, not whether they will file for the current year. Filing a return is a procedural requirement that cannot be fully evaluated at screening time.
- Source: RCW 82.08.0206(1); workingfamiliescredit.wa.gov/eligibility - Who is eligible for the Working Families Tax Credit?
- Impact: Medium 

6. **Cannot be claimed as a dependent on another person's tax return ⚠️ data gap**
- Screener: null
- Note: The screener does not capture whether the applicant is claimed as a dependent on someone else's return. This primarily affects young adults (18-24) who may still be claimed by parents.
- Source: IRS Publication 596; workingfamiliescredit.wa.gov/eligibility 
- Impact: Medium

---

## Priority Criteria

None. WFTC is a non-competitive entitlement program. 

---

## Benefit Value

- **2025 maximum credit amounts:** $335 for 0 qualifying children; $660 for 1 child; $995 for 2 children; $1,330 for 3 or more children. 
- **Minimum credit:** $50 for any eligible filer, regardless of income or children. 
- Citable source: RCW 82.08.0206; workingfamiliescredit.wa.gov/eligibility

**Calculator methodology:** (Max Credit) - (Phase-out Reduction). If result < 50, return 50. 

---

## Test Scenarios

All 9 scenarios below were approved.  

---

**Scenario 1: Married couple, two qualifying children, moderate earned income — Eligible (Golden Path)**
- What we're checking: Clearly eligible household meets all criteria: WA residency, earned income within EITC limits for 2 children, qualifying children under 19, filing jointly
- Expected: Eligible, value: 995

**Steps**:

Location: ZIP 98103, county King
Household size: 4
Person 1 (Head of Household): Birth June 1988 (age 37), earned income: Yes, monthly wages $3,200, filing status: Married Filing Jointly
Person 2 (Spouse): Birth September 1990 (age 35), earned income: Yes, monthly wages $1,500
Person 3 (Child): Birth March 2016 (age 10)
Person 4 (Child): Birth November 2019 (age 6)

**Why this matters**: Confirms the standard eligible household across all four core criteria simultaneously.

---

**Scenario 2: Single filer, no children, income just above limit — Ineligible (Primary Exclusion)**
- What we're checking: A single filer with no qualifying children whose earned income is $1/month above the $19,104 annual EITC limit for 0 children is correctly denied.
- Expected: Not eligible, value: 0

**Steps**:

Location: ZIP 98103, county King
Household size: 1
Person 1 (Head of Household): Birth June 1991 (age 34), filing status: Single, earned income: Yes, monthly wages $1,593 


**Why this matters**: Tests the over-income cutoff for the childless tier — the most common exclusion reason for single filers.

---

**Scenario 3: Single filer, no children, age 24 — Ineligible (Age Floor)**
- What we're checking: A filer with no qualifying children who is age 24 is below the minimum age of 25 and should be screened out.
- Expected: Not eligible, value: 0

**Steps**:

Location: ZIP 98101, county King
Household size: 1
Person 1 (Head of Household): Birth May 2002 (age 24), filing status: Single, earned income: Yes, monthly wages $1,200

**Why this matters**: Verifies the 25-year minimum age gate for childless filers from the ineligible side.

---

**Scenario 4: Already Receiving Working Families Tax Credit - Exclusion Check**
- What we're checking: Whether a person who already receives the Working Families Tax Credit is flagged as ineligible or shown a different message indicating they already have the benefit
- Expected: Not eligible, value: 0

**Steps**:

Location: Enter ZIP code 98103, Select county King
Household: Number of people: 3
Person 1: Birth month/year: June 1991 (age 34), Relationship: Head of Household, Has earned income: Yes, Monthly employment income: $2,500
Person 2: Birth month/year: September 2016 (age 9), Relationship: Child, No income
Person 3: Birth month/year: March 2020 (age 6), Relationship: Child, No income
Current Benefits: Select that the household already receives the Working Families Tax Credit

**Why this matters**: Verifies that the screen will not present program to applicant who already receives the tax credit. 

---

**Scenario 5: Married couple, three qualifying children, income $1 above limit — Ineligible (Income Ceiling)**
- What we're checking: Validates that a married filing jointly household with 3 qualifying children is correctly denied when earned income exceeds the EITC threshold of $68,675 for tax year 2026 (3+ children, MFJ)
- Expected: Not eligible, value: 0

**Steps**:

Location: ZIP 98103, county King
Household size: 5
Person 1 (Head of Household): Birth June 1988 (age 37), filing status: Married Filing Jointly, earned income: Yes, monthly wages $5,723 (annual ~$68,676)
Person 2 (Spouse): Birth September 1990 (age 35), earned income: No
Person 3 (Child): Birth January 2014 (age 12)
Person 4 (Child): Birth March 2016 (age 10)
Person 5 (Child): Birth July 2019 (age 6)

**Why this matters**: Validates the income ceiling at the highest child-tier threshold.

---

**Scenario 6: Single filer, one qualifying child, income within limit — Eligible (2-Person Household)**
- What we're checking: Validates that a single filer with one qualifying child and earned income below the one-child EITC/WFTC limit is considered eligible.
- Expected: Eligible, value: 335

**Steps**:

Location: ZIP 98103, county King
Household size: 2
Person 1 (Head of Household): Birth June 1990 (age 35), filing status: Single/Head of Household, earned income: Yes, monthly wages $4,000 (annual $48,000, below the $50,434 limit)
Person 2 (Child): Birth September 2016 (age 9)

**Why this matters**: Covers the single-parent + one-child tier, which is a distinct EITC income band. 

---

**Scenario 7: Single filer, no earned income (unearned income only) — Ineligible**
- What we're checking: A filer whose only income is unearned (Social Security retirement) and has no earned income is correctly denied. Earned income of $0 fails Criterion 2. 
- Expected: Not eligible, value: 0

**Steps**:

Location: ZIP 98144, county King
Household size: 1
Person 1 (Head of Household): Birth March 1954 (age 72), filing status: Single, earned income: No, income type: SSRetirement, monthly amount $1,400

**Why this matters**: Confirms that unearned-income-only households are screened out.

---

**Scenario 8: Married couple, three qualifying children, income well within limit — Eligible (Max Child Tier)**
- What we're checking: A married household with 3 qualifying children and combined income well below the $68,675 MFJ + 3-child ceiling is eligible and should receive the maximum credit tier.
- Expected: Eligible, value: 1330

**Steps**:

Location: ZIP 98103, county King
Household size: 5
Person 1 (Head of Household): Birth June 1985 (age 40), filing status: Married Filing Jointly, earned income: Yes, monthly wages $2,500
Person 2 (Spouse): Birth September 1987 (age 38), earned income: Yes, monthly wages $1,500
Person 3 (Child): Birth January 2010 (age 16)
Person 4 (Child): Birth March 2014 (age 12)
Person 5 (Child): Birth July 2019 (age 6)

**Why this matters**: Confirms the 3+ child tier returns the maximum credit amount ($1,330). 

---

**Scenario 9: Single filer, no qualifying children, exactly age 25 - meets minimum age requirement**
- What we're checking: Validates that a filer with no qualifying children who is exactly 25 years old (the minimum age for childless EITC/WFTC eligibility) is considered eligible.
- Expected: Eligible, value: 50

**Steps**:

Location: ZIP 98101, county King
Household size: 1
Person 1 (Head of Household): Birth January 2001 (age 25), filing status: Single, earned income: Yes, monthly wages $1,200

**Why this matters**: Confirms the minimum age requirement and tax credit amount. 