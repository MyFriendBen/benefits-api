# TX: Community Care for the Aged and Disabled (CCAD)

- **Program**: Community Care for the Aged and Disabled (CCAD)
- **State**: TX
- **White Label**: tx
- **Research Date**: 2026-03-03

## Eligibility Criteria

| # | Criterion | Screener Fields | Logic | Can Evaluate? | Notes | Source |
|---|-----------|-----------------|-------|---------------|-------|--------|
| 1 | Age 65+ OR age 21+ with disability | `household_member.age`, `household_member.disabled` | `age >= 65 OR (age >= 21 AND disabled == True)` | ✅ | | CCSE Handbook §3000 |
| 2 | Income at or below 300% FPL | `household_size`, all income fields | `calc_gross_income('yearly', 'all') <= FPL_300_PERCENT[household_size]` | ✅ | | CCSE Handbook §3000 |
| 3 | Functionally eligible (needs ADL assistance) | `household_member.disabled`, `household_member.long_term_disability` | `disabled == True OR long_term_disability == True` | ⚠️ | Screener has general disability fields but no detailed ADL assessment; CCAD requires professional nursing assessment of specific ADL limitations | CCSE Handbook §3000 |
| 4 | Texas residency | `county`, `zipcode` | `county in TEXAS_COUNTIES OR zipcode in TEXAS_ZIPCODES` | ✅ | | CCSE Handbook §3000 |
| 5 | Must not be residing in a nursing facility | `housing_situation` | `housing_situation != 'nursing_home'` | ✅ | | CCSE Handbook §3000 |
| 6 | Medicaid eligible or meets Medicaid financial criteria | `has_medicaid`, `household_member.medicaid` | `has_medicaid == True OR household_member.medicaid == True OR meets_medicaid_criteria` | ✅ | | CCSE Handbook §3000 |
| 7 | Asset limit: $2,000 individual / $3,000 couple (Medicaid standards) | `household_assets` | `assets <= 2000 (individual) or <= 3000 (couple)` | ⚠️ | Field is household-level, not individual/couple; Medicaid asset exemptions (home equity, one vehicle, burial funds) not captured | CCSE Handbook §3000 |
| 8 | At risk of nursing facility placement without services | — | Clinical determination | ❌ | No screener field captures nursing facility risk level | CCSE Handbook §3000 |
| 9 | U.S. citizenship or qualified immigration status | — | — | ❌ | No citizenship/immigration status field in screener; required because CCAD follows Medicaid eligibility rules | CCSE Handbook §3000 |
| 10 | No asset transfers below fair market value within lookback period | — | Medicaid 60-month lookback | ❌ | No screener field captures asset transfer history | Medicaid asset transfer rules |
| 11 | Medical necessity for home and community-based services | — | Professional assessment | ❌ | Medical necessity is determined by healthcare professional, not self-reported screener data | CCSE Handbook §3000 |
| 12 | Must choose CCAD over nursing facility placement | — | Applicant preference | ❌ | Determined during application process, not captured in screener | CCSE Handbook §3000 |
| 13 | Services available in applicant's geographic area | `county`, `zipcode` | — | ❌ | No data on service availability or waiting lists by region | CCSE Handbook §2000 |
| 14 | No responsible party able to provide necessary care | — | Informal caregiver assessment | ❌ | No field captures availability of informal caregivers or family support | CCSE Handbook §3000 |
| 15 | Must not already be receiving CCAD | `current_benefits` | `'ccad' not in current_benefits` | ✅ | | — |

## Coverage

- **Evaluable**: 6 of 15 criteria (40%)
- **Summary**: The evaluable criteria include age requirements, income limits (300% FPL), basic disability status, Texas residency, housing situation, and current Medicaid enrollment. Critical gaps include detailed asset limits with Medicaid exemptions, specific ADL functional assessment, nursing facility risk determination, citizenship/immigration status, and asset transfer history. The most significant limitation is the inability to perform detailed functional assessment and asset evaluation, both of which are core CCAD eligibility requirements.

## Benefit Value

Amount varies by household based on services needed. CCAD services may include personal care assistance, adult day care, emergency response systems, home-delivered meals, and medical supplies. No fixed dollar amount can be calculated by the screener.

