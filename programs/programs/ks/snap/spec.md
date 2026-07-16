# Implement Food Assistance - Supplemental Nutrition Assistance Program (SNAP) (KS) Program

## Program Details

- **Program**: Food Assistance - Supplemental Nutrition Assistance Program (SNAP)
- **State**: KS
- **White Label**: ks
- **Calculator Type**: PE Federal (state values)
- **PE Variable**: `snap` (implemented as `KsSnap(Snap)` — PolicyEngine federal SNAP calculator + KS state code)
- **Research Date**: 2026-06-21
- **Spec basis**: Adapted from `wa/snap/spec.md` (federal SNAP precedent). **Key state difference: Kansas has NOT adopted BBCE**, so WA's 200% FPL gross / waived-net / no-asset-test rules are replaced with the standard federal tests (130% gross, 100% net, $3,000/$4,500 asset limit). The only KS-specific *value* is the Standard Utility Allowance (SUA); value scenarios isolate it.

## Eligibility Criteria

> Listed core/priority criteria first (all screener-evaluable), then federal rules that the screener cannot measure (⚠️ data gaps), each with a handling suggestion. Pure administrative / application-stage requirements are **excluded** — see "Administrative requirements (excluded)" below.

### Core / priority criteria (screener-evaluable)

1. **Gross monthly income at or below 130% of the Federal Poverty Level** *(priority)*
   - Screener fields: `household_size`, `calc_gross_income`
   - Note: Kansas has **not** adopted Broad-Based Categorical Eligibility (the legislature prohibited it), so the standard federal 130% FPL gross test applies — not the 200% BBCE limit WA uses. FY2026 monthly limits (KEESM Appendix F-2): HH1 $1,696; HH2 $2,292; HH3 $2,888; HH4 $3,483; HH5 $4,079 (+$596 per additional person).
   - Source: 7 CFR 273.9(a)(1); KEESM Appendix F-2; FNS BBCE State Chart (KS not listed).

2. **Net monthly income at or below 100% of the Federal Poverty Level — test APPLIES** *(priority)*
   - Screener fields: `household_size`, `calc_net_income`
   - Note: Because KS has no BBCE, the 100% FPL net income test applies to all households (in WA it is waived). FY2026 monthly net limits: HH1 $1,305; HH2 $1,763; HH3 $2,221; HH4 $2,680; HH5 $3,138 (+$459 per additional person).
   - Source: 7 CFR 273.9(a)(2); KEESM Appendix F-2.

3. **Asset/resource test APPLIES: $3,000 standard; $4,500 for households with an elderly (60+) or disabled member** *(priority — KS-distinctive)*
   - Screener fields: `household_assets`
   - Note: KS has no BBCE asset-test waiver, so the standard federal resource limits apply (verified current for FY2026). PE's `snap_assets` counts liquid resources (bank accounts, stocks, bonds) and excludes vehicles — an acceptable approximation.
   - Source: 7 CFR 273.8; FNS FY2026 COLA; KEESM Appendix F-2.

4. **Household size determination** *(priority — foundational)*
   - Screener fields: `household_size`
   - Note: People who live together and customarily purchase and prepare meals together are one SNAP household. **A pregnant woman counts as one member** (unborn children are not counted); the `pregnant` field matters only for the work-requirement exemption, not household size.
   - Source: 7 CFR 273.1(a)-(b); KEESM.

