# Implement LIEAP (KS) Program

## Program Details

* **Program**: LIEAP
* **State**: KS
* **White Label**: ks
* **Research Date**: 2026-07-03
* **Reviewed**: 2026-07-05

## Eligibility Criteria

1. **Household gross income must be at or below 150% of the Federal Poverty Level (unless categorically eligible under Criterion 2)**
   * Screener fields:
     * `household_size`
     * `calc_gross_income("yearly", ["all"])`
   * Source: 42 U.S.C. § 8624(b)(2)(B) — quoted: *"households with incomes which do not exceed the greater of— (i) an amount equal to 150 percent of the poverty level for such State; or (ii) an amount equal to 60 percent of the State median income"*. Kansas DCF publishes dollar amounts tied to household size: *"The combined gross income (before deductions) of all persons living at the address may not exceed 150% of the federal poverty level."*
   * **FPL year:** the calculator applies 150% of the **2026** federal poverty guidelines (config `year: 2026`). The 150% caps used in the scenarios below are computed from those guidelines, not from DCF's most-recent published season table (which was based on the 2025 guidelines). Caps: HH1 $23,940/yr ($1,995/mo), HH2 $32,460 ($2,705/mo), HH3 $40,980 ($3,415/mo), HH4 $49,500 ($4,125/mo), HH5 $58,020 ($4,835/mo).
   * Household definition: "household" means everyone living at the address, not just people on a lease or related by blood. This is how the screener's `household_size` field should be interpreted for this program — everyone at the address, not a tax-filing unit or family-relationship count.
2. **Categorical eligibility: households with a member receiving TANF, SSI, or SNAP qualify regardless of income**
   * Screener fields:
     * `has_snap`, `has_tanf`, `has_ssi_or_ssi_income`
   * Source: Kansas 2026 LIHEAP Detailed Model Plan, Heating Assistance §1.4a — quoted: *"If a household member receives one of the benefits listed above, they are considered income eligible, and we use the income already verified through that program for the LIEAP case. Kansas has a shared eligibility system, so we have access to the client's TANF and SNAP case as well as an interface with SSA to determine if they receive SSI."* Also grounded in 42 U.S.C. § 8624(b)(2)(A) — quoted: *"households in which 1 or more individuals are receiving— (i) assistance under [TANF]... (ii) supplemental security income payments... (iii) supplemental nutrition assistance program benefits... or (iv) payments under section 1315, 1521, 1541, or 1542 of title 38 [VA benefits]"*.
   * This is a real, independent eligibility pathway — a household qualifies this way even with income above 150% FPL. See Scenario 12.
   * Means-tested VA benefits do not confer categorical eligibility for this program. Kansas's 2026 LIHEAP Model Plan §1.4 marks "Means-tested Veterans Programs" as "No" for the Heating component (also "No" for Crisis and Weatherization) — only TANF, SSI, and SNAP are checked "Yes."
