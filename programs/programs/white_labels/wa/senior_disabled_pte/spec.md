# Property Tax Exemption for Seniors and People with Disabilities (WA) — Spec

## Program Details

- **Program**: Property Tax Exemption for Seniors and People with Disabilities
- **State**: Washington
- **White Label**: `wa`
- **Program key / file stem**: `wa_senior_disabled_pte`
- **Review Date**: 2026-05-08

## Tax-Year Threshold Note

For the current implementation, use the WA Department of Revenue (DOR) **2024–2026** county income threshold table because this review is being completed in 2026. The DOR has posted 2027–2029 thresholds, but those are future-year thresholds and should be treated as a later update. Do **not** use the generated `$58,423` threshold.

Examples from the 2024–2026 DOR table:

| County | Income Threshold 1 | Income Threshold 2 | Income Threshold 3 |
|---|---:|---:|---:|
| King | $60,000 | $72,000 | $84,000 |
| Chelan | $35,000 | $41,000 | $48,000 |
| Spokane | $36,000 | $43,000 | $50,000 |

Source: WA DOR, *Income Thresholds for Senior Citizen and Disabled Persons Property Tax Exemption and Deferral for Tax Years 2024–2026*.

## Eligibility Criteria

1. **Applicant must own and occupy a primary residence in Washington** ⚠️ *data gap*
   - Screener fields:
     - `zipcode`
     - `county`
     - `housing_situation` ⚠️ *not currently collected from users — field exists in the data model but is not presented to users during screening; treat as unavailable for implementation*
   - Source: WA DOR overview page; RCW 84.36.381(1)-(2); WAC 458-16A-130(1), (4); DOR Form 64 0002.
   - Notes: The program applies to a principal residence in Washington. The claimant must own the property and occupy it as their principal residence for more than six months each calendar year, and must occupy the principal residence at the time of filing for each year the exemption is claimed. `zipcode` and `county` support WA/county routing and threshold selection. The screener cannot verify homeownership or principal-residence occupancy — `housing_situation` exists in the data model but is not collected from users (confirmed across multiple other WA program specs). Do **not** use `household_assets` as a proxy for homeownership because that field captures liquid assets, not real property ownership. Use an inclusivity assumption for details not captured by the screener and surface in the program description that applicants must own and live in the home as their main home.
   - Suggested screener improvement: Add an optional reusable housing question asking whether the household owns the home they live in. This would support this program and other homeowner-only programs.

2. **Applicant must meet at least one qualifying pathway: age, disability retirement, disabled veteran status, or surviving spouse/domestic partner continuation** ⚠️ *partial data gap*
   - Screener fields:
     - `birth_year`
     - `birth_month`
     - `long_term_disability` (HouseholdMember boolean — "disabilities that make you unable to work now or in the future")
     - `disabled` (HouseholdMember boolean — general disability indicator)
     - `veteran` (HouseholdMember boolean)
   - Source: RCW 84.36.381(3); WAC 458-16A-130(2); DOR Form 64 0002.
   - Notes: A claimant may qualify if they are age 61 or older by December 31 of the year the claim is filed; are retired from regular gainful employment because of disability; are a qualifying veteran with disabilities; or are a surviving spouse/domestic partner age 57+ continuing a deceased claimant's exemption. The age pathway is directly screenable using date of birth. The disability-retirement, disabled-veteran, and surviving-spouse/domestic-partner pathways are only partially screenable and require county assessor review and supporting documentation.
   - Data-gap handling:
     - Disability-retirement pathway: Use `long_term_disability` and `disabled` as partial proxies only. The screener does not confirm that the claimant is retired from regular gainful employment because of disability.
     - Disabled-veteran pathway: Use `veteran` plus disability-related indicators (`long_term_disability` or `disabled`) as a possible-match pathway only. The screener does not capture VA service-connected disability rating percentage or total disability rating.
     - Surviving spouse/domestic partner pathway: Treat as a possible-match pathway only unless a specific field exists. The screener does not confirm whether the deceased spouse/domestic partner was receiving this exemption.
   - Suggested screener improvements: Add **Retired**, **Veteran**, and **Surviving spouse or domestic partner** as reusable special circumstances. These should stay broad because the screener supports many programs, not only this one.
   - Veteran threshold note: Implement the **40% or higher service-connected disability rating, or a total disability rating** standard from current RCW 84.36.381 and WAC 458-16A-130. This threshold was lowered from 80% by Washington HB 1106; DOR's overview page and Form 64 0002 still reference the prior 80%/100% language but those agency materials lag the statute. Statute and regulation control — treat the DOR materials as a known outdated-guidance issue, not a live conflict. (Reviewer note 2026-05-12: team to follow up with DOR about updating its public materials; this does not block implementation.)

