# Implement Lifeline phone services (WA) Program

## Program Details

* **Program**: Lifeline phone services
* **State**: WA
* **White Label**: wa
* **Research Date**: 2026-05-01

## Eligibility Criteria

1. **Household income must be at or below 135% of the Federal Poverty Guidelines**
   * Screener fields:
     * `household_size`
     * `income_streams`
   * Source: USAC Lifeline National Verifier – Do I Qualify? (Income-Based Eligibility); 47 CFR § 54.409(a)(1); https://www.lifelinesupport.org/how-to-qualify/
2. **Program-based eligibility: Participation in Medicaid (Apple Health in WA)**
   * Screener fields:
     * `has_medicaid`
   * Note: WA brands Medicaid as "Apple Health" — display name may need localization in UI copy but the field is standard.
   * Source: WA HCA Lifeline Phone Services – Eligibility Criteria; USAC Lifeline Do I Qualify; 47 CFR § 54.409(a)(2); https://www.lifelinesupport.org/how-to-qualify/
3. **Program-based eligibility: Participation in SNAP (Supplemental Nutrition Assistance Program)**
   * Screener fields:
     * `has_snap`
   * Source: USAC Lifeline National Verifier – Do I Qualify; 47 CFR § 54.409(a)(2)(i); https://www.lifelinesupport.org/how-to-qualify/
4. **Program-based eligibility: Participation in Supplemental Security Income (SSI)**
   * Screener fields:
     * `has_ssi`
   * Source: USAC Lifeline National Verifier – Do I Qualify; 47 CFR § 54.409(a)(2)(ii); https://www.lifelinesupport.org/how-to-qualify/
5. **Program-based eligibility: Participation in Federal Public Housing Assistance (Section 8/HCV)**
   * Screener fields:
     * `has_section_8`
   * Note: Section 8/HCV is not in PolicyEngine's Lifeline categorical eligibility list (see PolicyEngine Implementation Notes below). Eligibility for this pathway must be enforced at the screener level via `has_section_8`.
   * Source: USAC Lifeline National Verifier – Do I Qualify; 47 CFR § 54.409(a)(2)(iii); https://www.lifelinesupport.org/how-to-qualify/
6. **Program-based eligibility: Participation in TANF (Temporary Assistance for Needy Families)**
   * Screener fields:
     * `has_tanf`
   * Source: USAC Lifeline National Verifier – Do I Qualify; 47 CFR § 54.409(a)(2); https://www.lifelinesupport.org/how-to-qualify/
   * Note: PolicyEngine's categorical eligibility for Lifeline does not include TANF for non-tribal households (see PolicyEngine Implementation Notes below). TANF-only eligibility may not trigger via the PolicyEngine path; screener-level override may be needed via `has_tanf`.
7. **Program-based eligibility: Participation in WIC (Special Supplemental Nutrition Program for Women, Infants, and Children)**
   * Screener fields:
     * `has_wic`
   * Source: USAC Lifeline National Verifier – Do I Qualify; https://www.lifelinesupport.org/how-to-qualify/
   * Note: WIC is not in PolicyEngine's Lifeline categorical eligibility list (see PolicyEngine Implementation Notes below). WIC-only eligibility may not trigger via the PolicyEngine path; screener-level override may be needed via `has_wic`.
8. **Applicant must reside in Washington State**
   * Screener fields:
     * `zipcode`
     * `county`
   * Source: WA HCA Lifeline Phone Services; 47 CFR § 54.410(b); https://www.lifelinesupport.org/how-to-qualify/
9. **Program-based eligibility: Participation in Pell Grant program (current award year)** ⚠️ *data gap*

* Note: `has_pell_grant` is not a field in the screener schema. No screener field captures Pell Grant participation. Additionally, Pell Grant is not in PolicyEngine's Lifeline categorical eligibility list (see PolicyEngine Implementation Notes below).
* Source: USAC Lifeline National Verifier – Do I Qualify; https://www.lifelinesupport.org/how-to-qualify/; 47 CFR § 54.409(a)(2)
* Impact: Low (Pell Grant recipients typically have low income and qualify via income pathway)

10. **Program-based eligibility: Participation in Veterans Pension and Survivors Benefit** ⚠️ *data gap*

