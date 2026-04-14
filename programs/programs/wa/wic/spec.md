# Implement Women, Infants, and Children (WIC) Nutrition Program (WA)

## Program Details

- **Program**: Women, Infants, and Children (WIC) Nutrition Program
- **State**: WA
- **White Label**: wa
- **Research Date**: 2026-03-19
- **Spec Last Updated**: 2026-04-07 (revised per patmanson review)

## Eligibility Criteria

1. **Categorical requirement: Must be a pregnant woman, postpartum woman (up to 6 months after end of pregnancy), breastfeeding woman (up to 12 months), infant (under 1 year), or child (ages 1–4, up to but not including 5th birthday)**
   - Screener fields:
     - `age`
     - `pregnant`
     - `birth_year_month`
     - `relationship`
   - Source: 7 CFR 246.7(c)(1); https://doh.wa.gov/you-and-your-family/wic/wic-eligibility

2. **Income eligibility: Household gross income at or below 185% of the Federal Poverty Level (FPL)**
   - Note: **Income is NOT used as a disqualifying criterion when any household member is enrolled in SNAP, Medicaid, or TANF** (see Criterion 3). The income check must be bypassed entirely when adjunctive eligibility applies — do not fail eligibility based on income in those cases.
   - Screener fields:
     - `household_size`
     - `income_streams`
   - Source: 7 CFR 246.7(d)(1); https://doh.wa.gov/you-and-your-family/wic/wic-eligibility

3. **Adjunctive income eligibility: Participants in SNAP, Medicaid, or TANF are automatically income-eligible for WIC**
   - Note: When any of these programs is active for the household, income is not evaluated as a disqualifying criterion.
   - Screener fields:
     - `has_snap`
     - `has_medicaid`
     - `has_tanf`
   - Source: 7 CFR 246.7(d)(2)(iv); https://doh.wa.gov/you-and-your-family/wic/wic-eligibility

4. **Residency: Must reside in the state of Washington**
   - Screener fields:
     - `zipcode`
     - `county`
   - Source: 7 CFR 246.7(c)(1)(i); https://doh.wa.gov/you-and-your-family/wic/wic-eligibility

5. **Age requirement for children: Child must be under 5 years of age (before their 5th birthday)**
   - Screener fields:
     - `age`
     - `birth_year_month`
   - Source: 7 CFR 246.2; https://doh.wa.gov/you-and-your-family/wic/wic-eligibility

6. **Household must contain at least one categorically eligible member**
   - Note: WIC eligibility attaches to the categorically eligible individual. A household with no pregnant/postpartum women, infants, or children under 5 is not eligible even if it has adjunctive benefits.
   - Screener fields:
     - `age`
     - `pregnant`
     - `birth_year_month`
   - Source: 7 CFR 246.7(c)(1); https://doh.wa.gov/you-and-your-family/wic/wic-eligibility

7. **Nutritional risk determination: Must be found at nutritional risk by a WIC health professional** ⚠️ *data gap*
   - Note: In-person clinical assessment at WIC clinic; cannot be pre-screened. Rarely a barrier for otherwise eligible individuals.
   - Impact: Low
   - Source: 7 CFR 246.7(c)(4); https://doh.wa.gov/you-and-your-family/wic/wic-eligibility

8. **Postpartum/breastfeeding window** ⚠️ *data gap*
   - Note: Non-breastfeeding postpartum women are eligible up to 6 months after end of pregnancy; breastfeeding women up to 12 months. No postpartum or breastfeeding status field exists in the screener. Can be approximated from infant age if an infant under 1 year is present in the household.
   - Impact: Medium
   - Source: 7 CFR 246.7(c)(1)(ii)–(iii); https://doh.wa.gov/you-and-your-family/wic/wic-eligibility

9. **Must not be currently receiving WIC benefits (no duplicate participation)** ⚠️ *data gap*
   - Note: `has_wic` field exists but duplicate enrollment is better surfaced as informational rather than a hard eligibility exclusion in the screener.
   - Impact: Low
   - Source: https://www.law.cornell.edu/cfr/text/7/246.2

10. **Citizenship/immigration status: None required — all residents eligible regardless of status** ⚠️ *data gap*
    - Note: WIC has no citizenship or immigration requirement. No citizenship check should be applied in screening logic.
    - Impact: Low
    - Source: https://doh.wa.gov/you-and-your-family/wic/wic-eligibility

