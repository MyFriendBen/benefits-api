# Seattle Utility Discount Program (UDP) — Specification

- **Program**: Seattle Utility Discount Program (UDP)
- **State**: WA
- **White Label**: wa
- **Research Date**: 2026-05-13
- **Spec finalized**: 2026-05-14

## Eligibility Criteria

The eligibility logic is:

```
eligible = (
  Criterion 1 (Seattle residency)
  AND (
    Criterion 4 (SSI categorical)
    OR Criterion 5 (SNAP streamlined)
    OR (Criterion 2 AND Criterion 3)   # standard income pathway
  )
)
```

In plain English: a household must be in Seattle's SCL/SPU service area (Criterion 1) AND satisfy one financial pathway — SSI categorical (Criterion 4), SNAP streamlined (Criterion 5), or both 70% SMI income tests (Criteria 2 + 3).

### Criterion 1 — Seattle SCL/SPU customer (account in own name OR Voucher Program participant)

**Household must have a Seattle City Light and/or Seattle Public Utilities bill in their name, OR be enrolled in the UDP Voucher Program (for tenants whose landlord pays utilities). This requires the household to reside within the SCL/SPU service area.** ⚠️ *partial data gap*

- Screener fields:
   - `zipcode`
   - `county`

- Source: SCL DPP 500 P III-428 §4.1; SPU CS-700 §2.A and §3.B.5; seattle.gov/utilities UDP page ("Eligibility"); Seattle Municipal Code 21.49.040; SMC 21.76

- Notes:

   - **The legal test is account-based, not residence-based**: Per CS-700 §2.A and DPP III-428 §4.1, the applicant must be the primary SCL/SPU account holder or a Voucher Program tenant. Residency is a precondition, not the test itself.

   - **Screener proxy**: The screener can't verify account status (data gap), so we proxy with ZIP + county: **include if `county == "King County"` AND `zipcode IN <seattle_zip_list>`**. Non-customers who pass this filter are caught at application time. Inclusivity assumption: any qualifying Seattle household has utility access — directly or via Voucher.

   - **Seattle ZIP list for the calculator** — **52 ZIPs** that fall within Seattle city limits and plausibly have residential households (cross-referenced between USPS Seattle-named ZIPs and the seattle.gov Census 2010 Census Tracts and ZIP Code Boundaries map):

      ```text
      98101, 98102, 98103, 98104, 98105, 98106, 98107, 98108, 98109, 98111,
      98112, 98113, 98114, 98115, 98116, 98117, 98118, 98119, 98121, 98122,
      98124, 98125, 98126, 98127, 98129, 98131, 98133, 98134, 98136, 98138,
      98139, 98141, 98144, 98145, 98146, 98154, 98160, 98161, 98164, 98165,
      98170, 98174, 98175, 98177, 98178, 98181, 98185, 98190, 98191, 98194,
      98195, 98199
      ```

      Sources:
      - https://www.seattle.gov/documents/Departments/LaborStandards/2010CensusTractsandZipCodeBoundaries.pdf
      - USPS city lookup for "SEATTLE WA" (60 total USPS-Seattle ZIPs; this list is the residential-within-city-limits subset)

      **Excluded** (with rationale):
      - **8 USPS-Seattle-named ZIPs that fall outside Seattle city limits** (suburbs, not served by SCL/SPU): 98110 (Bainbridge Island), 98148 (Burien), 98155 (Lake Forest Park / Kenmore), 98158 (SeaTac), 98166 (Burien Three Tree Point), 98168 (Tukwila / unincorporated King County), 98188 (SeaTac), 98198 (Des Moines)

   - **Voucher Program for landlord-billed utilities** (DPP III-428 §5.1.5 / CS-700 §3.B.5): Tenants under a written lease whose landlord pays utilities can qualify if the property owner participates in UDP. Surface in description: "You must have an SCL/SPU bill in your name, OR live in a property where your landlord participates in the UDP Voucher Program."

   - **The list is still slightly over-inclusive**: Both service areas are bounded by Seattle city limits, but a few of the 52 ZIPs (98146 includes White Center; 98178 includes Skyway) extend slightly beyond. Application-stage verification catches affected households; over-inclusion is acceptable at the screener level.

   - **Suggested screener enhancement to close this data gap** (priority: HIGH): Under Expenses → Utilities, add two follow-up questions when a Utilities expense is entered:
      1. **Utility provider dropdown** (multi-select) — Seattle City Light, Seattle Public Utilities, Tacoma Public Utilities, Puget Sound Energy, Snohomish County PUD, Avista, Clark Public Utilities, Pacific Power, Other.
      2. **Account ownership** — "Whose name is the utility bill in?": My name / Spouse or partner's name / Landlord (utilities included in rent) / Other / Don't know.

      Also benefits future WA utility programs (Tacoma TPU, PSE, Snohomish PUD, Avista, Clark PUD discount programs) and flags Voucher-Program-eligible UDP candidates (households selecting "Landlord (utilities included in rent)").

   - **Authoritative sources for verifying the geographic filter**:
      - **Seattle city limits ZIP boundaries** (used for the list above): https://www.seattle.gov/documents/Departments/LaborStandards/2010CensusTractsandZipCodeBoundaries.pdf
      - **SCL / SPU service area map** (confirms service area = Seattle city limits): https://experience.arcgis.com/experience/95749d0993164eefa99300182e99bd43
      - **City of Seattle GIS Open Data Portal** (for point-in-polygon geocoded address checks if finer precision is needed later): https://data-seattlecitygis.opendata.arcgis.com/