* Note: The screener has a 'veteran' field on HouseholdMember and 'has_va' at the screen level, but these indicate veteran status or VA health care, not specifically Veterans Pension or Survivors Benefit receipt. Cannot distinguish between VA health care and VA pension/survivors benefits.
* Source: USAC Lifeline National Verifier – Do I Qualify; 47 CFR § 54.409(a)(2)(iv); https://www.lifelinesupport.org/how-to-qualify/
* Impact: Medium

11. **Program-based eligibility: Participation in Bureau of Indian Affairs General Assistance** ⚠️ *data gap*

* Note: No screener field captures BIA General Assistance participation. This is relevant for tribal members in Washington State.
* Source: USAC Lifeline National Verifier – Do I Qualify; 47 CFR § 54.409(a)(2); https://www.lifelinesupport.org/how-to-qualify/
* Impact: Low

12. **Program-based eligibility: Participation in Tribally-Administered TANF** ⚠️ *data gap*

* Note: The has_tanf field may partially capture this, but Tribally-Administered TANF is a distinct program. Cannot differentiate between state TANF and tribal TANF.
* Source: USAC Lifeline National Verifier – Do I Qualify; 47 CFR § 54.409(a)(2); https://www.lifelinesupport.org/how-to-qualify/
* Impact: Low

13. **Program-based eligibility: Participation in Food Distribution Program on Indian Reservations (FDPIR)** ⚠️ *data gap*

* Note: No screener field captures FDPIR participation.
* Source: USAC Lifeline National Verifier – Do I Qualify; 47 CFR § 54.409(a)(2); https://www.lifelinesupport.org/how-to-qualify/
* Impact: Low

14. **Applicant must not be an institutionalized person (e.g., in prison, nursing facility where Medicaid pays for care)** ⚠️ *data gap*

* Note: No screener field captures institutionalization status. This is an edge case for most screener users.
* Source: 47 CFR § 54.400(h) (household definition excludes certain institutional settings)
* Impact: Low

15. **Applicant must be a legal adult (18 years old or older) or emancipated minor** ⚠️ *data gap*

* Note: The screener does not capture if a minor has been emancipated. Evaluable (age>=18) with a partial gap; emancipated minor exception cannot be detected.
* Source: FCC FORM 5631; https://www.usac.org/wp-content/uploads/lifeline/documents/forms/LI_Worksheet_NVstates-1.pdf
* Screener field: `age`
* Impact: Medium

16. **Household must not currently receive Lifeline (one benefit per household rule)**

* Screener fields:
  * `has_lifeline`
* Note: Enforced at the screener level only — PolicyEngine's `is_lifeline_eligible` variable does not check existing Lifeline participation (see PolicyEngine Implementation Notes below). If `has_lifeline == true`, the household is excluded from eligibility.
* Source: 47 CFR § 54.409(c); 47 CFR § 54.400(h) (household definition)

## Benefit Value

* **Standard benefit**: $9.25/month ($111/year) discount applied to a qualifying phone or
  broadband service.
* **Enhanced Tribal benefit**: Up to $34.25/month ($411/year) for eligible subscribers
  residing on qualifying Tribal lands ($9.25 standard + $25 additional).
* **Calculator implementation**: Use **$111** as the annual benefit value (9.25 × 12).
  The frontend divides by 12 for monthly display.
* **Application**: Applied as a discount on the subscriber's monthly bill. Some
  WA-approved providers (e.g., Assurance Wireless, Access Wireless) offer free
  service plans that consume the full subsidy.
* **Note (data gap)**: The screener cannot verify residence on qualifying
  Tribal lands, so the standard $9.25/month ($111/year) is used as the default citable
  value. The Enhanced Tribal amount is mentioned in the description.
* **Source**: 47 CFR § 54.403(a)(1) (standard); 47 CFR § 54.403(a)(2)
  (Enhanced Tribal); WA HCA Lifeline Phone Services – Enhanced Lifeline.

## Implementation Coverage

* ✅ Evaluable criteria: 9
* ⚠️  Data gaps: 7

