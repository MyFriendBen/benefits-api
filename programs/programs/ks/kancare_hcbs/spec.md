# Program Details

* **Program**: KanCare HCBS Waivers (Home and Community-Based Services)
* **State**: KS
* **White Label**: ks
* **Name Abbreviated**: `ks_kancare_hcbs`
* **Research Date**: 2026-06-05
* **Review Date**: 2026-06-05

---

## Program Overview

Kansas operates seven Home and Community-Based Service (HCBS) waivers through KanCare (Kansas Medicaid) that provide services to people who would otherwise require institutional care. Services are delivered at home or in the community instead of nursing homes, state hospitals, or rehabilitation facilities. KDADS administers these programs through KanCare managed care organizations (Healthy Blue, Sunflower, United Healthcare).

The seven waivers are:

- **Frail Elderly (FE):** Age 65+, nursing home level of care
- **Physical Disability (PD):** Age 16–64, SSA disability determination, nursing home level of care. Currently has a waiting list.
- **Intellectual/Developmental Disability (I/DD):** Age 5+, ICF-IID level of care. Currently has a waiting list.
- **Autism (AU):** Age 0–5 (under 6th birthday), autism spectrum disorder diagnosis
- **Brain Injury (BI):** Age 0–64, acquired or traumatic brain injury
- **Serious Emotional Disturbance (SED):** Age 4–18, serious emotional disturbance diagnosis
- **Technology Assisted (TA):** Age 0–21, medically fragile and technology-dependent

**Implementation decision:** Model as a single `ks_kancare_hcbs` calculator. The screener can only verify financial eligibility (assets, income) and age. Functional, diagnostic, and level-of-care eligibility are data gaps for all seven waivers. Surface the program to financially-eligible households, and rely on the formal KDADS assessment process to gate functional eligibility.

**Dev note — eligibility gating:** The calculator should surface the program to any financially-eligible household (asset test passing). Do **not** gate on disability flags (`disabled`, `long_term_disability`) — these are informational data gaps only, not hard eligibility gates. Do **not** filter on age — since BI covers ages 0–64 and FE covers age 65+, every household has at least one member covered by at least one waiver regardless of age. The only hard screener-testable gate is the asset limit.

All HCBS waiver participants must be enrolled in KanCare (Kansas Medicaid). Financial eligibility is determined by KDHE through the KanCare Clearinghouse.

