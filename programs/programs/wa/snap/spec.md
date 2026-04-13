# Implement Basic Food - Supplemental Nutrition Assistance Program (SNAP) (WA) Program

## Program Details

- **Program**: Basic Food - Supplemental Nutrition Assistance Program (SNAP)
- **State**: WA
- **White Label**: wa
- **Research Date**: 2026-03-23
- **Spec Revision**: 2026-04-07 (incorporating feedback from patmanson)

## Eligibility Criteria

1. **Gross monthly income must be at or below 200% of the Federal Poverty Level (Washington uses Broad-Based Categorical Eligibility)**
   - Screener fields: `household_size`, `calc_gross_income`
   - Source: WAC 388-414-0001; DSHS Basic Food overview page states households must meet income guidelines. Washington's BBCE raises the gross income limit to 200% FPL.

2. **Net monthly income must be at or below 100% of the Federal Poverty Level**
   - Screener fields: `household_size`, `calc_net_income`
   - Note: For most households, both the gross income test AND the net income test must be passed. However, for households with a member aged 60+ or with a disability, the net income test applies **only if the household did not pass the gross income test** (see criterion 7).
   - Source: 7 CFR 273.9(b)(2); 7 U.S.C. § 2014(c)(2); WAC 388-450-0001. The net income test applies to all SNAP households regardless of BBCE status.

3. **No asset/resource limit applies under Washington's Broad-Based Categorical Eligibility (BBCE)**
   - Screener fields: `household_assets`
   - Note: No asset limit applies for most households. **Exception**: if the household contains a member who is 60+ or has a disability AND the household fails the gross income test, a maximum resource limit of **$4,500** applies.
   - Source: WAC 388-470-0005; Washington DSHS eliminated the asset test for Basic Food under BBCE. Per USDA FNS BBCE policy, states that provide BBCE can eliminate the asset test.

4. **Household size determination**
   - Screener fields: `household_size`
   - Source: 7 CFR 273.1(a)-(b); WAC 388-408-0015. People who live together and customarily purchase and prepare meals together are considered one SNAP household.

5. **Must not already be receiving SNAP/Basic Food benefits**
   - Screener fields: `has_snap`
   - Source: General SNAP policy — households cannot receive duplicate benefits.

6. **Student eligibility: College students enrolled at least half-time in an institution of higher education must meet an exemption to be eligible, unless they are age 17 or younger**
   - Screener fields: `student`, `student_full_time`, `student_works_20_plus_hrs`, `student_has_work_study`, `student_job_training_program`, `age`
   - Source: 7 CFR 273.5; 7 U.S.C. § 2015(e); WAC 388-482-0005. Students enrolled at least half-time in higher education are ineligible unless they meet an exemption. Exemptions include: age 17 or younger, working 20+ hours/week, participating in work-study, in a job training program, caring for a dependent child under 6, etc. The student restriction effectively applies to students aged 18–49; students aged 17 or younger are categorically exempt.

7. **Elderly or disabled household member — alternative eligibility path**
   - Screener fields: `age`, `disabled`, `calc_gross_income`, `calc_net_income`, `household_assets`
   - Note: Households with a member aged 60+ or with a disability have **two paths** to eligibility:
     - **Option A (pass gross income test)**: Gross income ≤ 200% FPL → eligible; net income test is not required.
     - **Option B (fail gross income test)**: Gross income > 200% FPL → can still be eligible if net income ≤ 100% FPL. A $4,500 asset limit also applies under this path.
   - **Implementation**: Evaluate Option B in the screener. Check: (1) household has a member aged 60+ or with a disability, (2) gross income > 200% FPL, (3) net income ≤ 100% FPL, (4) assets ≤ $4,500. If all four conditions are met → eligible. Note: the screener approximates net income as gross minus housing/care expenses; the actual SNAP deduction formula (standard deduction, excess shelter, earned income deduction) is more complex — see criterion 21.
   - Source: 7 CFR 273.9(b)(1); 7 U.S.C. § 2014(c)(1); WAC 388-470-0005.
   - Impact: Medium