9 of 16 total eligibility criteria can be evaluated with current screener fields. The most critical evaluable criteria are: income at or below 135% FPL (income-based pathway), participation in qualifying programs (Medicaid, SNAP, SSI, TANF, WIC, Section 8), Washington State residency, and the one-Lifeline-per-household exclusion (`has_lifeline`). The 7 criteria that cannot be evaluated are: Pell Grant (no `has_pell_grant` field), tribal-specific programs (BIA General Assistance, FDPIR, Tribal TANF), and edge cases (institutionalization, Veterans Pension specifically, emancipated-minor exception). The evaluable criteria cover the vast majority of applicants since Medicaid, SNAP, SSI, and income-based qualification are the most common pathways.

## Research Sources

* [WA HCA Lifeline Phone Services – Eligibility Criteria (47 CFR § 54.409; RCW 80.36.470)](https://www.hca.wa.gov/about-hca/programs-and-initiatives/apple-health-medicaid/lifeline-phone-services#who-is-eligible)
* [WA HCA Lifeline Phone Services – Main Content (47 CFR § 54.400 et seq.)](https://www.hca.wa.gov/about-hca/programs-and-initiatives/apple-health-medicaid/lifeline-phone-services#main-content)
* [WA HCA Lifeline Phone Services – What Is Lifeline? (47 U.S.C. § 254; 47 CFR § 54.401)](https://www.hca.wa.gov/about-hca/programs-and-initiatives/apple-health-medicaid/lifeline-phone-services#what-is-lifeline)
* [WA HCA Lifeline Phone Services – How to Apply (47 CFR § 54.410)](https://www.hca.wa.gov/about-hca/programs-and-initiatives/apple-health-medicaid/lifeline-phone-services#how-do-I-apply)
* [WA HCA Lifeline Phone Services – Approved Service Providers in Washington State](https://www.hca.wa.gov/about-hca/programs-and-initiatives/apple-health-medicaid/lifeline-phone-services#lifeline-services-providers)
* [WA HCA Lifeline Phone Services – Enhanced Lifeline Benefits for Tribal Lands (47 CFR § 54.403(a)(2); 47 CFR § 54.400(e))](https://www.hca.wa.gov/about-hca/programs-and-initiatives/apple-health-medicaid/lifeline-phone-services#benefits-for-tribal-lands)
* [USAC Lifeline National Verifier – Do I Qualify? Federal Poverty Guidelines & Program-Based Eligibility (47 CFR § 54.409)](https://www.lifelinesupport.org/do-i-qualify/)
* [USAC Lifeline Support – Get Started: Application Steps & National Verifier Enrollment (47 CFR § 54.410)](https://www.lifelinesupport.org/get-started/)
* [Access Wireless – Lifeline Service Provider (Washington State Approved)](https://www.accesswireless.com/lifeline)
* [Assurance Wireless – Washington State Lifeline Free Government Phone Service](https://www.assurancewireless.com/lifeline-services/states/washington-lifeline-free-government-phone-service)

---

## Validation Scenarios

### Scenario 1: Single adult on SNAP with low income in Washington State

**What we're checking**: Clearly eligible applicant who qualifies via both income-based (below 135% FPL) and program-based (SNAP participation) eligibility, resides in WA, and does not already have Lifeline

**Expected**: Eligible, value: `111` (annual)

**Steps**:

* **Location**: Enter ZIP code `98101`, Select county `King County`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `June 1986` (age 39), Relationship: Head of Household, Citizenship: US Citizen, Has income: Yes, Employment income: `$1,200` per month, No other income sources, No health insurance
* **Current Benefits**: Select SNAP (food assistance) as a current benefit, Do NOT select Lifeline as a current benefit

---

### Scenario 2: Household of 2 with income just above 135% FPL - should NOT be eligible

**What we're checking**: Verifies that a 2-person household with gross annual income slightly above the 135% FPL threshold is correctly denied Lifeline eligibility when no qualifying programs are present. Combined income ($1,800 + $700) × 12 = $30,000/year vs. 2026 threshold of $29,214/year for household of 2.

**Expected**: Not eligible

**Steps**:

* **Location**: Enter ZIP code `98101`, Select county `King County`
* **Household**: Number of people: `2`
* **Person 1**: Birth month/year: `June 1980` (age 45), Relationship: Head of Household, Monthly employment income: `$1,800`
* **Person 2**: Birth month/year: `September 1982` (age 43), Relationship: Spouse, Monthly employment income: `$700`
* **Current Benefits**: Do NOT select any qualifying programs

---

### Scenario 3: Mixed household - head of household on Medicaid

**What we're checking**: Validates that Lifeline eligibility is determined at the household level — head of household participates in Medicaid (program-based eligible) while a second member has no qualifying programs, and combined household income remains below 135% FPL for household of 3. Combined income ($800 + $1,000) × 12 = $21,600/year vs. 2026 threshold of $36,882/year for household of 3.

**Expected**: Eligible, value: `111` (annual)

**Steps**:

* **Location**: Enter ZIP code `98103`, Select county `King County`
* **Household**: Number of people: `3`
* **Person 1 (Head)**: Birth month/year: `June 1986` (age 39), Employment income: `$800/month`, Currently on Medicaid
* **Person 2 (Spouse)**: Birth month/year: `September 1988` (age 37), Employment income: `$1,000/month`, No qualifying programs
* **Person 3 (Child)**: Birth month/year: `January 2018` (age 8), No income

---

### Scenario 4: SSI-only eligibility — senior with SSI as the sole qualifying program

**What we're checking**: Verifies that SSI participation alone (without SNAP, Medicaid, or other qualifying programs) triggers Lifeline eligibility via the program-based pathway. Tests the SSI categorical eligibility branch in isolation, since SSI is one of the three programs in PolicyEngine's non-tribal categorical eligibility list.

**Expected**: Eligible, value: `111` (annual)

**Steps**:

* **Location**: Enter ZIP code `98101`, Select county `King County`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `January 1960` (age 66), Relationship: Head of Household, Citizenship: US Citizen, Has income: Yes, SSI income: `$943` per month, No other income sources
* **Current Benefits**: Select `SSI (Supplemental Security Income)` as a current benefit, Do NOT select SNAP, Medicaid, or Lifeline

---

### Scenario 5: Household already receiving Lifeline — one-per-household exclusion

**What we're checking**: Validates that the one-per-household rule excludes a household already receiving Lifeline, even when they otherwise qualify via SNAP. Per 47 CFR § 54.409(c), only one Lifeline benefit is allowed per household. This rule is enforced at the screener level via `has_lifeline` (PolicyEngine does not check this).

**Expected**: Not eligible

**Steps**:

* **Location**: Enter ZIP code `98101`, Select county `King County`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `June 1980` (age 45), Relationship: Head of Household, Citizenship: US Citizen, Has income: Yes, Employment income: `$1,200` per month
* **Current Benefits**: Select `SNAP` as a current benefit, Select `Lifeline` as a current benefit (already receiving Lifeline phone service)

## PolicyEngine Implementation Notes

The following gaps and discrepancies were identified by reviewing scenarios against the PolicyEngine-US lifeline variable implementation (`policyengine_us/variables/gov/fcc/lifeline/`).

### FPL Values

PolicyEngine's parameters (`gov/hhs/fpg.yaml`) use:

| Year | FPL (1 person) | 135% threshold (HH1) | Per additional person |
| -- | -- | -- | -- |
| 2024 | $15,060 | $20,331/yr ($1,694.25/mo) | $5,380 |
| 2025 | $15,650 | $21,127.50/yr ($1,760.63/mo) | $5,500 |
| 2026 | $15,960 | $21,546/yr ($1,795.50/mo) | $5,680 |

### Programs Missing from PolicyEngine's Categorical Eligibility

PolicyEngine's `categorical_eligibility.yaml` for non-tribal households lists only: `medicaid`, `snap`, `ssi`. The following programs referenced in the eligibility criteria are NOT in PolicyEngine's non-tribal categorical eligibility list: TANF (tribal only), WIC, Section 8/HCV, Pell Grant.

### Age Requirement Not Enforced by PolicyEngine

PolicyEngine's `is_lifeline_eligible` variable does not check applicant age. The 18+ requirement must be enforced at the screener level.

### One-Per-Household Rule Not Enforced by PolicyEngine

The one-per-household rule depends entirely on screener-level `has_lifeline` field exclusion.

### No WA-Specific Implementation in PolicyEngine

Washington State uses the standard federal Lifeline benefit amount ($9.25/month standard, $34.25/month on qualifying Tribal lands).