### Criterion 2 — Annual income test

**Combined annual gross income of all adult (18+) household members must not exceed 70% of Washington State Median Income for the household size.**

- Screener fields:
   - `household_size`
   - Sum of `calc_gross_income("yearly", ["all"])` across `household_members[]` where `age >= 18`

- Source: SCL DPP 500 P III-428 §4.1; SPU CS-700 §2.B; seattle.gov/utilities UDP page ("Eligibility")

- 2026 annual limits (70% SMI, effective January 1, 2026, published by WA DSHS):

   | HH size | Annual    | HH size | Annual    |
   |---------|-----------|---------|-----------|
   | 1       | $51,228   | 6       | $130,032  |
   | 2       | $66,984   | 7       | $132,984  |
   | 3       | $82,740   | 8       | $135,936  |
   | 4       | $98,508   | 9       | $138,900  |
   | 5       | $114,264  | 10      | $141,852  |
   |         |           | +1      | +$2,964   |

- Notes:

   - **Adults only**: Only income from members age 18+ counts; minor income is exempted (DPP III-428 §5.6.2).

   - **MFB caps `household_size` at 8**; the program supports 9+ via the +$2,964/yr per-member step. Calculator must implement the linear extension for HH > 8.

   - **SMI updates annually**: WA DSHS publishes new figures each January. Calculator must reference a version-controlled SMI table, not hard-coded numbers.

   - **Income types included** (DPP III-428 §5.6.1): wages, self-employment, SSI, SSDI, Social Security retirement, TANF, child support received, pensions, ABD payments, foster/adoption support, unemployment, alimony, tips, rental income from non-owner-occupied properties, refugee support, scholarships/grants, third-party shelter payments, work/study, lump-sum income (averaged over 12 months).

   - **Income types exempted** (DPP III-428 §5.6.2): food assistance, loans, protective payee income, minor income, internal household rent.

   - **Allowable deductions** (DPP III-428 §5.6.3 — not modelable in screener): business expenses against self-employment income (only if home business <51%), education expenses against scholarship income, Medicare Part B premium against SS/SSI/SSDI. Calculator uses gross income (under-inclusivity favoring the applicant).

### Criterion 3 — Monthly income test

**In addition to the annual test, combined monthly gross income of adult (18+) household members in the one-month period preceding application must not exceed the 70% SMI monthly limit for the household size.**

- Screener fields:
   - `household_size`
   - Sum of `calc_gross_income("monthly", ["all"])` across `household_members[]` where `age >= 18`

- Source: seattle.gov/utilities UDP page ("Eligibility" — explicit dual test); SPU CS-700 §5 (1-month measurement period); DPP III-428 §5.6

- 2026 monthly limits (70% SMI, effective January 1, 2026):

   | HH size | Monthly | HH size | Monthly |
   |---------|---------|---------|---------|
   | 1       | $4,269  | 6       | $10,836 |
   | 2       | $5,582  | 7       | $11,082 |
   | 3       | $6,895  | 8       | $11,328 |
   | 4       | $8,209  | 9       | $11,575 |
   | 5       | $9,522  | 10      | $11,821 |
   |         |         | +1      | +$247   |