8. **Household must include at least one member who is a U.S. citizen or qualified non-citizen**
   - Source: 7 U.S.C. § 2015(f); 7 CFR 273.4; WAC 388-424-0001. Only U.S. citizens and certain qualified non-citizens are eligible for SNAP. However, Washington has a state-funded Food Assistance Program (FAP) for legal immigrants who don't qualify for federal SNAP.

9. **State residency — must reside in Washington State**
   - Screener fields: `zipcode`, `county`
   - Source: 7 CFR 273.3; WAC 388-468-0005. Applicants must reside in the state where they apply.

10. **TANF/SSI categorical eligibility — households where all members receive TANF or SSI are categorically eligible**
    - Screener fields: `has_tanf`, `has_ssi`
    - Note: Categorical eligibility bypasses the financial eligibility tests (income and asset), but non-financial eligibility rules (student status, citizenship, residency, etc.) still apply. The key phrase is *all members* — if even one household member does not receive TANF or SSI, this specific pathway does not apply.
    - Source: 7 CFR 273.2(j); 7 U.S.C. § 2014(a). *Statutory language — 7 U.S.C. § 2014(a): households in which each member receives benefits under a State program funded under part A of title IV of the Social Security Act (TANF), supplemental security income benefits under title XVI of the Social Security Act, or aid to the aged, blind, or disabled, shall be eligible to participate in the supplemental nutrition assistance program.*

11. **Pregnant women count as one household member for Basic Food (SNAP)** *(corrected — original spec was incorrect)*
    - Note: A pregnant woman counts as **one** person for household size purposes under WA SNAP. Federal SNAP rules and Washington's WAC 388-408-0015 do not count unborn children as household members for Basic Food. The `pregnant` screener field is relevant for the work requirement exemption only — a pregnant woman is exempt from the ABAWD work requirement, but pregnancy does **not** change household size for FPL threshold calculations.
    - Screener fields: `pregnant` (work requirement exemption only; does not affect `household_size`)
    - Source: WAC 388-408-0034; WAC 388-408-0035; WAC 388-400-0040; federal SNAP rules.

12. **U.S. citizenship or qualified non-citizen status** ⚠️ *data gap*
    - Note: The screener does not collect citizenship or immigration status. This is a federal requirement for SNAP. Qualified non-citizens include lawful permanent residents (with 5-year bar or exemptions), refugees, asylees, etc. Washington's state-funded FAP covers some legal immigrants who don't qualify for federal SNAP. Without this field, we cannot distinguish between citizens, qualified non-citizens, and ineligible non-citizens.
    - Source: 7 U.S.C. § 2015(f); 7 CFR 273.4; WAC 388-424-0001 through 388-424-0025
    - Impact: Medium

13. **Social Security Number requirement — must provide SSN or apply for one** ⚠️ *data gap*
    - Note: The screener does not collect SSN information (nor should it for a screening tool). This is an application-stage requirement, not a pre-screening criterion. Individuals who refuse to provide or apply for an SSN are ineligible, but this is verified during the application process.
    - Source: 7 CFR 273.6; 7 U.S.C. § 2015(e)(1).
    - Impact: Low

14. **Must not be a fleeing felon or in violation of parole/probation** ⚠️ *data gap*
    - Note: Individuals who are fleeing felons or violating conditions of parole or probation are ineligible for SNAP. The screener does not collect criminal justice status. This affects a small subset of applicants.
    - Source: 7 U.S.C. § 2015(k); 7 CFR 273.11(n); WAC 388-442-0010
    - Impact: Low

15. **Must not be residing in an institutional setting (unless exempt)** ⚠️ *data gap*
    - Note: The screener does not collect information about institutional residence. Homeless individuals ARE eligible for SNAP; this criterion specifically excludes those in institutions like prisons, hospitals (long-term), or nursing homes.
    - Source: 7 CFR 273.1(b)(7); WAC 388-408-0040.
    - Impact: Low

16. **ABAWD (Able-Bodied Adults Without Dependents) work requirement — adults aged 18–52 without dependents must work or participate in qualifying activities for at least 80 hours/month** ⚠️ *data gap*
    - Note: Cannot be fully evaluated because: (1) the screener doesn't track months of prior SNAP receipt, (2) Washington's ABAWD waiver status changes frequently by county and year, and (3) the 80 hours/month work requirement is more specific than the screener's employment fields capture. Washington has frequently obtained statewide or partial ABAWD waivers.
    - Source: 7 U.S.C. § 2015(o); 7 CFR 273.24; WAC 388-444-0030.
    - Impact: Medium

