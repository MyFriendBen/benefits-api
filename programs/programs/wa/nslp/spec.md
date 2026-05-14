# Washington National School Lunch Program (NSLP) — Eligibility Spec

## Program Details

- **Program:** National School Lunch Program (NSLP)
- **State:** Washington
- **White label:** `wa`
- **Internal program name:** `wa_nslp`
- **Review date:** 2026-05-08
- **Base program:** `nslp`

## Reviewer Notes

This spec treats NSLP as a household/student screening program for free or reduced-price school lunch eligibility. It does **not** treat Community Eligibility Provision (CEP), Provision 2, or Provision 3 as household eligibility pathways because those are school-level service models. A student may still receive meals at no cost through their school even when household income screening would not show eligibility.

The calculator should be intentionally inclusive where MFB does not capture school-specific facts. It should estimate eligibility based on Washington white-label routing, a likely child/student proxy, income, and screenable categorical pathways, while warning that the school or district makes the final eligibility decision.

## Eligibility Criteria

1. **Child must attend a participating NSLP/SBP school, district, or eligible institution** ⚠️ *data gap*

   - **Screener fields:** none
   - **How to implement:** Do not screen households out based on this criterion because MFB does not collect the child's school, district, grade, or residential child care institution (RCCI). Use an inclusivity assumption: if the household otherwise appears eligible, assume the school/institution participation requirement may be met.
   - **Notes:** This is a real program requirement, but it is not the same as a standalone "Washington residency" rule. If it were known that the child does not attend a participating NSLP/SBP school, district, or eligible institution, the child would not be eligible for NSLP benefits through that school. MFB can only route users to Washington materials through the WA white label and should tell users that their school or district makes the final decision.
   - **Suggested screener improvement:** Do not add a school-participation question unless MFB has a reliable school/district participation dataset. Without that dataset, keep this as an application-stage verification item.
   - **Sources:**
      - 7 CFR § 245.1
      - 7 CFR § 210.2
      - OSPI Meal Application and Verification Information

2. **Household must include at least one child/student who could receive school meals** ⚠️ *partial data gap*

   - **Screener fields:**
      - `household_members[].relationship`
      - `household_members[].birth_month`
      - `household_members[].birth_year`
      - derived `age` only for validation consistency; calculator should use `birth_month` + `birth_year`
   - **How to implement:** Count household members with relationship `child`, `fosterChild`, or `grandChild` who are age 5 through 18, using `birth_month` and `birth_year` rather than relying only on deprecated `age`. Do not use the screener's `student` field for this check because that field is meant for postsecondary/student-status questions, not K-12 enrollment.
   - **Notes:** This is a screening proxy, not a perfect legal rule. Federal NSLP rules define a "child" by school enrollment/grade or certain eligible institution/afterschool settings, not by a simple household age band. Some students outside the age 5-18 proxy may qualify, such as a student still enrolled in high school, a child under 21 in an eligible institution/center, or a student with a disability in an eligible school program. MFB cannot verify grade level, K-12 enrollment, school-year start age, RCCI status, or eligible disability-program enrollment, so this should remain a partial data gap.
   - **Suggested screener improvement:** If MFB later adds a question, keep it simple, such as: "Does this child attend elementary, middle, or high school, or another school meal program?" Avoid using the postsecondary `student` field for this.
   - **Dev note (validation):** `grandChild` is a valid relationship in the screener model and is used in production calculators (`il_ccap`, `co_first_step_savings`, `il_medicaid`). It is **not** currently in the `test_case_schema.json` relationship enum, so validation scenarios cannot include `grandChild` members. This is a schema limitation, not a spec issue. Validation coverage for grandchild households is deferred until the schema is updated.
   - **Sources:**
      - 7 CFR § 210.2
      - OSPI CNEEB Application

