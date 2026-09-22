# Implement SAFESR (KS) Program

## Program Details

- **Program**: SAFESR — Kansas Property Tax Relief for Low Income Seniors (Form K-40PT)
- **Program key**: `ks_safesr`
- **State / White label**: KS
- **Engine / Calculator type**: MFB Custom (new KS calculator — no PolicyEngine model, no MFB sibling to inherit from)
- **Closest sibling**: `ks_k40h` (`programs/programs/white_labels/ks/k40h/calculator.py`, class `KsK40h`)
- **Claim year documented**: 2025 (filed 1 Jan – 15 Apr 2026)
- **Spec last updated**: 2026-09-20
- **Sources verified as of**: 2026-09-18

Terms used below: a **homestead** is the Kansas home the claimant owns and lives in, which the
refund is claimed on; the **claimant** is the one household member who files. **FPL** is the federal
poverty level. K-40H and K-40SVR are Kansas's two other property-tax refunds — see Related Programs.

Maintenance notes and this spec's review history live in the companion
`ks_safesr_review-notes.md`.

## Eligibility Criteria

1. **Claimant must be age 65 or older for the entire tax year**
   - Evaluation scope: `member`
   - Screener fields: `birth_year` (`HouseholdMember`, property derived from `birth_year_month`)
   - Implementation: test `birth_year <= 1959` for the 2025 claim year — i.e. `birth_year <= claim_year - 66`, keyed off the config's `year`, not hardcoded. A raw `age >= 65` check would wrongly admit someone who turns 65 mid-year. Mirrors `KsK40h._meets_categorical`, which uses `member.birth_year <= claim_year - (senior_age + 1)`.
   - Note: `birth_year` is `None` when `birth_year_month` is unset, and a `None` member silently fails this test. Same behaviour as K-40H; flag in code comments.
   - Source: [Form K-40PT (2025)](https://www.ksrevenue.gov/pdf/k-40pt25.pdf), Qualifications item 3 — "Age **65 or over** for the entire year. Enter your date of birth (must be prior to 1960)" — accessed 2026-09-18; [KDOR SAFESR page](https://www.ksrevenue.gov/safesenior.html) — "You must have been aged 65 years or older for all of 2025 (born before January 1, 1960)" — accessed 2026-09-18
   - Source (the entire-year rule, in statute): [K.S.A. 79-4502(e)](https://www.ksrevisor.gov/statutes/chapters/ch79/079_045_0002.html) — a claimant is a person who "was, during the entire calendar year preceding the year in which such claim was filed for refund under this act, except as provided in K.S.A. 79-4503, and amendments thereto, both domiciled in this state and was" 65 or older. The definition reaches SAFESR because [K.S.A. 79-32,263](https://www.ksrevisor.gov/statutes/chapters/ch79/079_032_0263.html) provides that "The provisions of this act shall be part of and supplemental to the homestead property tax refund act." — accessed 2026-09-20

2. **Claimant must be a Kansas resident for the entire tax year**
   - Evaluation scope: `household`
   - Screener fields: `zipcode`, `county` (`Screen`) — the KS white label only serves Kansas ZIPs, so residency is satisfied structurally; duration is not observable (see criterion 9)
   - Source: [Form K-40PT (2025)](https://www.ksrevenue.gov/pdf/k-40pt25.pdf), Qualifications item 1 — "A **resident of Kansas** during the entire year of 2025;" — accessed 2026-09-18; [K.S.A. 79-4502(e)](https://www.ksrevisor.gov/statutes/chapters/ch79/079_045_0002.html) — the same entire-year clause requires a claimant to have been "both domiciled in this state" throughout that year — accessed 2026-09-20

3. **Claimant must own and occupy a home in Kansas during the tax year**
   - Evaluation scope: `household`
   - Screener fields: `expenses` (`Expense`, housing rows `rent`, `mortgage`, `propertyTax`) — a proxy. The standard screener has no homeowner field — `is_home_owner` exists only on `EnergyCalculatorScreen`, and `Screen.housing_situation` is on the model but absent from `ScreenSerializer` and read by no calculator.
   - Implementation:
     1. `rent` expense present → NOT eligible (renter)
     2. Else → treat as homeowner (covers `mortgage` entered, `propertyTax` entered, and nothing entered; paid-off homes are common among seniors 65+)
   - Note: `Screen.has_expense()` matches on expense **type**, ignoring amount — a `rent` row of $0 disqualifies. `KsK40h` implements this same gate as the single condition `not self.screen.has_expense(["rent"])`; branches 1 and 2 above are that one check. A manufactured homeowner renting the lot is a known false negative.
   - Source: [Form K-40PT (2025)](https://www.ksrevenue.gov/pdf/k-40pt25.pdf), Qualifications item 2 — "A **home owner** during 2025; and," — accessed 2026-09-18; [KDOR SAFESR page](https://www.ksrevenue.gov/safesenior.html) — "you must have owned and occupied a home in Kansas during 2025" — accessed 2026-09-18

4. **Household income must not exceed $25,380 for the 2025 tax year**
   - Evaluation scope: `household`
   - Screener fields: `income_streams` (`IncomeStream`, all members) via `member.calc_gross_income("yearly", ["all"], exclude=[...])`; `birth_year` (`HouseholdMember`), to identify members who were not 18 for the whole claim year
   - Comparator: `<=` — the form disqualifies only above the figure
   - **The ceiling is 120% of the federal poverty level (FPL) for two persons.** Two persons is fixed, however many people live in the home, and the figure is not CPI-indexed. **Do not derive it.** KDOR's published figures track the formula but have not always equalled it: against MFB's FPL table (`_FPL_DEFAULTS` in `programs/models.py`), 120% of the two-person level gives $23,664 for 2023 against a published $23,700, and $24,528 for 2024 against $24,500; only 2025 matches, at $25,380. Carry the figure KDOR publishes on the claim-year K-40PT, and use the formula as an annual cross-check.
   - **Key the ceiling and the age gate to one claim year.** Hold the ceiling in a table — `income_limit_by_year = {2025: 25_380}` — and read the year from `claim_year = int(self.program.year.period) if self.program.year else max(income_limit_by_year)`. Criterion 1's age gate reads the same value, so the two can never describe different years. The fallback is needed because `Program.year` is a foreign key to a `FederalPoveryLimit` row and `import_program_config` only writes a warning when no row matches — a mis-seeded config imports and leaves `self.program.year` as `None`. `KsK40h._meets_categorical` falls back to a bare `2025` and freezes its own limit as a class attribute; copy neither.
   - **SAFESR household income is not gross income, and it is not K-40H's 50% partial count.**
     - **Count 100%** of the four Social Security streams — `sSRetirement`, `sSSurvivor`, `sSI`, `sSDependent`. See criterion 7 for the split inside `sSI` and criterion 12 for the split inside `sSDependent`.
     - **Exclude entirely**: `sSDisability` (SSDI), `childSupport`, `gifts`, and `veteran`. The first three are the Excluded Income types the screener can identify — the same three `KsK40h.excluded_types` carries. `veteran` is different: it is excluded as a stand-in for a bucket the screener cannot split, not because Kansas excludes it. See criterion 11.
     - **Include at full value**: `wages`, `selfEmployment`, `pension`, `deferredComp`, `investment`, `rental`, `boarder`, `unemployment`, `workersComp`, `cashAssistance`, `cashAssistanceOther`, `alimony` — for every member, including an adult who is neither the claimant nor the spouse.
     - **Skip a member who was not 18 for the whole claim year** — `birth_year >= claim_year - 18`, i.e. born 2007 or later for 2025. The booklet says "adult individuals" without fixing when adulthood is tested; this reading matches criterion 1's entire-year rule and widens results, since excluding more income can only admit more households. See criterion 8.
   - Implementation note — **do not reuse `KsK40h`'s income logic**. It counts `sSRetirement`, `sSSurvivor` and `sSI` at 50% (`KsK40h.half_count_types`), so copying it under-counts SAFESR household income by roughly half. Its minor guard is wrong for SAFESR in two further ways: it is keyed to `relationship` in `("child", "stepChild", "fosterChild")`, so it misses a 16-year-old `grandChild`, `sisterOrBrother` or `relatedOther`; and its `member.age < 18` test reads a value `HouseholdMemberSerializer.validate` back-fills at creation time, so for a claim filed in the January–April window it carries the age reached in the **filing** year, and a member who turned 18 during the claim year is counted where the entire-year rule excludes them. Key the skip to birth year alone. Scenarios 12, 18 and 19 are the tests.
   - Source (the ceiling): [Form K-40PT (2025)](https://www.ksrevenue.gov/pdf/k-40pt25.pdf), Line 10 — "TOTAL HOUSEHOLD INCOME (Add lines 4 through 9. If line 10 is more than $25,380 you do not qualify for a refund)" — accessed 2026-09-18; [K.S.A. 79-32,263](https://www.ksrevisor.gov/statutes/chapters/ch79/079_032_0263.html) — "for tax year 2011 and all tax years thereafter, an amount equal to 75% of the amount of property and ad valorem taxes actually and timely paid by a taxpayer who is 65 years of age or older and who has household income equal to or less than 120% of the federal poverty level for two persons" — accessed 2026-09-20
   - Source (Social Security at 100%, not 50%): [2025 Homestead Booklet](https://www.ksrevenue.gov/pdf/k-40hbook25.pdf), page 2, *Definition of a Household and Household Income* — "Social Security and SSI benefits. The amount included depends on which refund claim you file: K-40H – 50% of Social Security and SSI benefits (except disability payments – see Excluded Income). K-40PT – 100% of Social Security and SSI benefits (except disability payments – see Excluded Income)." — accessed 2026-09-18. The statute is the source of that split: [K.S.A. 79-4502(a)](https://www.ksrevisor.gov/statutes/chapters/ch79/079_045_0002.html) caps Social Security at half for the homestead act, and [K.S.A. 79-32,263](https://www.ksrevisor.gov/statutes/chapters/ch79/079_032_0263.html) overrides the cap for SAFESR by counting "all income as defined in K.S.A. 79-4502(a), and amendments thereto, including any payments received under the federal social security act, received by persons of a household in a calendar year while members of such household." SSDI's exclusion is statutory too — "Income does not include disability payments received under the federal social security act." — accessed 2026-09-20
   - Source (whose income counts): same booklet, page 5, Line 9 instructions — "All income (regardless of source) received by adult individuals other than you and your spouse who lived in the homestead at any time during 2025." and "The income (child support, SSI, wages, etc.) of a minor child or incapacitated person, when that person is an owner of the homestead or is on the rental agreement." K-40PT adopts these on its back: "Lines 7 through 9: Use the instructions for lines 7 through 9 of Form K-40H on page 5 to complete these lines on Form K-40PT." — accessed 2026-09-18
   - Source (the form's income lines): [Form K-40PT (2025)](https://www.ksrevenue.gov/pdf/k-40pt25.pdf), Line 6 — "Total Social Security and SSI benefits, including Medicare deductions, received in 2025" — accessed 2026-09-18; Line 6 instructions — "Do not include Social Security or SSI “disability” payments." — accessed 2026-09-20; Line 7 — "Railroad Retirement benefits **and** all other pensions, annuities, and veterans benefits (do **not** include disability payments from Veterans and Railroad Retirement)" — accessed 2026-09-18; Line 8 — "TAF payments, general assistance, worker’s compensation, grants and scholarships" — accessed 2026-09-18; Line 9 — "All other income, including the income of others who resided with you" — accessed 2026-09-20
   - Source (definition unchanged for 2025): [KDOR Notice 25-05](https://www.ksrevenue.gov/taxnotices/notice25-05.pdf) (2025-07-03) — "2025 legislation does not change in the way in which household income is determined on the K-40H, Kansas Homestead Claim and the K-40PT, Kansas Property Tax Relief Claim for Low Income Seniors for claim year 2025." The Kansas-Adjusted-Gross-Income redefinition applies to K-40SVR only — accessed 2026-09-18
   - Note — the form and the statute disagree on child support, and the form governs. [K.S.A. 79-4502(a)](https://www.ksrevisor.gov/statutes/chapters/ch79/079_045_0002.html) counts "maintenance, support money, cash public assistance and relief" as income, which on its face reaches child support; the K-40PT lists "Child Support" at line 13(c) under Excluded Income, and `KsK40h.excluded_types` follows the form. The form is the operative filing instrument, and excluding the stream widens results. Scenario 18 turns on it — accessed 2026-09-20
   - Note — the booklet's summary sentences are broader than its line 9 detail, and the detail governs. The K-40H preamble and K-40PT's own instruction block both say the income of "ALL other persons who lived with you at any time during 2025", while the line 9 detail limits it to adult individuals plus a minor who holds title. K-40PT incorporates lines 7 through 9 by reference, so the detail is what it adopts — accessed 2026-09-18

5. **Household income excludes Social Security paid to someone whose benefits converted from disability at full retirement age** ⚠️ *data gap*
   - Why: the screener records a current income type, not its history. A 65+ claimant whose SSDI converted to retirement reports `sSRetirement`, indistinguishable from an ordinary retiree.
   - Handling: count the stream at 100% per criterion 4 — **narrows results**. Income gates SAFESR but does not size the refund, so the only effect is on the gate: a converted-disability recipient near $25,380 may be shown ineligible when a filed claim would succeed. Accepted because `sSRetirement` is what every ordinary retiree reports too, and excluding the type wholesale would strip the income test of its main input for this population. Note in calculator code comments.
   - Source: [Form K-40PT (2025)](https://www.ksrevenue.gov/pdf/k-40pt25.pdf), Line 6 instructions — "(NOTE: Social Security disability or SSI payments become regular Social Security payments when a recipient reaches full retirement age. These Social Security disability payments, that were once Social Security disability or SSI payments, are NOT included in household income.)" — accessed 2026-09-18

6. **Household income includes federal Earned Income Credit received, and grants and scholarships** ⚠️ *data gap*
   - Why: the screener collects neither. EITC is computed by other MFB programs but is not an `IncomeStream`; there is no grants/scholarships income type.
   - Handling: omit both — **widens results**. A household near the ceiling may be shown eligible when the filed claim would fail. Note in calculator code comments.
   - Source: [Form K-40PT (2025)](https://www.ksrevenue.gov/pdf/k-40pt25.pdf), Line 4 — "2025 Wages OR Kansas Adjusted Gross Income (if negative, enter zero)" followed by "plus Federal Earned Income Credit" (the two figures are entered in blanks on the form and totalled on the same line) — accessed 2026-09-18; Line 8 — "TAF payments, general assistance, worker’s compensation, grants and scholarships" — accessed 2026-09-18

7. **SSI disability cannot be separated from non-disability SSI** ⚠️ *data gap*
   - Why: the screener has one `sSI` type. The form counts non-disability SSI in full and excludes SSI disability entirely.
   - Handling: **count `sSI` at 100%**, per criterion 4, following the form's general rule for line 6 — **narrows results**, so a disability-SSI recipient near the ceiling can be shown ineligible. Accepted as the lesser error: excluding all `sSI` would under-state income for aged and blind recipients, whose SSI Kansas counts in full, and they are the larger share of the stream. Note in calculator code comments.
   - Source: [Form K-40PT (2025)](https://www.ksrevenue.gov/pdf/k-40pt25.pdf), Line 6 and Line 13(f) — "SSI, Social Security, Veterans or Railroad Disability" — accessed 2026-09-18

8. **A minor child's income counts only if that child owns the homestead or is on the rental agreement** ⚠️ *data gap*
   - Why: whether a member under 18 holds legal title, or is named on a rental agreement, is not observable — the screener has no ownership or title field at all, the same absence that puts criterion 3 on an expense stand-in.
   - Handling: treat no minor as a title-holder — always exclude the income of members whose `birth_year >= claim_year - 18`, per criterion 4. **Widens results**: a household is never denied on a working teenager's wages. Note in calculator code comments.
   - Source: [2025 Homestead Booklet](https://www.ksrevenue.gov/pdf/k-40hbook25.pdf), page 5, Line 9 instructions — "If a minor child or incapacitated person holds legal title to the property, the income (wages, child support, etc.) will also be entered on line 9." — accessed 2026-09-18; same booklet, page 6, *Excluded Income* — "On line (g), enter wages received by a minor child and any other income not considered “household income” as outlined on page 2." — accessed 2026-09-18

9. **Claimant must have owned and occupied the homestead for the whole period claimed** ⚠️ *data gap*
   - Why: the expense stand-in in criterion 3 shows current homeownership, not duration. The form requires ownership **"during 2025"**, not for the entire year — unlike residency, which is explicitly "the entire year." Partial-year ownership is claimable, with the claimable tax prorated.
   - Handling: `assumed-met` — do not exclude. Surface in the program description so applicants can check before filing.
   - Source: [Form K-40PT (2025)](https://www.ksrevenue.gov/pdf/k-40pt25.pdf), Qualifications item 2 — "A **home owner** during 2025; and," — accessed 2026-09-18
   - Source (the proration rule): [K.S.A. 79-4502(f)](https://www.ksrevisor.gov/statutes/chapters/ch79/079_045_0002.html) — where a household owns the homestead for only part of a calendar year, the claimable tax is that levied while the household both owned and occupied the home, "multiplied by the percentage of 12 months that the property was owned and occupied by the household as its homestead in the year." — accessed 2026-09-20

10. **Homestead's appraised value must not exceed $350,000** ⚠️ *data gap*
    - Why: the screener does not capture appraised home value. It was considered and rejected as too privacy-sensitive during K-40H discovery.
    - Comparator: `>` — the bar falls on a home valued *above* $350,000. Two KDOR sources disagree (the form face says "more than $350,000", the booklet says "$350,000 or more"); [K.S.A. 79-4522](https://www.ksrevisor.gov/statutes/chapters/ch79/079_045_0022.html) settles it with "exceeds $350,000", so the form face is right. No calculator impact either way, and the config description follows the form face.
    - Handling: `assumed-met` — assume the home is under the cap. Most homes of households at or below $25,380 in income will be well under $350,000; the worst case is a denied claim at filing. Surface in the program description and the document list.
    - Source: [Form K-40PT (2025)](https://www.ksrevenue.gov/pdf/k-40pt25.pdf), Line 11 — "General property taxes **paid timely** in 2025, excluding specials. (Tax on property valued at more than $350,000 does not qualify. See instructions on the back of this form.)" — accessed 2026-09-18; [KDOR SAFESR page](https://www.ksrevenue.gov/safesenior.html) — "your house cannot be valued more than $350,000" — accessed 2026-09-18; [2025 Homestead Booklet](https://www.ksrevenue.gov/pdf/k-40hbook25.pdf), Line 12 instructions (the conflicting wording) — "taxes on property valued at $350,000 or more does not qualify" — accessed 2026-09-18

11. **Veterans' disability compensation cannot be separated from veterans' pensions and other veterans' benefits** ⚠️ *data gap*
    - Why: the screener has one income type, `veteran`, labelled **"Veteran's Pension or Benefits"** (`configuration/white_labels/base.py`). Kansas splits that bucket — it excludes veterans' **disability compensation** only, and counts pensions, annuities and other veterans' benefits in full — and no screener field names which a member receives.
    - Handling: **exclude the whole `veteran` bucket** from SAFESR household income, per criterion 4. **Widens results**: it drops veterans' pension income Kansas counts, so a pension recipient near the ceiling may be admitted. That is the deliberate trade — counting the bucket instead would wrongly deny a disabled veteran, and for SAFESR income affects only the gate, never the refund amount. In calculator code comments, describe this as a stand-in for a split the screener cannot make, **not** as implementing the form.
    - Note — the framework's veterans-disability stand-in was considered and rejected. `IsFullyDisabledServiceConnectedVeteranDependency` (`programs/framework/pe_dependencies/member.py`) excludes the bucket only for a member who also reports `disabled` or `long_term_disability`, and counts it in full for every veteran who does not — including the disability compensation Kansas excludes. That narrows results, and it would deny a disabled veteran who did not tick the disability box. `KsK40h` counts the bucket in full, so SAFESR diverges from its sibling here, as it already does on the 50% Social Security rule and the minor guard. Scenario 20 is the test.
    - Source: [Form K-40PT (2025)](https://www.ksrevenue.gov/pdf/k-40pt25.pdf), Line 7 — "Railroad Retirement benefits **and** all other pensions, annuities, and veterans benefits (do **not** include disability payments from Veterans and Railroad Retirement)" — accessed 2026-09-18; same form, Line 13(f) Excluded Income — "SSI, Social Security, Veterans or Railroad Disability" — accessed 2026-09-18; [K.S.A. 79-4502(a)](https://www.ksrevisor.gov/statutes/chapters/ch79/079_045_0002.html) — "Income does not include veterans disability compensation." — accessed 2026-09-20

12. **Social Security dependent benefits cannot be separated from dependent disability benefits** ⚠️ *data gap*
    - Why: the screener has one `sSDependent` type, labelled **"Social Security Dependent Benefits (retirement, disability, or survivors)"** (`configuration/white_labels/base.py`, `ConfigurationData.income_options_by_category`) — the label declares the split. A benefit paid on a disabled worker's record is a disability payment Kansas excludes; the same stream on a retired or deceased worker's record is counted in full. Nothing says which record a member's benefit is paid on.
    - Handling: **count `sSDependent` at 100%**, per criterion 4 — the same resolution as criterion 7, and for the same reason: where the claimant is 65 or older the dependent benefit is most often paid on a retirement or survivor record, so the excluded sub-type is the smaller share. **Narrows results**, so such a household can be shown ineligible near the ceiling. Note in calculator code comments.
    - Source: [Form K-40PT (2025)](https://www.ksrevenue.gov/pdf/k-40pt25.pdf), Line 6 instructions — "Do not include Social Security or SSI “disability” payments." — accessed 2026-09-20; [K.S.A. 79-4502(a)](https://www.ksrevisor.gov/statutes/chapters/ch79/079_045_0002.html) — "Income does not include disability payments received under the federal social security act." — accessed 2026-09-20

13. **Citizenship / legal status**
    - Evaluation scope: `config`
    - Screener fields: none — handled by the program-level `legal_status_required`, not a calculator check
    - Note: the form requires a valid SSN to file but states no separate citizenship test and no ITIN provision. `legal_status_required` carries all six user-selected statuses — `citizen`, `non_citizen`, `gc_5plus`, `gc_5less`, `refugee`, `otherWithWorkPermission` — i.e. no restriction. The other labels the importer accepts are calculated from household data for programs with age- or pregnancy-specific immigration rules, and none reaches SAFESR (`CitizenLabels` in benefits-calculator `src/Components/Results/Filter/citizenshipFilterConfig.tsx`, mirrored in `programs/management/commands/tests/test_five_year_bar_legal_statuses.py`). This is handled in config, so it is not a data gap.
    - Source: [Form K-40PT (2025)](https://www.ksrevenue.gov/pdf/k-40pt25.pdf) — accessed 2026-09-18; [KDOR SAFESR page](https://www.ksrevenue.gov/safesenior.html) — accessed 2026-09-18

## Which Data Gaps the Description Surfaces

**Governing rule (reviewer, 2026-09-20): surface only the data gaps a *typical* user needs to
know.** Each sentence in the description competes for attention with the others, so a gap earns
one only if it clears two bars: it must **widen** results (a narrowing gap screens the household
out, so the description never reaches them), and it must touch a real share of this population —
65+, Kansas homeowner, household under the ceiling.

Surfaced (4):

| Gap | Why it earns a sentence |
|---|---|
| One refund per year | Every claimant faces it, and choosing the wrong one costs real money |
| Criterion 11 — veterans' benefits | Common in a 65+ Kansas household; the clearest false-hope case, since excluding the bucket under-states income |
| Criterion 10 — home appraised value | Low income plus an appreciated house is the specific SAFESR pattern — a long-time owner on a fixed income. The claimant can check it on their own tax statement |
| Criterion 9 — part-year ownership | Weakest of the four against the rule, since it touches only those who moved. Kept because the sentence is self-filtering ("If you bought or sold…"), so a typical reader skips it at no cost |

Not surfaced, and deliberately so:

- **Criteria 6 (federal EITC, grants and scholarships) and 8 (a minor child holding title).** Both
  widen results, so both are the same *shape* as the veterans line — but neither is typical. For 8
  the household needs a minor who holds legal title **and** has income, which is near-zero, and
  saying it would imply a teenager's wages generally count when we and Kansas both exclude them.
  For 6 the exposure is narrow and concentrated just under the ceiling; it is also the hardest of
  the nine to phrase at this reading level without prompting a reader to wonder whether their
  Social Security or the refund itself counts. **A later pass should not add these for symmetry
  with criterion 11** — the asymmetry is the rule working, not an oversight.
- **Criteria 5, 7 and 12.** All three count income at 100% and therefore **narrow** results. A
  household wrongly screened out never opens the program page, so no description can reach it.
  These are real accepted harms, documented in the criteria themselves, but they are not
  addressable here.

## Priority Criteria

None identified as of 2026-09-16. SAFESR has no set-aside, preference, waitlist, or target-population tier — every qualifying claimant who files by the deadline receives the refund.

## Related Programs

- **Kansas Homestead Refund (K-40H, `ks_k40h`)** — the general homestead property-tax refund, already implemented in MFB. Own eligibility: age 55+ (or disabled, blind, or a dependent child in the household), household income ≤ $43,389 for 2025, owner-occupant. Refund = allowed property tax capped at $700 × a sliding-scale percentage, with a $5 minimum. A claimant may file this **or** SAFESR, not both — see the one-refund rule below.
  - Source: [2025 K-40H Booklet](https://www.ksrevenue.gov/pdf/k-40hbook25.pdf), Line 10 — "If more than $43,389 you do not qualify for a homestead refund" — accessed 2026-09-18; Line 13 — "Amount of property tax allowed; cannot exceed $700" — accessed 2026-09-18
- **Property Tax Relief for Seniors and Disabled Veterans (K-40SVR)** — not implemented in MFB. Own eligibility: household income ≤ $58,041 for 2025 measured as **Kansas Adjusted Gross Income** (a different computation from K-40H's and SAFESR's), age 65+ or disabled veteran for the entire base year, owner-occupant, home ≤ $350,000. Refund = current-year property tax minus base-year property tax. A claimant may file this **or** SAFESR, not both.
  - Source: [KDOR Notice 25-05](https://www.ksrevenue.gov/taxnotices/notice25-05.pdf) — "For calendar year 2025 the income limitation will be $58,041" and "(3) For tax year 2025, and all tax years thereafter, “household income” means the total Kansas adjusted gross income of all persons of a household in a calendar year while members of such household." — accessed 2026-09-18

**Only one refund per year** ⚠️ *data gap*. A claimant may claim only one of the three refunds on the
same property for the same tax year. Having already filed a K-40H or K-40SVR **is** a household
eligibility gate, but MFB cannot see it: with `show_in_has_benefits_step: false` there is no screener
input by which a household could report another claim.
  - Handling: `assumed-met` — assume no other claim has been filed; note the assumption in calculator
    code comments. **Build no selection logic** — no `Eligibility.program_eligible` ordering, no
    `CALC_ORDER` change in `screener/views.py`. Both cards may surface, and the program description
    states the one-claim rule — "Kansas has three property tax refunds for homeowners, and you can
    claim only one each year" — and that which one pays most depends on income and tax bill. It
    names **no** comparison page: reviewer decision 2026-09-20, since `apply_button_link`
    (`forms-hs.html`) visibly lists all three forms, so the destination makes the choice available
    without the copy sending users to a second site. The description
    must not simply tell users to prefer SAFESR: SAFESR is the larger refund except where K-40H
    household income is at or below $12,000 *and* annual property tax falls under $709–$933.
  - Source (the one-refund rule, in statute): [K.S.A. 79-32,263](https://www.ksrevisor.gov/statutes/chapters/ch79/079_032_0263.html) — "A taxpayer shall not take the credit pursuant to this section if such taxpayer has received a homestead property tax refund pursuant to K.S.A. 79-4501 et seq., and amendments thereto, for such property for such tax year." Note the statute bars SAFESR where a homestead refund was **received**, while the form keys the bar to having **filed**; no calculator impact, since the criterion is `assumed-met` under either reading — accessed 2026-09-20
  - Source: [Form K-40PT (2025)](https://www.ksrevenue.gov/pdf/k-40pt25.pdf), Qualifications NOTE — "If you filed a Form K-40H or K-40SVR for 2025, you **DO NOT** qualify for this property tax refund." — accessed 2026-09-18; [KDOR SAFESR page](https://www.ksrevenue.gov/safesenior.html) — "No, a claimant may receive either a Homestead, SAFESR or a Property Tax Relief refund." — accessed 2026-09-18

**One claimant per household** — a separate statutory rule, and the one that makes a two-senior
household produce a single result rather than two. Where more than one occupant could qualify, the
occupants choose between them; the screener models a household, so the calculator returns one
household-level result and never a per-member one. Scenario 11 is the test.
  - Source: [K.S.A. 79-4507](https://www.ksrevisor.gov/statutes/chapters/ch79/079_045_0007.html) — "Only one (1) claimant per household per year shall be entitled to relief under this act." — accessed 2026-09-20; [K.S.A. 79-4502(e)](https://www.ksrevisor.gov/statutes/chapters/ch79/079_045_0002.html) — "When a homestead is occupied by two or more individuals and more than one of the individuals is able to qualify as a claimant, the individuals may determine between them as to whom the claimant will be." — accessed 2026-09-20

## Benefit Value

**Type**: Variable, computed. The refund scales directly with the household's property tax.

**Methodology**: Refund = 75% × general property tax timely paid on the homestead in the claim
year, excluding special assessments. Flat 75% — no cap, no sliding scale, no minimum-refund floor.

- Example: a household with $2,000 in annual property tax receives 75% × $2,000 = **$1,500**.
- **Rounding: to the nearest whole dollar.** Every money line on the K-40PT is printed with a fixed `00` cents box, so KDOR itself works in whole dollars, and the framework's contract is `ProgramCalculator.household_value() -> int`. Compute as `round(0.75 × annual property tax)`, matching `KsK40h.household_value`. Note that Python's `round` is half-to-even, so the fallback case below resolves to $1,756, not $1,757.
- `value_format`: `estimated_annual` — an annual amount claimed once a year. The card renders `$X/year` with no division by 12. The program page labels it "Average Annual Savings" (`YearlyValueLabel`, benefits-calculator `src/Components/Results/FormattedValue.tsx`); that wording fits a saving better than a refund, but `estimated_annual` is still correct, because the alternative `lump_sum` renders "Estimated One-Time Payment" and this claim recurs yearly. Do not switch format to change the label.
- Source: [Form K-40PT (2025)](https://www.ksrevenue.gov/pdf/k-40pt25.pdf), Line 12 — "PROPERTY TAX REFUND. Multiply the amount on line 11 by 75% (.75). This is the amount of your refund" — accessed 2026-09-18; [KDOR SAFESR page](https://www.ksrevenue.gov/safesenior.html) — "The refund is 75% of the property taxes actually and timely paid" — accessed 2026-09-18

**Property tax input**: the screener collects Property Taxes as a Housing expense (`propertyTax`),
often left blank.

1. If `screen.calc_expenses("yearly", ["propertyTax"])` is **greater than zero**: refund = 75% × that amount.
2. Otherwise — no `propertyTax` row at all, or a row entered at $0: refund = 75% × **$2,342/year** fallback = $1,756.50, rounded to **$1,756/year**.

The gate is the summed amount, **not** `Screen.has_expense(["propertyTax"])`. `has_expense` matches
on expense type and ignores the amount — which is what criterion 3's ownership test wants, but not
this. Gating the value on it would hand an eligible household a $0 refund whenever a `propertyTax`
row was entered at $0, which the expense form permits (`expenseRowSchema` is
`expenseAmount: z.number().int().min(0)`). `KsK40h._refund_amount` resolves the same fork the same
way. benefits-calculator applies no zero-value filter to results, so a $0 refund would render on
the card as `$0/year` rather than being suppressed. Scenario 16 is the test.

**Fallback methodology.** $2,342 is the median real estate tax on Kansas owner-occupied units **not
mortgaged** — the deliberate cohort choice, because outright ownership correlates with the 65+
population SAFESR screens and the row runs 23% below the mortgaged one ($3,056).

- Source: U.S. Census Bureau, ACS 5-year 2020–2024, table B25103 (*Mortgage Status by Median Real Estate Taxes Paid*), Kansas — "Not mortgaged: $2,342" — read at [data.census.gov](https://data.census.gov/table/ACSDT5Y2024.B25103?g=040XX00US20) — accessed 2026-09-16, re-confirmed against the source by the reviewer 2026-09-18

It is an **MFB-owned estimate, not a program-stated amount** — say so in code comments. It does not
reflect SAFESR's $25,380 income ceiling, so it sits above what the lowest-income claimants pay. The
error runs one way: generous, never restrictive, and any household entering a real `propertyTax`
bypasses it. More conservative than MFB precedent — `KsK40h` falls back to the statutory $700 cap, a
maximum rather than a central estimate.

**Disclosed simplifications** (note in calculator code comments — these change what the claimant
actually receives, not the computed refund):

- **Form ELG offset.** "If you filed Form ELG with your county, your refund will be reduced by the ELG amount applied to the first half of your 2025 property tax." Form ELG is the eligibility letter KDOR sends a claimant's County Treasurer under the optional Refund Advancement Program; the advanced amount is subtracted from the next refund. The estimator ignores it, so a prior-year advancement participant will receive less than shown. Narrow, opt-in population.
  - Source: [Form K-40PT (2025)](https://www.ksrevenue.gov/pdf/k-40pt25.pdf), Line 12 Important — accessed 2026-09-18
- **Debtor set-off.** Any delinquent debt to the State of Kansas — child support, student loan, medical bills, income tax — is applied against the refund before payment.
  - Source: [2025 K-40H Booklet](https://www.ksrevenue.gov/pdf/k-40hbook25.pdf), "Debtor Set-Off" — "your refund will be applied to that debt first and any remaining refund will be sent to you" — accessed 2026-09-18
- **Co-ownership with someone outside the household.** Where the homestead is held with a joint tenant or tenant in common who is not a household member — a senior who added an adult child to the deed, most commonly — only the household's ownership share of the tax is claimable. The screener captures no ownership share, so the calculator assumes the household owns all of it. That over-states the refund for co-owners, the same generous direction as the fallback, and never affects eligibility. Note in calculator code comments.
  - Source: [K.S.A. 79-4502(f)](https://www.ksrevisor.gov/statutes/chapters/ch79/079_045_0002.html) — where one or more owners is not a member of the claimant's household, the claimable tax "is that part of property taxes levied on the homestead that reflects the ownership percentage of the claimant's household" — accessed 2026-09-20
- **Specials and timeliness.** Line 11 counts only general property tax paid timely, excluding special assessments and service charges. The screener's `propertyTax` expense is whatever the user reports and may include specials, over-stating the refund slightly.
  - Source: [K.S.A. 79-4502(f)](https://www.ksrevisor.gov/statutes/chapters/ch79/079_045_0002.html) — the statutory definition counts property taxes "exclusive of special assessments, delinquent interest and charges for service" — accessed 2026-09-20

**Calculator dependencies.** Declare
`dependencies = ("age", "income_type", "income_amount", "income_frequency", "expenses")`.
`ProgramCalculator.can_calc` returns `not self.missing_dependencies.has(*self.dependencies)`, and a
program whose declared dependency is missing is left out of the results rather than reported
ineligible — so the tuple is binding, not documentation. `relationship` and `household_size` are
deliberately **not** dependencies: the minor guard is keyed to birth year (criterion 4) and no rule
reads household size. Note that `"age"` is the only token `HouseholdMember.missing_fields` offers
for birth data and does not guarantee `birth_year_month` is set; a member without it has
`birth_year` `None` and silently fails criterion 1, which stays the only handling there.

## Test Scenarios

*County names use the values the KS white label stores — `Douglas County`, not `Douglas`
(`configuration/white_labels/ks.py`, `counties_by_zipcode`). No SAFESR criterion matches on county;
`county` is collected only as part of the Kansas-residency check.*

*Every amount is a whole dollar, because the screener form does not accept cents — a scenario with
cents is constructible as a unit test but unenterable by a real user. Property tax is stated at
`yearly` frequency, which is how the bill arrives and which keeps 75% exact.*

**Coverage map**

| Rule / variation axis | Scenarios |
|---|---|
| Age 65+ entire year (`birth_year <= 1959`) | 5 (earliest qualifying year), 6 (born 1960 → fail), 7 (well above) |
| KS residency | all |
| Ownership — renter disqualified | 8 (fail) |
| Ownership — `propertyTax` entered | 1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 17, 18, 19, 20 |
| Ownership — `mortgage` only | 15 |
| Ownership — nothing entered | 14 |
| Income ≤ $25,380 | 3 (just under), 2 (exactly at), 4 (just over → fail), 13 (zero) |
| Income — 100% Social Security (not K-40H's 50%) | 2, 4 |
| Income — exclusions (`sSDisability`, `gifts`) | 17 |
| Income — the `veteran` bucket is excluded | 20 |
| Income — exclusion (`childSupport`) | 18 |
| Income — an adult non-claimant's income is counted | 12 (fail), 19 (fail) |
| Income — a member who was not 18 all year is excluded | 18 |
| Income — the adulthood boundary (born 2006 counted, born 2007 not) | 19, 18 |
| Value — 75% of entered `propertyTax` | 1, 2, 3, 5, 7, 9, 10, 11, 13, 17, 18, 20 |
| Value — fallback when no `propertyTax` row | 14, 15 |
| Value — fallback when the `propertyTax` row is $0 | 16 |
| Value — whole-dollar rounding | 14, 15, 16 |
| SNAP receipt does not disqualify | 9 |

**Known scenario gaps** (data gaps — not testable, per criteria 5–12 and the one-refund rule under Related
Programs): converted-disability Social Security, federal EITC and grants/scholarships, the `sSI`
disability split, which record a dependent Social Security benefit is paid on, which kind of
veterans' benefit a member receives, whether a minor child holds
title to the homestead, ownership duration, the $350,000 home-value cap, and whether a K-40H or
K-40SVR claim was already filed for the year. Where such a gap carries a committed handling the
calculator must implement — the `veteran` exclusion — the handling is tested even though the
underlying fact is not; scenario 20 is that test.

---

### Scenario 1: Clearly eligible senior homeowner — typical SAFESR applicant
**What we're checking**: A Kansas senior 65+ the entire year with income well below the ceiling and an entered property-tax expense qualifies at a real computed refund.
**Expected**: Eligible — $1,350/year (75% × $1,800)

**Steps**:
- **Location**: ZIP `66044`, county `Douglas County`
- **Household**: 1 person
- **Person 1**: Born March 1955 (age 70 in 2025; born before 1/1/1960), `headOfHousehold`, citizen, income: Social Security Retirement Benefits `$1,200`/month ($14,400/year)
- **Expenses**: Property Taxes `$1,800`/year; no rent

**Why this matters**: The golden path. Confirms the calculator returns 75% of the entered property tax rather than a flat or zero value.

---

### Scenario 2: Household income exactly at the ceiling
**What we're checking**: Household income of exactly $25,380 — the highest qualifying figure — is accepted.
**Expected**: Eligible — $750/year (75% × $1,000)

**Steps**:
- **Location**: ZIP `66044`, county `Douglas County`
- **Household**: 1 person
- **Person 1**: Born December 1959, `headOfHousehold`, citizen, income: Social Security Retirement Benefits `$2,115`/month ($25,380/year exactly)
- **Expenses**: Property Taxes `$1,000`/year; no rent

**Why this matters**: Pins the `<=` comparator from below — a strict `<` rejects this household. It does **not** test the age rule: the claimant's `birth_year` is 1959, the same as Scenario 5's, and the committed rule never reads birth month. K-40H's 50% Social Security rule computes $12,690 here and still passes; Scenario 4 is what catches that.

---

### Scenario 3: Income just below the ceiling
**What we're checking**: $25,280/year — $100 under the limit — qualifies.
**Expected**: Eligible — $900/year (75% × $1,200)

**Steps**:
- **Location**: ZIP `66044`, county `Douglas County`
- **Household**: 1 person
- **Person 1**: Born March 1958, `headOfHousehold`, citizen, income: Social Security Retirement Benefits `$25,280`/year
- **Expenses**: Property Taxes `$1,200`/year; no rent

**Why this matters**: Confirms households close to but under the cap are not turned away.

---

### Scenario 4: Income just above the ceiling — not eligible
**What we're checking**: $25,480/year — $100 over — is rejected.
**Expected**: Not eligible (no value)

**Steps**:
- **Location**: ZIP `66044`, county `Douglas County`
- **Household**: 1 person
- **Person 1**: Born March 1955, `headOfHousehold`, citizen, income: Social Security Retirement Benefits `$25,480`/year
- **Expenses**: Property Taxes `$1,800`/year

**Why this matters**: Kills the K-40H copy-paste bug: under the 50% rule this computes $12,740 and wrongly passes. With Scenario 2 it pins the exact `<=` boundary.

---

### Scenario 5: Earliest qualifying birth year
**What we're checking**: Born January 1959 — 65 for all of 2025 — meets the age rule, isolated from the income boundary.
**Expected**: Eligible — $600/year (75% × $800)

**Steps**:
- **Location**: ZIP `66044`, county `Douglas County`
- **Household**: 1 person
- **Person 1**: Born January 1959, `headOfHousehold`, citizen, income: Social Security Retirement Benefits `$900`/month ($10,800/year)
- **Expenses**: Property Taxes `$800`/year; no rent

**Why this matters**: Confirms the gate is `birth_year <= 1959`, at the earliest qualifying year.

---

### Scenario 6: Turned 65 during the year — not eligible
**What we're checking**: Born March 1960 — turns 65 during 2025 but was not 65 for the entire year — fails despite meeting everything else.
**Expected**: Not eligible (no value)

**Steps**:
- **Location**: ZIP `67202`, county `Sedgwick County`
- **Household**: 1 person
- **Person 1**: Born March 1960, `headOfHousehold`, citizen, income: Social Security Retirement Benefits `$900`/month
- **Expenses**: Property Taxes `$1,200`/year

**Why this matters**: The off-by-one the age rule exists to catch. A raw current-age snapshot passes this household; `birth_year <= 1959` rejects it. Pairs with Scenario 5.

---

### Scenario 7: Age well above the minimum
**What we're checking**: A 79-year-old qualifies — 65 is a floor with no upper bound.
**Expected**: Eligible — $675/year (75% × $900)

**Steps**:
- **Location**: ZIP `67202`, county `Sedgwick County`
- **Household**: 1 person
- **Person 1**: Born March 1946 (age 79 in 2025), `headOfHousehold`, citizen, income: Social Security Retirement Benefits `$900`/month ($10,800/year)
- **Expenses**: Property Taxes `$900`/year; no rent

**Why this matters**: Catches an age rule written as a band rather than a floor.

---

### Scenario 8: Renter, otherwise fully qualified — not eligible
**What we're checking**: A 71-year-old renter meeting age, income, and residency is excluded — SAFESR requires ownership.
**Expected**: Not eligible (no value)

**Steps**:
- **Location**: ZIP `67202`, county `Sedgwick County`
- **Household**: 1 person
- **Person 1**: Born March 1954 (age 71 in 2025), `headOfHousehold`, citizen, income: Social Security Retirement Benefits `$1,200`/month ($14,400/year)
- **Expenses**: Rent `$800`/month; no mortgage or property tax

**Why this matters**: The only scenario exercising the rent gate. Every other case takes a homeowner path, so a calculator that skipped the rent check entirely would ship undetected.

---

### Scenario 9: Senior homeowner receiving SNAP
**What we're checking**: SNAP participation does not disqualify a household from SAFESR.
**Expected**: Eligible — $525/year (75% × $700)

**Steps**:
- **Location**: ZIP `66604`, county `Shawnee County`
- **Household**: 1 person
- **Person 1**: Born March 1956 (age 69 in 2025), `headOfHousehold`, citizen, current benefits: SNAP, income: Social Security Retirement Benefits `$900`/month ($10,800/year)
- **Expenses**: Property Taxes `$700`/year; no rent

**Why this matters**: SNAP is also line 13(a) excluded income on the form, so this doubles as a check that SNAP receipt is never counted toward the income ceiling.

---

### Scenario 10: Mixed household — eligible senior head, younger spouse and adult child
**What we're checking**: Only the head meets the age test, but the income ceiling applies to the whole household.
**Expected**: Eligible — $1,200/year (75% × $1,600)

**Steps**:
- **Location**: ZIP `66502`, county `Riley County`
- **Household**: 3 people
- **Person 1 (head)**: Born March 1954 (age 71), `headOfHousehold`, citizen, Social Security Retirement Benefits `$700`/month ($8,400/year)
- **Person 2 (spouse)**: Born June 1968 (age 57), `spouse`, Wages `$500`/month ($6,000/year)
- **Person 3 (adult child)**: Born January 1996 (age 29), `child`, Wages `$400`/month ($4,800/year)
- **Expenses**: Property Taxes `$1,600`/year; no rent

**Why this matters**: The age test applies only to the claimant, the income test to everyone ($8,400 + $6,000 + $4,800 = $19,200). Catches a calculator that age-gates every member. It does **not** prove aggregation — this household stays eligible at the same $1,200 even if every non-claimant's income is dropped; Scenarios 12 and 19 are what force the other members' income to be counted.

---

### Scenario 11: Two seniors in one household
**What we're checking**: Both head and spouse are 65+ and combined income is under the ceiling.
**Expected**: Eligible — $750/year (75% × $1,000)

**Steps**:
- **Location**: ZIP `66044`, county `Douglas County`
- **Household**: 2 people
- **Person 1 (head)**: Born March 1958 (age 67), `headOfHousehold`, citizen, Social Security Retirement Benefits `$700`/month
- **Person 2 (spouse)**: Born July 1958 (age 67), `spouse`, Social Security Retirement Benefits `$550`/month
- **Expenses**: Property Taxes `$1,000`/year; no rent

**Why this matters**: Confirms two qualifying-age seniors produce one household result, not two — K.S.A. 79-4507 allows only one claimant per household per year, so a calculator returning a per-member result would pay this household twice. Like Scenario 10 it does not prove aggregation — $15,000 combined and $8,400 claimant-only both clear the ceiling at the same $750; Scenarios 12 and 19 carry that.

---

### Scenario 12: An adult child's income pushes the household over the ceiling — not eligible
**What we're checking**: An adult who is neither the claimant nor the spouse lives in the homestead, and their wages are what carry household income past $25,380.
**Expected**: Not eligible (no value)

**Steps**:
- **Location**: ZIP `66502`, county `Riley County`
- **Household**: 2 people
- **Person 1 (head)**: Born March 1953 (age 72 in 2025), `headOfHousehold`, citizen, Social Security Retirement Benefits `$700`/month ($8,400/year)
- **Person 2 (adult child)**: Born June 1990 (age 35), `child`, Wages `$1,500`/month ($18,000/year)
- **Expenses**: Property Taxes `$1,200`/year; no rent

**Why this matters**: The only scenario whose result turns on a non-claimant adult's income being counted — booklet page 5, line 9, "All income (regardless of source) received by adult individuals other than you and your spouse who lived in the homestead at any time during 2025." $8,400 + $18,000 = $26,400, over the ceiling. Two ways of building this wrong return eligible with a $900 value: summing the claimant's income alone, and skipping every `child`, `stepChild` or `fosterChild` outright rather than testing birth year. This is the only scenario that catches the second — Scenarios 18 and 19 both use a `grandChild`, which a relationship filter never reaches.

---

### Scenario 13: Senior with zero income
**What we're checking**: A senior homeowner with no income is eligible and the calculator does not error on absent income data.
**Expected**: Eligible — $450/year (75% × $600)

**Steps**:
- **Location**: ZIP `66044`, county `Douglas County`
- **Household**: 1 person
- **Person 1**: Born March 1951 (age 74 in 2025), `headOfHousehold`, citizen, has income: No
- **Expenses**: Property Taxes `$600`/year; no rent

**Why this matters**: The lower income boundary. Confirms $0 is handled as eligible rather than as missing data, and that a real refund still computes from the entered property tax.

---

### Scenario 14: No housing expense entered — homeowner default and fallback value
**What we're checking**: A senior entering no housing expenses at all is still treated as a homeowner, and the value falls back rather than returning $0.
**Expected**: Eligible — $1,756/year (75% × $2,342 fallback = $1,756.50, rounded)

**Steps**:
- **Location**: ZIP `66044`, county `Douglas County`
- **Household**: 1 person
- **Person 1**: Born March 1955 (age 70 in 2025), `headOfHousehold`, citizen, Social Security Retirement Benefits `$1,200`/month ($14,400/year)
- **Expenses**: None entered — no `rent`, `mortgage`, or `propertyTax`

**Why this matters**: The only entirely empty expense set. Catches a calculator that reads a blank housing section as "not a homeowner", and one that never implements the fallback and returns $0.

---

### Scenario 15: Mortgage entered, no property tax — homeowner via the mortgage path
**What we're checking**: A senior who enters a mortgage but leaves Property Taxes blank is a homeowner, and the value falls back.
**Expected**: Eligible — $1,756/year (75% × $2,342 fallback = $1,756.50, rounded)

**Steps**:
- **Location**: ZIP `66502`, county `Riley County`
- **Household**: 1 person
- **Person 1**: Born March 1953 (age 72 in 2025), `headOfHousehold`, citizen, Social Security Retirement Benefits `$1,100`/month ($13,200/year)
- **Expenses**: Mortgage `$650`/month; no rent, no property tax

**Why this matters**: The one homeowner path no other scenario takes. Fails a calculator that derives ownership from `propertyTax` alone, or requires `propertyTax` before computing a value — both of which pass Scenario 14.

---

### Scenario 16: Property-tax row entered at $0 — fallback, not a $0 refund
**What we're checking**: A senior who opens the Property Taxes row and leaves the amount at zero gets the fallback estimate, not a $0 refund.
**Expected**: Eligible — $1,756/year (75% × $2,342 fallback = $1,756.50, rounded)

**Steps**:
- **Location**: ZIP `66604`, county `Shawnee County`
- **Household**: 1 person
- **Person 1**: Born March 1955 (age 70 in 2025), `headOfHousehold`, citizen, Social Security Retirement Benefits `$1,200`/month ($14,400/year)
- **Expenses**: Property Taxes `$0`/year — the row is present with a zero amount; no rent

**Why this matters**: The expense form permits a zero amount (`expenseAmount: z.number().int().min(0)`), and `Screen.has_expense()` matches on expense type while ignoring the amount. A calculator that gates the value branch on `has_expense(["propertyTax"])` computes 75% × $0 and hands an eligible household a $0 refund, which the results page renders as `$0/year` rather than suppressing. Scenarios 14 and 15 both pass that calculator.

---

### Scenario 17: Excluded income — SSDI and gifts are not household income
**What we're checking**: A household whose gross income is well over $25,380 still qualifies once SSDI and gifts are excluded per the form's Excluded Income section.
**Expected**: Eligible — $900/year (75% × $1,200)

**Steps**:
- **Location**: ZIP `66604`, county `Shawnee County`
- **Household**: 2 people
- **Person 1 (head)**: Born March 1952 (age 73 in 2025), `headOfHousehold`, citizen, Social Security Retirement Benefits `$1,950`/month ($23,400/year) **and** Gifts or Contributions (Received) `$250`/month ($3,000/year)
- **Person 2 (adult child)**: Born June 1985 (age 40), `child`, Social Security Disability Benefits `$900`/month ($10,800/year)
- **Expenses**: Property Taxes `$1,200`/year; no rent

**Why this matters**: Gross income is $37,200; SAFESR household income is $23,400 once `sSDisability` and `gifts` drop. Each exclusion crosses the ceiling on its own, so either one being missed from the `exclude` list flips the result: counting `gifts` gives $26,400, counting `sSDisability` gives $34,200. Also catches `calc_gross_income` called with no `exclude` at all.

---

### Scenario 18: Grandchild who turns 18 mid-year, plus child support — neither counts
**What we're checking**: A grandchild born in June 2007 is 18 for part of 2025 but not all of it, so their wages stay out of household income; the child support the head receives for them is excluded too.
**Expected**: Eligible — $900/year (75% × $1,200)

**Steps**:
- **Location**: ZIP `66604`, county `Shawnee County`
- **Household**: 2 people
- **Person 1 (head)**: Born March 1953 (age 72 in 2025), `headOfHousehold`, citizen, income: Social Security Retirement Benefits `$1,900`/month ($22,800/year) **and** Child Support `$5,000`/year
- **Person 2 (grandchild)**: Born June 2007 (17 until June 2025), `grandChild`, income: Wages `$400`/month ($4,800/year)
- **Expenses**: Property Taxes `$1,200`/year; no rent

**Why this matters**: Household income is $22,800 against a $32,600 gross. Three ways of building this wrong cross the ceiling and return not eligible: keying the skip to `relationship`, since `grandChild` is not in `KsK40h`'s tuple ($27,600); writing the cutoff as `birth_year > claim_year - 18`, which treats a 2007 birth as an adult ($27,600); and omitting `childSupport` from the excluded types ($27,800). The child-support exclusion follows the K-40PT against a statute that reads the other way (see criterion 4); this scenario is what pins the form's treatment. Scenario 19 is the other half of the adulthood boundary.

---

### Scenario 19: Grandchild who was 18 all year — income counted, not eligible
**What we're checking**: A grandchild born in June 2006 was 18 for the whole of 2025, so their wages are household income and carry the household over the ceiling.
**Expected**: Not eligible (no value)

**Steps**:
- **Location**: ZIP `66604`, county `Shawnee County`
- **Household**: 2 people
- **Person 1 (head)**: Born March 1952 (age 73 in 2025), `headOfHousehold`, citizen, income: Social Security Retirement Benefits `$1,900`/month ($22,800/year)
- **Person 2 (grandchild)**: Born June 2006 (age 19 in 2025), `grandChild`, income: Wages `$400`/month ($4,800/year)
- **Expenses**: Property Taxes `$1,200`/year; no rent

**Why this matters**: $22,800 + $4,800 = $27,600, over the ceiling. Paired with Scenario 18 it pins the cutoff at exactly `birth_year >= claim_year - 18`: a cutoff one year too broad — `birth_year >= claim_year - 19`, which would also exclude a 2006 birth — returns eligible here with a $900 value.

---

### Scenario 20: Veteran's benefits excluded — eligible only because the bucket drops
**What we're checking**: A senior whose gross income is over the ceiling qualifies once the `veteran` income bucket is excluded per criterion 11.
**Expected**: Eligible — $1,050/year (75% × $1,400)

**Steps**:
- **Location**: ZIP `66502`, county `Riley County`
- **Household**: 1 person
- **Person 1**: Born March 1950 (age 75 in 2025), `headOfHousehold`, citizen, income: Social Security Retirement Benefits `$1,600`/month ($19,200/year) **and** Veteran's Pension or Benefits `$700`/month ($8,400/year)
- **Expenses**: Property Taxes `$1,400`/year; no rent

**Why this matters**: The only scenario carrying `veteran` income. Gross is $27,600; SAFESR household income is $19,200 once the bucket drops. Counting it — which is what `KsK40h` does — returns not eligible, so the suite fails the moment the exclusion is dropped. The exclusion is a stand-in, not the Kansas rule: a claimant whose $8,400 is a veterans' *pension* rather than disability compensation is admitted here when a filed claim would count it.

---

## Acceptance Criteria

The 20 cases in Test Scenarios are the scenario-level acceptance conditions — each carries one
committed eligibility result and, where eligible, one committed value. The build is accepted when
all 20 pass and the following hold:

[ ] Age gate reads `birth_year`, keyed to the config's claim year — not a hardcoded year, not `age`. When `self.program.year` is `None` the claim year falls back to the newest key in `income_limit_by_year`, so the age gate and the income ceiling always describe the same year
[ ] Household income counts all four Social Security streams — `sSRetirement`, `sSSurvivor`, `sSI`, `sSDependent` — at 100%, not K-40H's 50%
[ ] Household income excludes `sSDisability`, `childSupport`, `gifts`, and the whole `veteran` bucket — the last as a committed proxy for a split the screener cannot make, documented as such in code comments rather than as the Kansas rule
[ ] Household income skips members whose `birth_year >= claim_year - 18`, keyed to birth year rather than to `relationship`, and counts every other member — an adult `child` included
[ ] The calculator declares `dependencies = ("age", "income_type", "income_amount", "income_frequency", "expenses")` — not `relationship`, not `household_size`
[ ] The refund is rounded to the nearest whole dollar
[ ] The fallback applies whenever `calc_expenses("yearly", ["propertyTax"])` is zero, including when a `propertyTax` row exists at $0, and is $2,342/year (Census B25103, ACS 2020–2024, Kansas not-mortgaged), documented in code comments as an MFB estimate, producing $1,756

## Research Sources

| Title | URL | Retrieved |
|---|---|---|
| KDOR — Kansas Property Tax Relief for Low Income Seniors (SAFESR) | https://www.ksrevenue.gov/safesenior.html | 2026-09-16 |
| Form K-40PT (2025) — Kansas Property Tax Relief Claim for Low Income Seniors | https://www.ksrevenue.gov/pdf/k-40pt25.pdf | 2026-09-16 |
| 2025 Homestead Booklet (K-40H/K-40PT/K-40SVR) — the operative instructions for K-40PT lines 4–9 and Excluded Income, which the form's back incorporates by reference | https://www.ksrevenue.gov/pdf/k-40hbook25.pdf | 2026-09-18 |
| KDOR Notice 25-05 — Household Income for Property Tax Relief Claims (2025-07-03) | https://www.ksrevenue.gov/taxnotices/notice25-05.pdf | 2026-09-16 |
| KDOR — Kansas Homestead Refund Programs (three-refund comparison; filing software) | https://www.ksrevenue.gov/perstaxtypeshs.html | 2026-09-18 |
| KDOR — Homestead forms page (the config's apply target; carries K-40H, K-40PT and K-40SVR, 2025 back to 2008) | https://www.ksrevenue.gov/forms-hs.html | 2026-09-18 |
| U.S. Census Bureau ACS 5-year 2020–2024, table B25103, Kansas | https://data.census.gov/table/ACSDT5Y2024.B25103?g=040XX00US20 | 2026-09-16 |
| K.S.A. 79-32,263 — SAFESR: the 75% rate, the age test, the 120%-of-FPL-for-two-persons ceiling, the one-refund rule, and SAFESR's own household-income definition | https://www.ksrevisor.gov/statutes/chapters/ch79/079_032_0263.html | 2026-09-20 |
| K.S.A. 79-4502 — Homestead Property Tax Refund Act definitions: income, claimant, household, property taxes accrued | https://www.ksrevisor.gov/statutes/chapters/ch79/079_045_0002.html | 2026-09-20 |
| K.S.A. 79-4507 — one claimant per household per year | https://www.ksrevisor.gov/statutes/chapters/ch79/079_045_0007.html | 2026-09-20 |
| K.S.A. 79-4522 — the $350,000 appraised-value bar, and the comparator that settles the KDOR conflict | https://www.ksrevisor.gov/statutes/chapters/ch79/079_045_0022.html | 2026-09-20 |

## Program Configuration

File: `ks_safesr_initial_config.json`

`year` is set to `"2025"` **deliberately, even though SAFESR has no FPL-based income test.**
The Program Researcher handbook says to include `year` only for FPL-based thresholds and warns
that it is often added unnecessarily — that guidance does not apply here, and the field must not
be stripped on that basis. SAFESR's $25,380 ceiling is a flat figure published by KDOR; it is
statutorily 120% of the two-person FPL, but deriving it reproduces the published number only for
2025 ($23,664 vs a published $23,700 for 2023; $24,528 vs $24,500 for 2024), so the published
figure is operative and the formula is only a cross-check.

The field is carried because the **claim year** must come from config rather than a literal. The
calculator reads `self.program.year.period` for both the age gate ("born before January 1, 1960")
and the ceiling, so that both follow the tax year. `ks_k40h` omits `year` and therefore falls back
to a hardcoded 2025 in `_meets_categorical` — the defect this program is avoiding.

Two consequences a dev should know. `Program.year` is a **foreign key** to a `FederalPoveryLimit`
row, resolved by `import_program_config` as
`FederalPoveryLimit.objects.get(year=year_value, period=year_value)`, which logs only a *warning*
on miss — so if no row has `year == period == "2025"`, `program.year` silently lands as `None` and
the calculator must take its committed `None` branch. And `--dry-run` does not test this:
`handle()` calls `_print_dry_run_report` and returns before `_import_program` runs, so the year FK,
the category, the documents and the navigators are all echoed back unverified.
