# Implement TANF (MO) Program

## Program Details

- **Program:** Temporary Assistance (TA / TANF)
- **State:** MO
- **White Label:** mo
- **Engine:** PolicyEngine (`mo_tanf`, `mo_tanf_eligible`, `mo_tanf_maximum_benefit`) — Tier: State (custom)
- **Year:** 2026
- **Calculator type:** PolicyEngine-backed custom calculator. MFB applies the Missouri-specific eligibility and benefit rules documented below.
- **Scope:** this calculator covers Missouri's regular monthly Temporary Assistance cash grant only. It does not calculate Cash Diversion or the Transitional Employment Benefit — separate one-time/post-TA benefit mechanisms outside this spec's scope.

## Eligibility Criteria

Each criterion states the Missouri rule that determines household or member eligibility, the screener fields used, and the committed treatment for anything the screener cannot verify directly.

### 1. Dependent child required; pregnancy alone does not qualify ⚠️ *partial data gap*

**Rule:** the household must include a qualifying child — under 18, or under 19 and a full-time secondary (or vocational/technical equivalent) student — who has never married. Divorce does not restore dependent-child status; annulment can. Pregnancy alone does not qualify.

- **MFB fields:** `household_members.birth_year`/`birth_month`, `household_members.relationship`, `pregnant`
- **Committed treatment:** an 18-year-old reported as a dependent child is assumed enrolled and expected to graduate; no reported child is assumed married — the screener has no field for either fact. Committed inclusive handling, no scenario — MFB cannot establish secondary-school/equivalent attendance or marital history for an 18-year-old.
- **Cross-reference:** a dependent child's earnings can affect eligibility itself, not just grant value — see Benefit Value Step 6.
- **Source:** [13 CSR 40-2.325](https://www.law.cornell.edu/regulations/missouri/13-CSR-40-2-325) — *"a child under the age of eighteen (18) who resides with a custodial parent or other adult caretaker relative ... or a child under the age of nineteen (19) and a full-time student in a secondary school (or at the equivalent level of vocational or technical training)."* Pregnancy alone is not an independent basis. [0210.005.05](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-005-05/) — *"If the dependent child marries, they are no longer a dependent child, even if they get divorced. However, if the marriage is annulled, they could be considered a dependent child again."*

### 2. Deprivation of parental support ⚠️ *partial data gap*

**Rule:** the child must be deprived of parental support (death, absence, incapacity, divorce/separation, desertion, financial need, confinement, or restoration from Vocational Rehabilitation combined with a training absence). Two-parent households qualify via the financial-need basis without both parents being unemployed. A parent's strike participation cannot itself establish deprivation, but another basis may still apply.

- **MFB fields:** `household_members.relationship`, `household_members.disabled`, `household_members.long_term_disability`
- **Committed treatment:** assume deprivation exists whenever household composition suggests it (single-parent household, or a parent flagged `disabled`/`long_term_disability`), and that two-parent households qualify via financial need. Do not gate on employment or strike status — the income tests handle that.
- **Source:** 13 CSR 40-2.310(5)(A)1–8 and (5)(B) — *"Are deprived of parental support or care for the following reasons:"* (death, absence, incapacity, divorce/separation, desertion, confinement, Vocational Rehabilitation, financial need); *"Are not deprived of parental support due to the parent's participation in a strike."* [0205.050.25.10](https://dssmanuals.mo.gov/temporary-assistance-case-management/0205-050-25-10/)

### 3. Caretaker relationship to child ⚠️ *partial data gap*

**Rule:** Missouri recognizes an extensive list of qualifying caretaker relatives — parent, grandparent, sibling, aunt/uncle, first cousin, legal guardian, and others.

- **MFB fields:** `household_members.relationship`
- **Committed treatment:** MFB's relationship enum (`headOfHousehold`, `spouse`, `domesticPartner`, `child`, `stepChild`, `fosterChild`, `parent`, `fosterParent`, `stepParent`, `grandParent`, `grandChild`, `sisterOrBrother`, `stepSisterOrBrother`, `relatedOther`) records each member's relationship *to the household head*, not to each other. A kinship caretaker (e.g., a grandparent) is entered as `headOfHousehold`, with the children in their care as `grandChild`/`child`/`stepChild`/`fosterChild` as applicable — not `relatedOther`. For a caretaker relationship with no dedicated enum value relative to the head (aunt/uncle, legal guardian), it is the *child* whose relationship has no dedicated value, so the child is coded `relatedOther`; when a qualifying child is present and coded `relatedOther`, assume a qualifying caretaker relationship exists. Committed inclusive handling, no scenario — `relatedOther` doesn't reveal which specific qualifying relationship actually exists.
- **`fosterChild` default:** a `fosterChild` relationship doesn't by itself establish the blood/adoption/legal-guardian relationship Missouri requires of a caretaker, and MFB cannot determine whether the foster caretaker also qualifies as a relative or legal guardian. Treat `fosterChild` as satisfying the caretaker-relationship requirement for screening purposes — this does not imply receipt of foster-care maintenance (Criterion 4 assumes none is received). Committed inclusive handling, no scenario — MFB cannot verify the underlying qualifying relationship the `fosterChild` code stands in for.
- **`stepParent` field-semantics note:** `stepParent` means "this person is the household head's own step-parent" (the head is the step-child) — **not** "this person is a step-parent to the head's child." A head's spouse who isn't the biological/legal parent of the head's existing child can't be distinguished from an ordinary co-parent spouse — both are coded `spouse`, and no field records legal parentage per child. Real mapping limitation, not a resolved encoding — see Criterion 4's stepparent-income-deeming discussion.
- **Source:** [0205.025.00](https://dssmanuals.mo.gov/temporary-assistance-case-management/0205-025-00/)

### 4. Assistance-unit composition ⚠️ *partial data gap*

**Rule:** mandatory unit members are the eligible child(ren), their parents, and their own dependent siblings. A needy non-parent caretaker relative (NPCR) or guardian may optionally join. SSI recipients are excluded from needs, income, and resources entirely. Several other categories are excluded from needs only: non-dependent siblings (half-siblings not deprived of support, married siblings, siblings 18+ not meeting cash requirements or 19+), non-sibling children, ineligible aliens, certain felons/fugitives, and legal guardians when a parent is present.

- **MFB fields:** member income-stream type `sSI`, `household_members.relationship`, `household_members.birth_year`/`birth_month`, `current_benefits`
- **Need-unit size:** the Missouri need-unit size used to look up the Standard of Need and payment standard (Benefit Value) excludes (a) any member with SSI income and (b) any 18+ non-dependent sibling not independently meeting Criterion 1 — a separate step from excluding that member's own income/resources.

| Situation | Missouri treatment | MFB committed treatment |
|---|---|---|
| SSI recipient | Exclude expenses, income, resources; not counted toward household | Excluded from unit and need-unit size |
| SP/SAB recipient | Same exclusion as SSI | No field/current-benefit mapping exists; assume no member receives SP or SAB |
| SSI/SP/SAB member's resources | Excluded from countable resources | `household_assets` is a single aggregate with no per-member breakdown, so no countable resource figure is reported and the resource test does not deny the household (Criterion 7). Read from a reported `sSI` amount or the SSI current-benefit tile — either establishes an excluded member without identifying whose resources they are |
| Excluded non-dependent sibling's income | Counted only "in the amount made available to the household" — a fact-specific question | No income-availability field; assume $0 is made available, and budget the parent's own income against the remaining unit as usual. Committed inclusive handling, no scenario — MFB cannot establish the actual amount made available |
| SSI dependent child (only TA-qualifying child in household) | Child's needs/income/resources excluded | Payee (or second parent) may still receive a payee-only grant sized to the remaining non-SSI unit |
| Paternity non-cooperation | Alleged father/child cannot qualify; household may be ineligible | No cooperation-status field; trust the reported parent-child relationship and assume paternity established/cooperation/good cause |
| Foster-care or adoption-subsidy payment | Foster child's needs/income/resources generally excluded; adoption-subsidy child sometimes included instead | No payment-status field; do not infer receipt from `relationship: "fosterChild"` or otherwise — assume no such payment is received |
| Temporary absence / permanent separation / adoption / 90-day child absence | Temporary separation (<6 months, intended to continue) keeps the member in the unit; ≥6 months or permanent excludes their needs/income; adoption can sever a biological parent-child relationship; a child absent >90 consecutive days is not assisted | No duration/intent/adoption field; assume reported composition is the current, intended-to-continue arrangement and each child's absence (if any) is ≤90 days |

**NPCR inclusion/exclusion — Missouri's two-step rule with an automatic-needy exception:**
1. **Automatic-needy exception:** if the NPCR's spouse doesn't live in the home, or receives SSI/SSI-SP, deem the NPCR needy without a neediness budget — skip to step 3.
2. **Otherwise, determine neediness:** compare the NPCR's, co-resident spouse's, and their own under-18 children (excluding children already in the TA group) against the full Standard of Need for that group alone, without the $30-plus-⅓/$30-only earned-income disregards. Not needy → excluded, no elective choice.
3. If needy (either path), the NPCR may be included or excluded — Missouri's rule is to compute both policy-valid unit configurations and return the higher eligible monthly grant.
4. Spouse non-cooperation with the neediness determination makes the NPCR not needy; MFB cannot observe cooperation history, so assume the spouse cooperates.
5. Same procedure applies to a legal guardian's neediness determination (0210.005.40).

The exclusion branch is constructed by submitting the NPCR's household with that member (and any co-resident spouse) simply omitted from the request — a real, policy-valid alternate configuration, not a fabricated one. Steps 1–4 above are implemented exactly as stated: the automatic-needy-exception/neediness-budget pre-test is computed locally from inputs alone (no PE call needed), and the genuinely-elective case makes two live PE calls (NPCR included vs. excluded), keeping whichever eligible result has the higher benefit (Scenarios 10, 11, 12, 34; `mock_calculator/pe_integrated_path.py`).

**Income-deeming and blended-family branches — not representable with current screener inputs:** a minor parent living with their own parent (three-generation household) triggers major-parent income deeming only under a separate-filing arrangement (not under combined filing); a stepparent's income is deemed when the head's spouse isn't the legal/biological parent of the head's existing child. `household_members.relationship` doesn't reveal which filing arrangement a three-generation household uses, or whether a spouse is a stepparent to an existing child, so neither deeming branch can be triggered — inclusively assume a policy-valid arrangement with no additional deemed income. The same relationship-mapping gap also makes blended families, double-stepparent households (separate applications per parent), and three-generation filing-arrangement choice out of scope for this calculator version — Missouri evaluates the whole family together first, splitting into separate cases only once shown financially ineligible together.

- **Source:** [0210.005.05](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-005-05/); [0210.005.10](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-005-10/); [0210.005.30](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-005-30/); [0210.005.35](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-005-35/); [0210.005.40](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-005-40/); [0210.005.45](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-005-45/); [0225.045.00](https://dssmanuals.mo.gov/temporary-assistance-case-management/0225-045-00/); [0205.030.05](https://dssmanuals.mo.gov/temporary-assistance-case-management/0205-030-05/); [0210.005.00](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-005-00/); [13 CSR 40-2.365](https://www.law.cornell.edu/regulations/missouri/13-CSR-40-2-365); [13 CSR 40-2.310(8)(B)1.G–2](https://www.law.cornell.edu/regulations/missouri/13-CSR-40-2-310) (excluded-sibling income-availability standard)
- **Operative quotations:** 0210.005.10 — *"Exclude the expenses, income, and resources of the SSI, SP, or SAB participants in determining TA eligibility for the family. Do not consider any SSI, SP, or SAB income as available to the TA household."* 0210.005.35 — *"IF AN NPCR IS FOUND TO BE NEEDY, HE/SHE HAS THE OPTION OF BEING INCLUDED OR EXCLUDED FROM THE ASSISTANCE GROUP"*; *"When the NPCR is determined to be not needy, exclude the NPCR from the Temporary Assistance assistance group (both needs and income). The NPCR is not eligible for cash payment."*; the spouse-absent/SSI automatic-needy rule is also stated there. 0210.005.40 — apply the NPCR procedure to a legal guardian. 0210.005.05 — *"If the entire household is not eligible for benefits based on financial need, then and only then, can the children be in separate households"*; *"Complete an application for each parent with his/her own children. This is considered a 'double stepparent' case."* 0210.005.30 — *"consider all their needs and income as a single assistance group and do not apply the disregards described below"* (filing together) or *"the major parent's income is deemed to the minor parent's assistance group"* (filing separately). 0210.005.00 — *"When the separation is ongoing (longer than six months or permanent)... exclude the needs and income of the person separated from the family"*; *"Adoption severs all biological relationships for purposes of mandatory eligibility unit members."* 13 CSR 40-2.365 — *"a minor child who has been, or is expected ... to be, temporarily absent from the home for a period exceeding ninety (90) consecutive days"* is not assisted.

### 5. Missouri residency

**Rule:** the payee and children must be Missouri residents.

- **Committed treatment:** not evaluated by this calculator — no Missouri-residency field exists; assume the requirement is met.
- **Source:** [0205.035.00](https://dssmanuals.mo.gov/temporary-assistance-case-management/0205-035-00/); 13 CSR 40-2.310(1)(A) — *"to be eligible for Temporary Assistance, the payee and children must be Missouri residents."*

### 6. U.S. citizenship or qualified alien status

**Rule:** Missouri limits TA to citizens and eligible qualified aliens. Some qualified-alien subcategories are immediately eligible (refugees, asylees, withholding-of-removal grantees, Cuban/Haitian entrants, Amerasian immigrants, COFA citizens, Canadian-born American Indians, trafficking victims, and LPRs who previously held one of those statuses). Others — an ordinary LPR, a parolee admitted for one year or more, a conditional entrant, or a battered immigrant — generally face a five-year waiting period from date of entry (for entry on or after August 22, 1996), unless a military/veteran/dependent, unmarried surviving military spouse, or U.S.-born-child exception applies.

- **Source:** [0205.040.05.15](https://dssmanuals.mo.gov/temporary-assistance-case-management/0205-040-05-15/) — *"Qualified aliens entering the U.S. on or after August 22, 1996 ... are not eligible for Temporary Assistance for five years following their date of entry."*

### 7. Resource (asset) limit ⚠️ *accepted PE limitation*

**Rule:** the countable-resource limit is $1,000 for applicant families, $5,000 for participant families with a qualifying self-sufficiency pact / Individual Employment Plan (IEP).

- **MFB fields:** `household_assets`, `current_benefits`
- **Committed treatment — tier:** PolicyEngine's `mo_tanf_resources_eligible` applies a flat $1,000 test regardless of TA-recipient status, with no $5,000 IEP-tier concept to select into — a disclosed, accepted PE limitation, not an MFB-side default. Every household is evaluated against $1,000, current recipients included. Independent of that, no field indicates active IEP status either. No scenario tests the $5,000 tier, for either reason.
- **Committed treatment — liquid assets only:** Missouri's countable-resources definition covers several forms of real/personal property, subject to exclusions (home, one vehicle up to a threshold, household goods). `household_assets` captures only liquid assets (cash, checking, savings, stocks, bonds, mutual funds) — apply the $1,000/$5,000 limit to that reported figure, and assume the household meets any resource requirement involving asset types the screener doesn't collect (real property, vehicles, life insurance).
- **Committed treatment — SSI/SP/SAB member present:** no countable resource figure is reported, so the resource test does not deny the household. Their excluded share can't be isolated from the single `household_assets` total (Criterion 4), and PolicyEngine's own exclusion in `mo_tanf_countable_resources` reads person-level asset ownership the screener doesn't collect. Deliberately inclusive: such a household passes the resource test whatever the reported total.
- **Source:** 13 CSR 40-2.310(3), (3)(E)–(F) — *"A participant is not eligible for Temporary Assistance if his/her total countable resources exceeds one thousand dollars ($1,000). If the participant is participating in an Individual Employment Plan as defined in 13 CSR 40-2.370, the resource limit is five thousand dollars ($5,000)."* [0205.005.00](https://dssmanuals.mo.gov/temporary-assistance-case-management/0205-005-00/) distinguishes *"applicant families"* ($1,000) from *"participant families who have entered into a self sufficiency pact"* ($5,000).

### 8. Financial eligibility and income treatment ⚠️ *partial data gap*

**Rule:** a household must pass all three of Benefit Value's gates — Gross Max (185%), Standard of Need, and Percentage of Need (which also sets the grant) — to be eligible. Gates, tables, and formulas are in Benefit Value; this criterion states which income-treatment rules affect eligibility itself, not just grant value.

- **MFB fields:** per-member `income_streams` (type/amount/frequency), `current_benefits`, `household_assets`, `household_members.relationship`, `household_members.student`/`student_full_time`, `expenses` (`childCare`, `dependentCare`)
- **SSI exclusion** affects eligibility via Criterion 4 (income, resources, headcount all excluded).
- **Stepparent and major-parent (three-generation minor-parent) income deeming** are real Missouri rules that could affect eligibility but aren't triggerable from current screener inputs — committed-inclusive data gaps, not implemented branches. See Criterion 4 / Benefit Value Step 5.
- **Child-student and teen-parent student earned-income exclusions** affect eligibility, not just grant value — full field-semantics note and committed treatment in Benefit Value Step 6.
- **New-spouse disregard:** Missouri disregards a new spouse's income and resources entirely for 6 consecutive benefit months after an active participant marries. The resource half of this is still applied as an MFB default (Benefit Value Step 7); the income half is an accepted PE limitation — PE counts the spouse's income regardless — and is not implemented. See Benefit Value Step 7.
- **Disregard-duration defaults** (the $30-plus-⅓ and two-thirds earned-income disregards) affect the countable-income figure that feeds eligibility — see Benefit Value Step 3's committed default.
- **Earned-income-disregard disqualification default:** Missouri withholds the $90/$30-plus-⅓/two-thirds disregards from an individual who, without good cause, terminates/reduces earnings, refuses bona fide employment, or fails required timely earnings reporting. No employment/good-cause/reporting history is collected — see Benefit Value Step 3.
- **Income measurement basis:** each reported `income_streams` entry is treated as ongoing, expected recurring income, converted to a monthly figure — see Benefit Value.
- **MFB income-source treatment table:** Missouri's income-source manual classifies unearned income by source; several MFB income-stream types map onto sources Missouri treats differently:

| MFB `income_streams` type | Missouri treatment | Committed calculator behavior |
|---|---|---|
| `unemployment`, `pension`, `veteran`, `workersComp`, OASDI variants, `alimony` | Included, unearned | Count in full, no disregard, at every gate |
| `sSI` | Recipient excluded from the assistance unit entirely | See Criterion 4 |
| `gifts` | Included, unearned, unless a small non-recurring cash gift under the Percentage-of-Need standard | Every stream is modeled as recurring (see "Income measurement basis") and MFB's income UI has no one-time option, so a `gifts` entry is definitionally recurring and can't represent the non-recurring exception. **Count every reported amount as included unearned income** — not representable under MFB's recurring-income input model.¹ |
| `investment` — dividend/royalty | Included, unearned | — |
| `investment` — interest | Excluded | — |
| `investment` — stock-sale/capital gain | No source states a distinct treatment | See combined-bucket rule below |
| `investment` (MFB's combined field) | N/A — MFB reports interest, dividends, and stock-sale profit as one undifferentiated amount | **Exclude the entire reported `investment` amount** — cannot separate the components. Committed inclusive handling, no scenario |
| `rental` | Earned only if the reporting member manages the property ≥20 hrs/week; otherwise unearned | No management-hours sub-field. **Treat as earned income** (favorable-to-household default). Committed inclusive handling, no scenario |
| `childSupport` | Included, unearned, special pending/active-case budgeting rule | See below |
| `cashAssistance` | Excluded when it's the household's own MO TA payment; otherwise included, unearned | See below |
| `selfEmployment` | Net self-employment profit | See below |

  ¹ Not because Missouri lacks a threshold, but because MFB's input model cannot express a one-time amount.
  **Source:** [0210.015.05](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-015-05/) — *"workers compensation (WC-include)"*; *"unemployment compensation/insurance (UC-include)"*; *"Social Security ... (OASDI) (SS-include)"*; *"union fund/pension benefits/retirement (UF-include)"*; *"Veteran's benefits ... (VA-include)"*; *"dividend/royalty (DI-include)"*; *"interest (IN-exclude)"*; *"consider income from rental property earned income only if a member of the EU is actively engaged in managing the property at least 20 hours per week"*; *"gifts (GF-include unless this is a small non-recurring cash gift such as those for Christmas, birthdays, and graduations not exceeding the percentage of need standard for the assistance group in a month)."*
- **Committed treatment — child support received:** for a pending application, treat the reported `childSupport` amount as unearned income equal to what the household actually received that month. For an **active TA case**, Missouri first runs a trial eligibility budget using the total support paid to CSE/DFAS and/or sent directly to the child, and only if the household remains eligible there does it compute the regular (grant) budget using only the amount sent to the child. No field exists for the CSE/DFAS-retained amount, so the trial budget can't be run. **Committed inclusive treatment:** for both pending and active cases, use only the reported amount as unearned income in the regular budget, and don't impute any additional retained amount or assume it would independently fail the trial budget.
  - **Source:** [0210.015.20.20](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-015-20-20/) — *"Only budget the amount of current child support and arrearage payments actually received."* Missouri's own active-case worked example runs a trial budget with $156 ($125 retained by CSE + $31 sent to the household) before using only the $31 in the regular budget.
- **Committed treatment — cash assistance (MO TA self-exclusion):** 13 CSR 40-2.310(10)–(12) defines each income test using family income "other than Temporary Assistance benefits," and the income-source manual separately excludes TA itself. When `current_benefits` includes `mo_tanf`, exclude the reported `cashAssistance` amount from all three gates — it's the household's existing grant being recalculated, not outside income. A `cashAssistance` entry without `mo_tanf` in `current_benefits` isn't assumed to be MO TA (no field distinguishes the program) and is included as unearned income (e.g., another state's or program's cash assistance).
  - **Source:** 13 CSR 40-2.310(10)–(12); [0210.015.05](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-015-05/) — *"Temporary Assistance (C1-C6 exclude)."*
- **Committed treatment — self-employment income:** a reported `selfEmployment` amount is treated as net profit after ordinary business expenses, before personal taxes — consistent with the federal net-earnings-from-self-employment definition (26 U.S.C. § 1402) and Missouri's own business-profit definition. Include it directly in gross earned income at Gate 1 and carry it through the same disregard sequence as wages at Gates 2/3 (Benefit Value Steps 2–3) — no second business-expense subtraction.
- **Source:** [0210.010.05.185](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-010-05-185/); [0210.010.10](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-010-10/); [0210.010.15](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-010-15/); 0210.005.45; 0210.005.30; 0210.015.35.10; 0210.015.35.15; 0210.015.30.22; [0210.015.00](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-015-00/); [0210.015.05](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-015-05/); [0210.015.20.20](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-015-20-20/)

### 9. Job quit or refusal (two-parent households only) ⚠️ *data gap*

**Rule:** Missouri rejects an application when a non-disabled parent in a two-parent family quit a job or refused, without good cause, a bona fide offer of employment, training/education for work, Vocational Rehabilitation, or special work projects within the 30 days before application.

- **MFB fields:** none. **Committed treatment:** assume no disqualifying quit or refusal occurred.
- **Source:** [0205.050.25.20](https://dssmanuals.mo.gov/temporary-assistance-case-management/0205-050-25-20/) — *"Reject the application if a parent, who is not disabled, in a two-parent family ... quit a job or refused, without good cause, a bona fide offer of employment, training or education for work, Vocational Rehabilitation, or special work projects made within the 30-day period prior to the date of application."*

### 10. Minor-parent required living arrangement ⚠️ *data gap*

**Rule:** an unmarried parent under 18 must live with a parent, legal guardian, other adult relative, or in an adult-supervised supportive living arrangement, subject to statutory exceptions (no available relative; relative refusal; safety risk; state best-interest determination).

- **MFB fields:** `household_members.birth_year`/`birth_month`, `household_members.relationship`. **Committed treatment:** assume the minor parent meets the requirement or an exception.
- **Source:** [0205.030.10](https://dssmanuals.mo.gov/temporary-assistance-case-management/0205-030-10/); [13 CSR 40-2.345](https://www.law.cornell.edu/regulations/missouri/13-CSR-40-2-345); 42 U.S.C. § 608(a)(5)(A)–(B) — *"a minor parent under the age of eighteen who is not married ... must live in a place of residence maintained by his/her own parent, legal guardian, or other adult relative or in some other adult supervised supportive living arrangement. Exceptions ... may be allowed in accordance with section 608(a)(5)(B)."*

### 11. Federal 12-week funding restriction for unmarried minor parents ⚠️ *data gap*

**Rule:** federal law (codified in Missouri's own regulation) bars TANF funds for an unmarried individual under 18 with a child 12+ weeks old and no diploma, unless in education or an approved alternative program.

- **MFB fields:** `household_members.birth_year`/`birth_month`, `household_members.relationship`. **Committed treatment:** assume a teen-parent household has a diploma, has a child under 12 weeks, or is in qualifying education/an approved alternative.
- **Cross-reference:** Benefit Value's teen-parent student earned-income exclusion addresses earned income, not this funding restriction, but both affect the same population.
- **Source:** 42 U.S.C. § 608(a)(4); [13 CSR 40-2.340](https://www.law.cornell.edu/regulations/missouri/13-CSR-40-2-340).

### 12. Individual exclusions ⚠️ *data gap*

**Rule:** several individual (not whole-household) exclusions reduce the assistance unit rather than denying the household entirely: a post-8/22/1996 drug felony conviction (lifetime); fugitive-felon or probation/parole-violator status (while it persists); a residence-fraud conviction — fraudulently receiving assistance from two states simultaneously (10 years from conviction); and a household head 18+ who refuses or fails Missouri's required controlled-substance screening (3 years from the positive test/refusal, or from the hearing decision if one is requested) — other eligible members may continue via a protective payee.

- **MFB fields:** none. **Committed treatment:** assume none of these apply — collecting criminal-justice or drug-testing history is inappropriate for a public screening tool.
- **Source:** [0210.005.10](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-005-10/) — *"Individuals who are ineligible due to having been convicted of a drug-related felony after August 22, 1996, are ineligible forever"*; fugitive felons and probation/parole violators *"are ineligible for Temporary Assistance"*; residence-fraud convictions are *"ineligible for ten years from the date of conviction."* [RSMo § 208.027](https://revisor.mo.gov/main/OneSection.aspx?section=208.027) — *"declared ineligible ... for a period of three years from the date of the positive test, test refusal, or administrative hearing decision, if requested."* DSS Manuals 0240.000.00, 0240.005.05, 0240.005.15, [0240.025.10](https://dssmanuals.mo.gov/temporary-assistance-case-management/0240-025-10/).

### 13. 45-month lifetime limit ⚠️ *data gap*

**Rule:** Missouri limits TA to 45 cumulative months (shorter than the federal 60-month default, effective 2016-01-01), subject to exemption categories and six hardship-extension categories (domestic violence, substance abuse, mental health, active Children's Division involvement, family crisis, pending review). Under 13 CSR 40-2.350, months don't count toward the 45 when the participant was a minor and neither head-of-household nor married to the head; the household includes a battered/extreme-cruelty survivor; or the participant lived in Indian country or a Native Alaskan village with ≥50% adult unemployment. Separate state-program exemptions exist for age 60+, permanent-total disability, teen parents under 18 attending secondary school, and required caregivers of a disabled household member.

- **MFB fields:** none. **Committed treatment:** assume the household hasn't exhausted the 45-month limit — no field exists for lifetime months, no-count-month history, or exemption status. No scenario needed; there's no lifetime-month input to test against.
- **Source:** [0205.075.00](https://dssmanuals.mo.gov/temporary-assistance-case-management/0205-075-00/); [0205.075.10](https://dssmanuals.mo.gov/temporary-assistance-case-management/0205-075-10/); 0205.075.15; [13 CSR 40-2.350](https://www.law.cornell.edu/regulations/missouri/13-CSR-40-2-350) — *"TA is not provided to a family that includes an adult who has received assistance for more than forty-five (45) months."*

### 14. Requalification after a full-family work-sanction closure ⚠️ *data gap*

**Rule:** a household reapplying after closure for continued work-program noncompliance must, unless exempt, satisfy a work-activity requalification prerequisite before eligibility resumes. **Binding rule:** 13 CSR 40-2.315's codified standard — an average of 30 hours of work activities per week within one month — governs; the current DSS manual (0210.015.55) instead describes 30 hours in a work activity for at least one week, but a conflicting manual can't override an explicit regulatory computation (this spec's general source-precedence rule). Distinct from the Step 8b grant-reduction sanction, which reduces an ongoing case's grant rather than gating reapplication after closure.

- **MFB fields:** none. **Committed treatment:** assume the household isn't subject to this requalification condition, has already completed the prerequisite work activity, or is exempt.
- **Source:** [13 CSR 40-2.315](https://www.law.cornell.edu/regulations/missouri/13-CSR-40-2-315) (binding); [0210.015.55](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-015-55/) (conflicting operational guidance, not used for duration).

### 15. Pursuit of potentially available RSDI, unemployment, or veterans benefits ⚠️ *data gap*

**Rule:** when potential eligibility for RSDI, unemployment compensation (UC), or veterans benefits exists for the participant or spouse, Missouri requires applying for and cooperating in pursuing it; refusal is an eligibility gate (FSD rejects or closes the case), not a grant-value adjustment.

- **MFB fields:** none. **Committed treatment:** assume the participant/spouse applies for and cooperates in pursuing any potentially available benefit — collecting refusal/entitlement history isn't appropriate for a public screening tool.
- **Source:** [0210.015.00](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-015-00/) — *"When potential eligibility for RSDI, UC, or veteran's benefits exists, but the participant (or spouse) refuses to apply for these benefits, reject or close the case."*

## Priority Criteria

None.

## Benefit Value

**Type:** variable monthly cash benefit.

**Calculator outcome / screener value:** This section determines the household's estimated **monthly Temporary Assistance cash benefit**. Apply the Eligibility Criteria first, then use the steps below to determine the Missouri need unit, which income and resources count, and whether the household passes all three required income gates. Steps 2, 9, and 10 are the three gate checks; the intervening steps define the exclusions, disregards, deductions, and defaults used in those checks.

**The value displayed in the MFB screener is the final estimated monthly Temporary Assistance benefit.** After the household passes all eligibility requirements and all three income gates, Gate 3 determines the monthly grant from the payment standard minus fully-disregarded countable income. Any applicable grant reduction (Step 8a/8b) would then reduce that amount. Under current MFB inputs, sanction status is unobservable and assumed absent, so the displayed value is the Gate 3 monthly grant — not the Gross Max, Standard of Need, payment-standard ceiling, an annual amount, or a prorated first-month amount. If the household fails an eligibility requirement or any required gate, it is ineligible and no benefit value is returned. First-month proration is not reflected because MFB does not collect an application date.

For the explicitly accepted PolicyEngine divergences in Scenarios 8, 20, and 32, use the live PE result shown in each scenario as the final screener result, consistent with Acceptance Criterion 31.

### Gate summary

Missouri requires three independent income tests. All three must pass; a household can fail any one of them even after passing the other two (see "Gate interaction" below). Full formulas and tables are in Steps 2, 9, and 10.

| | Gate 1 — Gross Max | Gate 2 — Standard of Need | Gate 3 — Payment Standard |
|---|---|---|---|
| Comparator | gross countable income `<` ceiling | narrowly-disregarded income `<` ceiling | fully-disregarded income `<` ceiling |
| Child/teen-student earnings exclusion (Step 6) | Applies | Applies | Applies |
| New-spouse income exclusion (Step 7) | Not implemented — accepted PE limitation | Not implemented — accepted PE limitation | Not implemented — accepted PE limitation |
| Not-active earner's countable earnings | Gross, no disregard | Gross; retry with $30-plus-⅓ only if needed to pass — (9)(C)2) exception | $90 → $30-plus-⅓ (or $30-only continuation) → care deduction |
| Active earner's countable earnings | Gross, no disregard | Two-thirds disregard only | Two-thirds disregard → $90 → care deduction |
| Care-cost deduction (Step 4) | No | No | Yes |
| **Screener output** | No — eligibility test only | No — eligibility test only | **Produces the monthly grant; this is the displayed value under current MFB defaults** |

### Income measurement basis

Each reported `income_streams` entry (amount and frequency) is treated as the household's ongoing, expected recurring income and converted to a monthly figure. This calculator does not model averaging of irregular income or anticipated future income the household hasn't yet reported.

### Step 1 — Determine the Missouri need-unit size

Use Criterion 4's filtered need-unit size (excluding SSI recipients and non-qualifying members) for every table below.

### Step 2 — Gross income test (Gate 1): 185% of Standard of Need

`gross countable income < Gross_Max[need_unit_size]` — a household at exactly the ceiling is ineligible on this gate. Use the official Appendix B Gross Max table below for binding sizes 1–8, not `Standard_of_Need × 1.85`; sizes 9–22 are reference material only (scope note in Step 10). No earned-income disregard applies at this gate (see gate summary above) — but the child/teen-student exclusion isn't a disregard, it's income Missouri excludes before Gate 1 is even reached, so that excluded income never appears on either side of the comparison. The new-spouse income exclusion (Step 7) is also Missouri policy at this gate, but is an accepted PE limitation, not implemented — a new spouse's income appears in gross countable income here like any other household member's. A reported `selfEmployment` amount is net profit (Criterion 8), included directly in gross countable earned income here with no separate business-expense subtraction.

| Size | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Gross Max (Appendix B) | $727 | $1,254 | $1,565 | $1,832 | $2,078 | $2,307 | $2,538 | $2,755 | $2,971 | $3,186 | $3,402 |

| Size | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Gross Max (Appendix B) | $3,619 | $3,834 | $4,049 | $4,264 | $4,479 | $4,694 | $4,909 | $5,124 | $5,339 | $5,554 | $5,769 |

**Source:** 13 CSR 40-2.310; [0210.010.05.185](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-010-05-185/). **Operative quotation:** *"The assistance group's gross income (less overhead expenses only) may not exceed 185 percent of the Consolidated Standard Expense."* Appendix B publishes Gross Max as whole dollars; the manual states the size-3 ceiling as $1,565, not the raw $1,565.10.

### Step 3 — Earned-income treatment for each employed household member

Missouri uses a different disregard sequence depending on whether the **individual was already an active TA participant when they became employed** — see the gate summary above for how much of each sequence applies at Gates 1/2/3. The calculation runs separately per employed assistance-unit member; never combine household earnings first. A member's `selfEmployment` amount (net profit, Criterion 8) runs through the identical sequence as wages — the two aren't distinguished once gross earned income is established.

| | Not-active when employment began | Active when employment began |
|---|---|---|
| Gate 3 formula | `max(((gross_earned − 90 − 30) × 2/3) − care, 0)` | `max((gross_earned / 3 − 90) − care, 0)` |
| Sequence | $90 exemption → $30-plus-⅓ → care deduction; floor at $0 | Two-thirds disregard → $90 exemption → care deduction; floor at $0 |
| Duration | $30-plus-⅓ up to 4 consecutive months, then an 8-month $30-only continuation (runs even while unused or temporarily off TA); resets after 12 consecutive months off TA. A true first-time applicant (no TA grant in the preceding 4 months) is tested for need *without* this disregard first — only the grant budget applies it | Two-thirds disregard up to 12 consecutive months; only the remaining months are available on a return within the continuation period; a new 12-month period opens after 12 consecutive months off TA |

```text
# Not-active
after_work_exemption = max(gross_earned - 90, 0)
countable_before_care = max((after_work_exemption - 30) * 2/3, 0)
countable_earned_income = max(countable_before_care - allowable_care_costs, 0)

# Active
after_two_thirds_disregard = gross_earned / 3
after_work_exemption = max(after_two_thirds_disregard - 90, 0)
countable_earned_income = max(after_work_exemption - allowable_care_costs, 0)
```

#### MFB committed fallback when employment/receipt history is unavailable

The screener doesn't collect the historical facts Missouri uses to pick the disregard period an individual is actually in (when employment began relative to TA participation, how much of the $30-plus-⅓/two-thirds period is used, whether the 8-month continuation or 12-month reset applies). MFB uses current TA receipt as an inclusive proxy:

- `current_benefits` **does not include `mo_tanf`** → not-active calculation, full $30-plus-⅓ disregard.
- `current_benefits` **includes `mo_tanf`** → active calculation, full two-thirds disregard.

These are screening assumptions, not verified history — they deliberately pick the more favorable applicable calculation. Scenarios 3, 4, 5, 9, 17, 18, 19, 20, 22, 25, 26, 27, 28, and 30 apply this default.

#### Earned-income-disregard disqualification default ⚠️ *data gap*

None of the disregards above apply to an individual who, without good cause, terminates/reduces earnings, refuses bona fide employment, or fails to report earnings on time. No employment/good-cause/reporting history is collected.

**Committed default:** assume no disqualifying event occurred; apply the normal calculation above. No scenario included — not representable.

**Sources:** [0205.050.25.10](https://dssmanuals.mo.gov/temporary-assistance-case-management/0205-050-25-10/); [0210.015.30](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-015-30/); [0210.015.30.10](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-015-30-10-30/); [0210.015.30.15](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-015-30-15-30/); [0210.015.30.20](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-015-30-20/). **Operative quotations:** 0205.050.25.10's worked example (not-active-participant sequence) — *"Gross monthly income 714.94 ... Standard work expense −90.00 ... Net income 624.94 ... $30+1/3 −228.33 ... 396.61."* 0210.015.30 (active-participant sequence) — *"an amount equal to two-thirds of the individual's gross monthly earned income, standard work exemption, and child/incapacitated parent care costs"* (two-thirds first, then the $90 exemption).

### Step 4 — Care-cost deduction (applied after the earned-income disregard above)

Deduct actual, unreimbursed child-care or incapacitated-person care costs, capped per child/incapacitated adult:

- $200/month for a child under age 2
- $175/month for a child age 2 or older
- $175/month for incapacitated-parent care

Use the reported `childCare` expense for child care and `dependentCare` for incapacitated-person care when a qualifying incapacitated person is present. Cap each *actual reported cost*; don't apply a cap as a deduction when no cost was reported. `disabled`/`long_term_disability` alone doesn't establish that paid care is being purchased — don't apply this deduction on those flags alone without a corresponding `dependentCare` expense.

**Employment/training-necessity default:** Missouri limits this deduction to care needed because of the caretaker's employment or paid training. No field confirms this. **Committed default:** when a unit member has earned income and a qualifying `childCare`/`dependentCare` expense is reported, assume the expense satisfies this requirement.

**Aggregate care-cost cap:** MFB reports `childCare`/`dependentCare` as household-level aggregates, not per-child amounts, so a reported cost can't be tied to a specific child. Missouri's own rule (0210.015.30.25) proportionately allocates one aggregate payment between included and excluded children when costs can't be separated — MFB can't do that allocation, so this calculator uses a more inclusive override instead. **Committed rule:** treat the aggregate `childCare` cost as qualifying for the unit's included children, capped at the **sum of the applicable per-child caps** across those children (e.g., $200 + $175 = $375 for one included under-2 and one included 2-or-older child) — not across excluded children, not proportionately reduced. Cap aggregate `dependentCare` at $175 × the number of qualifying incapacitated persons in the included unit.

**Source:** 13 CSR 40-2.310(9)(A)5; [0210.015.30.25](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-015-30-25/); [0210.015.30.30](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-015-30-30/). **Operative quotation:** *"such amount for each such child or incapacitated individual does not exceed one hundred seventy-five dollars ($175) for children age two (2) and over, or two hundred dollars ($200) for children under two (2) years of age."* *"Only the amount a participant pays for child care and is NOT reimbursed is an allowable child care expense."*

### Step 5 — Major-parent and stepparent income deeming: not triggerable from current screener inputs

When a minor parent lives with their own parent (a three-generation household), Missouri permits multiple valid filing arrangements. Filing together as one assistance group considers all needs/income jointly and applies no deeming. Only the distinct, elective separate-filing arrangement deems the major (grandparent) parent's income into the minor parent's assistance group — per the manual's worked examples, disregarding that parent's earned income up to 100% FPL, then $90, then adding unearned income, then subtracting the full Standard of Need and outside-dependent/support-paid-elsewhere deductions. The deemed amount counts at Gate 1, Gate 2, and the grant calculation alike whenever deeming applies. Missouri similarly deems a stepparent's income when the head's spouse isn't the legal/biological parent of the head's existing child.

**Committed treatment — not representable:** `household_members.relationship` doesn't reveal which filing arrangement a three-generation household uses — a minor parent's own parent coded `parent` is equally consistent with combined filing (no deeming) and separate filing (deeming applies) — so the calculator can't determine whether major-parent deeming applies, and doesn't attempt to trigger it. The stepparent variant fails for an independent reason: MFB can't distinguish a stepparent-of-child spouse from an ordinary co-parent spouse (both coded `spouse`). Neither branch is implemented; both remain documented data gaps. See Criterion 4.

**Source:** [0210.005.45](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-005-45/); [0210.005.30](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-005-30/); [0210.010.05.185](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-010-05-185/) — *"consider all their needs and income as a single assistance group and do not apply the disregards described below"* (filing together) or *"the major parent's income is deemed to the minor parent's assistance group"* (filing separately).

### Step 6 — Child-student and teen-parent student earned-income exclusions ⚠️ *field-semantics data gap*

**Field-semantics gap:** MFB's `household_members.student`/`student_full_time` fields ask only whether the person is enrolled half-time or more at a **university, college, or community college**. For the child-student exclusion, `student: true` + `student_full_time: true` truthfully confirms one of Missouri's own qualifying channels (full-time student "at school/college/university") — a real, observable fact, not an assumption (see the first row below). Anything short of that (unanswered, `false`, or part-time) doesn't confirm the channel, but doesn't rule out the remaining ones (K-12/secondary/vocational attendance, or part-time-student-not-full-time-employee) either — those remain a genuine data gap (second row below). For the teen-parent exclusion, these fields don't measure the required condition (full-time *secondary* attendance) at all, under any value — that exclusion is a complete data gap (third row below). No row's exclusion can be *denied* based on these fields' values.

| Exclusion | Missouri condition | MFB committed default |
|---|---|---|
| **Child-student — truthfully observable channel** (0210.015.35.10) | Dependent child receiving/being added to a TA grant, full-time student "at school/college/university" — Missouri's own condition explicitly includes college/university enrollment, not secondary school alone | When `student: true` and `student_full_time: true` are both reported for a dependent child under 19, MFB's fields directly and truthfully confirm this exact qualifying channel — no assumption required. Apply the exclusion. Fields: `household_members.relationship: "child"`, `student`, `student_full_time`, per-member `income_streams`. Scenario 21 |
| **Child-student — remaining channels, unobservable** (0210.015.35.10) | Same exclusion also covers K-12/secondary/vocational attendance and the part-time-student-who-isn't-a-full-time-employee alternative; Gate 1 exclusion is additionally capped at 6 calendar-year months (not necessarily consecutive) | For a dependent child under 19 with earned income where `student`/`student_full_time` aren't both truthfully `true` (unanswered, `false`, or partial), MFB cannot establish or rule out these remaining channels — a `false` value doesn't disprove them either. Committed inclusive handling, no scenario: assume the exclusion applies regardless, and don't track the unobservable 6-month Gate-1 usage history. |
| **Teen-parent student** (0210.015.35.15) | Parent under 19, full-time student in high school (or vocational/technical equivalent) — narrower than the child-student condition, and not the college/university channel MFB's fields can confirm. Earnings disregarded for both eligibility and grant amount; no 6-month cap, no gate carve-out | MFB has no field capable of establishing full-time secondary/vocational attendance for a parent under 19 (`student`/`student_full_time` confirm only college/university enrollment, a different fact). Committed inclusive handling, no scenario: assume a household head or parent under 19 with reported earned income meets this condition; earnings disregarded entirely. |

- **Source:** [0210.015.35.10](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-015-35-10/) — *"Exclude all earned income of any child (not including a payee or second parent) receiving a Temporary Assistance cash grant, if the child is a full-time STUDENT or is a part-time student who is not a full-time employee."* [0210.015.35.15](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-015-35-15/) — *"Parents under age 19 who are full-time students in high school, or the equivalent vocational or technical school, have all of their earnings disregarded in determining Temporary Assistance eligibility and grant amount when they apply or receive as the caretaker of their own children."*

**Implementation note:** sending a dependent child's or an under-19 head's real earned income truthfully, PE excludes it from `mo_tanf_countable_income` on its own — `is_in_secondary_school`/`is_full_time_student` are inert for this exclusion and do not need to be set for it. Those two inputs remain necessary for a different, genuinely load-bearing purpose — the age-18 dependent-child tax-unit-dependency test (see `mo_tanf_implementation_notes.md` mechanics item 2) — set them for that reason, independent of this exclusion.

### Step 7 — New-spouse disregard

When an active TA participant marries, the new spouse's income and resources are disregarded entirely for 6 consecutive benefit months — once-in-a-lifetime for the recipient who marries, applied to both spouses if both are active recipients at the marriage date, and applied before the recipient's own earned-income disregard.

**⚠️ Accepted PE limitation — income:** PolicyEngine has no concept of this disregard and counts a new spouse's income in full at every gate, the same as any other household member's, regardless of marriage timing. This is a disclosed, accepted limitation, not an MFB-side default. Scenarios 3, 4, 5, 22, and 25 use the `spouse` relationship but report no spouse income, so none of their expected values are affected; no executable scenario isolates this limitation.

**Committed treatment — resources (unaffected by the above):** Missouri disregards the new spouse's resources for the same 6-month period. `household_assets` is a single aggregate with no per-member ownership breakdown, so the spouse's share can't be isolated. Inclusive default: whenever a current TA recipient's household includes a `spouse` and `household_assets` exceeds the applicable resource tier (Criterion 7), treat the resource test as passed rather than denying on that basis alone — some unknown portion of the aggregate could belong to the disregarded spouse. This resource-side default is unchanged and unrelated to the income limitation above. No scenario — MFB cannot verify marriage timing; see "Data gaps with no executable scenario."

**Source:** [0210.015.30.22](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-015-30-22/).

### Step 8 — Sanction-based grant reductions

#### Step 8a — Child-support noncooperation reduction ⚠️ *data gap*

Missouri reduces the otherwise-payable TA grant by 25% when Child Support determines that an applicant/participant failed, without good cause, to cooperate in establishing paternity or a support order. A grant reduction, not an eligibility gate.

- **MFB fields:** none. **Committed treatment:** assume no active sanction; don't reduce the estimated grant. No scenario — not representable.
- **Source:** [13 CSR 40-2.330](https://www.law.cornell.edu/regulations/missouri/13-CSR-40-2-330).

#### Step 8b — Work-program noncompliance reduction ⚠️ *data gap*

Missouri reduces the TA grant by 50% following work-program noncompliance after conciliation. No active work-sanction status is collected.

- **Committed treatment:** assume no active work sanction; don't reduce the estimated grant. No scenario — not representable.
- **Concurrent-sanction interaction:** when both this sanction and Step 8a's are active at once, the total reduction is 50%, not 75% — they don't stack (8a alone remains 25%). Has no effect under the current no-sanction default, but must not be implemented as a stacked 75% reduction if sanction status is ever added as a screener input.
- **Source:** [13 CSR 40-2.315](https://www.law.cornell.edu/regulations/missouri/13-CSR-40-2-315); [0210.015.52](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-015-52/).

### Step 9 — Standard of Need test (Gate 2)

**Source note:** 13 CSR 40-2.310(11) controls this calculator's Gate-2 treatment. DSS Manual 0210.010.10 and the FFY 2026–27 State Plan describe a conflicting calculation; the calculator follows the codified regulation.

13 CSR 40-2.310(9)(A) numbers its disregards: **(9)(A)1** child-student/teen-parent exclusion (Step 6, not a work exemption); **(9)(A)2** $90 work exemption; **(9)(A)3–4** $30-plus-⅓ and its 8-month continuation; **(9)(A)5** care-cost deduction. The two-thirds disregard sits separately at **(9)(D)**. Subsection (11) excludes "(9)(A)2.–5." at this gate ($90, care deduction, $30-plus-⅓) but permits (9)(A)1 and doesn't mention (9)(D) — so the two-thirds disregard is **not excluded** here for an active participant.

**(9)(C)2) exception for the not-active branch:** (11) excludes (9)(A)2.–5. "except paragraphs (9)(C)1. and 2. would have application." (9)(C)2 restores *only* the $30-plus-⅓ piece at this gate for a not-active participant if they received TA in one or more of the 4 preceding months and haven't already used the disregard for 4 consecutive months — the same historical fact Step 3 flags as a data gap for the Gate-3 calculation (no field distinguishes "never on TA" from "off TA within 4 months").

**⚠️ Data gap:** consistent with Step 3's favorable-assumption pattern, the committed default is: if a not-active participant's raw gross earned income would otherwise fail Gate 2, apply the $30-plus-⅓ disregard before concluding the gate is failed — i.e., assume the (9)(C)2) exception applies whenever it would change the outcome. No dedicated scenario isolates this default; Scenario 33 exercises the same retry mechanism without it changing the outcome (Gate 2 still fails).

**Committed formula:** not-active participant → `gross_earned(member)`; if that fails Gate 2 alone, retry with `max((gross_earned(member) − 30) × 2/3, 0)` (the (9)(C)2) exception) before concluding the gate is failed. Active participant → `gross_earned(member) / 3` only — no (9)(C)2)-style retry (that exception is specific to (9)(A)3, not used by active participants at this gate). No care-cost deduction or $90 exemption apply here for either branch. Sum each employed member's Gate-2 figure with gross unearned income and compare to the Standard of Need.

`(sum over employed members of the applicable Gate-2 earned figure above) + gross_unearned_income < Standard_of_Need[need_unit_size]`

| Size | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Standard of Need | $393 | $678 | $846 | $990 | $1,123 | $1,247 | $1,372 | $1,489 | $1,606 | $1,722 | $1,839 | $1,956 |

| Size | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 |
|---|---|---|---|---|---|---|---|---|---|---|
| Standard of Need | $2,072 | $2,188 | $2,304 | $2,420 | $2,536 | $2,652 | $2,768 | $2,884 | $3,000 | $3,116 |

The official Appendix B values are published for sizes 1–22 — do not derive sizes 13–22 from a flat $116-per-additional-person increment; use the published figures directly. This calculator's binding scope is sizes 1–8 (see the scope note under Step 10); sizes 9–22 are published above as reference material, and a household size above 22 is not addressed by any source reviewed.

**Source:** 13 CSR 40-2.310(11), (9)(A)1–5, (9)(C)1–2, (9)(D); [0210.015.30.20](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-015-30-20/); [0210.015.30.10](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-015-30-10-30/); [0210.010.10](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-010-10/) (worked example — not followed; see disclosed conflict above). **Operative quotations:** 13 CSR 40-2.310(11) — *"without application of the earned income disregards provided for in paragraphs (9)(A)2.–5., except paragraphs (9)(C)1. and 2. would have application,"* i.e., the $90 exemption, the $30-plus-⅓ sequence, and the care-cost deduction are all unavailable at this gate, except that (9)(C)2) restores the $30-plus-⅓ piece for a qualifying not-active participant; the two-thirds disregard (9)(D)) is not listed and is not excluded. 13 CSR 40-2.310(9)(C)2 — the $30-plus-⅓ disregard "shall not be applied if the income without applying this disregard was in excess of the standard of need, unless the person received TA in one (1) or more of the four (4) preceding such months" and the disregard has not already been used for four consecutive months. 0210.015.30.20 — for an active participant, "eligibility and grant amount are determined using the two-thirds disregard."

### Step 10 — Percentage of Need test (Gate 3, determines the grant)

A household with `countable_income ≥ payment_standard` (deficit ≤ $0) fails Gate 3 on the merits and is `eligible: false` — this is one of the three income tests 13 CSR 40-2.310(13) requires the household to pass, not a payment-mechanics question. For a household that does pass Gate 3 (a positive deficit), `benefit = floor(payment_standard − countable_income)`; if that floored result is $9.99 or less, the household is `eligible: false` with no value — see the source-hierarchy resolution below.

**Source note:** a sub-$10 result is `eligible: false`, not `eligible: true`/`$0`. 13 CSR 40-2.310(14) says only that "no cash payment will be made" below $10 — silent on case status. The operational manual fills that silence: *"the deficit is $9.99 or less, in which case no cash payment is made ... This case is not eligible for Temporary Assistance"* ([0210.020.00](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-020-00/)). Governing principle: the codified regulation controls an explicit computation it actually states; manual guidance may resolve a status question the regulation leaves silent, but can't override an explicit regulatory computation — which is why this follows the manual (resolving a silence) while Gate 2 follows the regulation instead (where the regulation is explicit and a manual example contradicts it).

| Size | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Payment standard (Appendix B) | $136 | $234 | $292 | $342 | $388 | $431 | $474 | $514 | $554 | $595 | $635 |

| Size | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Payment standard (Appendix B) | $675 | $715 | $755 | $795 | $835 | $875 | $915 | $955 | $995 | $1,035 | $1,075 |

The official Appendix B values are published for sizes 1–22 — do not derive or round these from the 34.526%-of-Standard-of-Need percentage (Appendix B's own rounding is not always to the nearest dollar; e.g., size 16's raw value of $835.53 is published as $835, not $836). A public Missouri DSS flyer lists $517 for size 8; the codified regulation and Appendix B agree on $514 — use $514. Only the final deficit (ceiling − countable income) is floored to a whole dollar; the ceiling itself needs no further rounding.

**Binding calculator scope — sizes 1–8:** this calculator version supports, and is scenario-tested through, household size 8 only. All sources agree on the Gross Max, Standard of Need, and payment-standard figures through size 8, and those figures are binding for this version. Sizes 9–22 are published above as reference material but are not binding for this version — a future version expanding beyond size 8 should re-verify those figures against DSS's then-current Appendix B/C before binding to them, since the codified regulation and archived Appendix B PDF give a different size-22 payment standard ($1,075) than DSS's current (August 2024) Appendix C ($1,073).

**Source:** [0210.010.15](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-010-15/); [0210.020.00](https://dssmanuals.mo.gov/temporary-assistance-case-management/0210-020-00/); [Appendix B](https://dssmanuals.mo.gov/wp-content/uploads/2019/04/TA-AppendixB.pdf); 13 CSR 40-2.310(13)–(14). **Operative quotation:** *"Subtract countable income from this [payment standard] amount to determine grant amount... round the deficit to the next lower dollar... When a Temporary Assistance grant amount would be less than $10, no payment is made."* 13 CSR 40-2.310(13) — eligibility is established once the three income tests in (10)–(12) are each satisfied. 13 CSR 40-2.310(14) — *"In the payment of TA benefits, the amount shall always be lowered to the nearest dollar interval. If the determined amount results in a grant of less than ten dollars ($10), no cash payment will be made."* 0210.020.00 — *"the grant amount is the deficit rounded to the next lower dollar unless the deficit is $9.99 or less, in which case no cash payment is made ... This case is not eligible for Temporary Assistance."* The manual's explicit case-status conclusion controls the eligibility question the regulation itself leaves silent — see the resolution above.

### Gate interaction

Gate 2 uses a much less-disregarded income figure than Gate 3, so it must be evaluated independently and can deny a household that passes Gates 1 and 3 — it must never be treated as automatically satisfied merely because Gate 3 passes. Scenario 33 demonstrates this: the household passes Gates 1 and 3 but fails Gate 2 even after the `(9)(C)2)` retry.

### First-month proration

Divide the full monthly grant by 30, multiply by the number of days from the application date (inclusive) through month-end, round down, and apply the $10 floor to the prorated amount. If the 30th day from application still falls within the application month, pay the full month's grant instead.

**Committed treatment:** the screener has no application-date field; the calculator evaluates a household as of a snapshot, so proration does not apply.

**Source:** [0220.010.10](https://dssmanuals.mo.gov/temporary-assistance-case-management/0220-010-10/). **Operative quotation:** *"Divide the grant amount determined for an entire month by 30"*; *"Multiply the result by the number of days from the date of application (including the date of application) through the end of the month"*; *"The result, rounded down to the lower dollar, is the prorated amount to be paid for the month of application"*; *"If this amount is less than $10, the family is not eligible for a cash payment in that month."*

### Cadence

TA is paid at regular monthly intervals.

## Acceptance Criteria

**Eligibility gates and unit construction**

- [ ] 1. A household without a qualifying dependent child is ineligible; pregnancy alone does not qualify.
- [ ] 2. Missouri need-unit size controls the Standard of Need, payment-standard, and Gross Max tables.
- [ ] 3. SSI recipients are excluded from needs, income, resources, and need-unit size.
- [ ] 4. The official Appendix B values are used for the calculator's binding sizes 1–8; sizes 9–22 are not binding for this version.
- [ ] 5. The three-gate income test (see Benefit Value gate summary) is applied as follows:
  - Gate 1: gross countable income strictly less than the Gross Max.
  - Gate 2: income with no disregard (not-active; falling back to $30-plus-⅓ alone under (9)(C)2) if needed) or only the two-thirds disregard (active) — never $90 or care-cost, either branch — strictly less than the Standard of Need. Evaluated independently; never assumed satisfied merely because Gate 3 passes.
  - Gate 3: fully-disregarded income strictly less than the payment standard (a positive deficit); failing on the merits (deficit ≤ $0) is `eligible: false`.
  - The $10 floor (AC 8) is a separate, later step applying only once Gate 3 is otherwise passed.

**Income and earnings treatment**

- [ ] 6. The not-active-participant and active-participant earned-income calculations are each applied separately per employed household member, not once against combined household earnings.
- [ ] 7. The child/incapacitated-care deduction cap is $200/month for a child under age 2, $175/month for a child age 2 or older, and $175/month for incapacitated-parent care, applied per person to actual cost.
- [ ] 8. For a household that otherwise passes Gate 3 (a positive deficit), a floored deficit of $9.99 or less results in `eligible: false` with no value, per 0210.020.00's explicit case-status conclusion (Benefit Value Step 10) — this is distinct from, but reaches the same practical outcome (no payment) as, failing Gate 3 outright (deficit ≤ $0), which is also `eligible: false`.

**PolicyEngine inputs and calculator output**

- [ ] 9. Current TA receipt triggers the active-participant treatment described in Benefit Value, while households not currently receiving TA use the not-active-participant treatment.
- [ ] 10. The calculator returns a monthly benefit amount.
- [ ] 11. Every finalized executable scenario's final MFB result matches the scenario's expected eligibility and value — for Scenarios 8, 20, and 32, the expected value is the accepted live PolicyEngine result (Acceptance Criterion 31), not the strict-regulation comparison shown in each scenario's policy note.

**Resources and assets**

- [ ] 12. When a current TA recipient's household includes a `spouse` and reported `household_assets` exceeds the applicable resource tier (Criterion 7), the household isn't excluded on `household_assets` alone. (This resource-side default is independent of the new-spouse income disregard, which is an accepted PE limitation — see AC 23.)

**Care deductions**

- [ ] 13. The aggregate `childCare` expense is qualifying care for the unit's included children, capped at the sum of applicable per-child caps ($200 under 2, $175 age 2+) — not a flat per-household cap, not across excluded children.
- [ ] 14. The aggregate `dependentCare` expense is capped at $175 per qualifying incapacitated person in the included unit.
- [ ] 15. No incapacitated-care deduction is applied solely on a `disabled`/`long_term_disability` flag — a `dependentCare` expense must be reported.

**Household composition and unobservable data gaps**

- [ ] 16. `household_members.student`/`student_full_time` confirm only post-secondary enrollment; a `false` value never disproves the child-student exclusion (also satisfied via secondary/vocational attendance or the part-time-not-full-time-employee test) or the teen-parent exclusion's secondary-school condition — both exclusions apply on age/relationship alone.
- [ ] 17. Current MFB relationship enum values are used throughout, not retired ones:
  - Includes `sisterOrBrother`, `stepSisterOrBrother`, `stepChild`, `relatedOther` — not retired `sibling`/`other`.
  - A qualifying child coded `relatedOther` or `fosterChild` relative to the head has a qualifying caretaker relationship (Criterion 3).
  - `fosterChild` alone doesn't imply receipt of foster-care maintenance payments (Criterion 4).
- [ ] 18. Work-sanction-requalification and earned-income-disregard-disqualification history are unobservable data gaps: assume no active requalification restriction and no disqualifying event (Criterion 14; Benefit Value Step 3).

**Self-employment and NPCR**

- [ ] 19. A reported `selfEmployment` amount is net self-employment profit, included directly in earned income at every gate — no second business-expense deduction.
- [ ] 20. NPCR neediness and election:
  - Not run unconditionally: automatically needy (no neediness budget) when the NPCR's spouse isn't in the household or receives SSI/SSI-SP.
  - When needy (either path), compute both valid unit configurations (NPCR included/excluded, each a truthful PE call) and return the higher eligible monthly grant.
  - Failing neediness → exclusion is mandatory, no elective comparison.
  - Spouse cooperation with the neediness determination is assumed.

**Other income sources**

- [ ] 21. A reported `childSupport` amount is counted as unearned income at the reported received/sent amount for both pending and active cases; the active-case CSE/DFAS-retained trial-budget amount is an unobservable data gap, not imputed (Criterion 8).

**Resources and assets (continued)**

- [ ] 22. The countable-resource limit is $1,000 for every household, current TA recipients included — PolicyEngine's flat `mo_tanf_resources_eligible` test is shipped as-is. The $5,000 IEP tier is an accepted PE limitation, not implemented (Criterion 7).
- [ ] 23. The new-spouse income disregard is an accepted PE limitation, not implemented — a new spouse's income is counted at Gate 1 and every other gate the same as any other household member's (Benefit Value Step 7).
- [ ] 24. When a reported SSI/SP/SAB member is present and aggregate `household_assets` exceeds the $1,000/$5,000 tier, the household isn't excluded on `household_assets` alone.

**Assistance-unit and household-composition outcomes**

- [ ] 25. A non-dependent 18+ sibling excluded under Criterion 1 doesn't affect eligibility or benefit result (Scenario 15). A sibling's own excluded income doesn't count against the remaining unit either — committed inclusive default, no executable scenario.
- [ ] 26. An 18-year-old dependent child qualifying under Criterion 1's inclusive default is included in the unit with their caretaker. Committed inclusive default, no executable scenario — MFB cannot establish secondary-school/equivalent attendance or marital history for an 18-year-old.
- [ ] 27. The new-spouse income disregard is an accepted PE limitation (AC 23) — a new spouse's income is counted at every gate like any other member's; no data-gap default applies to it.
- [ ] 28. A household passing the resource test under Criterion 7 isn't denied by a stricter flat resource check, when the new-spouse resource disregard (Step 7) or the SSI/SP/SAB aggregate-resource default (Criterion 4 / AC 24) is active. Committed inclusive default, no executable scenario — MFB cannot verify marriage timing or isolate the SSI member's share of the aggregate.
- [ ] 29. NPCR election (AC 20) reaching the genuinely-elective case returns whichever configuration produces the higher eligible benefit — not resolved by a static rule (Scenarios 10, 11, 12).
- [ ] 30. Income-source treatment matches Criterion 8's table: `rental` is earned income at every gate (committed inclusive default, no executable scenario — MFB cannot establish the ≥20-hrs/week management fact); `investment` doesn't affect eligibility or value (committed inclusive default, no executable scenario — MFB cannot separate interest/dividend/capital-gain components); `cashAssistance` representing the household's own `mo_tanf` grant doesn't affect its own recalculation (Scenario 31), otherwise it's counted as unearned income (Scenario 35).

**Accepted PolicyEngine divergences**

- [ ] 31. Scenarios 8, 20, and 32's expected value (AC 11) is PolicyEngine's live response, per each scenario's divergence note. No MFB-side override is implemented for these or any other scenario — a disclosed, accepted accuracy gap at these exact input patterns, not a silently-produced wrong answer.

## Test Scenarios

Age shorthand: unless otherwise noted, `birth_month = 1` and `birth_year = 2026 − age`, evaluated against this spec's Year 2026.

### Scenario 1: Golden path — primary regression test

**What we're checking**: Baseline eligibility and grant with no income, at household size 3.
**Expected**: Eligible — $292/month (size-3 household, no income; payment standard $292, Appendix B size 3).
**Steps**:
* Household size: `3`
* Person 1: Birth month/year `January 1996` (age 30), `headOfHousehold`, no income
* Person 2: Birth month/year `January 2020` (age 6), `child`, no income
* Person 3: Birth month/year `January 2023` (age 3), `child`, no income
* `current_benefits` does not include `mo_tanf`

**Why this matters**: Primary regression test — confirms the basic no-income calculation and the size-3 payment-standard lookup work correctly together.

### Scenario 2: No dependent child

**What we're checking**: Criterion 1's dependent-child gate.
**Expected**: Not eligible — no dependent child in the household.
**Steps**:
* Household size: `1`
* Person 1: Birth month/year `January 1996` (age 30), `headOfHousehold`, no income, `pregnant: false`

**Why this matters**: Confirms a household with no qualifying child is rejected outright, independent of any income test.

### Scenario 3: Not-active-participant earned-income calculation, two-parent household

**What we're checking**: The not-active-participant sequential $30-plus-1/3 disregard order.
**Expected**: Eligible — $222/month (`R = 300 − 90 = 210`; countable `= (210 − 30) × 2/3 = 120`; deficit `= 342` (size-4 payment standard) `− 120 = 222`).
**Steps**:
* Household size: `4`
* Person 1: Birth month/year `January 1996` (age 30), `headOfHousehold`, earner, wages: $300/month
* Person 2: Birth month/year `January 1996` (age 30), `spouse`, no income
* Person 3: Birth month/year `January 2020` (age 6), `child`, no income
* Person 4: Birth month/year `January 2023` (age 3), `child`, no income
* `current_benefits` does not include `mo_tanf`

**Why this matters**: Validates the not-active-participant sequential disregard order ($90, then $30, then two-thirds) for an individual who was not an active TA participant when they became employed.

### Scenario 4: Active-participant earned-income calculation, same household

**What we're checking**: The active-participant disregard order, on the identical household as Scenario 3.
**Expected**: Eligible — $332/month (`countable = max(300 ÷ 3 − 90, 0) = 10`; deficit `= 342 − 10 = 332`).
**Steps**:
* Same household as Scenario 3
* `current_benefits` includes `mo_tanf`

**Why this matters**: Confirms the active-participant calculation applies the two-thirds disregard in the reversed order from the not-active-participant calculation, on the same underlying household as Scenario 3, isolating the active-participant-status branch as the only variable.

### Scenario 5: Active-participant two-thirds treatment at Gate 2

**What we're checking**: The active-participant two-thirds treatment is actually applied at Gate 2, not just at Gate 3: the head's wages are set high enough ($1,200/month) that the raw, undisregarded figure fails Gate 2 against the size-4 Standard of Need ($1,200 ≥ $990), so this scenario only passes if the two-thirds disregard (`gross_earned / 3 = $400`) is actually applied at Gate 2. The spouse has no income, so this scenario doesn't depend on the new-spouse disregard (Step 7) — it isolates the Gate-2 treatment alone.
**Expected**: Eligible — $32/month (Gate 1: gross countable income $1,200 under the size-4 Gross Max of $1,832. Gate 2: `$1,200 ÷ 3 = $400 < $990` size-4 Standard of Need → passes. Gate 3: `after_two_thirds = 1,200 ÷ 3 = 400`; `countable = max(400 − 90, 0) = 310`; deficit `= 342 − 310 = 32`).
**Steps**:
* Same household as Scenario 4, except:
* Person 1 (`headOfHousehold`): wages $1,200/month
* Person 2 (`spouse`): no income
* `current_benefits` includes `mo_tanf`

**Why this matters**: Confirms the active-participant two-thirds treatment at Gate 2 is load-bearing on its own. Scenario 4 stays unchanged at $300/month wages, where its purpose remains clean: comparing the active calculation to Scenario 3's not-active calculation on the same household.

### Scenario 6: Applicant resource limit at the boundary

**What we're checking**: The $1,000 applicant resource limit, at the exact boundary.
**Expected**: Eligible — $234/month (liquid assets exactly at the $1,000 limit — passes; no income, size-2 payment standard $234).
**Steps**:
* Household size: `2`, assets: $1,000
* Person 1: Birth month/year `January 1996` (age 30), `headOfHousehold`, no income
* Person 2: Birth month/year `January 2020` (age 6), `child`, no income
* `current_benefits` does not include `mo_tanf`

**Why this matters**: Confirms the $1,000 applicant resource limit is enforced correctly at the exact boundary (passes, not fails).

### Scenario 7: Applicant with assets between the tiers

**What we're checking**: The $1,000 tier applies to applicants regardless of IEP status — it doesn't jump to $5,000 just because that tier exists for someone else.
**Expected**: Not eligible — $4,000 exceeds the $1,000 applicant-tier limit; the $5,000 tier only applies to current recipients.
**Steps**:
* Same as Scenario 6, except assets: $4,000

**Why this matters**: Confirms an applicant (not a current recipient) never gets the benefit of the $5,000 participant tier. The $5,000 tier itself has no executable scenario — see Criterion 7 — for two independent reasons: MFB cannot verify the active-IEP fact the tier depends on, and PolicyEngine's flat resource test has no path to apply a $5,000 tier at all (an accepted PE limitation, not implemented).

### Scenario 8: Gate 3 exact-equality boundary

**What we're checking**: Failure of the Percentage of Need test (Gate 3) at the exact equality boundary, isolated from Gates 1 and 2 — countable income exactly equal to the payment standard is a deficit of $0, which fails the strict `<` comparator.
**Expected**: Eligible — $0.00/month — the calculator ships PolicyEngine's live result as-is for this exact boundary (see divergence note below).
**Policy note (strict regulation):** Gate 1: $471 < $1,254 ✓ (size 2 Gross Max); Gate 2 (not-active participant, no disregard applies at this gate): $471 < $678 ✓ (size 2 Standard of Need); Gate 3: `R = 471 − 90 = 381`; countable `= (381 − 30) × 2/3 = 234`; `$234 ≥ $234` payment standard → deficit `= 0` → fails on the merits under strict Missouri regulation, `eligible: false`.
**Steps**:
* Household size: `2`
* Person 1: Birth month/year `January 1996` (age 30), `headOfHousehold`, wages: $471/month
* Person 2: Birth month/year `January 2020` (age 6), `child`, no income
* `current_benefits` does not include `mo_tanf`

**Why this matters**: Pins the strict `<` comparator at Gate 3 at the exact boundary under Missouri's own regulation — countable income equal to (not merely above) the payment standard fails on the merits, isolating Gate 3 as the binding constraint since the household passes both Gate 1 and Gate 2. See the divergence note below for PolicyEngine's accepted departure from this result.

**PE divergence from strict Missouri regulation — accepted, no MFB override:** Under strict application of Missouri's regulation (see policy note above), this exact boundary is `eligible: false`. PolicyEngine's live formula-based Standard-of-Need calculation instead returns `eligible: true, $0.00` — a permanent characteristic of that approach (as opposed to a table lookup), not a scenario-specific bug. This is a disclosed, accepted accuracy gap at this exact input pattern (Acceptance Criterion 31), narrow in scope — it should not be extended to other scenarios without the same root-causing.

### Scenario 9: Not-active-participant earned-income calculation, smaller household

**What we're checking**: The not-active-participant calculation at household size 2 (as opposed to size 4 in Scenario 3).
**Expected**: Eligible — $114/month (`R = 300 − 90 = 210`; countable `= (210 − 30) × 2/3 = 120`; deficit `= 234 − 120 = 114`).
**Steps**:
* Household size: `2`
* Person 1: Birth month/year `January 1996` (age 30), `headOfHousehold`, wages: $300/month
* Person 2: Birth month/year `January 2020` (age 6), `child`, no income
* `current_benefits` does not include `mo_tanf`

**Why this matters**: Confirms the same not-active-participant formula validated in Scenario 3 also scales correctly to a smaller household size.

### Scenario 10: Kinship caretaker, NPCR included

**What we're checking**: The `grandParent`/`grandChild` relationship encoding, and the NPCR-included configuration when inclusion is the better unit.
**Expected**: Eligible — $292/month (no income, so including the grandparent, size 3, $292, is at least as good as excluding them, size 2, $234; the NPCR election favors inclusion here).
**Steps**:
* Household size: `3`
* Person 1: Birth month/year `January 1971` (age 55), `headOfHousehold`, no income
* Person 2: Birth month/year `January 2020` (age 6), `grandChild`, no income
* Person 3: Birth month/year `January 2018` (age 8), `grandChild`, no income
* `current_benefits` does not include `mo_tanf`

**Why this matters**: Confirms the kinship-caretaker relationship encoding works and that the NPCR election correctly chooses inclusion when there's no income to make exclusion the better option.

### Scenario 11: NPCR automatic-needy exception, elective exclusion

**What we're checking**: The automatic-needy exception (no spouse in the household) followed by the elective best-of-two-units choice — not an income-based neediness budget, since no spouse is present to budget against.
**Expected**: Eligible — $234/month, via the excluded (child-only) configuration (no spouse in the household → NPCR is automatically needy, no neediness budget is run → elective choice applies; included, size 3: $292 − $100 = $192/month; excluded, size 2: $234/month; return the higher: $234).
**Steps**:
* Same household as Scenario 10, except:
* Person 1 (`headOfHousehold`, grandparent, no spouse present): unemployment income $100/month
* `current_benefits` does not include `mo_tanf`

**Why this matters**: Confirms that a spouse-absent NPCR is deemed needy automatically (not via an income comparison), and that the calculator still compares both valid unit configurations and returns the higher grant rather than defaulting to inclusion.

**⚠️ Pending PolicyEngine — not yet the shipped result:** PolicyEngine has no NPCR concept, so a qualifying caretaker is always an assistance-unit member and no neediness budget or election is run (AC 20). Until PE models it, this household returns the caretaker-included result. The expected value above is what the calculator should return once PE ships; the scenario's test is skipped in the meantime.

### Scenario 12: NPCR mandatory non-needy exclusion

**What we're checking**: The mandatory-exclusion branch, which requires a co-resident spouse to trigger the neediness budget at all (the automatic-needy exception in Scenario 11 applies whenever no spouse is present, so this branch cannot be tested without one).
**Expected**: Eligible — $234/month, via mandatory exclusion (NPCR + co-resident spouse neediness group, size 2, Standard of Need $678; countable income $700 ≥ $678 → not needy → NPCR must be excluded, no elective comparison; remaining cash group is the two grandchildren, size 2: $234).
**Steps**:
* Household size: `4`
* Person 1: Birth month/year `January 1971` (age 55), `headOfHousehold` (grandparent NPCR), unemployment income $700/month
* Person 2: Birth month/year `January 1973` (age 53), `spouse`, no income
* Person 3: Birth month/year `January 2020` (age 6), `grandChild`, no income
* Person 4: Birth month/year `January 2018` (age 8), `grandChild`, no income
* `current_benefits` does not include `mo_tanf`

**Why this matters**: Confirms that when a co-resident spouse triggers the neediness budget and the NPCR/spouse group fails it, exclusion is mandatory — the calculator must not offer an elective comparison in this branch.

**⚠️ Pending PolicyEngine — not yet the shipped result:** PolicyEngine has no NPCR concept, so a qualifying caretaker is always an assistance-unit member and no neediness budget or election is run (AC 20). Until PE models it, this household returns the caretaker-included result. The expected value above is what the calculator should return once PE ships; the scenario's test is skipped in the meantime.

### Scenario 13: SSI child, payee-only unit

**What we're checking**: SSI exclusion from needs, income, resources, and need-unit size, for the SSI-child branch.
**Expected**: Eligible — $136/month, via a payee-only unit (the SSI child is the household's only otherwise-eligible TA child; excluded from the unit; the payee still receives a payee-only grant sized to the remaining size-1 unit).
**Steps**:
* Household size: `2` (raw), need-unit size `1` after SSI exclusion
* Person 1: Birth month/year `January 1996` (age 30), `headOfHousehold`, no income
* Person 2: Birth month/year `January 2016` (age 10), `child`, SSI: $750/month

**Why this matters**: Confirms the SSI exclusion still produces a payee-only grant when the SSI recipient is the only qualifying child, rather than incorrectly zeroing out the whole household.

### Scenario 14: Larger household, official table

**What we're checking**: The official-table-vs-raw-percentage correction, at household size 5.
**Expected**: Eligible — $388/month (size-5 payment standard, Appendix B: $388, not the raw $387.73).
**Steps**:
* Household size: `5`
* Person 1: Birth month/year `January 1996` (age 30), `headOfHousehold`, no income
* Person 2: Birth month/year `January 2020` (age 6), `child`, no income
* Person 3: Birth month/year `January 2018` (age 8), `child`, no income
* Person 4: Birth month/year `January 2016` (age 10), `child`, no income
* Person 5: Birth month/year `January 2014` (age 12), `child`, no income
* `current_benefits` does not include `mo_tanf`

**Why this matters**: Confirms the calculator uses the official Appendix B payment-standard table at size 5, not a raw percentage-of-Standard-of-Need derivation, which would produce a different cents-level result.

### Scenario 15: Non-qualifying sibling excluded

**What we're checking**: Need-unit-size filtering excludes a non-dependent, non-qualifying older child from headcount. (This person is the dependent child's sibling — relative to `headOfHousehold`, both are coded the head's `child`, since `sisterOrBrother` would instead mean "the head's own sibling.") This person is excluded on **age alone** — exactly 19 fails Criterion 1's "under 19" test regardless of student status, so this scenario does not depend on (and does not report) `student`/`student_full_time`, which cannot establish secondary-school status in any case — see Benefit Value Step 6.
**Expected**: Eligible — $234/month, size 2 (the 19-year-old is excluded from headcount as a non-dependent, non-qualifying member, on age alone).
**Steps**:
* Household size: `3` (raw), need-unit size `2` after exclusion
* Person 1: Birth month/year `January 1996` (age 30), `headOfHousehold`, no income
* Person 2: Birth month/year `January 2016` (age 10), `child`, no income
* Person 3: Birth month/year `January 2007` (age 19), `child`, no income
* `current_benefits` does not include `mo_tanf`

**Why this matters**: Confirms need-unit filtering correctly drops a non-qualifying older sibling from the headcount used to look up the Standard of Need, Gross Max, and payment standard.

### Scenario 16: Pregnancy alone is not a qualifying pathway

**What we're checking**: Criterion 1's pregnancy exclusion — that pregnancy alone, without a qualifying dependent child, does not establish eligibility.
**Expected**: Not eligible — 13 CSR 40-2.325 requires a dependent child; pregnancy alone is not an independent basis.
**Steps**:
* Household size: `1`
* Person 1: Birth month/year `January 2001` (age 25), `headOfHousehold`, no income, `pregnant: true`

**Why this matters**: Confirms Missouri's dependent-child requirement and ensures pregnancy alone does not create eligibility.

### Scenario 17: Childcare deduction below the cap

**What we're checking**: The childcare deduction when actual cost is below the $175 cap.
**Expected**: Eligible — $214/month (`R = 300 − 90 = 210`; countable before care `= (210 − 30) × 2/3 = 120`; countable `= max(120 − 100, 0) = 20`; deficit `= 234 − 20 = 214`).
**Steps**:
* Household size: `2`
* Person 1: Birth month/year `January 1996` (age 30), `headOfHousehold`, wages: $300/month
* Person 2: Birth month/year `January 2020` (age 6), `child`, no income
* Expense: `childCare`, $100/month
* `current_benefits` does not include `mo_tanf`

**Why this matters**: Confirms the childcare deduction is applied dollar-for-dollar when actual cost is below the cap, rather than always applying the full cap regardless of reported cost.

### Scenario 18: Childcare deduction capped

**What we're checking**: The $175 cap when actual cost exceeds it. Earnings are set high enough that countable-before-care income exceeds $175, so the exact cap amount is observable in the result (unlike a lower-earnings household, where any cap ≥ the pre-care countable amount produces the same $0 regardless of its exact value).
**Expected**: Eligible — $109/month (`R = 570 − 90 = 480`; countable before care `= (480 − 30) × 2/3 = 300`; actual cost $300 exceeds the $175 cap, so `countable = max(300 − 175, 0) = 125`; deficit `= 234 − 125 = 109`).
**Steps**:
* Household size: `2`
* Person 1: Birth month/year `January 1996` (age 30), `headOfHousehold`, wages: $570/month
* Person 2: Birth month/year `January 2020` (age 6), `child`, no income
* Expense: `childCare`, $300/month
* `current_benefits` does not include `mo_tanf`

**Why this matters**: Confirms the $175 cap actually binds (rather than deducting the full reported cost) once reported cost exceeds it.

### Scenario 19: $10 minimum-payment floor, exact boundary

**What we're checking**: The $10 minimum floor at the boundary where payment is still made.
**Expected**: Eligible — $10/month (`R = 456 − 90 = 366`; countable `= (366 − 30) × 2/3 = 224`; deficit `= 234 − 224 = 10`).
**Steps**:
* Household size: `2`
* Person 1: Birth month/year `January 1996` (age 30), `headOfHousehold`, wages: $456/month
* Person 2: Birth month/year `January 2020` (age 6), `child`, no income
* `current_benefits` does not include `mo_tanf`

**Why this matters**: Confirms the $10 floor is inclusive — a deficit of exactly $10 still produces a payment, not a denial.

### Scenario 20: $10 floor, one dollar over the boundary

**What we're checking**: That a deficit of $9.99 or less results in `eligible: false`, not a suppressed-but-still-eligible $0 payment.
**Expected**: Eligible — $0.00/month — the calculator ships PolicyEngine's live result as-is for this exact boundary (see divergence note below).
**Policy note (Missouri's committed policy treatment):** `R = 457 − 90 = 367`; countable `= (367 − 30) × 2/3 = 224.67`; deficit `= 234 − 224.67 = 9.33` ≤ $9.99 → per 0210.020.00's explicit case-status conclusion (the regulation itself is silent on eligibility status below $10, see Benefit Value Step 10), this is `eligible: false`, not `eligible: true, value: $0`.
**Steps**:
* Same as Scenario 19, except wages: $457/month

**Why this matters**: Confirms Missouri's committed policy treatment of a sub-$10 deficit as ineligible, based on the current DSS manual's explicit case-status rule where the regulation itself is silent. See the divergence note below for PolicyEngine's accepted departure from this result.

**PE divergence from Missouri's committed policy treatment — accepted, no MFB override:** Under Missouri's committed policy treatment (see policy note above), this exact boundary is `eligible: false`. Same rounding character as Scenarios 8 and 32: PolicyEngine's continuous formula-based calculation doesn't land on a clean deficit at this exact-dollar boundary the way Missouri's discrete floor test does — a permanent characteristic of PolicyEngine's formula-based approach, not a scenario-specific bug. This is a disclosed, accepted accuracy gap at this exact input pattern (Acceptance Criterion 31) — narrow in scope, do not generalize without the same root-causing.

### Scenario 21: Child-student earned-income exclusion, truthful full-time-college-student channel

**What we're checking**: The child-student earnings exclusion affects eligibility itself, not just grant value — and, unlike the general inclusive default (a true data gap, no scenario — see Benefit Value Step 6), this specific input combination truthfully confirms one of Missouri's own qualifying channels: `student: true` and `student_full_time: true` on a dependent child directly reports full-time enrollment at a college/university, which 0210.015.35.10 explicitly recognizes ("at school/college/university," not secondary school alone). No assumption is required for this scenario.
**Expected**: Eligible — $234/month (the child's earnings are excluded from both Gate 1 and the grant calculation, leaving countable income at $0).
**Steps**:
* Household size: `2`
* Person 1: Birth month/year `January 1996` (age 30), `headOfHousehold`, no income
* Person 2: Birth month/year `January 2010` (age 16), `child`, `student: true`, `student_full_time: true`, wages: $1,300/month
* `current_benefits` does not include `mo_tanf`

**Why this matters**: Confirms the child-student exclusion applies at Gate 1 as well as the grant calculation for a genuinely observed qualifying fact — without it, $1,300/month would fail the household outright. This scenario is deliberately built on a truthful `student`/`student_full_time` report, not the inclusive default that applies when those fields are unanswered, `false`, or partial (a true data gap with no scenario — the remaining channels of 0210.015.35.10 aren't representable, and neither is the 6-month Gate-1 usage cap).

### Scenario 22: Two-earner calculation — not-active-participant default

**What we're checking**: The $90 exemption and $30-plus-1/3 disregard are applied per earner, not combined.
**Expected**: Eligible — $168/month (earner 1 countable `= (210 − 30) × 2/3 = 120`; earner 2 countable `= (110 − 30) × 2/3 ≈ 53.33`; total `≈ 173.33`; deficit `= 342 − 173.33 ≈ 168.67`, floored to $168. If deductions were instead computed once against the combined $500, the deficit would floor to $88 — this scenario exists to catch that error).
**Steps**:
* Household size: `4`
* Person 1: Birth month/year `January 1996` (age 30), `headOfHousehold`, earner 1, wages: $300/month
* Person 2: Birth month/year `January 1996` (age 30), `spouse`, earner 2, wages: $200/month
* Person 3: Birth month/year `January 2020` (age 6), `child`, no income
* Person 4: Birth month/year `January 2023` (age 3), `child`, no income
* `current_benefits` does not include `mo_tanf`

**Why this matters**: Confirms the calculator disregards each employed member's earnings independently, rather than pooling household earnings before applying a single disregard.

### Scenario 23: Verified countable unearned income

**What we're checking**: Unearned income receives no work-exemption or disregard treatment.
**Expected**: Eligible — $34/month (Gate 1: $200 < $1,254 ✓; Gate 2: $200 < $678 ✓; deficit `= 234 − 200 = 34`).
**Steps**:
* Household size: `2`
* Person 1: Birth month/year `January 1996` (age 30), `headOfHousehold`, unemployment income: $200/month
* Person 2: Birth month/year `January 2020` (age 6), `child`, no income
* `current_benefits` does not include `mo_tanf`

**Why this matters**: Confirms unearned income passes straight through to all three gates with no $90 exemption or disregard applied, unlike earned income.

### Scenario 24: Official size-8 payment standard

**What we're checking**: The official Appendix B value at size 8.
**Expected**: Eligible — $514/month (size-8 payment standard, Appendix B: $514 — not the raw $514.09, and not the flyer's erroneous $517).
**Steps**:
* Household size: `8`
* Person 1: Birth month/year `January 1996` (age 30), `headOfHousehold`, no income
* Person 2: Birth month/year `January 2024` (age 2), `child`, no income
* Person 3: Birth month/year `January 2022` (age 4), `child`, no income
* Person 4: Birth month/year `January 2020` (age 6), `child`, no income
* Person 5: Birth month/year `January 2018` (age 8), `child`, no income
* Person 6: Birth month/year `January 2016` (age 10), `child`, no income
* Person 7: Birth month/year `January 2014` (age 12), `child`, no income
* Person 8: Birth month/year `January 2012` (age 14), `child`, no income
* `current_benefits` does not include `mo_tanf`

**Why this matters**: Confirms the official table is used at the current maximum tested household size, and that neither the raw-percentage value nor the erroneous public-flyer figure is used instead.

### Scenario 25: Incapacitated-person-care deduction from a reported `dependentCare` expense

**What we're checking**: The incapacitated-person care deduction applies to an actual reported `dependentCare` cost — not automatically from a `disabled`/`long_term_disability` flag alone. Earnings are set high enough that countable-before-care income exceeds $175, so the exact deduction amount is observable (unlike a lower-earnings household, where the deduction would zero out countable income regardless of its exact value).
**Expected**: Eligible — $167/month (`R = 570 − 90 = 480`; countable before care `= (480 − 30) × 2/3 = 300`; the reported $175 `dependentCare` cost is within the $175-per-incapacitated-person cap: `countable = max(300 − 175, 0) = 125`; deficit `= 292` (size-3 payment standard) `− 125 = 167`).
**Steps**:
* Household size: `3`
* Person 1: Birth month/year `January 1996` (age 30), `headOfHousehold`, earner, wages: $570/month
* Person 2: Birth month/year `January 1996` (age 30), `spouse`, `long_term_disability: true`, no income
* Person 3: Birth month/year `January 2020` (age 6), `child`, no income
* Expense: `dependentCare`, $175/month
* `current_benefits` does not include `mo_tanf`

**Why this matters**: Confirms the incapacitated-care deduction requires an actual reported `dependentCare` cost tied to a qualifying incapacitated person — not an automatic deduction triggered by the disability flags alone with no expense reported (see Scenario 26).

### Scenario 26: No `dependentCare` expense reported — no automatic deduction

**What we're checking**: That `long_term_disability: true` with no `dependentCare` expense produces no care deduction, distinguishing this from an automatic deduction triggered by the disability flag alone.
**Expected**: Not eligible (identical household and wages to Scenario 25, but with no `dependentCare` expense reported: `R = 570 − 90 = 480`; countable `= (480 − 30) × 2/3 = 300`; no care deduction applies; deficit `= 292 − 300 = −8` → Gate 3 fails on the merits, `eligible: false` — this is a genuine income-test failure under 13 CSR 40-2.310(13), not the $10-floor payment-suppression rule in (14), which is never reached because Gate 3 fails outright).
**Steps**:
* Same household and wages as Scenario 25, except no `dependentCare` expense is reported

**Why this matters**: Confirms the calculator does not silently apply the $175 incapacitated-care deduction merely because a household member is flagged `disabled` or `long_term_disability` — Acceptance Criterion 15.

### Scenario 27: Under-age-2 childcare cap

**What we're checking**: The $200 under-2 cap, distinct from the $175 age-2-and-older cap tested in Scenarios 17/18.
**Expected**: Eligible — $134/month (`R = 570 − 90 = 480`; countable before care `= (480 − 30) × 2/3 = 300`; actual cost $300 exceeds the under-2 cap, so only $200 is deductible: `countable = max(300 − 200, 0) = 100`; deficit `= 234 − 100 = 134`. Applying the $175 cap instead would yield $109 — this scenario catches that age-bracket error.)
**Steps**:
* Household size: `2`
* Person 1: Birth month/year `January 1996` (age 30), `headOfHousehold`, wages: $570/month
* Person 2: Birth month/year `January 2025` (age 1, under 2 throughout 2026), `child`, no income
* Expense: `childCare`, $300/month
* `current_benefits` does not include `mo_tanf`

**Why this matters**: Confirms the age-based cap correctly selects $200 (not $175) for a child under age 2.

### Scenario 28: Self-employment income treated as net profit

**What we're checking**: The committed self-employment treatment (Criterion 8 / Benefit Value Steps 2–3) — a reported `selfEmployment` amount is treated as net profit already after ordinary business expenses and follows the same not-active/active-participant computation as wages, with no separate business-expense subtraction.
**Expected**: Eligible — $114/month (the not-active-participant calculation applies to the reported net amount the same as it would to wages: `after_work_exemption = 300 − 90 = 210`; countable `= (210 − 30) × 2/3 = 120`; deficit `= 234 − 120 = 114`).
**Steps**:
* Household size: `2`
* Person 1: Birth month/year `January 1996` (age 30), `headOfHousehold`, self-employment income: $300/month
* Person 2: Birth month/year `January 2020` (age 6), `child`, no income
* `current_benefits` does not include `mo_tanf`

**Why this matters**: Confirms self-employment income runs through the identical not-active/active-participant formula as wages, with no extra business-expense deduction layered on top.

### Scenario 29: Aggregate `childCare` cap across multiple children

**What we're checking**: The aggregate `childCare` cap is the *sum* of the applicable per-child caps, not a single flat per-household cap.
**Expected**: Eligible — $200/month (Gate 1: $820 < $1,565 ✓ (size 3 Gross Max); Gate 2, not-active participant, no disregard applies at this gate: $820 < $846 ✓ (size 3 Standard of Need); Gate 3: `R = 820 − 90 = 730`; countable before care `= (730 − 30) × 2/3 = 466.67`; allowable care `= $200 (under-2 cap) + $175 (age-2-and-older cap) = $375`; actual cost $500 exceeds $375, so only $375 is deductible: `countable = max(466.67 − 375, 0) = 91.67`; deficit `= 292` (size-3 payment standard) `− 91.67 = 200.33` → floored to `$200`. Applying a single flat $200 or $175 cap instead of summing per-child caps would produce a materially different result — this scenario catches that error.)
**Steps**:
* Household size: `3`
* Person 1: Birth month/year `January 1996` (age 30), `headOfHousehold`, wages: $820/month
* Person 2: Birth month/year `January 2025` (age 1, under 2 throughout 2026), `child`, no income
* Person 3: Birth month/year `January 2020` (age 6), `child`, no income
* Expense: `childCare`, $500/month
* `current_benefits` does not include `mo_tanf`

**Why this matters**: Confirms the household-level `childCare` aggregate is capped against the sum of each child's applicable per-child cap, rather than a single cap applied once regardless of how many children need care.

### Scenario 30: Child support received, active recipient

**What we're checking**: The committed child-support treatment (Criterion 8) for the **regular budget** — a reported `childSupport` amount is counted as unearned income equal to the amount actually sent to/received by the household, with no disregard. This scenario tests the reportable regular-budget amount under MFB's inclusive active-case default; it does not (and cannot) test Missouri's separate trial-budget step, which uses the CSE/DFAS-retained amount MFB does not collect.
**Expected**: Eligible — $203/month (Gate 1: $31 < $1,254 ✓; Gate 2: $31 < $678 ✓; deficit `= 234 − 31 = 203`).
**Steps**:
* Household size: `2`
* Person 1: Birth month/year `January 1996` (age 30), `headOfHousehold`, child support received (`childSupport`): $31/month
* Person 2: Birth month/year `January 2020` (age 6), `child`, no income
* `current_benefits` includes `mo_tanf`

**Why this matters**: Confirms `childSupport` counts as ordinary unearned income at the reported received amount in the regular budget — this scenario reproduces the final regular-budget figure ($234 payment standard − $31 received = $203) from Missouri's own active-case worked example, which uses $156 ($125 retained by CSE + $31 sent to the household) in a preceding trial budget that MFB cannot reproduce and does not need to in order to compute this regular-budget result.

### Scenario 31: Current TA cash grant excluded from its own recalculation

**What we're checking**: The committed cash-assistance treatment (Criterion 8) — when `current_benefits` includes `mo_tanf`, a reported `cashAssistance` amount representing the household's own existing TA grant is excluded entirely, not counted as additional unearned income against itself.
**Expected**: Eligible — $234/month (identical to a current recipient reporting no income at all — the reported `cashAssistance` amount is excluded from all three gates: Gate 1: $0 countable < $1,254 ✓; Gate 2: $0 < $678 ✓; deficit `= 234 − 0 = 234`. A naive implementation that counted the $234 `cashAssistance` entry as unearned income would instead compute deficit `= 234 − 234 = 0` and wrongly zero out the grant.)
**Steps**:
* Household size: `2`
* Person 1: Birth month/year `January 1996` (age 30), `headOfHousehold`, cash assistance (`cashAssistance`): $234/month
* Person 2: Birth month/year `January 2020` (age 6), `child`, no income
* `current_benefits` includes `mo_tanf`

**Why this matters**: Catches a realistic implementation error — a current TA recipient re-screening and reporting their own existing grant as `cashAssistance` income must not have that amount counted against them at any gate.

### Scenario 32: Gate 1 exact-equality boundary, genuinely isolated

**What we're checking**: The strict `<` comparator at Gate 1, in a household constructed so Gate 1 is the *only* gate that fails — Gates 2 and 3 both independently pass, so this scenario cannot pass merely because some other gate happens to deny the household too. This scenario uses an active participant's earned income and a childcare deduction specifically to decouple Gate 1 from Gates 2 and 3.
**Expected**: Eligible — $106.09/month — the calculator ships PolicyEngine's live result as-is for this exact boundary (see divergence note below).
**Policy note (strict regulation):** Gate 1: `$1,254 ≥ $1,254` size-2 Gross Max → fails on the merits under strict Missouri regulation, gross earned income receives no disregard at this gate. Gate 2, active participant: `$1,254 / 3 = $418 < $678` size-2 Standard of Need → passes. Gate 3, active participant: `$1,254/3 − $90 = $328`; minus the $200 under-2 childcare cap `= $128 < $234` payment standard → passes. Gate 1 alone would be dispositive under strict regulation, producing `eligible: false`.
**Steps**:
* Household size: `2`
* Person 1: Birth month/year `January 1996` (age 30), `headOfHousehold`, wages: $1,254/month
* Person 2: Birth month/year `January 2025` (age 1, under 2 throughout 2026), `child`, no income
* Expense: `childCare`, $200/month
* `current_benefits` includes `mo_tanf`

**Why this matters**: Proves Gate 1 is actually evaluated and actually binding under Missouri's own regulation, not just that the household ends up ineligible for some other reason — an implementation that omits the Gate 1 check entirely would incorrectly treat this household as passing every gate, since it otherwise passes both remaining gates. See the divergence note below for PolicyEngine's accepted departure from this result.

**PE divergence from strict Missouri regulation — accepted, no MFB override:** Under strict application of Missouri's regulation (see policy note above), this exact boundary is `eligible: false`. PolicyEngine's live formula-based Standard-of-Need calculation instead returns `eligible: true, $106.09` — a permanent characteristic of that approach, not a scenario-specific bug. This is a disclosed, accepted accuracy gap at this exact input pattern (Acceptance Criterion 31) — narrow in scope, do not generalize without the same root-causing.

### Scenario 33: Gate 2 independently denies even after the `(9)(C)2)` retry

**What we're checking**: That Gate 2 can independently deny a household — surviving even the `(9)(C)2)` favorable-history retry — while that same household would pass both Gate 1 and Gate 3. This is the load-bearing scenario for the "Gate 2 can independently bind" principle stated in Gate Interaction above.
**Expected**: Not eligible (Gate 1: `$1,515 < $1,832` size-4 Gross Max → passes. Gate 2, not-active participant: raw `$1,515 ≥ $990` size-4 Standard of Need fails; `(9)(C)2)` retry `= ($1,515 − $30) × 2/3 = $990`; `$990 ≥ $990` → **still fails** the strict `<` comparator, even at the retry. Gate 3, for reference only since Gate 2 already denies: `R = 1,515 − 90 = 1,425`; countable before care `= (1,425 − 30) × 2/3 = 930`; minus the $600 aggregate under-2 childcare cap (3 children × $200) `= 330`; `$330 < $342` size-4 payment standard → would independently pass, deficit `$12`.)
**Steps**:
* Household size: `4`
* Person 1: Birth month/year `January 1996` (age 30), `headOfHousehold`, wages: $1,515/month
* Person 2: Birth month/year `January 2025` (age 1, under 2 throughout 2026), `child`, no income
* Person 3: Birth month/year `June 2025` (age 0–1, under 2 throughout 2026), `child`, no income
* Person 4: Birth month/year `November 2025` (age 0–1, under 2 throughout 2026), `child`, no income
* Expense: `childCare`, $600/month
* `current_benefits` does not include `mo_tanf`

**Why this matters**: An implementation that treats Gate 2 as automatically satisfied whenever Gate 3 passes, or that omits the Gate-2 evaluation after applying the `(9)(C)2)` retry, would incorrectly return `eligible: true, $12` for this household.

### Scenario 34: NPCR automatic-needy exception via co-resident spouse's SSI

**What we're checking**: A second trigger of Criterion 4's NPCR automatic-needy exception — a co-resident spouse who *receives SSI*, as distinct from Scenario 11's "spouse absent from the home" trigger. Either condition deems the NPCR needy without running the neediness budget at all.
**Expected**: Eligible — $292/month. The NPCR is deemed automatically needy (spouse receives SSI); the SSI spouse is itself excluded from needs/income/resources (Criterion 4). Comparing the two valid configurations: NPCR included (grandparent + 2 grandchildren, size 3, no countable income) yields deficit `$292 − $0 = $292`; NPCR excluded (2 grandchildren alone, size 2) yields deficit `$234 − $0 = $234`. The higher eligible grant wins: **$292/month, NPCR included.**
**Steps**:
* Household size: `4` (SSI spouse excluded from the assistance unit; unit size 3)
* Person 1: Birth month/year `January 1971` (age 55), `headOfHousehold`, no income
* Person 2: Birth month/year `January 1973` (age 53), `spouse`, income stream `sSI`: $750/month
* Person 3: Birth month/year `January 2020` (age 6), `grandChild`, no income
* Person 4: Birth month/year `January 2018` (age 8), `grandChild`, no income
* `current_benefits` does not include `mo_tanf`

**Why this matters**: Confirms the automatic-needy exception's SSI-receipt trigger is implemented as an independent path to needy status, not merely the spouse-absent trigger already covered by Scenario 11. An implementation that only checks spouse presence — without separately checking SSI receipt — would incorrectly run the full neediness budget, and might still reach the same benefit number here, masking the missing branch.

### Scenario 35: Generic `cashAssistance` is excluded regardless of `mo_tanf` receipt ⚠️ *accepted PE limitation*

**What we're checking**: Criterion 8's committed cash-assistance treatment table — a reported `cashAssistance` amount is excluded *only* when `current_benefits` includes `mo_tanf` (Scenario 31); otherwise it is not assumed to represent the household's own MO TA grant, and is included as ordinary unearned income (e.g., cash assistance from another state or program).
**Expected**: Eligible — $234/month, the full size-2 payment standard: the reported amount is not counted (see the divergence note below). Under Criterion 8's committed treatment it would be $34/month (countable income $200; deficit `= $234 − $200 = $34`).
**Steps**:
* Household size: `2`
* Person 1: Birth month/year `January 1996` (age 30), `headOfHousehold`, income stream `cashAssistance`: $200/month
* Person 2: Birth month/year `January 2020` (age 6), `child`, no income
* `current_benefits` does not include `mo_tanf`

**Why this matters**: Pins the shipped treatment of the non-recipient branch, and marks the boundary of Scenario 31's self-exclusion rule.

**⚠️ Accepted PE limitation — no MFB-side override:** MFB's `cashAssistance` income type is its TANF field, so a reported amount reaches PolicyEngine as the `tanf` input. `tanf` is deliberately absent from PolicyEngine's TANF unearned-income sources (`gov.hhs.tanf.cash.income.sources.unearned`) — a program's own benefit is excluded from its own recalculation, which is what Scenario 31 relies on. PolicyEngine cannot distinguish the two branches, because both arrive as the same input; verified live at PE 1.794.2, sending `tanf` of $2,400/yr leaves `mo_tanf_gross_unearned_income` at $0, while the same amount as `unemployment_compensation` yields $200 and a $34.09 grant.

Reaching Criterion 8's treatment would mean routing the amount to a different PolicyEngine field based on `current_benefits` — deciding what the field means on our side, and changing `spm.Tanf`, which every PE program shares through `receipt_contract`. Not pursued: the divergence errs generously (a larger grant, not a denial) and only affects households reporting cash assistance from a program other than MO TA.

### Data gaps with no executable scenario

These have a committed inclusive-handling rule but no scenario, since MFB collects no corresponding screener input:

- Job quit/refusal (Criterion 9)
- Minor-parent living arrangement (Criterion 10)
- Federal 12-week funding restriction (Criterion 11)
- 45-month lifetime limit (Criterion 13)
- Individual criminal/drug-testing exclusions (Criterion 12)
- Foster-care/adoption-subsidy payment status (Criterion 4)
- Temporary-absence/adoption/90-day-absence unit continuity (Criterion 4)
- Paternity establishment (Criterion 4)
- Child-support noncooperation reduction (Benefit Value Step 8a)
- Work-program-noncompliance reduction and its concurrent-sanction interaction (Benefit Value Step 8b)
- Requalification after a full-family work-sanction closure (Criterion 14)
- Earned-income-disregard disqualification default (Benefit Value Step 3)
- Pursuit of potentially available RSDI/UC/veterans benefits (Criterion 15) — unobservable entitlement/refusal history
- `(9)(C)2)` prior-four-month TA-receipt history restoring the $30-plus-⅓ disregard at Gate 2 (Benefit Value Step 9) — Scenario 33 exercises the same retry mechanism as a side effect, without depending on the history fact itself
- New-spouse resource disregard, 6-consecutive-benefit-month window (Benefit Value Step 7) — no marriage-date field exists; MFB assumes the window is active whenever a current TA recipient's household includes a `spouse`, rather than scenario-testing the timing fact. (This is the resource half only — the income half is an accepted PE limitation, not a data gap; see below.)
- SSI/SP/SAB member's share of an aggregate `household_assets` total (Criterion 4) — `household_assets` has no per-member breakdown; don't deny on the aggregate alone
- Excluded non-dependent sibling's income-availability amount (Criterion 4) — assume $0 is made available to the assistance unit
- Age-18 dependent child's secondary-school attendance and marital history (Criterion 1) — assume enrolled, expected to graduate, and unmarried
- Child-student exclusion's remaining qualifying channels — K-12/secondary/vocational attendance, and part-time-student-not-full-time-employee (Benefit Value Step 6) — assume the exclusion applies regardless when `student`/`student_full_time` don't both confirm the full-time-college channel; the 6-month Gate-1 usage cap is also unobservable
- Teen-parent full-time secondary/vocational attendance (Benefit Value Step 6) — MFB's `student`/`student_full_time` fields confirm only college/university enrollment, a different fact; assume the condition is met
- `rental` income's ≥20-hrs/week management-hours fact (Criterion 8) — treat as earned income (favorable-to-household default)
- `investment` income's interest/dividend/capital-gain composition (Criterion 8) — exclude the entire reported amount, since the components can't be separated
- `fosterChild`/`relatedOther` caretaker's underlying qualifying relationship (Criterion 3) — assume both satisfy the caretaker-relationship requirement

### Accepted PolicyEngine limitations (no MFB-side override)

MFB ships no override code that substitutes a different number for what PE actually returns. These two areas are genuine PE capability gaps — no input, truthful or otherwise, gets PE to apply the rule:

- **$5,000 IEP/self-sufficiency-pact resource tier (Criterion 7):** PolicyEngine's `mo_tanf_resources_eligible` applies a flat $1,000 test regardless of TA-recipient status, with no $5,000-tier concept to select into. Every household is evaluated against $1,000, current recipients included.
- **New-spouse income disregard (Benefit Value Step 7):** PolicyEngine counts a new spouse's income in full at every gate; there is no PE input that reproduces Missouri's 6-month disregard.

NPCR election (Criterion 4) is not on this list: submitting two independently-truthful household configurations to PE and keeping the higher real result works correctly against live PE (Scenarios 10, 11, 12, 34) — see Criterion 4.

### Not represented by current screener inputs

- Blended-family/double-stepparent unit construction and three-generation minor-parent unit choice (Criterion 4), and the consequent major-parent income-deeming branch (Benefit Value Step 5) — `household_members.relationship` doesn't capture parent-child linkage
- Stepparent-of-child income-deeming variant (Benefit Value Step 5) — no field distinguishes a stepparent-of-child spouse from an ordinary co-parent spouse
- Household sizes above 8 — this version tests through the current maximum of 8
- Countable-resource exclusions for exempt property (vehicles, real property) — `household_assets` captures liquid assets only (Criterion 7)
- New-spouse resource disregard's precise dollar amount — `household_assets` is a household-level aggregate with no per-member ownership to isolate

## Source Documentation

- [MO TANF State Plan Modifications](https://dss.mo.gov/fsd/pdf/missouri-tanf-state-plan-modifications-ffy-2026-2027.pdf) (filename FFY 2026–2027; internal title metadata reads "Missouri PYs 2022–2023 (Mod)"). Cited only at Benefit Value Step 9's source note.
- 13 CSR 40-2 (Code of State Regulations, Division 40, Chapter 2) — sections .120, .305, .310, .315, .325, .330, .340, .345, .355, .360, .365, .370.
- [Appendix B — Consolidated Standard tables](https://dssmanuals.mo.gov/wp-content/uploads/2019/04/TA-AppendixB.pdf)
- [Missouri DSS Temporary Assistance program page](https://dss.mo.gov/employment-training-provider-portal/docs/temporary-assistance-final.pdf) — lists $517 for the size-8 payment standard, against $514 in the codified regulation and Appendix B (which agree); use $514.
- DSS Manuals: 0205.005.00, 0205.025.00, 0205.030.05, 0205.030.10, 0205.035.00, 0205.040.05.15, 0205.050.25.10, 0205.050.25.20, 0210.005.00, 0210.005.05, 0210.005.10, 0210.005.30, 0210.005.35, 0210.005.40, 0210.005.45, 0210.010.05.185, 0210.010.10, 0210.010.15, 0210.015.00, 0210.015.05, 0210.015.20.20, 0210.015.52, 0210.020.00, 0210.015.30, 0210.015.30.10, 0210.015.30.15, 0210.015.30.20, 0210.015.30.22, 0210.015.30.25, 0210.015.30.30, 0210.015.35.10, 0210.015.35.15, 0210.015.55, 0220.010.10, 0225.045.00, 0240.000.00, 0240.005.05, 0240.005.15
- [RSMo § 208.040](https://revisor.mo.gov/main/OneSection.aspx?section=208.040); RSMo § 208.027; 42 U.S.C. § 608(a)(4), (a)(5)(B)
- [RSMo § 536.010](https://revisor.mo.gov/main/OneSection.aspx?section=536.010); [RSMo § 536.021](https://revisor.mo.gov/main/OneSection.aspx?section=536.021); *[NME Hospitals, Inc. v. Department of Social Services](https://law.justia.com/cases/missouri/supreme-court/1993/75042-0.html)* (Mo. 1993) — the binding legal basis for this spec's source-precedence rule (codified regulation controls over a conflicting DSS operational manual or State Plan), applied at Benefit Value Step 9 (Gate 2) and Criterion 14 (work-sanction requalification duration).
- PolicyEngine (`mo_tanf` engine). Scenarios 8, 20, and 32 use the explicitly accepted live PE result rather than a hand-calculated correction (Acceptance Criterion 31).
