# Missouri Weatherization Assistance Program (WAP) — Implementation Spec

## Program Details

- **Program**: Weatherization Assistance Program
- **State**: Missouri
- **White Label**: `mo`
- **Program Key**: `mo_wap`
- **Calculator**: MFB Custom
- **Policy Basis**: Active federal WAP guidance (WPN 25-3, 25-4, 22-5) and Missouri's Program Year 2025 WAP State Plan Master File
- **Research Date**: 2026-08-19

**Source currency**: DOE's live "[Poverty Income Guidelines](https://www.energy.gov/cmei/scep/wap/poverty-income-guidelines)" page shows WPN 25-3 (2025) as DOE's current active WAP guidance as of 2026-08-21; no newer notice has superseded it.

**Master File status**: Missouri DNR's [State Weatherization Plan](https://dnr.mo.gov/energy/what-were-doing/state-weatherization-plan) index lists Program Year 2025 as its operative published plan (Annual File, Master File, Attachments), with PY2024 retained for reference. DNR published a [draft PY2026 plan](https://dnr.mo.gov/document-search/draft-missouri-weatherization-assistance-program-state-plan-program-year-2026-attachments) for public comment in spring 2026, but no final PY2026 plan has superseded PY2025. This spec is built on the PY2025 Master File as Missouri's current published plan.

## Eligibility Criteria

### 1. Household must satisfy at least one income-eligibility pathway (OR test)

#### 1a. Countable annual income ≤ 200% of the current WAP poverty guideline for household size
- **Screener fields**: `household_size`, income streams for all members (subject to the exclusions and net-income handling in Criterion 2)
- **Comparator**: ≤ (inclusive of the exact boundary)
- **Current table** (WPN 25-3, contiguous U.S., effective January 17, 2025):

  | Household size | 200% of poverty |
  |---:|---:|
  | 1 | $31,300 |
  | 2 | $42,300 |
  | 3 | $53,300 |
  | 4 | $64,300 |
  | 5 | $75,300 |
  | 6 | $86,300 |
  | 7 | $97,300 |
  | 8 | $108,300 |
  | Each additional person | +$11,000 |

