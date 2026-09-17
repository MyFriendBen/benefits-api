# Implement Metro Transit Reduced Fare Program (St. Louis) (MO) Program

## Program Details

- **Program**: Metro Transit Reduced Fare Program (St. Louis)
- **State**: MO
- **White Label**: mo
- **Research Date**: 2026-09-01

## Eligibility Criteria

1. **Applicant must be age 65 or older to qualify under the senior category**
   - Screener fields:
     - `birth_year_month` (via `member.calc_age()`, falling back to `age` if null — matches `IlTransportationMixin` / `WaOrcaLift` convention)
   - Source: Metro's *Disability-Based Reduced Fare Application for MetroBus and MetroLink*, Instructions for Completion (Revised 08/31/22): "In accordance with federal regulations, Metro offers a reduced fare program for people with disabilities and people age 65 or over to utilize MetroBus or MetroLink services... All persons age 65 or older are eligible for the reduced fare program." (https://www.metrostlouis.org/wp-content/uploads/2023/07/Metro-Disability-Reduced-Fare-Application-Revised-08-31-22.pdf). Cross-referenced against the Reduced Fare Programs page, which independently lists seniors aged 65+ as one of three eligible groups (https://www.metrostlouis.org/reduced-fare-program/, accessed 2026-09-12).

2. **Applicant has a disability that requires special facilities or special planning or design to ride MetroBus or MetroLink**
   - Screener fields:
     - `disabled` (also consider `visually_impaired` — Metro's own professional-verification form (Part II) lists legal blindness, defined as acuity of 20/200 or worse with best correction and/or visual field of 20 degrees or less, as one of the conditions that satisfies the "requires special facilities" standard, so mapping `visually_impaired` to this pathway is now grounded directly in Metro's source rather than only in `IlTransportationMixin` precedent)
   - Source: Same Reduced Fare Application, Instructions for Completion: "Persons with disabilities who require special facilities or special planning or design to utilize MetroBus and MetroLink are eligible for the reduced fare program."
   - **Not eligible** (from the same source, under "Who is not eligible for a Reduced Fare Permit?"):
     - People with disabilities who do not require accessibility features to use public transportation.
     - People whose limitations are solely based on pregnancy, obesity, dependency on alcohol or illegal substances, contagious diseases, or controlled epilepsy.
     - People whose conditions are in remission.

3. **Applicant is a Medicare ID holder, independent of age or disability status**
   - Screener fields:
     - `member.has_insurance("medicare")` (Medicare is on the `Insurance` model, not a bare household-member field)
   - Source: the Reduced Fare Application's Part I lists "I am a Medicare Recipient" as its own independent reason for applying (not nested under a disability determination), and Part II's instructions confirm Medicare recipients skip the professional-verification section entirely, alongside SSD/SSI/VA-100% recipients: "This section, Part II, is ONLY necessary if you are under 65 years of age AND you do not receive SSD, SSI, VA Disability (100%), or Medicare." Cross-referenced against the Reduced Fare Programs page, which lists Medicare ID holders as a third eligible group alongside (not subordinate to) seniors and disability. Confirmed against the existing `IlTransitReducedFare` calculator, which OR's `has_medicare` with the age and disability conditions rather than gating it to under-65 applicants.

4. **Applicant receives Social Security Disability (SSDI/SSD) benefits**
   - Screener fields:
     - `screen.has_base_benefit("ssdi")`
   - Source: Reduced Fare Application, Part I reason-for-application checkbox "I receive Social Security Disability," and the disability-verification list on the Instructions page, which accepts "Recent copy of your Social Security Disability (SSD) benefits verification letter" as sufficient proof on its own (no separate professional verification required).

5. **Applicant receives Supplemental Security Income (SSI)**
   - Screener fields:
     - `screen.has_base_benefit("ssi")`
   - Source: Reduced Fare Application, Part I reason-for-application checkbox "I receive Supplemental Security Income," and the disability-verification list, which accepts "Recent copy of your Supplemental Security Income (SSI) benefits verification letter" as sufficient proof on its own.

6. **Applicant has VA disability documentation showing 100% disability status** ⚠️ *data gap*
   - Note: no screener field captures a VA disability rating percentage. Cannot be evaluated with current screener fields; surface this pathway in the program description instead.
   - Source: Reduced Fare Application, Part I reason-for-application checkbox "I receive VA Disability (100%)," and the disability-verification list, which accepts "Copy of your VA disability documentation that shows 100% disability status" as sufficient proof on its own.
   - Impact: Low.