3. **Applicant's combined disposable income must be at or below the county's Income Threshold 3** ⚠️ *data gap for exact income definition*
   - Screener fields:
     - `calc_gross_income("yearly", ["all"])`
     - `county`
     - `expenses` for medical expenses, if available and if devs decide to approximate allowable deductions
   - Source: RCW 84.36.381(4); RCW 84.36.383; WAC 458-16A-130(3); WAC 458-16A-120; WAC 458-16A-135; WA DOR 2024–2026 county income threshold table; DOR Form 64 0002.
   - Notes: Income limits are county-specific and are **not** based on household size or FPL. For current implementation, compare estimated yearly income to Income Threshold 3 for the applicant's county using the 2024–2026 DOR table. If estimated income is above Threshold 3, the household should screen as ineligible. Threshold 1, 2, and 3 determine the benefit tier and are explained in the Benefit Value section.
   - Data-gap handling: The legal test uses combined disposable income, not ordinary gross income. Combined disposable income includes the claimant, spouse/domestic partner, and cotenants with ownership interest. The assessor starts with federal AGI or other income documents and applies statutory additions and deductions. The screener does not collect federal AGI, all statutory add-backs, all allowable deductions, or whether another household member is a cotenant with ownership interest. Use gross yearly income as an approximation for screening and note that final income eligibility is determined by the county assessor under the statutory combined disposable income rules.
   - Cotenant income handling: Do not make cotenant ownership status a hard exclusion. Use household income as a conservative approximation or flag this for a dev/product decision, because per-member income does not tell us which adults have legal ownership interest in the home.
   - Possible future screener improvement: For homeowner-related programs, consider asking whether each adult household member has an ownership interest in the home.

## Priority Criteria

No separate priority criteria were identified. Income Threshold 3 is an eligibility cutoff; Threshold 1, 2, and 3 affect benefit level, not priority or waitlist status.

## Data Gaps / Implementation Assumptions

- **Homeownership and principal residence:** The program requires the claimant to own and occupy the home as their principal residence for more than six months each calendar year. `housing_situation` exists in the Screen data model but is not currently collected from users during screening (confirmed across multiple WA program specs, including `tx/head_start` and `tx/ccad` which document this same gap). The screener cannot verify legal ownership, property title, ownership type, or principal-residence occupancy. Do not use `household_assets` as a proxy for homeownership because that field captures liquid assets, not real property. Use an inclusivity assumption. Suggested screener improvement: add an optional reusable housing question asking whether the household owns the home they live in.

- **Disability-retirement pathway:** The screener can identify disability-related circumstances via `long_term_disability` and `disabled`, but it does not confirm the full legal requirement that the claimant is retired from regular gainful employment because of disability. Use these fields as a possible-match pathway. Suggested screener improvement: add **Retired** as a reusable special circumstance that could support this and other programs.

- **Disabled veteran pathway:** The screener captures `veteran` status and disability indicators (`long_term_disability`, `disabled`), but does not capture VA service-connected disability rating percentage or total disability rating. Treat disabled veterans as potentially eligible and note that VA documentation is required. Suggested screener improvement: add **Veteran** as a reusable special circumstance.

- **Surviving spouse/domestic partner pathway:** The screener does not reliably confirm whether the applicant is continuing an exemption previously received by a deceased spouse or domestic partner. Treat this as a possible-match pathway only unless a specific field exists. Suggested screener improvement: add a reusable **Surviving spouse or domestic partner** special circumstance, possibly with a dropdown if product/dev later determines the status needs more detail.