## Sources

- [Texas HHS Community Care Services Eligibility (CCSE) Handbook](https://www.hhs.texas.gov/laws-regulations/handbooks/case-worker-community-care-aged-disabled-handbook)
- [CCAD Program Overview - PayingForSeniorCare.com](https://www.payingforseniorcare.com/texas/ccad)
- [CCAD Eligibility Requirements](https://www.payingforseniorcare.com/texas/ccad#Eligibility_Guidelines)
- [CCAD Covered Services](https://www.payingforseniorcare.com/texas/ccad#Benefits_and_Services)
- [CCAD Application Process](https://www.payingforseniorcare.com/texas/ccad#How_to_Apply_Learn_More)

## Test Scenarios

### Scenario 1: 65-Year-Old Retiree with Social Security Income Below 300% FPL

**Checks**: Core age-based eligibility (65+) with income clearly below threshold
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `78701`, County `Travis County`
- **Household**: 1 person
- **Person 1**: DOB `January 1961` (age 65), Head of Household, U.S. Citizen, Social Security Retirement `$1,500/month`, no disability, no insurance, no current benefits

**Why this matters**: Most common CCAD applicant profile — a senior with modest Social Security income. Tests the core age-based eligibility path at a clearly qualifying income level.

---

### Scenario 2: 21-Year-Old with Disability at Exactly 300% FPL

**Checks**: Minimum age (21 with disability) and maximum income threshold (exactly 300% FPL)
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `75001`, County `Collin`
- **Household**: 1 person
- **Person 1**: DOB `March 2005` (age 21), Head of Household, U.S. Citizen, has disability, SSDI `$3,825/month` ($45,900/year = 300% FPL for household of 1), no insurance

**Why this matters**: Tests both minimum boundaries simultaneously — youngest possible qualifying age and highest allowable income. Ensures no rounding errors at the precise income threshold.

---

### Scenario 3: 67-Year-Old with Income Just Below 300% FPL

**Checks**: Upper income boundary — applicant just under the threshold is eligible
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `75201`, County `Dallas`
- **Household**: 1 person
- **Person 1**: DOB `January 1959` (age 67), Head of Household, U.S. Citizen, Social Security Retirement `$4,200/month`, no disability, no insurance, no current benefits

**Why this matters**: Validates the income threshold boundary prevents false negatives for seniors close to but under the limit.

---

### Scenario 4: 70-Year-Old with Income Exactly at 300% FPL

**Checks**: Income exactly at the threshold qualifies ("at or below")
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `75201`, County `Dallas County`
- **Household**: 1 person
- **Person 1**: DOB `January 1956` (age 70), Head of Household, U.S. Citizen, Social Security Retirement `$4,395/month` ($52,740/year), no insurance, no current benefits

**Why this matters**: Confirms the boundary condition is inclusive — applicants at exactly 300% FPL must not be incorrectly excluded.

---

### Scenario 5: 72-Year-Old with Income Just Above 300% FPL

**Checks**: Income exceeding threshold is correctly rejected
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `75201`, County `Dallas County`
- **Household**: 1 person
- **Person 1**: DOB `January 1954` (age 72), Head of Household, U.S. Citizen, Social Security Retirement `$4,900/month`, no disability, no insurance, no current benefits

**Why this matters**: Ensures the income ceiling is enforced — prevents ineligible applicants from proceeding.

---

### Scenario 6: 21-Year-Old with Disability at Exact Minimum Age

**Checks**: Age threshold is inclusive (>= 21, not > 21) for disabled applicants
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `75001`, County `Collin`
- **Household**: 1 person
- **Person 1**: DOB `March 2005` (age 21), Head of Household, U.S. Citizen, has disability, SSI/SSDI `$943/month`, Medicaid

**Why this matters**: Confirms no off-by-one error in age calculation for the disability pathway minimum age.

---

### Scenario 7: 20-Year-Old with Disability — Below Minimum Age

**Checks**: Under-21 applicants are ineligible even with disability and qualifying income
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `75201`, County `Dallas`
- **Household**: 1 person
- **Person 1**: DOB `April 2006` (age 20), Head of Household, U.S. Citizen, has disability, SSI `$943/month`, no insurance, no current benefits

**Why this matters**: Validates the age gate for the disability pathway — a 20-year-old with disability does not qualify.

---

### Scenario 8: 85-Year-Old with Low Income

**Checks**: No unintended upper age limit; early birth years processed correctly
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `78701`, County `Travis`
- **Household**: 1 person
- **Person 1**: DOB `January 1941` (age 85), Head of Household, U.S. Citizen, Social Security Retirement `$1,200/month`, no disability, no insurance, no current benefits

**Why this matters**: Confirms the system handles birth years from the early 1940s and applies no unintended upper age limit.

---

### Scenario 9: Valid Texas Resident — Geographic Eligibility

**Checks**: Texas county and ZIP code validation passes
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `75201`, County `Dallas`
- **Household**: 1 person
- **Person 1**: DOB `January 1958` (age 68), Head of Household, U.S. Citizen, Social Security Retirement `$1,200/month`, no insurance

**Why this matters**: Confirms the screener correctly recognizes valid Texas counties and ZIP codes for the residency requirement.

---

### Scenario 10: Already Receiving CCAD

**Checks**: Duplicate benefit check — current CCAD recipients are ineligible
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `78701`, County `Travis`
- **Household**: 1 person
- **Person 1**: DOB `January 1961` (age 65), Head of Household, U.S. Citizen, no disability, Social Security Retirement `$1,200/month`, Medicaid, **current benefits: CCAD**

**Why this matters**: Prevents duplicate enrollment and ensures current beneficiaries are correctly identified.

---

### Scenario 11: Currently in Nursing Facility

**Checks**: Applicants in nursing facilities are excluded
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `75201`, County `Dallas`
- **Household**: 1 person
- **Person 1**: DOB `January 1961` (age 65), Head of Household, U.S. Citizen, has disability, Social Security Retirement `$1,200/month`, housing situation: Nursing Home/Long-term Care Facility, Medicaid

**Why this matters**: CCAD is a community-based alternative to institutional care — applicants already in nursing facilities do not qualify.

---

### Scenario 12: Mixed Household — Eligible Senior with Ineligible Adult Child

**Checks**: CCAD eligibility is per-individual, not household-wide
**Expected**: Eligible (for the senior)

**Steps**:
- **Location**: ZIP `78701`, County `Travis`
- **Household**: 2 people
- **Person 1 (Head)**: DOB `January 1958` (age 68), no disability, Social Security Retirement `$1,800/month`, Medicare, no current benefits, lives at home
- **Person 2 (Adult Child)**: DOB `June 1981` (age 44), no disability, Employment `$2,500/month`, employer insurance, no current benefits

**Why this matters**: Confirms individual-level evaluation within multi-member households and that combined household income is correctly applied to the eligible member.

---

### Scenario 13: Married Couple — Both 65+, Combined Income Below 300% FPL

**Checks**: Multiple eligible members in one household; income evaluated at household size of 2
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `78701`, County `Travis`
- **Household**: 2 people
- **Person 1 (Head)**: DOB `January 1959` (age 67), Social Security Retirement `$1,200/month`, no disability, no insurance, no current benefits
- **Person 2 (Spouse)**: DOB `June 1960` (age 65), Social Security Retirement `$1,000/month`, no disability, no insurance, no current benefits

**Why this matters**: Verifies the system evaluates combined household income against the correct FPL threshold for a 2-person household and recognizes both spouses as independently eligible.

---

### Scenario 14: 21-Year-Old with December Birthday — Age Calculation Edge Case

**Checks**: Age calculated correctly when birth month hasn't occurred yet in the current year
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `78701`, County `Travis`
- **Household**: 1 person
- **Person 1**: DOB `December 2004` (age 21 — birthday hasn't occurred yet in 2026), Head of Household, U.S. Citizen, has disability, SSDI `$1,200/month` ($14,400/year), no insurance

**Why this matters**: Ensures age calculation doesn't prematurely advance the applicant to 22 before their birthday. At exactly 21 with a disability, this is a critical boundary.