**No geographic eligibility gate.** Neither the Reduced Fare Programs page nor the Reduced Fare Application restricts eligibility to specific Missouri counties, ZIP codes, or any Metro service-area boundary — `county`/`zipcode` should not be used to exclude a household from this program. The existing `mo_metro_transit_reduced_fare` urgent_need fixture's county list (`St. Louis City`, `St. Louis County`) is an internal MFB data entry, not a rule Metro publishes anywhere found during this review, and should not be reused as an eligibility gate for this calculator.

**Not eligibility criteria — enrollment/documentation steps.** Obtaining the physical Reduced Fare Permit, providing proof of identity, and providing proof of disability or age are steps in Metro's enrollment process, not facts the screener can check ahead of time. They don't gate eligibility here and are instead reflected in the program description.

## Benefit Value

**Methodology — informed estimate anchored to the monthly 30-Day Pass differential, displayed as an average annual savings.**

Metro publishes fare and pass prices, not a benefit amount — its own materials describe the discount only as a reduced rate for permit holders, not as a dollar figure. The $468.00/year below is MFB's own estimate derived from Metro's published prices, not a number Metro states directly.

Per the Fares & Passes page (https://www.metrostlouis.org/fares-and-passes/, accessed 2026-09-12; the page carries no printed effective/last-updated date):

- Standard 30-Day Pass: **$78.00/month**
- Reduced Fare 30-Day Pass: **$39.00/month**

The 30-Day Pass is the only pass tier with a published reduced price — the One-Day Pass ($5.00) and 7-Day Pass ($27.00) have no published reduced-fare version. So the clean $39.00/month differential is only realized by riders who actually buy a 30-Day Pass every month; a cash-fare rider saves less per trip ($0.50 bus / $1.25 rail, per the same page) and a smaller, ridership-dependent amount overall.

- Monthly savings (30-Day Pass basis) = $78.00 − $39.00 = $39.00 per eligible household member per month
- Annual savings = $39.00 × 12 = **$468.00 per eligible household member per year**

**Calculator value (stored annually):** `$468.00 × (count of eligible household members)` per year.

**Display — deliberate departure from `WaOrcaLift`:** `value_format` is set to `"estimated_annual"` ("Average Annual Savings"), not left at the default (`null`). `WaOrcaLift` also stores its value annually but leaves `value_format` at the default, which divides by 12 to show a flat monthly figure — appropriate there because ORCA LIFT's $1.00 fare is a genuine fixed per-ride price for every rider. Here, only the 30-Day Pass has a published reduced price, so presenting "$39.00/month" as if it applied to every rider would overstate savings for anyone who doesn't buy that pass; presenting "$468.00/year" as an average annual savings is honest about being a representative estimate rather than an exact monthly figure. **This is intentional — do not revert `value_format` to the default to match `WaOrcaLift`'s display convention.**

**Ridership range, for context (not separately stored — the 30-Day Pass differential above is the calculator value):**
- Casual rider (~10 rides/month): saves roughly $5–$12.50/month
- Regular 30-Day Pass buyer (the anchor above): saves $39.00/month / $468.00/year
- Heavy commuter (40+ rides/month, cash fare): saves roughly $20–$50+/month

## Implementation Coverage

- ✅ Evaluable criteria: 5
- ⚠️ Data gaps: 1

5 of 6 qualifying categories can be evaluated with current screener fields: Seniors (65+), people with disabilities (self-reported `disabled`/`visually_impaired`), Medicare ID holders, SSDI recipients, and SSI recipients — combined with OR logic at the member level (meeting ANY one category makes that member eligible; these are NOT AND conditions). The 100% VA-disability pathway (Criterion 6) cannot be evaluated with current screener fields and is surfaced in the description instead. There are no income limits, asset limits, citizenship requirements, or geographic/county restrictions — the program is purely categorical.

## Research Sources

- [Metro Transit (Bi-State Development) – Reduced Fare Programs](https://www.metrostlouis.org/reduced-fare-program/) — accessed 2026-09-12; no printed effective/last-updated date
- [Metro Transit – Fares & Passes](https://www.metrostlouis.org/fares-and-passes/) — accessed 2026-09-12; no printed effective/last-updated date
- [Metro Transit – Student Passes](https://www.metrostlouis.org/student-passes/) — accessed 2026-09-12
- [Metro Disability-Based Reduced Fare Application for MetroBus and MetroLink, Revised 08/31/22](https://www.metrostlouis.org/wp-content/uploads/2023/07/Metro-Disability-Reduced-Fare-Application-Revised-08-31-22.pdf) — primary source for the disability rule, exclusions, and qualifying-document list (Criteria 1–6). Confirmed current as of 2026-09-12: no newer revision is indexed anywhere online, and the file is still live at this URL.
- `benefits-api/programs/programs/white_labels/il/transit_reduced_fare/calculator.py` and `il/transportation_mixin.py` — reference only for the bi-state calculator shape.
- `benefits-api/programs/management/commands/import_urgent_need_config_data/data/mo_metro_transit_reduced_fare.json` — an existing MO urgent_need fixture; its county list is **not** used as a source for this spec (see "No geographic eligibility gate" above), since it isn't grounded in anything Metro publishes.

**Application submission method.** The current (08/31/22) application form gives two concrete channels: mail to Metro ADA Services, or upload at MetroStLouis.org/ADAUpload — this is the operative process, since it's the most recent, specific, and directly actionable source. The program page's reference to "the Transit Access Center" names the ADA Services office itself, not a separate submission channel — contacting that office (314.982.1510 / OnTheWayADA@MetroStLouis.org) is how an applicant gets started before mailing or uploading. An earlier page describing in-person pickup has since been removed and is superseded by the current form. The config's description and `apply_button_link` correctly point to ADA Services contact info rather than the mail/upload mechanics, which belong to the permit-application flow itself, not the MFB listing.

## Acceptance Criteria

[ ] Scenario 1 (Senior Age 70 — Clearly Eligible): User should be **eligible**
[ ] Scenario 2 (Disabled Adult Age 45, No Income Threshold): User should be **eligible**
[ ] Scenario 3 (Medicare ID Holder Under 65, No Disability Determination): User should be **eligible**
[ ] Scenario 4 (Age Exactly 65 — Minimum Senior Threshold): User should be **eligible**
[ ] Scenario 5 (Age 64 — Just Below Senior Threshold, No Other Pathway): User should be **ineligible**
[ ] Scenario 6 (Visually Impaired Adult Age 50, Under 65): User should be **eligible**
[ ] Scenario 7 (SSDI Recipient Age 40, Not Otherwise Disabled): User should be **eligible**
[ ] Scenario 8 (SSI Recipient Age 38, Not Otherwise Disabled): User should be **eligible**
[ ] Scenario 9 (St. Charles County Senior — County Is Not a Gate): User should be **eligible**
[ ] Scenario 10 (Adult Age 35, No Qualifying Category on Any Pathway): User should be **ineligible**
[ ] Scenario 11 (Mixed Household — Senior and Disabled Adult Qualify; Children Ride Standard Fares): User should be **eligible**
[ ] Scenario 12 (Multiple Members, Each Qualifying Through a Different Isolated Pathway): User should be **eligible**

## Test Scenarios

### Scenario 1: Senior Age 70 — Clearly Eligible
**What we're checking**: A clearly eligible senior (age 70, well above the 65+ threshold) qualifies under the senior category.
**Expected**: Eligible, value: $468.00/year (1 eligible member × $468.00)

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1956` (age 70), Relationship: `Head of Household`, Indicate the person does NOT have a disability, Indicate the person does NOT currently receive Medicare, For income: Social Security Retirement of `$1,400` per month, No current benefits selected, Citizenship status: `U.S. Citizen`

**Why this matters**: The most straightforward happy path. If this scenario doesn't show eligibility, the program screening is fundamentally broken.

---

### Scenario 2: Disabled Adult Age 45, No Income Threshold
**What we're checking**: Confirms the Metro Transit Reduced Fare Program has NO income threshold — eligibility is categorical, not income-based.
**Expected**: Eligible, value: $468.00/year (1 eligible member × $468.00)

**Steps**:
- **Location**: Enter ZIP code `63103`, Select county `St. Louis City`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1981` (age 45), Relationship: `Head of Household`, Indicate the person HAS a disability, Enter employment income of `$3,500` per month ($42,000/year), Citizenship status: `US Citizen`, Do NOT select Medicare cardholder (disability alone should qualify)

**Why this matters**: Confirms the absence of an income gate — the screener must not incorrectly apply one.

---

### Scenario 3: Medicare ID Holder Under 65, No Disability Determination
**What we're checking**: Tests Medicare as an independent qualifying category — a person under 65 with a Medicare ID but no separate disability determination should still qualify.
**Expected**: Eligible, value: $468.00/year (1 eligible member × $468.00)

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1981` (age 45), Relationship: `Head of Household`, Indicate the person does NOT have a disability, Indicate the person currently receives Medicare, No income reported, Citizenship status: `US Citizen`

**Why this matters**: Distinguishes the Medicare pathway from the disability pathway — Metro's own form lets a Medicare recipient skip disability verification entirely.

---

### Scenario 4: Age Exactly 65 — Minimum Senior Threshold
**What we're checking**: Tests that a person who has just turned exactly 65 qualifies, validating a `>=` rather than a strict `>` comparison.
**Expected**: Eligible, value: $468.00/year (1 eligible member × $468.00)

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: **exactly 65 years before the date the test is executed** (e.g., if testing in March 2027, use March 1962 — do not hardcode a fixed year; a fixed birth date silently stops testing the boundary as time passes), Indicate the person is NOT disabled, Indicate the person does NOT have Medicare, Citizenship status: `US Citizen`, No current income, No current benefits

**Why this matters**: Pins the birth month to the exact current-month boundary to verify month-level `>= 65` precision, not just year-level rounding. Tying it to a relative offset (rather than a fixed date like "September 1961") keeps the test meaningful no matter when it's run.

---

### Scenario 5: Age 64 — Just Below Senior Threshold, No Other Pathway
**What we're checking**: A person aged 64, with no disability, Medicare, SSDI, or SSI, is correctly denied — the near-miss case immediately adjacent to the senior boundary.
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: **exactly 64 years before the date the test is executed** (e.g., if testing in March 2027, use March 1963 — do not hardcode a fixed year; a fixed birth date will eventually cross the 65 threshold and silently flip this scenario's expected outcome from ineligible to eligible), Relationship: `Head of Household`, Do NOT indicate any disability, Do NOT indicate Medicare coverage, Citizenship status: `US Citizen`, Has income: Yes, Income type: Employment/wages, Income amount: `$3,500` per month, Health insurance: Employer-provided, No current benefits selected

**Why this matters**: The most common near-miss for the senior category. Distinct from Scenario 10 below, which tests the general "no category applies" case away from any boundary.

---

### Scenario 6: Visually Impaired Adult Age 50, Under 65
**What we're checking**: Tests `visually_impaired` as its own path into the disability category, independent of the general `disabled` field.
**Expected**: Eligible, value: $468.00/year (1 eligible member × $468.00)

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1976` (age 50), Relationship: `Head of Household`, Indicate the person is visually impaired, Indicate the person does NOT otherwise report a disability, Indicate the person does NOT have Medicare, No income reported, Citizenship status: `US Citizen`, No current benefits selected

**Why this matters**: Metro's own professional-verification form lists legal blindness as a qualifying condition; without this scenario, a calculator that only checked `disabled` and ignored `visually_impaired` would pass every other test.

---

### Scenario 7: SSDI Recipient Age 40, Not Otherwise Disabled
**What we're checking**: Tests Social Security Disability (SSDI) as its own independent qualifying pathway.
**Expected**: Eligible, value: $468.00/year (1 eligible member × $468.00)

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1986` (age 40), Relationship: `Head of Household`, Indicate the person does NOT have a disability, Indicate the person does NOT have Medicare, Current benefits: select `Social Security Disability (SSDI)`, Citizenship status: `US Citizen`

**Why this matters**: SSDI recipients are a real, currently-askable pathway that the original spec missed entirely — without this test, a calculator that never checked SSDI would pass every other scenario.

---

### Scenario 8: SSI Recipient Age 38, Not Otherwise Disabled
**What we're checking**: Tests Supplemental Security Income (SSI) as its own independent qualifying pathway.
**Expected**: Eligible, value: $468.00/year (1 eligible member × $468.00)

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1988` (age 38), Relationship: `Head of Household`, Indicate the person does NOT have a disability, Indicate the person does NOT have Medicare, Current benefits: select `Supplemental Security Income (SSI)`, Citizenship status: `US Citizen`

**Why this matters**: Same rationale as Scenario 7 — SSI is a distinct, currently-askable pathway that needs its own dedicated test rather than being lumped in with the general disability check.

---

### Scenario 9: St. Charles County Senior — County Is Not a Gate
**What we're checking**: Confirms an otherwise-qualifying senior in St. Charles County — a county that appears on the unrelated `mo_metro_transit_reduced_fare` urgent_need fixture's list but not in this program's rules — is still eligible, since neither Metro source restricts this program by county.
**Expected**: Eligible, value: $468.00/year (1 eligible member × $468.00)

**Steps**:
- **Location**: Enter ZIP code `63301`, Select county `St. Charles County`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1956` (age 70), Relationship: `Head of Household`, Indicate the person does NOT have a disability, Indicate the person does NOT currently receive Medicare, Citizenship status: `U.S. Citizen`

**Why this matters**: This is the direct regression guard against reintroducing an unsourced county gate. An earlier draft of this spec used this exact profile to test that St. Charles County residents are *excluded* — that was wrong; nothing in Metro's materials supports it, and this scenario now proves the fix.

---

### Scenario 10: Adult Age 35, No Qualifying Category on Any Pathway
**What we're checking**: An adult who doesn't fall into any qualifying category — not 65+, not disabled, no Medicare, no SSDI, no SSI — is excluded. Unlike Scenario 5 (which isolates the age-boundary near-miss), this scenario explicitly rules out every other pathway to confirm none of them fire by accident.
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Person 1**: Birth month/year: `March 1991` (age 35), Relationship: `Head of Household`, Do you have a disability? Select `No`, Do you have Medicare? Select `No`, Current benefits: none selected (specifically confirm SSDI and SSI are NOT selected), Are you a US citizen? Select `Yes`, Employment status: Employed, Enter monthly earned income: `$3,500`

**Why this matters**: The most common exclusion path — the vast majority of working-age adults without a qualifying category will not qualify — and, by explicitly denying every pathway rather than just omitting them, this test would catch a bug in any one of the five OR branches.

---

### Scenario 11: Mixed Household — Senior and Disabled Adult Qualify; Children Ride Standard Fares
**What we're checking**: A 5-member household where a 70-year-old senior and a 50-year-old disabled adult each independently qualify. The household also includes an 8-year-old child and a 3-year-old toddler, who ride Metro on standard published child fares (half-price 5-12, free under 5) that require no permit and are out of scope for this program. A 40-year-old healthy adult in the same household has no qualifying category.
**Expected**: Eligible, value: $936.00/year (2 eligible members — Person 1 and Person 2 — × $468.00; Persons 3–5 contribute $0)

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `5`
- **Person 1**: Birth month/year: `March 1956` (age 70), Relationship: Head of Household, Has a disability: No, Has Medicare: No, Citizenship: US Citizen — qualifies under the senior (65+) category
- **Person 2**: Birth month/year: `June 1976` (age 50), Relationship: Other related, Has a disability: Yes, Has Medicare: No, Citizenship: US Citizen — qualifies under the disability category
- **Person 3**: Birth month/year: `January 2018` (age 8), Relationship: Child, Has a disability: No, Has Medicare: No, Citizenship: US Citizen — rides on the standard half-price child fare (not this program)
- **Person 4**: Birth month/year: `April 2023` (age 3), Relationship: Child, Has a disability: No, Has Medicare: No, Citizenship: US Citizen — rides free on the standard under-5 fare (not this program)
- **Person 5**: Birth month/year: `February 1986` (age 40), Relationship: Other related, Has a disability: No, Has Medicare: No, Citizenship: US Citizen — does not qualify for any category

**Why this matters**: Verifies the calculator determines household eligibility from the two qualifying adults without treating the children's presence as relevant to (or required for) this program's eligibility — a common real-world household composition.

---

### Scenario 12: Multiple Members, Each Qualifying Through a Different Isolated Pathway
**What we're checking**: A household with three members who each qualify through a distinct, non-overlapping pathway — one senior with no other qualifying trait, one disabled adult with no other qualifying trait, and no member who qualifies two ways at once. This isolates each pathway so a bug in one calculator branch can't be masked by another branch quietly covering for it.
**Expected**: Eligible, value: $1,404.00/year (3 eligible members × $468.00)

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `3`
- **Person 1**: Relationship: `Head of Household`, Birth month/year: `March 1956` (age 70), Has disability: `No`, Has Medicare: `No`, Has income: `Yes`, Income: Social Security Retirement $1,400/month, Insurance: `None`, Citizenship: `US Citizen` — qualifies solely via the senior pathway
- **Person 2**: Relationship: `Spouse`, Birth month/year: `July 1958` (age 68), Has disability: `No`, Has Medicare: `No`, Has income: `Yes`, Income: Social Security Retirement $1,100/month, Insurance: `None`, Citizenship: `US Citizen` — qualifies solely via the senior pathway
- **Person 3**: Relationship: `Other related`, Birth month/year: `November 1984` (age 41), Has disability: `Yes`, Has Medicare: `No`, Current benefits: none selected, Has income: `Yes`, Income: none from disability-linked sources, Insurance: `None`, Citizenship: `US Citizen` — qualifies solely via the disability pathway

**Why this matters**: The original version of this scenario gave every person Medicare and gave Person 3 SSDI on top of a disability flag — meaning a broken Medicare check or a broken SSDI check could have gone undetected because age or disability quietly covered for it. This version isolates each pathway so it actually tests what it claims to.

## Program Configuration

File: `mo_mtrfp_initial_config.json`
