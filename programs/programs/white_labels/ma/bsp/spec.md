# Implement BabySteps Savings Plan (MA) Program

## Program Details

- **Program**: BabySteps Savings Plan
- **State**: MA
- **White Label**: ma

## Eligibility Criteria

BabySteps eligibility is determined **separately for each child** in the household. Each qualifying child may receive one $50 deposit into an eligible individual MEFA U.Fund 529 account. A household with multiple qualifying children is worth $50 per qualifying child, not a single flat $50.

### 1. Child must be a Massachusetts resident when the U.Fund account is opened

- **Rule**: Applies to the **child**, not necessarily the parent, guardian, or account owner — anyone (a relative or friend) may open the account on the eligible child's behalf.
- **Screener fields**: none read by this calculator — `relationship` identifies which household members are evaluated as beneficiaries, but it is not a residency test.
- **Handling**: Enforced upstream by white-label routing, not by this calculator — `ma_bsp` is only ever evaluated for `ma` screens, and the program is statewide, so there is no sub-state or ZIP condition to apply. No out-of-state scenario is listed below because an out-of-state household never reaches this calculator.
- **Source**: Mass.gov BabySteps eligibility FAQ ("Live in Massachusetts"); Massachusetts Treasury, "This 529 Day, Claim $50 for Your Child's Future with BabySteps" (2026), which confirms relatives or friends may open the account.

### 2. Child must qualify through the birth pathway or the adoption pathway

#### 2a. Birth pathway

