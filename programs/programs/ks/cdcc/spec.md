# Implement CDCC (KS) Program

## Program Details

- **Program**: CDCC
- **State**: KS
- **White Label**: ks
- **Research Date**: 2026-06-02
- **Reviewer Date**: 2026-06-03

## Eligibility Criteria

1. **Must have at least one qualifying dependent: a child under age 13, or a disabled spouse or dependent of any age who is physically or mentally incapable of self-care**
   - Screener fields:
     - `birth_year + birth_month (HouseholdMember)`
     - `relationship (HouseholdMember)`
     - `disabled (HouseholdMember)`
   - Source: IRC § 21(b)(1); K.S.A. 79-32,111 (Kansas adopts federal definitions); Kansas K-40 Instructions - Child and Dependent Care Credit section

2. **Must have earned income (wages, salaries, tips, self-employment income) during the tax year**
   - Screener fields:
     - `has_income (HouseholdMember)`
     - `IncomeStream.type`
   - Source: IRC § 21(d)(1); K.S.A. 79-32,111; Kansas K-40 Instructions

3. **If married, must file a joint return (Married Filing Jointly)**
   - Screener fields:
     - `relationship (HouseholdMember)`
   - Source: IRC § 21(e)(2); K.S.A. 79-32,111; Kansas K-40 Instructions

4. **Must be a Kansas resident or part-year resident who files a Kansas income tax return**
   - Screener fields:
     - `zipcode`
     - `county`
   - Source: K.S.A. 79-32,111; Kansas K-40 Instructions

5. **Must have incurred expenses for the care of a qualifying individual to enable the taxpayer (and spouse, if married) to work or actively look for work**
   - Screener fields:
     - `Expense.type`
   - Source: IRC § 21(a)(1); K.S.A. 79-32,111; Kansas K-40 Instructions

6. **Must have filed or be eligible to file a federal income tax return claiming the federal Child and Dependent Care Credit (Form 2441)**
   - Screener fields:
     - `last_tax_filing_year`
   - Source: K.S.A. 79-32,111; Kansas K-40 Instructions - the Kansas credit is computed as a percentage of the federal credit

7. **The qualifying individual must have lived with the taxpayer for more than half the year**
   - Screener fields:
     - `relationship (HouseholdMember)`
   - Source: IRC § 21(b)(1)(A); K.S.A. 79-32,111

8. **Care provider must not be the taxpayer's spouse, parent of the qualifying child (if under 13), or a dependent claimed on the taxpayer's return, and must not be the taxpayer's child under age 19** ⚠️ *data gap*
   - Note: The screener does not collect information about who provides the care. This is verified at tax filing time.
   - Source: IRC § 21(e)(6); K.S.A. 79-32,111
   - Impact: ImpactLevel.LOW

9. **Full-time student or disabled spouse exception to the earned income requirement — if one spouse is a full-time student or is incapable of self-care, they are deemed to have earned income of $250/month (one qualifying individual) or $500/month (two or more), satisfying the earned-income requirement even with no actual earnings**
    - Screener fields:
      - `student_full_time (HouseholdMember)`
      - `disabled (HouseholdMember)`
    - Source: IRC § 21(d)(2); K.S.A. 79-32,111

## Benefit Value

Calculated by the Policy Engine `ks_cdcc` calculator. The credit is non-refundable and computed as follows:

1. **Federal CDCC amount** is calculated first per IRC § 21. The credit percentage (20%–35%) is determined by the taxpayer's AGI: 35% for AGI ≤ $15,000, decreasing by 1 percentage point per $2,000 (or fraction) above $15,000, with a floor of 20%. This percentage is applied to qualifying care expenses, capped at $3,000 (one qualifying individual) or $6,000 (two or more).

2. **Kansas credit** = 50% of the federal CDCC amount. Per Kansas Tax Notice 24-09 (SB1 §17, amending K.S.A. 79-32,111c), the credit was increased from 25% to a flat 50% of the federal credit for tax year 2024 and all years thereafter — there is no income-based tiering. The credit reduces Kansas income tax liability; it is non-refundable.

**PE variable:** `ks_cdcc`
**Sources:** IRC § 21(a)(2); K.S.A. 79-32,111c; Kansas Department of Revenue Tax Notice 24-09; Kansas K-40 instructions, Line 14

## Implementation Coverage

- ✅ Evaluable criteria: 8
- ⚠️  Data gaps: 1 (Criterion 8 — care-provider identity)

The core eligibility requirements — having a qualifying dependent (child under 13, or a disabled spouse/dependent incapable of self-care), having earned income (including the § 21(d)(2) deemed income for a full-time-student or disabled spouse), Kansas residency, dependent care expenses, filing status, and co-residency — can all be assessed from available screener fields. The one data gap is Criterion 8 (care-provider identity), an administrative requirement verified at tax filing time. The screener provides a strong preliminary eligibility determination for the Kansas CDCC.