- **Cotenant income / ownership interest:** Combined disposable income may include income from cotenants with an ownership interest, but the screener does not identify which household members have legal ownership interest in the home. Per-member income helps, but it does not resolve whose income legally counts. Do not make this a hard exclusion; final income counting is determined by the county assessor. Implementation should use household income as a conservative approximation or flag this for a dev/product decision. Possible future screener improvement: for homeowner-related programs, consider asking whether each adult household member has an ownership interest in the home.

- **Exact benefit value:** Exact property-tax savings are not an eligibility criterion. The screener does not collect assessed residence value, taxable value, local levy details, excess levy amounts, or frozen-value history. Keep exact value limitations in the Benefit Value section, not the Eligibility Criteria section.

## Application Notes

Applications are filed with the county assessor's office for the county where the principal residence is located. The county assessor may use its own approved paper or electronic application form, so the DOR form is useful as a general source, but users may need to apply through their county assessor.

Supporting documents may include proof of ownership, proof that the property is the claimant's principal residence, legal ID showing age, disability documentation if applying through the disability pathway, VA documentation if applying through the disabled-veteran pathway, and income documents for the claimant, spouse/domestic partner, and any cotenants.

## Benefit Value

This program reduces property taxes rather than paying a cash benefit. The value is variable. It depends on the claimant's county income threshold tier, assessed residence value, taxable value, local property-tax levies, excess levy amounts, and frozen-value history.

The citable benefit structure comes from RCW 84.36.381 and WAC 458-16A-130. At or below Income Threshold 3, the claimant receives exemption from certain excess/state/lid-lift property taxes and receives the statutory residence valuation freeze. At or below Income Threshold 2, the claimant also receives regular-property-tax relief on part of the residence value. At or below Income Threshold 1, the claimant receives a larger regular-property-tax exemption.

Because the screener does not collect assessed value, taxable value, levy details, excess levy amounts, or frozen-value history, the calculator cannot determine the exact exemption amount. For MFB implementation, use the household's reported annual `propertyTax` expense as an informed rough proxy for estimated annual value. This estimate should be treated as an upper-bound/proxy, not a guaranteed savings amount.

Methodology:
- Determine likely eligibility by comparing estimated annual income to the county's 2024–2026 Income Threshold 3.
- Determine likely benefit tier by comparing estimated annual income to the county's 2024–2026 Threshold 1, 2, and 3.
- If eligible and annual `propertyTax` expense is available, set estimated annual value to annual `propertyTax`.
- If eligible and no annual `propertyTax` expense is available, return a fallback estimated annual value only if devs define one; otherwise flag value as not calculable from current screener inputs.

For validation scenarios, the eligible case includes annual `propertyTax` expense of `$1,200`, so the expected annual value is `1200`. This value follows the proxy methodology above and is not an exact statutory exemption amount.

## Test Scenarios

### Scenario 1: Eligible golden path — senior homeowner, low income, King County

**What we're checking:** A typical eligible senior applicant who meets the age pathway, lives in Washington, owns/occupies the home, and has income below King County Threshold 1.

**Expected:** Eligible.

**Steps:**
- Location: ZIP `98101`, county `King County`.
- Household: 1 person.
- Person 1: Head of household, born March 1959, age 67, owns and occupies the home as principal residence.
- Income: Social Security retirement income of `$1,200/month` (`$14,400/year`).

**Why this matters:** Confirms the basic happy path: WA resident, senior pathway, homeowner/occupancy assumption, and income below all county thresholds.

---

### Scenario 2: Ineligible — age 60, no screenable qualifying pathway

**What we're checking:** Applicant meets location and income criteria but does not meet any screenable qualifying pathway (age 61+, disability, or veteran). The surviving-spouse/domestic-partner pathway is a true data gap and is not screenable; it is not part of this test by design.

**Expected:** Ineligible.