- **Rule**: The child must have been born on or after January 1, 2020 (the program's operating start date), and the eligible U.Fund account must be opened **before the child's first birthday**.
- **Screener fields**: `birth_year`, `birth_month`
- **Handling**: The screener does not collect day of birth, so a child in the month of their first birthday could fall on either side of the exact deadline. Treat the entire first-birthday month as inclusively within the window. Official sources differ slightly on the exact boundary (Mass.gov: first birthday/adoption anniversary; MEFA participation terms: 365-calendar-day deadline), which can diverge by a day around leap years — since the screener only captures month/year, this day-level distinction can't be resolved either way, so the month-level inclusive treatment applies regardless of which framing governs.
- **Source**: Mass.gov BabySteps eligibility page; MEFA BabySteps Adoption Verification and Participation Terms.

#### 2b. Adoption pathway ⚠️ *data gap*

- **Rule**: The qualifying adoption must have occurred on or after January 1, 2020, and the eligible U.Fund account must be opened **before the first anniversary of the child's adoption**. The adoptive family must also complete the BabySteps Adoption Verification Form (see Application Process). Adopted children can qualify at any age based on the adoption date, independent of birth date.
- **Screener fields**: none — the screener does not collect whether a child was adopted, the adoption date, or whether the first adoption anniversary has passed.
- **Handling**: Not evaluable — the adoption window runs one year from the *adoption date*, not from birth, so it cannot be approximated from the birth date the screener does collect. The birth-pathway cutoff (Criterion 2a) therefore applies to every beneficiary candidate: a child past their first-birthday month is ineligible. This is a known false negative for children adopted within the preceding year, accepted deliberately — an inclusive default here would instead pass every child of every age in every Massachusetts household, since the adoption pathway has no age bound at all. The narrow exception cannot carry the eligibility decision for the common case. See **User-facing handling** below: the description cannot currently reach the affected households.
- **User-facing handling**: The program description states that adopted children can qualify at any age within one year of the adoption, and directs families who adopted within the past year to check with MEFA directly. ⚠️ **This does not reach the affected households.** Results filtering drops a program when no member is eligible (`eligible && value > 0` in the frontend's `isProgramBasicallyVisible`), so a household whose only candidate is past the cutoff never renders the card and never sees this copy. The description reaches only households that already qualify. The false negative is therefore unmitigated in the product, accepted knowingly under MFB-1729. Closing it needs either a screener adoption field or a surface for near-miss programs; neither is in scope here.
- **Product decision**: Reversed under MFB-1729 after a partner reported a two-year-old shown as eligible. Closing the gap properly requires a screener field capturing recent adoption (or adoption date); until that exists, the cutoff plus description disclosure is the accepted handling.
- **Source**: Mass.gov BabySteps eligibility page and information booklet (adopted children of any age may qualify); MEFA BabySteps and Adoption Verification pages.

### 3. Child must not have already received a BabySteps contribution ⚠️ *data gap*

- **Rule**: Only one BabySteps $50 contribution is available per designated beneficiary (per child).
- **Screener fields**: none — the screener's current-benefits field is household-level and cannot reliably identify prior BabySteps receipt for each individual child.
- **Handling**: Do not exclude the whole household from a household-level "currently receiving BabySteps" response. A family may have already received BabySteps for one child but still have a newly born or adopted child who separately qualifies. Default inclusively per child.
- **Source**: MEFA BabySteps page and BabySteps program participation terms ("There is a limit of one BabySteps contribution per child").

### 4. Child must have been born or adopted in Massachusetts ⚠️ *data gap*

- **Rule**: The designated beneficiary must have been born or adopted in Massachusetts on or after January 1, 2020, in addition to being a Massachusetts resident when the account is opened (Criterion 1).
- **Screener fields**: none — the screener does not collect birthplace or adoption location.
- **Source-hierarchy note**: MEFA's active participation terms and Fidelity's U.Fund Plan Fact Kit both explicitly require the beneficiary to have been "born or adopted in Massachusetts." The current Mass.gov eligibility page and 2026 Treasury guidance state only that the child must live in Massachusetts, without addressing birthplace — treated as an incomplete public restatement rather than a conflicting policy, so the MEFA/Fidelity requirement is treated as the real criterion here.
- **Handling**: The screener cannot verify birthplace or adoption location, so apply the inclusive default — do not exclude a household based on this unavailable information. Actual eligibility remains subject to verification during enrollment.
- **User-facing handling**: State in the program description that the child must have been born or adopted in Massachusetts.
- **Source**: Fidelity Massachusetts U.Fund Plan Fact Kit (Jan. 2, 2026), "BabySteps Program" section; MEFA BabySteps Adoption Verification and Participation Terms; MEFA BabySteps Program Page; Mass.gov BabySteps FAQ.

### Eligibility-unit rule

- Evaluate eligibility separately for every qualifying household member.
- One qualifying child = $50; multiple qualifying children = $50 per qualifying child (e.g., three qualifying children = $150 total).
- An older or otherwise-uncertain member does not prevent another qualifying member in the same household from qualifying.

#### Beneficiary/member-identification mapping

**Why this mapping exists**: No source maps BabySteps beneficiary status onto specific MFB `relationship` values — "anyone may open the account on the child's behalf" describes who may act as the **account participant**, not who the **beneficiary** is. Product has mapped this directly from the existing `relationship` enum, since no source settles it and no new screener field is available.

- **Beneficiary candidates:** `child`, `fosterChild`, `grandChild`, `sibling`, `other`
- **Not beneficiary candidates:** `headOfHousehold`, `spouse`, `domesticPartner`, `parent`, `fosterParent`, `stepParent`, `grandParent` — these describe adult caregiver/partner roles typically opening or managing the account, not the enrolled child.

**Scope note**: This mapping defines the **assistance unit** — which household members are in scope for evaluation at all — a separate question from the inclusive-default rule, which governs unverifiable facts about a candidate already in scope (e.g., recent adoption, Criterion 2b).

**Known accepted limitations** *(both accepted as known edge cases, not oversights — revisit only if either proves to matter in practice)*:

- **False negative:** Massachusetts permits adult adoption, and adopted children of any age may qualify. A household member legitimately adopted as an adult but reported under an excluded role (e.g., `headOfHousehold`) won't be picked up by this rule.
- **False positive:** a `sibling` or `other` household member under one year old is treated as a beneficiary candidate and valued at $50 with no direct evidence they are the intended beneficiary. The Criterion 2b age cutoff bounds this to members inside the birth-pathway window rather than members of any age.

**Required test coverage:** the full mapping (all 12 `relationship` values) must be covered by a parameterized unit test asserting `is_beneficiary_candidate(rel)`:

| `relationship` value | Beneficiary candidate? |
| --- | --- |
| `child` | Yes |
| `fosterChild` | Yes |
| `grandChild` | Yes |
| `sibling` | Yes |
| `other` | Yes |
| `headOfHousehold` | No |
| `spouse` | No |
| `domesticPartner` | No |
| `parent` | No |
| `fosterParent` | No |
| `stepParent` | No |
| `grandParent` | No |

**Coverage note**: Scenarios 1, 5, and 8 (below) exercise `child`, `headOfHousehold`/`spouse`, and `grandChild` at the household level; the remaining values should be covered by this table as a direct unit-level assertion, not additional full scenarios.

### Legal status

**Rule**: BabySteps does not impose a citizenship or immigration-status eligibility gate. Configure all six MFB base `legal_status_required` values (no restriction).

**Note**: The U.Fund provider (Fidelity) requests identifying and taxpayer information for the beneficiary during account opening (see Application Process), but that is an application/documentation requirement, not a BabySteps eligibility criterion.

### Not eligibility gates

- **Household income, assets, health insurance status, or other benefit receipt**: no source establishes any of these as a base BabySteps eligibility test. SNAP participation is not an exclusion and is not required either. (A household on SNAP may separately qualify for an additional $120 under the related "SNAP into BabySteps" initiative — a distinct program, out of scope for this base $50 calculator.)
- **A separate parent/guardian Massachusetts-residency requirement**: Treasury's 2026 guidance confirms anyone may open the account on the child's behalf, including relatives and friends — there is no requirement that a parent/guardian be a household member or personally reside in Massachusetts.

## Priority Criteria

None. BabySteps does not prioritize otherwise-eligible children based on income, SNAP participation, geography within Massachusetts, or any other household characteristic.

## Continuing Eligibility / Participant Requirements

None for receipt of the one-time BabySteps contribution — no ongoing household eligibility test applies after the account is opened.

- Opening an eligible U.Fund account constitutes consent to MEFA sharing certain account information with the Massachusetts State Treasurer's Office when required to fund the contribution.
- A participant may opt out within 30 calendar days of opening the account. If sharing is required for funding, opting out makes the account ineligible for the contribution.
- This is a post-opening participant action, not a household eligibility gate — the screener has no field for it and it isn't used as a calculator condition.

Source: Fidelity Massachusetts U.Fund Plan Fact Kit, Jan. 2, 2026.

## Application Process / Program Requirements

1. Open a new MEFA U.Fund 529 account — **must be an individual account** — within one year of the qualifying child's birth or adoption.
2. Name the qualifying child as the account's designated beneficiary.
3. The account may be opened by an eligible adult participant, including a relative or friend outside the child's household. Per Fidelity's U.Fund Plan Fact Kit (Jan. 2, 2026), the participant must:
   - be at least 18
   - be a U.S. resident
   - maintain a U.S. legal/mailing address
   - have an SSN or Tax ID

   The beneficiary must also have an SSN or Tax ID. These are U.Fund account-opening requirements, not a BabySteps citizenship gate.
4. Provide the beneficiary's identifying and taxpayer information (SSN or Tax ID).
5. Adoptive families must additionally submit the BabySteps Adoption Verification Form.
6. No family contribution is required — MEFA deposits the $50 automatically to any account meeting the above steps within the enrollment window, approximately six weeks after the account is opened.

Source: Mass.gov BabySteps page (deposit arrives "approximately 6 weeks after opening"); Massachusetts Treasury 2026 guidance; Fidelity U.Fund application and U.Fund Plan Fact Kit (Jan. 2, 2026); MEFA BabySteps Adoption Verification page.

## Program Availability

MEFA's BabySteps participation terms note that deposits are subject to the availability of sufficient state funding and that the program could be modified or discontinued. As of the most recent Massachusetts Treasury announcement (May 2026), the program remains active. This is a program-level note, not a household eligibility gate.

Source: MEFA BabySteps Adoption Verification / participation terms page.

## Benefit Value

### Base benefit amount

For each qualifying child with an eligible, funded BabySteps enrollment, Massachusetts contributes a one-time $50 seed deposit to the child's individual MEFA U.Fund 529 account, paid into the account rather than directly to the household as cash.

- **Per-child value:** $50.00
- **Household value formula:** `$50 × number of qualifying children` (every eligible scenario returns this; ineligible scenarios return no value)
- **Examples:** one child = $50; two children = $100; three children = $150
- **Contribution cadence:** one time per child
- **Value format:** `lump_sum`
- **Required family contribution:** $0

Source: MEFA BabySteps page ("a $50 seed deposit into a U.Fund 529 account"; "limit of one BabySteps contribution per child"); Fidelity U.Fund Plan Fact Kit (Jan. 2, 2026), "BabySteps Program" section.

### Investment growth

The calculator must return the fixed **$50 seed-deposit amount**, not an estimated future account balance. The deposit may grow or lose value after investment depending on investment selection, market performance, expenses, additional contributions, and time invested. Any published illustrative growth example must not be included in the committed MFB benefit value.

### Related programs

Do not add the separate SNAP into BabySteps benefit to this calculator. That program can provide an additional $120 through twelve monthly $10 deposits, but has separate enrollment and eligibility requirements. A household receiving SNAP remains valued at **$50 per qualifying child** under this base calculator.

## Test Scenarios

All scenarios and expected results are evaluated as of July 22, 2026. Automated tests must freeze the calculation date to July 22, 2026 so the fixed birth months/years below continue to test the intended eligibility branches.

### Scenario 1: Golden Path — MA Resident with Recently Born Child
**What we're checking**: A typical Massachusetts household with a child born within the past year qualifies for the base $50 deposit.
**Expected**: Eligible, $50.00

- **Location**: ZIP `02101` (Suffolk County)
- **Household**: 2 people
- Person 1: `headOfHousehold`, born March 1994
- Person 2: `child`, born February 2026

**Why this matters**: The primary regression test — a Massachusetts household with a child clearly inside the birth-pathway window.

---

### Scenario 2: No Income Gate — High-Income MA Family with Qualifying Child
**What we're checking**: BabySteps has no income limit; a high-income household with a qualifying child is still eligible for the full $50.
**Expected**: Eligible, $50.00

- **Location**: ZIP `02139` (Middlesex County)
- **Household**: 3 people
- Person 1: `headOfHousehold`, born March 1991, employment income $6,250/month
- Person 2: `spouse`, born June 1992, employment income $5,417/month
- Person 3: `child`, born February 2026, no income

**Why this matters**: No source supports an income limit for base BabySteps; this confirms income has no bearing on eligibility.

---

### Scenario 3: Multiple Qualifying Children — Twins Both Within Enrollment Window
**What we're checking**: A household with two children who both qualify under the birth pathway receives $50 for each child, not a single flat household amount.
**Expected**: Eligible, $100.00

- **Location**: ZIP `01201` (Berkshire County)
- **Household**: 4 people
- Person 1: `headOfHousehold`, born March 1990
- Person 2: `spouse`, born August 1991
- Person 3: `child`, born November 2025
- Person 4: `child`, born November 2025

**Why this matters**: Confirms the calculator stacks $50 per qualifying child rather than treating eligibility as a single household-level flag.

---

### Scenario 4: Mixed-Age Household — Recent Birth Plus Older Sibling
**What we're checking**: A household with one child inside the birth-pathway window and one older sibling past the first-birthday cutoff. Only the child inside the window is valued; per-child evaluation means the ineligible sibling does not block the eligible child.
**Expected**: Eligible, $50.00 (only the recent-birth child qualifies)

- **Location**: ZIP `02148` (Middlesex County)
- **Household**: 4 people
- Person 1: `headOfHousehold`, born March 1990
- Person 2: `spouse`, born June 1991
- Person 3: `child`, born September 2018 (older sibling; past the first-birthday cutoff)
- Person 4: `child`, born February 2026

**Why this matters**: Confirms the age cutoff is applied per child rather than per household — the older sibling is excluded without suppressing the qualifying newborn. If the older child was in fact adopted within the past year they would really qualify; that known false negative is disclosed in the program description (Criterion 2b).

---

### Scenario 5: No Qualifying Beneficiary in Household
**What we're checking**: A Massachusetts household containing only members reported under non-beneficiary roles (`headOfHousehold`, `spouse`) has no BabySteps beneficiary candidate present, and is therefore ineligible.
**Expected**: Ineligible

- **Location**: ZIP `01201` (Berkshire County)
- **Household**: 2 people
- Person 1: `headOfHousehold`, born March 1990
- Person 2: `spouse`, born August 1991

**Why this matters**: BabySteps is evaluated per qualifying beneficiary. Per the relationship mapping, `headOfHousehold` and `spouse` are excluded as adult caregiver/partner roles, so this household has no evaluable beneficiary candidate at all.

---

### Scenario 6: SNAP Participation Does Not Exclude — Family Also Receiving SNAP
**What we're checking**: A household currently receiving SNAP is still eligible for the base $50 deposit; SNAP receipt is neither required nor an exclusion for the base program.
**Expected**: Eligible, $50.00

- **Location**: ZIP `02148` (Middlesex County)
- **Household**: 3 people
- Person 1: `headOfHousehold`, born March 1990, employment income $2,800/month
- Person 2: `spouse`, born August 1989, employment income $2,200/month
- Person 3: `child`, born February 2026
- **Current Benefits**: SNAP

**Why this matters**: Confirms the base $50 calculator is unaffected by SNAP participation in either direction. The separate "SNAP into BabySteps" $120 add-on is a distinct program and out of scope here.

---

### Scenario 7: Qualifying Grandchild — Non-`child` Relationship Value
**What we're checking**: A household member reported under a relationship value other than `child` — here `grandChild`, a committed beneficiary candidate — is evaluated as a potential beneficiary. BabySteps' rule is about Massachusetts residency and birth/adoption timing, not being the head of household's biological son or daughter.
**Expected**: Eligible, $50.00

- **Location**: ZIP `02101` (Suffolk County)
- **Household**: 2 people
- Person 1: `headOfHousehold`, born March 1968
- Person 2: `grandChild`, born March 2026

**Why this matters**: A calculator that filters beneficiaries with `relationship == "child"` only would wrongly exclude this household despite it meeting residency and birth-pathway criteria.

---

### Scenario 8: Birth-Pathway Month Boundary — Child Turning One This Month
**What we're checking**: The screener only collects birth month/year, not day. A child turning one during the current month is treated inclusively as still within the one-year enrollment window.
**Expected**: Eligible, $50.00

**Internal assertion (required)**: the unit test must assert `birth_pathway_eligible == true` for Person 2, in addition to the top-level eligible/$50.00 result. This pins the inclusive month-level boundary specifically, rather than leaving it to the top-level result.

- **Location**: ZIP `02148` (Middlesex County)
- **Household**: 2 people
- Person 1: `headOfHousehold`, born May 1990
- Person 2: `child`, born July 2025 (turning one this month)

**Why this matters**: The first-birthday month is the exact boundary the whole cutoff turns on, and it is the one month where the missing birth *day* makes the answer genuinely ambiguous. Scenario 9 is the paired case one month later, where the window has definitively closed.

---

### Scenario 9: Birth Pathway Expired — Ineligible
**What we're checking**: A child whose birth-pathway window has definitively closed is ineligible. The adoption pathway would require an adoption date the screener does not collect, so it cannot rescue this case.
**Expected**: Ineligible

**Internal assertion (required)**: the unit test must assert `birth_pathway_eligible == false` for Person 2, alongside the top-level ineligible/$0.00 result.

- **Location**: ZIP `02139` (Middlesex County)
- **Household**: 2 people
- Person 1: `headOfHousehold`, born March 1990
- Person 2: `child`, born June 2025 (birth pathway closed as of the frozen July 22, 2026 evaluation date — 13 months, one month past the window)

**Why this matters**: Paired with Scenario 8, this pins the boundary from both sides — the first-birthday month is inside the window, the following month is outside it. This is the direct regression test for MFB-1729.

---

### Scenario 10: Reported Bug Household — Two Children Under One Plus a Two-Year-Old
**What we're checking**: The MFB-1729 partner-reported household shape. Only the two children under one are valued; the two-year-old is excluded.
**Expected**: Eligible, $100.00

**Internal assertion (required)**: the unit test must assert `birth_pathway_eligible == true` for both under-one children and `false` for the two-year-old.

- **Location**: ZIP `02148` (Middlesex County)
- **Household**: 5 people
- Person 1: `headOfHousehold`, born March 1990
- Person 2: `domesticPartner`, born March 1991
- Person 3: `child`, born January 2026 (under one)
- Person 4: `fosterChild`, born October 2025 (under one)
- Person 5: `child`, born May 2024 (about two years old)

**Note on dates**: The originating ticket listed DOBs of 03/2025, 12/2025, and 07/2024, described relative to the live reporting date. Those are re-anchored here to the frozen July 22, 2026 evaluation date so the household keeps its intended shape (two under one, one past two).

**Why this matters**: This is the exact household a partner reported, where all three children were shown as eligible. It reproduces the multi-child, mixed-role, mixed-age shape end to end rather than testing the boundary in isolation.

---

## Data Gaps Without a Dedicated Scenario

Four real eligibility/program facts have no corresponding screener input at all, for any household, so no scenario can exercise them as a distinguishable input. Each is tracked here against the executable scenario that represents the calculator's behavior when the fact is unknown. Criteria 3 and 4 default inclusively (the calculator does not exclude on them); Criterion 2b does not, because its window turns on a date the screener never sees:

| Policy fact | Actual program result if fact were known | MFB calculator result (fact unknown) | Executable coverage |
|---|---|---|---|
| Child confirmed born/adopted outside Massachusetts | Ineligible | Eligible, $50 (Criterion 4 inclusive default) | Scenario 1 |
| Child confirmed to have already received a BabySteps contribution | Ineligible for a second contribution | Eligible, $50 — no household-level current-benefits field is read for this per-child fact (Criterion 3) | Scenario 1 |
| Older child adopted this year in a household with a newborn | Eligible, $100 (both children) | Eligible, $50 — only the newborn passes the age cutoff | Scenario 4 |
| Older child confirmed adopted within the preceding year | Eligible, $50, via the adoption pathway | **Ineligible** — the birth-pathway cutoff applies and no adoption input exists (Criterion 2b). Known false negative. | Scenario 9 |

If BabySteps is later added as a selectable current-benefits option for an unrelated product reason, it must not be wired into this calculator's eligibility logic without a fresh, source-supported per-child mapping.

## Research Sources

### MEFA / Fidelity

- [MEFA BabySteps Program Page](https://www.mefa.org/article/babysteps/) — Massachusetts residency, one-year birth/adoption window, January 1, 2020 start date, $50 value, no required family contribution, one contribution per child, adoption process.
- [MEFA BabySteps Adoption Verification and Participation Terms](https://www.mefa.org/babysteps-adoption-verification/) — "born or adopted in Massachusetts" language, residency at account opening, 365-day deadline framing, individual-account requirement, one contribution per beneficiary, funding-availability language.
- [MEFA U.Fund College Investing Plan – Overview](https://www.mefa.org/ways-to-save/mefa-u-fund/)
- [Fidelity 529 College Savings Plans – FAQs About Accounts](https://www.fidelity.com/529-plans/faqs-about-accounts)
- [New Fidelity Account Application — U.Fund College Investing Plan](https://www.fidelity.com/bin-public/060_www_fidelity_com/documents/applications/529_MA_application.pdf) — SSN/ITIN and Foreign Citizen pathway for both account owner and beneficiary.
- [Fidelity Massachusetts U.Fund College Investing Plan Fact Kit, January 2, 2026](https://www.fidelity.com/bin-public/060_www_fidelity_com/documents/529_MA_fact-kit.pdf) — BabySteps Program section; 30-calendar-day account-information-sharing opt-out.

### Mass.gov / Treasury

- [Mass.gov BabySteps Official Program Page](https://www.mass.gov/info-details/babysteps) — child must live in Massachusetts, born or adopted less than one year ago, named as U.Fund beneficiary before first birthday/adoption anniversary.
- [Massachusetts Treasury: "This 529 Day, Claim $50 for Your Child's Future with BabySteps" (2026)](https://www.mass.gov/news/this-529-day-claim-50-for-your-childs-future-with-babysteps) — residency at account opening; anyone (including relatives/friends) may open the individual account.
- [BabySteps Savings Plan – Frequently Asked Questions (Mass.gov PDF)](https://www.mass.gov/doc/babysteps-frequently-asked-questions/download)
- [BabySteps Information Booklet (Mass.gov PDF)](https://www.mass.gov/doc/babysteps-information-booklet/download) — adopted children of any age qualifying; January 1, 2020 program start date.

## Program Configuration

File: `ma_bsp_initial_config.json`
