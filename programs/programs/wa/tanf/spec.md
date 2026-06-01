# Temporary Assistance for Needy Families (TANF) — Implementation Spec

**Program:** `wa_tanf`
**State:** Washington
**White Label:** `wa`
**Research Date:** 2026-05-12
**Post-Production Revision:** 2026-05-21 (per QA findings on MFB-749 — updated to match PolicyEngine parameters and 2024 statutory changes from HB 1447)

> ⚠️ **Income methodology note:** Washington TANF applies an earned-income disregard of a **$500 flat work-related deduction, then 50% of remaining earned income disregarded** (WAC 388-450-0170, RCW 74.08A.230, effective 2024-08-01 per HB 1447). The calculator implements this in full. Countable income = max((gross_earned_income − $500) × 0.5, 0). This replaces the older $90 federal-style disregard. See Criterion 2 for details.

> ⚠️ **Household size > 5 note:** WAC 388-478-0020 documents payment standards for household sizes 1–5. For households of 6+, the calculator uses an extrapolation rule ($959 + $126 × (household_size − 5)) — based on the documented HH 4 → HH 5 increment. This favors inclusion (false positives over false negatives) and is explicitly marked as an extrapolation beyond the cited WAC. See Criterion 2 and Benefit Value for details.

---

## Eligibility Criteria

