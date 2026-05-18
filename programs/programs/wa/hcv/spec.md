# Implement HCV (WA) Program

## Program Details

- **Program**: HCV
- **State**: WA
- **White Label**: wa
- **Research Date**: 2026-05-06

## Eligibility Criteria

1. **Household annual gross income must not exceed the applicable HUD income limit for the area and household size.**
   - A household qualifies via either branch:
     - **(a) Very Low-Income (VLI)** — generally 50% of Area Median Income (AMI), adjusted for family size and area; OR
     - **(b) Low-Income (LI)** — generally 80% of AMI — AND meets one of: continuously assisted under public housing, HCV, project-based Section 8, or another 1937 Housing Act program; OR displaced by mortgage prepayment of "eligible low-income housing" per 24 CFR § 248.101; OR meets a PHA-set local-needs criterion.
   - Income limits vary by WA county/metro area and are published annually by HUD.
   - Screener fields:
     - `household_size`
     - `county`
     - `zipcode`
     - `income_streams[].category`, `.type`, `.frequency`, `.amount` (sum across all members for gross income)
   - Note: Branch 1(b) is a partial data gap — the screener does not capture continuous-assistance history, displacement-by-prepayment, or PHA-specific local criteria. Inclusivity assumption: apply only the VLI (50% AMI) test in the calculator. Households at 50–80% AMI who would qualify under branch 1(b) will be incorrectly screened out; surface this in the program description.
   - **Screener enhancement**: none recommended — affects a narrow subset of households and would require listing federal program names users don't recognize.
   - Source: 42 U.S.C. § 1437a(b)(2); 24 CFR § 982.201(b)(1); 24 CFR § 5.603; HUD FY2026 Section 8 Income Limits (https://www.huduser.gov/portal/datasets/il/il26/Section8-IncomeLimits-FY26.pdf); HUD FY2026 Income Limits Methodology (https://www.huduser.gov/portal/datasets/il/il26/IncomeLimitsMethodology-FY26.pdf)

2. **Applicant household must qualify as a "family" under HUD's definition.**
   - The HUD definition is broad — virtually any household composition qualifies, including:
     - A single person
     - A family with or without children
     - An elderly family (head, co-head, spouse, or sole member age 62+)
     - A near-elderly family (head, co-head, spouse, or sole member age 50–61)
     - A disabled family
     - A displaced family
     - The remaining member of a tenant family
   - A pregnant woman with no other household members is treated as a 2-person family for income-limit purposes.
   - Screener fields:
     - `household_size`
     - `birth_month`, `birth_year` (per member; derived `age`)
     - `pregnant`
     - `household_members[].relationship` (per-member relationship to head; valid enum values: `headOfHousehold`, `spouse`, `domesticPartner`, `child`, `fosterChild`, `parent`, `fosterParent`, `stepParent`, `grandParent`, `grandChild`, `sibling`, `other`)
     - `blind_or_visually_impaired`, `unable_to_work_due_to_disability`, `long_term_medical_or_developmental_condition`
   - Note: Basic eligibility is `household_size >= 1`. The `relationship` field allows us to fully evaluate the family sub-categories — e.g., "elderly family" can be checked by verifying the head, `spouse`, or sole member is age 62+. Sub-categories matter mainly for Priority Criteria and downstream income deductions, not basic eligibility. **Open question for dev**: confirm whether the disability/blindness fields on the `HouseholdMember` model are named `blind_or_visually_impaired`/`unable_to_work_due_to_disability`/`long_term_medical_or_developmental_condition` (per the MyFriendBen Screener Field Coverage Reference) or `visually_impaired`/`disabled`/`long_term_disability` (per the dev's earlier auto-fix). Two reference docs disagree — using whichever name is wrong will silently break the calculator.
   - Source: 24 CFR § 5.403; 24 CFR § 982.201(c); 24 CFR § 982.402(b)(5); HCV Guidebook (Eligibility Determination chapter), § 3

3. **At least one household member must be a U.S. citizen or have eligible immigration status.** ⚠️ *data gap*
   - Mixed families (with both eligible and ineligible members) receive prorated assistance.
   - Noncitizen students, even with otherwise eligible immigration status, are categorically ineligible — this exclusion also extends to their accompanying noncitizen spouse and minor children.
   - Screener fields: none
   - Note: The screener does not collect citizenship/immigration status — by design, MFB welcomes all users including immigrants and does not require them to disclose status during screening. Inclusivity assumption: assume all households meet this requirement; users will provide legal documentation at application via the SAVE system. Surface the requirement in the program description so users know to bring documentation when applying.
   - **Screener enhancement**: none — citizenship/immigration status is intentionally not collected (MFB design principle).
   - Source: 42 U.S.C. § 1436a(a); 24 CFR § 5.506; 24 CFR § 5.522; 24 CFR § 982.201(b)(3); HCV Guidebook (Eligibility Determination chapter), § 7

4. **Applicant household must not currently be receiving Section 8 assistance from any PHA.**
   - Applies to both tenant-based (HCV) and project-based Section 8 — duplicate Section 8 subsidies are prohibited.
   - Screener fields:
     - `has_section_8` (Screen-level Boolean)
   - Note: Verified at application via HUD's EIV Existing Tenant Search. In the screener, this maps directly to the `has_section_8` Boolean field on the Screen model — when `has_section_8 = true`, the household is currently receiving Section 8 and is excluded from a duplicate voucher. There is no single clean CFR/USC citation for the prohibition itself — it is operationalized through the EIV procedural check at admission.
   - Source: HCV Guidebook (Eligibility Determination chapter), § 2.2 and § 11.1 (EIV Existing Tenant Search and Avoiding Duplicate Subsidy)

5. **Net family assets must not exceed $100,000.** ⚠️ *data gap (partial)*
   - HOTMA asset limit; inflation-adjusted annually by HUD.
   - This rule was added by HOTMA (Pub. L. 114-201) and HUD's HOTMA implementing rule effective Jan 1, 2024. It is **not** in the November 2019 HCV Guidebook because that predates HOTMA implementation.
   - Screener fields:
     - `household_assets`
   - Note: The screener asks for a single total amount the household has in cash, checking/savings, stocks, bonds, or mutual funds — the user enters one number, no asset-type breakdown is captured. Inclusivity assumption: apply the $100,000 threshold against the screener's `household_assets` total. Households with substantial illiquid assets (vehicles, life insurance cash value, real property) that aren't part of the user-entered total may pass the screener but fail at application — surface this caveat in the program description.
   - **Screener enhancement**: none recommended — asset-type breakdown adds significant user friction without reliably matching any one program's asset rules.
   - Source: 42 U.S.C. § 1437n(e)(1)(A); 24 CFR § 5.618

6. **Household must not have an ownership interest in real property suitable for occupancy as a residence.** ⚠️ *data gap*
   - Specifically: no present ownership interest in, legal right to reside in, AND effective legal authority to sell such property.
   - Exceptions: HCV homeownership program participants, victims of domestic violence, and families actively offering the property for sale.
   - This rule was added by HOTMA (Pub. L. 114-201) and HUD's HOTMA implementing rule effective Jan 1, 2024. It is **not** in the November 2019 HCV Guidebook because that predates HOTMA implementation.
   - Screener fields: none
   - Note: The screener does not capture real property ownership. Inclusivity assumption: assume households meet this requirement; verified at application; surface in the program description.
   - **Screener enhancement (suggested)**: while `housing_situation` captures current residence type (renting, owning, etc.), a yes/no follow-up — "Does anyone in your household own real property (a home, condo, or other dwelling), other than their current residence, that they could legally live in?" — would close most of this gap. The same field would provide useful signal for any other WA program that treats real property as a countable asset or distinguishes property owners from renters. Program-specific exceptions (HCV homeownership program participant, domestic violence, actively listing for sale) would still need application-stage verification.
   - Source: 42 U.S.C. § 1437n(e)(1)(B); 24 CFR § 5.618

7. **No household member may be subject to a lifetime sex offender registration requirement under any state's program.** ⚠️ *data gap*
   - Mandatory federal denial — PHAs must check state registries.
   - Screener fields: none
   - Note: No screener field captures sex offender registry status. Inclusivity assumption: assume households meet this requirement; verified at application via PHA background screening.
   - **Screener enhancement**: none recommended for criteria 7–10 — criminal-history questions don't fit MFB's low-friction, low-judgment screener style and risk deterring eligible applicants.
   - Source: 42 U.S.C. § 13663; 24 CFR § 5.856; 24 CFR § 982.553(a)(2)(i); HCV Guidebook (Eligibility Determination chapter), § 10.1.4

8. **No household member may have been convicted of manufacturing methamphetamine on the premises of federally assisted housing.** ⚠️ *data gap*
   - Permanent ban — no time limit, no exceptions.
   - Screener fields: none
   - Note: No screener field captures criminal history. Inclusivity assumption: assume households meet this requirement; verified at application via PHA background screening.
   - **Screener enhancement**: none — see criterion 7.
   - Source: 42 U.S.C. § 1437n(f)(1); 24 CFR § 982.553(a)(1)(ii)(C); HCV Guidebook (Eligibility Determination chapter), § 10.1.4

9. **No household member may have been evicted from federally assisted housing for drug-related criminal activity within the past 3 years.** ⚠️ *data gap*
   - Exception: ban does not apply if the household member completed an approved rehabilitation program or the circumstances leading to eviction no longer exist.
   - Screener fields: none
   - Note: No screener field captures prior eviction or drug-related criminal history. Inclusivity assumption: assume households meet this requirement; verified at application.
   - **Screener enhancement**: none — see criterion 7.
   - Source: 42 U.S.C. § 13661(a); 24 CFR § 982.553(a)(1)(i); HCV Guidebook (Eligibility Determination chapter), § 10.1.4

10. **No household member may currently be illegally using a controlled substance, or have a pattern of drug or alcohol abuse that interferes with other residents.** ⚠️ *data gap*
    - Two-part rule:
      - Current illegal drug use is disqualifying on its own.
      - A pattern of illegal drug use OR pattern of alcohol abuse is disqualifying if it may interfere with the health, safety, or right to peaceful enjoyment of the premises by other residents.
    - This is separate from the conviction-based bans (criteria 8 and 9) — it is about *current* use, not past convictions.
    - Screener fields: none
    - Note: No screener field captures current drug use or alcohol abuse. Inclusivity assumption: assume households meet this requirement; verified at application.
    - **Screener enhancement**: none — see criterion 7.
    - Source: 42 U.S.C. § 13661(b); 24 CFR § 982.553(a)(1)(ii)(A)–(B); 24 CFR § 982.552(b); HCV Guidebook (Eligibility Determination chapter), § 10.1.4

11. **A student at an institution of higher education who does not live with their parents is subject to a special eligibility rule.** ⚠️ *data gap (partial)*
    - The rule applies regardless of full-time or part-time status.
    - A student is exempt from the rule if any one of the following is true:
      - Age 24 or older
      - Veteran
      - Married
      - Has a dependent child
      - Person with disabilities who was receiving HCV assistance as of Nov 30, 2005
      - Graduate or professional student
      - HUD-defined "independent student" (orphan, in/from foster care, ward of court, emancipated minor, or in legal guardianship)
      - "Vulnerable Youth" per the McKinney-Vento Homeless Assistance Act
    - A student who meets no exemption can still qualify via the dual-income test: BOTH (i) the student must be individually income-eligible AND (ii) the student's parents must be income-eligible.
    - Screener fields:
      - `student` and follow-ups (`student_half_time_or_more`, `student_job_training_program`, `student_work_study`, `student_work_hours_20_plus_or_80_monthly`)
      - `birth_year`, `birth_month` (derived `age`)
      - `household_members[].relationship` (key signals below)
      - `unable_to_work_due_to_disability`, `blind_or_visually_impaired`, `long_term_medical_or_developmental_condition`
      - `insurance = "VA health care benefits"` (partial proxy for veteran status — see enhancement note below)
      - `household_size`
    - Note: With the `relationship` field, several exemptions become evaluable:
      - **Rule does not apply at all** if the household includes anyone with `relationship: parent`, `fosterParent`, or `stepParent` — the student lives with a parent.
      - **Married exemption** is met if the household includes a `spouse` or `domesticPartner` relationship.
      - **Dependent-child exemption** is met if the household includes a `child`, `fosterChild`, or `stepChild`-equivalent relationship (note: the screener does not have a separate `stepChild` enum — `child` covers all child relationships).
      - **Age 24+** and **disability** exemptions are evaluable from existing fields.
      - **Veteran exemption** is only partially evaluable — `insurance = "VA health care benefits"` is a partial proxy because not all veterans have VA coverage.

      Remaining gaps: veteran status (partial proxy only), graduate/professional-student status, head's own past foster-care/ward history, Vulnerable Youth status, and parental income for the dual-income fallback.

      Inclusivity assumption: only flag a student as potentially ineligible if ALL of these are true — the user is a student under 24, no parent/spouse/child relationship in household, no VA insurance proxy, no disability indicator. Surface the rule in the program description so users with edge-case exemptions (veteran without VA coverage, graduate student, foster youth, etc.) can self-identify.
    - **Screener enhancement (suggested — veteran)**: add a per-member `veteran` Boolean under Special Circumstances. Today the only veteran signal is `insurance = "VA health care benefits"`, which misses veterans without VA coverage. A direct Boolean would close the gap for HCV's veteran-exemption and provide useful signal for any future WA program with veteran priority (e.g., VASH, state veteran services).
    - **Screener enhancement (suggested — foster youth)**: a per-member *past foster care / ward of court history* Boolean — distinct from the existing `relationship: fosterChild` field (which identifies a child *in the household* who is currently a foster child) — would close the head's-own-foster-history gap for HCV's "independent student" exemption and would also provide useful signal for any other WA program that gives standing or priority to former foster youth (e.g., John H. Chafee Foster Care Independence programs, Education and Training Voucher programs, age-extended Medicaid coverage for former foster youth).
    - Source: 24 CFR § 5.612; HCV Guidebook (Eligibility Determination chapter), §§ 5–6

## Priority Criteria

These are local PHA preferences that affect waitlist position rather than eligibility. They are not used for the calculator's pass/fail logic but should be highlighted in the program description so users know which preferences may apply to them.

1. **Elderly family preference** — many WA PHAs prioritize families whose head, co-head, spouse, or sole member is age 62+.
   - Source: 24 CFR § 982.207; PHA Administrative Plans (varies by PHA)

2. **Disabled family preference** — many WA PHAs prioritize families with a disabled head, co-head, spouse, or sole member.
   - Source: 24 CFR § 982.207; PHA Administrative Plans (varies by PHA)

3. **Families with children preference** — some PHAs prioritize families with dependent children.
   - Source: 24 CFR § 982.207; PHA Administrative Plans (varies by PHA)

4. **Veteran preference** — some WA PHAs prioritize veterans or families of veterans (VASH vouchers are specifically for veterans).
   - Source: 24 CFR § 982.207; HUD-VASH program requirements

5. **Homelessness preference** — several WA PHAs (e.g., Seattle Housing Authority, King County Housing Authority) prioritize families experiencing homelessness.
   - Source: 24 CFR § 982.207; PHA Administrative Plans (varies by PHA)

6. **Involuntary displacement preference** — some PHAs prioritize families displaced by government action, domestic violence, natural disaster, or other qualifying events.
   - Source: 24 CFR § 982.207; 24 CFR § 5.403 (definition of displaced family)

## Benefit Value

**Type**: Variable monthly subsidy (rental assistance), defined by regulation. The methodology below is **citable**, not estimated. The simplifying assumptions used at screener stage (called out below) introduce uncertainty in the dollar amount but preserve the structure of the underlying formula.

### Formula

The monthly Housing Assistance Payment (HAP) — paid directly by the PHA to the landlord on behalf of the family — is:

```
HAP = lower of (Payment Standard, Gross Rent) − Total Tenant Payment
```

Where:

- **Payment Standard**: an amount set by each PHA, generally between 90% and 110% of HUD's published Fair Market Rent (FMR) for the FMR area and unit bedroom size. PHAs may set values up to 120% with HUD approval.
- **Gross Rent**: contract rent plus a utility allowance for any utilities the tenant pays directly.
- **Total Tenant Payment (TTP)**: the greatest of (i) 30% of monthly adjusted income, (ii) 10% of monthly gross income, (iii) the welfare rent (where applicable), or (iv) the PHA minimum rent (typically $50).

### Inputs the screener has vs. does not have

- **Has**: gross income (via `incomeStreams`), household size and composition, county, ZIP, disability and elderly indicators.
- **Does not have**: the actual rent of a leased unit (the family hasn't yet selected one at screening), whether utilities are included in rent, bedroom count of the chosen unit, and most adjusted-income deductions (medical expenses, childcare, disability-assistance expenses).

### Recommended calculator methodology

For a screener-stage estimate, calculate as follows:

1. **Estimate bedroom size from family composition** using HUD's standard occupancy guideline of two persons per bedroom (24 CFR § 982.401(d)). Suggested mapping: 1–2 persons → 1BR; 3–4 → 2BR; 5–6 → 3BR; 7–8 → 4BR; 9+ → 5BR.

2. **Look up the FY2026 FMR** for the family's county / FMR area at the bedroom size from step 1, using HUD's published FMR tables.

3. **Set Payment Standard = 100% of FMR** as a default assumption. Each WA PHA sets its own Payment Standard within 90–110% of FMR; 100% is a reasonable midpoint. Document this assumption in the calculator code comments.

4. **Compute monthly adjusted income** from monthly gross income minus the deductions the screener can support. The dependent and elderly/disabled allowances are HOTMA baseline amounts that HUD adjusts annually for inflation (rounded to the next lowest multiple of $25); HUD publishes the updated amounts by September 1 each year, so the dev should look up the current FY2026 figure rather than hard-coding:
    - $480/year baseline ($40/month) per dependent — defined as a household member who is under 18, a full-time student, or a person with disabilities, excluding the head of household and spouse (24 CFR § 5.611(a)(1))
    - $525/year baseline ($43.75/month) for any elderly or disabled family (24 CFR § 5.611(a)(2))
    - Medical/health expense and childcare deductions are skipped at screener stage — data gap; document this assumption. (Under HOTMA the medical deduction is also restructured — applies to amounts exceeding 10% of annual income — so omitting it is conservative for screener purposes.)

5. **Compute Total Tenant Payment** as `max(0.30 × monthly adjusted income, 0.10 × monthly gross income, $50)`.

6. **Compute Monthly HAP** as `max(0, Payment Standard − TTP)`. (HAP cannot be negative; a family whose TTP exceeds the Payment Standard is still technically eligible but receives $0 subsidy that month.)

7. **Report annualized benefit** as `Monthly HAP × 12`.

### Source

- HAP calculation: 24 CFR § 982.505
- Payment Standard: 24 CFR § 982.503
- Total Tenant Payment: 24 CFR § 5.628; 42 U.S.C. § 1437a(a)
- Annual income definition: 24 CFR § 5.609
- Adjusted income / deductions: 24 CFR § 5.611
- Occupancy / unit size: 24 CFR § 982.401(d)
- HUD Fair Market Rents (FY2026, published annually): https://www.huduser.gov/portal/datasets/fmr.html

### Confidence

- **Citable, regulation-defined**: the formula structure, TTP calculation, and dependent/elderly deductions
- **Estimated assumptions** (introducing uncertainty): Payment Standard set to 100% of FMR (PHA-specific in reality), bedroom size derived from occupancy formula (real households may select smaller or larger units), and omitted medical/childcare deductions

The screener-stage estimate is likely to **underestimate** the true HAP slightly because the omitted deductions (medical, childcare) would lower adjusted income and thereby lower TTP, raising HAP. Estimates within ±15% of the actual subsidy are reasonable for a screener.

## Implementation Coverage

- ✅ Fully evaluable: 2 (criteria 2, 4 — basic family eligibility and duplicate-subsidy check)
- 🟡 Partially evaluable (real screener support, with documented gaps): 3 (criteria 1, 5, 11)
- ⚠️ Full data gaps (no screener support; rely on inclusivity assumptions surfaced in the program description): 6 (criteria 3, 6, 7, 8, 9, 10)

The income eligibility check (criterion 1) is the primary evaluable test and requires a county-specific lookup table of HUD FY2026 VLI limits for Washington State. The asset cap (criterion 5) is evaluated against the screener's `household_assets` total. The student restriction (criterion 11) can be evaluated for the most common exemptions thanks to the `relationship` field (parent → rule does not apply; spouse → married; child/fosterChild → dependent child); remaining gaps are veteran status (only partially evaluable via the `insurance = "VA health care benefits"` proxy), graduate-student status, the head's own foster history, Vulnerable Youth, and parental income. Criminal-history (7–10), immigration-status (3), and real-property-ownership (6) criteria are pure data gaps verified at application. Suggestions for closing or narrowing each gap are inline within each criterion.

## Research Sources

- [HUD Housing Choice Voucher (Section 8) Program Guide for Tenants — 42 U.S.C. § 1437f](https://www.hud.gov/helping-americans/housing-choice-vouchers-tenants)
- [HCV Guidebook: Eligibility Determination and Denial of Assistance — 24 CFR § 982.201](https://www.hud.gov/sites/dfiles/PIH/documents/HCV_Guidebook_Eligibility_Determination_and_Denial_of_Assistance.pdf)
- [HUD Section 8 Income Limits Summary for FY2026 — 42 U.S.C. § 1437a(b)(2)](https://www.huduser.gov/portal/datasets/il/il26/Section8-IncomeLimits-FY26.pdf)
- [HUD FY2026 Income Limits Calculation Methodology — 42 U.S.C. § 1437a(b)(2); 24 CFR § 5.609](https://www.huduser.gov/portal/datasets/il/il26/IncomeLimitsMethodology-FY26.pdf)
- [USA.gov Overview: Housing Choice Voucher (Section 8) Program — 42 U.S.C. § 1437f](https://www.usa.gov/housing-voucher-section-8)

## Research Output

Local path: `/app/output/wa_HCV_20260506_141730`

Files generated:
- Program config: `{white_label}_{program_name}_initial_config.json`
- Test cases: `{white_label}_{program_name}_test_cases.json`
- Full research data in output directory


## Acceptance Criteria

Each scenario in the Test Scenarios section below is an acceptance criterion. The implementation should produce the **Expected** outcome (Eligible / Not eligible) for each scenario. Specific dollar values for the calculated HCV benefit should follow the methodology in the Benefit Value section and are not hard-coded in these scenarios; the dev should verify benefit-value math against the formula plus FY2026 FMR / income-limit lookups.

## Test Scenarios

### Scenario 1: Single Mother + 2 Children, King County (Basic Eligible)

**What we're checking**: Income eligibility (Criterion 1 — VLI test), basic family qualification (Criterion 2), and no duplicate Section 8 (Criterion 4).
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `98108`, county `King County`
- **Household size**: 3
- **Person 1** (head): birth `Mar 1991` (age 35)
  - Income: Employment / Wages, `$1,800`/month
- **Person 2**: birth `Sep 2016` (age 9), `relationship: child`
- **Person 3**: birth `Jan 2021` (age 5), `relationship: child`
- **Current benefits**: `has_section_8 = false`

**Why this matters**: Single parents with young children are the most common HCV applicant type. This is the primary regression test for the standard income-eligible path through the calculator.

---

### Scenario 2: Family of 4 Just Below VLI, Pierce County (Income Boundary — Below)

**What we're checking**: Income eligibility at the lower boundary (Criterion 1 — 4-person VLI for Tacoma HMFA).
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `98402`, county `Pierce County`
- **Household size**: 4
- **Person 1** (head): birth `Mar 1986` (age 40)
  - Income: Employment / Wages, `$3,583`/month *(verify against FY2026 4-person VLI for Tacoma HMFA — should land just below threshold)*
- **Person 2**: birth `Jul 1988` (age 37), `relationship: spouse`
- **Person 3**: birth `Jan 2016` (age 10), `relationship: child`
- **Person 4**: birth `Sep 2019` (age 6), `relationship: child`
- **Current benefits**: `has_section_8 = false`

**Why this matters**: Confirms the calculator correctly INCLUDES households whose income lands just below the VLI threshold. Boundary cases are where off-by-one comparison errors typically appear.

---

### Scenario 3: Single Adult Exactly at VLI, Clark County (Income Boundary — At Limit)

**What we're checking**: Income eligibility at exactly the VLI limit (Criterion 1 — 1-person VLI for Portland-Vancouver-Hillsboro HMFA).
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `98661`, county `Clark County`
- **Household size**: 1
- **Person 1** (head): birth `Aug 1981` (age 44)
  - Income: Employment / Wages, `$2,917`/month *(verify equals FY2026 1-person VLI for Portland-Vancouver-Hillsboro HMFA / 12)*
- **Current benefits**: `has_section_8 = false`

**Why this matters**: HUD income-limit policy treats income at the limit as eligible (the comparison is `<=`, not `<`). Easy to get wrong and silently exclude qualifying applicants.

---

### Scenario 4: Family of 3 Just Above VLI, Snohomish County (Income Boundary — Above)

**What we're checking**: Income eligibility boundary above the limit (Criterion 1 — 3-person VLI for Seattle-Bellevue HMFA).
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `98201`, county `Snohomish County`
- **Household size**: 3
- **Person 1** (head): birth `Aug 1986` (age 39)
  - Income: Employment / Wages, `$3,542`/month
- **Person 2**: birth `Nov 1988` (age 37), `relationship: spouse`
  - Income: Employment / Wages, `$1,250`/month
- **Person 3**: birth `Mar 2018` (age 8), `relationship: child`
- **Current benefits**: `has_section_8 = false`

*(Combined annual income should be ~$50–$200 above the FY2026 3-person VLI for Seattle-Bellevue HMFA — verify against table.)*

**Why this matters**: Confirms the calculator correctly EXCLUDES households just above the VLI threshold. Pairs with Scenario 2 to lock down both sides of the boundary.

---

### Scenario 5: Elderly Single Adult, Kitsap County

**What we're checking**: Income eligibility (Criterion 1) for an elderly applicant with non-employment income (Social Security Retirement).
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `98312`, county `Kitsap County`
- **Household size**: 1
- **Person 1** (head): birth `Jan 1951` (age 75)
  - Income: Social Security Retirement, `$1,200`/month
  - Insurance: Medicare
- **Current benefits**: `has_section_8 = false`

**Why this matters**: A large share of HCV applicants are seniors on fixed retirement income. Validates that non-wage income streams are correctly summed for the gross-income test and that elderly indicators don't trigger any unexpected calculator branches.

---

### Scenario 6: Family in Rural Walla Walla County

**What we're checking**: Geographic coverage (Criterion 1 lookup for a non-metro WA county).
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `99362`, county `Walla Walla County`
- **Household size**: 3
- **Person 1** (head): birth `Sep 1988` (age 37)
  - Income: Employment / Wages, `$1,800`/month
- **Person 2**: birth `Feb 1990` (age 36), `relationship: spouse`
  - Income: Employment / Wages, `$1,200`/month
- **Person 3**: birth `Jul 2018` (age 7), `relationship: child`
- **Current benefits**: `has_section_8 = false`

**Why this matters**: WA's FMR and income-limit tables include both metro HMFAs and non-metro counties. This ensures rural counties aren't missing from the lookup table — a common implementation gap when teams test only major metros.

---

### Scenario 7: Currently Receiving Section 8 (Criterion 4 Ineligible)

**What we're checking**: Duplicate-Section-8 exclusion (Criterion 4 — `has_section_8 = true` should disqualify regardless of income).
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `98103`, county `King County`
- **Household size**: 3
- **Person 1** (head): birth `Mar 1980` (age 46)
  - Income: Employment / Wages, `$2,000`/month
- **Person 2**: birth `Jul 1982` (age 43), `relationship: spouse`
  - Income: Employment / Wages, `$1,200`/month
- **Person 3**: birth `Sep 2016` (age 9), `relationship: child`
- **Current benefits**: `has_section_8 = true`

**Why this matters**: The duplicate-subsidy prohibition is one of two fully evaluable criteria. A household that's otherwise income-eligible must still be excluded if they already have a voucher.

---

### Scenario 8: Multi-Generational Household with Multiple Income Types, Grant County

**What we're checking**: Multi-member income aggregation (Criterion 1) across multiple income types (Social Security Retirement, VA Pension, SSDI, wages), with elderly and disability indicators on different members.
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `98837`, county `Grant County`
- **Household size**: 5
- **Person 1** (head): birth `Jan 1958` (age 68)
  - Income: Social Security Retirement, `$1,200`/month
  - Income: VA Pension, `$400`/month
  - Insurance: VA health care benefits, Medicare
- **Person 2**: birth `Mar 1960` (age 66), `relationship: spouse`
  - `unable_to_work_due_to_disability = true`
  - Income: SSDI, `$950`/month
- **Person 3**: birth `Aug 1994` (age 31), `relationship: child`
  - Income: Employment / Wages, `$1,400`/month
- **Person 4**: birth `Jun 2018` (age 7), `relationship: grandChild`
- **Person 5**: birth `Nov 2021` (age 4), `relationship: grandChild`
- **Current benefits**: `has_section_8 = false`

**Why this matters**: Real HCV applicants often include several earners and several income types. Validates that the calculator sums correctly across members and types, and that elderly/disability fields on non-head members don't disrupt the eligibility calculation.

---

### Scenario 9: Three Adult Siblings Sharing Household, Whatcom County

**What we're checking**: Family-definition flexibility (Criterion 2) and multi-adult income aggregation (Criterion 1) for a non-traditional household.
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `98225`, county `Whatcom County`
- **Household size**: 3
- **Person 1** (head): birth `Sep 1991` (age 34)
  - Income: Employment / Wages, `$1,400`/month
- **Person 2**: birth `Feb 1994` (age 32), `relationship: sibling`
  - Income: Employment / Wages, `$1,200`/month
- **Person 3**: birth `Nov 1997` (age 28), `relationship: sibling`
  - Income: Employment / Wages, `$1,000`/month
- **Current benefits**: `has_section_8 = false`

**Why this matters**: HUD's family definition is broad — including non-traditional groupings like adult siblings sharing housing. Confirms the calculator doesn't accidentally require children, spouses, or seniors as a prerequisite.

---

### Scenario 10: Household of 8 at VLI, King County (Large Household Edge Case)

**What we're checking**: Large-household income-limit lookup (Criterion 1 — 8-person VLI for Seattle-Bellevue HMFA, applying the 1.32× 4-person multiplier).
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `98101`, county `King County`
- **Household size**: 8
- **Person 1** (head): birth `Mar 1981` (age 45)
  - Income: Employment / Wages, `$2,917`/month
- **Person 2**: birth `Jul 1983` (age 42), `relationship: spouse`
  - Income: Employment / Wages, `$2,500`/month
- **Person 3**: birth `Jan 2008` (age 18), `relationship: child`
  - Income: Employment / Wages, `$500`/month
- **Person 4**: birth `Sep 2010` (age 15), `relationship: child`
- **Person 5**: birth `Feb 2013` (age 13), `relationship: child`
- **Person 6**: birth `Nov 2015` (age 10), `relationship: child`
- **Person 7**: birth `Apr 2018` (age 8), `relationship: child`
- **Person 8**: birth `Jun 2021` (age 4), `relationship: child`
- **Current benefits**: `has_section_8 = false`

*(Combined annual income should be at or just below the FY2026 8-person VLI for Seattle-Bellevue HMFA — verify against table.)*

**Why this matters**: HUD income limits adjust by family size up to 8+ persons. Tables that stop at 4 or 6 persons will silently break for large families. Also exercises the screener's max household size of 8.

---

### Scenario 11: Otherwise-Eligible Household with Liquid Assets > $100K, Spokane County (Asset Cap Ineligible)

**What we're checking**: HOTMA asset cap exclusion (Criterion 5 — `household_assets > $100,000` disqualifies regardless of income).
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `99201`, county `Spokane County`
- **Household size**: 2
- **Person 1** (head): birth `Jun 1972` (age 53)
  - Income: Employment / Wages, `$2,000`/month
- **Person 2**: birth `Mar 1974` (age 51), `relationship: spouse`
  - Income: Employment / Wages, `$1,200`/month
- **Household assets**: `$150,000`
- **Current benefits**: `has_section_8 = false`

**Why this matters**: The HOTMA $100K asset cap is the second fully evaluable criterion after the duplicate-Section-8 check. A household that's income-eligible but asset-ineligible must still be excluded.

---

### Scenario 12: Single Pregnant Adult, Pierce County (Pregnant = 2-Person Family Rule)

**What we're checking**: Pregnancy + household-size special rule (Criterion 2 — a pregnant person with no other household members is counted as 2 for income-limit purposes per 24 CFR § 982.402(b)(5)).
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `98402`, county `Pierce County`
- **Household size**: 1
- **Person 1** (head): birth `May 1995` (age 31)
  - `pregnant = true`
  - Income: Employment / Wages, `$2,400`/month *(should be at or below the FY2026 2-person VLI for Tacoma HMFA — verify)*
- **Current benefits**: `has_section_8 = false`

**Why this matters**: This is an HCV-specific quirk that's easy to miss. Without the special rule, a pregnant applicant living alone would be tested against the 1-person VLI instead of the (more generous) 2-person VLI and might be incorrectly excluded.

---

### Scenario 13: Single Student Under 24, No Disqualifying Factors (Student Inclusivity)

**What we're checking**: Student-rule inclusivity (Criterion 11 — a single student under 24 with no parent/spouse/child/disability/VA-insurance indicator should still be eligible per the inclusivity assumption).
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `99201`, county `Spokane County`
- **Household size**: 1
- **Person 1** (head): birth `Sep 2003` (age 22)
  - `student = true`; `student_half_time_or_more = true`
  - Income: Employment / Wages, `$1,200`/month
- **Current benefits**: `has_section_8 = false`

**Why this matters**: The student rule has many exemptions (veteran, foster youth, graduate student, married, etc.) the screener can't fully evaluate. The inclusivity assumption says we shouldn't flag students as ineligible based on partial-field heuristics alone — this prevents over-exclusion of edge-case exemptees.

---


## Source Documentation

- https://www.hud.gov/helping-americans/housing-choice-vouchers-tenants
- https://www.hud.gov/sites/dfiles/PIH/documents/HCV_Guidebook_Eligibility_Determination_and_Denial_of_Assistance.pdf
- https://www.huduser.gov/portal/datasets/il/il26/Section8-IncomeLimits-FY26.pdf
- https://www.huduser.gov/portal/datasets/il/il26/IncomeLimitsMethodology-FY26.pdf
- https://www.usa.gov/housing-voucher-section-8

## JSON Test Cases
File: `/app/output/wa_HCV_20260506_141730/ticket_content/wa_HCV_test_cases.json`

## Program Configuration
File: `/app/output/wa_HCV_20260506_141730/ticket_content/wa_HCV_initial_config.json`
