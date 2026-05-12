# Implement Head Start (WA) Program

## Program Details

- **Program**: Head Start (combines Head Start Preschool, Early Head Start, and Migrant or Seasonal Head Start)
- **State**: WA
- **White Label**: wa
- **Research Date**: 2026-05-06

> **Note for dev review:** This entry combines Head Start Preschool, Early Head Start, and Migrant/Seasonal Head Start under a single program. MFB's `base_program` enum supports `head_start` and `early_head_start` as distinct entries. Reviewer decision (2026-05-10): keep combined under `base_program: "head_start"`.

---

## Eligibility Criteria

A pregnant woman or child is eligible via one of two parallel federal pathways:

- **Pathway A — Head Start Preschool / Early Head Start:** criterion #1 (age) AND any one of #2–#5 (income, public assistance, foster care, homelessness)
- **Pathway B — Migrant or Seasonal Head Start:** criterion #1 (age) AND criterion #6 (agricultural family). No income or categorical test required.

Additionally, two **discretionary enrollment pathways** exist outside the federal eligibility floor — see the "Discretionary Enrollment Pathways" section below.

---

**1. Age / status requirement.**

- **Early Head Start:** Under age 3, OR pregnant woman.
- **Head Start Preschool:** At least 3 (or turns 3 by the local public-school eligibility date), and no older than required school age.
- **Migrant or Seasonal Head Start:** Younger than compulsory school age (age 8 in Washington, RCW 28A.225.010); requires criterion #6 (MSHS agricultural-family condition).

   - Screener fields: `birth_year` + `birth_month` (HouseholdMember), `pregnant` (HouseholdMember), `relationship` (HouseholdMember)
   - Source: [45 CFR § 1302.12(b)(1)–(3)](https://headstart.gov/policy/45-cfr-chap-xiii/1302-12-determining-verifying-documenting-eligibility); [Head Start Act §§ 645, 645A](https://headstart.gov/policy/head-start-act/sec-645-participation-head-start-programs)
   - Note: Use `birth_year` + `birth_month` (not the deprecated `age` field) for precise age calculation.

---

**2. Family income at or below 100% FPL.**

   - Screener fields: `household_size`, `calc_gross_income("yearly", ["all"])` (sums all income types — earned and unearned — per § 1302.12(i)(1))
   - Source: [45 CFR § 1302.12(c)(1)(i)](https://headstart.gov/policy/45-cfr-chap-xiii/1302-12-determining-verifying-documenting-eligibility); [HHS Poverty Guidelines (ASPE)](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines)
   - Note: Head Start defines "family" per 45 CFR § 1305.2. The screener uses `household_size`, which is a reasonable approximation.

   **2026 FPL reference (48 contiguous states, including WA):**

   | Family size | 100% FPL (annual) | 100% FPL (monthly) | 130% FPL (annual) |
   |---|---|---|---|
   | 1 | $15,960 | $1,330 | $20,748 |
   | 2 | $21,640 | $1,803 | $28,132 |
   | 3 | $27,320 | $2,277 | $35,516 |
   | 4 | $33,000 | $2,750 | $42,900 |
   | 5 | $38,680 | $3,223 | $50,284 |

---

**3. Family receives public assistance — TANF, SSI, or SNAP.**

   - Screener fields: `has_tanf`, `has_ssi`, `has_snap`
   - Sources: [45 CFR § 1302.12(c)(1)(ii)](https://headstart.gov/policy/45-cfr-chap-xiii/1302-12-determining-verifying-documenting-eligibility); [Head Start FAQs](https://headstart.gov/about-us/article/head-start-faqs); [ERSEA Insights — Eligibility: Determining Need and Meeting Expectations](https://headstart.gov/ersea/ersea-insights/eligibility-determining-need-meeting-expectations); [ACF-IM-HS-22-03](https://headstart.gov/policy/im/acf-im-hs-22-03)
   - Note: Per OHS interpretation, "public assistance" under § 1302.12(c)(1)(ii) includes TANF, SSI, **and SNAP**. Receipt of any one confers categorical eligibility regardless of income.

---

**4. Child is in foster care.**

   - Screener fields: `relationship (HouseholdMember)` — count members where `relationship == "fosterChild"`
   - Source: [45 CFR § 1302.12(c)(1)(iv)](https://headstart.gov/policy/45-cfr-chap-xiii/1302-12-determining-verifying-documenting-eligibility); [Head Start FAQs](https://headstart.gov/about-us/article/head-start-faqs)
   - Note: WA `relationship` enum confirmed to include a `fosterChild` option. Foster care eligibility applies regardless of income.

---

**5. Child is homeless (McKinney-Vento Homeless Assistance Act, 42 U.S.C. § 11434a; 45 CFR Part 1305).** ⚠️ *data gap*

   - Screener fields: none
   - Source: [45 CFR § 1302.12(c)(1)(iii)](https://headstart.gov/policy/45-cfr-chap-xiii/1302-12-determining-verifying-documenting-eligibility); [Head Start FAQs](https://headstart.gov/about-us/article/head-start-faqs)
   - Note: No reliable screener field for homelessness. `housing_situation` exists but isn't broad enough for McKinney-Vento (which includes doubled-up, motels, cars, parks). **Assumption:** Calculator excludes the homelessness check; user is treated as NOT homeless. Homeless families who fail criteria #2–#4 will receive ineligible result despite being federally categorically eligible. **Suggestion to product team:** Add a "Special Circumstance" option capturing McKinney-Vento situations.
   - Impact: ImpactLevel.HIGH

---

**6. Migrant or Seasonal Head Start (alternative pathway).** ⚠️ *data gap*

Notwithstanding the income/categorical criteria in #2–#5, pregnant women and children **are eligible** for Migrant or Seasonal Head Start if both apply:
- At least one family member's income comes primarily from agricultural employment (29 U.S.C. § 1802), AND
- The child meets the MSHS age requirement in criterion #1.

**No income or categorical test is required for MSHS.** This is a parallel federal eligibility pathway — § 1302.12(f) uses "are eligible" language, making it a true alternative eligibility right.

   - Screener fields: none
   - Source: [45 CFR § 1302.12(b)(3) and (f)](https://headstart.gov/policy/45-cfr-chap-xiii/1302-12-determining-verifying-documenting-eligibility); 29 U.S.C. § 1802; Head Start Act § 645(a)(1)(A)
   - Note: No screener field for migrant/seasonal agricultural worker families. WA has significant ag communities (Yakima, Chelan, Grant, Franklin, Benton). **Assumption:** Calculator excludes the check; treated as NOT migrant/seasonal. **Suggestion to product team:** Add a "Special Circumstance" option for migrant/seasonal agricultural worker households.
   - Impact: ImpactLevel.MEDIUM

---

## Discretionary Enrollment Pathways

The following are **not** federal eligibility requirements. They are federal regulations that **allow programs to enroll additional families at their discretion**. The regulations use "**may enroll**" / "**may determine**" language. The screener cannot predict whether a local program will use these provisions, so families in these situations receive an ineligible result. They should be informed via the program description that they may still apply.

---

### A. Extended Eligibility (100–130% FPL) ⚠️ *data gap — program-level discretion*

Programs **may enroll** an additional 35% of participants whose family income falls between 100% and 130% FPL, provided the program first meets the needs of (c)(1)-eligible families.

   - Screener fields: not used for screener decision
   - Source: [45 CFR § 1302.12(d)(1)–(2)](https://headstart.gov/policy/45-cfr-chap-xiii/1302-12-determining-verifying-documenting-eligibility)
   - Note: Screener evaluates strictly against 100% FPL. Families in 100–130% band are informed via the program description that they may still qualify. **No screener improvement suggestion** — the MFB screener is generalized; a HS-specific 100–130% question would not generalize.
   - Impact: ImpactLevel.MEDIUM

---

### B. Tribal Program Waiver ⚠️ *data gap — Tribal-program-level discretion*

Tribal Head Start programs **may determine** any pregnant woman or child in their approved service area to be eligible regardless of income or categorical status (waiving criteria #2–#5), provided the age requirement in #1 is met. WA tribal programs include Tulalip, Muckleshoot, Yakama, and others.

   - Screener fields: `zipcode` and `county` as partial proxy for tribal program service area (no field for tribal enrollment).
   - Source: [45 CFR § 1302.12(e)(1)](https://headstart.gov/policy/45-cfr-chap-xiii/1302-12-determining-verifying-documenting-eligibility); Head Start Act §§ 645(a)(1)(A), 640(a)(3)
   - Note: No field identifies tribal membership directly. ZIP/county is imprecise. **Assumption:** Calculator excludes the tribal waiver; family treated as NOT residing in service area. **Suggestion to product team:** Add a "Special Circumstance" option for federally recognized tribal enrollment.
   - Impact: ImpactLevel.LOW

---

## Brief notes for description

- **Finding a local Head Start program.** Head Start is administered by local grantees, each serving a specific area.
- **Small communities (≤1,000 residents):** Programs may set their own eligibility criteria, but children meeting standard criteria cannot be denied participation ([§ 1302.12(g)](https://headstart.gov/policy/45-cfr-chap-xiii/1302-12-determining-verifying-documenting-eligibility)).
- **Kinship care:** Children in formal kinship foster care qualify under criterion #4. Kinship caregivers receiving TANF/SSI/SNAP qualify under criterion #3. Otherwise, eligibility uses caregiver's income under #2 (45 CFR § 1305.2; [ACF-IM-HS-19-03](https://headstart.gov/policy/im/acf-im-hs-19-03)).
- **"Would benefit" 10% flexibility:** Up to 10% of enrollment may serve children who don't meet any standard criterion ([§ 1302.12(c)(2)](https://headstart.gov/policy/45-cfr-chap-xiii/1302-12-determining-verifying-documenting-eligibility)).
- **Housing cost adjustment:** Programs may reduce gross income by housing costs >30% of total income ([§ 1302.12(i)(1)(ii)](https://headstart.gov/policy/45-cfr-chap-xiii/1302-12-determining-verifying-documenting-eligibility)). Optional, when income above 100% FPL. See [Housing Cost Adjustment Calculator FAQs](https://headstart.gov/ersea/article/housing-cost-adjustment-calculator-faqs).
- **Recent income changes:** Programs may use current income if significant change like job loss ([§ 1302.12(i)(1)(v)](https://headstart.gov/policy/45-cfr-chap-xiii/1302-12-determining-verifying-documenting-eligibility)).
- **Military families:** Income calculated using IRS gross-income rules. Some allowances/combat pay excluded. See [Family Income Guidelines: Military Income](https://headstart.gov/ersea/article/family-income-guidelines-military-income).
- **No citizenship / immigration status requirement** ([ACF-IM-HS-22-03](https://headstart.gov/policy/im/acf-im-hs-22-03)).
- **Transitional eligibility:** Children remain eligible through end of succeeding program year ([§ 1302.12(j)](https://headstart.gov/policy/45-cfr-chap-xiii/1302-12-determining-verifying-documenting-eligibility)). MSHS children under 3 remain eligible until they turn 3.

---

## Priority Criteria ⚠️ *data gap*

Per 45 CFR § 1302.14, common priority criteria include:

- Severity of poverty (lowest-income families served first)
- Children with disabilities under IDEA — ≥10% of enrollment reserved for IDEA-eligible
- Single-parent households
- Age (closer to kindergarten entry)
- Tribal program priority for children from Tribal families ([§ 1302.14(a)(2)](https://headstart.gov/policy/45-cfr-chap-xiii/1302-14-selection-process))
- Migrant/seasonal program priority for families that relocated frequently for agricultural work (§ 1302.14(a)(3))
- Children of staff members (§ 1302.14(a)(6))
- Other locally-determined risk factors

Sources: [45 CFR § 1302.14](https://headstart.gov/policy/45-cfr-chap-xiii/1302-14-selection-process); [Selection: Prioritizing Families](https://headstart.gov/ersea/ersea-insights/selection-prioritizing-families-responsive-policies-criteria); local grantee policies.

Not screener-evaluable.

### Data gap notes (priority criteria)

Priority gaps either overlap with existing eligibility/discretionary data gaps (closed by the same Special Circumstance suggestions) or are not appropriate for a generalized screener. No new suggestions warranted.

- **Covered by existing Special Circumstance suggestions:** homelessness (McKinney-Vento), migrant/seasonal, tribal enrollment.
- **Derivable from existing screener data** (not currently surfaced): severity of poverty (`calc_gross_income` + `household_size`), single-parent (from `relationship`), age proximity to K (from `birth_year` + `birth_month`).
- **Not screener-addressable:** IDEA-specific disability (school-district determination), staff children (per-program), locally-determined factors.

---

## Benefit Value

**Methodology:** Flat per-eligible-participant annual value of **$10,381**, applied for each Head Start-eligible person in the household (HS Preschool-age child, EHS-age child, or pregnant woman applying via the EHS pathway).

For a household with multiple eligible participants, the value scales linearly:
- 1 eligible participant → $10,381/yr
- 2 eligible participants → $20,762/yr
- 3 eligible participants → $31,143/yr
- *n* eligible participants → *n* × $10,381/yr

**Source:** [WSIPP Benefit-Cost Analysis, Program #272 — Head Start (Washington)](https://www.wsipp.wa.gov/BenefitCost/Program/272), "Present value of net program costs (in 2023 dollars)."

**WSIPP derivation:** WSIPP calculated this figure as total Washington Head Start federal funding ÷ total Washington enrollment, as reported by the Office of Head Start Region 10 (T. Saenz-Thompson, personal communication, October 24, 2019). The $10,381 figure represents the net program cost in 2023 present-value dollars — gross HS spending per child ($13,550/yr in 2018 dollars) minus the average cost of the comparison group.

**Note on EHS and pregnancy:** WSIPP's analysis is specific to HS Preschool (ages 3-5). We apply the same per-participant value to EHS (ages 0-2) and pregnant women as a simplifying assumption since no separate WA-specific cost figure exists. Informed estimate for EHS/pregnancy.

**In the config:**
- `value_type: "benefit"`
- `estimated_value: ""` (calculator computes the value)
- `value_format: "estimated_annual"`
- Calculator returns *n* × $10,381

**Sources:**
- [WSIPP Benefit-Cost Analysis, Program #272](https://www.wsipp.wa.gov/BenefitCost/Program/272)
- [45 CFR § 1302.18 — Fees](https://headstart.gov/policy/45-cfr-chap-xiii/1302-18-fees) — Head Start cannot charge fees; the calculator value represents cost of services, not a fee.

---

## Implementation Coverage

**Eligibility criteria (federal "are eligible" rights):**
- ✅ Evaluable: 4 (age #1, income #2, public assistance #3, foster care #4)
- ⚠️ Data gaps: 2 (homelessness #5, migrant/seasonal #6)

**Discretionary enrollment pathways (federal "may enroll" allowances):**
- ⚠️ Both data gaps: extended 100–130% FPL (A), tribal program waiver (B)

WA doesn't add state-specific eligibility criteria beyond federal requirements. WA also runs [ECEAP](https://dcyf.wa.gov/services/earlylearning-childcare/eceap-headstart) as a separate state program — NOT Head Start.

---

## Test Scenarios

### Acceptance Criteria

- [ ] Scenario 1 (Low-Income Family with 4-Year-Old + 2-Year-Old): **eligible** $20,762/year (2 eligible: HS Preschool + EHS)
- [ ] Scenario 2 (Income Exactly at 100% FPL with 3-Year-Old): **eligible** $10,381/year (1 eligible: HS Preschool)
- [ ] Scenario 3 (Income $1 Below 100% FPL): **eligible** $10,381/year (1 eligible: HS Preschool)
- [ ] Scenario 4 (Family of 4 with Income Exactly at 100% FPL): **eligible** $20,762/year (2 eligible: HS Preschool + EHS)
- [ ] Scenario 5 (Family of 2 with Income $1 Above 100% FPL): **ineligible**
- [ ] Scenario 6 (Child Exactly Age 3): **eligible** $10,381/year (1 eligible: HS Preschool)
- [ ] Scenario 7 (Child Age 2 — EHS): **eligible** $10,381/year (1 eligible: EHS)
- [ ] Scenario 8 (Child Age 5): **eligible** $10,381/year (1 eligible: HS Preschool)
- [ ] Scenario 9 (King County — duplicates Sc 1): **eligible** $10,381/year
- [ ] Scenario 10 (Already Receiving Head Start): **ineligible**
- [ ] Scenario 11 (No Age-Eligible Children): **ineligible**
- [ ] Scenario 12 (Mixed Household — 4yo + 7yo + 1yo): **eligible** $20,762/year (2 eligible)
- [ ] Scenario 13 (Two HS-age + TANF): **eligible** $20,762/year (2 eligible)
- [ ] Scenario 14 (Pregnant Woman Alone): **eligible** $10,381/year (1 eligible)
- [ ] Scenario 15 (SSI Categorical, income above FPL): **eligible** $10,381/year (1 eligible)
- [ ] Scenario 16 (SNAP Categorical, income above FPL): **eligible** $10,381/year (1 eligible)
- [ ] Scenario 17 (Foster Child, income above FPL): **eligible** $10,381/year (1 eligible)

---

### Scenario 1: Low-Income Family with 4-Year-Old Child — Clearly Eligible

**Expected:** Eligible — **$20,762/year** (2 eligible × $10,381)

- **Location:** ZIP `98101`, County `King`
- **Household size:** 3
- **Person 1:** Birth `March 1994` (age 32), HoH, Employment income `$1,200`/month, US Citizen
- **Person 2:** Birth `August 2021` (age 4), Child, no income
- **Person 3:** Birth `January 2024` (age 2), Child, no income
- **Current Benefits:** None

**Annual income:** $14,400 — well below 2026 FPL of $27,320 for HH 3.

**Why:** Core happy path; verifies value scales linearly with eligible-participant count.

---

### Scenario 2: Income Exactly at 100% FPL with 3-Year-Old Child

**Expected:** Eligible — **$10,381/year** (1 eligible: HS Preschool age 3)

- **Location:** ZIP `98101`, County `King`
- **Household size:** 3
- **Person 1:** Birth `June 1994` (age 31), HoH, Employment income `$27,320` per year (frequency: `yearly`)
- **Person 2:** Birth `January 1996` (age 30), Spouse, no income
- **Person 3:** Birth `April 2023` (age 3), Child, no income
- **Current Benefits:** None

**Annual income:** $27,320 — exactly at 2026 FPL of $27,320 for HH 3. Per § 1302.12(c)(1)(i), at-or-below is eligible.

**Why:** Tests two boundaries simultaneously — minimum eligible age + income exactly at FPL.

---

### Scenario 3: Family of 3 with Income $1 Below 100% FPL

**Expected:** Eligible — **$10,381/year** (1 eligible: HS Preschool age 3)

- **Location:** ZIP `98101`, County `King`
- **Household size:** 3
- **Person 1:** Birth `March 1990` (age 36), HoH, Employment income `$27,319` per year (frequency: `yearly`)
- **Person 2:** Birth `August 1992` (age 33), Spouse, no income
- **Person 3:** Birth `October 2022` (age 3), Child, no income
- **Current Benefits:** None

**Annual income:** $27,319 — $1 below 2026 FPL of $27,320 for HH 3.

**Why:** Precise boundary test, just-below.

---

### Scenario 4: Family of 4 with Income Exactly at 100% FPL — Boundary Eligible

**Expected:** Eligible — **$20,762/year** (2 eligible)

- **Location:** ZIP `98103`, County `King`
- **Household size:** 4
- **Person 1:** Birth `March 1991` (age 35), HoH, Employment income `$2,750`/month
- **Person 2:** Birth `August 1993` (age 32), Spouse, no income
- **Person 3:** Birth `January 2022` (age 4), Child, HS Preschool eligible
- **Person 4:** Birth `November 2024` (age 1), Child, EHS eligible
- **Current Benefits:** None

**Annual income:** $33,000 — exactly at 2026 FPL of $33,000 for HH 4.

**Why:** Tests HH 4 boundary at exactly FPL with two eligible children.

---

### Scenario 5: Family of 2 with Income $1 Above 100% FPL

**Expected:** Not eligible

- **Location:** ZIP `98101`, County `King`
- **Household size:** 2
- **Person 1:** Birth `March 1990` (age 36), HoH, Employment income `$21,641` per year (frequency: `yearly`), Special Circumstances: none (not pregnant)
- **Person 2:** Birth `January 2022` (age 4), Child, not in foster care
- **Current Benefits:** No TANF, no SSI, no SNAP, no current Head Start

**Annual income:** $21,641 — $1 above 2026 FPL of $21,640 for HH 2.

**Why:** Tests upper income boundary. Just above FPL with no categorical pathway → ineligible.

---

### Scenario 6: Child Exactly Age 3 — Minimum Age for Head Start Preschool

**Expected:** Eligible — **$10,381/year** (1 eligible: HS Preschool)

- **Location:** ZIP `98101`, County `King`
- **Household size:** 3
- **Person 1:** Birth `March 1994` (age 32), HoH, Employment income `$1,800`/month
- **Person 2:** Birth `June 1995` (age 30), Spouse, no income
- **Person 3:** Birth `April 2023` (age 3, just turned 3 in April 2026), Child, no income
- **Current Benefits:** None

**Annual income:** $21,600 — below FPL.

**Why:** Child just reached minimum age 3 for HS Preschool (would have been EHS-eligible one month earlier).

---

### Scenario 7: Child Age 2 — Eligible via Early Head Start

**Expected:** Eligible — **$10,381/year** (1 eligible: EHS)

- **Location:** ZIP `98902`, County `Yakima`
- **Household size:** 3
- **Person 1:** Birth `March 1994` (age 32), HoH, Employment income `$1,200`/month, US Citizen
- **Person 2:** Birth `January 1996` (age 30), Spouse, no income, US Citizen
- **Person 3:** Birth `August 2023` (age 2), Child, no income, US Citizen
- **Current Benefits:** None

**Annual income:** $14,400 — below FPL.

**Why:** Child under HS Preschool min still eligible via EHS within combined entry.

---

### Scenario 8: Child Age 5 — Within Head Start Preschool Range

**Expected:** Eligible — **$10,381/year** (1 eligible: HS Preschool)

- **Location:** ZIP `98101`, County `King`
- **Household size:** 3
- **Person 1:** Birth `March 1990` (age 36), HoH, Employment income `$1,500`/month, US Citizen
- **Person 2:** Birth `June 2020` (age 5, turning 6 in June 2026), Child, no income, US Citizen
- **Person 3:** Birth `September 1992` (age 33), Spouse, no income, US Citizen
- **Current Benefits:** None

**Annual income:** $18,000 — below FPL.

**Why:** Confirms upper-bound HS Preschool eligibility (still under required school age).

---

### Scenario 9: Eligible Location Within Washington State Service Area — King County

**Expected:** Eligible — **$10,381/year** (1 eligible: HS Preschool)

*Originally tested geographic eligibility. Effectively duplicates Scenario 1 now — exclude when picking validation cases.*

- **Location:** ZIP `98101`, County `King`
- **Household size:** 3
- **Person 1:** Birth `March 1990` (age 36), HoH, Employment income `$1,500`/month
- **Person 2:** Birth `January 1992` (age 34), Spouse, no income
- **Person 3:** Birth `August 2022` (age 3), Child, no income
- **Current Benefits:** None

**Annual income:** $18,000 — below FPL.

---

### Scenario 10: Family Already Receiving Head Start — Exclusion Due to Current Benefit Receipt

**Expected:** Not eligible

- **Location:** ZIP `98103`, County `King`
- **Household size:** 3
- **Person 1:** Birth `March 1990` (age 36), HoH, Employment income `$1,500`/month, US Citizen
- **Person 2:** Birth `August 1992` (age 33), Spouse, no income, US Citizen
- **Person 3:** Birth `January 2022` (age 4), Child, no income, US Citizen
- **Current Benefits:** Currently receiving `Head Start`

**Annual income:** $18,000 — below FPL.

**Why:** Operational exclusion (`has_head_start`), not eligibility criterion. Confirm with dev how MFB handles exclusion display.

---

### Scenario 11: Household with No Age-Eligible Children — All Children Over Age 5

**Expected:** Not eligible

- **Location:** ZIP `98103`, County `King`
- **Household size:** 3
- **Person 1:** Birth `March 1990` (age 36), HoH, Employment income `$1,500`/month
- **Person 2:** Birth `January 1992` (age 34), Spouse
- **Person 3:** Birth `February 2019` (age 7), Child
- **Current Benefits:** Receiving `SNAP` (no Head Start)

**Annual income:** $18,000.

**Why:** Age requirement is hard exclusion even with SNAP categorical. Tests **age + at least one eligible person** is required regardless of categorical pathway.

---

### Scenario 12: Mixed Household — 4-Year-Old Eligible, 7-Year-Old Too Old, Infant Eligible for EHS

**Expected:** Eligible — **$20,762/year** (2 eligible: HS Preschool + EHS; 7-year-old excluded)

- **Location:** ZIP `98103`, County `King`
- **Household size:** 5
- **Person 1:** Birth `March 1990` (age 36), HoH, Employment income `$1,800`/month
- **Person 2:** Birth `June 1992` (age 33), Spouse, Employment income `$800`/month
- **Person 3:** Birth `January 2022` (age 4), Child, HS Preschool eligible
- **Person 4:** Birth `September 2018` (age 7), Child, too old
- **Person 5:** Birth `February 2025` (age 1), Child, EHS eligible
- **Current Benefits:** None

**Annual income:** $31,200 — below FPL for HH 5 ($38,680).

**Why:** Real-world household with mixed ages. Tests per-child age evaluation and value scaling.

---

### Scenario 13: Household with Two HS Age-Eligible Children Plus TANF Receipt

**Expected:** Eligible — **$20,762/year** (2 eligible: ages 3 and 5; 6-year-old excluded)

- **Location:** ZIP `98902`, County `Yakima`
- **Household size:** 5
- **Person 1:** Birth `August 1990` (age 35), HoH, Employment income `$2,200`/month
- **Person 2:** Birth `November 1992` (age 33), Spouse, no income
- **Person 3:** Birth `January 2023` (age 3), Child, no income
- **Person 4:** Birth `March 2021` (age 5), Child, no income
- **Person 5:** Birth `June 2019` (age 6), Child, no income
- **Current Benefits:** Receiving `TANF`

**Annual income:** $26,400 — below FPL for HH 5 (income would also qualify alone).

**Why:** Multiple age-eligible children + TANF categorical. 6-year-old excluded; value reflects 2 eligible.

---

### Scenario 14: Pregnant Woman with No Other Children — Edge Case for EHS

**Expected:** Eligible — **$10,381/year** (1 eligible: pregnant woman via EHS)

- **Location:** ZIP `98103`, County `King`
- **Household size:** 1
- **Person 1:** Birth `September 1998` (age 27), HoH, Employment income `$1,200`/month
- **Special Circumstances:** Pregnant
- **Current Benefits:** None

**Annual income:** $14,400 — below FPL for HH 1 ($15,960).

**Why:** Zero children present; pregnant woman alone qualifies via EHS (§ 1302.12(b)(1)). Tests pregnancy pathway via `pregnant` field.

---

### Scenario 15: Household with SSI Receipt — Categorical Eligibility via SSI

**Expected:** Eligible — **$10,381/year** (1 eligible: HS Preschool age 4)

- **Location:** ZIP `98101`, County `King`
- **Household size:** 3
- **Person 1:** Birth `March 1991` (age 35), HoH, Employment income `$2,500`/month
- **Person 2:** Birth `August 1991` (age 34), Spouse, SSI `$1,000`/month
- **Person 3:** Birth `October 2021` (age 4), Child, no income
- **Current Benefits:** Receiving `SSI`

**Annual income:** $42,000 — above FPL ($27,320 for HH 3).

**Why:** SSI receipt makes household categorically eligible per § 1302.12(c)(1)(ii) even when income > FPL. Pairs with Sc 13 (TANF) and Sc 16 (SNAP) to cover all three public-assistance sub-pathways.

---

### Scenario 16: Household with SNAP Receipt — Categorical Eligibility via SNAP (Income Above 100% FPL)

**Expected:** Eligible — **$10,381/year** (1 eligible: HS Preschool age 3)

- **Location:** ZIP `98101`, County `King`
- **Household size:** 2
- **Person 1:** Birth `April 1996` (age 30), HoH, Employment income `$2,000`/month
- **Person 2:** Birth `February 2023` (age 3), Child, no income
- **Current Benefits:** Receiving `SNAP`

**Annual income:** $24,000 — above FPL ($21,640 for HH 2).

**Why:** Validates OHS interpretation that "public assistance" includes SNAP (ACF-IM-HS-22-03). Without categorical, household would fail income test. Complements Sc 11 (SNAP + no age-eligible → ineligible) — together they validate SNAP grants eligibility only when an age-eligible person is present.

---

### Scenario 17: Household with Foster Child — Categorical Eligibility via Foster Care

**Expected:** Eligible — **$10,381/year** (1 eligible: foster child age 4)

- **Location:** ZIP `98103`, County `King`
- **Household size:** 2
- **Person 1:** Birth `February 1986` (age 40), HoH, Employment income `$3,000`/month
- **Person 2:** Birth `September 2021` (age 4), `fosterChild`, no income
- **Current Benefits:** None

**Annual income:** $36,000 — well above FPL ($21,640 for HH 2).

**Why:** Foster care categorical pathway works regardless of income (§ 1302.12(c)(1)(iv)). Only test exercising the `fosterChild` relationship enum.

---

## Research Sources

### Primary regulatory and statutory

- [45 CFR Chapter XIII — Head Start Program Performance Standards](https://headstart.gov/policy/45-cfr-chap-xiii)
- [45 CFR § 1302.12 — Determining, verifying, and documenting eligibility](https://headstart.gov/policy/45-cfr-chap-xiii/1302-12-determining-verifying-documenting-eligibility)
- [45 CFR § 1302.18 — Fees](https://headstart.gov/policy/45-cfr-chap-xiii/1302-18-fees)
- [45 CFR § 1302.14 — Selection process](https://headstart.gov/policy/45-cfr-chap-xiii/1302-14-selection-process)
- [45 CFR Part 1305 — Definitions](https://headstart.gov/policy/45-cfr-chap-xiii/part-1305-definitions)
- [45 CFR § 1305.2 — Terms](https://headstart.gov/policy/45-cfr-chap-xiii/1305-2-terms)
- [Head Start Act § 645 (42 U.S.C. § 9840)](https://headstart.gov/policy/head-start-act/sec-645-participation-head-start-programs)
- [Head Start Act § 645A (42 U.S.C. § 9840a)](https://headstart.gov/policy/head-start-act/sec-645a-early-head-start-programs)

### Office of Head Start guidance

- [Head Start FAQs](https://headstart.gov/about-us/article/head-start-faqs)
- [ERSEA Insights — Eligibility: Determining Need and Meeting Expectations](https://headstart.gov/ersea/ersea-insights/eligibility-determining-need-meeting-expectations)
- [Eligibility Reference Sheet](https://headstart.gov/ersea/ersea-insights/eligibility-reference-sheet)
- [Selection: Prioritizing Families](https://headstart.gov/ersea/ersea-insights/selection-prioritizing-families-responsive-policies-criteria)
- [Housing Cost Adjustment Calculator FAQs](https://headstart.gov/ersea/article/housing-cost-adjustment-calculator-faqs)
- [Family Income Guidelines: Military Income](https://headstart.gov/ersea/article/family-income-guidelines-military-income)
- [ACF-IM-HS-22-03 — SNAP categorical eligibility](https://headstart.gov/policy/im/acf-im-hs-22-03)
- [ACF-IM-HS-19-03 — Kinship care guidance](https://headstart.gov/policy/im/acf-im-hs-19-03)

### Benefit value source

- [WSIPP Benefit-Cost Analysis, Program #272 — Head Start (Washington)](https://www.wsipp.wa.gov/BenefitCost/Program/272)

### Income thresholds

- [HHS Poverty Guidelines (ASPE)](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines)

### Washington-specific

- [WA DCYF — ECEAP and Head Start](https://dcyf.wa.gov/services/earlylearning-childcare/eceap-headstart)
- RCW 28A.225.010 — Washington compulsory school attendance age
