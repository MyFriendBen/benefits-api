# Implement Nurse-Family Partnership (KS) Program

## Program Details

* **Program**: Nurse-Family Partnership
* **State**: KS
* **White Label**: ks
* **Research Date**: 2026-06-19
* **Review Date**: 2026-06-28

## Eligibility Criteria

1. **Must be pregnant (first-time mother) - enrolled during pregnancy, ideally by 28th week of gestation**
   * Screener fields:
     * `pregnant`
   * Source: Changent NFP program description: 'NFP serves first-time birthing people during pregnancy'; HomVEE model profile: 'Pregnant individuals having their first baby'; Shawnee County NFP page: 'first-time moms and their babies'
2. **Must be a first-time parent (no previous live births)** ⚠️ *data gap*
   * Screener fields:
     * `num_children`
   * Source: Changent NFP description: 'first-time birthing people'; HomVEE: 'Pregnant individuals having their first baby'; Shawnee County: 'first-time moms'
   * Note: While we can approximate this by checking for existing children in the household, there is no screener field that directly asks 'Is this your first pregnancy?' or 'Have you had any previous live births?' Edge cases include: children from previous relationships not in the household, prior pregnancies that ended in miscarriage/stillbirth (which would still make someone eligible), adopted-out children, etc. The `num_children` proxy works for most cases but is not definitive. Impact: High.
3. **Must reside in a service area where NFP is implemented - confirmed Kansas sites are Shawnee County and Johnson County**
   * Screener fields:
     * `county`
     * `zipcode`
   * Source: Shawnee County Health Department NFP page (snco.gov); Johnson County Department of Health and Environment pregnancy services page (jocogov.org/department/health/pregnancy-services): 'Through this free nurse-led home visitation program, expectant mothers and families with infants who live in Johnson County, Kansas, receive personalized care'; NFP national locations page for Kansas (nursefamilypartnership.org/locations/kansas/)
   * Note: A KCMO-area affiliate (Building Blocks of MO-KC Region) may serve some KS residents in the KC metro area. This is harder to gate on county/ZIP alone and should be flagged as a potential edge case for the developer.