**Steps:**
- Location: ZIP `98101`, county `King County`.
- Household: 1 person.
- Person 1: Head of household, born January 1966, age 60.
- Special circumstances: `disabled: false`, `long_term_disability: false`, `veteran: false`.
- Income: Other income of `$1,200/month` ($14,400/year), well below King County Threshold 3 ($84,000).

**Why this matters:** Confirms the calculator does not approve someone based on location and income alone — the applicant must meet one of the screenable qualifying pathways. Income being below threshold is not sufficient.

---

### Scenario 3: Eligible age boundary — exactly age 61 by December 31

**What we're checking:** Applicant at the minimum age boundary qualifies through the senior pathway.

**Expected:** Eligible.

**Steps:**
- Location: ZIP `98101`, county `King County`.
- Household: 1 person.
- Person 1: Head of household, born March 1965, age 61 by December 31 of the claim year, owns and occupies the home as principal residence.
- Income: Social Security retirement income of `$1,200/month` and pension income of `$500/month` (`$20,400/year`).

**Why this matters:** Confirms the age comparison is inclusive and uses `birth_year`/`birth_month`, not a deprecated `age` field alone.

---

### Scenario 4: Ineligible income — senior homeowner above King County Threshold 3

**What we're checking:** Applicant meets age, location, and homeownership assumptions but has estimated yearly income above King County Threshold 3 for the 2024–2026 table.

**Expected:** Ineligible.

**Steps:**
- Location: ZIP `98103`, county `King County`.
- Household: 1 person.
- Person 1: Head of household, born January 1958, age 68, owns and occupies the home as principal residence.
- Income: Annual pension/retirement income of `$85,000/year`.

**Why this matters:** King County Threshold 3 is `$84,000` for 2024–2026. This verifies that income above the county threshold screens out.

---

### Scenario 5: Eligible income boundary — exactly at King County Threshold 3

**What we're checking:** Applicant's income is exactly equal to the maximum county eligibility threshold.

**Expected:** Eligible.

**Steps:**
- Location: ZIP `98103`, county `King County`.
- Household: 1 person.
- Person 1: Head of household, born October 1958, age 67, owns and occupies the home as principal residence.
- Income: Annual pension/retirement income of `$84,000/year`.

**Why this matters:** Confirms the calculator uses `<=` for the threshold comparison and not a strict `<` comparison.

---

### Scenario 6: Eligible — under 61 with long-term disability (disability-retirement pathway)

**What we're checking:** An applicant under 61 with a long-term disability indicator qualifies via the disability-retirement pathway. The screener uses `long_term_disability: true` as an inclusivity proxy for the legal "retired from regular gainful employment because of disability" requirement, which the screener cannot directly verify.

**Expected:** Eligible per screener. Final eligibility requires county assessor review of retirement-due-to-disability status.

**Steps:**
- Location: ZIP `99201`, county `Spokane County`.
- Household: 1 person.
- Person 1: Head of household, born September 1980, age 45.
- Special circumstances: `long_term_disability: true`.
- Income: Annual income of `$30,000/year`, below Spokane County Threshold 1 ($36,000).

**Why this matters:** Tests the disability-retirement pathway using only currently-screenable fields. Confirms the inclusivity assumption is implemented — under-61 applicants with `long_term_disability` screen as eligible, deferring legal disability-retirement verification to the county assessor.

---

### Scenario 7: Eligible — under 61 veteran with disability indicator (disabled-veteran pathway)

**What we're checking:** An applicant under 61 who is a veteran with a disability indicator qualifies via the disabled-veteran pathway. The screener uses `veteran: true` plus `long_term_disability: true` (or `disabled: true`) as an inclusivity proxy for the legal "VA service-connected disability rating of 40% or higher, or total disability rating" requirement, which the screener cannot directly verify.

**Expected:** Eligible per screener. Final eligibility requires VA documentation of service-connected disability rating.

**Steps:**
- Location: ZIP `99201`, county `Spokane County`.
- Household: 1 person.
- Person 1: Head of household, born September 1980, age 45.
- Special circumstances: `veteran: true`; `long_term_disability: true`.
- Income: Annual income of `$30,000/year`, below Spokane County Threshold 1 ($36,000).

