# TX: Community Care for the Aged and Disabled (CCAD)

- **Program**: Community Care for the Aged and Disabled (CCAD)
- **State**: TX
- **White Label**: tx
- **Research Date**: 2026-03-03

## Eligibility Criteria

| # | Criterion | Screener Fields | Logic | Can Evaluate? | Notes | Source |
|---|-----------|-----------------|-------|---------------|-------|--------|
| 1 | Age 65+ OR age 21+ with disability | `household_member.age`, `household_member.is_disabled` | `age >= 65 OR (age >= 21 AND is_disabled == True)` | ✅ | `is_disabled` is a calculated field covering `disabled`, `long_term_disability`, and `visually_impaired`. For applicants 65+, disability status is not required. | CCSE Handbook §3000 |
| 2 | Income at or below 300% FPL, OR categorically eligible | `household_size`, all income fields, `has_snap`, `has_ssi`, `has_tanf`, `has_medicaid` | `calc_gross_income('yearly', 'all') <= FPL_300_PERCENT[household_size] OR has_snap OR has_ssi OR has_tanf OR has_medicaid` | ✅ | Categorical eligibility (SSI, TANF, SNAP, Medicaid, SLMB, QMB) bypasses the income test. See [CCSE §3300](https://www.hhs.texas.gov/handbooks/community-care-services-eligibility-handbook/3300-income-eligibility). | CCSE Handbook §3300 |
| 3 | Functionally eligible (needs ADL assistance) | `household_member.age`, `household_member.disabled`, `household_member.long_term_disability` | `age >= 65 OR is_disabled == True` | ⚠️ | Screener has general disability fields but no detailed ADL assessment; CCAD requires professional nursing assessment of specific ADL limitations. For applicants 65+, `is_disabled` is not required as a proxy — seniors may need ADL assistance without being marked as disabled. For applicants under 65, `is_disabled` (covering `disabled`, `long_term_disability`, and `visually_impaired`) is used as a proxy. | CCSE Handbook §3000 |
| 4 | Texas residency | — | Handled by TX white label association | ✅ | Not evaluated separately — CCAD is associated exclusively with the TX white label, so non-TX screens are filtered out before this check applies. | CCSE Handbook §3000 |
| 5 | Must not be residing in a nursing facility | — | — | ❌ | **Gap**: `housing_situation` field does not exist in the screener | CCSE Handbook §3000 |
| 6 | Medicaid eligible or categorically eligible | `has_medicaid`, `has_snap`, `has_ssi`, `has_tanf` | `has_medicaid OR has_snap OR has_ssi OR has_tanf` | ✅ | Overlaps with Criterion 2 categorical path; listed separately for clarity | CCSE Handbook §3000 |
| 7 | Asset limit: $2,000 individual / $3,000 couple (Medicaid standards) | `household_assets` | Not enforced | ⚠️ | **Gap (not enforced)**: Asset exemptions (home equity, one vehicle, burial funds) are complex and not fully captured. A warning message is shown to users instead. | CCSE Handbook §3000 |
| 8 | At risk of nursing facility placement without services | — | Clinical determination | ❌ | No screener field captures nursing facility risk level | CCSE Handbook §3000 |
| 9 | U.S. citizenship or qualified immigration status | `legal_status` | Via `legal_status_required` config filter | ✅ | Per CCSE §3110: most CCSE services are available regardless of immigration status; only Community Attendant Services (CAS) and waiver services require citizenship/identity verification. Config includes all statuses (citizen, gc_5plus, gc_5less, refugee, otherWithWorkPermission, non_citizen). Warning message surfaces the CAS/waiver caveat. | CCSE Handbook §3110 |
| 10 | No asset transfers below fair market value within lookback period | — | Medicaid 60-month lookback | ❌ | No screener field captures asset transfer history | Medicaid asset transfer rules |
| 11 | Medical necessity for home and community-based services | — | Professional assessment | ❌ | Medical necessity is determined by healthcare professional, not self-reported screener data | CCSE Handbook §3000 |
| 12 | Must choose CCAD over nursing facility placement | — | Applicant preference | ❌ | Determined during application process, not captured in screener | CCSE Handbook §3000 |
| 13 | Services available in applicant's geographic area | — | — | ❌ | No data on service availability or waiting lists by region; waiting list information is surfaced via program config | CCSE Handbook §2000 |
| 14 | No responsible party able to provide necessary care | — | Informal caregiver assessment | ❌ | No field captures availability of informal caregivers or family support | CCSE Handbook §3000 |
| 15 | Must not already be receiving CCAD | `has_ccad` | `has_ccad != True` | ✅ | `has_ccad` field to be added to Screen model during implementation, following the same pattern as `has_ccs`, `has_tx_dart`, etc. | — |

## Coverage

- **Evaluable**: 6 of 14 criteria (43%)
- **Summary**: The evaluable criteria include age requirements, income limits with categorical eligibility (300% FPL or SSI/TANF/SNAP/Medicaid), citizenship/immigration status via config filter, and duplicate enrollment check (requires adding `has_ccad` to the Screen model during implementation). Texas residency is handled automatically by the TX white label. Critical gaps include housing situation (no `housing_situation` field in screener), detailed ADL functional assessment, nursing facility risk determination, asset evaluation with Medicaid exemptions, and asset transfer history. The most significant limitation is the inability to perform detailed functional assessment and asset evaluation, both of which are core CCAD eligibility requirements.

## Benefit Value

- **Single value estimate**: $10,000/year
- **Range estimate**: $5,000–$20,000/year

**Methodology**: CCAD is a service bundle, not a cash transfer. Value is derived from the cost of services the state purchases on behalf of recipients.

The program's hard ceiling is the daily cost of nursing facility placement (~$193/day in TX, ~$70,000/year), per [CCSE Handbook Appendix II](https://www.hhs.texas.gov/handbooks/community-care-services-eligibility-handbook/appendix-ii-cost-limit-purchased-services).

The dominant service is **Primary Home Care (PHC)** — personal care attendants. Texas reimburses providers at ~$17/hour (based on the $13.00/hr base attendant wage + 14% payroll taxes/benefits + administrative component per the [Sept 2025 rate action](https://pfd.hhs.texas.gov/sites/default/files/documents/long-term-svcs/2025/9-1-2025-phc-rates.pdf)). The [CCSE Handbook §4600](https://www.hhs.texas.gov/handbooks/community-care-services-eligibility-handbook/4600-primary-home-care-community-attendant-services) authorizes 6–50 hours/week; a typical recipient receives ~15 hrs/week, yielding ~$13,260/year in PHC alone. Adding supplemental services (home-delivered meals ~$1,200–2,000/yr, emergency response ~$400/yr) suggests a realistic midpoint of ~$14,000–15,000/year for moderate-need recipients. The $10,000 single-value estimate is intentionally conservative to account for lower-intensity recipients (6–12 hrs/week) who pull the average down.

**Value Estimate Sources**:
- [CCSE Handbook Appendix II — Cost Limit for Purchased Services](https://www.hhs.texas.gov/handbooks/community-care-services-eligibility-handbook/appendix-ii-cost-limit-purchased-services)
- [CCSE Handbook §4600 — Primary Home Care and Community Attendant Services](https://www.hhs.texas.gov/handbooks/community-care-services-eligibility-handbook/4600-primary-home-care-community-attendant-services)
- [Texas HHS 2025 Attendant Rate Action (effective Sept 1, 2025)](https://pfd.hhs.texas.gov/sites/default/files/documents/long-term-svcs/2025/9-1-2025-phc-rates.pdf)
- [Nursing Home Costs by State — Medicaid Planning Assistance](https://www.medicaidplanningassistance.org/nursing-home-costs/)
- [Adult Day Care Costs 2026 — SeniorLiving.org](https://www.seniorliving.org/adult-day-care/costs/)

## Sources

- [Texas HHS Community Care Services Eligibility (CCSE) Handbook](https://www.hhs.texas.gov/laws-regulations/handbooks/case-worker-community-care-aged-disabled-handbook)
- [CCAD Program Overview - PayingForSeniorCare.com](https://www.payingforseniorcare.com/texas/ccad)
- [CCAD Eligibility Requirements](https://www.payingforseniorcare.com/texas/ccad#Eligibility_Guidelines)
- [CCAD Covered Services](https://www.payingforseniorcare.com/texas/ccad#Benefits_and_Services)
- [CCAD Application Process](https://www.payingforseniorcare.com/texas/ccad#How_to_Apply_Learn_More)
- [CCSE Income Eligibility §3300](https://www.hhs.texas.gov/handbooks/community-care-services-eligibility-handbook/3300-income-eligibility)
- [CCSE Verification Procedures §3400](https://www.hhs.texas.gov/handbooks/community-care-services-eligibility-handbook/3400-verification-procedures)

## Test Scenarios

Scenarios marked `[validation]` are included in `tx_ccad.json` as automated validations run in CI. All scenarios are covered by unit tests in `programs/programs/tx/ccad/tests/test_ccad.py`. All scenarios are used for Playwright QA against local/staging/prod.

---

### Scenario 1: 65-Year-Old Retiree with Social Security Income Below 300% FPL `[validation]`

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
- **Person 1**: DOB `March 2005` (age 21), Head of Household, U.S. Citizen, has disability (`disabled = True`), SSDI `$3,765/month` ($45,180/year = exactly 300% FPL for household of 1 in 2025), no insurance

**Why this matters**: Tests both minimum boundaries simultaneously — youngest possible qualifying age and highest allowable income. Ensures no rounding errors at the precise income threshold.

---

### Scenario 3: 70-Year-Old with Income Exactly at 300% FPL

**Checks**: Income exactly at the threshold qualifies ("at or below")
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `75201`, County `Dallas County`
- **Household**: 1 person
- **Person 1**: DOB `January 1956` (age 70), Head of Household, U.S. Citizen, Social Security Retirement `$3,765/month` ($45,180/year = exactly 300% FPL for 2025), no insurance, no current benefits

**Why this matters**: Confirms the boundary condition is inclusive — applicants at exactly 300% FPL must not be incorrectly excluded.

---

### Scenario 4: 72-Year-Old with Income Just Above 300% FPL `[validation]`

**Checks**: Income exceeding threshold is correctly rejected
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `75201`, County `Dallas County`
- **Household**: 1 person
- **Person 1**: DOB `January 1954` (age 72), Head of Household, U.S. Citizen, Social Security Retirement `$4,900/month`, no disability, no insurance, no current benefits

**Why this matters**: Ensures the income ceiling is enforced — prevents ineligible applicants from proceeding.

---

### Scenario 5: 21-Year-Old with Disability at Exact Minimum Age

**Checks**: Age threshold is inclusive (>= 21, not > 21) for disabled applicants
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `75001`, County `Collin`
- **Household**: 1 person
- **Person 1**: DOB `March 2005` (age 21), Head of Household, U.S. Citizen, has disability (`disabled = True`), SSI/SSDI `$943/month`, Medicaid

**Why this matters**: Confirms no off-by-one error in age calculation for the disability pathway minimum age.

---

### Scenario 6: 19-Year-Old with Disability — Below Minimum Age

**Checks**: Under-21 applicants are ineligible even with disability and qualifying income
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `75201`, County `Dallas`
- **Household**: 1 person
- **Person 1**: DOB `April 2007` (age 19), Head of Household, U.S. Citizen, has disability (`disabled = True`), SSI `$943/month`, no insurance, no current benefits

**Why this matters**: Validates the age gate for the disability pathway — a 19-year-old with disability does not qualify.

---

### Scenario 7: Already Receiving CCAD — Duplicate Benefit Check

**Checks**: Current CCAD recipients are excluded from re-enrollment
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `78701`, County `Travis`
- **Household**: 1 person
- **Person 1**: DOB `January 1961` (age 65), Head of Household, U.S. Citizen, no disability, Social Security Retirement `$1,200/month`, Medicaid, `has_ccad = True`

**Why this matters**: Prevents duplicate enrollment — someone already receiving CCAD should not be shown as newly eligible.

---

### Scenario 8: Mixed Household — Eligible Senior with Ineligible Adult Child

**Checks**: CCAD eligibility is per-individual, not household-wide
**Expected**: Eligible (for the senior)

**Steps**:
- **Location**: ZIP `78701`, County `Travis`
- **Household**: 2 people
- **Person 1 (Head)**: DOB `January 1958` (age 68), no disability, Social Security Retirement `$1,800/month`, Medicare, no current benefits, lives at home
- **Person 2 (Adult Child)**: DOB `June 1981` (age 44), no disability, Employment `$2,500/month`, employer insurance, no current benefits

**Why this matters**: Confirms individual-level evaluation within multi-member households and that combined household income is correctly applied to the eligible member.

---

### Scenario 9: Married Couple — Both 65+, Combined Income Below 300% FPL

**Checks**: Multiple eligible members in one household; income evaluated at household size of 2
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `78701`, County `Travis`
- **Household**: 2 people
- **Person 1 (Head)**: DOB `January 1959` (age 67), Social Security Retirement `$1,200/month`, no disability, no insurance, no current benefits
- **Person 2 (Spouse)**: DOB `June 1960` (age 65), Social Security Retirement `$1,000/month`, no disability, no insurance, no current benefits

**Why this matters**: Verifies the system evaluates combined household income against the correct FPL threshold for a 2-person household and recognizes both spouses as independently eligible.

---

### Scenario 10: 21-Year-Old with December Birthday — Age Calculation Edge Case

**Checks**: Age calculated correctly when birth month hasn't occurred yet in the current year
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `78701`, County `Travis`
- **Household**: 1 person
- **Person 1**: DOB `December 2004` (age 21 — birthday hasn't occurred yet in 2026), Head of Household, U.S. Citizen, has disability (`disabled = True`), SSDI `$1,200/month` ($14,400/year), no insurance

**Why this matters**: Ensures age calculation doesn't prematurely advance the applicant to 22 before their birthday. At exactly 21 with a disability, this is a critical boundary.

---

### Scenario 11: Categorically Eligible — SNAP Recipient Above 300% FPL `[validation]`

**Checks**: Categorical eligibility path — SNAP recipient qualifies regardless of income
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `78701`, County `Travis`
- **Household**: 1 person
- **Person 1**: DOB `January 1958` (age 68), Head of Household, U.S. Citizen, Social Security Retirement `$4,500/month` (above 300% FPL), no disability, no insurance, currently receiving SNAP (`has_snap = True`)

**Why this matters**: Confirms that categorical eligibility (SNAP) overrides the income test — a senior above 300% FPL who receives SNAP should still qualify.

---

### Scenario 12: TANF Recipient Above 300% FPL — Categorical Bypass

**Checks**: TANF (household-level) bypasses the income test
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `78701`, County `Travis County`
- **Household**: 1 person
- **Person 1**: DOB `January 1958` (age 68), Head of Household, U.S. Citizen, Social Security Retirement `$4,500/month` (above 300% FPL), no insurance, `has_tanf = True`

**Why this matters**: Confirms TANF (a household-level benefit) bypasses the income test independently of SNAP. Scenario 11 covers SNAP; this isolates TANF.

---

### Scenario 13: Medicaid Recipient Above 300% FPL — Categorical Bypass (No SSI)

**Checks**: Member-level Medicaid insurance alone bypasses the income test
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `78701`, County `Travis County`
- **Household**: 1 person
- **Person 1**: DOB `January 1958` (age 68), Head of Household, U.S. Citizen, Social Security Retirement `$4,500/month` (above 300% FPL), Medicaid insurance, no SSI income

**Why this matters**: Scenario 5 has both Medicaid and SSI — this isolates Medicaid as the sole categorical trigger, confirming it works independently without SSI income.

---

### Scenario 14: Non-Age-Eligible Member Has Medicaid — Should Not Bypass Income Test

**Checks**: Medicaid belonging to a non-age-eligible member does not grant categorical eligibility to the age-eligible member
**Expected**: Not eligible (income above 300% FPL, only the ineligible member has Medicaid)

**Steps**:
- **Location**: ZIP `78701`, County `Travis County`
- **Household**: 2 people
- **Person 1 (Head)**: DOB `January 1958` (age 68), no insurance, Social Security Retirement `$4,500/month` (above 300% FPL)
- **Person 2**: DOB `June 1990` (age 35), Medicaid, no income

**Why this matters**: Validates that Medicaid categorical eligibility is tied to the individual applicant — a younger household member's Medicaid should not bypass the income test for an unrelated age-eligible member.

---

### Scenario 15: `is_disabled` via `long_term_disability` — Not Directly Marked as Disabled

**Checks**: `is_disabled` composite field includes `long_term_disability = True` even when `disabled = False`
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `78701`, County `Travis`
- **Household**: 1 person
- **Person 1**: DOB `March 2003` (age 23), Head of Household, U.S. Citizen, `disabled = False`, `long_term_disability = True`, SSDI `$1,200/month`, no insurance

**Why this matters**: Validates that the `is_disabled` composite field correctly captures long-term disability as a qualifying signal, even when the direct `disabled` flag is not set. This is important for applicants who identify as having a long-term disability but haven't checked the general "disabled" box.