3. **Household income must be at or below the reduced-price income limit to screen as eligible**

   - **Screener fields:**
      - `household_size`
      - `income_streams[].type`
      - `income_streams[].amount`
      - `income_streams[].frequency`
      - `calc_gross_income(frequency, ["all"])`
   - **How to implement:** Compare household gross income to the 2025-26 OSPI/USDA Child Nutrition Program income guideline for the household size, using a **frequency-matched limit** from the OSPI table rather than always annualizing. The OSPI table publishes both annual and monthly limits; for some household sizes the monthly limit × 12 differs from the annual limit by a few dollars because OSPI rounds the monthly value (for HH size 3, $4,109/mo × 12 = $49,308 vs. the published $49,303 annual). Mirror OSPI's published behavior: if a household reports a single pay frequency, compare against the matching OSPI limit (monthly income → monthly limit; yearly income → annual limit). Only annualize when income streams are reported at mixed frequencies — in that case, use `calc_gross_income("yearly", ["all"])` and compare to the annual limit. Classify as:
      - **Free meal income tier:** income is at or below the free limit for the matched frequency.
      - **Reduced-price meal income tier:** income is above the free limit and at or below the reduced-price limit for the matched frequency.
   - **Notes:** For validation and initial implementation, use the OSPI 2025-26 rounded income table as the source of truth rather than re-calculating raw FPL percentages, because the published table is the operative household-facing source. If the MFB FPL table is used instead, confirm it reproduces the OSPI rounded limits. The legal rule uses current household income at the time of application; MFB's gross income calculation should annualize income streams according to the published pay-frequency conversion rules only when frequency-matching isn't possible. The school/district verifies the final application details.
   - **Sources:**
      - 42 U.S.C. § 1758(b)(1)(A)
      - 42 U.S.C. § 1758(b)(9)(A)-(B)
      - 7 CFR § 245.3(a)-(c)
      - 7 CFR § 245.6(c)(4)
      - Federal Register, Child Nutrition Programs: Income Eligibility Guidelines, 90 FR 11938 (Mar. 13, 2025)
      - OSPI Income Guidelines 2025-26

4. **Household is categorically eligible for free meals through Basic Food/SNAP, TANF, or FDPIR** ⚠️ *partial data gap*

   - **Screener fields:**
      - `has_benefits`
      - `has_snap`
      - `has_tanf`
   - **How to implement:** If the household has at least one child/student who meets the MFB proxy and `has_snap` or `has_tanf` is true, screen the household as eligible regardless of income. Do not implement FDPIR as an automatic eligibility check unless a `has_fdpir` or equivalent field is confirmed.
   - **Notes:** In Washington, the application refers to SNAP as **Basic Food**. Federal rules extend categorical eligibility to all children in a household receiving SNAP, FDPIR, or TANF. The OSPI application asks for FDPIR case numbers, but MFB does not appear to capture FDPIR participation in the current screener field list. User-facing copy should mention that some pathways may not be fully captured by the screener.
   - **Suggested screener improvement:** Consider adding `has_fdpir` to the WA current-benefits list if FDPIR should be reusable for categorical eligibility across programs.
   - **Sources:**
      - 7 CFR § 245.2
      - 7 CFR § 245.6(b)(7)
      - 7 CFR § 245.6(c)(4)(i)
      - 42 U.S.C. § 1758(b)(12)
      - OSPI CNEEB Application

5. **Individual child is categorically eligible for free meals through Head Start, Early Head Start, foster care, homelessness, migrant status, or runaway status** ⚠️ *partial data gap*

   - **Screener fields:**
      - `has_head_start`
      - `has_early_head_start`
      - `household_members[].relationship` where relationship is `fosterChild` (partial proxy only)
      - `housing_situation` only if confirmed available for the WA flow (partial proxy only)
   - **How to implement:** Treat `has_head_start` or `has_early_head_start` as a categorical pathway when a child/student who meets the MFB proxy is present. Treat `relationship == "fosterChild"` as a partial proxy for foster categorical eligibility, but note that formal foster status is ultimately verified by the school/agency. Do not implement migrant or runaway status unless a screener field is added. Do not rely on `needs_housing_help` as a homelessness proxy.
   - **Notes:** Under federal rules, foster/homeless/migrant/runaway/Head Start categorical eligibility is individual to that child and does not extend to all other children in the household. MFB should not overextend this pathway across the whole household unless the implementing calculator only returns one household-level recommendation and documents the simplification.
   - **Suggested screener improvement:** Do not add sensitive questions for this initial launch unless the team decides these pathways are important enough to screen directly. If added later, use simple optional yes/no questions, and avoid collecting more detail than needed.
   - **Dev note (validation):** `has_head_start` and `has_early_head_start` exist in the screener model but are **not** currently in the `test_case_schema.json` household properties. Validation scenarios that test the Head Start pathway (Spec Scenario 7 below) cannot be represented in the JSON format. Recommend a follow-up engineering ticket to add these fields to `test_case_schema.json` so the Head Start categorical pathway becomes validation-testable. Coverage gap is acknowledged in the current 3-scenario validation file.
   - **Sources:**
      - 7 CFR § 245.2
      - 7 CFR § 245.6(b)(8)
      - 42 U.S.C. § 1758(b)(12)
      - OSPI CNEEB Application
      - USDA/FNS Eligibility Manual for School Meals