- Notes:

   - **Why two income tests?** The program requires BOTH to pass — catching both borderline-annual-with-high-month and borderline-monthly-with-steady-annual cases.

   - **For screener purposes** the two tests collapse into one: yearly limit = monthly limit × 12 exactly per the seattle.gov tables, and the screener captures income as an ongoing pay rate (not a 1-month-prior snapshot). Note this approximation in calculator comments.

   - **Seasonal income**: Per DPP III-428 §5.6, seasonal-income applicants may use a 12-month annualized period instead of 1-month lookback. Not screener-relevant.

   - **Lump-sum income** (DPP III-428 §5.6): One-time payments (gifts, inheritance, insurance) are averaged over 12 months by the program; not screener-capturable. Inclusivity assumption: assume any income entered is ongoing.

### Criterion 4 — SSI categorical pathway

**Any adult household member receives Supplemental Security Income (SSI) under Title 42 USC §§1381–1383. This pathway bypasses Criteria 2 and 3 (the income tests).**

- Screener fields:
   - Any `household_members[].income_streams[].type == "sSI"`

- Source: SCL DPP 500 P III-428 §4.1; SPU CS-700 §2.B

- Notes:

   - **True categorical eligibility**: Any SSI recipient in the household qualifies the entire household regardless of income. Implement as an OR pathway with Criteria 2+3.

   - **SSI vs SSDI**: The pathway is SSI only (42 USC §§1381–1383). SSDI (Title II disability) does NOT confer categorical eligibility. Filter on `income_streams[].type == "sSI"`, not `"sSID"`.

   - **State SSI supplements**: WA has no state SSI supplement (repealed). Screener doesn't distinguish federal vs state SSI — moot.

### Criterion 5 — SNAP streamlined pathway

**Household is currently certified for SNAP (federal Supplemental Nutrition Assistance Program) or WA Basic Food Assistance. This pathway is treated as proof of income eligibility (no further income verification required) and effectively bypasses Criteria 2 and 3 for screener purposes.**

- Screener fields:
   - `has_benefit("snap")`

- Source: SCL DPP 500 P III-428 §5.1.2; SPU CS-700 §3.B.2; seattle.gov/utilities UDP page

- Notes:

   - **Legal distinction**: Legally a "Streamlined Application" path, not true categorical eligibility — the applicant still meets the income test; UDP just accepts SNAP certification as proof. For screener purposes it functions like categorical eligibility (regardless of independently captured income).

   - **Why it's screener-safe**: SNAP's WA threshold (~130% FPL with deductions) is more restrictive than 70% SMI, so any SNAP-enrolled household passes the UDP income test. Treating SNAP as a pathway can't create false positives.

   - **WA Basic Food = SNAP**: Same program, WA's name. Policy docs reference both interchangeably. MFB's `has_benefit("snap")` captures both — no separate `wa_basic_food` current benefit needed.

## Ineligibility / Exclusions

These conditions disqualify a household even if all positive eligibility criteria are met. Both are data gaps in the MFB screener — calculator should assume neither applies (inclusivity assumption) and surface in the program description.

1. **Mixed-load accounts (single-meter multi-unit)** ⚠️ *data gap*
   - Single-meter mother-in-law apartments and duplexes are ineligible unless all units within the meter apply as one combined household.
   - Source: SCL DPP III-428 §5.5.2.1; SPU CS-700 §4.B
   - Notes: Screener captures no signal about meter sharing. Inclusivity assumption: assume the household has its own meter. Description should note: "Households sharing a single utility meter with other units may need to apply jointly."