1. **Household must include a dependent child under age 19, OR the applicant must be pregnant**
   - Screener fields: `household_members` (age, relationship), `pregnant`
   - Note: The full WA TANF rule requires a dependent child under age 18, OR age 18 if expected to complete high school before turning 19. The screener has no field for "expected to complete high school." Per the false-positive-over-false-negative preference, the spec treats **all individuals under age 19** as potentially qualifying dependents.
   - Source: [Washington DSHS TANF Program Overview](https://www.dshs.wa.gov/esa/community-services-offices/temporary-assistance-needy-families); RCW 74.04.005; WAC 388-400-0005

2. **Household income must be at or below the TANF/SFA payment standard for household size (after applying earned-income disregards)**
   - Screener fields: `income_streams`, `household_size`
   - Note: The calculator applies the WA earned-income disregard: $500 flat work-related deduction, then 50% of the remaining earned income disregarded. Countable income = max((gross_earned_income − $500) × 0.5, 0). Eligibility is determined by comparing countable income to the payment standard for the household size.
   - WA TANF/SFA payment standards (WAC 388-478-0020, effective 2024-01-01): 1-person: $450/mo | 2-person: $570/mo | 3-person: $706/mo | 4-person: $833/mo | 5-person: $959/mo.
   - **For household sizes 6+ (extrapolation rule — not in the cited WAC):** payment standard = $959 + $126 × (household_size − 5). The $126 increment matches the documented HH 4 → HH 5 increment. This is explicitly an extrapolation beyond the WAC source, intended to keep the calculator from breaking for larger households and to favor false positives. Dev note: revisit if WA publishes standards for HH 6+.
   - Source: [WAC 388-478-0020](https://app.leg.wa.gov/WAC/default.aspx?cite=388-478-0020); WAC 388-450-0170; RCW 74.08A.230; HB 1447 (2023 c 418)

3. **Household must reside in Washington State**
   - Screener fields: `zipcode`, `county`
   - ⚠️ **Known platform limitation:** The PolicyEngine-based calculator infrastructure hardcodes `state = "WA"` for all screens submitted under the `wa` white label (via `WaStateCodeDependency`). The ZIP code is not validated against WA state boundaries at the calculator level. In practice, users access the WA screener via a WA-specific URL, so out-of-state ZIPs are an edge case. This applies to all PE-based state programs across all states — it is a platform design decision, not a wa_tanf-specific bug. See Scenario 16.
   - Source: [Washington DSHS TANF Program Overview](https://www.dshs.wa.gov/esa/community-services-offices/temporary-assistance-needy-families); RCW 74.04.005

4. **Household resources/assets must not exceed $12,000**
   - Screener fields: `household_assets`
   - Note: The $12,000 limit applies to countable resources. This limit was raised from $6,000 to $12,000 by HB 1447 (2023 c 418, Sec 1), codified at RCW 74.04.005(13), effective 2024-02-01. Certain assets are excluded (primary vehicle up to a value, household goods, burial funds up to $1,500). The screener captures a single `household_assets` figure as an approximation. Assets exactly at $12,000 are eligible (≤ comparison).
   - Source: [RCW 74.04.005(13)](https://app.leg.wa.gov/RCW/default.aspx?cite=74.04.005); [WAC 388-470-0005](https://app.leg.wa.gov/WAC/default.aspx?cite=388-470-0005); WAC 388-470-0045; HB 1447 (2023 c 418, Sec 1)

5. **Citizenship/immigration status** ⚠️ *data gap* — Federal TANF requires U.S. citizenship or qualified alien status; 5-year bar may apply for some qualified aliens. Washington SFA provides state-funded assistance for some immigrants who don't qualify federally. The screener has no citizenship/immigration field. `legal_status_required` is set to `["citizen", "gc_5plus", "gc_5less", "refugee", "otherWithWorkPermission"]` to reflect both federal TANF and WA SFA pathways and to favor false positives over false negatives. Source: 8 U.S.C. § 1612; WAC 388-424-0010

6. **SSI receipt per member** ⚠️ *data gap* — SSI recipients are excluded from the TANF assistance unit. The screener has `has_ssi` at household level but not per-member. Source: WAC 388-450-0162

7. **60-month lifetime time limit** ⚠️ *data gap* — TANF has a 60-month federal lifetime limit on cash assistance. The screener does not track benefit history. Inclusivity assumption: we assume households have months remaining and rely on DSHS to enforce the limit at application. Source: WAC 388-484-0005; 42 U.S.C. § 608(a)(7)

8. **Work participation (WorkFirst)** ⚠️ *data gap* — Non-exempt adults must participate in WorkFirst activities. Exemptions exist for disabled individuals, caregivers of children under 1, pregnant women (third trimester), domestic violence victims, and adults over 60. The screener partially captures some exemption categories but cannot fully determine work-requirement compliance. Treated as a post-enrollment compliance issue. Source: RCW 74.08A.100; Chapter 388-310 WAC

---

## Benefit Value

TANF benefit amounts are based on household size per WAC 388-478-0020, with countable income subtracted from the payment standard. Monthly payment standards (effective 2024-01-01):

| Household size | Monthly payment standard | Source |
|---|---|---|
| 1 | $450 | WAC 388-478-0020 |
| 2 | $570 | WAC 388-478-0020 |
| 3 | $706 | WAC 388-478-0020 |
| 4 | $833 | WAC 388-478-0020 |
| 5 | $959 | WAC 388-478-0020 |
| 6+ | $959 + $126 × (size − 5) | Extrapolation (not in cited WAC) |

**Calculator methodology:** Monthly benefit = max(payment_standard − countable_income, 0), where countable_income = max((gross_earned_income − $500) × 0.5, 0). Annual `estimated_value` returned by the API is monthly_benefit × 12. `value_format` is `null` (monthly). `estimated_value` in the config is `""` (blank — defers to calculator).

Source: [WAC 388-478-0020](https://app.leg.wa.gov/WAC/default.aspx?cite=388-478-0020); WAC 388-450-0170 (earned-income disregard)

---

## Test Scenarios

> 📝 **Post-production note (MFB-749, 2026-05-21):** Scenarios updated to reflect WA's current statutory parameters (WAC 388-478-0020 payment standards, $500 + 50% disregard, $12,000 asset limit per HB 1447). Each "What we're checking" includes both gross income and computed countable income for clarity. All eligible scenarios' values have been recalculated to match the PolicyEngine calculator's `max(payment_standard − countable_income, 0)` formula.

---

### Scenario 1: Clearly Eligible Single Parent with Two Young Children

**What we're checking**: Golden-path eligible case — single parent, two young children, WA resident, low assets. Gross income $800/month for household of 3. Countable income = ($800 − $500) × 0.5 = $150 ≤ payment standard $706 → Eligible. Benefit = $706 − $150 = $556/month.

**Expected**: Eligible, value: `556` (monthly) / `6672` (annual)

**Steps**:

* **Location**: Enter ZIP code `98101`, Select county `King County`
* **Household**: Number of people: `3`
* **Person 1 (Head)**: Birth month/year: `June 1996` (age 29), Employment income: `$800/month`
* **Person 2 (Child)**: Birth month/year: `April 2019` (age 7), No income
* **Person 3 (Child)**: Birth month/year: `July 2022` (age 3), No income
* **Assets**: `$1,500`

---

### Scenario 2: Minimally Eligible — Single Parent with One Child at Boundary Conditions

**What we're checking**: Boundary conditions — child just under 18 (will turn 18 in mid-2026) and income at $521/month for household of 2. Countable income = ($521 − $500) × 0.5 = $10.50 ≤ payment standard $570 → Eligible. Benefit = $570 − $10.50 = $559.50/month.

**Expected**: Eligible, value: `559.50` (monthly) / `6714` (annual)

**Steps**:

* **Location**: Enter ZIP code `98109`, Select county `King County`
* **Household**: Number of people: `2`
* **Person 1 (Head)**: Birth month/year: `March 1990` (age 36), Employment income: `$521/month`
* **Person 2 (Child)**: Birth month/year: `June 2008` (age 17), No income
* **Assets**: `$6,000`

---

### Scenario 3: Single Parent with Three Children — Income Just Below 4-Person Threshold

**What we're checking**: Gross income $720/month for household of 4. Countable income = ($720 − $500) × 0.5 = $110 ≤ payment standard $833 → Eligible. Benefit = $833 − $110 = $723/month.

**Expected**: Eligible, value: `723` (monthly) / `8676` (annual)

**Steps**:

* **Location**: Enter ZIP code `98112`, Select county `King County`
* **Household**: Number of people: `4`
* **Person 1 (Head)**: Birth month/year: `April 1992` (age 34), Employment income: `$720/month`
* **Person 2 (Child)**: Birth month/year: `June 2014` (age 11), No income
* **Person 3 (Child)**: Birth month/year: `August 2017` (age 8), No income
* **Person 4 (Child)**: Birth month/year: `March 2021` (age 5), No income
* **Assets**: `$2,000`

---

### Scenario 4: Single Parent with One Child — Income at Old 2-Person Threshold

**What we're checking**: Gross income $440/month for household of 2. Countable income = max(($440 − $500) × 0.5, 0) = $0 ≤ payment standard $570 → Eligible. Benefit = $570 − $0 = $570/month. Tests that the disregard floor at zero is respected.

**Expected**: Eligible, value: `570` (monthly) / `6840` (annual)

**Steps**:

* **Location**: Enter ZIP code `98103`, Select county `King County`
* **Household**: Number of people: `2`
* **Person 1 (Head)**: Birth month/year: `October 1995` (age 30), Employment income: `$440/month`
* **Person 2 (Child)**: Birth month/year: `February 2020` (age 6), No income
* **Assets**: `$1,500`

---

### Scenario 5: Single Parent with Two Children — Income Above Gross Threshold but Eligible After Disregards

**What we're checking**: Reframed post-MFB-749. Gross income $700/month for household of 3 (slightly above the 3-person payment standard of $706 in gross terms, but the calculator applies disregards before comparison). Countable income = ($700 − $500) × 0.5 = $100 ≤ payment standard $706 → Eligible. Benefit = $706 − $100 = $606/month. This scenario tests that the disregards are correctly applied.

**Expected**: Eligible, value: `606` (monthly) / `7272` (annual)

**Steps**:

* **Location**: Enter ZIP code `98115`, Select county `King County`
* **Household**: Number of people: `3`
* **Person 1 (Head)**: Birth month/year: `July 1993` (age 32), Employment income: `$700/month`
* **Person 2 (Child)**: Birth month/year: `March 2018` (age 8), No income
* **Person 3 (Child)**: Birth month/year: `November 2021` (age 4), No income
* **Assets**: `$2,000`

---

### Scenario 6: Newborn Child (Age 0) — Minimum Age for Dependent Child

**What we're checking**: A newborn (age 0) satisfies the dependent-child requirement. Tests the lower age boundary. Gross income $500/month for household of 2. Countable income = max(($500 − $500) × 0.5, 0) = $0 ≤ payment standard $570 → Eligible. Benefit = $570/month.

**Expected**: Eligible, value: `570` (monthly) / `6840` (annual)

**Steps**:

* **Location**: Enter ZIP code `98105`, Select county `King County`
* **Household**: Number of people: `2`
* **Person 1 (Head)**: Birth month/year: `November 1994` (age 31), Employment income: `$500/month`
* **Person 2 (Child)**: Birth month/year: `January 2026` (age 0), No income
* **Assets**: `$1,000`

---

### Scenario 7: 18-Year-Old Child, Income Above 2-Person Payment Standard — Ineligible

**What we're checking**: Household of 2 with an 18-year-old as the only child and gross earned income of $800/month. Expected to fail the eligibility check.

**Expected**: Ineligible

**Steps**:

* **Location**: Enter ZIP code `98117`, Select county `King County`
* **Household**: Number of people: `2`
* **Person 1 (Head)**: Birth month/year: `May 1985` (age 41), Employment income: `$800/month`
* **Person 2 (Child)**: Birth month/year: `April 2008` (age 18), No income
* **Assets**: `$1,000`

---

### Scenario 8: Parent with 9-Year-Old Child — Clearly Within Age Range, No Income

**What we're checking**: A 9-year-old (well within the dependent-child age range) and a parent with no earned income. Countable income = $0 ≤ payment standard $570 → Eligible. Benefit = $570/month.

**Expected**: Eligible, value: `570` (monthly) / `6840` (annual)

**Steps**:

* **Location**: Enter ZIP code `98122`, Select county `King County`
* **Household**: Number of people: `2`
* **Person 1 (Head)**: Birth month/year: `August 1990` (age 35), No income
* **Person 2 (Child)**: Birth month/year: `July 2016` (age 9), No income
* **Assets**: `$500`

---

### Scenario 9: Valid WA ZIP Code (Spokane) — Eastern WA Residency Confirmed

**What we're checking**: A Spokane ZIP code (99201) satisfies WA state residency. Confirms the screener accepts eastern WA ZIPs. Gross income $500/month for household of 2. Countable income = $0 ≤ payment standard $570 → Eligible. Benefit = $570/month.

**Expected**: Eligible, value: `570` (monthly) / `6840` (annual)

**Steps**:

* **Location**: Enter ZIP code `99201`, Select county `Spokane County`
* **Household**: Number of people: `2`
* **Person 1 (Head)**: Birth month/year: `November 1994` (age 31), Employment income: `$500/month`
* **Person 2 (Child)**: Birth month/year: `March 2022` (age 4), No income
* **Assets**: `$1,500`

---

### Scenario 10: Mixed Household — Adult Non-Dependent Plus Two Young Children

**What we're checking**: A 21-year-old adult child does not count as a qualifying dependent, but the two younger children (ages 7 and 3) do. Spouse earns $800/month; household of 5 → payment standard $959/month. Countable income = ($800 − $500) × 0.5 = $150. Benefit = $959 − $150 = $809/month.

**Expected**: Eligible, value: `809` (monthly) / `9708` (annual)

**Steps**:

* **Location**: Enter ZIP code `98201`, Select county `Snohomish County`
* **Household**: Number of people: `5`
* **Person 1 (Head)**: Birth month/year: `February 1986` (age 40), No income
* **Person 2 (Spouse)**: Birth month/year: `September 1987` (age 38), Employment income: `$800/month`
* **Person 3 (Adult Child)**: Birth month/year: `March 2005` (age 21), No income
* **Person 4 (Child)**: Birth month/year: `June 2018` (age 7), No income
* **Person 5 (Child)**: Birth month/year: `April 2023` (age 3), No income
* **Assets**: `$2,500`

---

### Scenario 11: Two-Parent Household with Three Children of Varying Ages

**What we're checking**: All three children (ages 14, 8, and 1) qualify as dependents. Household of 5 → payment standard $959/month. Countable income = ($800 − $500) × 0.5 = $150. Benefit = $959 − $150 = $809/month.

**Expected**: Eligible, value: `809` (monthly) / `9708` (annual)

**Steps**:

* **Location**: Enter ZIP code `98226`, Select county `Whatcom County`
* **Household**: Number of people: `5`
* **Person 1 (Head)**: Birth month/year: `January 1985` (age 41), No income
* **Person 2 (Spouse)**: Birth month/year: `October 1986` (age 39), Employment income: `$800/month`
* **Person 3 (Child)**: Birth month/year: `September 2011` (age 14), No income
* **Person 4 (Child)**: Birth month/year: `October 2017` (age 8), No income
* **Person 5 (Child)**: Birth month/year: `February 2025` (age 1), No income
* **Assets**: `$2,500`

---

### Scenario 12: Assets at Old $6,000 Limit — Still Well Under Current $12,000 Limit

**What we're checking**: Assets at $6,000 are well below the current $12,000 limit (raised by HB 1447). Income $300/month for household of 2. Countable income = $0 ≤ payment standard $570 → Eligible. Benefit = $570/month.

**Expected**: Eligible, value: `570` (monthly) / `6840` (annual)

**Steps**:

* **Location**: Enter ZIP code `98444`, Select county `Pierce County`
* **Household**: Number of people: `2`
* **Person 1 (Head)**: Birth month/year: `December 1996` (age 29), Employment income: `$300/month`
* **Person 2 (Child)**: Birth month/year: `April 2022` (age 4), No income
* **Assets**: `$6,000`

---

### Scenario 13: Pregnant Applicant, No Children — Eligible via Pregnancy Branch

**What we're checking**: Criterion 1's pregnancy branch. A pregnant applicant with no children in the household should be eligible. Household of 1 → payment standard $450/month. Countable income = $0 ≤ $450 → Eligible. Benefit = $450/month.

**Expected**: Eligible, value: `450` (monthly) / `5400` (annual)

**Steps**:

* **Location**: Enter ZIP code `98101`, Select county `King County`
* **Household**: Number of people: `1`
* **Person 1 (Head)**: Birth month/year: `July 1998` (age 27), Employment income: `$200/month`, **Pregnant: yes**
* **Assets**: `$500`

---

### Scenario 14: Income Well Above Payment Standard — Clearly Ineligible

**What we're checking**: Clear income ineligibility. Gross income $2,000/month for a household of 3. Countable income = ($2,000 − $500) × 0.5 = $750 > payment standard $706 → Ineligible.

**Expected**: Ineligible

**Steps**:

* **Location**: Enter ZIP code `98103`, Select county `King County`
* **Household**: Number of people: `3`
* **Person 1 (Head)**: Birth month/year: `May 1990` (age 36), Employment income: `$2,000/month`
* **Person 2 (Spouse)**: Birth month/year: `October 1992` (age 33), No income
* **Person 3 (Child)**: Birth month/year: `April 2021` (age 5), No income
* **Assets**: `$1,000`

---

### Scenario 15: Assets Above $12,000 Limit — Ineligible on Resources

**What we're checking**: Asset exclusion using the current $12,000 limit (raised from $6,000 by HB 1447, effective 2024-02-01). Assets of $15,000 exceed the $12,000 limit; household is otherwise eligible. Updated post-MFB-749 from prior $7,500 asset value, which was under the current limit.

**Expected**: Ineligible

**Steps**:

* **Location**: Enter ZIP code `98033`, Select county `King County`
* **Household**: Number of people: `2`
* **Person 1 (Head)**: Birth month/year: `March 1991` (age 35), Employment income: `$200/month`
* **Person 2 (Child)**: Birth month/year: `June 2022` (age 3), No income
* **Assets**: `$15,000`

---

### Scenario 16: Out-of-State ZIP Code — Known Platform Limitation

**What we're checking**: Residency exclusion via ZIP. ⚠️ **Known platform limitation (MFB-749):** the PolicyEngine-based calculator infrastructure hardcodes `state = "WA"` for all screens submitted under the `wa` white label, so ZIP-based state validation does not occur at the calculator level. This scenario will return Eligible even with an Oregon ZIP code. The scenario is retained for documentation purposes; in practice, users access the WA screener via a WA-specific URL. This is not a wa_tanf-specific bug — it applies to all PE-based state programs across all states.

**Expected**: Eligible (per known platform behavior — *spec-intent would be Ineligible if ZIP validation were enforced*)

**Steps**:

* **Location**: Enter ZIP code `97201`, Select county `Multnomah County` (Oregon — outside WA)
* **Household**: Number of people: `2`
* **Person 1 (Head)**: Birth month/year: `November 1994` (age 31), Employment income: `$300/month`
* **Person 2 (Child)**: Birth month/year: `April 2022` (age 4), No income
* **Assets**: `$1,000`