## Other Eligibility Pathways / Data Gaps Not Implemented as Automatic Checks

### Medicaid direct certification

- **Screener fields:** `has_medicaid` and member-level Medicaid fields are **not sufficient by themselves**.
- **How to implement:** Do not screen a household as NSLP-eligible based only on `has_medicaid`. The household may still qualify through income or other categorical pathways.
- **Notes:** Federal law allows direct certification through Medicaid for children in families with income at or below a specified poverty-line threshold, and federal verification rules require Medicaid income/household-size detail in states with higher Medicaid income limits. MFB does not capture the Medicaid income percentage or direct-certification match data needed to safely use this pathway.
- **Suggested screener improvement:** Do not add a generic Medicaid shortcut. Only implement this pathway if MFB receives reliable state Medicaid direct-certification data or a direct-certification indicator.
- **Sources:**
   - 42 U.S.C. § 1758(b)(15)
   - 7 CFR § 245.6a(g)(4)
   - USDA/FNS Direct Certification with Medicaid Demonstration Project

### CEP, Provision 2, and Provision 3 school-wide free meals

- **Screener fields:** none.
- **How to implement:** Do not treat CEP, Provision 2, or Provision 3 as household eligibility pathways in the calculator. A household may screen ineligible through household-based NSLP rules and still have a child who receives no-cost meals at a school-wide free-meal school.
- **Notes:** Surface this in the program description by telling users that some Washington schools provide meals at no cost to all students and that the school/district makes the final decision.
- **Suggested screener improvement:** Only add a school lookup if MFB has reliable, maintained school-level data for CEP/Provision 2/Provision 3 or other no-cost meal participation.
- **Sources:**
   - 7 CFR § 245.9
   - OSPI NSLP / Meal Application information

## Already-Has / Display Suppression Logic — Not an Eligibility Criterion

- **Screener fields:**
   - `has_benefits`
   - `has_nslp`
- **How to implement:** If `has_nslp` is true, suppress the program from the results or show it as already received, depending on MFB's standard current-benefits behavior.
- **Notes:** This is not an eligibility criterion; it is display/suppression logic.

## Priority Criteria

No household-level priority criteria were identified for this initial implementation. CEP, Provision 2, Provision 3, and other school-wide no-cost meal models are school-level service models, not household priority criteria.

## Income Guideline Table for 2025-26

Use the OSPI/USDA Child Nutrition Program Income Guidelines effective July 1, 2025 through June 30, 2026.

| Household size | Free annual limit | Free monthly limit | Reduced-price annual limit | Reduced-price monthly limit |
|---:|---:|---:|---:|---:|
| 1 | $20,345 | $1,696 | $28,953 | $2,413 |
| 2 | $27,495 | $2,292 | $39,128 | $3,261 |
| 3 | $34,645 | $2,888 | $49,303 | $4,109 |
| 4 | $41,795 | $3,483 | $59,478 | $4,957 |
| 5 | $48,945 | $4,079 | $69,653 | $5,805 |
| 6 | $56,095 | $4,675 | $79,828 | $6,653 |
| 7 | $63,245 | $5,271 | $90,003 | $7,501 |
| 8 | $70,395 | $5,867 | $100,178 | $8,349 |
| Each additional member | +$7,150 | +$596 | +$10,175 | +$848 |

**Note on monthly vs annual rounding:** OSPI's published monthly limits are rounded values derived from the annual limits. For some household sizes the monthly limit × 12 differs slightly from the published annual limit (e.g., HH size 3: $4,109 × 12 = $49,308 vs. published $49,303). When comparing household income to the table, **use the frequency-matched limit** (monthly income against the monthly column; annual income against the annual column) rather than always annualizing. Only annualize when income streams are reported at mixed frequencies.

For mixed pay frequencies, annualize using the OSPI method:
- monthly x 12
- twice per month x 24
- every two weeks x 26
- weekly x 52

## Benefit Value

**Type:** In-kind benefit estimate.