- Source: [DOE WPN 25-3](https://www.energy.gov/sites/default/files/2025-04/wap-wpn-25-3_041625_0.pdf): *"(1) Is at or below 200 percent of the poverty level..."*; table verbatim from the WPN 25-3 attachment.
- **Do not** substitute the general HHS/ACA poverty-guideline table used by other MFB programs — WAP uses its own DOE notice, which can differ in effective date.

#### 1b. Cash-assistance categorical eligibility
- Source: 10 CFR 440.3, per WPN 25-3: *"(2) Is the basis on which cash assistance payments have been paid during the preceding twelve-month period under Titles IV and XVI of the Social Security Act or applicable State or local law."* (Title IV = TANF, Title XVI = SSI; this is a general cash-assistance rule, not limited to SSI/TANF.) MO confirmation: [JFCAC](https://www.jfcac.org/weatherization.html): *"If you receive Supplemental Security Income (SSI) and/or Temporary Assistance for Needy Families (TANF), you are automatically eligible."*
- **Screener fields**: a household member currently reporting a nonzero `sSI` or `cashAssistance` income-stream amount — both base MFB income-stream types available to every white label, including MO (`configuration/white_labels/base.py`, not overridden by `mo.py`).
- Presence of either income-stream type with amount > $0 is sufficient positive evidence and overrides Criterion 1a for that household.
- **⚠️ Data Gap**: this captures current receipt only, not the 12-month lookback window WPN 25-3 describes. Handling: treat current receipt as sufficient positive evidence; do not model the lookback window or treat its absence as disproving eligibility (Criterion 1a and the other pathways still apply). Program description: surface that receiving SSI or cash assistance within the past 12 months — not just currently — can independently qualify a household for WAP.

#### 1c. LIHEAP-based eligibility
- **Screener mechanism**: `Screen.has_base_benefit("liheap")` — `mo_liheap` carries `base_program: liheap`, so the structural read matches it (and any future Missouri LIHEAP variant) without naming it.
- Missouri has elected this option. Source: MO WAP State Plan Master File (PY2025): *"Codified in 10 CFR 440.22(a)(3), the WAP already has a provision to allow the inclusion of households that are income eligible for the U.S. Department of Health and Human Services' (HHS) Low-Income Home Energy Assistance Program (LIHEAP)... Households that have been deemed income eligible for [LIHEAP] assistance may use their LIHEAP eligibility as verification of income."* Base federal option: 10 CFR 440.22(a)(3): *"If a Grantee elects, is the basis for eligibility for assistance under [LIHEAP], provided that such basis is at least 200 percent of the poverty level."*
- **Implemented.** `mo_liheap` is set `show_in_has_benefits_step: true` so a Missouri household can report LIHEAP receipt, and reported receipt bypasses the Criterion 1a income test. This widens eligibility rather than duplicating 1a: Missouri's LIHEAP standard is 60% SMI, which exceeds 200% of poverty at every household size (size 1: $34,080 vs $31,300; size 4: $65,532 vs $64,300), so the federal proviso — *"provided that such basis is at least 200 percent of the poverty level"* — is satisfied.
- **⚠️ Residual Data Gap**: the screener records LIHEAP *receipt*, while Missouri's plan admits households *income eligible* for LIHEAP whether or not they enrolled. Receipt is the inclusive half of that rule — it admits households Criterion 1a would reject and never rejects one Criterion 1a would admit — so an unenrolled but LIHEAP-income-eligible household is still evaluated on the other pathways. Program description: surface that existing LIHEAP eligibility can independently qualify a household for WAP.

#### 1d. HUD means-tested program eligibility (including Section 8)
- Missouri has elected this option (WPN 22-5). Source: MO Master File: *"Missouri intends to implement categorical eligibility as outlined in WPN 22-5 to support and enhance the guidance provided in WPN 24-3."* WPN 22-5 extends eligibility to HUD means-tested programs' income qualifications at or below 80% of Area Median Income; Master File examples include Community Development Block Grants, HOME, Lead Hazard Control & Healthy Homes, and Section 8 Housing Choice Voucher holders.
- **Screener mechanism**: `Screen.has_base_benefit("section_8")` (`screener/models.py`) — the correct, existing call for "does this household already receive a `section_8`-base-program benefit," used identically by `wa_hcv` and `tx_hcv`.
- **⚠️ Data Gap in practice**: Missouri has no `section_8`-base-program `Program` row today (no `mo_hcv`), and both the has-benefits step (`screener/views.py: HasBenefitsProgramsView`) and its write path (`screener/serializers.py: _write_current_benefits`) are scoped per white label — so no MO household can report Section 8/HCV receipt today, and `has_base_benefit("section_8")` evaluates to no-match regardless of actual receipt. Handling: wire the pathway now so it activates automatically if Missouri adds an HCV program later; until then, don't treat the absence of a recorded benefit as disproving eligibility. Other HUD means-tested programs (CDBG, HOME, OLHCHH) have no MFB representation at all and remain data gaps ⚠️ regardless. Program description: surface that qualifying HUD means-tested program eligibility (Section 8/HCV, CDBG, HOME, OLHCHH) can independently qualify a household for WAP, since none of these are checkable today for Missouri.

#### 1e. USDA means-tested program eligibility
- **Screener fields**: none available.
- Missouri has elected this option (WPN 25-4). Source: MO Master File: *"Weatherization Program Notice (WPN) 25-4, Expansion of Client Eligibility in the Weatherization Assistance Program... expanding WAP's categorical income eligibility to include U.S. Department of Agriculture's (USDA) means-tested program's income qualifications at or below 80% of Area Median Income"* — examples given: Section 521 Rental Assistance, Section 502 Direct, Section 533, and Section 504.
- **⚠️ Data Gap — Handling**: inclusive data gap — no MFB field. Program description: surface that qualifying USDA means-tested program eligibility can independently qualify a household for WAP.

**SNAP is not a pathway.** 10 CFR 440.22(a)(2) names only Title IV (TANF) and Title XVI (SSI) — not SNAP — and Missouri's Master File eligibility section doesn't mention SNAP as a basis. Do not add a SNAP check for `mo_wap`.

### 2. WAP-specific income counting rules apply to Criterion 1a
Source: [DOE WPN 25-3](https://www.energy.gov/sites/default/files/2025-04/wap-wpn-25-3_041625_0.pdf), Attachment "Definition of Income":

- **Base rule**: gross cash income for the household (Section A: *"Income means Cash Receipts earned and/or received by the applicant before taxes during applicable tax year(s) but not the Income Exclusions... Gross Income is to be used, not Net Income."*).
- **⚠️ Data Gap — Two explicit net exceptions**: (B.2) *"Net receipts from non-farm or farm self-employment (receipts from a person's own business or from an owned or rented farm after deductions for business or farm expenses)"*; (B.6) *"Net rental income and net royalties."* MFB has no field for business/farm or rental-property expenses (`expense_categories` in `configuration/white_labels/base.py` cover only housing, utilities, healthcare, and dependent care). Since WPN 25-3 requires *net* income here and MFB cannot compute net, using the reported gross figure as net would risk wrongly excluding a household whose true net income is lower. **Handling**: exclude the `selfEmployment`, `rental`, and `boarder` income-stream types entirely from `mo_wap` countable income. (`boarder` is grouped with `rental` under MFB's "property" income category and shares the same net-income problem, though WPN 25-3 doesn't name boarder income specifically.)
- **⚠️ Data Gap — Interest and dividends** (B.5, *"Dividends and/or interest"*) are countable at gross. **Capital gains** are excluded (C.1). MFB's `investment` income-stream type conflates capital gains with interest and dividends into a single figure, with no way to separate them. **Handling**: exclude the `investment` stream entirely from `mo_wap` countable income — the combined figure would otherwise over-count excluded capital gains.
- **Alimony** (B.3, *"Regular payments from social security, railroad retirement, unemployment compensation, strike benefits from union funds, worker's compensation, veteran's payments, training stipends, alimony, and military family allotments"*) is explicitly countable, at gross, with no netting question. MFB's `alimony` income-stream type maps directly — count it in full.
- **Child support** (Section E) is excluded whether received or paid: *"Child Support payments, whether received by the Payee or paid by the Payor, are not considered Sources of Income to be added to the payee income or deducted from the payor income."* MFB has both a `childSupport` income-stream type (received) and a `childSupport` expense type (paid). Both must be excluded entirely from the countable-income calculation — ignored, not deducted.
- **Gifts** (C.6, *"Gifts, loans, or lump-sum inheritances"*) are excluded. MFB's `gifts` income-stream type maps directly — exclude it.
- **Minors and full-time high-school students** (Section D.1): *"Do not count, or enter, earned income or unemployment compensation for minors under the age of 18 (or full-time high school students) at the time of the application."* MFB's `birth_year`/`birth_month` fields (validated into `HouseholdMember.birth_year_month`) give an exact under-18 test. MFB's `student_full_time` field is a general boolean with no high-school/college distinction (`screener/models.py`). **Handling**: use age < 18 as the exact branch (core scenario). For the high-school-student sub-clause, read `student and student_full_time` **at exactly age 18 only**. Reading the flag at every age would exclude a 45-year-old full-time student's wages outright, and past 18 the flag reaches adult education, GED programs and college far more often than high school — 18 is the one age where "still in high school" is the ordinary reading. **⚠️ Residual Data Gap**: a 19-plus high-school student's earned income is counted. Accepted as a rare enough case not to justify the over-exclusion the wider read would cause. The `student` conjunction matches `FullTimeCollegeStudentDependency`: `student_full_time` is only asked once `student` is ticked, but nothing enforces that server-side, so a direct API write can set it on a non-student.
- Partial-year income may be annualized (Section F) — standard MFB income intake already annualizes reported income; no `mo_wap`-specific handling needed.

### 3. Legal status — qualified aliens
Missouri's Master File states: *"the State of Missouri will follow guidance provided by [HHS] under [LIHEAP] to ensure that 'Qualified Aliens' are eligible for weatherization benefits,"* defining qualified aliens per PRWORA §431 (1996) as: lawful permanent residents, refugees, asylees, individuals paroled in for ≥1 year, individuals granted withholding of removal, conditional entrants, and certain domestic-abuse victims — *"eligible to receive assistance and services under the WAP program so long as they meet other WAP program requirements."*
- This is a real eligibility gate, implemented via MFB's existing legal-status configuration.
- **Committed mapping**: `legal_status_required = ["citizen", "refugee", "gc_5plus", "gc_5less", "otherWithWorkPermission"]`, excluding the generic `non_citizen` catch-all. All five committed values are valid members of MFB's legal-status enum (`programs/models.py: LegalStatus.is_user_selected`).

## Priority Criteria

10 CFR 440.16(b) sets five priority categories: *"Priority is given to identifying and providing weatherization assistance to: (1) Elderly persons; (2) Persons with disabilities; (3) Families with children; (4) High residential energy users; and (5) Households with a high energy burden."* MO confirmation (first three categories): [JFCAC](https://www.jfcac.org/weatherization.html): *"Priority is given to Missourians who are older than age of 60, those with disabilities, those with children in the home."*

This affects service order only, not eligibility or benefit value. Not modeled in the calculator; no test scenario required.

## Benefit Value

- **Estimated annual value**: $370 per eligible household
- **Cadence**: `estimated_annual` — an average annual heating/cooling cost-savings estimate, not a cash payment or the cost of the weatherization work itself
- No caps, offsets, phase-outs, proration, or interactions with other benefits
- MFB assigns the same $370 estimated annual value to every eligible result; there is no eligible-but-$0 result

**Source**: [MO DNR — Missouri Weatherization Assistance Program, PUB2832](https://dnr.mo.gov/document-search/missouri-weatherization-assistance-program-pub2832/pub2832): *"Weatherization saves, on average, $370 per house in heating and cooling costs, annually, at current prices."* Use `estimated_annual` because the $370 figure is an annual cost-savings estimate, not a payment or project cost.

## Acceptance Criteria

- [ ] A household with countable annual income (per Criterion 2's rules) ≤ the WPN 25-3 200%-of-poverty amount for its `household_size` is eligible for `mo_wap` at $370/year.
- [ ] A household with countable income exactly $1 over its household-size limit, with no current `sSI`/`cashAssistance` receipt or Section 8, is ineligible.
- [ ] Current `sSI` income-stream receipt independently establishes eligibility regardless of income.
- [ ] Current `cashAssistance` income-stream receipt independently establishes eligibility regardless of income.
- [ ] Reported LIHEAP receipt independently establishes eligibility regardless of income.
- [ ] SNAP receipt alone does not establish eligibility, even though it does for TX's implementation of this same program.
- [ ] Child support received or paid does not affect countable income.
- [ ] Gifts received do not affect countable income.
- [ ] Earned income and unemployment compensation of a household member under 18 are excluded from countable income.
- [ ] Self-employment, rental, boarder, and investment income streams are excluded from countable income (net-income data gap ⚠️; see Criterion 2).
- [ ] Alimony income is counted in full toward the income limit.
- [ ] Household income is aggregated across all members, not evaluated per-member against the 1-person limit.
- [ ] A household above the standard 8-person table correctly applies the +$11,000-per-additional-person extension.
- [ ] Every eligible result returns exactly $370/year (`estimated_annual`); every ineligible result returns no value.
- [ ] The calculator does not exclude a household based on dwelling type, prior-weatherization history, or priority status.

### Test scenario coverage matrix

| Eligibility/value branch | Scenario | Expected eligibility | Expected value |
|---|---|---:|---:|
| Standard income below limit | 1 | Eligible | $370 |
| Exact 200% boundary | 2 | Eligible | $370 |
| Just above limit, no pathway | 3 | Not eligible | — |
| Cash-assistance categorical (over-income) | 4 | Eligible | $370 |
| Cash-assistance categorical, second pathway | 5 | Eligible | $370 |
| Child support received excluded | 6 | Eligible | $370 |
| Minor wages + unemployment comp excluded | 7 | Eligible | $370 |
| Alimony counted, flips household over the limit | 8 | Not eligible | — |
| Income aggregated across members | 9 | Not eligible | — |
| Gifts excluded | 10 | Eligible | $370 |
| Child support paid not deducted | 11 | Not eligible | — |
| Household size > 8 | 12 | Eligible | $370 |
| Legal status filtering | — | N/A | Verified via `legal_status_required` config, not a household scenario (platform-level, not `mo_wap`-specific) |
| LIHEAP receipt categorical (over-income) | 13 | Eligible | $370 |
| ⚠️ USDA / HUD / LIHEAP-income-eligible-but-unenrolled / 12-month lookback / self-employment / rental / investment (data gaps) — SNAP (not a gap; not a pathway) | — | N/A | Committed inclusive handling per Criteria 1b–1e and 2 — no scenario |

## Test Scenarios

### Scenario 1: Standard Income Path — Single Adult Below the Limit
**Expected**: Eligible, $370/year
- ZIP `64108`, county `Jackson`, household size 1
- Person 1: Head of Household, birth month/year June 1986, wages $2,600/month ($31,200/year — below the $31,300 limit for 1 person)
- No cash-assistance categorical benefit
- **Why this matters**: confirms the verified WPN 25-3 threshold for a 1-person household (not the generic HHS figure, which would incorrectly show this household as further below/above threshold).

### Scenario 2: Exact 200% Boundary — Four-Person Household
**Expected**: Eligible, $370/year
- ZIP `65201`, county `Boone`, household size 4
- Person 1: Head of Household, birth month/year June 1988, wages $64,300/year exactly (the correct 4-person WPN 25-3 limit)
- Persons 2–4: Spouse and two children, no income
- **Why this matters**: validates the ≤ comparator at the exact WPN 25-3 boundary for a 4-person household.

### Scenario 3: Just Above the Income Limit, No Categorical Pathway
**Expected**: Not eligible
- ZIP `65802`, county `Greene`, household size 3
- Person 1: Head of Household, wages $53,400/year (just above the $53,300 3-person limit); Persons 2–3: no income
- No cash-assistance categorical benefit
- **Why this matters**: confirms the income ceiling is a hard gate at the verified WPN 25-3 threshold.

### Scenario 4: Cash-Assistance Categorical Eligibility Above the Income Limit
**Expected**: Eligible, $370/year
- ZIP `63101`, county `St. Louis City`, household size 2
- Person 1: Head of Household, wages $44,400/year (above the $42,300 2-person limit), plus a `cashAssistance` income stream of $500/month ($6,000/year)
- Person 2: Child, no income
- **Why this matters**: confirms current `cashAssistance` receipt independently overrides an income level that would otherwise fail.

### Scenario 5: SSI Categorical Eligibility Above the Income Limit
**Expected**: Eligible, $370/year
- ZIP `65616`, county `Taney`, household size 2
- Person 1: `sSI` income stream $900/month; Person 2 (spouse): wages $3,000/month (combined $46,800/year, above the $42,300 2-person limit)
- No `cashAssistance` income stream
- **Why this matters**: confirms `sSI` is tested as a pathway distinct from `cashAssistance`.

### Scenario 6: Child Support Received Is Excluded from Countable Income
**Expected**: Eligible, $370/year
- ZIP `63101`, county `St. Louis City`, household size 2
- Person 1: wages $42,000/year + child support received $12,000/year; Person 2: child, no income
- No categorical benefit
- **Calculation**: countable income is $42,000 (child support excluded), which is ≤ the $42,300 2-person limit; without the exclusion this household would incorrectly fail at $54,000.
- **Why this matters**: this is the one scenario in this suite that would produce the *wrong* eligibility result if Criterion 2's exclusion isn't implemented — the clearest test of that rule.

### Scenario 7: Minor's Earned Income and Unemployment Compensation Are Both Excluded from Countable Income
**Expected**: Eligible, $370/year
- ZIP `65201`, county `Boone`, household size 2
- Person 1: wages $42,000/year; Person 2: child, birth month/year June 2011 (age 15), wages $1,800/year plus unemployment compensation $600/year ($2,400/year total)
- No categorical benefit
- **Calculation**: countable income is $42,000 (both the minor's wages and unemployment compensation are excluded, per WPN 25-3's *"earned income or unemployment compensation for minors under the age of 18"*), ≤ the $42,300 limit.
- **Why this matters**: without this exclusion the household's income ($44,400) would incorrectly exceed the limit. Covers both income types the exclusion names, not wages alone.

### Scenario 8: Alimony Is Counted and Flips the Household Over the Limit
**Expected**: Not eligible
- ZIP `63101`, county `St. Louis City`, household size 1
- Person 1: wages $28,000/year, plus alimony income $5,000/year ($33,000/year total)
- No categorical benefit
- **Calculation**: wages alone ($28,000) are below the $31,300 limit, but WPN 25-3 counts alimony at gross (Section B.3), bringing the household to $33,000 — above the limit.
- **Why this matters**: proves the calculator sums a countable non-wage income stream rather than checking wages alone, and that alimony — unlike self-employment, rental, boarder, or investment income — has no netting ambiguity and is fully counted.

### Scenario 9: Income Aggregation Across Two Adults
**Expected**: Not eligible
- ZIP `65201`, county `Boone`, household size 2
- Person 1: wages $24,000/year; Person 2 (spouse): wages $20,000/year (each individually below the $31,300 1-person figure, combined $44,000/year against the $42,300 2-person limit)
- No categorical benefit
- **Why this matters**: WPN 25-3 requires income for *"the entire family living in the residence"* — none of the other scenarios prove that two members' incomes are actually summed rather than evaluated independently. A calculator that incorrectly checks each member against the 1-person limit would wrongly pass this household.

### Scenario 10: Gifts Are Excluded from Countable Income
**Expected**: Eligible, $370/year
- ZIP `64801`, county `Jasper`, household size 1
- Person 1: wages $31,000/year + a `gifts` income stream of $5,000/year
- No categorical benefit
- **Calculation**: countable income is $31,000 (gifts excluded per WPN 25-3 Section C.6), ≤ the $31,300 1-person limit; without the exclusion this household ($36,000) would incorrectly fail.
- **Why this matters**: `gifts` is a real, existing MFB income-stream type, so this is an executable regression guard, not a documentation-only note.

### Scenario 11: Child Support Paid Is Not Deducted from Countable Income
**Expected**: Not eligible
- ZIP `65802`, county `Greene`, household size 1
- Person 1: wages $32,000/year, plus a `childSupport` expense of $12,000/year
- No categorical benefit
- **Calculation**: countable income remains $32,000 — above the $31,300 1-person limit. WPN 25-3 Section E.2 bars deducting child support paid from income; a calculator that incorrectly treats the expense as a deduction would show $20,000 and wrongly pass this household.
- **Why this matters**: MFB has a real `childSupport` expense type, so this is the executable counterpart to Scenario 6's received-side exclusion.

### Scenario 12: Household Size Above 8 Applies the Per-Person Extension
**Expected**: Eligible, $370/year
- ZIP `64108`, county `Jackson`, household size 9
- Person 1: Head of Household, wages $119,300/year exactly (the 8-person limit of $108,300 plus the $11,000 per-additional-person extension for the 9th member); Persons 2–9: no income
- No categorical benefit
- **Why this matters**: confirms the +$11,000-per-additional-person rule is correctly applied above the table's explicit 8-person row, at the exact boundary.

### Scenario 13: LIHEAP Receipt Establishes Eligibility Above the Income Limit
**Expected**: Eligible, $370/year
- ZIP `63101`, county `St. Louis City`, household size 1
- Person 1: Head of Household, wages $34,000/year (above the $31,300 1-person limit, and within Missouri's 60% SMI LIHEAP standard of $34,080)
- Reports receiving LIHEAP on the "already have this benefit" step; no `sSI` or `cashAssistance` stream
- **Why this matters**: this is the band the LIHEAP pathway exists to cover — a household over 200% of poverty but inside Missouri's own LIHEAP standard, which 10 CFR 440.22(a)(3) admits and Criterion 1a alone would reject.

## Source Documentation

- [10 CFR 440.22 — Eligible dwelling units](https://www.ecfr.gov/current/title-10/chapter-II/subchapter-D/part-440/section-440.22)
- [10 CFR 440.16 — Minimum program requirements (priority)](https://www.law.cornell.edu/cfr/text/10/440.16)
- [42 U.S.C. § 6865(c)(2) — Limitations on financial assistance (15-year re-weatherization bar)](https://www.law.cornell.edu/uscode/text/42/6865)
- [DOE WPN 25-3 — 2025 Federal Poverty Guidelines and Definition of Income](https://www.energy.gov/sites/default/files/2025-04/wap-wpn-25-3_041625_0.pdf)
- [DOE — Poverty Income Guidelines (current-guidance page, checked 2026-08-21)](https://www.energy.gov/cmei/scep/wap/poverty-income-guidelines)
- [DOE WPN 25-4 — Expansion of Client Eligibility to Select USDA Programs](https://www.energy.gov/cmei/scep/wap/articles/weatherization-program-notice-25-4-expansion-client-eligibility-select-us)
- [DOE WPN 22-5 — Expansion of Client Eligibility (HUD)](https://www.energy.gov/cmei/scep/wap/articles/weatherization-program-notice-22-5-expansion-client-eligibility)
- Missouri WAP State Plan Master File, Program Year 2025 (Revision 0) — obtained via DNR document search; DNR's [State Weatherization Plan index](https://dnr.mo.gov/energy/what-were-doing/state-weatherization-plan)
- [MO DNR — Local Weatherization Agencies](https://dnr.mo.gov/energy/weatherization/local-agencies)
- [MO DNR — Missouri Weatherization Assistance Program, PUB2832](https://dnr.mo.gov/document-search/missouri-weatherization-assistance-program-pub2832/pub2832)
- [Jefferson Franklin Community Action Corporation — Weatherization Assistance Program](https://www.jfcac.org/weatherization.html)
- [DOE WAP Overview](https://www.energy.gov/scep/wap/weatherization-assistance-program)

## Config Decisions Not Sourced from a Missouri Citation

- **`estimated_application_time: "30-60 minutes"`** — committed MFB convention, not a Missouri-verified figure. DNR's WAP pages describe the intake process (contact local agency, complete forms, provide income documentation) but publish no application-time estimate, and Missouri's 18 local agencies may use different forms/intake processes. This value is borrowed from Colorado's live `cowap` production config (checked 2026-08-21) as the closest available WAP-family precedent, chosen over WA/TX's "1 - 2 hours" for its narrower range. If a Missouri-specific application/intake flow is later reviewed and this range doesn't hold, update this value and this note.