**Why this matters:** Tests the disabled-veteran pathway using only currently-screenable fields. Confirms the inclusivity assumption is implemented — under-61 veterans with disability indicators screen as eligible, deferring VA rating verification to the application/documentation stage.

---

### Scenario 8: Eligible — multi-member household (senior couple), combined income below King County Threshold 3

**What we're checking:** A two-person household where both members are 61+ qualifies via the age pathway. Tests that the calculator correctly aggregates household income across multiple members, since the legal income test is **combined disposable income** (claimant + spouse/domestic partner + any cotenants with ownership interest) per RCW 84.36.383 and WAC 458-16A-120.

**Expected:** Eligible.

**Steps:**
- Location: ZIP `98101`, county `King County`.
- Household: 2 people.
- Person 1: Head of household, born March 1959, age 67.
- Person 2: Spouse, born February 1962, age 64.
- Income: Person 1 receives Social Security retirement of `$1,800/month` ($21,600/year); Person 2 receives pension of `$3,000/month` ($36,000/year). Combined annual income: `$57,600`, below King County Threshold 3 ($84,000).

**Why this matters:** Tests multi-member income aggregation. Confirms the calculator sums income across all household members (consistent with the combined-disposable-income statutory definition) rather than evaluating only the head of household's income.

---

### Note on omitted scenarios

The **surviving spouse / domestic partner** continuation pathway is a true data gap — the screener has no field for prior-exemption-recipient status, so it cannot be tested with current screener data. It is documented under Criterion 2 and the Data Gaps section but is not included as a test scenario.

A **non-owner / renter** scenario is also omitted because `housing_situation` is not currently collected from users in the WA screener flow (treated as a data gap under Criterion 1). The screener cannot distinguish renters from owners; any user is treated as a potential homeowner under the inclusivity assumption. Re-introduce a renter scenario if/when the suggested housing-question improvement is implemented.

## Research Sources

- [WA DOR — Property tax exemption for seniors, people retired due to disability, and veterans with disabilities](https://dor.wa.gov/taxes-rates/property-tax/property-tax-exemption-seniors-people-retired-due-disability-and-veterans-disabilities)
- [RCW 84.36.381 — Residences—Property tax exemptions—Qualifications](https://app.leg.wa.gov/RCW/default.aspx?cite=84.36.381)
- [RCW 84.36.383 — Residences—Definitions](https://app.leg.wa.gov/RCW/default.aspx?cite=84.36.383)
- [WAC 458-16A-120 — Determining Combined Disposable Income](https://app.leg.wa.gov/WAC/default.aspx?cite=458-16A-120)
- [WAC 458-16A-130 — Qualifications for Exemption](https://app.leg.wa.gov/WAC/default.aspx?cite=458-16A-130)
- [WAC 458-16A-135 — Application Procedures](https://app.leg.wa.gov/WAC/default.aspx?cite=458-16A-135)
- [WA DOR — Income Thresholds for Tax Years 2024–2026](https://dor.wa.gov/sites/default/files/2023-08/Income_ThreshTY24-26.pdf)
- [WA DOR Form 64 0002 — Senior Citizen and People with Disabilities Exemption from Real Property Taxes](https://dor.wa.gov/sites/default/files/2022-02/64-0002.pdf)

## Final Review Notes

- Replaced generated `$58,423` threshold logic with 2024–2026 county threshold logic.
- Replaced generated 80% disabled-veteran implementation language with the current RCW/WAC 40% or total-disability standard, while preserving a source-conflict note because DOR's overview page and Form 64 0002 still use 80%/100% language.
- Removed administrative filing/document requirements from eligibility and moved them to Application Notes.
- Collapsed the eligibility section to three true eligibility criteria: primary residence in Washington, qualifying pathway, and income at or below county Threshold 3.
- Moved benefit-tier logic to the Benefit Value section and folded statutory income-definition detail into the income criterion.
- Kept exact benefit value out of eligibility because exact savings cannot be calculated with current screener fields.
- Added reusable screener-improvement suggestions both inline under the relevant criteria and in the Data Gaps / Implementation Assumptions summary section.