## Research Sources

- [Kansas Individual Income Tax Return (K-40) Instructions - Tax Year 2010](https://www.ksrevenue.gov/pdf/k-40inst10.pdf)
- [Kansas Department of Revenue Tax Notice 24-09 - Child Tax Credit and Related Tax Provisions (2024)](https://www.ksrevenue.gov/taxnotices/notice24-09.pdf#search=child%20tax%20credit)

## Acceptance Criteria

Dollar values for the eligible scenarios are PolicyEngine-verified (KS CDCC = 50% of the federal CDCC).

[ ] Scenario 1 (Golden path — single parent, child under 13, earned income, care expenses): User should be **eligible**, value: $540/year
[ ] Scenario 2 (Married filing jointly, child age 12 — boundary condition): User should be **ineligible** (federal CDCC is non-refundable and this household's income tax liability is fully absorbed, leaving $0 of credit capacity)
[ ] Scenario 3 (Zero earned income — only investment income): User should be **ineligible**
[ ] Scenario 4 (Child age 13 — just above qualifying age cutoff): User should be **ineligible**
[ ] Scenario 5 (Married couple, non-working spouse — spouse lacks earned income): User should be **ineligible**
[ ] Scenario 6 (Two working parents, three qualifying children): User should be **eligible**, value: $1,050/year
[ ] Scenario 7 (Child turns 13 mid-year — still 12 at time of screening): User should be **eligible**, value: $570/year
[ ] Scenario 8 (No qualifying dependent — only teenager age 16 in household): User should be **ineligible**
[ ] Scenario 9 (Disabled adult dependent — alternative qualifying individual): User should be **eligible** per IRC § 21, value: $540/year
[ ] Scenario 10 (Disabled spouse with no earned income — deemed-income path): User should be **eligible** per IRC § 21(d)(2), value: $525/year

## Test Scenarios

### Scenario 1: Golden Path — Single Parent with Young Child and Childcare Expenses
**What we're checking**: Typical happy path - single parent with earned income, one young child, childcare expenses, Kansas resident, recently filed taxes
**Expected**: Eligible, value: $540/year

**Steps**:
- **Location**: Enter ZIP code `66044`, Select county `Douglas`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `March 1991` (age 35), Relationship: Head of Household, Has earned income: Yes, Employment income: `$3,500` per month, Filing status: Single / Head of Household, Last tax filing year: `2025`, Citizenship: US Citizen
- **Person 2**: Birth month/year: `September 2023` (age 2), Relationship: Child, Lives with head of household: Yes
- **Expenses**: Has childcare expenses: Yes, Monthly childcare cost: `$800`

**Why this matters**: This is the most straightforward eligible scenario — a single working parent in Kansas with a young child under 13, documented childcare expenses, earned income, and a recent tax filing. All seven evaluable eligibility criteria are clearly satisfied.

---

### Scenario 2: Married Filing Jointly — Child Age 12 Boundary Condition
**What we're checking**: Married couple both with earned income, filing jointly, child just under the age 13 cutoff. Tests criterion 1 (age boundary) and criterion 3 (joint filing) together.
**Expected**: Ineligible — at $22,800 MFJ income the household's federal income tax liability is fully absorbed by other credits, leaving $0 of capacity for the non-refundable CDCC, so the KS credit ($0) is $0. (The age-boundary and joint-filing eligibility logic is still exercised; only the dollar value resolves to $0.)

**Steps**:
- **Location**: Enter ZIP code `66002`, Select county `Atchison`
- **Household**: Number of people: `3`
- **Person 1**: Relationship: `Head of Household`, Birth month/year: `January 1996` (age 30), Has earned income: Yes, Income: `$1,100/month` (wages), Filing status: Married Filing Jointly, Last tax filing year: `2025`
- **Person 2**: Relationship: `Spouse`, Birth month/year: `March 1997` (age 29), Has earned income: Yes, Income: `$800/month` (wages)
- **Person 3**: Relationship: `Child`, Birth month/year: `July 2013` (age 12, turns 13 in July 2026 — still 12 as of June 3, 2026), Lives with taxpayer: Yes
- **Expenses**: Child care expenses: Yes, Monthly childcare expense amount: `$100`

**Why this matters**: Tests the age 13 boundary (criterion 1) and the married filing jointly requirement (criterion 3) simultaneously. The child is one month from turning 13, confirming the screener uses current age not end-of-year age.

---

### Scenario 3: Zero Earned Income — Investment Income Only
**What we're checking**: Taxpayer with substantial unearned income (investment) but no earned income. Tests criterion 2.
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `66044`, Select county `Douglas`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `March 1990` (age 36), Relationship: Head of Household, Has income: Yes, Investment income: `$4,000/month`, No earned income (wages/salary/self-employment): `$0`, Filing status: Single / Head of Household, Last tax filing year: `2025`
- **Person 2**: Birth month/year: `January 2022` (age 4), Relationship: Child, Lives with Person 1: Yes
- **Expenses**: Child care expenses: Yes, Monthly child care cost: `$800`

**Why this matters**: The CDCC requires earned income (IRC § 21(d)(1)). Unearned income does not qualify. Tests that the screener correctly distinguishes income type, not just whether income is present.

---

### Scenario 4: Child Age 13 — Just Above Qualifying Age Cutoff
**What we're checking**: Household where the only child has already turned 13. Tests the upper boundary of criterion 1.
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `66502`, Select county `Riley`
- **Household**: Number of people: `2`
- **Person 1**: Relationship: `Head of Household`, Birth month/year: `March 1988` (age 38), Has earned income: Yes, Employment income: `$3,500/month`, Filing status: Single / Head of Household, Last tax filing year: `2025`
- **Person 2**: Relationship: `Child`, Birth month/year: `January 2013` (age 13), No income, Lives with head of household: Yes
- **Expenses**: Child care expenses: Yes, Monthly childcare expense: `$400`

**Why this matters**: A child who has already turned 13 fails criterion 1. All other criteria are met, isolating the age check. This is the direct ineligible counterpart to Scenario 1.

---

### Scenario 5: Married Couple — Non-Working Spouse Lacks Earned Income
**What we're checking**: Married couple filing jointly with one qualifying child, but only one spouse has earned income. Tests criterion 2's two-earner requirement for married households.
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `66502`, Select county `Riley`
- **Household**: Number of people: `3`
- **Person 1**: Relationship: `Head of Household`, Birth month/year: `March 1988` (age 38), Has earned income: Yes, Wages/salary: `$3,800/month`, Filing status: Married Filing Jointly
- **Person 2**: Relationship: `Spouse`, Birth month/year: `September 1990` (age 35), Has earned income: No, Income: `$0`
- **Person 3**: Relationship: `Child`, Birth month/year: `January 2022` (age 4)
- **Expenses**: Child care expenses: Yes, Monthly childcare expense: `$600`
- **Tax Filing**: Last tax filing year: `2025`, Filing status: Married Filing Jointly

**Why this matters**: IRC § 21(d)(1) requires both spouses to have earned income (unless the student/disabled exception applies). A stay-at-home spouse with no earned income and no applicable exception disqualifies the household — a real and common disqualifying condition for married filers.

---

### Scenario 6: Two Working Parents, Three Qualifying Children
**What we're checking**: Multi-member household with two working parents filing jointly and three children all under age 13. Tests criterion 1 with multiple qualifying dependents.
**Expected**: Eligible, value: $1,050/year (expenses capped at $6,000 for 2+ qualifying individuals)

**Steps**:
- **Location**: Enter ZIP code `66502`, Select county `Riley`
- **Household**: Number of people: `5`
- **Person 1**: Birth month/year: `March 1990` (age 36), Relationship: Head of Household, Has earned income: Yes, Employment income: `$3,200/month` (wages), Filing status: Married Filing Jointly, Last tax filing year: `2025`
- **Person 2**: Birth month/year: `July 1991` (age 34), Relationship: Spouse, Has earned income: Yes, Employment income: `$2,800/month` (wages)
- **Person 3**: Birth month/year: `September 2018` (age 7), Relationship: Child
- **Person 4**: Birth month/year: `January 2021` (age 5), Relationship: Child
- **Person 5**: Birth month/year: `November 2023` (age 2), Relationship: Child
- **Expenses**: Childcare expenses: Yes, Monthly childcare cost: `$1,800`

**Why this matters**: Validates the multi-qualifying-dependent case. With three children under 13 and two earners, all criteria are met. Also confirms the system handles households exceeding the federal two-dependent cap for expense purposes (capped at $6,000 for 2+) without error.

---

### Scenario 7: Child Turns 13 Mid-Year — Still 12 at Time of Screening
**What we're checking**: Child is currently 12 but will turn 13 later this calendar year. Tests the age boundary logic at its most critical point for criterion 1.
**Expected**: Eligible, value: $570/year

**Steps**:
- **Location**: Enter ZIP code `66502`, Select county `Riley`
- **Household**: Number of people: `2`
- **Person 1**: Relationship: `Head of Household`, Birth month/year: `March 1988` (age 38), Has earned income: Yes, Employment income: `$3,200/month` (wages), Filing status: Single / Head of Household, Last tax filing year: `2025`
- **Person 2**: Relationship: `Child`, Birth month/year: `December 2013` (age 12, turns 13 in December 2026), Lives with head of household: Yes
- **Expenses**: Child care expenses: Yes, Monthly child care cost: `$400`

**Why this matters**: Under IRC § 21(b)(1), the qualifying-age test is whether the child is under 13. A child currently 12 qualifies even if they turn 13 later in the year. Tests that the screener uses current age, not end-of-year age.

---

### Scenario 8: No Qualifying Dependent — Teenager Age 16
**What we're checking**: Household with a head of household and a single dependent who is 16 — no one under age 13 and no disabled individual. Tests criterion 1 with a complete absence of a qualifying dependent.
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `66044`, Select county `Douglas`
- **Household**: Number of people: `2`
- **Person 1**: Relationship: `Head of Household`, Birth month/year: `March 1985` (age 41), Has earned income: Yes, Employment income: `$3,500/month`, Filing status: Single / Head of Household, Last tax filing year: `2025`
- **Person 2**: Relationship: `Child`, Birth month/year: `April 2010` (age 16), No income
- **Expenses**: Child care expenses: Yes, Monthly child care cost: `$400`

**Why this matters**: Even with earned income, KS residency, and care expenses, a household with no one under 13 and no disabled dependent fails criterion 1. This tests the most fundamental disqualifier — the absence of any qualifying individual.

---

### Scenario 9: Disabled Adult Dependent — Alternative Qualifying Individual
**What we're checking**: Household where the qualifying individual is a disabled dependent (not a child under 13). Tests the alternative path in criterion 1.
**Expected**: Eligible, value: $540/year. Per IRC § 21, a disabled dependent incapable of self-care is a qualifying individual at any age, so care expenses for that dependent qualify the household for the credit. (Value: $900/mo expenses exceed the $3,000 single-individual cap → 36% × $3,000 = $1,080 federal → 50% = $540 KS.)

**Steps**:
- **Location**: Enter ZIP code `66044`, Select county `Douglas`
- **Household**: Number of people: `2`
- **Person 1**: Relationship: `Head of Household`, Birth month/year: `March 1978` (age 48), Has earned income: Yes, Employment income: `$3,500/month`, Filing status: Single / Head of Household, Last tax filing year: `2025`
- **Person 2**: Relationship: `Sibling`, Birth month/year: `July 1980` (age 45), Disabled: Yes (physically incapable of self-care), Has earned income: No, Income: `$0`
- **Expenses**: Care expenses: Yes, Monthly care cost for disabled sibling: `$900`

**Why this matters**: Criterion 1 has two paths: child under 13, or a disabled spouse/dependent incapable of self-care. This scenario tests the second path entirely. A household with no children under 13 but a disabled dependent still qualifies — and is a real population that would otherwise be missed.

---

### Scenario 10: Disabled Spouse with No Earned Income — Deemed-Income Path
**What we're checking**: Married couple where one spouse is disabled (incapable of self-care) and has no earned income, with care expenses for that spouse. Under IRC § 21(d)(2), a spouse incapable of self-care is deemed to have earned income of $250/month (one qualifying individual), which both makes them a qualifying individual and satisfies the two-earner requirement — so the household should qualify.
**Expected**: Eligible, value: $525/year. Per IRC § 21(d)(2), a disabled spouse incapable of self-care is deemed to have $250/month of earned income, which both makes them a qualifying individual and satisfies the two-earner requirement, so the household qualifies for the credit. (Value: expenses limited to the lower "earner's" deemed $3,000/year → 35% × $3,000 = $1,050 federal → 50% = $525 KS.)

**Steps**:
- **Location**: Enter ZIP code `66044`, Select county `Douglas`
- **Household**: Number of people: `2`
- **Person 1**: Relationship: `Head of Household`, Birth month/year: `March 1985` (age 41), Has earned income: Yes, Employment income: `$3,500/month`, Filing status: Married Filing Jointly, Last tax filing year: `2025`
- **Person 2**: Relationship: `Spouse`, Birth month/year: `May 1986` (age 40), Disabled: Yes (physically/mentally incapable of self-care), Has earned income: No, Income: `$0`
- **Expenses**: Care expenses: Yes, Monthly care cost for disabled spouse: `$500` (i.e. $6,000/year)

**Why this matters**: This is the deemed-income path of IRC § 21(d)(2), distinct from Scenario 9's disabled-dependent path. A married household with one disabled non-earning spouse and care expenses for that spouse still qualifies — a real population that would otherwise be missed if the deemed $250/month were not applied.

## Source Documentation

- https://www.ksrevenue.gov/pdf/k-40inst10.pdf
- https://www.ksrevenue.gov/taxnotices/notice24-09.pdf#search=child%20tax%20credit

## Program Configuration

`programs/management/commands/import_program_config_data/data/ks_cdcc_initial_config.json`