17. **Drug felony compliance** ⚠️ *data gap*
    - Note: Washington does not impose a lifetime ban on SNAP for drug felons (RCW 74.04.805), but there may be compliance conditions. The screener does not collect criminal history. This affects a small population.
    - Source: 7 U.S.C. § 2015(k)(1).
    - Impact: Low

18. **Identity verification and interview requirement** ⚠️ *data gap*
    - Note: This is a procedural/administrative requirement during the application process, not a pre-screening criterion.
    - Source: 7 CFR 273.2(e); WAC 388-452-0005.
    - Impact: Low

19. **Voluntary quit — individuals who voluntarily quit a job or reduce work hours below 30/week without good cause within 60 days prior to application may be disqualified** ⚠️ *data gap*
    - Note: The screener captures `unemployed` and `worked_in_last_18_mos` but does not capture the reason for job separation or whether hours were voluntarily reduced.
    - Source: 7 CFR 273.7(j); WAC 388-444-0055
    - Impact: Low

20. **Intentional Program Violation (IPV) disqualification** ⚠️ *data gap*
    - Note: The screener cannot and should not attempt to evaluate prior fraud disqualifications. This is verified through state databases during the application process.
    - Source: 7 CFR 273.16; 7 U.S.C. § 2015(b); WAC 388-446-0001
    - Impact: Low

21. **Precise SNAP net income deduction calculations** ⚠️ *data gap*
    - Note: The screener can approximate but not precisely replicate SNAP deduction methodology: (1) standard deduction amounts change annually and vary by household size, (2) Washington uses a Standard Utility Allowance (SUA) rather than actual utility costs, (3) excess shelter deduction has a cap ($672/month for FFY 2025) unless household has elderly/disabled member, (4) medical expense deduction only applies to elderly/disabled members for amounts exceeding $35/month.
    - Source: 7 CFR 273.9(d); WAC 388-450-0185 through 388-450-0230.
    - Impact: Medium


## Benefit Value

- The maximum monthly benefit depends on household size and is only paid to households with no income at all. Benefits are calculated as:
  **Maximum for household size MINUS 30% of household's net monthly income**
  (where net income = gross income after deductions for rent, utilities, childcare, and medical expenses)
- The estimated average benefit per person in FY 2026 is **$188 per month** ($6.17 per day).
- Maximum monthly benefit amounts (as of October 2025):

| Household Size | Maximum Monthly Benefit | Annual Value |
|---|---|---|
| 1 person | $298 | $3,576 |
| 2 people | $546 | $6,552 |
| 3 people | $785 | $9,420 |
| 4 people | $994 | $11,928 |

