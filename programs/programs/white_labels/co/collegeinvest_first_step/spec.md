# Implement Colorado CollegeInvest First Step (CO) Program

## Program Details

- **Program**: Colorado CollegeInvest First Step
- **State**: CO
- **White Label**: co
- **Research Date**: 2026-05-19

## Eligibility Criteria

1. **Household must reside in Colorado**
   - Screener fields:
     - `zipcode`
     - `county`
   - Source: C.R.S. § 23-3.1-308.5; [CollegeInvest First Step Overview](https://www.collegeinvest.org/first-step/)

2. **Household must have at least one child aged 0–7**
   - Screener fields:
     - `age (HouseholdMember)`
     - `relationship (HouseholdMember)`
   - Note: Eligible children must be age 0–7 (inclusive). The deposit must be claimed before the child's 8th birthday.
   - Source: [CollegeInvest First Step FAQ for Advisors (January 2026)](https://www.collegeinvest.org/images/pdfs/First%20Step%20FAQs%20for%20Advisors%20FINAL%201.5.26.pdf)

3. **Child must have been born on or after January 1, 2020**
   - Screener fields:
     - `birth_year (HouseholdMember)`
   - Note: The program launched with children born on or after January 1, 2020. Check `birth_year >= 2020` for each candidate child. In 2026, this is only binding for children born in 2019 who are age 6–7 and might otherwise pass the age check.
   - Source: [CollegeInvest First Step FAQ for Advisors (January 2026)](https://www.collegeinvest.org/images/pdfs/First%20Step%20FAQs%20for%20Advisors%20FINAL%201.5.26.pdf)

4. **Child must have been born or adopted in Colorado** ⚠️ *data gap*
   - Screener fields: none
   - Note: The program requires birth or adoption to have occurred in Colorado. The screener verifies current CO residency via `zipcode`/`county` but cannot verify birth or adoption location. We use current CO residency as a proxy (inclusivity assumption). Exception: active military families with permanent CO residence qualify even if the child was born outside Colorado — this exception is also a data gap since the screener does not capture military status. Both gaps are noted in the program description.
   - Source: C.R.S. § 23-3.1-308.5; [CollegeInvest First Step Overview](https://www.collegeinvest.org/first-step/)

5. **Applicant must be a U.S. citizen or resident alien** *(config-enforced, not evaluated in calculator)*
   - Screener fields: none — `HouseholdMember` has no `legal_status` field; this requirement is declared via the `legal_status_required` program config (`citizen`, `gc_5plus`, `gc_5less`) and surfaced to users by the frontend, consistent with the codebase pattern for citizenship requirements (see trump_account).
   - Source: [MFB-958](https://linear.app/myfriendben/issue/MFB-958); [CollegeInvest First Step Overview](https://www.collegeinvest.org/first-step/)

## Priority Criteria

- **December 31, 2026 deadline for enhanced award**: Applications received by December 31, 2026 may be eligible for a higher award amount. This is surfaced in the program description as a time-sensitive note but is not modeled in the calculator.

## Benefit Value

- **2026 award amount**: $121 per eligible child (one-time seed deposit)
  - Source: [MFB-958](https://linear.app/myfriendben/issue/MFB-958); [CollegeInvest First Step FAQ for Advisors (January 2026)](https://www.collegeinvest.org/images/pdfs/First%20Step%20FAQs%20for%20Advisors%20FINAL%201.5.26.pdf)
- **Dollar-for-dollar matching**: CollegeInvest also matches family contributions dollar-for-dollar. The matching amount depends on family contributions and is not modeled in the screener calculator. It is surfaced in the program description.
- **Calculator methodology**: Count the number of children in the household satisfying all evaluable criteria (CO residency, age 0–7, `birth_year >= 2020`). Multiply by $121.
  - 1 eligible child → $121; 2 eligible children → $242
- **`value_format`**: `"lump_sum"` (one-time deposit)

## Implementation Coverage

- ✅ Evaluable criteria: 3 (CO residency, age 0–7, birth year ≥ 2020)
- ⚠️ Data gaps: 2 (birth/adoption location; military exception)
- ℹ️ Config-enforced: 1 (citizenship via `legal_status_required`: `citizen`, `gc_5plus`, `gc_5less`)

## Test Scenarios

### Scenario 1: Clearly Eligible — Denver Family with Newborn
**What we're checking**: Standard CO household with a newborn qualifies for the $121 deposit.
**Expected**: Eligible, value: $121

**Steps**:
- **Location**: ZIP `80202`, county `Denver County`
- **Person 1**: Head of Household, birth month/year: March 1992 (age 34), employment income $4,500/month, citizen
- **Person 2**: Spouse, birth month/year: July 1993 (age 32), employment income $3,500/month, citizen
- **Person 3**: Child, birth month/year: January 2026 (age 0)

---

### Scenario 2: Ineligible — No Children Under 8
**What we're checking**: CO household with only a 9-year-old is screened out — the primary exclusion.
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `80202`, county `Denver County`
- **Person 1**: Head of Household, birth month/year: March 1990 (age 36), employment income $4,000/month, citizen
- **Person 2**: Child, birth month/year: January 2017 (age 9)

---

### Scenario 3: Edge Case — Child Born January 2020 (Minimum Birth Year)
**What we're checking**: A child born exactly at the January 2020 threshold is still eligible.
**Expected**: Eligible, value: $121

**Steps**:
- **Location**: ZIP `80903`, county `El Paso County`
- **Person 1**: Head of Household, birth month/year: June 1990 (age 35), employment income $3,500/month, citizen
- **Person 2**: Child, birth month/year: January 2020 (age 6)

---

### Scenario 4: Multiple Eligible Children
**What we're checking**: Household with two eligible children receives $242 (2 × $121).
**Expected**: Eligible, value: $242

**Steps**:
- **Location**: ZIP `80204`, county `Denver County`
- **Person 1**: Head of Household, birth month/year: August 1990 (age 35), employment income $3,500/month, citizen
- **Person 2**: Spouse, birth month/year: November 1991 (age 34), no income, citizen
- **Person 3**: Child, birth month/year: February 2023 (age 3)
- **Person 4**: Child, birth month/year: March 2026 (age 0)

---

## Research Sources

- [CollegeInvest First Step Program Overview (C.R.S. § 23-3.1-308.5)](https://www.collegeinvest.org/first-step/)
- [CollegeInvest First Step FAQ for Advisors (January 2026)](https://www.collegeinvest.org/images/pdfs/First%20Step%20FAQs%20for%20Advisors%20FINAL%201.5.26.pdf)
- [CollegeInvest First Step Application Portal](https://firststep.collegeinvest.org/)
- [Linear Ticket MFB-958](https://linear.app/myfriendben/issue/MFB-958/co-add-colorado-collegeinvest-first-step-program)