3. **Must reside in the state of Kansas**
   * Screener fields:
     * `county`
     * `zipcode`
   * Source: Kansas DCF LIEAP page (https://www.dcf.ks.gov/services/ees/Pages/EnergyAssistance.aspx) — a KS DCF-administered program serving KS addresses.
   * No ineligible scenario is needed for this criterion: the KS screener's location step only offers Kansas ZIP codes/counties as selectable values, so an out-of-state address isn't a reachable input — this is enforced by the location picker, not by calculator eligibility logic.
4. **Must be responsible for home energy costs (directly or as part of rent)**
   * Screener fields:
     * `is_home_owner`
     * `is_renter`
     * `electric_provider`
     * `gas_provider`
   * Source: Kansas DCF LIEAP page — quoted: *"An adult living at the address must be personally responsible for paying the heating costs at the current residence, payable either to the landlord, utility company, or fuel supplier."*
5. **U.S. citizenship or qualified non-citizen status required for at least one household member**
   * Source: 8 U.S.C. § 1611(a) and (c)(1)(B) — quoted: *"an alien who is not a qualified alien... is not eligible for any Federal public benefit"*, where "Federal public benefit" is defined to include *"any retirement, welfare, health, disability, public or assisted housing... or any other similar benefit... provided to an individual, household, or family eligibility unit by an agency of the United States or by appropriated funds of the United States"*. Kansas's 2026 LIHEAP Model Plan §17.3 (Citizenship/Legal Residency Verification) confirms this is actively verified for LIEAP recipients via attestation, SSA documentation, immigration status documentation, and the federal SAVE system.
   * Per program standards, immigration status is not a data gap: the program is configured to display only for the correct `legal_status_required` set rather than screened as a question, which is also why no scenario tests a household where zero members qualify — that case is handled by config filtering, not calculator logic.
6. **Must not reside in an institution (e.g., nursing home, prison) where energy costs are fully covered** ⚠️ *data gap*
   * Source: derives from Criterion 4 — an institutionalized person whose energy costs are fully covered by the institution would not meet Criterion 4 in practice, but this can't be verified via the current screener.
   * The screener does not collect institutionalization status. Per the inclusive principle, this is not built as a hard exclusion — display a note instead.
   * Impact: Low
7. **Renters in subsidized housing where heating fuel costs are included in their rent are not eligible** ⚠️ *data gap*
   * Source: Kansas 2026 LIHEAP Model Plan §2.3 — quoted verbatim: *"Renters living in subsidized housing where the heating fuel costs are included in their rent are not eligible for energy assistance."*
   * The screener does not collect whether a renter's rent includes heating costs, so this cannot be evaluated directly. Per the inclusive principle, this is not built as a hard exclusion without that data — display a note instead.
   * Impact: Medium

## Benefit Value

* **Range: $130 minimum – $4,301 maximum per household per season** (Kansas 2026 LIHEAP Model Plan §2.6).
* **Determined by**: income, household size, and a fuel-provider rate-tier matrix (§2.5) — quoted: *"Kansas uses a matrix with fuel providers in tiers based on a range of their rates during a specific month."* The matrix itself is a separate attachment to the State Plan and is not available for this spec. As these number change based on month, the calculator will provide the average benefit amount.
* **Value used in test scenarios: $680/year (flat).** DCF's reported statewide average benefit for the most recently completed season — quoted: *"In 2025, more than 43,000 Kansas households received an average benefit of about $680."*
* Because every eligible scenario below uses this same flat value, the test suite validates eligibility determinations but does not validate the benefit calculation itself.

## Implementation Coverage

* ✅ Evaluable criteria: 5 (income including household definition, categorical eligibility, KS residency, energy-cost responsibility, citizenship)
* ⚠️ Data gaps: 2 (institutionalization, subsidized-housing utility inclusion)
* Not eligibility criteria — belongs in config `description`/`documents`: seasonal application-window notice, one-benefit-per-season note, SSN requirement, proof-of-income/identity/utility documentation.
* Not tested: household sizes above 5 (DCF's table extends the income limit to larger households via a +$688/month-per-person increment).

## Research Sources

* [Kansas DCF – Low Income Energy Assistance Program (LIEAP) Overview & Eligibility Information](https://www.dcf.ks.gov/services/ees/Pages/EnergyAssistance.aspx)
* [Kansas DCF Newsroom – LIEAP 2026 Application Period Announcement (income table, application window, $680 average benefit)](https://www.dcf.ks.gov/Newsroom/pages/LIEAP2026.aspx)
* [Kansas KEES Self-Service Portal – Online Application for LIEAP](https://cssp.kees.ks.gov/apspssp/sspNonMed.portal)
* [Kansas 2026 LIHEAP Detailed Model Plan (State Plan filed with ACF)](https://liheapch.acf.gov/docs/2026/state-plans/KS_Plan_2026.pdf)
* [42 U.S.C. § 8624 – Applications and requirements (federal LIHEAP statute)](https://www.law.cornell.edu/uscode/text/42/8624)
* [8 U.S.C. § 1611 – Aliens who are not qualified aliens ineligible for Federal public benefits](https://www.law.cornell.edu/uscode/text/8/1611)

## Acceptance Criteria

[ ] Scenario 1 (Single Adult Well Below Income Limit - Clearly Eligible): User should be **eligible** with $680/year
[ ] Scenario 2 (Two-Person Household Near Income Ceiling - Barely Eligible): User should be **eligible** with $680/year
[ ] Scenario 3 (Three-Person Household Income Just Below 150% FPL - Barely Eligible): User should be **eligible** with $680/year
[ ] Scenario 4 (Four-Person Household Income Exactly at 150% FPL - Boundary Eligible): User should be **eligible** with $680/year
[ ] Scenario 5 (Single Adult Income Just Above 150% FPL - Ineligible): User should be **ineligible**
[ ] Scenario 6 (65-Year-Old Senior on Social Security, Clearly Eligible): User should be **eligible** with $680/year
[ ] Scenario 7 (Household Already Receiving LIEAP Benefits - Exclusion Check): User should be **ineligible**
[ ] Scenario 8 (Household Not Responsible for Home Energy Costs - Excluded): User should be **ineligible**
[ ] Scenario 9 (Mixed Household - Some Members Citizen, Some Non-Citizen, Income Eligible): User should be **eligible** with $680/year
[ ] Scenario 10 (Five-Person Household with Two Adults and Three Children - All Eligible Members): User should be **eligible** with $680/year
[ ] Scenario 11 (Single-Person Household with Zero Income - Edge Case Eligible): User should be **eligible** with $680/year
[ ] Scenario 12 (Household Over Income Limit but Categorically Eligible via SNAP): User should be **eligible** with $680/year

## Test Scenarios

### Scenario 1: Single Adult Well Below Income Limit - Clearly Eligible

**What we're checking**: Typical clearly eligible applicant: single Kansas resident, U.S. citizen, responsible for energy costs, income well below 150% FPL
**Expected**: Eligible, $680/year

**Steps**:

* **Location**: Enter ZIP code `66603`, Select county `Shawnee`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `March 1971` (age 55), Relationship: `Head of Household`, U.S. citizen: `Yes`, Has income: `Yes`, Employment/wages income: `$1,200` per month ($14,400/year — well below the $23,940/year (150% FPL) threshold for a household of 1: $1,995/month × 12)
* **Energy Costs**: Indicate household is responsible for home energy costs: `Yes`, Select heating fuel type if prompted (e.g., `Natural Gas`)
* **Current Benefits**: No current benefits selected

**Why this matters**: Baseline happy-path test for a straightforward, clearly eligible single adult in Kansas with income well below the 150% FPL threshold and direct energy cost responsibility, using employment income (see Scenario 6 for the Social Security income-type variant).

---

### Scenario 2: Two-Person Household Near Income Ceiling - Barely Eligible

**What we're checking**: Household with gross income just under the 150% FPL threshold for a 2-person household ($32,460/year = $2,705/month × 12)
**Expected**: Eligible, $680/year

**Steps**:

* **Location**: Enter ZIP code `66502`, Select county `Riley`
* **Household**: Number of people: `2`
* **Person 1**: Birth month/year: `January 1986` (age 40), Relationship: `Head of Household`, U.S. citizen: `Yes`, Has income: `Yes`, Employment income: `$1,500` per month
* **Person 2**: Birth month/year: `March 1988` (age 38), Relationship: `Spouse`, U.S. citizen: `Yes`, Has income: `Yes`, Employment income: `$1,200` per month
* **Energy Costs**: Indicate household is responsible for home heating costs: `Yes`, Select heating fuel type if prompted (e.g., `Natural Gas`)

**Why this matters**: Combined income is $2,700/month ($32,400/year) — $60/year under the $32,460 cap. Confirms the screener does not incorrectly reject households barely within the income limit.

---

### Scenario 3: Three-Person Household Income Just Below 150% FPL - Barely Eligible

**What we're checking**: A household of 3 with gross annual income just below the 150% FPL threshold ($40,980/year = $3,415/month × 12)
**Expected**: Eligible, $680/year

**Steps**:

* **Location**: Enter ZIP code `66502`, Select county `Riley`
* **Household**: Number of people: `3`
* **Person 1**: Birth month/year: `March 1991` (age 35), Relationship: `Head of Household`, U.S. citizen: `Yes`, Has income: `Yes`, Employment income: `$3,400` per month
* **Person 2**: Birth month/year: `September 1992` (age 33), Relationship: `Spouse`, U.S. citizen: `Yes`, Has income: `No`
* **Person 3**: Birth month/year: `January 2021` (age 5), Relationship: `Child`, U.S. citizen: `Yes`, Has income: `No`
* **Energy Costs**: Indicate the household is responsible for home energy costs: `Yes`, Select heating fuel type if prompted: `Natural Gas`

**Why this matters**: Combined income is $3,400/month ($40,800/year) — $180/year under the $40,980 cap.

---

### Scenario 4: Four-Person Household Income Exactly at 150% FPL - Boundary Eligible

**What we're checking**: A 4-person household whose gross monthly income equals exactly the 150% FPL cap ($4,125/month = $49,500/year)
**Expected**: Eligible, $680/year

**Steps**:

* **Location**: Enter ZIP code `66604`, Select county `Shawnee`
* **Household**: Number of people: `4`
* **Person 1**: Birth month/year: `March 1986` (age 40), Relationship: `Head of Household`, U.S. citizen: `Yes`, Has income: `Yes`, Employment income: `$3,125` monthly, No other income sources
* **Person 2**: Birth month/year: `September 1988` (age 37), Relationship: `Spouse`, U.S. citizen: `Yes`, Has income: `Yes`, Employment income: `$1,000` monthly, No other income sources
* **Person 3**: Birth month/year: `January 2016` (age 10), Relationship: `Child`, U.S. citizen: `Yes`, Has income: `No`
* **Person 4**: Birth month/year: `June 2019` (age 7), Relationship: `Child`, U.S. citizen: `Yes`, Has income: `No`
* **Energy Costs**: Indicate household is responsible for home energy costs: `Yes`, Heating fuel type: `Natural gas`

**Why this matters**: Combined monthly income ($3,125 + $1,000 = $4,125) exactly matches the 150% FPL monthly cap for a 4-person household. Tests that the comparison is inclusive (≤), not strictly less-than.

---

### Scenario 5: Single Adult Income Just Above 150% FPL - Ineligible

**What we're checking**: A single-person household with gross income just above the 150% FPL cap ($1,995/month) is correctly denied
**Expected**: Not eligible

**Steps**:

* **Location**: Enter ZIP code `66502`, Select county `Riley`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `March 1976` (age 50), Relationship: `Head of Household`, U.S. citizen: `Yes`, Has income: `Yes`, Employment income: `$2,000` per month (annualizes to $24,000/year, above the $23,940/year cap), No other income sources
* **Energy Costs**: Indicate household is responsible for home energy costs: `Yes`
* **Current Benefits**: No current benefits selected

**Why this matters**: $2,000/month is $5 above the $1,995 monthly cap ($60/year above the $23,940 annual cap) for a 1-person household — a genuine "just above" test using the same 150% FPL threshold as Scenario 1.

---

### Scenario 6: 65-Year-Old Senior on Social Security, Clearly Eligible

**What we're checking**: A senior with income from Social Security (a distinct income type from Scenario 1's employment income, both of which must count under Criterion 1's "all income types" test), well below the income cap
**Expected**: Eligible, $680/year

**Steps**:

* **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `March 1961` (age 65), Relationship: `Head of Household`, U.S. citizen: `Yes`, Has income: `Yes`, Social Security Retirement income: `$900` per month, No other income sources
* **Energy Costs**: Indicate household is responsible for home energy costs: `Yes`
* **Current Benefits**: No current benefits selected

**Why this matters**: Seniors on Social Security are a primary LIEAP population, and this confirms unearned income is aggregated the same as earned income for the FPL test.

---

### Scenario 7: Household Already Receiving LIEAP Benefits - Exclusion Check

**What we're checking**: A household already receiving LIEAP this season is not shown as newly eligible
**Expected**: Not eligible

**Steps**:

* **Location**: Enter ZIP code `66604`, Select county `Shawnee`
* **Household**: Number of people: `2`
* **Person 1**: Birth month/year: `March 1961` (age 65), Relationship: `Head of Household`, U.S. citizen: `Yes`, Has income: `Yes`, Social Security Retirement income: `$900` per month
* **Person 2**: Birth month/year: `June 1963` (age 63), Relationship: `Spouse`, U.S. citizen: `Yes`, Has income: `No`
* **Expenses**: Indicate household pays home energy costs directly: `Yes`
* **Current Benefits**: Select that the household currently receives `LIEAP`

**Why this matters**: LIEAP pays only one benefit per year, per DCF: *"LIEAP pays only one benefit per year."* Handled via a dedicated `has_ks_lieap` screener field (matching the `has_il_liheap`/`has_nc_lieap` pattern used for other states), not a numbered eligibility criterion.

---

### Scenario 8: Household Not Responsible for Home Energy Costs - Excluded

**What we're checking**: A household with no responsibility for home energy costs (Criterion 4) is excluded, even with eligible income
**Expected**: Not eligible

**Steps**:

* **Location**: Enter ZIP code `66604`, Select county `Shawnee`
* **Household**: Number of people: `2`
* **Person 1**: Birth month/year: `March 1980` (age 46), Relationship: Head of Household, U.S. citizen: Yes
* **Person 2**: Birth month/year: `September 1982` (age 43), Relationship: Spouse, U.S. citizen: Yes
* **Income**: Person 1 employment income: `$1,200`/month, Person 2 employment income: `$800`/month — total $2,000/month ($24,000/year), well below DCF's $31,728/year cap for a 2-person household
* **Energy Costs / Housing**: Indicate the household does NOT pay energy costs directly and energy is NOT included in rent (e.g., paid entirely by a landlord with no pass-through)

**Why this matters**: Tests Criterion 4 (DCF: "an adult... must be personally responsible for paying the heating costs"). Income-eligible but not cost-responsible households should still be excluded.

---

### Scenario 9: Mixed Household - Some Members Citizen, Some Non-Citizen, Income Eligible

**What we're checking**: A household with mixed citizenship status is handled inclusively per Criterion 5
**Expected**: Eligible, $680/year

**Steps**:

* **Location**: Enter ZIP code `66502`, Select county `Riley`
* **Household**: Number of people: `4`
* **Person 1**: Birth month/year: `March 1986` (age 40), Relationship: Head of Household, Citizenship status: `US Citizen`, Has income: Yes, Employment income: `$1,800`/month
* **Person 2**: Birth month/year: `September 1988` (age 37), Relationship: Spouse, Citizenship status: `Non-citizen / Not eligible`, Has income: Yes, Employment income: `$1,200`/month
* **Person 3**: Birth month/year: `January 2016` (age 10), Relationship: Child, Citizenship status: `US Citizen`, Has income: No
* **Person 4**: Birth month/year: `June 2019` (age 7), Relationship: Child, Citizenship status: `US Citizen`, Has income: No
* **Energy Costs**: Indicate the household is responsible for home energy costs: Yes, Energy type: Gas and Electric
* **Current Benefits**: No current LIEAP benefits received this season

**Why this matters**: Since at least one household member (the head of household) is a U.S. citizen, Criterion 5 is met at the household level; the whole household should be counted for size and income purposes rather than excluded.

---

### Scenario 10: Five-Person Household with Two Adults and Three Children - All Eligible Members

**What we're checking**: Standard multi-earner, multi-child household is aggregated correctly
**Expected**: Eligible, $680/year

**Steps**:

* **Location**: Enter ZIP code `66502`, Select county `Riley`
* **Household**: Number of people: `5`
* **Person 1**: Birth month/year: `March 1986` (age 40), Relationship: `Head of Household`, U.S. citizen: `Yes`, Has income: `Yes`, Employment income: `$2,400`/month
* **Person 2**: Birth month/year: `June 1988` (age 38), Relationship: `Spouse`, U.S. citizen: `Yes`, Has income: `Yes`, Employment income: `$1,200`/month
* **Person 3**: Birth month/year: `September 2012` (age 13), Relationship: `Child`, U.S. citizen: `Yes`, Has income: `No`
* **Person 4**: Birth month/year: `February 2016` (age 10), Relationship: `Child`, U.S. citizen: `Yes`, Has income: `No`
* **Person 5**: Birth month/year: `January 2021` (age 5), Relationship: `Child`, U.S. citizen: `Yes`, Has income: `No`
* **Energy Costs**: Indicate household is responsible for home energy costs: `Yes`, Heating fuel type: `Natural Gas`
* **Current Benefits**: LIEAP currently receiving: `No`

**Why this matters**: Combined income $3,600/month ($43,200/year) is well under the 5-person cap ($4,835/month = $58,020/year). Confirms multi-earner, multi-child aggregation.

---

### Scenario 11: Single-Person Household with Zero Income - Edge Case Eligible

**What we're checking**: A household reporting exactly $0 income is still processed as eligible
**Expected**: Eligible, $680/year

**Steps**:

* **Location**: Enter ZIP code `66604`, Select county `Shawnee`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `January 1980` (age 46), Relationship: `Head of Household`, Citizenship status: `U.S. Citizen`, Has income: `No` (all income fields left at $0), No current benefits selected
* **Energy Costs**: Indicate household is responsible for home energy costs: `Yes`, Energy cost type: `Directly pays heating bills`

**Why this matters**: LIEAP has no minimum-income requirement, only a maximum. Confirms $0 is handled as a valid value, not an error.

---

### Scenario 12: Household Over Income Limit but Categorically Eligible via SNAP

**What we're checking**: Tests Criterion 2 — a household with gross income above the standard 150% FPL cap is still eligible because a member receives SNAP
**Expected**: Eligible, $680/year

**Steps**:

* **Location**: Enter ZIP code `66604`, Select county `Shawnee`
* **Household**: Number of people: `2`
* **Person 1**: Birth month/year: `March 1985` (age 41), Relationship: `Head of Household`, U.S. citizen: `Yes`, Has income: `Yes`, Employment income: `$3,200`/month
* **Person 2**: Birth month/year: `June 1987` (age 39), Relationship: `Spouse`, U.S. citizen: `Yes`, Has income: `Yes`, Employment income: `$0`/month
* **Income total**: $3,200/month = $38,400/year — **above** the $32,460/year (150% FPL) cap for a 2-person household
* **Energy Costs**: Indicate household is responsible for home energy costs: `Yes`
* **Current Benefits**: Select that the household currently receives `SNAP` (Supplemental Nutrition Assistance Program)

**Why this matters**: Confirms a household over the income cap but SNAP-eligible is still correctly shown as eligible, per Kansas's state-plan policy (Criterion 2). This is also the natural counterpart-check to Scenario 5 — same income shape, different outcome once categorical eligibility applies.