**Dev note — per-waiver application guidance:** Each of the seven waivers has a different entry point, application process, and contact. Since this is modeled as a single calculator entry, the program page should prominently surface that application steps vary by waiver. Consider a callout box or expandable section per waiver on the program results page, or at minimum a clear note directing users to the KDADS HCBS programs page (https://www.kdads.ks.gov/services-programs/long-term-services-supports/home-and-community-based-services-hcbs-programs/hcbs-programs) where each waiver's entry point is listed.

---

## Eligibility Criteria

1. **Kansas residency**

   Must be a Kansas resident.

   Screener fields: `zipcode`, `county`

   Source: [KEESM 8210 — Description of Waiver Programs](https://khap.kdhe.ks.gov/KEESM/Oct_2023_Output/keesm8210.htm)

   Notes: Standard Medicaid residency requirement. ZIP code is sufficient to confirm KS residence for screening purposes.

2. **Income limit: $2,982/month (300% SSI FBR, 2026); screener treats as non-disqualifying via Miller Trust inclusivity assumption** ⚠️ *data gap (net benefit impact; Miller Trust pathway)*

   The technical income limit for HCBS waiver eligibility is $2,982/month (300% of the SSI Federal Benefit Rate in 2026: $994/month × 3). Income above this level technically disqualifies an applicant unless they establish a Qualified Income Trust (Miller Trust) to redirect excess income. Income below this level has no cost-sharing obligation.

   For screener purposes, income is treated as non-disqualifying: the calculator surfaces the program to anyone meeting the asset test, based on the inclusivity assumption that applicants above the threshold may still qualify by establishing a Miller Trust. The screener cannot determine whether an applicant has or will establish one.

   Screener fields: `calc_gross_income("monthly", ["all"])` via `income_streams`

   Source: [KEESM 8210 — KanCare HCBS Eligibility Determination](https://khap.kdhe.ks.gov/KEESM/Oct_2023_Output/keesm8210.htm); [SSI Federal Payment Amounts 2026 — SSA.gov](https://www.ssa.gov/oact/cola/SSI.html); [Kansas Medicaid Eligibility 2026 — MedicaidPlanningAssistance.org](https://www.medicaidplanningassistance.org/medicaid-eligibility-kansas/) *(third-party)*; [42 U.S.C. § 1396p(d)(4)(B) — Qualified Income Trusts](https://www.law.cornell.edu/uscode/text/42/1396p)

   Notes: For the calculator, do not disqualify based on income. Surface the program to anyone meeting the asset test. If income exceeds $2,982/month, flag a cost-sharing obligation but keep the program eligible. The Miller Trust pathway is a data gap — inclusivity assumption: applicants above the threshold may still qualify through a Miller Trust. Surface in the program description: "If your income is above $2,982/month, you may still qualify through a legal planning arrangement. Consider speaking with a Medicaid planning attorney."

   **Individual income test:** HCBS financial eligibility is based on the individual applicant's income only, not household income — even for children. Only the income of the person who will receive services is counted. Use income streams for the specific applicant member, not a household aggregate. ⚠️ *In multi-member households the screener does not identify which member is applying — use the HoH's income streams as the proxy for the cost-share flag. This may over-flag cost-sharing obligations for households where a non-HoH member is the HCBS applicant. See screener improvement #8.*

   **SSI auto-eligibility:** SSI recipients are automatically eligible for KanCare (Kansas Medicaid) and therefore automatically meet the financial eligibility criteria for HCBS waivers. `has_ssi` is a confirmed standalone `BooleanField` on Screen. In practice, use the Screen's `has_ssi_or_ssi_income` signal (`has_ssi OR calc_gross_income("yearly", ("sSI",)) > 0`), which catches both the checkbox and any SSI income streams — consistent with how other KS programs handle SSI categorical eligibility.

3. **Asset limit: $2,000 (single applicant) / $3,000 (both spouses applying)**

   Countable assets must be at or below:

   - Single applicant: $2,000
   - Both spouses applying: $3,000 combined
   - One spouse applying: $2,000 for applicant spouse; non-applicant spouse retains up to the Community Spouse Resource Allowance (CSRA) of up to $162,660 (2026)

   Countable assets include: bank accounts (checking, savings, money market), stocks, bonds, investments, CDs, retirement accounts (applicant's IRA/401k counts; non-applicant spouse's IRA/401k is exempt).

   Exempt assets include: primary home (generally exempt; see home equity note below), one vehicle, personal belongings and household goods, life insurance with face value up to $1,500, irrevocable burial fund up to $11,960, burial spaces.

   **Home equity:** The primary home is generally exempt from the asset test. However, if home equity exceeds $752,000 (2026), the home becomes a countable resource (unless a spouse, minor child, or permanently disabled child resides there). The screener does not capture home equity value — this is a data gap. Inclusivity assumption: assume the home is exempt. Surface in the program description: "If you own your home, it is generally not counted as an asset. In rare cases where home equity exceeds $752,000, additional rules may apply."

   **Spousal protections:** When one spouse applies, the non-applying community spouse may retain up to the CSRA ($162,660 maximum in 2026) and is entitled to a Minimum Monthly Maintenance Needs Allowance (MMMNA) of $2,643.75/month (2026) from the applicant's income. The screener captures total household assets but cannot split them between spouses. See screener improvement #3.

   Screener fields: `household_assets`

   Source: [KEESM 8210 — KanCare HCBS Eligibility Determination](https://khap.kdhe.ks.gov/KEESM/Oct_2023_Output/keesm8210.htm); [Kansas Medicaid Eligibility 2026 — MedicaidPlanningAssistance.org](https://www.medicaidplanningassistance.org/medicaid-eligibility-kansas/) *(third-party)*; [42 U.S.C. § 1396p(f) — Home Equity Limit](https://www.law.cornell.edu/uscode/text/42/1396p); [42 U.S.C. § 1396r-5 — Spousal Impoverishment Protections](https://www.law.cornell.edu/uscode/text/42/1396r-5)

   Notes: The screener asset question captures liquid assets (cash, checking, savings, stocks, bonds, mutual funds) but not retirement accounts, vehicles, or life insurance separately. Since most non-liquid assets are exempt, this approximation is acceptable. Apply $2,000 limit for single-member household; $3,000 if both spouses are applying. For a married applicant with a non-applying spouse, the CSRA means combined household assets up to ~$164,660 may still qualify after protecting the community spouse's share.

   **"Both spouses applying" is not screener-detectable** ⚠️ *data gap*: The screener cannot determine whether both spouses are applying for HCBS services or only one. This affects whether the $2,000 or $3,000 asset limit applies. Conservatively apply the $2,000 limit unless a spousal-applicant question is added to the screener. See scenario 8 and screener improvements #3 and #4.

   **Individual asset test:** As with income, HCBS financial eligibility is based on the individual applicant's assets only, not the household total — even for children. Only the assets of the person who will receive services are counted (with spousal protections applied where applicable).

   **Multi-member non-spousal households:** For households where more than one person lives together but only one is applying (e.g., an elderly parent and adult child), the individual asset test technically applies only to the applicant's assets — but `household_assets` captures the combined total and cannot be split by member. Use `household_assets` as the best available proxy for the applicant's assets. This may over-exclude some households where the non-applying member holds most of the assets. Surface in the program description that the asset limit applies to the applying individual only, not the whole household, so users with shared finances can seek a formal assessment. See screener improvement #8.

4. **Age eligibility — at least one household member falls within a covered waiver age range** ⚠️ *data gap (functional/diagnostic criteria)*

   Each waiver has specific age requirements:

   - Frail Elderly (FE): age 65+
   - Physical Disability (PD): age 16–64
   - Intellectual/Developmental Disability (I/DD): age 5+
   - Autism (AU): age 0–5 (under 6th birthday)
   - Brain Injury (BI): age 0–64
   - Serious Emotional Disturbance (SED): age 4–18
   - Technology Assisted (TA): age 0–21

   Screener fields: `birth_year`, `birth_month` (per `HouseholdMember`)

   Source: [KDADS HCBS Access Guide (PDF)](https://www.kdads.ks.gov/home/showpublisheddocument/4907/638866120114730000); [KEESM 8211–8217](https://khap.kdhe.ks.gov/KEESM/Oct_2023_Output/keesm8210.htm)

   Notes: Use `birth_year` + `birth_month` (not the deprecated `age` field) to calculate precise age. Since BI covers age 0–64 and FE covers age 65+, together they cover every age — meaning no age is excluded from at least one waiver. **Do not filter on age in the calculator.** Age ranges are documented here for routing context (helping users understand which waiver applies to them) but do not gate screener eligibility. Functional and diagnostic eligibility requirements are separate data gaps (see criteria 6 and 9).

   **Age exceptions:** SED waiver age exceptions (under 4 or 18–22) may be granted with Program Manager approval (KEESM 8216). BI waiver participants may continue past age 64 with waiver manager approval (KEESM 8215). PD waiver participants who turn 65 may elect to remain on PD or transition to FE (KEESM 8212). These exceptions are data gaps — the screener cannot capture approval status.

5. **Disability or functional limitation — applicant must have a qualifying condition** ⚠️ *data gap (specific diagnosis and SSA determination)*

   Each waiver requires a specific type of disability or condition:

   - FE: frailty/functional decline requiring nursing home level of care (age 65+ serves as proxy)
   - PD: physical disability determined by the Social Security Administration (SSA); excludes primary diagnoses of I/DD, SPMI, or SED
   - I/DD: intellectual disability (impaired function in at least two adaptive skills areas) or developmental disability (began before age 22 with substantial limitation in three life functioning areas)
   - AU: autism spectrum disorder (ASD), Asperger's syndrome, or pervasive developmental disorder
   - BI: acquired or traumatic brain injury causing structural brain damage and residual deficits
   - SED: serious emotional disturbance substantially disrupting social, academic, or emotional functioning with risk of inpatient treatment
   - TA: chronic illness or medical fragility requiring dependence on medical technology

   Screener fields: `disabled`, `long_term_disability` (per `HouseholdMember`)

   Source: [KDADS HCBS Access Guide (PDF)](https://www.kdads.ks.gov/home/showpublisheddocument/4907/638866120114730000); [KMAP HCBS PD Provider Manual — Section II Eligibility Criteria](https://portal.kmap-state-ks.us/Documents/Provider/Provider%20Manuals/HCBS_PD_22038_21201.pdf)

   Notes: The screener has general disability flags (`disabled`, `long_term_disability`) but cannot distinguish between disability types or verify SSA disability determination. For FE waiver, age 65+ serves as the frailty proxy. These flags are informational only — the calculator does not gate eligibility on them (see implementation decision above). See screener improvement #1.

6. **Nursing facility level of care (NFLOC) or equivalent level-of-care determination required** ⚠️ *data gap*

   Each waiver requires a formal level-of-care determination:

   - FE, PD, BI: nursing facility level of care, determined via functional assessment by the ADRC using the state-approved functional eligibility instrument (LOC score 26+, ADL score 6+, or IADL score 12+ for PD)
   - I/DD: ICF-IID level of care, determined by CDDO screening
   - SED: serious emotional disturbance level with risk of inpatient psychiatric treatment, determined by CMHC
   - AU: ASD functional eligibility, determined by contracted Functional Eligibility Specialists
   - TA: nursing-level medical technology dependence, determined by MATLOC Eligibility Specialist

   Screener fields: none

   Source: [KEESM 8210–8217](https://khap.kdhe.ks.gov/KEESM/Oct_2023_Output/keesm8210.htm); [KMAP HCBS PD Provider Manual — Section II.A.3 Level of Care](https://portal.kmap-state-ks.us/Documents/Provider/Provider%20Manuals/HCBS_PD_22038_21201.pdf)

   Notes: This is the most critical clinical eligibility requirement and cannot be assessed through a screener. The level-of-care standard varies by waiver. Inclusivity assumption: assume any household member with disability flags may meet the level-of-care requirement. Surface prominently in the program description: "To qualify, you must also meet a level-of-care requirement determined through a formal assessment — contact your local ADRC to start that process." No screener improvement is possible — this requires a formal clinical determination that cannot be approximated through a screener question.

7. **Applicant must intend to live in the community** ⚠️ *data gap*

   HCBS waivers provide services in the community as an alternative to institutional care. Applicants must choose to receive community-based services. However, individuals currently residing in qualifying institutional settings (nursing facilities, state hospitals, ICF-IIDs, Brain Injury Rehabilitation Facilities) may apply through the Institutional Transition pathway and can bypass the waitlist for I/DD and PD waivers after a minimum of 90 consecutive days in the institution (per KEESM 8218).

   Screener fields: none

   Source: [KDADS HCBS Access Guide (PDF)](https://www.kdads.ks.gov/home/showpublisheddocument/4907/638866120114730000); [42 CFR § 441.301(b)(1)(i)](https://www.law.cornell.edu/cfr/text/42/441.301)

   Notes: The screener does not capture institutional living status. Inclusivity assumption: assume the applicant is living in or intends to live in the community. See screener improvement #2.

8. **U.S. citizenship or qualified non-citizen immigration status required** ⚠️ *data gap*

   Kansas Medicaid (including HCBS waivers) requires applicants to be U.S. citizens or qualified non-citizens. The screener does not collect citizenship or immigration status.

   Screener fields: none

   Source: [KEESM 8112 — KanCare Medical Assistance Eligibility Groups](https://www.kdheks.gov/hcf/kancare/Oct_2020_Output/keesm8112.htm#8112); [8 U.S.C. § 1611](https://www.law.cornell.edu/uscode/text/8/1611); [42 U.S.C. § 1396b(v)](https://www.law.cornell.edu/uscode/text/42/1396b)

   Notes: Per MFB policy, the screener does not and should not collect immigration/citizenship status. The `legal_status_required` field in the config is set to all 6 values to include all statuses. Inclusivity assumption: surface the program to all households regardless of immigration status. No screener improvement is possible — this is a policy decision, not a technical data gap.

9. **Applicant must have a specific qualifying condition matching the waiver type** ⚠️ *data gap*

   Each waiver has specific diagnostic requirements (see criterion 5 for details). Key exclusions: applicants with a primary diagnosis of I/DD, SPMI, or SED are excluded from the PD waiver and referred to the appropriate waiver. Applicants with a primary I/DD diagnosis are referred to the CDDO.

   Screener fields: none

   Source: [KDADS HCBS Access Guide (PDF)](https://www.kdads.ks.gov/home/showpublisheddocument/4907/638866120114730000); [KEESM 8211–8217](https://khap.kdhe.ks.gov/KEESM/Oct_2023_Output/keesm8210.htm); [KMAP HCBS PD Provider Manual — Section II.A.4–5](https://portal.kmap-state-ks.us/Documents/Provider/Provider%20Manuals/HCBS_PD_22038_21201.pdf)

   Notes: The screener cannot distinguish between disability types. Inclusivity assumption: surface the program to all financially eligible households. This criterion and criterion 5 are closely related — criterion 5 covers functional presence of disability; this criterion covers specific diagnostic type. See screener improvement #1.

10. **Autism (AU) waiver: maximum 3-year participation limit** ⚠️ *data gap*

    Participation in the AU waiver is limited to a maximum of three years. A one-year extension may be approved by the Autism Review team if the child has demonstrated continued improvement. Children who age out of or complete the AU waiver may transition to the I/DD waiver if they meet I/DD eligibility criteria.

    Screener fields: none

    Source: [KEESM 8217 — Autism Waiver](https://khap.kdhe.ks.gov/KEESM/Oct_2023_Output/keesm8210.htm)

    Notes: This is a hard program limit unique to the AU waiver. The screener cannot determine how long a child has been enrolled in the AU waiver. Inclusivity assumption: surface the program to all age-eligible children with ASD. Surface in the program description that the AU waiver has a 3-year maximum duration. No screener improvement is possible — enrollment history is not information a screener can capture.

11. **5-year asset transfer look-back period** ⚠️ *data gap*

    Kansas applies a 60-month (5-year) look-back period for HCBS waiver Medicaid. Asset transfers made for less than fair market value during this period may result in a penalty period of ineligibility. The penalty period is calculated by dividing the transferred amount by the Kansas penalty divisor (~$7,800/month in 2026, reflecting the average monthly private-pay nursing home cost).

    Screener fields: none

    Source: [KEESM 8210](https://khap.kdhe.ks.gov/KEESM/Oct_2023_Output/keesm8210.htm); [42 U.S.C. § 1396p(c)](https://www.law.cornell.edu/uscode/text/42/1396p); [Kansas Medicaid Eligibility 2026 — MedicaidPlanningAssistance.org](https://www.medicaidplanningassistance.org/medicaid-eligibility-kansas/) *(third-party, penalty divisor figure)*

    Notes: The screener does not collect asset transfer history. Inclusivity assumption: assume no disqualifying transfers have occurred. Surface in the program description: "If you have transferred or given away assets in the last 5 years, this may affect your eligibility. Consider speaking with a Medicaid planning attorney before applying." See screener improvement #7.

---

## Priority Criteria

- **Waitlists exist for some waivers.** As of 2026, the I/DD and Physical Disability (PD) waivers have active waiting lists. The Autism (AU) waiver maintains a Proposed Recipient List (waitlist) due to limited enrollment capacity. Individuals who qualify may be approved but not receive services immediately. Other waivers (FE, BI, SED, TA) do not currently have waiting lists, but waitlists can open at any time. Surface prominently in the program description and warning message.

- **Institutional transitions bypass the waitlist.** Individuals transitioning from a qualified institutional setting (nursing facility, state hospital, ICF-IID, Brain Injury Rehabilitation Facility, etc.) after at least 90 consecutive days can bypass the waitlist for I/DD and PD waivers (KEESM 8218). Note: the HCBS Access Guide states 60 days; KEESM 8218 states 90 days — KEESM is the authoritative policy document.

- **Military bypass.** Active duty and honorably discharged military personnel and their immediate family members (as defined by IRS dependency rules) may bypass the waitlist for all HCBS waivers. Must provide proof of active service or honorable discharge (DD-214, military ID, or LES) and Tricare ECHO coverage documentation.

- **Crisis exceptions.** Any applicant may request a crisis exception at the time of initial assessment or while on the waiting list, for individuals at imminent risk of institutionalization.

- **Working Healthy/WORK program participants.** PD waiver participants transitioning back from the Working Healthy/WORK program can bypass the PD waitlist.

Source: [KDADS HCBS Access Guide (PDF)](https://www.kdads.ks.gov/home/showpublisheddocument/4907/638866120114730000); [KMAP HCBS PD Provider Manual — Waiting List Management and Military Inclusion sections](https://portal.kmap-state-ks.us/Documents/Provider/Provider%20Manuals/HCBS_PD_22038_21201.pdf)

See screener improvement #6.

---

## Benefit Value

KanCare HCBS waivers are **in-kind benefits** — Medicaid pays service providers directly rather than issuing cash to participants. Services vary by waiver and individual care plan and may include personal care, home modifications, assistive technology, adult day care, home-delivered meals, medication reminders, personal emergency response systems, supported employment, and rehabilitation therapies.

**Value type:** Insurance coverage (in-kind services)

**Value format:** Estimated annual

**Estimation methodology:**

Kansas Legislative Research Department (KLRD) data indicates the cost of adding 350 disability waiver slots (I/DD and PD type) is approximately $24.5M annually (all funds, including ~$9.6M State General Funds), yielding approximately **$70,000/year per participant** for higher-intensity waivers.

Frail Elderly and lower-acuity waivers (SED, Autism) likely have lower per-participant costs. A conservative cross-waiver average estimate, accounting for the range of service intensities, is approximately **$20,000–$40,000/year**.

**Recommended estimated value for the calculator: $35,000/year**, clearly marked as an informed estimate. Note: KLRD sources are from November 2023 — figures should be refreshed against current KDADS per-waiver expenditure data before finalizing.

Source: [KLRD — Medicaid HCBS Waivers (Nov 2023)](https://klrd.gov/2023/11/30/medicaid-hcbs-waivers/); [KLRD — HCBS Waiver Rates (Nov 2023)](https://klrd.gov/2023/11/22/hcbs_waiver_rates/)

---

## Implementation Coverage

* ✅ Evaluable criteria: 4
* ⚠️ Data gaps: 7

The 4 evaluable criteria cover Kansas residency (zip/county), asset limit ($2,000 individual), income cost-share threshold ($2,982/month for patient liability flag), and age (captured via `birth_year`/`birth_month` for routing context). The only hard screener-testable gate is the asset limit — income does not disqualify and age covers all ages across the seven waivers. The 7 data gaps (criteria 5–11) cover disability type and SSA determination, nursing facility level of care, community living intent, immigration/citizenship, qualifying condition by waiver type, AU waiver participation duration, and the 5-year asset transfer look-back period. All data gaps are handled with inclusivity assumptions; the formal KDADS assessment process gates functional eligibility.

---

## Screener Improvement Opportunities

The following changes to the MFB screener would close data gaps or improve accuracy for this program. Each is flagged inline under its relevant criterion above. None are required for the initial implementation.

| # | Suggested change | Closes | Also benefits |
|---|---|---|---|
| 1 | Add disability/condition type follow-up question (physical disability, I/DD, autism, brain injury, SED, medical technology dependence) | Criteria 5 + 9 — improves waiver routing accuracy | Other disability-linked programs |
| 2 | Add "Currently living in a nursing home, care facility, or other institution" checkbox to Special Circumstances | Criterion 7 — identifies institutional transition candidates who bypass waitlist | Other LTSS programs |
| 3 | Add "Some or all of these assets belong to my spouse" checkbox near Liquid Assets | Criterion 3 — enables CSRA calculation for married applicants | Other Medicaid/LTSS programs |
| 4 | Add "Is your spouse also applying for HCBS waiver services?" question when household includes a spouse | Criterion 3 — determines whether $2,000 or $3,000 asset limit applies | — |
| 5 | Add `has_kancare_hcbs` to KS current benefits step | Suppresses program for current enrollees (no data gap closure — UX improvement) | — |
| 6 | Add veteran/military status checkbox to Special Circumstances | Priority Criteria — enables targeted waitlist bypass notice for military households | Other veteran-priority programs |
| 7 | Add "I have given away or transferred assets for less than their value in the last 5 years" checkbox to Special Circumstances | Criterion 11 — surfaces look-back penalty warning rather than silently assuming eligible | Other Medicaid LTSS programs |
| 8 | Add "Which household member will be receiving HCBS services?" selector when `household_size > 1` | Criteria 2 + 3 — enables individual income and asset tests against the correct member rather than the HoH proxy | Other programs with individual (not household) financial eligibility tests |

---

## Test Scenarios

*Scenarios 1, 2, and 3 below are reflected in the validation JSON (`ks_kancare_hcbs.json`) as the validation suite's core 3 (golden path, primary exclusion, edge case). All other scenarios are documented here for broader QA coverage and traceability. All scenarios use 2026 financial figures (SSI FBR $994/month; 300% = $2,982/month cost-share threshold; individual asset limit $2,000).*

---

### Scenario 1: Standard Frail Elderly Case — Eligible (Golden Path) ✓ in validation JSON

**What we're checking**: Single elderly applicant with low income and assets well under the $2,000 limit qualifies. Tests criteria 1 (residency), 2 (income/no disqualification), and 3 (asset limit). Frail Elderly (FE) waiver target population.
**Expected**: Eligible, value $35,000/year.
**Steps**:
* Location: ZIP `67202`, county `Sedgwick County`
* Household size: 1
* Assets: $1,200
* Person 1: Birth month/year `March 1954` (age 72), `headOfHousehold`, `disabled: true`, `long_term_disability: true`, income: Social Security Retirement $950/month, insurance: none

**Why this matters**: Golden path for the most common waiver type. Confirms basic financial eligibility logic with a clearly eligible FE-range applicant.

---

### Scenario 2: Over Asset Limit — Ineligible (Primary Exclusion) ✓ in validation JSON

**What we're checking**: Single applicant with countable assets of $8,500 — well above the $2,000 individual limit — is correctly excluded (criterion 3). The only hard screener-testable gate.
**Expected**: Not eligible.
**Steps**:
* Location: ZIP `66604`, county `Shawnee County`
* Household size: 1
* Assets: $8,500
* Person 1: Birth month/year `September 1956` (age 69), `headOfHousehold`, `disabled: true`, `long_term_disability: true`, income: Social Security Retirement $900/month, insurance: none

**Why this matters**: Tests the primary and only hard screener gate. An applicant who is otherwise eligible is excluded solely because countable assets exceed the limit.

---

### Scenario 3: High Income Above Cost-Share Threshold — Still Eligible (Key Design Decision) ✓ in validation JSON

**What we're checking**: Income above $2,982/month (300% SSI FBR, 2026) triggers a cost-sharing obligation but does NOT disqualify the applicant (criterion 2). Physical Disability (PD) waiver target population.
**Expected**: Eligible, value $35,000/year.
**Steps**:
* Location: ZIP `66604`, county `Shawnee County`
* Household size: 1
* Assets: $500
* Person 1: Birth month/year `June 1975` (age 50–51 in 2026), `headOfHousehold`, `disabled: true`, `long_term_disability: true`, income: SSDI $2,200/month + pension $1,600/month ($3,800 total, above $2,982 threshold), insurance: none

**Why this matters**: Tests the core design decision that income is never a disqualifying factor. Confirms the calculator surfaces the program while flagging the cost-sharing obligation.

---

### Scenario 4: SSI Auto-Eligibility Bypasses Asset and Income Checks

**What we're checking**: An SSI recipient with assets above the $2,000 limit is still eligible because SSI receipt confers automatic KanCare financial eligibility, bypassing both the income and asset checks (criterion 2 SSI auto-eligibility pathway).
**Expected**: Eligible, value $35,000/year.
**Steps**:
* Location: ZIP `66044`, county `Douglas County`
* Household size: 1
* Assets: $3,500 (above $2,000 standard limit — intentionally over to confirm bypass)
* Person 1: Birth month/year `September 1970` (age 55), `headOfHousehold`, `disabled: true`, income: SSI $943/month, insurance: none

**Why this matters**: SSI auto-eligibility is a key design decision in criterion 2. This is the only scenario that tests whether the asset check is correctly bypassed for SSI recipients. ⚠️ *Verify `has_ssi` field exists on Screen before implementing — see criterion 2 note.*

---

### Scenario 5: Asset Limit Boundary — Exactly at Limit, Eligible

**What we're checking**: An applicant with exactly $2,000 in countable assets is eligible (criterion 3: asset limit is ≤ $2,000, inclusive).
**Expected**: Eligible, value $35,000/year.
**Steps**:
* Location: ZIP `67401`, county `Saline County`
* Household size: 1
* Assets: $2,000 (exactly at the limit)
* Person 1: Birth month/year `October 1959` (age 66), `headOfHousehold`, `disabled: true`, income: Social Security Retirement $800/month, insurance: none

**Why this matters**: Tests the inclusive boundary condition. Confirms the comparison is ≤ not <.

---

### Scenario 6: Asset Limit Boundary — One Dollar Over, Ineligible

**What we're checking**: An applicant with $2,001 in assets — one dollar over the limit — is correctly excluded (criterion 3).
**Expected**: Not eligible.
**Steps**:
* Location: ZIP `67401`, county `Saline County`
* Household size: 1
* Assets: $2,001 (one dollar over the limit)
* Person 1: Birth month/year `October 1959` (age 66), `headOfHousehold`, `disabled: true`, income: Social Security Retirement $800/month, insurance: none

**Why this matters**: Paired with scenario 5. Confirms the boundary is strict and off-by-one errors are caught.

---

### Scenario 7: No Disability Flags Set — Still Eligible

**What we're checking**: A financially eligible applicant with `disabled: false` and `long_term_disability: false` is still surfaced. Disability flags are informational only and do not gate screener eligibility (implementation decision).
**Expected**: Eligible, value $35,000/year.
**Steps**:
* Location: ZIP `67202`, county `Sedgwick County`
* Household size: 1
* Assets: $600
* Person 1: Birth month/year `October 1995` (age 30), `headOfHousehold`, `disabled: false`, `long_term_disability: false`, no income, insurance: none

**Why this matters**: Confirms the dev note that disability flags are not gates. A dev who accidentally gated on disability flags would fail this scenario.

---

### Scenario 8: Both Spouses Applying — Combined Assets Between $2,000 and $3,000

**What we're checking**: Married household with combined assets of $2,500 — above the $2,000 single-applicant limit but below the $3,000 both-spouses limit. Tests the data gap: the screener cannot detect whether both spouses are applying (criterion 3).
**Expected**: **Ineligible** under the conservative $2,000 implementation (recommended until a spousal-applicant checkbox is added). Eligible if the dev implements $3,000 for any household containing a spouse member. Team to decide.
**Steps**:
* Location: ZIP `66606`, county `Shawnee County`
* Household size: 2
* Assets: $2,500
* Person 1: Birth month/year `October 1957` (age 68), `headOfHousehold`, `disabled: true`, income: Social Security Retirement $1,600/month, insurance: none
* Person 2: Birth month/year `October 1960` (age 65), `spouse`, `disabled: true`, no income, insurance: none

**Why this matters**: Surfaces the implementation decision required for the $2k vs $3k threshold. See screener improvement #4.

---

### Scenario 9: Child in AU/TA Waiver Age Range — Financially Eligible Household

**What we're checking**: A household with a young child (age 4, within AU age 0–5 and SED age 4–18 ranges) and no disability flags on any member is surfaced when assets are under $2,000. Confirms no age filter and no disability gate (implementation decision).
**Expected**: Eligible, value $35,000/year.
**Steps**:
* Location: ZIP `67601`, county `Ellis County`
* Household size: 2
* Assets: $500
* Person 1: Birth month/year `October 1993` (age 32), `headOfHousehold`, `disabled: false`, no income, insurance: none
* Person 2: Birth month/year `October 2021` (age 4), `child`, no income, insurance: none

**Why this matters**: Confirms the calculator surfaces to child-waiver-range households even when no disability flags are set, and that age does not act as a filter.

---

### Scenario 10: PD Waiver Target Population — Working-Age Adult, Low Assets

**What we're checking**: A working-age adult (age 28, within the PD waiver range of 16–64) with disability flags and assets under $2,000 is eligible (criteria 3, 5). Income is well under the cost-share threshold.
**Expected**: Eligible, value $35,000/year.
**Steps**:
* Location: ZIP `66762`, county `Crawford County`
* Household size: 1
* Assets: $900
* Person 1: Birth month/year `October 1997` (age 28), `headOfHousehold`, `disabled: true`, `long_term_disability: true`, income: wages $1,100/month, insurance: none

**Why this matters**: Confirms mid-life eligibility for the PD waiver target population. Distinct from scenario 3 (same age range but focuses on the high-income edge case).

---

*Notes on scenario coverage:*

* *Disability flags are informational only — scenario 7 confirms the program surfaces without them. A developer unit test is also recommended.*
* *SSI auto-eligibility (scenario 4) is not in the validation JSON — add a unit test: SSI recipient, assets above $2,000, expected eligible.*
* *Multi-member non-spousal households are not tested in the validation JSON — a developer unit test with household_size > 1 (non-spousal) would improve coverage of the individual asset test data gap.*
