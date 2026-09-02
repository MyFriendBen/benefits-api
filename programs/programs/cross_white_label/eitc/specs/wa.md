# Implement Earned Income Tax Credit (EITC) — WA Program

## Program Details

- **Program**: Earned Income Tax Credit (EITC)
- **State**: WA (federal program, configured under WA white label)
- **White Label**: wa
- **Research Date**: 2026-03-31
- **Tax Year**: 2025 (returns filed in 2026)

## Program Note

The EITC is a federal refundable tax credit administered by the IRS for working individuals and families with low to moderate earned income. Configured under the `wa` white label. Washington's Working Families Tax Credit (WFTC) is a separate state tax credit/refund program with different rules, including ITIN eligibility, and should be implemented separately.

## Eligibility Criteria

1. **Must have earned income**
   - Includes: wages, salaries, tips, net self-employment income, union strike benefits, disability retirement benefits received **before** minimum retirement age, clergy housing allowance (as SE income).
   - Excludes: Social Security retirement, unemployment compensation, alimony, pension/annuity income, rental income, investment income, SSDI, SSI, military disability pensions, VA rehabilitation payments, disability insurance payments where the filer paid the premium, post-MRA disability retirement, workers' compensation, nontaxable foster care payments, and earnings while incarcerated.
   - Special elections: military filers may elect to include nontaxable combat pay; filers receiving Medicaid waiver payments per Notice 2014-7 may elect to include or exclude.
   - Screener fields:
     - `income_streams[].type` / `income_streams[].category` for EITC-earned income types
     - Implementation should start with `calc_gross_income("yearly", ["wages", "selfEmployment"])` for cleanly captured earned income, then document any tax-specific earned-income items that are not separately captured (for example, nontaxable combat pay election, Medicaid waiver payment election, clergy housing, and pre-minimum-retirement-age disability retirement).
   - Notes: Excluded income types must not flow into the earned-income calculation even if captured under generic categories. Do not count Social Security retirement, unemployment, SSI/SSDI, pension, alimony, rental, or investment income as earned income.
   - Source: 26 U.S.C. § 32(c)(2); IRS Pub 596 Rule 7; [Disability and the EITC](https://www.irs.gov/credits-deductions/individuals/earned-income-tax-credit/disability-and-the-earned-income-tax-credit-eitc); [Military and Clergy Rules](https://www.irs.gov/credits-deductions/individuals/earned-income-tax-credit/military-and-clergy-rules-for-the-earned-income-tax-credit)

2. **Adjusted Gross Income (AGI) must be below income thresholds based on filing status and qualifying child count (Tax Year 2025)**
   - Thresholds by filing status and number of qualifying children:

     | Filing Status               | 0 Children | 1 Child  | 2 Children | 3+ Children |
     |-----------------------------|------------|----------|------------|-------------|
     | Single / HOH / qualifying MFS / QSS | $19,104    | $50,434  | $57,310    | $61,555     |
     | Married Filing Jointly (MFJ)| $26,214    | $57,554  | $64,430    | $68,675     |

   - **QSS / qualifying MFS note**: Qualifying Surviving Spouse uses the Single/HOH column (not MFJ). A married person filing separately only belongs in this column if they meet the separated-spouse exception in criterion 5. QSS = recently widowed filer (spouse died in either of the 2 prior tax years) with a dependent child living with them all year.
   - Screener fields:
     - `income_streams` for the filer and spouse, if MFJ
     - `screen.num_children()`
     - `screen.is_joint()`
   - Implementation note: EITC uses the tax filer/spouse AGI and earned income, not broad household income from every person listed in the screener. Do not include income from a domestic partner, elderly parent, or other non-spouse household member in the EITC income test unless that income belongs to the filer/spouse.
   - Source: 26 U.S.C. § 32(b); IRS Pub 596 Rule 1; IRS EITC Income Limits Tables

3. **Earned income must also independently be below the same income thresholds**
   - Both AGI and earned income must each fall below the applicable threshold from criterion 2.
   - The credit's phase-out (see Benefit Value) is calculated against the **greater of AGI or earned income** per 26 U.S.C. § 32(a)(2)(B).
   - Screener fields:
     - `income_streams[].type` / `income_streams[].category` for filer/spouse EITC-earned income types
     - `screen.num_children()`
     - `screen.is_joint()`
   - Implementation note: Use the same filer/spouse income unit as criterion 2. This matters for multigenerational households where another adult has income that should not be part of the tax filer's EITC calculation.
   - Source: 26 U.S.C. § 32(a)(2)(B); IRS Pub 596 Rule 15

4. **Investment income must not exceed $11,950 (Tax Year 2025)**
   - Includes: taxable and tax-exempt interest, dividends, capital gains, net rental/royalty income, passive activity income.
   - The screener captures investment income as a distinct income type, so this is cleanly evaluable.
   - Screener fields:
     - `income_streams[].type == investment`
   - Source: 26 U.S.C. § 32(i); IRS Pub 596 Rule 6

5. **Married filers generally must file jointly unless the separated-spouse exception applies** ⚠️ *data gap*
   - Exception (TY2021 onward): A married filer not filing jointly may still claim EITC if they had a qualifying child who lived with them more than half the year AND either (a) lived apart from their spouse for the last 6 months of the year, OR (b) is legally separated under state law via a written separation agreement or decree of separate maintenance and did not live in the same household as their spouse at year-end.
   - **Data gap**: The screener infers filing status from relationship structure. Single, HOH, QSS, and MFJ can be proxied, but MFS cannot be represented directly. A married couple with both spouses in-household is treated as MFJ, which may create a false positive if they actually file separately. The separated-spouse exception also cannot be evaluated because the screener does not capture whether spouses lived apart for the last 6 months or were legally separated at year-end. See Data Gap #19.
   - **Suggested screener improvement**: One conditional question shown only to married households — "Do you and your spouse plan to file your taxes together (jointly) or separately?" Resolves both this gap and Data Gap #19.
   - Screener fields:
     - `screen.is_joint()` (identifies MFJ vs. single/HOH; cannot detect MFS)
     - `relationship` (head + spouse signals MFJ)
   - Source: 26 U.S.C. § 32(d); IRS Pub 596 Rule 3

6. **Must be a U.S. citizen or resident alien for the entire tax year**
   - "Resident alien" is broad (green card or substantial presence test), so this rule alone doesn't exclude any MFB legal-status value. Practical ineligibility for non-citizens is driven by the SSN-validity rule (criterion 16).
   - `legal_status_required`: all 6 base values — `['citizen', 'non_citizen', 'refugee', 'gc_5plus', 'gc_5less', 'otherWithWorkPermission']`.
   - Source: 26 U.S.C. § 32(c)(1)(D); IRS Pub 596 Rule 4

7. **Cannot file Form 2555 (Foreign Earned Income Exclusion)** ⚠️ *data gap*
   - Affects U.S. citizens and resident aliens working abroad who exclude foreign earned income.
   - Screener fields: none
   - Notes: We assume households meet this requirement; verified at filing. Narrow population.
   - Source: 26 U.S.C. § 32(c)(1)(A)(ii); IRS Pub 596 Rule 5

8. **Age requirement for filers WITHOUT qualifying children: Must be at least 25 and under 65 at end of tax year** ⚠️ *precision data gap*
   - Applies only when claiming EITC with no qualifying children.
   - **MFJ exception**: At least one spouse must meet the age requirement (25–64 at end of tax year); the other spouse can be any adult age.
   - **Precision gap**: The IRS rule applies at end of tax year (Dec 31). The calculator must compute age from `birth_month` and `birth_year` against December 31 of the configured tax year. Relying on current derived age can create errors, so a user filing in early 2026 who is currently 25 may have been 24 at end of TY2025 — a false positive. Evaluate age against December 31 of the configured tax `year`.
   - Screener fields:
     - `birth_month` and `birth_year` (head of household)
     - `birth_month` and `birth_year` (spouse, if MFJ)
     - `screen.num_children()`
     - `screen.is_joint()`
   - Source: 26 U.S.C. § 32(c)(1)(A)(ii)(II); IRS Pub 596 Rule 11; [IRS Who Qualifies for EITC – Childless filer rules](https://www.irs.gov/credits-deductions/individuals/earned-income-tax-credit/who-qualifies-for-the-earned-income-tax-credit-eitc#without)

9. **Qualifying child — Relationship test**
   - Must be the filer's son, daughter, stepchild, adopted child, foster child, brother, sister, half-brother, half-sister, stepbrother, stepsister, or a descendant of any of these (e.g., grandchild, niece, nephew).
   - **Adopted child**: must be lawfully placed for legal adoption (pre-finalization placements count). The screener's "Child" option covers biological and adopted children identically.
   - **Foster child**: must be placed by a state/local government agency, an Indian tribal government, a tax-exempt org licensed by a state or tribe, or a court order. Informal arrangements don't qualify. ⚠️ *Precision data gap*: the `fosterChild` option conflates formal foster placements with kinship arrangements that may not meet the IRS requirement, producing false positives for kinship caregivers without formal placement.
   - ⚠️ *Precision data gap — distant relatives*: IRS-qualifying relationships include nieces, nephews, half-siblings, and great-grandchildren. These fall under the screener's `other` relationship option, which also includes non-qualifying relationships (aunts, cousins, unrelated members). We assume members under `other` who are younger than the filer are NOT qualifying children — producing false negatives for caregivers raising nieces, nephews, or half-siblings.
   - **Suggested screener improvements**: (a) distinguish formal `fosterChild` placements from informal kinship care; (b) add a follow-up under `other` — "Is this person your niece, nephew, half-sibling, or another descendant relationship such as great-grandchild?" Cross-program value beyond EITC.
   - Screener fields:
     - `relationship`
   - Source: 26 U.S.C. § 32(c)(3)(B); IRS Pub 596 Rule 8 (Relationship Test); [Qualifying Child Rules](https://www.irs.gov/credits-deductions/individuals/earned-income-tax-credit/qualifying-child-rules)

10. **Qualifying child — Age test**
    - Must be under age 19 at end of tax year, OR under age 24 if a full-time student, OR any age if permanently and totally disabled.
    - AND must be younger than the filer (or spouse, if MFJ).
    - **Full-time student precision gap**: IRS requires the qualifying child to be a full-time student for at least 5 months of the tax year. The screener example/reference appears to capture student status and a `student_half_time_or_more` follow-up, which is broader than the IRS full-time standard. If the active codebase has a true `student_full_time` field, use that. Otherwise, use `student_half_time_or_more` only as an inclusive proxy and flag the potential false positive.
    - ⚠️ *Permanently and totally disabled (precision data gap)*: IRS standard is strict — unable to engage in any substantial gainful activity due to a physical/mental condition, with a doctor attesting the condition has lasted, will last, or can lead to death (≥1 year). The screener has two relevant flags: (1) generic "unable to work" disability (broader than IRS, over-includes) and (2) "condition lasting/expected to last more than 12 months" (closer match). Prefer the 12-month-condition flag for the "any age if disabled" path.
    - Screener fields:
      - `birth_month` and `birth_year` (qualifying child + filer + spouse for end-of-tax-year age and younger-than-filer comparison)
      - `student_full_time` if available; otherwise `student_half_time_or_more` as an inclusive proxy with a precision-gap note
      - `long_term_disability` for the 12-month-condition proxy; `disabled` is broader and should only be used with caution
    - Source: 26 U.S.C. § 32(c)(3)(C) and § 152(c)(3)(A); IRS Pub 596 Rule 8 (Age Test); [Qualifying Child Rules](https://www.irs.gov/credits-deductions/individuals/earned-income-tax-credit/qualifying-child-rules); [Disability and the EITC](https://www.irs.gov/credits-deductions/individuals/earned-income-tax-credit/disability-and-the-earned-income-tax-credit-eitc)

11. **Qualifying child — Residency test** ⚠️ *precision data gap*
    - Must have lived with the filer in the United States for more than half the tax year.
    - **"United States"** = the 50 states, DC, and U.S. military bases. Does NOT include U.S. territories (Puerto Rico, Guam, USVI, etc.).
    - IRS interpretation is generous: homeless shelters count as a home; temporary absences (illness, school, vacation, military service, juvenile detention) count as time lived together; a child born or who died during the year counts if the home was theirs more than half the time the child was alive.
    - **Precision gap**: `household_size` is a current snapshot, not "more than half the year." We assume the listed household meets the half-year requirement; verified at filing and noted in the description. False positives possible for mid-year custody changes.
    - Screener fields:
      - `household_size` (proxy for half-year-plus residency)
    - Source: 26 U.S.C. § 32(c)(3)(A)(ii); IRS Pub 596 Rule 8 (Residency Test); [Qualifying Child Rules](https://www.irs.gov/credits-deductions/individuals/earned-income-tax-credit/qualifying-child-rules)

12. **Qualifying child — Joint Return test** ⚠️ *data gap*
    - The qualifying child cannot have filed a joint return, unless the joint return was filed solely to claim a refund of withheld or estimated tax.
    - **Married-child rule**: A married child who doesn't file jointly still cannot be a qualifying child unless the filer can claim them as a dependent (or could but for the divorced/separated-parents rule).
    - Screener fields: none
    - Notes: The screener does not capture a child's filing or marital status. We assume qualifying children are unmarried and not filing joint returns. Edge case: e.g., a married teen with a part-time job.
    - **Impact: Low**
    - Source: 26 U.S.C. § 32(c)(3)(B); IRS Pub 596 Rule 8 (Joint Return Test)

13. **Filer cannot be a qualifying child of another taxpayer** ⚠️ *precision data gap*
    - Applies to all filers, regardless of whether they have qualifying children. The filer (and spouse, if MFJ) cannot themselves be claimed as a qualifying child on another person's return.
    - Common case: a young parent living with their own parents — they could be both a parent of their own QC AND a QC of their parent, which disqualifies them.
    - **Precision gap**: The screener can only infer this for relationships visible inside the household. It cannot detect whether a person outside the household could claim the filer or spouse as a qualifying child. We assume the filer/spouse is not a qualifying child of someone outside the household; verified at filing.
    - **Implementation note**: For in-household checks, test whether the head of household or spouse could be another member's qualifying child using the visible `parent`, `grandParent`, or other relevant relationship, age, full-time student status, and disability fields. A young parent living with their own parent can be disqualified even if they have their own qualifying child.
    - Screener fields:
      - `relationship`
      - `birth_month` and `birth_year`
      - `student_full_time`
      - `long_term_disability` / `disabled`
    - Source: 26 U.S.C. § 32(c)(1)(A)(ii)(I); IRS Pub 596 Rules 10 (filers with a QC) and 13 (filers without a QC)

14. **Childless filer cannot be a dependent of another person** ⚠️ *data gap*
    - Applies only when the filer claims EITC with no qualifying children. The filer cannot be claimable as a dependent — either as a "qualifying child" OR as a "qualifying relative" — on another person's return.
    - Distinct from criterion 13: a person who isn't a QC of someone else may still be claimable as a "qualifying relative" (e.g., a 26-year-old graduate student supported by their parents).
    - Screener fields: none
    - Notes: The screener does not capture dependent status. We assume childless filers are not dependents; verified at filing and mentioned in the description.
    - **Suggested screener improvement**: One conditional question shown only to childless filers under ~30 — "Could a parent or other family member claim you as a dependent on their tax return?"
    - **Impact: Medium** (common for young-adult workers supported by parents)
    - Source: 26 U.S.C. § 152; IRS Pub 596 Rule 12

15. **Filer and spouse must have lived in the United States for more than half the tax year** ⚠️ *precision data gap*
    - "United States" = 50 states, DC, U.S. military bases (NOT territories) — same definition as criterion 11.
    - U.S. military personnel stationed outside the U.S. on extended active duty are treated as living in the U.S.
    - **Precision gap**: `zipcode` is a current snapshot, not "more than half the year." We assume current U.S. residency meets the half-year requirement; verified at filing and noted in the description. False positives possible for mid-year arrivals.
    - Screener fields:
      - `zipcode` (proxy for half-year-plus U.S. residency)
    - Source: 26 U.S.C. § 32(c)(1)(A)(ii)(I); IRS Pub 596 Rule 14

16. **Filer (and spouse if MFJ) must have a valid SSN authorized for employment** ⚠️ *data gap*
    - SSN must be issued on or before the return due date (including extensions). ITINs do not qualify. SSNs marked "Not Valid for Employment" do not qualify.
    - The screener does not capture SSN status. `legal_status_required` is the closest proxy but doesn't map perfectly. We assume work-authorized statuses have valid employment SSNs; verified at filing and noted in the description. (Contrast WA WFTC, which accepts ITINs.)
    - Screener fields: none (proxied by `legal_status_required` at config level)
    - Source: 26 U.S.C. § 32(c)(1)(E); IRS Pub 596 Rule 2

17. **Each qualifying child must have a valid SSN (not an ITIN or ATIN)** ⚠️ *data gap*
    - Children with ITINs or ATINs do NOT count as qualifying children.
    - **Mixed-SSN tier rule**: If only some QCs have valid SSNs, the credit tier is the count with SSNs. Example: 3 QCs, 2 with SSNs → claim at the 2-child tier.
    - A filer whose only QC lacks a valid SSN may still claim the childless ("self-only") EITC if they meet criteria 8, 13, 14, and 15.
    - The screener does not capture child SSN status. We assume household children have valid SSNs; verified at filing and noted in the description.
    - Screener fields: none
    - Source: 26 U.S.C. § 32(c)(3)(D); IRS Pub 596 Rule 2

## Data Gaps

Gaps and precision concerns not already flagged at the criterion level. Criteria already marked ⚠️ above: #5, #7, #8, #9 (foster + distant-relative), #10 (student + disabled), #11, #12, #13, #14, #15, #16, #17 — not duplicated here.

18. **Qualifying child claimed by another taxpayer (tiebreaker rules)** ⚠️ *data gap*
    - The screener cannot detect if someone outside the household is claiming the same child (common in divorced/separated households).
    - Tiebreaker hierarchy: parent > non-parent; longer residence > higher AGI.
    - **Self-only fallback**: A filer who loses a QC to another taxpayer may still claim the childless EITC if they meet criteria 8, 13, 14, and 15.
    - **Impact: Medium**
    - Source: 26 U.S.C. § 152(c)(4); IRS Pub 596 Rule 9; [IRS Qualifying Child Rules](https://www.irs.gov/credits-deductions/individuals/earned-income-tax-credit/qualifying-child-rules)

19. **Married Filing Separately and the 6-month-separation exception** ⚠️ *data gap*
    - Filing status is inferred from relationship structure: Single / HOH / MFJ are correct, but **MFS cannot be represented** — any married couple with both spouses in the household is treated as MFJ, producing a false positive for MFS filers on criterion 5.
    - The 6-month-separation / legal-separation exception also cannot be evaluated (no "lived apart from spouse" signal).
    - Domestic Partner is distinguished from Spouse, so federal single/HOH treatment is preserved.
    - QSS is not separately captured but is harmless (QSS uses single/HOH thresholds anyway).
    - We assume married in-household couples file jointly. The MFS path is mentioned in the description.
    - **Impact: Medium**
    - Source: 26 U.S.C. § 32(d); IRS Pub 596 Rule 3

20. **Prior EITC disallowance / 2-year or 10-year ban (Form 8862)** ⚠️ *data gap*
    - If a filer's EITC was previously denied or reduced for reasons other than math/clerical error, they are barred from claiming the credit for **2 years** (reckless or intentional disregard of the rules) or **10 years** (fraud). After the ban, they must attach Form 8862 to recertify eligibility.
    - The screener does not capture prior-denial history. We assume filers have not been previously disallowed; verified at filing.
    - **Impact: Low** (niche population — filers with a prior denial)
    - Screener fields: none
    - Source: 26 U.S.C. § 32(k); IRS Pub 596 Chapter 5; [IRS Form 8862 Instructions](https://www.irs.gov/forms-pubs/about-form-8862)

## Priority Criteria

None found. EITC is claimed through federal tax filing and is not a limited-slot benefit or waitlist program.

## Benefit Value

- **Type**: Federal refundable tax credit (annual, claimed on the tax return).
- **Methodology**: The screener shows users the **maximum credit for their filing-status × qualifying-child-count tier**, provided they pass the eligibility criteria. The actual credit a filer receives may be less if their earned income or AGI is in the phase-in or phase-out region of the EITC formula; the screener does not model phase-in/phase-out precisely.
- **Maximum credit amounts (Tax Year 2025)**:

  | Qualifying Children | Maximum Credit |
  |---------------------|----------------|
  | 0                   | $649           |
  | 1                   | $4,328         |
  | 2                   | $7,152         |
  | 3+                  | $8,046         |

  Tier is determined by the count of qualifying children with valid SSNs (see criterion 17 for the mixed-SSN rule). Screener fields used: `relationship` (qualifying child), `birth_month` and `birth_year` (qualifying child and filer), `student_full_time` or closest available student proxy, `long_term_disability` / `disabled`, and `screen.is_joint()`.
- Users wanting a precise estimate based on their own income can use the official **[IRS EITC Assistant](https://apps.irs.gov/app/eitc)**.
- **Average benefit** (context, not surfaced): ~$2,916 based on TY2024 returns (~23.5M filers, ~$68.5B total — IRS EITC Statistics).
- **Sources**: 26 U.S.C. § 32(b); IRS Pub 596 Rule 1 / EIC Tables; IRS Rev. Proc. 2024-40 (TY2025 inflation adjustments).

## Implementation Coverage

- ✅ Evaluable (clean): 5 — criteria 1, 2, 3, 4, 6
- ⚠️ Evaluable with precision caveats: 7 — criteria 8 (age-at-end-of-tax-year), 9 (distant-relative + foster/kinship), 10 (student + disabled flags), 11 and 15 (current-snapshot residency), 13 (filer qualifying-child status only inferable within household), 16 (SSN proxied by `legal_status_required`)
- ⚠️ Full data gaps (assumption + description): 5 — criteria 5 (filing status), 7 (Form 2555), 12 (joint return), 14 (dependent of another), 17 (child SSN)
- ⚠️ Additional gap notes: 3 — entries 18, 19, and 20

Core eligibility is substantially evaluable. Strongest signals: earned-income presence, AGI/earned-income thresholds, childless-filer age range. Highest-impact gaps: MFS filing status (criterion 5 / gap 19) and SSN validity (criteria 16, 17). SSN validity is partially handled by `legal_status_required`. The "childless filer cannot be a dependent" gap (criterion 14) is medium-impact and should be surfaced in the description.

## Research Sources

- [IRS Publication 596 (2025), Earned Income Credit (EIC)](https://www.irs.gov/publications/p596) — primary source
- [IRS: Who Qualifies for the EITC](https://www.irs.gov/credits-deductions/individuals/earned-income-tax-credit/who-qualifies-for-the-earned-income-tax-credit-eitc)
- [IRS: Qualifying Child Rules](https://www.irs.gov/credits-deductions/individuals/earned-income-tax-credit/qualifying-child-rules)
- [IRS: EITC Income Limits and Credit Amounts](https://www.irs.gov/credits-deductions/individuals/earned-income-tax-credit/earned-income-and-earned-income-tax-credit-eitc-tables)
- [IRS: EITC Assistant Tool](https://www.irs.gov/credits-deductions/individuals/earned-income-tax-credit/use-the-eitc-assistant)
- [IRS: Disability and the EITC](https://www.irs.gov/credits-deductions/individuals/earned-income-tax-credit/disability-and-the-earned-income-tax-credit-eitc)
- [IRS: Military and Clergy Rules for the EITC](https://www.irs.gov/credits-deductions/individuals/earned-income-tax-credit/military-and-clergy-rules-for-the-earned-income-tax-credit)
- [IRS: About Form 8862 (Information to Claim Certain Credits After Disallowance)](https://www.irs.gov/forms-pubs/about-form-8862)
- [IRS Rev. Proc. 2024-40 (TY2025 inflation adjustments)](https://www.irs.gov/pub/irs-drop/rp-24-40.pdf)
- [WA DOR: Working Families Tax Credit (separate program)](https://dor.wa.gov/about/news-releases/2026/working-families-tax-credit-application-window-opens-feb-1)
- [26 U.S.C. § 32 — Earned Income Credit (Cornell Law)](https://www.law.cornell.edu/uscode/text/26/32)

## Research Output

Generated via MFB-851 research on 2026-03-31; dev-feedback cleanup completed on 2026-05-08.

Files to be committed to repo:
- Program config: `programs/management/commands/import_program_config_data/data/wa_eitc_initial_config.json`
- Test cases: `validations/management/commands/import_validations/data/wa_eitc.json`

## Acceptance Criteria

- [ ] Scenario 1 (Single Parent, 2 Qualifying Children, Wages Below Threshold): User should be **eligible**
- [ ] Scenario 2 (Single, No Children, Age 25, Wages Just Below Single/No-Child Threshold): User should be **eligible**
- [ ] Scenario 3 (Married Filing Jointly, 3 Children, Combined Income Below MFJ/3-Child Threshold): User should be **eligible**
- [ ] Scenario 4 (Single/HOH, 1 Child, Income Just Below Single/1-Child Threshold): User should be **eligible**
- [ ] Scenario 5 (Single, No Children, Income Just Above Single/No-Child Threshold): User should be **ineligible**
- [ ] Scenario 6 (Single, No Children, Age Exactly 25 — Minimum Age Boundary): User should be **eligible**
- [ ] Scenario 7 (Single, No Children, Age 24 — Below Minimum Age): User should be **ineligible**
- [ ] Scenario 8 (Already Receiving EITC — Platform Exclusion): User should be **ineligible**
- [ ] Scenario 9 (Social Security Retirement Only, Age 67 — No Earned Income): User should be **ineligible**
- [ ] Scenario 10 (Married Filing Jointly, 2 Children, Elderly Parent with SS Retirement): User should be **eligible**
- [ ] Scenario 11 (Domestic Partner HOH, 3 Children, Elderly Parent): User should be **eligible**
- [ ] Scenario 12 (Investment Income Just Under TY2025 Limit of $11,950): User should be **eligible**
- [ ] Scenario 13 (Investment Income Just Over TY2025 Limit of $11,950): User should be **ineligible**

## Test Scenarios

### Scenario 1: Single Parent, 2 Qualifying Children, Income Below Threshold
**What we're checking**: Validates that a single-parent household with two qualifying children and wages well below the single/2-child income threshold qualifies for EITC
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King County`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1990` (age 36), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$2,800` per month ($33,600/year, well below $57,310 TY2025 single/2-child threshold), Insurance: `None`, Citizenship: `U.S. Citizen`
- **Person 2 (Child 1)**: Relationship: `Child`, Birth month/year: `March 2018` (age 7), Has income: `No`, Insurance: `None`, Citizenship: `U.S. Citizen`
- **Person 3 (Child 2)**: Relationship: `Child`, Birth month/year: `June 2020` (age 5), Has income: `No`, Insurance: `None`, Citizenship: `U.S. Citizen`
- **Current Benefits**: Select `None`

**Why this matters**: This is the most common EITC eligibility pathway — a working single parent with preschool- and school-age children earning a moderate wage. Tests the core earned income and income threshold requirements under 26 U.S.C. § 32(a)–(b) with 2 qualifying children.

---

### Scenario 2: Single, No Children, Age 25, Wages Just Below Single/No-Child Threshold
**What we're checking**: Validates that a childless filer who meets the minimum age requirement (25) with income just under the single/no-child threshold qualifies for EITC
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King County`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `December 2000` (age 25 at end of TY2025), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$1,549` per month ($18,588/year, just under $19,104 TY2025 single/no-child threshold), Insurance: `None`, Citizenship: `U.S. Citizen`
- **Current Benefits**: Select `None`

**Why this matters**: Tests the intersection of the minimum age requirement (must be at least 25 at end of tax year) and the income threshold for childless filers under 26 U.S.C. § 32(c)(1)(A)(ii)(II) and § 32(b). Income is ~97% of the threshold — close enough to confirm the screener applies the correct TY2025 limit without false negatives.

---

### Scenario 3: Married Filing Jointly, 3 Children, Combined Income Below MFJ/3-Child Threshold
**What we're checking**: Validates that a married couple filing jointly with three qualifying children and combined income just below the MFJ/3-child threshold qualifies for EITC
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King County`
- **Household**: Number of people: `5`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1988` (age 38), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$3,200` per month, Insurance: `None`, Citizenship: `U.S. Citizen`
- **Person 2 (Spouse)**: Relationship: `Spouse`, Birth month/year: `March 1990` (age 36), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$2,250` per month, Insurance: `None`, Citizenship: `U.S. Citizen`
- **Person 3 (Child 1)**: Relationship: `Child`, Birth month/year: `January 2008` (age 17), Has income: `No`, Insurance: `None`, Citizenship: `U.S. Citizen`
- **Person 4 (Child 2)**: Relationship: `Child`, Birth month/year: `June 2012` (age 13), Has income: `No`, Insurance: `None`, Citizenship: `U.S. Citizen`
- **Person 5 (Child 3)**: Relationship: `Child`, Birth month/year: `September 2016` (age 9), Has income: `No`, Insurance: `None`, Citizenship: `U.S. Citizen`
- **Current Benefits**: Select `None`

Combined income: $3,200 + $2,250 = $5,450/month ($65,400/year), just below $68,675 TY2025 MFJ/3-child threshold (~95% of limit).

**Why this matters**: Tests the highest-value EITC tier (3+ children, MFJ) under 26 U.S.C. § 32(b). Validates that the screener applies the MFJ threshold (not the single threshold) when a spouse is present, and correctly counts three qualifying children to determine the credit tier.

---

### Scenario 4: Single/HOH, 1 Child, Income Just Below Single/1-Child Threshold
**What we're checking**: Validates that a single parent with one qualifying child and income just under the single/1-child threshold qualifies for EITC
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King County`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `June 1985` (age 40), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$4,090` per month ($49,080/year, just under $50,434 TY2025 single/1-child threshold), Insurance: `None`, Citizenship: `U.S. Citizen`
- **Person 2 (Child)**: Relationship: `Child`, Birth month/year: `April 2012` (age 13), Has income: `No`, Insurance: `None`, Citizenship: `U.S. Citizen`
- **Current Benefits**: Select `None`

**Why this matters**: Tests the single/1-child income threshold under 26 U.S.C. § 32(b) at ~97% of the limit. Confirms the screener applies the correct TY2025 ceiling for a one-child household and distinguishes this tier from the two-child and childless tiers.

---

### Scenario 5: Single, No Children, Income Just Above Threshold — Not Eligible
**What we're checking**: Verifies that a childless single filer with income just above the single/no-child threshold is correctly identified as ineligible
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King County`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `April 1985` (age 41), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$1,600` per month ($19,200/year, just above $19,104 TY2025 single/no-child threshold), Insurance: `None`, Citizenship: `U.S. Citizen`
- **Current Benefits**: Select `None`

**Why this matters**: Validates the income ceiling for childless filers under 26 U.S.C. § 32(b). At $19,200/year (just above $19,104), this household should not receive EITC. This is the income boundary test for the no-child tier and ensures the screener does not round or soften the cutoff.

---

### Scenario 6: Single, No Children, Age Exactly 25 — Minimum Age Boundary
**What we're checking**: Validates that a childless filer who is exactly 25 at the end of the tax year meets the minimum age requirement and qualifies when income is below the threshold
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King County`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `December 2000` (age 25 at end of TY2025, December 31, 2025), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$1,200` per month ($14,400/year, well below $19,104 threshold), Insurance: `None`, Citizenship: `U.S. Citizen`
- **Current Benefits**: Select `None`

**Why this matters**: Tests the minimum age boundary (exactly 25 at end of tax year) for childless filers per 26 U.S.C. § 32(c)(1)(A)(ii)(II). A person born in December 2000 turns 25 in December 2025, satisfying the requirement at the end of TY2025. Ensures the screener does not incorrectly exclude filers who turn 25 during the tax year.

---

### Scenario 7: Single, No Children, Age 24 — Below Minimum Age — Not Eligible
**What we're checking**: Tests that a childless filer who is 24 at the end of the tax year is correctly excluded from EITC eligibility
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King County`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `June 2001` (age 24 at end of TY2025; turns 25 in June 2026), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$1,200` per month ($14,400/year, below income threshold), Insurance: `None`, Citizenship: `U.S. Citizen`
- **Current Benefits**: Select `None`

**Why this matters**: Tests the minimum age boundary at month-level granularity (the precision available in the screener). A person born in June 2001 is 24 at December 31, 2025 — one half-year short of the requirement. Validates that the screener correctly excludes filers who have not yet reached age 25 by end of the tax year per 26 U.S.C. § 32(c)(1)(A)(ii)(II). Note: day-level precision is not testable since the screener captures only birth month and year.

---

### Scenario 8: Already Receiving EITC — Platform Exclusion
**What we're checking**: Tests that the screener's standard "currently receiving" exclusion logic filters out households already enrolled in EITC and does not re-surface it as a new result
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King County`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1985` (age 41), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$3,000` per month ($36,000/year, below $50,434 single/1-child threshold), Insurance: `None`, Citizenship: `U.S. Citizen`
- **Person 2 (Child)**: Relationship: `Child`, Birth month/year: `June 2015` (age 10), Has income: `No`, Insurance: `None`, Citizenship: `U.S. Citizen`
- **Current Benefits**: Select `EITC`

**Why this matters**: Tests that the platform's existing "currently receiving" exclusion behaves correctly for EITC. The household is otherwise fully eligible — the only reason for ineligibility is that they are already enrolled. This is platform-level behavior, not a new eligibility rule. It should be treated as platform-level duplicate suppression and should be verified separately from `show_in_has_benefits_step`, which should remain `false` unless EITC is intended to confer categorical eligibility for another program.

---

### Scenario 9: Social Security Retirement Only, Age 67 — No Earned Income — Not Eligible
**What we're checking**: Validates that a household whose only income is Social Security retirement benefits is ineligible for EITC due to both no earned income and exceeding the childless filer age maximum (64)
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King County`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1958` (age 67), Has income: `Yes`, Income type: `Social Security (Retirement)`, Income amount: `$1,400` per month, Insurance: `None`, Citizenship: `U.S. Citizen`
- **Current Benefits**: Select `None`

**Why this matters**: Tests two simultaneous ineligibility conditions: (1) no earned income — Social Security retirement is unearned income and does not qualify under 26 U.S.C. § 32(c)(2); and (2) age 67 exceeds the 64-year maximum for childless filers per 26 U.S.C. § 32(c)(1)(A)(ii)(II). Either condition independently renders this household ineligible; the scenario confirms the screener handles both correctly.

---

### Scenario 10: Married Filing Jointly, 2 Children, Elderly Parent with SS Retirement
**What we're checking**: Validates that a married couple with 2 qualifying children and earned wages qualifies for EITC even when an elderly household member contributes Social Security retirement income that pushes total household income toward the threshold
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King County`
- **Household**: Number of people: `5`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `June 1982` (age 43), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$2,000` per month, Insurance: `None`, Citizenship: `U.S. Citizen`
- **Person 2 (Spouse)**: Relationship: `Spouse`, Birth month/year: `March 1984` (age 42), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$1,500` per month, Insurance: `None`, Citizenship: `U.S. Citizen`
- **Person 3 (Child 1)**: Relationship: `Child`, Birth month/year: `August 2010` (age 15), Has income: `No`, Insurance: `None`, Citizenship: `U.S. Citizen`
- **Person 4 (Child 2)**: Relationship: `Child`, Birth month/year: `April 2014` (age 11), Has income: `No`, Insurance: `None`, Citizenship: `U.S. Citizen`
- **Person 5 (Elderly Parent)**: Relationship: `Parent`, Birth month/year: `January 1950` (age 76), Has income: `Yes`, Income type: `Social Security (Retirement)`, Income amount: `$1,400` per month, Insurance: `Medicare`, Citizenship: `U.S. Citizen`
- **Current Benefits**: Select `None`

Total household income: $2,000 + $1,500 + $1,400 = $4,900/month ($58,800/year), below the $64,430 MFJ/2-child TY2025 threshold.

**Why this matters**: Tests that a multi-generational household with mixed income sources (wages from earners, Social Security retirement from a non-earner) is correctly evaluated. The elderly parent's SS retirement is not earned income and should not preclude the couple's EITC eligibility; only the earners' wages drive the earned income test. Validates the screener correctly distinguishes income types in a complex household.

---

### Scenario 11: Domestic Partner HOH, 3 Children, Elderly Parent — Eligible
**What we're checking**: Validates that an unmarried domestic partner filing as Head of Household with 3 qualifying children is correctly treated as a single/HOH filer (not MFJ) and qualifies when household income is below the single/3-child threshold
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King County`
- **Household**: Number of people: `6`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1985` (age 41), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$3,500` per month ($42,000/year), Insurance: `None`, Citizenship: `U.S. Citizen`
- **Person 2 (Domestic Partner)**: Relationship: `Domestic Partner`, Birth month/year: `June 1987` (age 38), Has income: `No`, Insurance: `None`, Citizenship: `U.S. Citizen`
- **Person 3 (Child 1)**: Relationship: `Child`, Birth month/year: `April 2010` (age 15), Has income: `No`, Insurance: `None`, Citizenship: `U.S. Citizen`
- **Person 4 (Child 2)**: Relationship: `Child`, Birth month/year: `August 2013` (age 12), Has income: `No`, Insurance: `None`, Citizenship: `U.S. Citizen`
- **Person 5 (Child 3)**: Relationship: `Child`, Birth month/year: `December 2016` (age 9), Has income: `No`, Insurance: `None`, Citizenship: `U.S. Citizen`
- **Person 6 (Elderly Parent)**: Relationship: `Parent`, Birth month/year: `January 1950` (age 76), Has income: `Yes`, Income type: `Social Security (Retirement)`, Income amount: `$1,400` per month, Insurance: `Medicare`, Citizenship: `U.S. Citizen`
- **Current Benefits**: Select `None`

Total household income: $3,500 + $1,400 = $4,900/month ($58,800/year), below the $61,555 TY2025 single/HOH/3-child threshold.

**Why this matters**: Tests that the screener correctly applies the single/HOH income threshold (not the MFJ threshold) for domestic partners. Unmarried domestic partners are not treated as married for federal tax purposes and file separately; only the HOH's income and qualifying children drive EITC eligibility. This is a meaningful distinction from Scenario 3 (MFJ) because the single/3-child threshold ($61,555) is lower than MFJ ($68,675).

---

### Scenario 12: Investment Income Just Under TY2025 Limit of $11,950
**What we're checking**: Validates that a household with investment income just under the TY2025 limit ($11,950) and earned wages below the income threshold qualifies for EITC
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King County`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1985` (age 41), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$2,500` per month; also Income type: `Investment Income (Dividends/Interest)`, Income amount: `$995` per month ($11,940/year, just under $11,950 TY2025 investment income limit), Insurance: `None`, Citizenship: `U.S. Citizen`
- **Person 2 (Child)**: Relationship: `Child`, Birth month/year: `June 2015` (age 10), Has income: `No`, Insurance: `None`, Citizenship: `U.S. Citizen`
- **Current Benefits**: Select `None`

Total income: $2,500 + $995 = $3,495/month ($41,940/year), below $50,434 single/1-child threshold. Investment income: $11,940/year < $11,950 TY2025 limit.

**Why this matters**: Tests the TY2025 investment income ceiling ($11,950) established under 26 U.S.C. § 32(i). Investment income of $995/month ($11,940 annually) falls just under the updated limit, confirming the screener applies the TY2025 figure (not the prior-year $11,600 value). Families with moderate investment income who otherwise qualify should still receive the credit.

---

### Scenario 13: Investment Income Just Over TY2025 Limit of $11,950 — Not Eligible
**What we're checking**: Verifies that a household whose investment income exceeds the TY2025 limit ($11,950) is correctly identified as ineligible, even when earned income and AGI are well below the income thresholds
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King County`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1985` (age 41), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$2,500` per month; also Income type: `Investment Income (Dividends/Interest)`, Income amount: `$1,000` per month ($12,000/year, just above $11,950 TY2025 investment income limit), Insurance: `None`, Citizenship: `U.S. Citizen`
- **Person 2 (Child)**: Relationship: `Child`, Birth month/year: `June 2015` (age 10), Has income: `No`, Insurance: `None`, Citizenship: `U.S. Citizen`
- **Current Benefits**: Select `None`

Total income: $2,500 + $1,000 = $3,500/month ($42,000/year), well below $50,434 single/1-child threshold. Investment income: $12,000/year > $11,950 TY2025 limit (by $50).

**Why this matters**: Tests the ineligible side of the TY2025 investment income ceiling under 26 U.S.C. § 32(i). At $12,000 annual investment income, this household exceeds the $11,950 cap by $50 — confirming the screener applies a strict cutoff rather than rounding or softening the boundary. Pairs with Scenario 12 (just under the limit, eligible) to validate both sides of the boundary. The household is otherwise fully EITC-eligible — investment income is the only disqualifying factor.

---

## JSON Test Cases
File: `validations/management/commands/import_validations/data/wa_eitc.json`

## Generated Program Configuration
File: `programs/management/commands/import_program_config_data/data/wa_eitc_initial_config.json`