**Recommended calculator value:** `eligible_school_age_child_count * 828`, displayed as an estimated annual value.

**Methodology:**

- Use an estimated **$828 per eligible child per school year**.
- Calculation: **$4.60 per lunch x 180 school days = $828**.
- The $4.60 per-lunch estimate uses the SY 2025-26 contiguous-state federal reimbursement components for free lunches in lower-payment SFAs: $0.44 Section 4 payment + $4.16 Section 11 free-lunch payment.
- This is a conservative proxy. It excludes the additional $0.09 performance-based payment and excludes USDA Foods/cash-in-lieu value. It also does not try to estimate district-specific lunch prices or local/state copay policies.
- For reduced-price eligible households, use the same estimated annual value for MFB screening unless devs decide to display a lower avoided-cost value. Washington/local policy may make reduced-price meals effectively no-cost for many students, but this should be verified before coding a separate value.

**Sources:**
- USDA/FNS SY 2025-26 National Average Payments/Maximum Reimbursement Rates
- OSPI Income Guidelines 2025-26

## Suggested Implementation Logic

1. If `has_nslp` is true, suppress or mark as already received.
2. Count likely eligible students:
   - relationship in `child`, `fosterChild`, `grandChild`
   - age 5 through 18 using `birth_month` and `birth_year`
3. If count is 0, return ineligible.
4. If `has_snap` or `has_tanf` is true, return eligible with value `count * 828`.
5. If `has_head_start` or `has_early_head_start` is true, return eligible with value `count * 828`, while noting this is an imperfect household-level simplification.
6. Determine the household's income frequency. Compare household gross income to the OSPI reduced-price limit for `household_size` using the **frequency-matched column** (monthly income → monthly limit; yearly income → annual limit). If income streams are at mixed frequencies, annualize using `calc_gross_income("yearly", ["all"])` and compare to the annual limit.
7. If income is at or below the reduced-price limit for the matched frequency, return eligible with value `count * 828`; otherwise return ineligible, but the program description should still explain that school-wide free meals may apply.

## Test Scenarios

### Scenario 1: Eligible by income — standard free-meal case

**What this checks:** A standard WA household with one likely school-meal-eligible child and income below the free-meal income limit.

**Expected:** Eligible. Estimated annual value: `$828`.

**Steps:**
- Location: ZIP `98101`, county `King County`.
- Household size: `3`.
- Person 1: `headOfHousehold`, born March 1990, wages `$2,000` monthly.
- Person 2: `spouse`, born July 1991, no income.
- Person 3: `child`, born September 2018, no income.
- Current benefits: no SNAP, TANF, or NSLP.

**Why this matters:** This is the golden-path income scenario and validates the core household-size plus gross-income pathway.

### Scenario 2: Eligible at the reduced-price upper boundary

**What this checks:** A household at the published monthly reduced-price limit remains eligible. Acts as a regression test for the frequency-matched comparison rule in Criterion 3.

**Expected:** Eligible. Estimated annual value: `$828`.

**Steps:**
- Location: ZIP `98103`, county `King County`.
- Household size: `3`.
- Person 1: `headOfHousehold`, born January 1987, wages `$4,109` monthly.
- Person 2: `spouse`, born June 1988, no income.
- Person 3: `child`, born September 2013, no income.
- Current benefits: no SNAP, TANF, or NSLP.

**Why this matters:** Household size 3 has a 2025-26 reduced-price monthly limit of `$4,109` and annual limit of `$49,303`. The household reports income monthly, so the calculator should compare `$4,109/mo` to the monthly column (`$4,109`) and return eligible. A calculator that incorrectly always annualizes will compute `$4,109 × 12 = $49,308`, compare to the annual limit `$49,303`, and incorrectly return ineligible by `$5`. This scenario therefore serves as a regression test for the frequency-matched comparison rule in Criterion 3.

### Scenario 3: Ineligible above the reduced-price limit; Medicaid alone is not enough

**What this checks:** A household just above the reduced-price limit should be ineligible even if it reports Medicaid.

**Expected:** Ineligible. No value.

**Steps:**
- Location: ZIP `98103`, county `King County`.
- Household size: `3`.
- Person 1: `headOfHousehold`, born January 1987, wages `$4,110` monthly.
- Person 2: `spouse`, born June 1988, no income.
- Person 3: `child`, born September 2013, no income.
- Current benefits: Medicaid reported, but no SNAP, TANF, Head Start, Early Head Start, or NSLP.