5. **TANF/SSI categorical eligibility — households where all members receive TANF or SSI are categorically eligible** *(priority)*
   - Screener fields: `has_tanf`, `has_ssi`
   - Note: Categorical eligibility bypasses the financial (income and asset) tests; non-financial rules (student, citizenship, residency) still apply. *All* members must receive TANF or SSI. (KS's SSPP does not independently confer categorical eligibility — SSPP recipients qualify via their SSI status.)
   - Source: 7 CFR 273.2(j); 7 U.S.C. § 2014(a); KEESM Section 2510.

6. **Elderly or disabled household member — federal alternative treatment**
   - Screener fields: `birth_year`, `birth_month`, `disabled`, `calc_net_income`, `household_assets`
   - Note: A household with a member aged 60+ or disabled is **exempt from the gross income test** and qualifies on the net income test (≤100% FPL) alone, uses the higher **$4,500** asset limit, and receives an **uncapped** excess-shelter deduction. (There is no BBCE Option A/B; this is the standard federal treatment.)
   - Source: 7 CFR 273.9(a); 7 CFR 273.8; 7 CFR 273.9(d)(6); KEESM Appendix F-2.

7. **Student eligibility — half-time+ college students aged 18–49 must meet an exemption**
   - Screener fields: `student`, `student_full_time`, `student_works_20_plus_hrs`, `student_has_work_study`, `student_job_training_program`, `birth_year`, `birth_month`
   - Note: Students enrolled at least half-time in higher education are ineligible unless they meet an exemption (working 20+ hrs/week, work-study, job-training/employment-and-training program, caring for a dependent child under 6 — or under 12 if a single parent enrolled full-time — or age 17 or younger).
   - Source: 7 CFR 273.5; 7 U.S.C. § 2015(e); KEESM Student Eligibility Criteria.

8. **Must not already be receiving SNAP/Food Assistance benefits**
   - Screener fields: current benefits (read via `screen.has_benefit("ks_snap")` / `has_base_benefit("snap")`). Not a calculator check — the generic `already_has` results-layer workflow filters the program out of results when the household reports it.
   - Source: General SNAP policy — households cannot receive duplicate benefits.

9. **State residency — must reside in Kansas**
   - Screener fields: `zipcode`, `county`
   - Source: 7 CFR 273.3; KEESM.

### Federal & KS-specific rules the screener cannot fully measure (⚠️ data gaps)

10. **At least one household member must be a U.S. citizen or qualified non-citizen** ⚠️ *not screened — by design*
    - Note: This is a federal eligibility rule, but **MFB intentionally does not screen or gate on citizenship.** The calculation always runs as `CITIZEN`, so SNAP is computed and shown to everyone; status only affects which program cards are *displayed*, via the results-page `legal_status_required` filter (post-OBBBA: `citizen`, `gc_5plus`, `gc_5less`). KS has no state-funded food program for immigrants (unlike WA's FAP).
    - **Suggestion — no screener improvement:** Because citizenship isn't a screener input at all (it's handled only as a results-page display filter), there's no screener field to add. The single action is keeping that filter accurate — the dev's current cleanup dropping the now-ineligible statuses (`refugee`, `non_citizen`, `otherWithWorkPermission`). The Cuban/Haitian/COFA edge stays an accepted inclusivity assumption (small group; PE's COFA gap #8296 mishandles it anyway).
    - Source: 7 U.S.C. § 2015(f); 7 CFR 273.4. Impact: Medium

11. **General work requirement — "work registrants" aged 18–59 must register for work, accept suitable employment, and not voluntarily quit** ⚠️ *data gap (PE applies the hours test)*
    - Note: Kansas's HOPE Act sets the general SNAP work requirement at **30 hours/week** (the federal general-requirement threshold) and refers anyone working under it to **mandatory Employment & Training**; KS extended this stricter treatment to ages 50–59. PE applies the hours-based general work test via `weekly_hours_worked_before_lsr`, so a working applicant passes and an unexempted non-worker fails. Not captured: E&T-participation compliance, and the reason for a job separation (voluntary quit / hour reduction below 30/week without good cause).
    - **Suggestion (inclusivity assumption):** Don't add E&T-compliance or job-separation-reason questions (administrative, rarely dispositive at screening). PE's point-in-time hours test is sufficient; assume compliant / good cause. The config description's work line covers expectations.
    - Source: 7 CFR 273.7; K.S.A. 39-709 (HOPE Act); KEESM. Impact: Medium

12. **ABAWD time limit — able-bodied adults without dependents aged 18–64 limited to 3 months of benefits in 36 unless working ≥80 hrs/month** ⚠️ *data gap (PE applies the hours test)*
    - Note: KS applies full ABAWD rules statewide with **no waivers** (FY2025–2026); age range **18–64** (federal OBBBA expansion; KS independently added 50–59 in 2023). PE applies the work test monthly via `weekly_hours_worked_before_lsr` but does not model the **3-month-in-36 time-limit clock** (months of prior SNAP receipt).
    - **Suggestion (inclusivity assumption + program description):** Don't ask prior-SNAP-receipt history (invasive, low-value). Assume not time-limited. The program description already surfaces this ("Adults without dependents may need to work or train to keep their benefits") — keep that line.
    - Source: 7 U.S.C. § 2015(o); 7 CFR 273.24; FNS ABAWD Waivers FY2025–2029 (KS not waived). Impact: Medium

13. **Child support cooperation — Kansas requires custodial parents to cooperate with child support enforcement as a condition of eligibility** ⚠️ *data gap — KS-specific state option*
    - Note: **KS-specific.** Federal SNAP makes child-support cooperation a *state option*; Kansas adopted it (HOPE Act, 2015) and has repeatedly declined to repeal it. A custodial parent living with a child whose other parent is absent must cooperate in establishing paternity and pursuing support; without cooperation — and absent a good-cause exception such as domestic violence — that adult is ineligible. The child(ren) may remain eligible, and the non-cooperating adult's income/resources are counted pro-rata. The screener does not collect cooperation status, and PolicyEngine does not model it.
    - **Suggestion (inclusivity assumption + surface in program description):** Don't add a screener question — it's invasive, hinges on an absent parent and good-cause/abuse exceptions, and conflicts with MFB's simple design; assume the applicant cooperates or has good cause (inclusive default for the calculation). But because this hits a meaningful population (single parents) and is a real KS condition, **add a brief, neutral line to the program description** — e.g. "Single parents may need to cooperate with child support services to get benefits. Some exceptions apply, such as for safety reasons." Keep it short and non-alarming.
    - Source: 7 CFR 273.11(o)-(p) (state option); K.S.A. 39-709; KEESM. Impact: Medium

14. **Drug felony disqualification — Kansas modified ban** ⚠️ *data gap*
    - Note: KS has a **modified** ban (Kan. Stat. Ann. § 39-709(f)(4)): convictions on/after July 1, 2015 disqualify; a first conviction allows reinstatement via treatment/testing, a second+ is permanent. PE does not model this; the screener does not collect criminal history.
    - **Suggestion (inclusivity assumption):** Do not add a criminal-history question (invasive, sensitive, small affected population). Assume not disqualified. Not recommended for the program description either — too niche and potentially alarming.
    - Source: Kan. Stat. Ann. § 39-709(f)(4); 21 U.S.C. § 862a (federal drug-felony ban states may modify). Impact: Low

15. **Must not be a fleeing felon or in violation of parole/probation** ⚠️ *data gap*
    - Note: Federal disqualification; not screenable.
    - **Suggestion (inclusivity assumption):** Do not collect criminal-justice status (invasive, small population). Assume not disqualified.
    - Source: 7 CFR 273.11(n). Impact: Low

16. **Must not reside in an ineligible institutional setting** ⚠️ *data gap*
    - Note: Homeless individuals ARE eligible; this excludes those in institutions (prisons, long-term hospitals, nursing homes). The screener's `housing_situation` captures homelessness but not institutional residence.
    - **Suggestion (inclusivity assumption):** No dedicated field needed — the vast majority of screener users are community-residing. Assume not institutionalized. (`housing_situation` already correctly keeps homeless users eligible.)
    - Source: 7 CFR 273.1(b). Impact: Low

17. **Precise net-income deduction calculations** (value-precision note, not an eligibility gate)
    - Note: The screener approximates net income; PolicyEngine computes the exact deductions. KS FY2026 values (KEESM Appendix F-2): standard deduction $209 (HH 1–3) / $223 (4) / $261 (5) / $299 (6+); **SUA/HCSUA $469**, LUA $345, Telephone $44; excess shelter cap **$744** (uncapped for elderly/disabled); homeless shelter deduction $198.99; standard medical deduction $175 (elderly/disabled only).
    - **Suggestion:** No screener change needed — `estimated_value` uses PolicyEngine's exact calculation. The screener's approximate net income is used only for the eligibility gate, which is acceptable.
    - Source: 7 CFR 273.9(d); KEESM Appendix F-2.

### Administrative requirements (excluded from eligibility criteria)

These are application/process requirements, not eligibility rules the screener should evaluate, so they are intentionally **not** listed above: **SSN provision** (7 CFR 273.6 — application-stage), **identity verification & interview** (7 CFR 273.2(e) — process), and **Intentional Program Violation (IPV) disqualification** (7 CFR 273.16 — verified administratively via state databases). None are screenable and none belong in the eligibility logic.


## Benefit Value

- Calculated as **maximum allotment for household size MINUS 30% of net monthly income** (net income = gross minus the standard deduction, 20% earned-income deduction, excess shelter + Standard Utility Allowance, dependent care, and elderly/disabled medical deductions).
- Maximum monthly allotments (48 contiguous states + DC, eff. October 2025; KEESM Appendix F-2, verified):

| Household Size | Max Monthly Benefit | Annual Value |
|---|---|---|
| 1 | $298 | $3,576 |
| 2 | $546 | $6,552 |
| 3 | $785 | $9,420 |
| 4 | $994 | $11,928 |
| 5 | $1,183 | $14,196 |
| Each add'l | +$218 | +$2,616 |

- **KS state-specific value:** the Standard Utility Allowance feeds the excess-shelter deduction. KS FY2026 HCSUA = **$469/mo** (LUA $345, phone $44), verified against KEESM Appendix F-2 and confirmed in PolicyEngine effective 2025-10-01.
- `estimated_value` uses PolicyEngine's exact calculation (the screener's net-income approximation is not used for the dollar amount).
- Source: [KEESM Appendix F-2](https://content.dcf.ks.gov/EES/KEESM/Appendix/F-2%20FA%20Program%20Standards.pdf); [FNS FY2026 COLA](https://www.fns.usda.gov/snap/allotment/cola/fy26); [CBPP SNAP guide](https://www.cbpp.org/research/food-assistance/a-quick-guide-to-snap-eligibility-and-benefits).


## Implementation Coverage

- ✅ Evaluable criteria: 9 (criteria 1–9)
- ⚠️ Data gaps: 7 (criteria 10–16) — work requirements (11–12) are partially applied by PolicyEngine via the hours test; all are otherwise addressed via inclusivity assumptions or program-description surfacing; none is viable/appropriate as a new screener field
- ℹ️ Value-precision note: 1 (criterion 17) — handled by PolicyEngine

The screener evaluates the criteria that drive nearly all SNAP outcomes: gross income (130% FPL), net income (100% FPL), the $3,000/$4,500 asset test, household size, TANF/SSI categorical eligibility, the elderly/disabled path, student rules, duplicate-benefit exclusion, and residency. Because KS has no BBCE, the net income test and asset test are *live* screening criteria here (they are not for WA). The data gaps are federal rules — plus one **KS-specific** rule, the child-support-cooperation requirement (criterion 13) — that are invasive or low-value to screen for; each is handled by the `CITIZEN` inclusivity default, the point-in-time work-hours test PolicyEngine already applies, an "assume not disqualified / cooperating" inclusivity assumption, or existing program-description language — consistent with MFB's inclusive design.


## Acceptance Criteria

All dollar values are the expected annual benefit, derived independently from the FY2026 SNAP
benefit formula (max allotment − 30% of net income, with the standard, 20%-earned-income, and
excess-shelter/SUA deductions) and confirmed against the calculator. Monthly figures are shown
for reference.

- [ ] Scenario 1 (Single Adult Worker — Clearly Eligible): **eligible**, **$864/yr ($72/mo)**
- [ ] Scenario 2 (Family of Four — Just Under 130% Gross & 100% Net): **eligible**, **$6,432/yr ($536/mo)**
- [ ] Scenario 3 (Single Parent HH2 — Gross $1 Below 130% FPL): **eligible**, **$3,540/yr ($295/mo)**
- [ ] Scenario 4 (Single Adult — Gross Above 130% FPL): **ineligible** ($0)
- [ ] Scenario 5 (Net Income Test Failure — Gross Passes, Net Fails): **ineligible** ($0)
- [ ] Scenario 6 (Non-Elderly Household — Assets Above $3,000): **ineligible** ($0)
- [ ] Scenario 7 (Elderly — Gross Above 130%, Net Below 100%, Assets ≤ $4,500): **eligible**, **$276/yr ($23/mo)**
- [ ] Scenario 8 (Categorical Eligibility — All Members on SSI, Income/Assets Above Limits): **eligible**, **$1,080/yr ($90/mo)** — ⏸️ *deferred to MFB-1312 (SSI categorical requires the global `use_reported_ssi` change; not wired in this PR)*
- [ ] Scenario 9 (Half-Time Student 18–49, No Exemption): **ineligible** ($0)
- [ ] Scenario 10 (Half-Time Student with Job-Training Exemption): **eligible**, **$864/yr ($72/mo)**
- [ ] Scenario 11 (Already Receiving SNAP — Duplicate Exclusion): **ineligible** (gated by MFB `already_has` results-layer filter, not raw PE)
- [ ] Scenario 12 (SUA value — Single Adult): **eligible**, **$2,424/yr ($202/mo)**
- [ ] Scenario 13 (SUA value — Elderly Individual): **eligible**, **$3,576/yr ($298/mo)**
- [ ] Scenario 14 (SUA value — Family of Three): **eligible**, **$4,668/yr ($389/mo)**
- [ ] Scenario 15 (Asset Test Pass — Below Standard $3,000 Limit): **eligible**, **$1,728/yr ($144/mo)**
- [ ] Scenario 16 (Large Household of Five): **eligible**, **$7,212/yr ($601/mo)**
- [ ] Scenario 17 (Disabled Non-Elderly — Uncapped Shelter & $4,500 Asset Limit): **eligible**, **$1,884/yr ($157/mo)**
- [ ] Scenario 18 (TANF Categorical Eligibility — Cash Recipient, Assets Above Limit): **eligible**, **$2,880/yr ($240/mo)**
- [ ] Scenario 19 (Half-Time Student Working 20+ Hours/Week): **eligible**, **$864/yr ($72/mo)**
- [ ] Scenario 20 (Half-Time Student with Federal Work-Study): **eligible**, **$864/yr ($72/mo)**
- [ ] Scenario 21 (Single Full-Time Student Parent with Dependent Child): **eligible**, **$3,840/yr ($320/mo)**
- [ ] Scenario 22 (SSI Categorical — Reported Receipt with High Other Income): **eligible**, **$276/yr ($23/mo)** — ⏸️ *deferred to MFB-1312 (SSI categorical requires the global `use_reported_ssi` change; not wired in this PR)*


## Test Scenarios

> **Verification method.** Each value is derived independently from the FY2026 SNAP policy
> formula (KEESM Appendix F-2 / FNS FY2026 parameters) and then checked against the calculator —
> the spec is the oracle, not a copy of calculator output. Eligible cases assert the computed
> annual benefit; ineligible cases (4–6, 9) assert **$0**. **Scenario 11** (already receiving
> SNAP) is filtered out by the generic `already_has` results-layer workflow when the household
> reports it (`screen.has_benefit("ks_snap")`), so it's verified by design rather than a raw PE value.
>
> **Categorical eligibility.** A household with reported SSI receipt (**Scenarios 8, 22**) or TANF
> cash receipt (**Scenario 18**) is categorically eligible — the income and asset tests are bypassed
> (7 U.S.C. § 2014(a); 7 CFR 273.2(j)(2)). Categorical eligibility keys off *reported* receipt, not a
> recalculated benefit amount (**Scenario 22**).
>
> **Disabled treatment.** A disabled household member on a qualifying disability program (e.g. SSDI)
> receives the elderly/disabled treatment — no gross-income test, the higher $4,500 asset limit, and
> the uncapped excess-shelter deduction (**Scenario 17**). This applies the elderly/disabled *rules*;
> it does not categorically bypass the tests the way the SSI/TANF categorical path does.
>
> **Student exemptions.** A half-time+ college student aged 18–49 (**Scenario 9**) is an ineligible
> student unless they meet an exemption — a job-training / employment-and-training program placement
> (**Scenario 10**), working 20+ hours/week (**Scenario 19**), federal work-study (**Scenario 20**),
> or the parent-of-a-dependent-child exemption (**Scenario 21**) (7 CFR 273.5).

### Scenario 1: Single Adult Worker — Clearly Eligible for Food Assistance

**What we're checking**: Typical single adult with low wage income who clearly meets both the federal gross (130% FPL) and net (100% FPL) income tests (criteria 1–2).

**Expected**: Eligible — $864/yr ($72/mo)
**Benefit math** (FY2026): gross $1,200/mo earned; net = 1,200 − 209 std − 240 (20% earned) = $751; benefit = 298 max − 0.30 × 751 = **$72/mo**.

**Steps**:
- **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1992` (age 34), Relationship: Head of Household, Sex: Male, Not a student enrolled in higher education, Not pregnant, No disability, U.S. citizen
- **Income**: Employment income: `$1,200` per month, No other income sources
- **Current Benefits**: Not currently receiving SNAP/Food Assistance, Not receiving TANF, Not receiving SSI
- **Assets**: No significant countable assets

**Why this matters**: The most common Food Assistance applicant profile — a single working adult with modest earnings. Validates that the screener correctly identifies a clearly eligible household passing both the 130% FPL gross test and the 100% FPL net test, with no complicating factors.

---

### Scenario 2: Family of Four — Income Just Under 130% FPL Gross and 100% FPL Net

**What we're checking**: A household that barely meets both the gross (130% FPL) and net (100% FPL) income tests, validating edge-case eligibility at the income ceiling with shelter and dependent-care deductions (criteria 1, 2, 4, 16).

**Expected**: Eligible — $6,432/yr ($536/mo)

**Steps**:
- **Location**: Enter ZIP code `66603`, Select county `Shawnee`
- **Household**: Number of people: `4`
- **Person 1**: Birth month/year: `January 1987` (age 39), Relationship: Head of Household, Sex: Male, Not a student, Not pregnant, No disability, U.S. citizen, Employment income: `$3,400` per month
- **Person 2**: Birth month/year: `January 1989` (age 37), Relationship: Spouse, Sex: Female, Not a student, Not pregnant, No disability, U.S. citizen, No income
- **Person 3**: Birth month/year: `January 2016` (age 10), Relationship: Child, Sex: Female, No income
- **Person 4**: Birth month/year: `January 2020` (age 6), Relationship: Child, Sex: Male, No income
- **Income**: Employment income (Person 1): `$3,400` per month (below the HH4 gross limit of $3,483)
- **Expenses**: Monthly rent: `$1,300`, Monthly dependent care: `$300`, Heating/cooling utilities
- **Current Benefits**: Not currently receiving SNAP/Food Assistance, Not receiving TANF, Not receiving SSI

**Why this matters**: Tests the boundary where a family's gross income is just under the 130% FPL limit and net income, after the standard deduction, earned-income deduction, and excess-shelter/SUA deductions, falls just under 100% FPL.

---

### Scenario 3: Single Parent (Household of 2) — Gross Income $1 Below 130% FPL

**What we're checking**: A 2-person household with gross monthly income $1 below the 130% FPL threshold ($2,292/mo for HH2) is correctly found eligible (criterion 1, boundary).

**Expected**: Eligible — $3,540/yr ($295/mo)

**Steps**:
- **Location**: Enter ZIP code `66102`, Select county `Wyandotte`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `January 1992` (age 34), Relationship: Head of Household, Sex: Female, Not a student, Not pregnant, No disability, U.S. citizen, Employment income: `$2,291` per month ($1 below the HH2 limit of $2,292)
- **Person 2**: Birth month/year: `January 2021` (age 5), Relationship: Child, Sex: Male, No income
- **Expenses**: Monthly rent: `$1,000`, Monthly child care: `$400`
- **Current Benefits**: Not currently receiving SNAP/Food Assistance, Not receiving TANF, Not receiving SSI

**Why this matters**: Validates the exact gross-income boundary at $1 below the federal 130% FPL limit for a household of 2 in Kansas.

---

### Scenario 4: Single Adult — Gross Income Above 130% FPL

**What we're checking**: A single-person household with gross income above the 130% FPL limit is correctly denied (criterion 1, gross cap).

**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1992` (age 34), Relationship: Head of Household, Sex: Male, Not a student, Not pregnant, No disability, U.S. citizen, Employment income: `$1,800` per month (above the HH1 limit of $1,696)
- **Current Benefits**: Not currently receiving SNAP/Food Assistance, Not receiving TANF, Not receiving SSI

**Why this matters**: Confirms the screener enforces the federal 130% FPL gross cap for Kansas — there is no BBCE 200% allowance as in Washington.

---

### Scenario 5: Net Income Test Failure — Gross Passes, Net Fails

**What we're checking**: A household whose gross income is below the 130% FPL limit but whose net income exceeds the 100% FPL limit is denied — the KS-distinctive net income test that Washington (BBCE) waives (criterion 2).

**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `66603`, Select county `Shawnee`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1986` (age 40), Relationship: Head of Household, Sex: Male, Not a student, Not pregnant, No disability, U.S. citizen
- **Income**: Unemployment income: `$1,650` per month (unearned; below the gross limit of $1,696, but with only the $209 standard deduction and no earned-income or shelter deductions, net ≈ $1,441, above the net limit of $1,305)
- **Expenses**: No shelter or dependent-care expenses
- **Current Benefits**: Not currently receiving SNAP/Food Assistance, Not receiving TANF, Not receiving SSI

**Why this matters**: The only scenario that flips to eligible if the net income test were accidentally waived (e.g., BBCE wrongly applied to Kansas). Directly validates that the 100% FPL net test is enforced.

---

### Scenario 6: Non-Elderly Household — Countable Assets Above $3,000

**What we're checking**: A non-elderly/non-disabled household that passes the income tests but holds countable assets above $3,000 is denied — the KS-distinctive asset test that Washington (BBCE) eliminates (criterion 3).

**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `66603`, Select county `Shawnee`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1986` (age 40), Relationship: Head of Household, Sex: Female, Not a student, Not pregnant, No disability, U.S. citizen, Employment income: `$1,000` per month (well under the income limits)
- **Assets**: `$5,000` in countable resources (above the $3,000 limit)
- **Current Benefits**: Not currently receiving SNAP/Food Assistance, Not receiving TANF, Not receiving SSI

**Why this matters**: Validates that the federal asset test is enforced for Kansas. This scenario flips to eligible if the asset test were wrongly waived.

---

### Scenario 7: Elderly Individual — Gross Above 130% FPL, Net Below 100% FPL, Assets ≤ $4,500

**What we're checking**: The federal elderly/disabled treatment — a 60+ household is exempt from the gross income test and qualifies on net income alone, using the higher $4,500 asset limit and an uncapped shelter deduction (criterion 6).

**Expected**: Eligible — $276/yr ($23/mo)

**Steps**:
- **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1959` (age 67), Relationship: Head of Household, Not a student, Not pregnant, Not disabled (using the age 60+ exemption)
- **Income**: Social Security retirement income: `$1,800` per month (above the HH1 gross limit of $1,696)
- **Expenses**: Monthly rent: `$1,000`, Heating/cooling utilities (uncapped shelter deduction for elderly)
- **Assets**: `$1,000` (below the $4,500 elderly/disabled limit)
- **Current Benefits**: Not currently receiving SNAP/Food Assistance, Not receiving TANF, Not receiving SSI

**Why this matters**: Tests the path unique to elderly/disabled households — gross income exceeds 130% FPL, but the household still qualifies via the net income test, using the higher asset limit and uncapped shelter deduction.

---

### Scenario 8: Categorical Eligibility — All Members Receive SSI, Income and Assets Above Limits

**What we're checking**: A household in which all members receive SSI is categorically eligible — the income and asset tests are bypassed (criterion 5).

> ⏸️ **Deferred to MFB-1312.** SSI categorical eligibility requires `use_reported_ssi`, which is global per PE request (flips `applicable_ssi` for every program — SNAP, IL AABD, KS TANF, TX CEAP). That federal all-state change (verified IL AABD $0→$10k swing) is out of scope for this KS SNAP PR and is handled in MFB-1312. This scenario does not pass in the code shipping with this PR.

**Expected**: Eligible — $1,080/yr ($90/mo)

**Steps**:
- **Location**: Enter ZIP code `66102`, Select county `Wyandotte`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1981` (age 45), Relationship: Head of Household, Not a student, Not pregnant, Disabled, U.S. citizen
- **Income**: SSI income `$900`/month (reported SSI receipt)
- **Assets**: `$6,000` (above the $3,000 standard limit)
- **Current Benefits**: Currently receiving SSI, Not currently receiving SNAP/Food Assistance, Not receiving TANF

**Why this matters**: Validates that an all-SSI household is categorically eligible regardless of income or assets — reported SSI receipt drives categorical eligibility, which bypasses the asset/income tests.

---

### Scenario 9: Half-Time College Student Aged 18–49 — No Exemption

**What we're checking**: A college student enrolled at least half-time, aged 18–49, with no qualifying exemption is an ineligible student (criterion 7).

**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `66045`, Select county `Douglas`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 2006` (age 20), Relationship: Head of Household, Student status: enrolled in higher education at least half-time, Working: No, No work-study, No job-training program, No dependent child, No disability
- **Income**: No earned or unearned income, Total gross monthly income: `$0`
- **Current Benefits**: Not currently receiving SNAP/Food Assistance, Not receiving TANF, Not receiving SSI

**Why this matters**: Confirms the federal student restriction is applied — an unexempted half-time student aged 18–49 is ineligible even with $0 income.

---

### Scenario 10: Half-Time College Student with Job-Training Exemption

**What we're checking**: A half-time college student aged 18–49 who is enrolled in a workforce/job-training program (WIOA, SNAP E&T, career/technical ed) meets a student exemption under 7 CFR 273.5(b)(3) and is eligible (criterion 7).

**Expected**: Eligible — $864/yr ($72/mo)

**Steps**:
- **Location**: Enter ZIP code `66045`, Select county `Douglas`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 2004` (age 22), Relationship: Head of Household, Student status: enrolled in higher education at least half-time, Enrolled in a job-training program (`student_job_training_program` = Yes), Not working 20+ hrs, No disability
- **Income**: Employment income `$1,200`/month
- **Current Benefits**: Not currently receiving SNAP/Food Assistance, Not receiving TANF, Not receiving SSI

**Why this matters**: The job-training / employment-and-training program placement is one of the federal student exemptions (7 CFR 273.5(b)(3)). A half-time student who would otherwise be an ineligible student qualifies through it, so this household is eligible rather than denied at $0.

---

### Scenario 11: Already Receiving SNAP/Food Assistance — Duplicate Benefit Exclusion

**What we're checking**: A household already receiving Food Assistance is flagged ineligible, preventing duplicate enrollment (criterion 8).

**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `66102`, Select county `Wyandotte`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `January 1986` (age 40), Relationship: Head of Household, Sex: Female, Not a student, Not pregnant, No disability, U.S. citizen, Employment income: `$1,500` per month
- **Person 2**: Birth month/year: `January 2019` (age 7), Relationship: Child, Sex: Male, No income
- **Current Benefits**: Already receiving SNAP/Food Assistance (reported on the "already have" step → `screen.has_benefit("ks_snap")`)

**Why this matters**: Preventing duplicate enrollment is critical for program integrity.

---

### Scenario 12: Standard Utility Allowance — Single Adult, Moderate Income

**What we're checking**: A single adult below the maximum allotment with a binding excess-shelter deduction, so the KS Standard Utility Allowance ($469/mo HCSUA) flows through to the benefit. Committed expected benefit: **$2,424/yr ($202/mo)**.

**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1991` (age 35), Relationship: Head of Household, Not a student, Not pregnant, No disability, U.S. citizen
- **Income**: Employment income: `$1,500` per month ($18,000/year)
- **Expenses**: Monthly rent: `$700`, Heating/cooling utilities (qualifies for HCSUA $469/mo)
- **Current Benefits**: Not currently receiving SNAP/Food Assistance, Not receiving TANF, Not receiving SSI

**Why this matters**: Primary SUA validation. Reducing the KS HCSUA $469→$400 lowers this benefit by exactly $248/yr (0.30 × $69 × 12), proving the expected value isolates the SUA. PolicyEngine-verified on `policyengine-us` 1.739.4.

---

### Scenario 13: Standard Utility Allowance — Elderly Individual

**What we're checking**: An elderly household (uncapped shelter deduction) where the SUA is binding. Committed expected benefit: **$3,576/yr ($298/mo)**. The uncapped elderly shelter deduction (rent + HCSUA) drives net income to $0, so the household qualifies for the full HH1 max allotment ($298/mo). Note: $298 is the FY2026 HH1 maximum — the benefit cannot exceed it, which is why the prior $300/mo value was impossible.

**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `66603`, Select county `Shawnee`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1959` (age 67), Relationship: Head of Household, Not a student, Not pregnant, Not disabled (age 60+ exemption)
- **Income**: Social Security retirement income: `$14,000` per year (~$1,167/month)
- **Expenses**: Monthly rent: `$1,000`, Heating/cooling utilities (qualifies for HCSUA $469/mo)
- **Assets**: Below the $4,500 elderly/disabled limit
- **Current Benefits**: Not currently receiving SNAP/Food Assistance, Not receiving TANF, Not receiving SSI

**Why this matters**: SUA validation on the elderly/disabled path; the HCSUA feeds the uncapped elderly shelter deduction that zeroes net income. Verified against the live PolicyEngine API (the path benefits-api uses), version 1.715.2.

---

### Scenario 14: Standard Utility Allowance — Family of Three

**What we're checking**: A three-person working household below the maximum allotment with a binding shelter deduction. Committed expected benefit: **$4,668/yr ($389/mo)**.

**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `66102`, Select county `Wyandotte`
- **Household**: Number of people: `3`
- **Person 1**: Birth month/year: `January 1991` (age 35), Relationship: Head of Household, Not a student, No disability, U.S. citizen, Employment income: `$30,000` per year ($2,500/month)
- **Person 2**: Birth month/year: `January 1993` (age 33), Relationship: Spouse, No income, No disability, U.S. citizen
- **Person 3**: Birth month/year: `January 2021` (age 5), Relationship: Child, No income
- **Expenses**: Monthly rent: `$900`, Heating/cooling utilities (qualifies for HCSUA $469/mo)
- **Current Benefits**: Not currently receiving SNAP/Food Assistance, Not receiving TANF, Not receiving SSI

**Why this matters**: SUA validation at a larger household size; confirms the KS HCSUA flows through the excess-shelter deduction for a multi-person household.

---

### Scenario 15: Asset Test Pass — Below the Standard $3,000 Limit

**What we're checking**: A non-elderly/non-disabled household with low income and countable assets just **below** the $3,000 standard limit is eligible (criterion 3, the passing side of the asset test).

**Expected**: Eligible — $1,728/yr ($144/mo)

**Steps**:
- **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1992` (age 34), Relationship: Head of Household, Not a student, No disability, U.S. citizen
- **Income**: Employment income `$900`/month
- **Assets**: `$2,900` (just below the $3,000 standard limit)
- **Current Benefits**: Not currently receiving SNAP/Food Assistance, Not receiving TANF, Not receiving SSI

**Why this matters**: Scenario 6 tests the asset test failing at $5,000; this is the passing counterpart just under the limit — together they pin the $3,000 boundary for a non-categorical household.

---

### Scenario 16: Large Household of Five

**What we're checking**: A five-person household exercises the larger max allotment and the per-additional-person standards (criterion 4, household-size scaling).

**Expected**: Eligible — $7,212/yr ($601/mo)

**Steps**:
- **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
- **Household**: Number of people: `5`
- **Person 1**: Birth month/year: `January 1986` (age 40), Relationship: Head of Household, Employment income: `$3,500`/month
- **Person 2**: Birth month/year: `January 1988` (age 38), Relationship: Spouse, No income
- **Persons 3–5**: Children ages 12, 8, 5, No income
- **Expenses**: Monthly rent: `$1,400`, Heating/cooling utilities (HCSUA)
- **Current Benefits**: Not currently receiving SNAP/Food Assistance, Not receiving TANF, Not receiving SSI

**Why this matters**: Confirms benefit scaling for a larger household — the HH5 max allotment and standard deduction tier — beyond the HH1–4 cases above.

---

### Scenario 17: Disabled Non-Elderly — Uncapped Shelter & $4,500 Asset Limit

**What we're checking**: A non-elderly disabled SSDI recipient receives the federal disabled treatment: the **uncapped** excess-shelter deduction and the higher **$4,500** asset limit (criterion 6, the disabled path).

**Expected**: Eligible — $1,884/yr ($157/mo)

**Steps**:
- **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1981` (age 45), Relationship: Head of Household, **Disabled**, Not a student, U.S. citizen
- **Income**: Social Security disability (SSDI) `$1,500`/month
- **Expenses**: Monthly rent: `$1,000`, Heating/cooling utilities (HCSUA)
- **Assets**: `$1,000` (below the $4,500 disabled limit)
- **Current Benefits**: Not currently receiving SNAP/Food Assistance, Not receiving TANF, Not receiving SSI

**Why this matters**: The disabled treatment requires **receipt of a qualifying disability program** (e.g. SSDI), not the generic disability flag — a disabled SSDI recipient gets the uncapped excess-shelter deduction and the higher $4,500 asset limit. (A companion check: the same household with $4,000 in assets is eligible as disabled but would be **denied** if non-disabled, since $4,000 exceeds the $3,000 standard limit — confirming the higher disabled limit is applied.)

---

### Scenario 18: TANF Categorical Eligibility — Cash Recipient, Assets Above Limit

**What we're checking**: A household receiving TANF cash assistance should be categorically eligible for SNAP — the income and asset tests are bypassed (criterion 5, the TANF path).

**Expected**: Eligible — $2,880/yr ($240/mo)

**Steps**:
- **Location**: Enter ZIP code `66102`, Select county `Wyandotte`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1986` (age 40), Relationship: Head of Household, Not a student, No disability, U.S. citizen
- **Income**: Cash assistance (TANF) `$400`/month
- **Assets**: `$6,000` (above the $3,000 standard limit)
- **Current Benefits**: Currently receiving TANF cash assistance, Not currently receiving SNAP/Food Assistance, Not receiving SSI

**Why this matters**: TANF cash recipients are categorically eligible for SNAP under 7 U.S.C. § 2014(a); the income and asset tests are bypassed. This household is eligible despite $6,000 in assets (above the $3,000 standard limit), driven by the reported TANF cash amount. This is the TANF analog to the SSI categorical path in Scenario 8.

---

### Scenario 19: Half-Time College Student Working 20+ Hours/Week

**What we're checking**: A half-time college student aged 18–49 who works at least 20 hours per week meets a student exemption (7 CFR 273.5(b)(2)) and is eligible (criterion 7, work-hours exemption).

**Expected**: Eligible — $864/yr ($72/mo)

**Steps**:
- **Location**: Enter ZIP code `66045`, Select county `Douglas`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 2004` (age 22), Relationship: Head of Household, Student status: enrolled in higher education at least half-time, Working 20+ hrs/week, No work-study, No job-training program, No dependent child, No disability
- **Income**: Employment income `$1,200`/month
- **Current Benefits**: Not currently receiving SNAP/Food Assistance, Not receiving TANF, Not receiving SSI

**Why this matters**: The 20-hour work exemption is one of the federal student exemptions. A half-time student who would otherwise be an ineligible student qualifies through it, so this household is eligible rather than denied at $0.

---

### Scenario 20: Half-Time College Student with Federal Work-Study

**What we're checking**: A half-time college student aged 18–49 who participates in federal work-study meets a student exemption (7 CFR 273.5(b)(2)) and is eligible (criterion 7, work-study exemption).

**Expected**: Eligible — $864/yr ($72/mo)

**Steps**:
- **Location**: Enter ZIP code `66045`, Select county `Douglas`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 2004` (age 22), Relationship: Head of Household, Student status: enrolled in higher education at least half-time, Participates in federal work-study, Not working 20+ hrs, No job-training program, No dependent child, No disability
- **Income**: Employment income `$1,200`/month
- **Current Benefits**: Not currently receiving SNAP/Food Assistance, Not receiving TANF, Not receiving SSI

**Why this matters**: Work-study participation is one of the federal student exemptions. A half-time student who would otherwise be an ineligible student qualifies through it, so this household is eligible rather than denied at $0.

---

### Scenario 21: Single Full-Time Student Parent with a Dependent Child

**What we're checking**: A single parent enrolled full-time in higher education, responsible for a dependent child under 12, meets a student exemption (7 CFR 273.5(b)(4)) and is eligible (criterion 7, parent exemption).

**Expected**: Eligible — $3,840/yr ($320/mo)

**Steps**:
- **Location**: Enter ZIP code `66045`, Select county `Douglas`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `January 2000` (age 26), Relationship: Head of Household, Student status: enrolled in higher education full-time, Not married, No work-study, No job-training program, Not working 20+ hrs, No disability
- **Person 2**: Birth month/year: `January 2018` (age 8), Relationship: Child, No income
- **Income**: Employment income (Person 1) `$1,200`/month
- **Current Benefits**: Not currently receiving SNAP/Food Assistance, Not receiving TANF, Not receiving SSI

**Why this matters**: The parent exemption is one of the federal student exemptions — a single parent enrolled full-time with a dependent child under 12 (or, for a two-parent household, a child under 6) qualifies. Without it, the student parent would be excluded and the household under-served.

---

### Scenario 22: SSI Categorical Eligibility — Reported Receipt with High Other Income

**What we're checking**: A household reporting SSI receipt is categorically eligible even when other income is high enough that the modeled SSI amount would compute to $0. Categorical eligibility must key off *reported* receipt, not a recalculated SSI amount (criterion 5, the SSI path).

> ⏸️ **Deferred to MFB-1312.** Same reason as Scenario 8 — the reported-SSI categorical path depends on the global `use_reported_ssi` change tracked in MFB-1312. Not wired in this PR.

**Expected**: Eligible — $276/yr ($23/mo)

**Steps**:
- **Location**: Enter ZIP code `66102`, Select county `Wyandotte`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1981` (age 45), Relationship: Head of Household, Disabled, Not a student, U.S. citizen
- **Income**: SSI income `$900`/month (reported SSI receipt), Pension `$2,000`/month
- **Assets**: `$6,000` (above the $3,000 standard limit)
- **Current Benefits**: Currently receiving SSI, Not currently receiving SNAP/Food Assistance, Not receiving TANF

**Why this matters**: With $24,000/yr of pension income, a from-scratch SSI computation would return $0 (over the SSI income limit) — which would wrongly deny categorical eligibility. Because the household's *reported* SSI receipt drives the categorical check, it stays eligible. This scenario fails if categorical eligibility ever reverts to using the modeled SSI amount instead of reported receipt.


## PE Verification

KS uses the federal SNAP calculator (`KsSnap(Snap)`) with no eligibility variance; the KS SUA values ($469/$345/$44, eff. 2025-10-01) and all FY2026 standards (max allotment, deductions, shelter cap, asset/income limits) match KEESM/FNS in PolicyEngine.

Previously triaged and cleared for MFB — #8296 (COFA) and OBBBA non-citizen narrowing bypassed via the `CITIZEN` default; #7745 (OBBBA HCSUA restriction) doesn't affect MFB (actual-expense pathway); the 3-month ABAWD time-limit clock is an architectural PE limitation.


## Research Sources

- [KS DCF Food Assistance (SNAP)](https://www.dcf.ks.gov/services/ees/pages/food/foodassistance.aspx)
- [KS DCF Food Assistance FAQ](https://www.dcf.ks.gov/services/ees/Pages/Food/FoodAssistanceFAQs.aspx)
- [KEESM Appendix F-2 — Food Assistance Program Standards (eff. 10/1/2025)](https://content.dcf.ks.gov/EES/KEESM/Appendix/F-2%20FA%20Program%20Standards.pdf)
- [KEESM Section 2510 — Categorical Eligibility](https://content.dcf.ks.gov/ees/KEESM/current/keesm2510.htm)
- [KEESM Student Eligibility Criteria for Food Assistance](https://content.dcf.ks.gov/ees/keeswebhelp/nonmedical-keeswebhelp/Student_Eligibility_Criteria_for_Food_Assistance.htm)
- [FNS SNAP Recipient Eligibility](https://www.fns.usda.gov/snap/recipient/eligibility)
- [FNS BBCE State Chart](https://www.fns.usda.gov/snap/broad-based-categorical-eligibility) (KS not listed)
- [FNS FY2026 COLA](https://www.fns.usda.gov/snap/allotment/cola/fy26)
- [FNS ABAWD Waivers FY2025–2029](https://www.fns.usda.gov/snap/abawd/waivers/2025-2029) (KS not waived)
- [Public Health Law Center — KS Drug Felony](https://www.publichealthlawcenter.org/resources/snap-ban-opt-out-states-map/ks)
- [Legal Information Institute — 7 U.S.C. § 2014](https://www.law.cornell.edu/uscode/text/7/2014)


## JSON Test Cases

File: `validations/management/commands/import_validations/data/ks_snap.json`

Scenarios 1–14. Expected `eligible`:
- `true`: 1, 2, 3, 7, 8, 10, 12, 13, 14
- `false`: 4, 5, 6, 9, 11

SUA value scenarios 12–14 carry committed amounts ($2,424 / $3,576 / $4,668 per year), each hand-derived from the FY2026 formula and confirmed against the calculator.


## Generated Program Configuration

File: `programs/management/commands/import_program_config_data/data/ks_snap_initial_config.json` (PR #1586). Config carries no `warning_message`, 7 required documents, and 2 navigators (Mirror Inc., Harvesters).

Two config updates this spec recommends:
- **`legal_status_required`** → `citizen`, `gc_5plus`, `gc_5less` (drop `refugee`, `non_citizen`, `otherWithWorkPermission` — no longer SNAP-eligible post-OBBBA; see the dev thread on the ticket).
- **Program description** → add a child-support-cooperation line (criterion 13). Suggested: append to the eligibility paragraph — *"Single parents may need to cooperate with child support services to get benefits. Some exceptions apply, such as for safety reasons."*


## Version note

Expected values for scenarios 12–14 were computed on `policyengine-us` 1.739.4. MFB serves SNAP via the hosted PolicyEngine API at the version in `PolicyEngineConfig` (defaults to blank → PE "current," which as of June 2026 carries the FY2026 KS SUA). If the config is pinned to a release predating the FY2026 SUA load, re-run scenarios 12–14 on that version before locking.


## Changelog

| Date | Author | Change |
|---|---|---|
| 2026-06-21 | Discovery (KS) | Initial KS spec adapted from `wa/snap/spec.md`; replaced WA BBCE criteria with standard federal tests (130% gross, 100% net, $3,000/$4,500 asset limit); KS SUA = $469; SUA-isolating value scenarios with PolicyEngine-verified amounts. |
| 2026-06-21 | Discovery QA | Removed administrative/process items (SSN, identity/interview, IPV) from eligibility criteria; reordered with priority/screenable criteria first; added a handling suggestion (inclusivity assumption or program-description surfacing) to every data gap; verified FY2026 asset limit ($3,000/$4,500); expanded scenarios to cover net-test failure, asset test, categorical (SSI) eligibility, and student exemption (14 total). |
| 2026-06-21 | Discovery QA | Citation fidelity pass — verified every spec citation against live primary sources. Two fixes: criterion 14 (drug felony) `7 U.S.C. § 2015(k)` → `21 U.S.C. § 862a` (2015 covers benefit-trafficking, not the felony ban); criterion 15 (fleeing felon) dropped the unverifiable `7 U.S.C. § 2015(k)`, kept `7 CFR 273.11(n)`. Confirmed `7 CFR 273.11(o)-(p)` is correct for child-support cooperation. All other CFR/USC/KEESM cites verified. |
| 2026-06-21 | Discovery QA | Ran all eligibility scenarios through PolicyEngine (1.739.4): scenarios 1–10 confirm their eligible/ineligible outcomes, 12–14 confirm committed SUA amounts; scenario 11 (duplicate-benefit) is handled by the `already_has` results-layer workflow (`has_benefit("ks_snap")`), verified by design. Student scenarios are handled by the federal calculator's `is_snap_ineligible_student` dependency, computed from screener fields and passed to PE as an input. |
| 2026-06-21 | Discovery QA | Added missing criteria: **child support cooperation** (criterion 13 — KS-specific state option mandated under the HOPE Act, verified via Kansas Action for Children / KEESM) and a distinct **general work requirement / work registrant 18–59** (criterion 11, KS HOPE Act 30-hr + mandatory E&T), split from the ABAWD time-limit criterion (12); folded the standalone voluntary-quit item into the general work requirement. Reformatted all test scenarios to match the `wa/snap/spec.md` structure. |