11. **Physical presence at WIC clinic for certification** ⚠️ *data gap*
    - Note: Procedural/administrative requirement; not a pre-screening criterion. Some telehealth exceptions available post-COVID.
    - Impact: Low
    - Source: https://doh.wa.gov/you-and-your-family/wic/wic-eligibility

12. **Homelessness/housing status: Homeless individuals are eligible; no permanent address required** ⚠️ *data gap*
    - Note: Non-restrictive; this is an affirmative inclusion. No action needed in screener logic.
    - Impact: Low
    - Source: https://doh.wa.gov/you-and-your-family/wic/wic-eligibility

## Benefit Value

- **Estimated value**: $50–$165 per eligible household member per month

**Methodology**: WIC provides food benefits that vary by participant category (pregnant/breastfeeding women, infants, and children each receive different monthly food packages). The national average WIC benefit was **$81.51 per participant per month in FY2024**. King County WA specifically reports approximately **$150/month for a family of two**.

For calculator purposes: multiply the number of WIC-eligible household members by $80, expressed as a range of $50–$165 per eligible person per month.

Note: the initial config estimated "$50–$75/month per participant" — this is too low and should be updated to $50–$165 per eligible person per month.

**Value Estimate Sources**:
- [CBPP — WIC average $81.51/participant/month in FY2024](https://www.cbpp.org/research/food-assistance/special-supplemental-nutrition-program-for-women-infants-and-children)
- [King County WA WIC (~$150/month for a family of two)](https://kingcounty.gov/en/dept/dph/health-safety/health-centers-programs-services/maternity-support-wic/wic-supplemental-nutrition-program)

## Implementation Coverage

- ✅ Evaluable criteria: 6
- ⚠️ Data gaps: 6

6 of 12 criteria can be evaluated with current screener fields. The core requirements — categorical status (pregnant/postpartum/infant/child under 5), income at or below 185% FPL, adjunctive eligibility via SNAP/Medicaid/TANF, Washington residency, age, and household composition — are all well-covered. The 6 data gaps are low/medium impact: nutritional risk assessment and physical clinic presence are procedural; citizenship/immigration and homelessness are non-restrictions (affirmative inclusions); postpartum window can be approximated from infant age; duplicate WIC participation is better handled as informational.

**Critical implementation note**: The income check must be bypassed entirely when adjunctive eligibility (SNAP, Medicaid, or TANF) is present. Applying the income test to adjunctive-eligible households would incorrectly exclude them.

## Research Sources

- [WA DOH WIC Eligibility and Income Limits](https://doh.wa.gov/you-and-your-family/wic/wic-eligibility)
- [USDA WIC Regulations — 7 CFR Part 246](https://www.ecfr.gov/current/title-7/subtitle-B/chapter-II/subchapter-A/part-246)
- [Cornell LII — 7 CFR 246.2 (Definitions: "child," "infant," "postpartum woman")](https://www.law.cornell.edu/cfr/text/7/246.2)
- [Cornell LII — 7 CFR 246.7 (Certification of participants)](https://www.law.cornell.edu/cfr/text/7/246.7)
- [CBPP WIC Research (FY2024 average benefit)](https://www.cbpp.org/research/food-assistance/special-supplemental-nutrition-program-for-women-infants-and-children)
- [King County WA WIC Supplemental Nutrition Program](https://kingcounty.gov/en/dept/dph/health-safety/health-centers-programs-services/maternity-support-wic/wic-supplemental-nutrition-program)

## Acceptance Criteria

[ ] Scenario 1 (Pregnant Woman, Low Income — Clearly Eligible): User should be **eligible**
[ ] Scenario 2 (Child at 4 Years 11 Months, Income Exactly at 185% FPL): User should be **eligible**
[ ] Scenario 3 (Household of 3, Income $1 Below 185% FPL): User should be **eligible**
[ ] Scenario 4 (Household of 4, Income Exactly at 185% FPL): User should be **eligible**
[ ] Scenario 5 (Household of 2, Income $1 Above 185% FPL, No Adjunctive): User should be **ineligible**
[ ] Scenario 6 (Infant Exactly Age 1 — Eligible as Child): User should be **eligible**
[ ] Scenario 7 (Infant Under 1 Year Old — Eligible as WIC Infant): User should be **eligible**
[ ] Scenario 8 (3-Year-Old Child — Clearly Eligible): User should be **eligible**
[ ] Scenario 9a (Pregnant Woman, Valid WA ZIP Code): User should be **eligible**
[ ] Scenario 9b (Pregnant Woman, Non-WA ZIP Code): User should be **ineligible**
[ ] Scenario 10 (Household Already Receiving WIC): User should be **ineligible**
[ ] Scenario 11 (Adults Only, No Pregnancy — No Categorically Eligible Members): User should be **ineligible**
[ ] Scenario 12 (Mixed Household — Eligible Toddler, Ineligible 6-Year-Old): User should be **eligible**
[ ] Scenario 13 (Pregnant Woman, Infant, and Toddler — All Categorically Eligible): User should be **eligible**
[ ] Scenario 14 (Child at 4 Years 11 Months — Near Age Cutoff): User should be **eligible**
[ ] Scenario 15a (SNAP Recipient, Child Under 5 — Adjunctive Auto-Qualify): User should be **eligible**
[ ] Scenario 15b (Medicaid Recipient, Child Under 5 — Adjunctive Auto-Qualify): User should be **eligible**
[ ] Scenario 15c (TANF Recipient, Child Under 5 — Adjunctive Auto-Qualify): User should be **eligible**

## Test Scenarios

> ⚠️ **Income threshold note**: Scenarios involving income at or near the 185% FPL boundary use 2026 estimates derived from the 2026 HHS poverty guidelines (HH of 4 confirmed at $5,088/month per WA DOH). Verify all boundary thresholds against [https://doh.wa.gov/you-and-your-family/wic/wic-eligibility](https://doh.wa.gov/you-and-your-family/wic/wic-eligibility) before running threshold-sensitive tests. Approximate 2026 185% FPL monthly values: HH of 1 ≈ $2,503, HH of 2 ≈ $3,364, HH of 3 ≈ $4,226, HH of 4 = $5,088.

---

### Scenario 1: Pregnant Woman with Low Income — Clearly Eligible ⭐ Priority QA
**What we're checking**: Pregnant woman in a 2-person household with income well below 185% FPL — validates the most common WIC eligibility pathway
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `June 1996` (age 29), Relationship: Head of Household, Pregnant: `Yes`, Employment income: `$1,800` per month (well below 185% FPL for HH of 2: ~$3,364/month)
- **Person 2**: Birth month/year: `March 2019` (age 7), Relationship: Child, No income
- **Current Benefits**: Do NOT select SNAP, Medicaid, or TANF

**Why this matters**: Validates the core categorical + income eligibility pathway. Pregnancy is the most straightforward categorical qualifier. With income well below the threshold, this confirms both criteria work in combination.

---

### Scenario 2: Child at 4 Years 11 Months, Income at Exactly 185% FPL — Minimally Eligible
**What we're checking**: Child just under the age-5 cutoff with household income at the exact 185% FPL boundary — validates both the age upper boundary and the income ceiling (inclusive ≤)
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98001`, Select county `King`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `June 1990` (age 35), Relationship: Head of Household, Employment income: `$3,364` per month (approximately 185% FPL for HH of 2 in 2026 — verify against WA DOH income limits page before running)
- **Person 2**: Birth month/year: `May 2021` (age 4 years 11 months — will turn 5 in May 2026), Relationship: Child, No income
- **Current Benefits**: Do NOT select SNAP, Medicaid, or TANF

**Why this matters**: Tests two boundaries simultaneously: the child's age (just under 5) and the income ceiling (exactly at 185% FPL). Both should be inclusive. If either gate is misconfigured as strictly less than, this scenario will catch it.

---

### Scenario 3: Household of 3 with Income $1 Below 185% FPL — Just Under Threshold
**What we're checking**: A household of 3 with income just below the 185% FPL ceiling — validates the income threshold is correctly applied and inclusive
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98103`, Select county `King`
- **Household**: Number of people: `3`
- **Person 1**: Birth month/year: `June 1988` (age 37), Relationship: Head of Household, Employment income: `$4,225` per month (approximately $1 below 185% FPL for HH of 3 in 2026 — verify against WA DOH income limits page)
- **Person 2**: Birth month/year: `September 1990` (age 35), Relationship: Spouse, No income
- **Person 3**: Birth month/year: `January 2024` (age 2), Relationship: Child, No income
- **Current Benefits**: Do NOT select SNAP, Medicaid, or TANF

**Why this matters**: Confirms the income ceiling is applied correctly for a 3-person household. The $1 buffer ensures we're testing the threshold itself, not just a comfortably-below value.

---

### Scenario 4: Household of 4 at Exactly 185% FPL — Boundary Eligible
**What we're checking**: 4-person household with income exactly equal to 185% FPL — confirms the threshold is inclusive (≤, not <)
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `4`
- **Person 1**: Birth month/year: `June 1988` (age 37), Relationship: Head of Household, Employment income: `$5,088` per month (exactly 185% FPL for HH of 4 in 2026 — confirmed per WA DOH)
- **Person 2**: Birth month/year: `September 1990` (age 35), Relationship: Spouse, No income
- **Person 3**: Birth month/year: `January 2024` (age 2), Relationship: Child, No income
- **Person 4**: Birth month/year: `March 2025` (age 1), Relationship: Child, No income
- **Current Benefits**: Do NOT select SNAP, Medicaid, or TANF

**Why this matters**: Validates the income threshold is evaluated as ≤ 185% FPL (not strictly <). At exactly $5,088/month for a 4-person household, this is the confirmed 2026 WIC income ceiling.

---

### Scenario 5: Household of 2 with Income $1 Above 185% FPL — Just Over Threshold ⭐ Priority QA
**What we're checking**: 2-person household with income just above the 185% FPL ceiling and no adjunctive benefits — confirms the income ceiling is enforced when no bypass applies
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `June 1990` (age 35), Relationship: Head of Household, Employment income: `$3,365` per month (approximately $1 above 185% FPL for HH of 2 in 2026 — verify against WA DOH income limits page)
- **Person 2**: Birth month/year: `May 2021` (age 4), Relationship: Child, No income
- **Current Benefits**: Do NOT select SNAP, Medicaid, or TANF

**Why this matters**: Confirms the income ceiling is a hard gate. With no adjunctive benefits, a household $1 over the limit must be denied. This pairs with Scenario 2 to confirm the boundary is enforced correctly in both directions.

---

### Scenario 6: Infant Exactly Age 1 — Eligible as Child
**What we're checking**: Infant who has just turned exactly 1 year old — confirms the age-1 minimum for the "child" category and that the infant-to-child transition contains no eligibility gap
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `June 1993` (age 32), Relationship: Head of Household, Employment income: `$2,000` per month
- **Person 2**: Birth month/year: `April 2025` (age exactly 1 year — born this month last year), Relationship: Child, No income
- **Current Benefits**: Do NOT select SNAP, Medicaid, or TANF

**Why this matters**: Children ages 1–4 are categorically eligible for WIC. Infants under 1 are also eligible but counted separately. A child turning exactly 1 transitions from the "infant" to "child" WIC category — both are eligible, and this confirms the age-1 boundary is not treated as a gap or exclusion.

---

### Scenario 7: Infant Under 1 Year Old — Eligible as WIC Infant
**What we're checking**: Infant clearly under 1 year old — validates the infant eligibility pathway
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `June 1993` (age 32), Relationship: Head of Household, Employment income: `$2,000` per month
- **Person 2**: Birth month/year: `January 2026` (age ~3 months), Relationship: Child, No income
- **Current Benefits**: Do NOT select SNAP, Medicaid, or TANF

**Why this matters**: Infants under 1 year are a core WIC categorical group. Validates the infant pathway works independently of the child pathway.

---

### Scenario 8: 3-Year-Old Child — Clearly Eligible
**What we're checking**: Child at age 3, well within the child eligibility range — straightforward mid-range eligibility check
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `June 1990` (age 35), Relationship: Head of Household, Employment income: `$2,500` per month
- **Person 2**: Birth month/year: `January 2023` (age 3), Relationship: Child, No income
- **Current Benefits**: Do NOT select SNAP, Medicaid, or TANF

**Why this matters**: A non-boundary check for the child age range. Avoids edge cases to confirm basic child eligibility functions as expected.

---

### Scenario 9a: Pregnant Woman in Valid WA ZIP Code — Eligible Location ⭐ Priority QA
**What we're checking**: Confirms the residency check passes for a valid Washington ZIP code
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1993` (age 33), Relationship: Head of Household, Pregnant: `Yes`, Employment income: `$1,800` per month
- **Current Benefits**: Do NOT select SNAP, Medicaid, or TANF

**Why this matters**: Confirms the WA residency check passes for a valid in-state ZIP. Run alongside Scenario 9b for a paired location test.

---

### Scenario 9b: Pregnant Woman in Non-WA ZIP Code — Location Invalid
**What we're checking**: Confirms the residency check correctly denies eligibility for an out-of-state address
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `97201` (Portland, OR), Select county `Multnomah`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1993` (age 33), Relationship: Head of Household, Pregnant: `Yes`, Employment income: `$1,800` per month
- **Current Benefits**: Do NOT select SNAP, Medicaid, or TANF

**Why this matters**: WA WIC is state-administered. A user with an Oregon address must not receive a WA WIC eligibility result. This is the natural counterpart to Scenario 9a.

---

### Scenario 10: Household Already Receiving WIC — Exclusion Check
**What we're checking**: Household with `has_wic` indicated — validates that existing WIC participants are not shown as newly eligible
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `June 1993` (age 32), Relationship: Head of Household, Employment income: `$1,800` per month
- **Person 2**: Birth month/year: `January 2024` (age 2), Relationship: Child, No income
- **Current Benefits**: Select `WIC`

**Why this matters**: Confirms that households already receiving WIC are correctly handled and not shown as newly eligible.

---

### Scenario 11: Adults Only, No Pregnancy — No Categorically Eligible Members
**What we're checking**: Household with no pregnant women, infants, or children under 5 — confirms WIC does not appear even when adjunctive benefits are present
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `June 1985` (age 40), Relationship: Head of Household, Employment income: `$1,800` per month
- **Person 2**: Birth month/year: `March 1988` (age 38), Relationship: Spouse, No income
- **Current Benefits**: Select `SNAP`

**Why this matters**: Even SNAP adjunctive eligibility does not override the categorical requirement. A household with no pregnant/postpartum women, infants, or children under 5 is not eligible for WIC regardless of income or benefit status. This is an important counterpart to the adjunctive scenarios.

---

### Scenario 12: Mixed Household — Eligible Toddler, Ineligible 6-Year-Old ⭐ Priority QA
**What we're checking**: Household with both an age-eligible child (under 5) and an age-ineligible older child — confirms the presence of an ineligible member does not disqualify the eligible one
**Expected**: Eligible (toddler qualifies; 6-year-old does not)

**Steps**:
- **Location**: Enter ZIP code `98103`, Select county `King`
- **Household**: Number of people: `3`
- **Person 1**: Birth month/year: `June 1990` (age 35), Relationship: Head of Household, Employment income: `$2,800` per month
- **Person 2**: Birth month/year: `January 2023` (age 3), Relationship: Child, No income
- **Person 3**: Birth month/year: `February 2020` (age 6), Relationship: Child, No income
- **Current Benefits**: Do NOT select SNAP, Medicaid, or TANF

**Why this matters**: Tests that WIC eligibility is assessed per eligible household member, not per household unit. A 6-year-old aging out of WIC should not cause the 3-year-old to lose eligibility.

---

### Scenario 13: Pregnant Woman, Infant, and Toddler — All Categorically Eligible
**What we're checking**: Household where all child/maternal members are categorically eligible — confirms multi-member categorical eligibility works
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `4`
- **Person 1**: Birth month/year: `June 1993` (age 32), Relationship: Head of Household, Pregnant: `Yes`, Employment income: `$2,500` per month
- **Person 2**: Birth month/year: `March 1995` (age 31), Relationship: Spouse, No income
- **Person 3**: Birth month/year: `March 2025` (age ~13 months), Relationship: Child, No income
- **Person 4**: Birth month/year: `January 2023` (age 3), Relationship: Child, No income
- **Current Benefits**: Do NOT select SNAP, Medicaid, or TANF

**Why this matters**: Validates that a household with multiple categorically eligible members (pregnant woman + infant + toddler) is correctly identified as eligible.

---

### Scenario 14: Child at 4 Years 11 Months — Near Age Cutoff
**What we're checking**: Child at 4 years 11 months (1 month before turning 5) — validates the age-5 cutoff is enforced correctly and that children just before the cutoff remain eligible
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `June 1990` (age 35), Relationship: Head of Household, Employment income: `$2,500` per month
- **Person 2**: Birth month/year: `May 2021` (age 4 years 11 months — will turn 5 in May 2026), Relationship: Child, No income
- **Current Benefits**: Do NOT select SNAP, Medicaid, or TANF

**Why this matters**: Since the screener collects birth month/year (not exact day), a child born in May 2021 is currently 4 years 11 months old and is still eligible. This tests the upper age boundary without requiring an exact birth date. (Note: an original scenario tested "child turns 5 tomorrow" — that is impractical given we only collect birth month. "4 years 11 months" is the correct proxy.)

---

### Scenario 15a: SNAP Recipient with Child Under 5 — Adjunctive Auto-Qualify ⭐ Priority QA
**What we're checking**: Household with income above 185% FPL but receiving SNAP — validates adjunctive eligibility bypasses the income check
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `3`
- **Person 1**: Birth month/year: `June 1988` (age 37), Relationship: Head of Household, Employment income: `$4,500` per month (above 185% FPL for HH of 3: ~$4,226/month)
- **Person 2**: Birth month/year: `September 1990` (age 35), Relationship: Spouse, No income
- **Person 3**: Birth month/year: `January 2024` (age 2), Relationship: Child, No income
- **Current Benefits**: Select `SNAP` — do NOT select Medicaid or TANF
- **Note**: SNAP may not yet be programmed for the WA white label. This scenario documents the expected behavior for when adjunctive eligibility is implemented.

**Why this matters**: Adjunctive eligibility via SNAP is one of the most critical pathways in WIC. A household over the income threshold must still qualify if they receive SNAP. This is the primary test of the income bypass logic.

---

### Scenario 15b: Medicaid Recipient with Child Under 5 — Adjunctive Auto-Qualify
**What we're checking**: Same income-over-threshold household as 15a, but qualifying via Medicaid alone — validates Medicaid independently triggers the income bypass
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `3`
- **Person 1**: Birth month/year: `June 1988` (age 37), Relationship: Head of Household, Employment income: `$4,500` per month (above 185% FPL for HH of 3)
- **Person 2**: Birth month/year: `September 1990` (age 35), Relationship: Spouse, No income
- **Person 3**: Birth month/year: `January 2024` (age 2), Relationship: Child, No income
- **Current Benefits**: Select `Medicaid` — do NOT select SNAP or TANF

**Why this matters**: Validates Medicaid is independently recognized as an adjunctive eligibility trigger per 7 CFR 246.7(d)(2)(iv), separate from SNAP.

---

### Scenario 15c: TANF Recipient with Child Under 5 — Adjunctive Auto-Qualify
**What we're checking**: Same income-over-threshold household as 15a, but qualifying via TANF alone — validates TANF independently triggers the income bypass
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `3`
- **Person 1**: Birth month/year: `June 1988` (age 37), Relationship: Head of Household, Employment income: `$4,500` per month (above 185% FPL for HH of 3)
- **Person 2**: Birth month/year: `September 1990` (age 35), Relationship: Spouse, No income
- **Person 3**: Birth month/year: `January 2024` (age 2), Relationship: Child, No income
- **Current Benefits**: Select `TANF` — do NOT select SNAP or Medicaid

**Why this matters**: Validates TANF is independently recognized as an adjunctive eligibility trigger. All three adjunctive programs (SNAP, Medicaid, TANF) must be tested individually to confirm each one bypasses the income check on its own.

---

## Source Documentation

- https://doh.wa.gov/you-and-your-family/wic/wic-eligibility
- https://www.cbpp.org/research/food-assistance/special-supplemental-nutrition-program-for-women-infants-and-children
- https://kingcounty.gov/en/dept/dph/health-safety/health-centers-programs-services/maternity-support-wic/wic-supplemental-nutrition-program
- https://www.law.cornell.edu/cfr/text/7/246.2
- https://www.law.cornell.edu/cfr/text/7/246.7