**Why this matters:** `has_medicaid` alone is not enough because MFB does not capture Medicaid direct-certification income/match data. `$4,110/mo` exceeds the monthly limit ($4,109) directly and also exceeds the annual limit when annualized ($49,320 vs $49,303) — so this is unambiguously ineligible under any comparison approach.

### Scenario 4: Ineligible because there is no likely school-meal-eligible child

**What this checks:** Categorical eligibility through SNAP should not bypass the need for a likely child/student.

**Expected:** Ineligible. No value.

**Steps:**
- Location: ZIP `98103`, county `King County`.
- Household size: `2`.
- Person 1: `headOfHousehold`, born March 1986, wages `$1,800` monthly.
- Person 2: `child`, born September 2022, age 3, no income.
- Current benefits: SNAP selected.

**Why this matters:** This validates the MFB applicability proxy. NSLP should not be shown to a household with no likely school-meal-eligible child.

### Scenario 5: Eligible through Basic Food/SNAP categorical pathway despite high income

**What this checks:** A household with SNAP/Basic Food is categorically eligible even if income is above the normal income limit.

**Expected:** Eligible. Estimated annual value: `$828`.

**Steps:**
- Location: ZIP `99201`, county `Spokane County`.
- Household size: `3`.
- Person 1: `headOfHousehold`, born June 1985, wages `$7,000` monthly.
- Person 2: `spouse`, born February 1987, no income.
- Person 3: `child`, born March 2016, no income.
- Current benefits: SNAP selected; no NSLP.

**Why this matters:** This validates the screenable household categorical pathway.

### Scenario 6: Eligible through TANF categorical pathway despite high income

**What this checks:** A household with TANF is categorically eligible even if income is above the normal income limit.

**Expected:** Eligible. Estimated annual value: `$828`.

**Steps:**
- Location: ZIP `98901`, county `Yakima County`.
- Household size: `3`.
- Person 1: `headOfHousehold`, born April 1989, wages `$5,500` monthly.
- Person 2: `spouse`, born August 1990, no income.
- Person 3: `child`, born October 2017, no income.
- Current benefits: TANF selected; no NSLP.

**Why this matters:** This separately validates `has_tanf`, which is a screenable household categorical pathway.

### Scenario 7: Eligible through Head Start / Early Head Start pathway

**What this checks:** A household with a likely child/student and Head Start or Early Head Start participation can screen eligible through a child categorical pathway.

**Expected:** Eligible. Estimated annual value: `$828`.

**Steps:**
- Location: ZIP `98402`, county `Pierce County`.
- Household size: `3`.
- Person 1: `headOfHousehold`, born May 1992, wages `$5,000` monthly.
- Person 2: `spouse`, born September 1993, no income.
- Person 3: `child`, born May 2021, age 5, no income.
- Current benefits: Head Start or Early Head Start selected; no SNAP, TANF, or NSLP.

**Why this matters:** This validates the screenable child categorical pathway and checks that income does not block the categorical pathway.

**Dev note:** This scenario cannot currently be expressed in the validation JSON because `has_head_start` and `has_early_head_start` are not in `test_case_schema.json` household properties. See Criterion 5 dev note. The calculator should still implement this pathway.

### Scenario 8: Already receiving NSLP suppression

**What this checks:** A household that reports already receiving NSLP should not receive a new recommendation for the same program.

**Expected:** Ineligible/suppressed or marked already received, according to MFB current-benefits behavior.

**Steps:**
- Location: ZIP `98101`, county `King County`.
- Household size: `3`.
- Person 1: `headOfHousehold`, born March 1990, wages `$2,000` monthly.
- Person 2: `spouse`, born July 1991, no income.
- Person 3: `child`, born September 2018, no income.
- Current benefits: NSLP selected.

**Why this matters:** This validates already-has/display suppression and keeps it separate from true eligibility.

### Scenario 9: Multiple likely eligible children — value scales by child count

**What this checks:** A larger household with more than one likely school-meal-eligible child should receive a value estimate for each likely eligible child.

**Expected:** Eligible. Estimated annual value: `$2,484` for three likely eligible children (`3 x $828`).

