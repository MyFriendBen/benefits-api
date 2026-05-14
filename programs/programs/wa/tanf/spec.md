# Temporary Assistance for Needy Families (TANF) — Implementation Spec

**Program:** `wa_tanf`
**State:** Washington
**White Label:** `wa`
**Research Date:** 2026-05-12

> ⚠️ **Income methodology note:** Washington TANF applies earned income disregards ($90 work-related expense deduction, then 50% of remaining earned income disregarded). The screener cannot apply these disregards precisely and compares **gross income directly to the TANF payment standard** as an approximation. This overstates countable income — some households flagged as ineligible by the screener may actually qualify. This is documented as a known limitation. See Criterion 2 and the Data Gaps section for details.

> ⚠️ **Household size > 5 note:** WAC 388-478-0035 only documents payment standards for household sizes 1–5. For households of 6+, the calculator uses an extrapolation rule ($826 + $105 × (household_size − 5)). This favors inclusion (false positives over false negatives) and is explicitly marked as an extrapolation beyond the cited WAC. See Criterion 2 and Benefit Value for details.

---

## Eligibility Criteria

1. **Household must include a dependent child under age 19, OR the applicant must be pregnant**
   - Screener fields: `household_members` (age, relationship), `pregnant`
   - Note: The full WA TANF rule requires a dependent child under age 18, OR age 18 if expected to complete high school before turning 19. The screener has no field for "expected to complete high school." Per the false-positive-over-false-negative preference, the screener treats **all individuals under age 19** as potentially qualifying dependents.
   - Source: [Washington DSHS TANF Program Overview](https://www.dshs.wa.gov/esa/community-services-offices/temporary-assistance-needy-families); RCW 74.04.005; WAC 388-400-0005

2. **Household income must be at or below the TANF/SFA payment standard for household size (using gross income as screener approximation)**
   - Screener fields: `income_streams`, `household_size`
   - Note: The screener compares **gross earned income directly to the payment standard** as an approximation. The true TANF methodology applies earned income disregards ($90 work-related deduction, then 50% of remaining earned income disregarded). Using gross income overstates countable income and will screen out some technically eligible households. Devs should add a comment in the calculator noting that gross income is used as an approximation and the actual eligibility threshold is higher when disregards are applied.
   - WA TANF/SFA payment standards (WAC 388-478-0035): 1-person: $339/mo | 2-person: $440/mo | 3-person: $654/mo | 4-person: $721/mo | 5-person: $826/mo.
   - **For household sizes 6+ (extrapolation rule — not in the cited WAC):** payment standard = $826 + $105 × (household_size − 5). The $105 increment matches the documented HH 4 → HH 5 increment. This is explicitly an extrapolation beyond the WAC source, intended to keep the calculator from breaking for larger households and to favor false positives. Dev note: revisit if WA publishes standards for HH 6+.
   - Source: [WAC 388-478-0035](https://app.leg.wa.gov/WAC/default.aspx?cite=388-478-0035); WAC 388-450-0156; WAC 388-450-0170

3. **Household must reside in Washington State**
   - Screener fields: `zipcode`, `county`
   - Source: [Washington DSHS TANF Program Overview](https://www.dshs.wa.gov/esa/community-services-offices/temporary-assistance-needy-families); RCW 74.04.005

4. **Household resources/assets must not exceed $6,000**
   - Screener fields: `household_assets`
   - Note: The $6,000 limit applies to countable resources. Certain assets are excluded (primary vehicle up to a value, household goods, burial funds up to $1,500). The screener captures a single `household_assets` figure as an approximation. Assets exactly at $6,000 are eligible (≤ comparison).
   - Source: [WAC 388-470-0005](https://app.leg.wa.gov/WAC/default.aspx?cite=388-470-0005); WAC 388-470-0045

5. **Citizenship/immigration status** ⚠️ *data gap* — Federal TANF requires U.S. citizenship or qualified alien status; 5-year bar may apply for some qualified aliens. Washington SFA provides state-funded assistance for some immigrants who don't qualify federally. The screener has no citizenship/immigration field. `legal_status_required` is set to `["citizen", "gc_5plus", "gc_5less", "refugee", "otherWithWorkPermission"]` to reflect both federal TANF and WA SFA pathways and to favor false positives over false negatives. Source: 8 U.S.C. § 1612; WAC 388-424-0010

6. **SSI receipt per member** ⚠️ *data gap* — SSI recipients are excluded from the TANF assistance unit. The screener has `has_ssi` at household level but not per-member. Source: WAC 388-450-0162

7. **60-month lifetime time limit** ⚠️ *data gap* — TANF has a 60-month federal lifetime limit on cash assistance. The screener does not track benefit history. Inclusivity assumption: we assume households have months remaining and rely on DSHS to enforce the limit at application. Source: WAC 388-484-0005; 42 U.S.C. § 608(a)(7)

8. **Work participation (WorkFirst)** ⚠️ *data gap* — Non-exempt adults must participate in WorkFirst activities. Exemptions exist for disabled individuals, caregivers of children under 1, pregnant women (third trimester), domestic violence victims, and adults over 60. The screener partially captures some exemption categories but cannot fully determine work-requirement compliance. Treated as a post-enrollment compliance issue. Source: RCW 74.08A.100; Chapter 388-310 WAC

---

## Benefit Value

TANF benefit amounts are based on household size per WAC 388-478-0035. Monthly payment standards:

| Household size | Monthly payment standard | Source |
|---|---|---|
| 1 | $339 | WAC 388-478-0035 |
| 2 | $440 | WAC 388-478-0035 |
| 3 | $654 | WAC 388-478-0035 |
| 4 | $721 | WAC 388-478-0035 |
| 5 | $826 | WAC 388-478-0035 |
| 6+ | $826 + $105 × (size − 5) | Extrapolation (not in cited WAC) |

**Calculator methodology:** Return the payment standard for the household size as the monthly benefit value. For household sizes 6+, apply the extrapolation rule above. `value_format` is `null` (monthly). `estimated_value` is `""` (blank — defers to calculator).

Source: [WAC 388-478-0035](https://app.leg.wa.gov/WAC/default.aspx?cite=388-478-0035)

---

## Test Scenarios

> ⚠️ **Income inconsistency note (devs):** Several "Eligible" scenarios carry gross income that exceeds the payment standard for their household size (Scenarios 1, 2, 6, 9). Under the screener's gross-income approximation in Criterion 2, these would be flagged as ineligible. The draft assumed earned-income disregards would apply ($90 + 50%). If the calculator does not apply disregards, these test cases will fail. Either (a) the calculator should implement disregards, or (b) the income amounts in these scenarios should be lowered before running tests.

---

### Scenario 1: Clearly Eligible Single Parent with Two Young Children

**What we're checking**: Golden-path eligible case — single parent, two young children, WA resident, low assets. Gross income $800/month for household of 3 vs. payment standard $654/month (WAC 388-478-0035). Note: gross exceeds standard by $146; with disregards applied, ($800 − $90) × 0.5 = $355 countable, below the $654 threshold. See income inconsistency note above.

**Expected**: Eligible, value: `654` (monthly)

**Steps**:

* **Location**: Enter ZIP code `98101`, Select county `King County`
* **Household**: Number of people: `3`
* **Person 1 (Head)**: Birth month/year: `June 1996` (age 29), Employment income: `$800/month`
* **Person 2 (Child)**: Birth month/year: `April 2019` (age 7), No income
* **Person 3 (Child)**: Birth month/year: `July 2022` (age 3), No income
* **Assets**: `$1,500`

---

### Scenario 2: Minimally Eligible — Single Parent with One Child at Boundary Conditions

**What we're checking**: Boundary conditions across three dimensions — child just under 18 (will turn 18 in mid-2026), assets exactly at the $6,000 limit (≤ comparison), and income at $521/month for household of 2. Gross income $521 vs. payment standard $440; with disregards: ($521 − $90) × 0.5 = $215.50, below threshold. See income inconsistency note above.

**Expected**: Eligible, value: `440` (monthly)

**Steps**:

* **Location**: Enter ZIP code `98109`, Select county `King County`
* **Household**: Number of people: `2`
* **Person 1 (Head)**: Birth month/year: `March 1990` (age 36), Employment income: `$521/month`
* **Person 2 (Child)**: Birth month/year: `June 2008` (age 17), No income
* **Assets**: `$6,000`

---

### Scenario 3: Single Parent with Three Children — Income $1 Below 4-Person Payment Standard

**What we're checking**: Gross income $720/month is $1 below the 4-person payment standard of $721/month. Confirms the ≤ comparison admits values just under the threshold.

**Expected**: Eligible, value: `721` (monthly)

**Steps**:

* **Location**: Enter ZIP code `98112`, Select county `King County`
* **Household**: Number of people: `4`
* **Person 1 (Head)**: Birth month/year: `April 1992` (age 34), Employment income: `$720/month`
* **Person 2 (Child)**: Birth month/year: `June 2014` (age 11), No income
* **Person 3 (Child)**: Birth month/year: `August 2017` (age 8), No income
* **Person 4 (Child)**: Birth month/year: `March 2021` (age 5), No income
* **Assets**: `$2,000`

---

### Scenario 4: Single Parent with One Child — Income Exactly at 2-Person Payment Standard

**What we're checking**: Gross income exactly at $440/month, the 2-person payment standard. Should be eligible under the ≤ comparison.

**Expected**: Eligible, value: `440` (monthly)

**Steps**:

* **Location**: Enter ZIP code `98103`, Select county `King County`
* **Household**: Number of people: `2`
* **Person 1 (Head)**: Birth month/year: `October 1995` (age 30), Employment income: `$440/month`
* **Person 2 (Child)**: Birth month/year: `February 2020` (age 6), No income
* **Assets**: `$1,500`

---

### Scenario 5: Single Parent with Two Children — Income $46 Above 3-Person Payment Standard — Ineligible

**What we're checking**: Gross income $700/month exceeds the 3-person payment standard of $654/month by $46. Screener approximation marks ineligible. With disregards applied, this household would likely qualify — documented as a known false negative of the gross-income methodology.

**Expected**: Ineligible

**Steps**:

* **Location**: Enter ZIP code `98115`, Select county `King County`
* **Household**: Number of people: `3`
* **Person 1 (Head)**: Birth month/year: `July 1993` (age 32), Employment income: `$700/month`
* **Person 2 (Child)**: Birth month/year: `March 2018` (age 8), No income
* **Person 3 (Child)**: Birth month/year: `November 2021` (age 4), No income
* **Assets**: `$2,000`

---

### Scenario 6: Newborn Child (Age 0) — Minimum Age for Dependent Child

**What we're checking**: A newborn (age 0) satisfies the dependent-child requirement. Tests the lower age boundary. Gross income $500/month vs. 2-person payment standard $440/month; with disregards: ($500 − $90) × 0.5 = $205. See income inconsistency note above.

**Expected**: Eligible, value: `440` (monthly)

**Steps**:

* **Location**: Enter ZIP code `98105`, Select county `King County`
* **Household**: Number of people: `2`
* **Person 1 (Head)**: Birth month/year: `November 1994` (age 31), Employment income: `$500/month`
* **Person 2 (Child)**: Birth month/year: `January 2026` (age 0), No income
* **Assets**: `$1,000`

---

### Scenario 7: 18-Year-Old Child, Income Above 2-Person Payment Standard — Ineligible

**What we're checking**: Reframed from the draft. Under the inclusivity assumption documented in Criterion 1 (all individuals under age 19 are treated as qualifying dependents), an 18-year-old counts as a qualifying dependent, so this scenario no longer isolates the dependent-child age branch. The household is ineligible on income — $800/month gross exceeds the 2-person payment standard of $440/month and would still exceed it after disregards (($800 − $90) × 0.5 = $355, but still subject to other deduction rules).

**Expected**: Ineligible

**Steps**:

* **Location**: Enter ZIP code `98117`, Select county `King County`
* **Household**: Number of people: `2`
* **Person 1 (Head)**: Birth month/year: `May 1985` (age 41), Employment income: `$800/month`
* **Person 2 (Child)**: Birth month/year: `April 2008` (age 18), No income
* **Assets**: `$1,000`

---

### Scenario 8: Parent with 9-Year-Old Child — Clearly Within Age Range, No Income

**What we're checking**: A 9-year-old (well within the dependent-child age range) and a parent with no earned income. Confirms the middle of the age range works and the calculator handles zero income.

**Expected**: Eligible, value: `440` (monthly)

**Steps**:

* **Location**: Enter ZIP code `98122`, Select county `King County`
* **Household**: Number of people: `2`
* **Person 1 (Head)**: Birth month/year: `August 1990` (age 35), No income
* **Person 2 (Child)**: Birth month/year: `July 2016` (age 9), No income
* **Assets**: `$500`

---

### Scenario 9: Valid WA ZIP Code (Spokane) — Eastern WA Residency Confirmed

**What we're checking**: A Spokane ZIP code (99201) satisfies WA state residency. Confirms the screener recognizes eastern WA ZIPs. Gross income $500/month vs. 2-person payment standard $440; with disregards: ($500 − $90) × 0.5 = $205. See income inconsistency note above.

**Expected**: Eligible, value: `440` (monthly)

**Steps**:

* **Location**: Enter ZIP code `99201`, Select county `Spokane County`
* **Household**: Number of people: `2`
* **Person 1 (Head)**: Birth month/year: `November 1994` (age 31), Employment income: `$500/month`
* **Person 2 (Child)**: Birth month/year: `March 2022` (age 4), No income
* **Assets**: `$1,500`

---

### Scenario 10: Mixed Household — Adult Non-Dependent Plus Two Young Children

**What we're checking**: A 21-year-old adult child does not count as a qualifying dependent, but the two younger children (ages 7 and 3) do. Confirms mixed-age households are assessed correctly. Spouse earns $800/month; household of 5 vs. payment standard $826/month (eligible at $800 ≤ $826).

**Expected**: Eligible, value: `826` (monthly)

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

**What we're checking**: All three children (ages 14, 8, and 1) qualify as dependents. Tests that all children count toward the assistance unit and the 5-person payment standard ($826/month) is used. Spouse income $800/month ≤ $826.

**Expected**: Eligible, value: `826` (monthly)

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

### Scenario 12: Assets Exactly at $6,000 Limit — Maximum Allowable Resources

**What we're checking**: Assets at exactly $6,000 should still be eligible per the ≤ comparison in WAC 388-470-0005. Income $300/month is comfortably under the 2-person payment standard.

**Expected**: Eligible, value: `440` (monthly)

**Steps**:

* **Location**: Enter ZIP code `98444`, Select county `Pierce County`
* **Household**: Number of people: `2`
* **Person 1 (Head)**: Birth month/year: `December 1996` (age 29), Employment income: `$300/month`
* **Person 2 (Child)**: Birth month/year: `April 2022` (age 4), No income
* **Assets**: `$6,000`

---

### Scenario 13: Pregnant Applicant, No Children — Eligible via Pregnancy Branch

**What we're checking**: Criterion 1's pregnancy branch. A pregnant applicant with no children in the household should be eligible. Tests that pregnancy alone satisfies the dependent-child / pregnancy requirement.

**Expected**: Eligible, value: `339` (monthly)

**Steps**:

* **Location**: Enter ZIP code `98101`, Select county `King County`
* **Household**: Number of people: `1`
* **Person 1 (Head)**: Birth month/year: `July 1998` (age 27), Employment income: `$200/month`, **Pregnant: yes**
* **Assets**: `$500`

---

### Scenario 14: Income Well Above Payment Standard — Clearly Ineligible

**What we're checking**: Clear income ineligibility. Gross income $2,000/month for a household of 3 is well above the $654/month payment standard, and remains over the threshold even with disregards applied (($2,000 − $90) × 0.5 = $955).

**Expected**: Ineligible

**Steps**:

* **Location**: Enter ZIP code `98103`, Select county `King County`
* **Household**: Number of people: `3`
* **Person 1 (Head)**: Birth month/year: `May 1990` (age 36), Employment income: `$2,000/month`
* **Person 2 (Spouse)**: Birth month/year: `October 1992` (age 33), No income
* **Person 3 (Child)**: Birth month/year: `April 2021` (age 5), No income
* **Assets**: `$1,000`

---

### Scenario 15: Assets Above $6,000 Limit — Ineligible on Resources

**What we're checking**: Asset exclusion. Assets of $7,500 exceed the $6,000 limit; household is otherwise eligible (low income, qualifying child, WA resident).

**Expected**: Ineligible

**Steps**:

* **Location**: Enter ZIP code `98033`, Select county `King County`
* **Household**: Number of people: `2`
* **Person 1 (Head)**: Birth month/year: `March 1991` (age 35), Employment income: `$200/month`
* **Person 2 (Child)**: Birth month/year: `June 2022` (age 3), No income
* **Assets**: `$7,500`

---

### Scenario 16: Out-of-State ZIP Code — Ineligible on Residency

**What we're checking**: Residency exclusion. An Oregon ZIP code (97201, Portland) should fail the WA state residency requirement; household is otherwise eligible.

**Expected**: Ineligible

**Steps**:

* **Location**: Enter ZIP code `97201`, Select county `Multnomah County` (Oregon — outside WA)
* **Household**: Number of people: `2`
* **Person 1 (Head)**: Birth month/year: `November 1994` (age 31), Employment income: `$300/month`
* **Person 2 (Child)**: Birth month/year: `April 2022` (age 4), No income
* **Assets**: `$1,000`