2. **51%+ home business use** ⚠️ *data gap*
   - Self-employed applicants whose IRS Form 8829 shows 51% or more of their home is used for business (e.g., in-home beauty salons, daycares, mechanic shops) are ineligible.
   - Source: SCL DPP III-428 §5.5.2.2; SPU CS-700 §4.B
   - Notes: Screener captures no business-use-of-home percentage. Inclusivity assumption: assume <51% business use. Description should note: "Self-employed people who use over half their home for business may not qualify." (Matches the description's actual phrasing.)

## Priority Criteria

**None.** Seattle UDP does not prioritize by income tier, age, disability status, disconnection risk, or other factors. Applications are processed first-in-first-out with a 21-business-day determination target (DPP III-428 §5.2.3 / CS-700 §3.C.4).

Senior-only (65+) and auto-enrolled households recertify less frequently (3 and 5 years respectively, vs. 2 years standard per DPP III-428 §5.3.1 / CS-700 §3.D.1) — a recertification convenience, not initial-service priority.

Households facing imminent disconnection should be directed to Seattle's separate **Emergency Bill Assistance Program** (SCL) and **Emergency Assistance Program** (SPU).

## Benefit Value

### Methodology

Two distinct benefit structures depending on household type:

#### Standard household (account in own name)

- **60% discount on Seattle City Light electric bills**
- **50% discount on Seattle Public Utilities water/sewer/garbage bills**

**Citation**: SCL DPP 500 P III-428 §1.1 (60% SCL); SPU CS-700 §1; seattle.gov/utilities UDP page (60% SCL + 50% SPU); seattle.gov/human-services UDP page.

#### Tenant with landlord-paid SPU, own SCL bill

Fixed monthly Utility Credits applied to the SCL bill (effective January 1, 2026 for water/sewer/drainage; April 1, 2026 for garbage/yard waste):

| Housing type     | Water  | Sewer  | Drainage | Garbage | Yard Waste | Monthly total |
|------------------|--------|--------|----------|---------|------------|---------------|
| Single-family    | $25.36 | $43.39 | $29.45   | $23.25  | $7.55      | **$129.00**   |
| Duplex           | $25.36 | $43.39 | $14.72   | $23.25  | $7.55      | **$114.27**   |
| Multi-family     | $14.19 | $30.27 | $3.15    | $18.95  | $7.55      | **$74.11**    |

**Citation**: seattle.gov/utilities UDP page ("Not directly billed for your SPU utilities?" section).

### Ancillary benefits (in-kind, not monetized in calculator)

- 2 free Special Item Collections per year (single-family households with SPU bill in name)
- 2 free Transfer Station Passes per year (UDP-enrolled, primary account holder at UDP-enrolled address)

**Citation**: seattle.gov/utilities UDP page ("Additional Benefits" section).

### Calculator value methodology

Use **$732/year** as the calculator value for eligible households. This is the **average annual savings figure** published on the seattle.gov/human-services UDP page. An informed estimate, since the screener doesn't capture individual utility bills.

- `value_format`: `null` (monthly default — the frontend will divide by 12 to display $61/month)
- Calculator output: `732` (annual) for any household passing eligibility

Likely conservative for larger households and slightly high for the smallest. Acceptable for v1 — refine if MFB adds utility-expense fields.

For the landlord-paid utility credit path: the screener can't identify these households, so skip the separate path in v1. The $732/year ($61/month displayed) is a reasonable default.

## Test Scenarios

### Scenario 1 — Eligible, standard income path, single adult

**What we're checking**: Golden-path single-adult Seattle household, income clearly below 70% SMI, no categorical pathway needed.

**Expected**: Eligible, value $732/year

**Steps**:
- ZIP 98103 (Wallingford), King County, HH=1
- Person 1: age 35, headOfHousehold, wages $2,000/mo ($24,000/yr) — well under $4,269/mo and $51,228/yr limits
- No current benefits

**Covers**: Criteria 1, 2, 3 succeed via income pathway.

**Why this matters**: The most common UDP applicant profile — working-age adult with modest wages. If this fails, the screener produces false negatives for the typical user, making the calculator unreliable for most qualifying households.

---

### Scenario 2 — Eligible at boundary, household of 4 exactly at limit

**What we're checking**: Income at the 70% SMI ceiling for HH=4 — boundary inclusion test.

**Expected**: Eligible, value $732/year

**Steps**:
- ZIP 98118, King County, HH=4
- Person 1: age 40, headOfHousehold, wages $4,500/mo
- Person 2: age 37, spouse, wages $3,709/mo (total $8,209 = exactly the HH=4 limit)
- Persons 3 & 4: minor children (ages 9 and 6)

**Covers**: Boundary inclusion at ≤70% SMI; multi-member adult income aggregation; minor presence does not contribute to income.

**Why this matters**: The threshold uses "at or below," so households at the limit must qualify. Off-by-one logic (`<` instead of `<=`) would silently exclude families at the cutoff — a small bug with outsized impact, since households near the limit are exactly who the program targets.

---

### Scenario 3 — Ineligible, income just above 70% SMI

**What we're checking**: Income $1/mo above the HH=4 limit — boundary exclusion test.

**Expected**: Ineligible

**Steps**:
- ZIP 98118, King County, HH=4
- Person 1: age 40, headOfHousehold, wages $4,500/mo
- Person 2: age 37, spouse, wages $3,710/mo (total $8,210 = $1 over limit)
- Persons 3 & 4: minor children
- No SSI, no SNAP

**Covers**: Confirms the income ceiling fails correctly; complements Scenario 2.

**Why this matters**: Validates the income ceiling is enforced. A regression that loosens the check would over-extend the program to non-qualifying households — eroding trust when they're denied at application and creating downstream work for SCL/SPU staff.

---

### Scenario 4 — Eligible via SSI categorical pathway (income above threshold)

**What we're checking**: SSI recipient bypasses the income tests even when household income exceeds 70% SMI.

**Expected**: Eligible, value $732/year

**Steps**:
- ZIP 98109, King County, HH=2
- Person 1: age 67, headOfHousehold, SSI $943/mo, wages $4,000/mo
- Person 2: age 65, spouse, Social Security retirement $2,000/mo
- Total adult monthly income: $6,943 (> $5,582 HH=2 limit) BUT SSI present

**Covers**: SSI categorical pathway (Criterion 4) bypasses Criteria 2 and 3.

**Why this matters**: Many seniors and people with disabilities receive SSI plus additional income (part-time work, spouse, family support) that pushes them over 70% SMI. Missing this pathway would systematically exclude a demographic the program is designed to serve — one particularly vulnerable to shutoff.

---

### Scenario 5 — Eligible via SNAP streamlined pathway (income above threshold)

**What we're checking**: SNAP enrollment bypasses the income tests.

**Expected**: Eligible, value $732/year

**Steps**:
- ZIP 98144, King County, HH=3
- Person 1: age 35, headOfHousehold, wages $5,000/mo
- Person 2: age 33, spouse, wages $2,500/mo
- Person 3: age 8, child
- Total adult monthly income: $7,500 (> $6,895 HH=3 limit) BUT receiving SNAP (`has_benefit("snap")`)

**Covers**: SNAP streamlined pathway (Criterion 5) bypasses Criteria 2 and 3.

**Why this matters**: SNAP recipients are the audience UDP wants to reach with minimal paperwork — Seattle built the streamlined application for them. A broken pathway would tell SNAP households they don't qualify, defeating the design and sending the wrong message to families already juggling multiple benefit systems.

---

### Scenario 6 — Ineligible, outside Seattle service area

**What we're checking**: A low-income WA household outside Seattle is excluded on residency, even with categorical pathway active.

**Expected**: Ineligible

**Steps**:
- ZIP 98003 (Federal Way), King County, HH=2
- Person 1: age 40, headOfHousehold, wages $1,000/mo
- Person 2: age 38, spouse, no income
- receiving SNAP — `has_benefit("snap")` (testing that categorical pathway alone does not override residency)

**Covers**: Criterion 1 fails; categorical pathways do not override location.

**Why this matters**: Seattle UDP is funded by Seattle ratepayers and serves only SCL/SPU territory. Surfacing it to non-Seattle households (Tacoma, Federal Way, Bellevue) creates false hope and undermines the screener's credibility. This also guards against a logic error where categorical pathways bypass the geographic check.

---

### Scenario 7 — Eligible, multi-generational household with adult-only income aggregation

**What we're checking**: Multi-generational household; senior's SS retirement counts in adult income aggregation; minor presence does not contribute.

**Expected**: Eligible, value $732/year

**Steps**:
- ZIP 98103, King County, HH=4
- Person 1: age 38, headOfHousehold, wages $2,800/mo
- Person 2: age 71, parent of HoH, Social Security retirement $1,100/mo
- Person 3: age 35, spouse, no income
- Person 4: age 8, child
- Total adult monthly income: $3,900 (well under $8,209 HH=4 limit)

**Covers**: Multi-generational household; adult-only aggregation; seniors count toward adult income.

**Why this matters**: Multi-generational households are common in UDP's target demographic — immigrant families, those caring for elderly parents, adult children with retired parents. The calculator must correctly handle the mix without misclassifying members or miscounting income.

---

### Scenario 8 — Eligible, minor's income is exempted

**What we're checking**: Working teenager's income is exempted from household total per DPP III-428 §5.6.2.

**Expected**: Eligible, value $732/year

**Steps**:
- ZIP 98115, King County, HH=2
- Person 1: age 42, headOfHousehold, wages $4,000/mo
- Person 2: age 17, child, wages $1,800/mo
- Naive household total: $5,800/mo (> $5,582 HH=2 limit)
- Correct adult-only total: $4,000/mo (< $5,582 limit) → eligible

**Covers**: Adult-only income filter; minor income exemption.

**Why this matters**: A working teenager (part-time job, summer earnings, gig work) is increasingly common as Seattle's cost of living rises. The program explicitly exempts minor income to protect family eligibility. A bug here means an after-school job could disqualify a family from a $700+/year benefit.

---

### Scenario 9 — Eligible, zero-income household via SNAP

**What we're checking**: $0 income households are not rejected; SNAP path works at zero income.

**Expected**: Eligible, value $732/year

**Steps**:
- ZIP 98144, King County, HH=1
- Person 1: age 29, headOfHousehold, no income
- receiving SNAP (`has_benefit("snap")`)

**Covers**: Zero-income edge case; SNAP path works independent of income.

**Why this matters**: Zero-income households (between jobs, displaced, in crisis) are at highest risk of shutoff and are a top program priority. The SNAP categorical pathway catches them. This also guards against a common defensive-coding bug: null-handling errors when summing an empty income_streams array.

---

### Scenario 10 — Eligible, large household with multiple minor children

**What we're checking**: Multi-adult, multi-child household using a mid-range SMI table lookup (HH=6); guards against a cap bug that truncates the table at HH=4.

**Expected**: Eligible, value $732/year

**Steps**:
- ZIP 98118, King County, HH=6
- Person 1: age 40, headOfHousehold, wages $5,000/mo
- Person 2: age 38, spouse, wages $4,500/mo
- Persons 3, 4, 5, 6: minor children (ages 12, 10, 6, 3)
- Total adult monthly income: $9,500 (< $10,836 HH=6 limit)

**Covers**: Correct HH=6 table lookup ($10,836/mo); multi-child household; adult-only income aggregation.

**Note**: The per-member SMI extension (`SMI_70_ANNUAL[10] + (size - 10) * 2,964`) activates only for HH > 10. MFB caps household size at 8, so the extension code is never reachable via the screener and is not covered by any spec scenario.

**Why this matters**: Large families have higher utility costs and are often among the lowest-income-per-capita households. A bug that caps the HH-size lookup at 4 (a common copy-paste error when porting other programs' logic) would exclude families of 5+ — punishing those with the heaviest utility burden.

---

## Sources

Primary sources (.gov / governing policy documents):

1. **SCL Department Policy & Procedure 500 P III-428** — https://clerk.seattle.gov/~CFS/CF_320280.pdf
2. **SPU Director's Rule CS-700** — https://www.seattle.gov/documents/Departments/SPU/AboutUs/Policies-Directors-Rules/accounts/CS-700_Utility-Discounts.pdf
3. **Seattle UDP — Seattle Public Utilities** — https://www.seattle.gov/utilities/your-services/discounts-and-incentives/utility-discount-program
4. **Seattle UDP — Human Services Department** — https://www.seattle.gov/human-services/services-and-programs/utility-discount-program
5. **Seattle UAP Quick Start Guide** — https://www.seattle.gov/documents/Departments/HumanServices/UtilityDiscountProgram/UAP-Quick-Start-Guide.pdf

Statutory authority:

- **Seattle Municipal Code 21.49.040** (SCL Residential Rate Assistance ordinance)
- **Seattle Municipal Code 21.76** (SPU Residential Rate Assistance ordinance)
- **City of Seattle Ordinance 125171** (Electric Rates and Provisions)