**Steps:**
- Location: ZIP `99201`, county `Spokane County`.
- Household size: `6`.
- Person 1: `headOfHousehold`, born March 1985, wages `$2,400` monthly.
- Person 2: `spouse`, born July 1987, wages `$800` monthly.
- Person 3: `child`, born September 2010, no income.
- Person 4: `child`, born January 2014, no income.
- Person 5: `child`, born November 2019, no income.
- Person 6: `child`, born February 2023, no income.
- Current benefits: no SNAP, TANF, or NSLP.

**Why this matters:** This validates household-size income logic and the benefit value method for multiple likely eligible children.

## Representative Validation Scenarios Used in `wa_nslp.json`

The validation file contains 3 scenarios chosen to give broad coverage of the eligibility space without duplicating test dimensions:

1. **Eligible by income — household of 3 with one school-age child below the free-meal income limit**
   - WA household of 3 (head + spouse + child age 7). Head earns `$2,000/mo` wages — well below the free-meal monthly limit (`$2,888` for HH size 3).
   - Expected: eligible, estimated value `$828`.

2. **Ineligible by income — household just above the reduced-price limit; Medicaid alone is not enough**
   - WA household of 3 (head + spouse + child age 12). Head earns `$4,110/mo` wages — `$1` above the reduced-price monthly limit (`$4,109`). Household reports Medicaid but not SNAP, TANF, or Head Start.
   - Expected: ineligible. Validates that `has_medicaid` alone is not a categorical pathway.

3. **Eligible by categorical pathway — household receives Basic Food/SNAP despite income above the reduced-price limit**
   - WA household of 3 (head + spouse + child age 10). Head earns `$7,000/mo` wages — far above the reduced-price limit — but `has_snap: true`.
   - Expected: eligible, estimated value `$828`. Validates the SNAP categorical pathway overrides the income test.

These 3 cover: (a) the standard income-eligible golden path, (b) the most common disqualifying reason with a noise variable (Medicaid) thrown in, and (c) the highest-volume categorical override. Spec Scenarios 2 (boundary), 4 (no child), 6 (TANF), 7 (Head Start), 8 (suppression), and 9 (multi-child value scaling) are documented in the spec but not in `wa_nslp.json` due to either the 3-scenario design constraint or current test-schema limitations (see Criterion 5 dev note for Head Start).

## Source Verification Notes

- **7 CFR Part 245:** Supports using Part 245 as the primary CFR source for eligibility determinations, income guidelines, applications, direct certification, categorical eligibility, and school-level alternatives.
- **7 CFR § 210.2:** Supports the student/school-enrollment definition of "child," which is why MFB age screening is only a proxy.
- **42 U.S.C. § 1758:** Supports the 130% FPL free-lunch threshold, 185% FPL reduced-price threshold, income eligibility, and automatic eligibility pathways.
- **OSPI Income Guidelines 2025-26:** Supports the exact WA 2025-26 income limits and annualization method.
- **OSPI CNEEB Application:** Supports Washington-specific application pathways, including Basic Food, TANF, FDPIR, income, foster/homeless/migrant indicators, SSN exceptions, and school-use approval categories.
- **OSPI Application Finder and Meal Application page:** Supports using a district application finder as the apply link and explains that families can apply any time during the school year.
- **USDA/FNS reimbursement rates:** Supports the conservative annual value estimate.

## Source URLs

- https://www.ecfr.gov/current/title-7/subtitle-B/chapter-II/subchapter-A/part-245
- https://www.ecfr.gov/current/title-7/subtitle-B/chapter-II/subchapter-A/part-210#210.2
- https://uscode.house.gov/view.xhtml?req=%28title%3A42%20section%3A1758%20edition%3Aprelim%29
- https://www.federalregister.gov/documents/2025/03/13/2025-03821/child-nutrition-programs-income-eligibility-guidelines
- https://www.fns.usda.gov/cn/eligibility-manual-school-meals
- https://www.fns.usda.gov/cn/direct-certification-medicaid-demonstration-project
- https://ospi.k12.wa.us/sites/default/files/2025-03/incomeguidelines_25-26.pdf
- https://ospi.k12.wa.us/policy-funding/child-nutrition/school-meals/national-school-lunch-program/meal-application-and-verification-information
- https://ospi.k12.wa.us/policy-funding/child-nutrition/school-meals/national-school-lunch-program
- https://ospi.k12.wa.us/policy-funding/child-nutrition/school-meals/washington-school-meals-application-finder
- https://www.fns.usda.gov/schoolmeals/fr-072425