- Note: Calculating an exact benefit per scenario requires net income (post-deduction), which the screener can only approximate. `estimated_value` will use PolicyEngine's calculation.
- Source: [Center on Budget and Policy Priorities](https://www.cbpp.org/research/food-assistance/a-quick-guide-to-snap-eligibility-and-benefits); [Snap Benefit Calculator](https://snapbenefitcalculator.com/washington-snap-calculator/)


## Implementation Coverage

- ✅ Evaluable criteria: 11
- ⚠️  Data gaps: 10

11 of 21 total eligibility criteria can be evaluated with current screener fields. The most critical evaluable criteria are: gross income test (200% FPL under WA BBCE), net income test (100% FPL), elderly/disabled Option B alternative path, household size, state residency, current SNAP receipt status, and student eligibility exemptions. Washington's BBCE significantly simplifies screening by eliminating the asset test for most households and raising the gross income limit to 200% FPL. Key corrections from original spec: (1) pregnant women count as **one** household member for Basic Food — pregnancy only affects the work requirement exemption, not household size; (2) the elderly/disabled Option B path (criterion 7) is now evaluated in the screener using an approximated net income calculation. Primary gaps are citizenship/immigration status (medium impact), ABAWD work requirements (medium impact, frequently waived in WA), and precise net income deduction calculations (medium impact, approximated).



## Acceptance Criteria

- [ ] Scenario 1 (Single Adult Worker — Clearly Eligible): User should be **eligible**
- [ ] Scenario 2 (Family of Four — Income Just Under 200% FPL Gross and 100% FPL Net): User should be **eligible**
- [ ] Scenario 3 (Single Parent with Child — Gross Income $1 Below 200% FPL): User should be **eligible**
- [ ] Scenario 4 (Couple Household — Gross Income Exactly at 200% FPL): User should be **eligible**
- [ ] Scenario 5 (Single Adult — Gross Income $1 Above 200% FPL): User should be **ineligible**
- [ ] Scenario 6 (Person Exactly Age 18 — Minimum Adult Age): User should be **eligible**
- [ ] Scenario 7 (17-Year-Old Living Alone — Half-Time Student, Age Exemption Applies): User should be **eligible**
- [ ] Scenario 8 (75-Year-Old Elderly Individual — Option B: Gross Above 200% FPL, Net Below 100% FPL): User should be **eligible**
- [ ] Scenario 9 (Single Adult — Gross Income Below 200% FPL, Net Income Exceeds 100% FPL): User should be **ineligible**
- [ ] Scenario 10 (Already Receiving Basic Food/SNAP — Duplicate Benefit Exclusion): User should be **ineligible**
- [ ] Scenario 11 (Mixed Household — Elderly Member, College Student with Exemption, Working Adult): User should be **eligible**
- [ ] Scenario 12 (Family of Five — Two Working Adults, Pregnant Member, Two Children): User should be **eligible**


## Test Scenarios

### Scenario 1: Single Adult Worker — Clearly Eligible for Basic Food

**What we're checking**: Typical single adult with low wage income who clearly meets both gross and net income tests under Washington's BBCE program.

**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `June 1991` (age 34), Relationship: Head of Household, Sex: Male, Not a student enrolled in higher education, Not pregnant, No disability, U.S. citizen
- **Income**: Employment income: `$1,500` per month, No other income sources
- **Current Benefits**: Not currently receiving SNAP/Basic Food, Not receiving TANF, Not receiving SSI
- **Assets**: No asset information needed (WA BBCE eliminates asset test)

**Why this matters**: This is the most common Basic Food applicant profile — a single working adult with modest earnings. It validates that the screener correctly identifies a clearly eligible household that passes both the gross income test (200% FPL under WA BBCE) and the net income test (100% FPL), with no complicating factors like student status, disability, or elderly exemptions.

---

### Scenario 2: Family of Four — Income Just Under 200% FPL Gross and 100% FPL Net

**What we're checking**: Household that barely meets both the gross income test (200% FPL) and net income test (100% FPL) thresholds, validating edge-case eligibility at the income ceiling.

**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `4`
- **Person 1**: Birth month/year: `June 1986` (age 39), Relationship: Head of Household, Sex: Male, Not a student, Not pregnant, Not disabled, US citizen, Employment income: `$4,800` per month
- **Person 2**: Birth month/year: `September 1988` (age 37), Relationship: Spouse, Sex: Female, Not a student, Not pregnant, Not disabled, US citizen, No income
- **Person 3**: Birth month/year: `January 2016` (age 10), Relationship: Child, Sex: Female, US citizen, No income
- **Person 4**: Birth month/year: `April 2019` (age 6), Relationship: Child, Sex: Male, US citizen, No income
- **Expenses**: Monthly rent/mortgage: `$2,200`, Monthly dependent care costs: `$400`
- **Current Benefits**: Not currently receiving SNAP/Basic Food, Not receiving TANF, Not receiving SSI

**Why this matters**: This scenario tests the boundary condition where a family's gross income is just barely under the 200% FPL limit and their net income, after all applicable deductions, falls just under the 100% FPL threshold. It validates that the screener correctly applies Washington's BBCE gross income limit, the standard SNAP net income test, and all relevant deductions for a household with children and shelter costs.

---

### Scenario 3: Single Parent with Child — Gross Income Below 200% FPL Threshold

**What we're checking**: Validates that a household of 2 with gross monthly income $1 below the 2026 200% FPL threshold for a household of 2 ($3,607/mo) is correctly found eligible.

**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98103`, Select county `King`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `June 1991` (age 34), Relationship: Head of Household, Sex: Female, Not a student, Not pregnant, No disability, U.S. citizen, Employment income: `$3,606` per month ($1 below 200% FPL for HH of 2 in 2026: threshold = $3,607/mo, based on 2026 FPL: $21,640/yr ÷ 12 × 2)
- **Person 2**: Birth month/year: `September 2020` (age 5), Relationship: Child, Sex: Male, No income, U.S. citizen
- **Expenses**: Rent/housing cost: `$1,200` per month, Child care costs: `$400` per month
- **Current Benefits**: Not currently receiving SNAP/Basic Food, Not receiving TANF, Not receiving SSI

**Why this matters**: This test validates that a single-parent household just under the 200% FPL gross income limit is correctly identified as eligible under Washington's BBCE policy. Income is set at $3,606/mo — $1 below the 2026 FPL threshold of $3,607/mo (200% of $21,640/yr for HH=2). Note: the screener calls PolicyEngine with period "2026-01", which applies 2026 calendar-year FPL values. This differs from SNAP FY2026 (Oct 2025–Sep 2026), which technically uses 2025 HHS guidelines ($21,150/yr → $3,525/mo); the calendar-year vs. fiscal-year distinction is a deliberate screener design choice.

---

### Scenario 4: Couple Household — Gross Income Exactly at 200% FPL Threshold

**What we're checking**: Validates that a 2-person household with gross monthly income exactly at the 2026 200% FPL threshold ($3,607/month for HH of 2) is eligible under Washington's BBCE gross income test ("at or below" per WAC 388-414-0001), and net income after standard deduction passes 100% FPL.

**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98103`, Select county `King`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `June 1986` (age 39), Relationship: Head of Household, Sex: Male, Not a student, Not pregnant, Not disabled, US citizen, Employment income: `$2,000` per month
- **Person 2**: Birth month/year: `September 1988` (age 37), Relationship: Spouse, Sex: Female, Not a student, Not pregnant, Not disabled, US citizen, Employment income: `$1,607` per month
- **Combined gross income**: `$3,607/month` (exactly at 200% FPL for HH of 2 in 2026: threshold = $3,607/mo, based on 2026 FPL: $21,640/yr ÷ 12 × 2).
- **Current Benefits**: Not currently receiving SNAP/Basic Food, Not receiving TANF, Not receiving SSI

**Why this matters**: Validates that a couple household at exactly the 200% FPL gross income limit is correctly found eligible under Washington's BBCE policy — the criterion is "at or below" (WAC 388-414-0001), so the boundary value must be eligible. Income is set to exactly $3,607/mo (2026 FPL for HH=2: $21,640/yr ÷ 12 × 2). The screener uses PolicyEngine period "2026-01", applying 2026 calendar-year FPL. This is consistent with Scenarios 3 and 5 — all boundary tests use 2026 FPL values.

---

### Scenario 5: Single Adult — Gross Income $1 Above 200% FPL, Should Be Ineligible

**What we're checking**: Validates that a single-person household with gross monthly income just $1 above the 2026 200% FPL threshold for a household of 1 ($2,660/mo) is correctly denied Basic Food benefits.

**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `98103`, Select county `King`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `June 1991` (age 34), Relationship: Head of Household, Sex: Male, Not a student, Not pregnant, No disability, US citizen, Employment income: `$2,661` per month ($1 above 200% FPL for HH of 1 in 2026: 200% FPL = $2,660/mo)
- **Expenses**: Rent/mortgage: `$900` per month, No other deductions or expenses
- **Current Benefits**: Not currently receiving SNAP/Basic Food, Not receiving TANF, Not receiving SSI

**Why this matters**: This tests the upper boundary of the gross income test under Washington's BBCE policy. A household exceeding this threshold by even $1 should be denied, confirming the screener correctly enforces the boundary rather than rounding or allowing a tolerance. Note: income updated from original spec to reflect 2026 FPL values (200% FPL for HH of 1 = $2,660/mo; use $2,661 to be $1 above).

---

### Scenario 6: Person Exactly Age 18 — Minimum Age for Adult SNAP Eligibility

**What we're checking**: Validates that a person who just turned 18 is eligible for Basic Food when all other criteria are met, and that this person is not incorrectly subject to the student eligibility restriction since they are not enrolled in higher education.

**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 2008` (age 18), Relationship: Head of Household, Not a student enrolled in higher education, Not pregnant, No disability, Employment income: `$800/month`, No other income sources
- **Current Benefits**: Not currently receiving SNAP/Basic Food, Not receiving TANF, Not receiving SSI

**Why this matters**: Age 18 is the minimum threshold at which a person can independently apply for SNAP as an adult head of household. This test verifies the system correctly handles someone at exactly the minimum adult age boundary. It also confirms that an 18-year-old who is NOT enrolled in higher education is not incorrectly flagged by the student eligibility restriction (which only applies to students aged 18–49 enrolled at least half-time).

---

### Scenario 7: 17-Year-Old Living Alone — Half-Time Student, Age Exemption Applies, Eligible

**What we're checking**: Validates that a 17-year-old (just below age 18) who is a college student enrolled half-time is eligible, because WAC 388-482-0005 explicitly lists "age 17 or younger" as a qualifying exemption from the student eligibility restriction.

**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `June 2008` (age 17 — will turn 18 in June 2026), Relationship: Head of Household, Student status: enrolled in higher education at least half-time, Working: No, No disability, Not pregnant
- **Income**: No earned income, No unearned income, Total gross monthly income: `$0`
- **Current Benefits**: Not currently receiving SNAP/Basic Food, Not receiving TANF, Not receiving SSI

**Why this matters**: Tests the age exemption in the student eligibility rule. WAC 388-482-0005 states that students age 17 or younger are categorically exempt from the student eligibility restriction — being a minor is itself a qualifying exemption. A 17-year-old half-time student with $0 income is well below 200% FPL and should receive the maximum benefit for a household of 1 ($298/mo).

---

### Scenario 8: 75-Year-Old Elderly Individual — Option B: Gross Above 200% FPL, Net Below 100% FPL

**What we're checking**: Validates the Option B alternative eligibility path for elderly/disabled households (criterion 7). The person's gross income exceeds the 200% FPL threshold, so they fail the standard gross income test. However, high housing costs bring their net income below 100% FPL, which qualifies them under Option B. This tests the distinctive edge case: gross income > 200% FPL AND net income ≤ 100% FPL for a household with a member aged 60+.

**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1951` (age 75), Relationship: Head of Household, Not a student, Not pregnant, Not disabled (using age 60+ exemption, not disability)
- **Income**: Social Security Retirement income: `$2,700` per month (above 200% FPL of $2,660/mo for HH of 1), No other income sources
- **Expenses**: Monthly rent/housing cost: `$1,500`
- **Assets**: `$0` (well below the $4,500 asset limit that applies under Option B)
- **Current Benefits**: Not currently receiving SNAP/Basic Food, Not receiving TANF, Not receiving SSI

**Why this matters**: Tests the Option B path that is unique to elderly/disabled households. At $2,700/mo gross, this person fails the 200% FPL gross income test ($2,660 threshold for HH=1), so they are not eligible under Option A. But $1,500/mo rent brings approximated net income to $1,200/mo ($2,700 − $1,500), which is below the 100% FPL threshold of $1,255/mo for HH=1 — qualifying under Option B. This is the scenario that Scenario 1 does not cover: an elderly person whose gross income slightly exceeds the standard limit but whose housing costs create genuine financial need.

---

### Scenario 9: Single Adult — Passes Gross Income Test, Fails Net Income Test

**What we're checking**: A household whose gross income falls below the 200% FPL gross limit ($2,660/mo for HH of 1 in SNAP FY2026) but whose net income — after the 20% earned income deduction and standard deduction — exceeds the 100% FPL net limit ($1,330/mo). This isolates criterion 2 (net income test) independently from the gross income boundary.

**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `June 1991` (age 34), Relationship: Head of Household, Not a student enrolled in higher education, Not pregnant, No disability, U.S. citizen
- **Income**: Employment income: `$2,200` per month, No other income sources
- **Expenses**: No significant shelter or dependent care expenses
- **Current Benefits**: Not currently receiving SNAP/Basic Food, Not receiving TANF or SSI

**Why this matters**: Tests the net income test (criterion 2) as a standalone ineligible gate. Gross income ($2,200/mo) is well under the 200% FPL limit ($2,660/mo), so the household passes the gross test. After applying the 20% earned income deduction ($440) and the FY2025 standard deduction for HH of 1 ($219), net income is approximately $1,541/mo — above the 100% FPL net limit of $1,330/mo — making the household ineligible. Without significant shelter or dependent care costs, no additional deductions reduce net income below the threshold. Every other eligible scenario in this spec already uses a WA ZIP code, so geographic validation is implicitly covered.

---

### Scenario 10: Already Receiving Basic Food/SNAP — Duplicate Benefit Exclusion

**What we're checking**: Validates that a household already receiving SNAP/Basic Food benefits is flagged as ineligible, preventing duplicate benefit enrollment.

**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `98103`, Select county `King`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `June 1985` (age 40), Relationship: Head of Household, Sex: Female, Not a student, Not pregnant, Not disabled, U.S. citizen, Employment income: `$1,800` per month
- **Person 2**: Birth month/year: `September 2018` (age 7), Relationship: Child, Sex: Male, Not a student, Not disabled, U.S. citizen
- **Current Benefits**: Select that the household **already receives SNAP/Basic Food** benefits (`has_snap` = Yes)

**Why this matters**: Preventing duplicate SNAP benefit enrollment is critical for program integrity. Households already receiving Basic Food should not be screened as eligible for a second enrollment.

---

### Scenario 11: Mixed Household — Elderly Exempt Member, College Student with Work Exemption, Working Adult

**What we're checking**: Validates a mixed household where one member is elderly (age 65), one is a college student aged 22 enrolled half-time who qualifies via the 20+ hours/week work exemption, and one is a working adult. Tests interaction of elderly gross income exemption (criterion 7), student eligibility rules (criterion 6), household size determination (criterion 4), and net income test (criterion 2).

**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98103`, Select county `King`
- **Household**: Number of people: `3`
- **Person 1**: Birth month/year: `June 1960` (age 65), Relationship: Head of Household, Not a student, Social Security Retirement income: `$1,200` per month, Not currently receiving SNAP/Basic Food
- **Person 2**: Birth month/year: `September 1996` (age 29), Relationship: Child/Dependent adult, Not a student, No disability, Employment income: `$2,400` per month
- **Person 3**: Birth month/year: `January 2004` (age 22), Relationship: Grandchild, Student: Yes (enrolled at least half-time in higher education), Works 20+ hours per week (qualifies for student exemption), Employment income: `$900` per month, No disability
- **Current Benefits**: Not currently receiving SNAP/Basic Food, Not receiving TANF or SSI

**Why this matters**: Validates that the screener correctly applies the elderly/disabled gross income exemption while still enforcing the net income test, and properly handles student eligibility rules within a multi-member household.

---

### Scenario 12: Family of Five — Two Working Adults, Pregnant Member, and Two Children

**What we're checking**: Validates that a multi-member household with two working adults (one pregnant), and two children correctly determines eligibility for a household of 5. Pregnancy does NOT change household size for SNAP — the household remains 5 members.

**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98103`, Select county `King`
- **Household**: Number of people: `5`
- **Person 1**: Birth month/year: `June 1991` (age 34), Relationship: Head of Household, Sex: Male, US citizen, Employment income: `$2,000` per month, Not a student, No disability
- **Person 2**: Birth month/year: `September 1993` (age 32), Relationship: Spouse, Sex: Female, US citizen, Employment income: `$1,500` per month, Not a student, **Pregnant: Yes** (note: counts as 1 household member, not 2; pregnancy is relevant for work requirement exemption only), No disability
- **Person 3**: Birth month/year: `January 2014` (age 12), Relationship: Child, Sex: Female, US citizen, No income
- **Person 4**: Birth month/year: `July 2017` (age 8), Relationship: Child, Sex: Male, US citizen, No income
- **Person 5**: Birth month/year: `November 2021` (age 4), Relationship: Child, Sex: Male, US citizen, No income
- **Current Benefits**: Not currently receiving SNAP/Basic Food, Not receiving TANF or SSI

**Why this matters**: Tests multiple interacting eligibility criteria simultaneously — household size determination with multiple members, combined income from two earners evaluated against the correct FPL thresholds, and verification that children are included without issue. Confirms that pregnancy does NOT increase household size from 5 to 6 for SNAP (federal SNAP rules and WAC 388-408-0015 do not count unborn children as household members for Basic Food).


## Research Sources

- [DSHS Basic Food (SNAP) Program Overview — Washington State](https://www.dshs.wa.gov/esa/community-services-offices/basic-food)
- [Help Me Grow WA — Basic Food (SNAP) Eligibility Guide](https://helpmegrowwa.org/basic-food-snap)
- [Washington Connection — Online Benefits Application Portal (DSHS)](https://www.washingtonconnection.org/home/)
- [DSHS Food Assistance Program for Legal Immigrants (FAP)](https://www.dshs.wa.gov/esa/program-summary/food-assistance-program-legal-immigrants-fap)
- [Center on Budget and Policy Priorities — A Quick Guide to SNAP Eligibility and Benefits](https://www.cbpp.org/research/food-assistance/a-quick-guide-to-snap-eligibility-and-benefits)
- [USDA Food and Nutrition Service — SNAP Recipient Eligibility](https://www.fns.usda.gov/snap/recipient/eligibility)
- [Legal Information Institute — 7 U.S.C. § 2014](https://www.law.cornell.edu/uscode/text/7/2014)
- [Washington State Legislature — WAC 388-400-0040](https://app.leg.wa.gov/wac/default.aspx?cite=388-400-0040)
- [SNAP Benefit Calculator — Washington](https://snapbenefitcalculator.com/washington-snap-calculator/)


## JSON Test Cases

File: `validations/management/commands/import_validations/data/wa_snap.json`

Scenarios 1–12 (scenario 14 removed — the premise that a pregnant woman's unborn child counts as a second household member is incorrect for WA SNAP under federal rules and WAC 388-408-0015).

Updated `eligible` values:
- Scenarios 1, 2, 3, 4, 6, 7, 8, 9, 11, 12: `true`
- Scenarios 5, 10: `false`

Updated income amounts for 2026 FPL:
- Scenario 3 (HH=2, $1 below 200% FPL): `$3,606/mo` (was $2,429)
- Scenario 4 (HH=2, exactly 200% FPL): `$3,607/mo` total combined wages (was $2,510); net income at exactly 100% FPL = `$1,803/mo`
- Scenario 5 (HH=1, $1 above 200% FPL): `$2,661/mo` (was $2,431)


## Generated Program Configuration

File: `programs/management/commands/import_program_config_data/data/wa_snap_initial_config.json`


## Changelog

| Date | Author | Change |
|---|---|---|
| 2026-04-13 | catonph (review) | Removed redundant Scenario 11 (duplicate `has_snap` check, parent-child household); renumbered Scenarios 12→11 and 13→12 |
| 2026-03-23 | Josh Mejia | Initial research and spec |
| 2026-04-07 | patmanson | Corrections: pregnant women count as 1 HH member (not 2); updated 2026 FPL thresholds in scenarios 3/4/5; clarified elderly/disabled alternative path (criteria 2, 3, 7); recommended disclaimer for 60+/disabled edge case; removed scenario 14; estimated_value deferred to PolicyEngine |
| 2026-04-13 | catonph | Scenario 9 replaced: geographic validation was redundant (all eligible scenarios use WA ZIP codes); new Scenario 9 isolates net income test failure — gross passes 200% FPL, net fails 100% FPL after standard SNAP deductions |
| 2026-04-13 | catonph/patrickwey | Scenario 8 updated to exercise Option B path (gross > 200% FPL, net ≤ 100% FPL via $1,500/mo rent) instead of the low-income Option A path; criterion 7 updated to implement Option B in screener rather than disclaimer-only; evaluable criteria count increased from 10 to 11 |
| 2026-04-13 | patmanson | Fix FPL year inconsistency (catonph review): scenarios 3/4 text still referenced 2025 FPL ($3,525/mo) — updated to 2026 FPL ($3,607/mo for HH=2, matching the program's year=2026 PolicyEngine config); scenario 3 income $3,400→$3,606 (tight boundary, $1 below threshold); scenario 4 income $3,500→$3,607 (exactly at threshold, matching acceptance criteria); added note explaining calendar-year vs. SNAP fiscal-year FPL distinction |