4. **Income eligibility - household income must be at or below 171% FPL (Kansas Medicaid/KanCare threshold for pregnant women, used as NFP income eligibility proxy)**
   * Screener fields:
     * `household_size`
     * `calc_gross_income("monthly", ["all"])`
   * Source: Shawnee County NFP page (snco.gov): *"Low-income"* listed as an eligibility requirement; Kansas Medicaid (KanCare) covers pregnant women at 171% FPL (https://www.kancare.ks.gov) — this is the standard low-income proxy used by NFP sites statewide. HomVEE model profile: *"Nurse-Family Partnership serves low-income, first-time mothers."*
   * Note: 171% FPL for a 1-person household in 2026 = $15,960 × 1.71 = $27,291.60, rounded to the nearest whole dollar = **$27,292/year** ≈ $2,274/month. The calculator rounds the FPL-derived limit to the nearest whole dollar (not truncate) so the threshold matches this documented figure; a household earning exactly $27,292/year is income-eligible. Some sites may accept participants slightly above this threshold at nurse discretion; lean inclusive on edge cases.
5. **Must enroll early enough in pregnancy (ideally by 28th week of gestation, must enroll before birth)** ⚠️ *data gap*
   * Note: The screener has a 'pregnant' boolean field but does not capture gestational age or due date. The program requires enrollment during pregnancy, ideally by 28 weeks. Some sites may accept enrollment later in pregnancy but before birth. The screener cannot determine how far along the pregnancy is. Impact: Medium.
   * Source: HomVEE: 'Visits begin during pregnancy (as early as possible and no later than the 28th week of pregnancy)'; Changent: enrollment during pregnancy
6. **Must not have previously participated in NFP with a prior pregnancy** ⚠️ *data gap*
   * Note: The screener does not track prior program participation history. The `has_nfp` field indicates current benefit receipt, not historical participation. Impact: Low.
   * Source: NFP model fidelity requirements - program is designed for first-time parents and participants typically cannot re-enroll for subsequent pregnancies

## Benefit Value

NFP provides registered nurse home visits from enrollment through the child's second birthday. There is no direct cash payment to participants — the benefit is the in-kind value of the nursing services delivered.

* Value type: in-kind benefit (calculated)
* Methodology: ~60 nurse home visits over the 2.5-year program period, valued at $100/visit (mid-range rate for private-duty/skilled home nursing) = $6,000 total value ÷ 2.5 years = **$2,400/year**
* Sources: https://www.cebc4cw.org/program/nurse-family-partnership/detailed (visit schedule); https://arhomecare.com/blog/how-much-does-private-home-care-really-cost-your-2025-price-guide (hourly rate range)
* Matches the existing IL (`il_nfp`) and CO (`co_nfp`) NFP calculators, which use `amount = 6_000 / 2.5` from the same two sources
* Although each pregnant person enrolls independently with their own nurse, the value is stored **household-level** (`amount = 6_000 / 2.5`, counted once per household) to match the existing `co_nfp` / `il_nfp` precedent. A household with two eligible pregnant members is still valued at $2,400, not $4,800.
* For screener display: $2,400/year

## Implementation Coverage

* ✅ Evaluable criteria: 4
* ⚠️  Data gaps: 2

4 of 4 primary eligibility criteria can be evaluated (fully or approximately) with current screener fields. The two most critical criteria — being pregnant and being a first-time parent — can be assessed: pregnancy directly via the `pregnant` field, and first-time parent status approximately via checking for existing children. Geographic eligibility can be checked via county/zipcode. Income can be approximated using Medicaid thresholds for pregnant women in Kansas (171% FPL). The 2 data gaps cover: definitive first-time parent verification and gestational age/timing of enrollment.

## Test Scenarios

### Scenario 1: Clearly Eligible First-Time Pregnant Mother in Shawnee County

**What we're checking**: Verifies that a first-time pregnant woman living in an NFP service area (Shawnee County) with low income is identified as eligible for Nurse-Family Partnership
**Expected**: Eligible, value: $2,400/year

**Steps**:

* **Location**: Enter ZIP code `66604`, Select county `Shawnee`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `September 2003` (age 22), Select sex: `Female`, Indicate pregnant: `Yes`, Indicate number of existing children: `0` (first-time parent, no previous live births), Indicate citizenship/immigration status: `US Citizen`, Indicate income: `Yes`, Enter monthly employment income: `$1,200`, Indicate current health insurance: `Medicaid`

**Why this matters**: This is the core happy path scenario: a young, low-income, first-time pregnant woman residing in a known NFP service area (Shawnee County, KS). She meets every eligibility criterion — pregnant, first-time parent, lives in a served county, and has low income. This validates that the screener correctly identifies the most typical NFP-eligible applicant.

---

### Scenario 2: Young First-Time Pregnant Woman, Low Income, Shawnee County

**What we're checking**: Verifies eligibility for a young first-time pregnant woman with income well below the 171% FPL threshold
**Expected**: Eligible, value: $2,400/year

**Steps**:

* **Location**: Enter ZIP code `66612`, Select county `Shawnee`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `August 2008` (age 17, turning 18 in August 2026), Sex: `Female`, Indicate pregnant: `Yes`, Number of existing children: `0` (first-time parent), Relationship: `Head of Household`, Has income: `Yes`, Enter employment income: `$1,300` per month (approximately 98% FPL for household of 1), Citizenship status: `US Citizen`

**Why this matters**: Tests that a very young first-time pregnant person with income well below the 171% FPL threshold ($1,300/month vs. $2,274/month limit) is correctly identified as eligible. Ensures the screener does not exclude a minor or young adult who clearly qualifies on all dimensions.

---

### Scenario 3: First-Time Pregnant Woman with Income Just Below the 171% FPL Threshold in Shawnee County

**What we're checking**: Validates that a first-time pregnant woman with income just below the 171% FPL threshold (Kansas Medicaid/KanCare proxy used for NFP income eligibility) qualifies for NFP
**Expected**: Eligible, value: $2,400/year

**Steps**:

* **Location**: Enter ZIP code `66604`, Select county `Shawnee`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `September 2001` (age 24), Sex: `Female`, Relationship: `Head of Household`, Indicate `pregnant`, Indicate `first pregnancy` / no previous live births, Number of children: `0`, Citizenship status: `US Citizen`, Enter monthly gross income of `$2,200` ($26,400/year ≈ 165% FPL for household of 1 — just below the 171% FPL threshold of $2,274/month)

**Why this matters**: Tests that an applicant with income just below the 171% FPL threshold (2026: $2,274/month for a 1-person household) is identified as income-eligible. Scenario 4 tests the exact boundary; this scenario confirms eligibility slightly below it.

---

### Scenario 4: First-Time Pregnant Woman with Income Exactly at the 171% FPL Threshold in Shawnee County

**What we're checking**: Whether a first-time pregnant woman whose household income is exactly at the 171% FPL threshold (Kansas Medicaid/KanCare proxy for NFP income eligibility) is determined eligible for NFP
**Expected**: Eligible, value: $2,400/year

**Steps**:

* **Location**: Enter ZIP code `66603`, Select county `Shawnee`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `September 2002` (age 23), Select sex: `Female`, Indicate pregnant: `Yes`, Indicate first pregnancy / no previous live births: `Yes` (no existing children), Enter monthly gross income: `$2,274` ($27,288/year; 2026 FPL for 1-person household = $15,960 × 1.71 = $27,292/year ≈ $2,274/month), Income source: `Employment / wages`, Citizenship status: `US Citizen`

**Why this matters**: Kansas Medicaid (KanCare) covers pregnant women at 171% FPL, which NFP sites use as their income guideline. Testing at exactly $2,274/month (the 2026 boundary value) confirms that an applicant at the threshold is not incorrectly excluded. This differs from Scenario 3 (income just below threshold) by testing the exact boundary value.

---

### Scenario 5: First-Time Pregnant Woman with Income Just Above the 171% FPL Threshold in Shawnee County

**What we're checking**: Validates that a first-time pregnant woman whose household income exceeds the 171% FPL threshold (2026: $2,274/month for household of 1) is flagged as NOT eligible for NFP due to income being too high
**Expected**: Not eligible

**Steps**:

* **Location**: Enter ZIP code `66604`, Select county `Shawnee`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `September 1999` (age 26), Sex: `Female`, Indicate `Pregnant`, Indicate this is her first pregnancy / no existing children, Relationship: `Head of Household`, Has income: `Yes`, Employment income: `$2,800` per month, No current benefits or insurance

**Why this matters**: Kansas uses 171% FPL for pregnant women's Medicaid eligibility, which NFP programs typically use as their income guideline. An applicant earning above this threshold ($2,800/month vs. $2,274/month limit) should be excluded, ensuring the program targets low-income first-time mothers as intended.

---

### Scenario 6: First-Time Pregnant Woman in Shawnee County — Second Distinct ZIP Code

**What we're checking**: Validates that a different Topeka ZIP code (66602) within Shawnee County is correctly mapped to the NFP service area, confirming geographic eligibility is not limited to one specific ZIP
**Expected**: Eligible, value: $2,400/year

**Steps**:

* **Location**: Enter ZIP code `66602`, Select county `Shawnee`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `September 2001` (age 24), Select sex: `Female`, Indicate pregnant: `Yes`, Number of existing children: `0`, Income type: `Employment / wages`, Enter monthly income: `$1,500`

**Why this matters**: Confirms that the geographic gate covers multiple ZIP codes within Shawnee County, not just one hard-coded address. A misconfigured ZIP list could silently exclude valid addresses in the same county.

---

### Scenario 7: First-Time Pregnant Woman in Shawnee County Already Enrolled in Nurse-Family Partnership

**What we're checking**: Whether a person who already receives NFP benefits is flagged as ineligible or shown a different message indicating they already have the benefit
**Expected**: Not eligible

**Steps**:

* **Location**: Enter ZIP code `66603`, Select county `Shawnee`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `September 2003` (age 22), Select sex: `Female`, Indicate pregnant: `Yes`, Indicate number of existing children: `0` (first-time mother), Indicate citizenship status: `US Citizen`
* **Income**: Enter monthly employment income: `$1,200`
* **Current Benefits**: Select or indicate that the applicant is already enrolled in `Nurse-Family Partnership` (NFP), If a checkbox or selection for current benefits is available, mark NFP as a benefit currently being received

**Why this matters**: Applicants who are already enrolled in NFP should not be told to apply again. The screener should detect current enrollment and either suppress the recommendation or display an appropriate message, preventing duplicate enrollments and confusion.

---

### Scenario 8: Second-Time Pregnant Mother in Shawnee County - Excluded Due to Previous Live Birth

**What we're checking**: Validates that a pregnant woman who already has a child (not a first-time parent) is excluded from NFP. NFP strictly serves first-time birthing people only.
**Expected**: Not eligible

**Steps**:

* **Location**: Enter ZIP code `66603`, Select county `Shawnee`
* **Household**: Number of people: `3` (mother, existing child, and unborn child counted as part of household)
* **Person 1**: Birth month/year: `September 1998` (age 27), Sex: `Female`, Relationship: `Head of Household`, Indicate she is `pregnant`, Indicate she has `1` existing child (not a first-time parent), Citizenship: `US Citizen`
* **Person 2**: Birth month/year: `March 2024` (age 2), Sex: `Female`, Relationship: `Child`, This is the existing child from a previous birth
* **Income**: Person 1 monthly income: `$1,800` (employment/wages), No other income sources
* **Current Benefits**: Select any currently received benefits if applicable (e.g., SNAP, Medicaid)

**Why this matters**: NFP is exclusively for first-time birthing people. A woman who is pregnant with her second child has already had a previous live birth and is categorically excluded from the program regardless of income, location, or other factors. This tests the critical first-time parent exclusion criterion.

---

### Scenario 9: Mixed Household - Eligible First-Time Pregnant Woman with Ineligible Partner and Child from Partner's Previous Relationship

**What we're checking**: Validates that in a multi-member household, only the first-time pregnant woman is identified as potentially eligible for NFP, while her partner (male, not pregnant) and his child from a previous relationship are not eligible
**Expected**: Not eligible (see implementation note — the naive expectation would be Eligible, but the screener's household-level `num_children` cannot attribute the child to the partner)

**Steps**:

* **Location**: Enter ZIP code `66604`, Select county `Shawnee`
* **Household**: Number of people: `3`
* **Person 1**: Birth month/year: `September 1998` (age 27), Sex: `Female`, Relationship: `Head of Household`, Pregnant: `Yes`, Number of children: `0` (first-time mother, no previous live births), Has income: `Yes`, Employment income: `$1,200` per month, Citizenship: `US Citizen`
* **Person 2**: Birth month/year: `March 1996` (age 30), Sex: `Male`, Relationship: `Spouse/Partner`, Pregnant: `No`, Has income: `Yes`, Employment income: `$1,800` per month, Citizenship: `US Citizen`
* **Person 3**: Birth month/year: `January 2022` (age 4), Sex: `Female`, Relationship: `Child`, Pregnant: `No`, Has income: `No`, Citizenship: `US Citizen`

**Why this matters**: This scenario tests a realistic mixed household where only one member meets all NFP eligibility criteria. It validates that the screener correctly identifies the first-time pregnant woman as eligible while not flagging ineligible household members. Critically, it also tests whether the presence of a child in the household (who is the partner's child, not the applicant's) incorrectly disqualifies the first-time pregnant woman. The `num_children` check must correctly attribute children to the right parent.

> **Implementation note (developer):** The screener's `num_children` is strictly household-level and `relationship` is always relative to the head of household, so there is no way to attribute a child to a specific parent. Person 3 ("Child") is therefore counted as an existing child of the household, and the household-level first-time-parent gate returns **Not eligible** for this scenario. This is a known screener data-model limitation (the same one flagged in Discovery Review), and it is the intended trade-off for correctly excluding Scenario 8. See `tests/test_ks_nurse_family_partnership.py::test_scenario_9_mixed_household_child_present`.

---

### Scenario 10: Two First-Time Pregnant Women in Same Household - Both Potentially Eligible in Shawnee County

**What we're checking**: Whether the screener correctly identifies multiple eligible members when two first-time pregnant women reside in the same household, each independently meeting pregnancy, first-time parent, geographic, and income criteria
**Expected**: Eligible, value: $2,400/year (household-level, counted once — see implementation note; NOT $4,800)

**Steps**:

* **Location**: Enter ZIP code `66604`, Select county `Shawnee`
* **Household**: Number of people: `3`
* **Person 1**: Birth month/year: `September 2002` (age 23), Sex: `Female`, Relationship: `Head of Household`, Pregnant: `Yes`, Number of children: `0` (first-time parent, no previous live births), US citizen: `Yes`, Monthly income: `$1,200` (part-time employment)
* **Person 2**: Birth month/year: `March 2006` (age 20), Sex: `Female`, Relationship: `Sister` or `Other related`, Pregnant: `Yes`, Number of children: `0` (first-time parent, no previous live births), US citizen: `Yes`, Monthly income: `$800` (part-time employment)
* **Person 3**: Birth month/year: `January 2000` (age 26), Sex: `Male`, Relationship: `Other related` or `Spouse`, Pregnant: `No`, Number of children: `0`, US citizen: `Yes`, Monthly income: `$1,500` (employment)

**Why this matters**: This scenario tests whether the screener can correctly handle a household with two independently eligible members. NFP eligibility is individual (each pregnant person enrolls separately with their own nurse), so the system must recognize that both first-time pregnant women in the same household can each qualify. This validates that the screener does not assume only one person per household can be eligible.

> **Implementation note (developer):** Per the MFB `co_nfp` / `il_nfp` precedent (and confirmed for this ticket), the NFP value is stored as a **household-level** `amount = 6_000 / 2.5` that is counted once. The screener therefore reports **$2,400** for this household, not $4,800. The household is still correctly flagged **eligible** with two eligible pregnant members. See `tests/test_ks_nurse_family_partnership.py::test_scenario_10_two_pregnant_members`.

---

### Scenario 11: Pregnant Woman with No Living Children but Previous Stillbirth - Edge Case for First-Time Parent Definition

**What we're checking**: Whether a woman who has been pregnant before but had a stillbirth (no previous live births) qualifies as a 'first-time' parent, testing the boundary of the 'no previous live births' criterion
**Expected**: Eligible, value: $2,400/year

**Steps**:

* **Location**: Enter ZIP code `66603`, Select county `Shawnee`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `September 1998` (age 27), Sex: `Female`, Relationship: `Head of Household`, Indicate she is currently pregnant, Number of children in household: `0` (no living children - previous pregnancy resulted in stillbirth, not a live birth), Enter monthly income: `$1,200`, Income type: `Employment/wages`, Income frequency: `Monthly`

**Why this matters**: NFP eligibility specifies 'first-time birthing people' and 'no previous live births.' A stillbirth is not a live birth, so a woman whose only prior pregnancy ended in stillbirth should still qualify as a first-time parent. This edge case tests whether the screener correctly distinguishes between prior pregnancies and prior live births. The screener likely uses `num_children` as a proxy, so having 0 children should result in eligibility.

---

### Scenario 12: First-Time Pregnant Woman in Johnson County - Second Confirmed Service Area

**What we're checking**: Validates that a first-time pregnant woman in Johnson County, the second confirmed NFP service area in Kansas, is correctly identified as geographically eligible
**Expected**: Eligible, value: $2,400/year

**Steps**:

* **Location**: Enter ZIP code `66061`, Select county `Johnson`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `March 2000` (age 26), Sex: `Female`, Indicate pregnant: `Yes`, Number of existing children: `0` (first-time parent), Relationship: `Head of Household`, Has income: `Yes`, Employment income: `$1,400` per month, Citizenship: `US Citizen`

**Why this matters**: Johnson County is a confirmed NFP service site alongside Shawnee County. This scenario verifies that the geographic gate correctly includes Johnson County and is not limited only to Shawnee County. Without this test, a Shawnee-only configuration could go undetected.

---

### Scenario 13: First-Time Pregnant Woman Outside Any NFP Service Area - Excluded Due to Geography

**What we're checking**: Validates that a first-time pregnant woman who otherwise meets all criteria (pregnant, first-time parent, low income) is excluded because she lives outside the confirmed NFP service areas in Kansas
**Expected**: Not eligible

**Steps**:

* **Location**: Enter ZIP code `66044`, Select county `Douglas`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `September 2001` (age 24), Sex: `Female`, Indicate pregnant: `Yes`, Number of existing children: `0` (first-time parent), Relationship: `Head of Household`, Has income: `Yes`, Employment income: `$1,200` per month, Citizenship: `US Citizen`

**Why this matters**: NFP in Kansas is only available in Shawnee and Johnson counties. A woman in Douglas County (Lawrence, KS) — who would otherwise qualify — must be excluded. Without this test, a misconfigured geographic gate that matches all KS counties instead of just the two served ones would go undetected.

---

### Scenario 14: Non-Pregnant Woman - Excluded Because Pregnancy Criterion Not Met

**What we're checking**: Validates that a woman who meets all other criteria (first-time parent, service area, low income) but is not currently pregnant is correctly excluded from NFP
**Expected**: Not eligible

**Steps**:

* **Location**: Enter ZIP code `66604`, Select county `Shawnee`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `September 2001` (age 24), Sex: `Female`, Indicate pregnant: `No`, Number of existing children: `0`, Relationship: `Head of Household`, Has income: `Yes`, Employment income: `$1,200` per month, Citizenship: `US Citizen`

**Why this matters**: NFP requires active pregnancy for enrollment — the nurse visits begin during pregnancy. A woman who is not currently pregnant (even if planning a pregnancy or postpartum) cannot enroll. This confirms the pregnancy gate is enforced as a hard requirement, not just a soft filter.

---

## Source Documentation

* https://www.snco.gov/hd/nurse_family_partnership.php
* https://www.jocogov.org/department/health/pregnancy-services
* https://www.nursefamilypartnership.org/locations/kansas/
* https://changent.org/what-we-do/nurse-family-partnership/
* https://homvee.acf.hhs.gov/models/nurse-family-partnership-nfpr
* https://cdn.snco.gov/health-department/document/Nurse_family_referral_form.pdf
* https://www.cebc4cw.org/program/nurse-family-partnership/detailed
* https://arhomecare.com/blog/how-much-does-private-home-care-really-cost-your-2025-price-guide
