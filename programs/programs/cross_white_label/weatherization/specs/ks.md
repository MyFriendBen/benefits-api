# Weatherization Assistance Program (KS) — Program Spec

- **Program key**: `ks_wap` (`programs/programs/cross_white_label/weatherization/ks.py`, class `KsWap`)
- **Base federal program**: Weatherization Assistance Program for Low-Income Persons (U.S. Department of Energy), 42 U.S.C. §§ 6861–6873 and 10 CFR part 440 — `base_program: wap`
- **White label**: KS
- **Engine**: MFB custom
- **Added to MFB**: not yet added
- **Policy year**: 2026
- **Spec last updated**: 2026-09-03
- **Sources verified as of**: 2026-09-02

## Covered Eligibility Criteria

**(criterion 1 OR criterion 3) AND criterion 4 AND criterion 5.** Categorical receipt substitutes for the income test; it is never ANDed with it. Criterion 2 defines the income criterion 1 measures, and criterion 6 defines the unit both are measured over.

1. **The household's income is at or below 200 percent of the federal poverty level for its size.**
   - Evaluation scope: `household`
   - Captured via: countable income as defined by criterion 2, compared against `household_size` (Screen, IntegerField)
   - Implementation:
     - `countable_income <= fpl_percent * program.year.get_limit(household_size)`, with `fpl_percent = 2.0` as a class constant.
     - Read the threshold through `program.year.get_limit(household_size)`. Never index `program.year.as_dict()[household_size]` — that raises `KeyError` above the table's explicit rows, while the helper extrapolates.
     - The comparison is inclusive (`<=`).
     - `household_size` is nullable. When absent, treat the criterion as met rather than comparing.
     - The poverty edition is configuration, not a constant: the program row's `year: "2026"` reproduces Kansas's printed limits exactly — 200 percent of the 2026 one-person guideline of $15,960 is the $31,920 Kansas prints.
   - Source: 42 U.S.C. § 6862(7)(A) — "is at or below 200 percent of the poverty level determined in accordance with criteria established by the Director of the Office of Management and Budget" — [snapshot `2026-08-26--42-usc-6862`](../../../sources/ks/ks_wap/2026-08-26--42-usc-6862/content.md), accessed 2026-08-26
   - Source: 10 CFR 440.22(a)(1) — "Whose income is at or below 200 percent of the poverty level determined in accordance with criteria established by the Director of the Office of Management and Budget," — [snapshot `2026-09-02--10-cfr-440-22`](../../../sources/ks/ks_wap/2026-09-02--10-cfr-440-22/content.md), accessed 2026-09-02
   - Source: KHRC standardized weatherization application, revised 2026-02-23, p. 1 "PROGRAM ELIGIBILITY", the operative limits — the printed table interleaves two columns, sizes 1–8 on the left and 9–16 on the right: "Maximum Income for Maximum Income for Family Family Weatherization Weatherization Size Size (200% of FPL) (200% of FPL) 1 $31,920 9 $122,800 2 $43,280 10 $134,160 3 $54,640 11 $145,520 4 $66,000 12 $156,880 5 $77,360 13 $168,240 6 $88,720 14 $179,600 7 $100,080 15 $190,960 8 $111,440 16 $202,320" — [snapshot `2026-08-26--khrc-standardized-wx-application-2026-02-23`](../../../sources/ks/ks_wap/2026-08-26--khrc-standardized-wx-application-2026-02-23/content.md), accessed 2026-08-26
   - Source: HHS ASPE, 2026 poverty guidelines, identifying that table's edition — the one-person figure "15,960.00" doubles to the $31,920 Kansas publishes, under the heading "2026 Poverty Guidelines: 48 Contiguous States (all states except Alaska and Hawaii) Dollars Per Year Household/ Family Size 50% 75% 100" — [snapshot `2026-08-26--hhs-2026-poverty-guidelines`](../../../sources/ks/ks_wap/2026-08-26--hhs-2026-poverty-guidelines/content.md), accessed 2026-08-26

2. **Countable income is gross cash receipts before taxes, less the exclusions the current DOE Weatherization Program Notice lists, and excluding the earned income and unemployment compensation of members under 18 or in full-time high school. Self-employment and rental income count at their *net* amount.**
   - Evaluation scope: `household`
   - Captured via: accessor `HouseholdMember.calc_gross_income("yearly", ["all"], exclude=[…])`, summed across members
   - Implementation, in calculation order:
     1. For each `HouseholdMember`, start from the base exclusion list: `childSupport`, `gifts`, `selfEmployment`, `rental`, `boarder`, `investment`.
     2. If that member's `calc_age()` is under 18, or the member is `student` and `student_full_time`, add `wages` and `unemployment` to their exclusions.
     3. Annualize: `calc_gross_income("yearly", ["all"], exclude=<that member's list>)`.
     4. Sum across members. No rounding.
   - The base list has two halves that must not be conflated. **DOE policy exclusions**: `childSupport`, `gifts`. **MFB inclusive proxies**, standing in for figures MFB cannot compute: `selfEmployment`, `rental`, `boarder`, `investment` (Data Gap 7). `alimony` is countable and stays in.
   - Kansas states no income definition of its own; it defers wholesale to the DOE notice, so the notice's definition *is* the Kansas rule. Income-stream spellings are verbatim from `configuration/white_labels/base.py`; Kansas ships no `income_options_by_category` override. Two further limits on the same definition are Data Gap 8 (the period the income is measured over) and Data Gap 9 (the Medicare deduction on a Social Security benefit letter).
   - Source: Subrecipient Procedure Manual 2025 v3, "Determining Client Income Eligibility" (manual p. 40), the deferral that makes the DOE notice controlling — "Definition of Income- Income shall be defined by the most recent DOE issued WPN in effect. Income guidance comes in WPNs labeled as WPN “year” - 3." — [snapshot `2026-08-26--khrc-wx-subrecipient-manual-2025v3`](../../../sources/ks/ks_wap/2026-08-26--khrc-wx-subrecipient-manual-2025v3/content.md), accessed 2026-08-26
   - Source: DOE WPN 25-3, Attachment "Definition of Income" § A — "Income means Cash Receipts earned and/or received by the applicant before taxes during applicable tax year(s) but not the Income Exclusions listed below in Section C. Gross Income is to be used, not Net Income." — [snapshot `2026-08-26--doe-wpn-25-3-poverty-income-guidelines`](../../../sources/ks/ks_wap/2026-08-26--doe-wpn-25-3-poverty-income-guidelines/content.md), accessed 2026-08-26
   - Source: DOE WPN 25-3, Attachment § B.2 and § B.6, the two net-figure categories — "Net receipts from non-farm or farm self-employment (receipts from a person's own business or from an owned or rented farm after deductions for business or farm expenses)." and "Net rental income and net royalties." — [snapshot `2026-08-26--doe-wpn-25-3-poverty-income-guidelines`](../../../sources/ks/ks_wap/2026-08-26--doe-wpn-25-3-poverty-income-guidelines/content.md), accessed 2026-08-26
   - Source: DOE WPN 25-3, Attachment § C, the exclusions — "Capital gains." and "Gifts, loans, or lump-sum inheritances." and "Child support, as defined below in Section E." — [snapshot `2026-08-26--doe-wpn-25-3-poverty-income-guidelines`](../../../sources/ks/ks_wap/2026-08-26--doe-wpn-25-3-poverty-income-guidelines/content.md), accessed 2026-08-26
   - Source: DOE WPN 25-3, Attachment § E, child support in both directions — "Child Support payments, whether received by the Payee or paid by the Payor, are not considered Sources of Income to be added to the payee income or deducted from the payor income for the purposes of determining applicant eligibility." — [snapshot `2026-08-26--doe-wpn-25-3-poverty-income-guidelines`](../../../sources/ks/ks_wap/2026-08-26--doe-wpn-25-3-poverty-income-guidelines/content.md), accessed 2026-08-26
   - Source: DOE WPN 25-3, Attachment § D.1, the minor rule — "Do not count, or enter, earned income or unemployment compensation for minors under the age of 18 (or full-time high school students) at the time of the application." — [snapshot `2026-08-26--doe-wpn-25-3-poverty-income-guidelines`](../../../sources/ks/ks_wap/2026-08-26--doe-wpn-25-3-poverty-income-guidelines/content.md), accessed 2026-08-26
   - Source: DOE WPN 25-3, Attachment § B.3, alimony countable — "Regular payments from social security, railroad retirement, unemployment compensation, strike benefits from union funds, worker's compensation, veteran's payments, training stipends, alimony, and military family allotments." — [snapshot `2026-08-26--doe-wpn-25-3-poverty-income-guidelines`](../../../sources/ks/ks_wap/2026-08-26--doe-wpn-25-3-poverty-income-guidelines/content.md), accessed 2026-08-26

3. **A household containing a member who currently receives SSI, TANF or LIEAP, or whose screen records a Section 8 / Housing Choice Voucher benefit, is income-eligible whatever its income.**
   - Evaluation scope: `household`
   - Implementation: `SSI OR TANF OR LIEAP OR Section 8/HCV` → skip the criterion 1 income test.
     - **SSI** — `Screen.has_base_benefit("ssi")`, or `Screen.calc_gross_income("yearly", ["sSI"]) > 0`. The stream test is a backstop: the single-benefit toggle endpoint does not re-derive the current-benefit row, so a screen can carry the stream without the row.
     - **TANF** — `Screen.has_base_benefit("tanf")`, or `Screen.calc_gross_income("yearly", ["cashAssistance"]) > 0`. MFB files TANF dollars under `cashAssistance` and never `tanf`, so the stream test is required, not optional. Kansas administers TANF under the name TAF; one program row, `ks_tanf`, backs both names.
     - **LIEAP** — `Screen.has_base_benefit("liheap")`. Wire it now; it returns false on every Kansas screen until the white-label change in Test Scenarios ships.
     - **Section 8 / HCV** — `Screen.has_base_benefit("section_8")`. Wired and inert: Kansas has no voucher program row, so it changes no current verdict and activates on its own if one is added. It reaches only Section 8 / HCV; the other HUD means-tested programs are Data Gap 1.
   - The sourced rule also reaches *past* receipt, which MFB cannot see — Data Gap 3.
   - Source: KHRC, Weatherization Assistance Program page — "Households that receive Supplemental Security Income (SSI), Temporary Assistance for Needy Families (TANF), or utility assistance from the Low Income Energy Assistance Program (LIEAP) are automatically income-eligible." — [snapshot `2026-08-26--khrc-weatherization-assistance`](../../../sources/ks/ks_wap/2026-08-26--khrc-weatherization-assistance/content.md), accessed 2026-08-26
   - Source: Subrecipient Procedure Manual 2025 v3, "Determining Client Income Eligibility" (manual p. 40) — "Applicants receiving LIEAP Utility Assistance from Kansas Department of Children and Families (KDCF) during the current program year will automatically income-qualify for weatherization services." — [snapshot `2026-08-26--khrc-wx-subrecipient-manual-2025v3`](../../../sources/ks/ks_wap/2026-08-26--khrc-wx-subrecipient-manual-2025v3/content.md), accessed 2026-08-26
   - Source: 10 CFR 440.22(a)(3), the election Kansas has taken — "If the State elects, is eligible for assistance under the Low-Income Home Energy Assistance Act of 1981, provided that such basis is at least 200 percent of the poverty level determined in accordance with criteria established by the Director of the Office of Management and Budget." — [snapshot `2026-09-02--10-cfr-440-22`](../../../sources/ks/ks_wap/2026-09-02--10-cfr-440-22/content.md), accessed 2026-09-02
   - Source: 10 CFR 440.22(a)(2) — "Which contains a member who has received cash assistance payments under Title IV or XVI of the Social Security Act or applicable State or local law at any time during the 12-month period preceding the determination of eligibility for weatherization assistance; or" — [snapshot `2026-09-02--10-cfr-440-22`](../../../sources/ks/ks_wap/2026-09-02--10-cfr-440-22/content.md), accessed 2026-09-02
   - Source: DOE Weatherization Program Notice 22-5 v3, "PURPOSE", the HUD route — "include U.S. Department of Housing and Urban Development’s (HUD) means-tested programs’ income qualifications at or below 80% of Area Median Income." — [snapshot `2026-08-26--doe-wpn-22-5-v3-hud-categorical`](../../../sources/ks/ks_wap/2026-08-26--doe-wpn-22-5-v3-hud-categorical/content.md), accessed 2026-08-26

4. **At least one United States citizen or Qualified Alien resides at the address.**
   - Evaluation scope: `config`
   - Captured via: the program row's `legal_status_required`, set to `["citizen", "gc_5plus", "gc_5less", "refugee", "otherWithWorkPermission"]`. Not calculator logic.
   - Implementation: the filter matches a household holding at least one listed status, which is the rule exactly — one qualifying resident satisfies it, so a mixed-status household passes on that member. `non_citizen` is deliberately excluded: including it would extend the program to households in which no resident is a citizen or Qualified Alien, the case Kansas's signed certification rules out. Qualified Alien carries its statutory definition.
   - Source: Subrecipient Procedure Manual 2025 v3, "Qualified Aliens Eligibility" (manual p. 42) — "All client files will contain the signed Eligibility Certification statement “I certify that there is at least one United States citizen or Qualified Alien who resides at the address listed on this application. Qualified Alien is defined in section 431 of the Personal Responsibility and Work Opportunity Reconciliation Act of 1996.”" — [snapshot `2026-08-26--khrc-wx-subrecipient-manual-2025v3`](../../../sources/ks/ks_wap/2026-08-26--khrc-wx-subrecipient-manual-2025v3/content.md), accessed 2026-08-26

5. **The dwelling is in Kansas.**
   - Evaluation scope: `config`
   - Captured via: white-label routing — a screen reaching the `ks` white label is in Kansas; `assumed-met` in the calculator
   - Implementation: service area adds no further restriction. Each subrecipient must cover the whole of its own territory, so no Kansas address is outside the program.
   - Source: Kansas Weatherization State Plan 2025, § V.1.1 — "shall be eligible for weatherization assistance in Kansas" — [snapshot `2026-08-26--ks-weatherization-state-plan-2025-draft`](../../../sources/ks/ks_wap/2026-08-26--ks-weatherization-state-plan-2025-draft/content.md), accessed 2026-08-26
   - Source: Subrecipient Procedure Manual 2025 v3, "Priority Groups" (manual p. 42), on coverage being complete — "Local agencies are required to serve their entire geographic area. Each county shall receive, at a minimum, service once every two years." — [snapshot `2026-08-26--khrc-wx-subrecipient-manual-2025v3`](../../../sources/ks/ks_wap/2026-08-26--khrc-wx-subrecipient-manual-2025v3/content.md), accessed 2026-08-26

6. **The unit measured is the family unit: all persons living together in the dwelling.**
   - Evaluation scope: `household`
   - Captured via: `household_size` (Screen, IntegerField) and the entered `HouseholdMember` list, which are what criteria 1 and 2 read
   - Implementation: use `household_size` and the entered member list **as entered**, for both the poverty-table row and the countable-income sum. Do **not** reconstruct the unit from tax-unit status or relationship fields. This follows the Kansas LIEAP convention, which also treats the unit as everyone living at the address.
   - The proxy is imperfect in both directions, and neither direction is observable: MFB's household-size step includes a spouse "even if you file taxes separately or live apart" (broader than the family unit), and includes another resident "only ... if you buy and prepare the majority of your food together" (narrower). Residual limitation: Data Gap 4.
   - Source: 10 CFR 440.3 — "Family Unit means all persons living together in a dwelling unit." — [snapshot `2026-09-02--10-cfr-440-3`](../../../sources/ks/ks_wap/2026-09-02--10-cfr-440-3/content.md), accessed 2026-09-02
   - Source: 10 CFR 440.22(a) — "A dwelling unit shall be eligible for weatherization assistance under this part if it is occupied by a family unit:" — [snapshot `2026-09-02--10-cfr-440-22`](../../../sources/ks/ks_wap/2026-09-02--10-cfr-440-22/content.md), accessed 2026-09-02

## Missing Eligibility Criteria (Data Gaps)

Every gap below carries one committed treatment.

**Shared convention, gaps 1–3.** For an affirmative categorical pathway MFB cannot observe, absence of an MFB record is not treated as proof that the pathway does not apply. The calculator evaluates every observable income and current-benefit route; the unobservable route cannot independently activate eligibility, and it is disclosed to the user. It is not inferred true either — assuming an OR-branch met would resolve the eligibility disjunction for every Kansas household and reduce criterion 1 to dead code.

1. **HUD means-tested categorical route**
   - Rule: a household qualifying under a HUD means-tested program is income-eligible whatever its income.
   - MFB handling: shared convention above. The Section 8 / HCV sliver is already wired in criterion 3 and becomes live if a Kansas voucher row lands; public housing, TBRA and the non-housing HUD programs have no MFB representation at all.
   - Effect: disclosure-only.
   - User-facing: yes.
   - Source: Subrecipient Procedure Manual 2025 v3, "Determining Client Income Eligibility" (manual p. 40) — "WPN 22-5 extended categorical income eligibility to HUD means-tested programs." — [snapshot `2026-08-26--khrc-wx-subrecipient-manual-2025v3`](../../../sources/ks/ks_wap/2026-08-26--khrc-wx-subrecipient-manual-2025v3/content.md), accessed 2026-08-26
   - Source: Subrecipient Procedure Manual 2025 v3, "Eligibility Determined by Outside Agency/Program" (manual p. 40), what Kansas accepts as proof — "such as a copy of the LIEAP list, USDA or HUD eligibility documentation (TBRA, Section 8 or public housing eligibility), will suffice as evidence of client eligibility" — [snapshot `2026-08-26--khrc-wx-subrecipient-manual-2025v3`](../../../sources/ks/ks_wap/2026-08-26--khrc-wx-subrecipient-manual-2025v3/content.md), accessed 2026-08-26

2. **USDA means-tested categorical route**
   - Rule: a household qualifying under a select USDA means-tested program at or below 80 percent of area median income is income-eligible whatever its income.
   - MFB handling: shared convention above. MFB has no representation of any USDA means-tested program in any white label, so there is nothing to wire.
   - Effect: disclosure-only.
   - User-facing: yes.
   - Source: Subrecipient Procedure Manual 2025 v3, "Determining Client Income Eligibility" (manual p. 40) — "WPN 25-4 extended categorical income eligibility to select U.S. Department of Agriculture (USDA) means-tested programs at 80% AMI or below." — [snapshot `2026-08-26--khrc-wx-subrecipient-manual-2025v3`](../../../sources/ks/ks_wap/2026-08-26--khrc-wx-subrecipient-manual-2025v3/content.md), accessed 2026-08-26
   - Source: DOE Weatherization Program Notice 25-4, "BACKGROUND" — "USDA’s means-tested low-income programs accept households using 80% AMI or below, depending on specific program parameters." — [snapshot `2026-08-26--doe-wpn-25-4-usda-categorical`](../../../sources/ks/ks_wap/2026-08-26--doe-wpn-25-4-usda-categorical/content.md), accessed 2026-08-26

3. **Cash assistance received in the prior 12 months**
   - Rule: past receipt qualifies a household, not only present receipt — cash assistance at any point in the preceding twelve months.
   - MFB handling: shared convention above. The current-benefit table is a screen-to-program join with no dates and no field records a formerly-held benefit, so the lookback cannot be modelled; current receipt is sufficient positive evidence.
   - Effect: disclosure-only. The affected population is ordinary rather than marginal — leaving TANF or SSI for work is the standard exit path and income at exit routinely lands above the limit — so the description names this route explicitly.
   - User-facing: yes.
   - Source: 10 CFR 440.22(a)(2) — "at any time during the 12-month period preceding the determination of eligibility for weatherization assistance" — [snapshot `2026-09-02--10-cfr-440-22`](../../../sources/ks/ks_wap/2026-09-02--10-cfr-440-22/content.md), accessed 2026-09-02
   - Source: Subrecipient Procedure Manual 2025 v3, "Determining Client Income Eligibility" (manual p. 40), defining the window — "“During the 12- month period” is defined as having received within the 12-month period but not restricted to the entire period during that program year." — [snapshot `2026-08-26--khrc-wx-subrecipient-manual-2025v3`](../../../sources/ks/ks_wap/2026-08-26--khrc-wx-subrecipient-manual-2025v3/content.md), accessed 2026-08-26

4. **Family unit vs MFB household**
   - Rule: WAP counts all persons living together in the dwelling. MFB does not independently observe who lives at the address.
   - MFB handling: the committed proxy in criterion 6 — `household_size` and the entered member list, used as entered, never reconstructed from tax-unit or relationship fields.
   - Effect: non-uniform. The mismatch runs in both directions, and a smaller unit means a lower poverty-table row but also less income counted, so the direction of error is not fixed.
   - User-facing: yes — the description says the provider will confirm who lives in the home.
   - Source: 10 CFR 440.3 — "Family Unit means all persons living together in a dwelling unit." — [snapshot `2026-09-02--10-cfr-440-3`](../../../sources/ks/ks_wap/2026-09-02--10-cfr-440-3/content.md), accessed 2026-09-02

5. **Occupancy of the dwelling applied for**
   - Rule: the household must occupy the dwelling for which it is applying.
   - MFB handling: `assumed-met`. The screener collects no housing or tenure information — `housing_situation` exists as a column on `Screen` but is not collected, is absent from `ScreenSerializer`, is never assigned by the frontend, and is read by no calculator.
   - Effect: inclusive — widens results, for households with no dwelling to weatherize.
   - User-facing: yes — the description must tell the applicant they have to live in the home they are applying for.
   - Source: 10 CFR 440.22(a) — "A dwelling unit shall be eligible for weatherization assistance under this part if it is occupied by a family unit:" — [snapshot `2026-09-02--10-cfr-440-22`](../../../sources/ks/ks_wap/2026-09-02--10-cfr-440-22/content.md), accessed 2026-09-02
   - Source: KHRC standardized weatherization application, revised 2026-02-23, p. 1 "PROGRAM ELIGIBILITY" — "You and your household must occupy the home that you are applying to receive assistance with through this Program." — [snapshot `2026-08-26--khrc-standardized-wx-application-2026-02-23`](../../../sources/ks/ks_wap/2026-08-26--khrc-standardized-wx-application-2026-02-23/content.md), accessed 2026-08-26
   - Source: Subrecipient Procedure Manual 2025 v3, "Eligible Rental Units" (manual p. 44), tenure being neutral — "Renter occupied housing units are eligible for weatherization services if they meet all other eligibility requirements." — [snapshot `2026-08-26--khrc-wx-subrecipient-manual-2025v3`](../../../sources/ks/ks_wap/2026-08-26--khrc-wx-subrecipient-manual-2025v3/content.md), accessed 2026-08-26

6. **Full-time high-school student**
   - Rule: the earned income and unemployment compensation of a full-time high-school student is excluded regardless of age.
   - MFB handling: inclusive proxy. Criterion 2 implements the under-18 half exactly from `birth_year_month`; for the other half, `student` and `student_full_time` (HouseholdMember, BooleanField) record full-time student status without distinguishing high school from college, so the exclusion applies at any age.
   - Effect: inclusive — widens results. It over-excludes full-time college students' wages, which lowers countable income and so cannot turn an eligible household ineligible.
   - Source: DOE WPN 25-3, Attachment § D.1 — "Do not count, or enter, earned income or unemployment compensation for minors under the age of 18 (or full-time high school students) at the time of the application." — [snapshot `2026-08-26--doe-wpn-25-3-poverty-income-guidelines`](../../../sources/ks/ks_wap/2026-08-26--doe-wpn-25-3-poverty-income-guidelines/content.md), accessed 2026-08-26

7. **Net self-employment and rental income, and capital gains**
   - Rule: self-employment and rental income count at their net amount, and capital gains are excluded from otherwise-countable dividends and interest.
   - MFB handling: inclusive proxy. MFB collects no business, farm or rental expense fields, so it cannot derive a net figure from a reported gross one; and its `investment` stream fuses countable dividends and interest with excluded capital gains into one number that cannot be split. `selfEmployment`, `rental`, `boarder` and `investment` are therefore excluded in full. `boarder` is grouped here because MFB files it with `rental` and it carries the same net-figure problem, though the notice does not name it.
   - Effect: inclusive — widens results, since dropping a whole stream can only lower countable income. This is the one gap whose inclusive direction produces an actionable false positive: a household reporting substantial self-employment, rental or investment income can be shown eligible on income Kansas will in fact count.
   - User-facing: yes — the description says the provider may count self-employment, rental, or investment income differently.
   - Source: DOE WPN 25-3, Attachment § B.2 — "Net receipts from non-farm or farm self-employment (receipts from a person's own business or from an owned or rented farm after deductions for business or farm expenses)." — [snapshot `2026-08-26--doe-wpn-25-3-poverty-income-guidelines`](../../../sources/ks/ks_wap/2026-08-26--doe-wpn-25-3-poverty-income-guidelines/content.md), accessed 2026-08-26
   - Source: DOE WPN 25-3, Attachment § B.6 — "Net rental income and net royalties." — [snapshot `2026-08-26--doe-wpn-25-3-poverty-income-guidelines`](../../../sources/ks/ks_wap/2026-08-26--doe-wpn-25-3-poverty-income-guidelines/content.md), accessed 2026-08-26
   - Source: DOE WPN 25-3, Attachment § B.5 and § C.1, the split MFB cannot make — "Dividends and/or interest." and "Capital gains." — [snapshot `2026-08-26--doe-wpn-25-3-poverty-income-guidelines`](../../../sources/ks/ks_wap/2026-08-26--doe-wpn-25-3-poverty-income-guidelines/content.md), accessed 2026-08-26

8. **Income measurement period**
   - Rule: income is verified or calculated for the one-year period prior to the certification month, may be annualized from a shorter recent period (Kansas's stated method is the most recent three months × 4), and a household found ineligible on the three-month average may provide twelve months of documentation for re-determination. The choice of method is the subrecipient's.
   - MFB handling: compare the annualized current recurring figure MFB holds — of Kansas's own accepted methods, the closest to what the screener collects. `IncomeStream` carries `amount` and `frequency` and no dates, so no history exists to use: fabricate none, and make no inference in either direction about the twelve-month route.
   - Effect: non-uniform. It widens results where income has recently fallen and narrows them where it has recently risen.
   - User-facing: yes — the description says the provider may look at recent income or a longer income history.
   - Source: Subrecipient Procedure Manual 2025 v3, "Determining Client Income Eligibility" (manual p. 40) — "Applicant income must be verified or calculated for the one-year period prior to the certification month. Income data for a part of a year may be annualized to determine eligibility. For example, by multiplying by four the amount of income received during the most recent three months. A minimum of three months’ income documentation must be available." — [snapshot `2026-08-26--khrc-wx-subrecipient-manual-2025v3`](../../../sources/ks/ks_wap/2026-08-26--khrc-wx-subrecipient-manual-2025v3/content.md), accessed 2026-08-26
   - Source: Subrecipient Procedure Manual 2025 v3, "Determining Client Income Eligibility" (manual p. 40), the route back from an adverse three-month result — "If the household is determined to be ineligible based on the average income for three months, the applicant should be notified that 12 months of documentation may be provided to re-determine eligibility." — [snapshot `2026-08-26--khrc-wx-subrecipient-manual-2025v3`](../../../sources/ks/ks_wap/2026-08-26--khrc-wx-subrecipient-manual-2025v3/content.md), accessed 2026-08-26
   - Source: Kansas Weatherization State Plan 2025, § V.1.2, the choice of method belonging to the agency — "The method of calculation is to be determined by the Subrecipient in accordance with WPN 22-3 and the Subrecipient Procedures Manual and should be uniformly applied." — [snapshot `2026-08-26--ks-weatherization-state-plan-2025-draft`](../../../sources/ks/ks_wap/2026-08-26--ks-weatherization-state-plan-2025-draft/content.md), accessed 2026-08-26

9. **Medicare deduction on Social Security**
   - Rule: when Social Security income is calculated from a benefit letter, the Medicare deduction is not income; Kansas counts the net monthly benefit.
   - MFB handling: count the Social Security amount as entered and manufacture no deduction. MFB records only whether a member carries Medicare — `medicare` (Insurance, BooleanField, one row per `HouseholdMember`), reached through `has_insurance_types` — never the premium withheld.
   - Effect: non-uniform. A user who entered their net deposit already matches Kansas; one who entered the gross benefit is over-counted, which is the narrowing direction. MFB cannot tell which was entered.
   - User-facing: yes — the description says that for Social Security, the provider uses the amount after Medicare is taken out.
   - Source: Subrecipient Procedure Manual 2025 v3, "Determining Client Income Eligibility" (manual p. 40) — "KWAP has received clarification that when using a Social Security Benefit Letter to calculate income, the deduction for Medicare is not considered income. Use the net value after the Medicare deduction for the monthly benefit." — [snapshot `2026-08-26--khrc-wx-subrecipient-manual-2025v3`](../../../sources/ks/ks_wap/2026-08-26--khrc-wx-subrecipient-manual-2025v3/content.md), accessed 2026-08-26

## Priority Criteria

Kansas uses these to order a waiting list among households that are already eligible; none affects whether a household qualifies, and none is calculator logic. Entries 2 and 3 are surfaced in the program description; entry 1 and the existence of the waiting list are surfaced in the program config's `warning_message` instead, because both are operational rather than evergreen.

1. **Emergencies outrank every other priority** — life-threatening housing conditions.
2. **Demographic groups, served first** among ordinary applicants: clients age 60 or over; clients with disabilities; families with children 18 years of age or under.
3. **Energy tier, reached only by applicants outside those three groups**: high residential energy users — previous 12-month use above 100 MCF of natural gas, 14,000 kWh of electricity or 800 gallons of propane — or a high energy burden, meaning annual energy costs at or above 15 percent of annual household income.

- Source: Subrecipient Procedure Manual 2025 v3, "Priority Groups" (manual p. 42) — "Among eligible clients there are program priorities which the Kansas Weatherization Assistance Program and the weatherization subrecipients observe. Priority is given to:" followed by "Low-income elderly clients (age 60 or over)" and "Low-income families with children 18 years of age or under" — [snapshot `2026-08-26--khrc-wx-subrecipient-manual-2025v3`](../../../sources/ks/ks_wap/2026-08-26--khrc-wx-subrecipient-manual-2025v3/content.md), accessed 2026-08-26
- Source: 10 CFR 440.16(b) — "Priority is given to identifying and providing weatherization assistance to:" followed by "Persons with disabilities;" — [snapshot `2026-09-02--10-cfr-440-16`](../../../sources/ks/ks_wap/2026-09-02--10-cfr-440-16/content.md), accessed 2026-09-02
- Source: Subrecipient Procedure Manual 2025 v3, "Priority Groups" (manual p. 42), the conditional structure — "If applicants are not elderly, disabled, or members of families with children 18 years old or under, they may also be prioritized if they qualify as high residential energy users or a household with a high energy burden." — [snapshot `2026-08-26--khrc-wx-subrecipient-manual-2025v3`](../../../sources/ks/ks_wap/2026-08-26--khrc-wx-subrecipient-manual-2025v3/content.md), accessed 2026-08-26
- Source: Subrecipient Procedure Manual 2025 v3, "Priority Groups" (manual p. 42), the thresholds — "High energy users are households who’s previous 12-month energy use exceeds 100 MCF of natural gas or 14,000 kWh for electricity or 800 gallons of propane." and "High energy burden households are households where overall annual energy costs are equal to or greater than 15% of the household’s annual income." — [snapshot `2026-08-26--khrc-wx-subrecipient-manual-2025v3`](../../../sources/ks/ks_wap/2026-08-26--khrc-wx-subrecipient-manual-2025v3/content.md), accessed 2026-08-26
- Source: Subrecipient Procedure Manual 2025 v3, "Priority Groups" (manual p. 42), emergencies — "Emergencies may take precedence over all other priorities. Emergencies are defined as life-threatening housing conditions and shall be documented in the client file." — [snapshot `2026-08-26--khrc-wx-subrecipient-manual-2025v3`](../../../sources/ks/ks_wap/2026-08-26--khrc-wx-subrecipient-manual-2025v3/content.md), accessed 2026-08-26

## Related Programs

- **Kansas Low Income Energy Assistance Program (LIEAP)** — `ks_lieap`, Kansas's LIHEAP program, administered by the Department for Children and Families rather than KHRC. Current LIEAP receipt is a categorical route into KS WAP (criterion 3). It is otherwise a separate program with its own eligibility and its own value, and nothing about it enters this program's calculation.
  - Source: KEESM 13000, LIEAP's own income standard, which is not this program's — "Combined income of all persons living at the address must not exceed 150% of the federal poverty level;" — [snapshot `2026-08-26--keesm-13000-lieap`](../../../sources/ks/ks_wap/2026-08-26--keesm-13000-lieap/content.md), accessed 2026-08-26

## Benefit Value

- **Estimated value**: **$7,475**, one time
- **`value_format`**: `lump_sum`. The program installs measures once; it is not recurring, so no annualization applies.
- **Type**: an MFB estimate of the in-kind weatherization service. Not a payment, not an entitlement, and not a promise of a fixed amount of work — the measures come from an on-site energy audit and vary by home.
- **Method**: Kansas's most recently published average program-operations cost per dwelling unit, $7,474.93, rounded to the dollar.
- **Variation axes**: flat. The audit-selected measures, the fuel type and single-family versus multifamily drive the real cost, and none is derivable from anything the screener collects, so the value does not vary by household and no scenario varies it.
- **Not the ceiling**: the PY2025 average expenditure limit of $8,550 in the same plan caps what the grantee may average statewide, not what a household receives; the plan's own planning figure of $7,500 sits beside the $7,474.93. Kansas publishes no energy-savings estimate, so a cost-per-unit figure is the only Kansas-specific option.
- Source: Kansas Weatherization State Plan 2025, § IV.2 WAP Production Schedule — "Average Program Operations Costs per Unit (F divided by G) ..............................................                       $ 7,474.93" and "Total Average Cost per Dwelling Unit (H plus I) ..................................................................              $7,474.93" — [snapshot `2026-08-26--ks-weatherization-state-plan-2025-draft`](../../../sources/ks/ks_wap/2026-08-26--ks-weatherization-state-plan-2025-draft/content.md), accessed 2026-08-26
- Source: Kansas Weatherization State Plan 2025, § IV.2, the ceiling distinguished — "The PY 2025 average expenditure limit is $8,550 per Weatherization Program Notice 23-1, effective date of December 20, 2024, and shall be the maximum average expenditure allowed. For planning purposes an average of $7,500 will be used which is closer to historical state averages." — [snapshot `2026-08-26--ks-weatherization-state-plan-2025-draft`](../../../sources/ks/ks_wap/2026-08-26--ks-weatherization-state-plan-2025-draft/content.md), accessed 2026-08-26

## Test Scenarios

Sixteen core scenarios, all executable against the current screener. Location appears in every scenario because the screener collects it, but it never discriminates: criterion 5 is satisfied by the white label and coverage is statewide. Every eligible scenario expects the flat $7,475; no scenario varies the value.

**Coverage map**

| Modelable branch | Scenarios |
|---|---|
| Income at or below 200% FPL, inclusive boundary (criterion 1) | 1, 2, 3 |
| Limit indexed to household size (criterion 1) | 4, 5, 16 |
| Income summed across members; monthly converted to yearly (criterion 1) | 2 |
| Zero income is $0, not missing data (criterion 1) | 10 |
| DOE policy exclusions — child support received, gifts (criterion 2) | 11 |
| Child support *paid* is not a deduction (criterion 2) | 15 |
| Minor's wages and unemployment excluded (criterion 2) | 12 |
| Alimony countable (criterion 2) | 13 |
| Categorical route — SSI, current benefit and income stream (criterion 3) | 6, 7 |
| Categorical route — TANF, current benefit and `cashAssistance` stream (criterion 3) | 8, 14 |
| Categorical route — LIEAP (criterion 3) | none yet; see the binding implementation requirements below |
| SNAP is not a categorical route (criterion 3) | 9 |
| Value | flat $7,475 in every eligible scenario |

**Known scenario gaps**

- Config-level criteria are tested outside this calculator suite: legal status (criterion 4) is the program row's `legal_status_required`, and Kansas routing (criterion 5) is the white label.
- The committed data gaps have no executable scenarios, because the screener cannot observe them.
- Section 8 / HCV has no executable Kansas scenario: no Kansas `section_8` program row exists.
- LIEAP is covered by binding implementation requirement 1 below.
- **Household sizes 9–16 are not reachable.** The screener caps household size at 8, so no scenario above that size can be entered. Sizes 1–8 are the full testable range; requirement 2 below records what was and was not delivered.

**Binding implementation requirements**

Both were committed build requirements for this program. Requirement 1 is delivered; requirement 2 is delivered on the calculator side only.

1. **LIEAP current-benefit visibility — delivered.** `ks_lieap.show_in_has_benefits_step` is set to `true` (in the program's config and, for rows that already exist, migration `0175_ks_lieap_on_has_benefits_step`). No separate white-label or frontend change was needed: the has-benefits step is data-driven, rendering whatever `/api/has_benefits_programs/{white_label}` returns and grouping it by the program's own category. Until this landed, no `CurrentBenefit` row for LIEAP could be written, `has_base_benefit("liheap")` was false on every Kansas screen, and criterion 3's LIEAP route could not fire. Regression, now ordinary coverage: an over-income Kansas household with current `ks_lieap` → **Eligible — $7,475**.

2. **Kansas household sizes 1–16 — calculator only; the screener still caps at 8.**
   - **Delivered:** `KsWap` reads the threshold through `program.year.get_limit(household_size)`, never `as_dict()[household_size]`. That extends past size 8 by the per-additional-person amount and reproduces KHRC's printed rows for 9 through 16 exactly ($122,800 … $202,320). Unit-tested at every published size, including 10 and 16.
   - **Not delivered:** the screener does not accept a household larger than 8. The cap is a hardcoded `.lte(8)` in `benefits-calculator` (`src/Components/Steps/HouseholdSize/HouseholdSize.tsx`), not a per-white-label setting, so Kansas cannot be raised on its own without a frontend change. A Kansas household of 9 or more therefore cannot be screened at all, and this program's sizes 9–16 support is unreachable in production.
   - **Why it was not done here:** raising the cap is cross-cutting rather than KS-specific. Twelve calculators and urgent needs index `program.year.as_dict()[household_size]` directly and would raise `KeyError` above size 8 — and because `screener/views.py` catches only `DependencyError` around the per-program loop, that would 500 the entire eligibility response rather than dropping one program. HUD publishes AMI only for sizes 1–8 (and the client enforces it), and the SMI service has its own `MAX_HOUSEHOLD_SIZE = 8`, so ~28 programs have no upstream limit to read above 8. Kansas's PolicyEngine-backed programs have also never received a household that large.
   - **Tracked in MFB-1869**, an investigation into whether and how to raise the cap. Until it concludes, treat size 8 as this program's effective maximum.

### Scenario 1: Four-person household under the income limit — Eligible, $7,475
**What we're checking**: the reference case — income comfortably within the limit for the household's size.
**Expected**: Eligible — $7,475
**Household size**: `4`
**Steps**:
* Location: ZIP `66603`, county `Shawnee County`
* Person 1 — `headOfHousehold`: `birth_year` 1988, `birth_month` 3, income `wages` $60,000/yearly
* Person 2 — `spouse`: `birth_year` 1990, `birth_month` 7, no income
* Person 3 — `child`: `birth_year` 2016, `birth_month` 1, no income
* Person 4 — `child`: `birth_year` 2019, `birth_month` 5, no income
* Current benefits: none
**Calculation**: $60,000 ≤ $66,000, the four-person limit.
**Why this matters**: Confirms the income comparison runs and is neither inverted nor dropped.

### Scenario 2: Four-person household exactly at the income limit — Eligible, $7,475
**What we're checking**: the boundary is inclusive, income is summed across earners, and monthly income is annualized first.
**Expected**: Eligible — $7,475
**Household size**: `4`
**Steps**:
* Location: ZIP `66603`, county `Shawnee County`
* Person 1 — `headOfHousehold`: `birth_year` 1988, `birth_month` 3, income `wages` $4,000/monthly
* Person 2 — `spouse`: `birth_year` 1990, `birth_month` 7, income `wages` $1,500/monthly
* Person 3 — `child`: `birth_year` 2016, `birth_month` 1, no income
* Person 4 — `child`: `birth_year` 2019, `birth_month` 5, no income
* Current benefits: none
**Calculation**: ($4,000 + $1,500) × 12 = $66,000, exactly the four-person limit, and the comparison is `<=`.
**Why this matters**: Confirms the inclusive boundary, multi-member summation and monthly-to-yearly conversion all hold at once.

### Scenario 3: Four-person household one dollar over the income limit — Ineligible
**What we're checking**: the limit actually excludes, with no observable categorical route in play.
**Expected**: Ineligible
**Household size**: `4`
**Steps**:
* Location: ZIP `66603`, county `Shawnee County`
* Person 1 — `headOfHousehold`: `birth_year` 1988, `birth_month` 3, income `wages` $66,001/yearly
* Person 2 — `spouse`: `birth_year` 1990, `birth_month` 7, no income
* Person 3 — `child`: `birth_year` 2016, `birth_month` 1, no income
* Person 4 — `child`: `birth_year` 2019, `birth_month` 5, no income
* Current benefits: none
**Calculation**: $66,001 > $66,000, the four-person limit.
**Why this matters**: Confirms the income limit excludes when no categorical route applies.

### Scenario 4: One-person household at the one-person limit — Eligible, $7,475
**What we're checking**: the one-person entry of the poverty table, at its exact value.
**Expected**: Eligible — $7,475
**Household size**: `1`
**Steps**:
* Location: ZIP `66603`, county `Shawnee County`
* Person 1 — `headOfHousehold`: `birth_year` 1975, `birth_month` 2, income `wages` $31,920/yearly
* Current benefits: none
**Calculation**: $31,920 = $31,920, the one-person limit, and the comparison is `<=`.
**Why this matters**: Pins the one-person poverty-table entry at $31,920.

### Scenario 5: One-person household at a four-person income — Ineligible
**What we're checking**: the limit is indexed to the household's own size, in the failing direction.
**Expected**: Ineligible
**Household size**: `1`
**Steps**:
* Location: ZIP `66603`, county `Shawnee County`
* Person 1 — `headOfHousehold`: `birth_year` 1975, `birth_month` 2, income `wages` $66,000/yearly
* Current benefits: none
**Calculation**: $66,000 > $31,920, the one-person limit. The same income is eligible at four people (scenario 2).
**Why this matters**: Confirms the limit is indexed to `household_size` rather than to a constant.

### Scenario 6: Household above the income limit receiving SSI — Eligible, $7,475
**What we're checking**: categorical receipt substitutes for the income test rather than adding to it.
**Expected**: Eligible — $7,475
**Household size**: `2`
**Steps**:
* Location: ZIP `66603`, county `Shawnee County`
* Person 1 — `headOfHousehold`: `birth_year` 1962, `birth_month` 11, income `wages` $90,000/yearly
* Person 2 — `spouse`: `birth_year` 1966, `birth_month` 11, no income
* Current benefits: SSI (`ks_ssi`)
**Calculation**: $90,000 > $43,280, the two-person limit; SSI receipt qualifies the household regardless.
**Why this matters**: Confirms categorical SSI receipt bypasses the income test rather than being ANDed with it.

### Scenario 7: Household above the income limit reporting SSI only as income — Eligible, $7,475
**What we're checking**: SSI reported as an income stream counts, and the stream is found on any member rather than only the head.
**Expected**: Eligible — $7,475
**Household size**: `2`
**Steps**:
* Location: ZIP `66603`, county `Shawnee County`
* Person 1 — `headOfHousehold`: `birth_year` 1958, `birth_month` 11, income `wages` $39,000/yearly
* Person 2 — `spouse`: `birth_year` 1960, `birth_month` 11, income `sSI` $11,000/yearly
* Current benefits: none
**Calculation**: $39,000 + $11,000 = $50,000 > $43,280, the two-person limit; the `sSI` stream qualifies the household regardless.
**Why this matters**: Confirms the `sSI` income-stream route is checked on every member, not only the head of household.

### Scenario 8: Household above the income limit receiving TANF — Eligible, $7,475
**What we're checking**: the TANF route, which Kansas administers under the name TAF.
**Expected**: Eligible — $7,475
**Household size**: `3`
**Steps**:
* Location: ZIP `66603`, county `Shawnee County`
* Person 1 — `headOfHousehold`: `birth_year` 1992, `birth_month` 7, income `wages` $70,000/yearly
* Person 2 — `child`: `birth_year` 2014, `birth_month` 12, no income
* Person 3 — `child`: `birth_year` 2021, `birth_month` 2, no income
* Current benefits: TANF (`ks_tanf`)
**Calculation**: $70,000 > $54,640, the three-person limit; TANF receipt qualifies the household regardless.
**Why this matters**: Confirms TANF is implemented as a categorical route alongside SSI, not instead of it.

### Scenario 9: Household above the income limit receiving only SNAP — Ineligible
**What we're checking**: SNAP is not a categorical route; other benefits do not bypass the income test.
**Expected**: Ineligible
**Household size**: `2`
**Steps**:
* Location: ZIP `67202`, county `Sedgwick County`
* Person 1 — `headOfHousehold`: `birth_year` 1970, `birth_month` 5, income `wages` $55,000/yearly
* Person 2 — `spouse`: `birth_year` 1972, `birth_month` 1, no income
* Current benefits: SNAP (`ks_snap`)
**Calculation**: $55,000 > $43,280, the two-person limit, and SNAP is not a Kansas categorical route.
**Why this matters**: Prevents SNAP from being mistakenly included in Kansas's categorical-benefit list.

### Scenario 10: Household with no income — Eligible, $7,475
**What we're checking**: zero income is under the limit, not missing data.
**Expected**: Eligible — $7,475
**Household size**: `1`
**Steps**:
* Location: ZIP `66603`, county `Shawnee County`
* Person 1 — `headOfHousehold`: `birth_year` 1968, `birth_month` 7, no income
* Current benefits: none
**Calculation**: $0 ≤ $31,920, the one-person limit.
**Why this matters**: Confirms absent income is treated as $0 rather than as missing data or an error.

### Scenario 11: Household at the limit on wages, with child support and gifts received — Eligible, $7,475
**What we're checking**: the two income types the DOE notice itself excludes are excluded.
**Expected**: Eligible — $7,475
**Household size**: `2`
**Steps**:
* Location: ZIP `66603`, county `Shawnee County`
* Person 1 — `headOfHousehold`: `birth_year` 1985, `birth_month` 3, income `wages` $43,280/yearly
* Person 2 — `spouse`: `birth_year` 1987, `birth_month` 7, income `childSupport` $6,000/yearly, `gifts` $2,000/yearly
* Current benefits: none
**Calculation**: Countable income = $43,280, exactly the two-person limit; the $6,000 and $2,000 are excluded. Summing `["all"]` gives $51,280 and fails.
**Why this matters**: Confirms the DOE policy exclusions for child support received and gifts are applied.

### Scenario 12: Household at the limit with a working 16-year-old — Eligible, $7,475
**What we're checking**: a minor's earned income and unemployment compensation are excluded.
**Expected**: Eligible — $7,475
**Household size**: `3`
**Steps**:
* Location: ZIP `66603`, county `Shawnee County`
* Person 1 — `headOfHousehold`: `birth_year` 1982, `birth_month` 6, income `wages` $54,640/yearly
* Person 2 — `spouse`: `birth_year` 1984, `birth_month` 4, no income
* Person 3 — `child`: `birth_year` 2010, `birth_month` 3, income `wages` $8,000/yearly, `unemployment` $2,000/yearly
* Current benefits: none
**Calculation**: Countable income = $54,640, exactly the three-person limit; the minor's $10,000 is excluded. Counting it gives $64,640 and fails.
**Why this matters**: Confirms wages and unemployment are excluded by member age, not by stream type.

### Scenario 13: Household one dollar over the limit on wages plus alimony — Ineligible
**What we're checking**: alimony is countable — the exclusion list does not over-reach into the rest of its income category.
**Expected**: Ineligible
**Household size**: `2`
**Steps**:
* Location: ZIP `67202`, county `Sedgwick County`
* Person 1 — `headOfHousehold`: `birth_year` 1979, `birth_month` 1, income `wages` $30,000/yearly
* Person 2 — `spouse`: `birth_year` 1981, `birth_month` 8, income `alimony` $13,281/yearly
* Current benefits: none
**Calculation**: $30,000 + $13,281 = $43,281 > $43,280, the two-person limit. Excluding `alimony` leaves $30,000 and wrongly returns Eligible.
**Why this matters**: Confirms `alimony` stays countable and is not excluded alongside the other `support` types.

### Scenario 14: Household above the income limit reporting TANF as a `cashAssistance` income stream — Eligible, $7,475
**What we're checking**: the TANF categorical route is found through the income stream, not only through the current-benefit tile.
**Expected**: Eligible — $7,475
**Household size**: `3`
**Steps**:
* Location: ZIP `66603`, county `Shawnee County`
* Person 1 — `headOfHousehold`: `birth_year` 1990, `birth_month` 5, income `wages` $70,000/yearly, `cashAssistance` $4,800/yearly
* Person 2 — `child`: `birth_year` 2013, `birth_month` 2, no income
* Person 3 — `child`: `birth_year` 2018, `birth_month` 11, no income
* Current benefits: none
**Calculation**: $70,000 + $4,800 = $74,800 > $54,640, the three-person limit; the `cashAssistance` stream qualifies the household regardless.
**Why this matters**: Confirms TANF is detected through the `cashAssistance` stream, not only through the current-benefit tile.

### Scenario 15: Household one dollar over the limit paying child support — Ineligible
**What we're checking**: child support *paid* is not deducted from countable income.
**Expected**: Ineligible
**Household size**: `2`
**Steps**:
* Location: ZIP `67202`, county `Sedgwick County`
* Person 1 — `headOfHousehold`: `birth_year` 1983, `birth_month` 2, income `wages` $43,281/yearly
* Person 2 — `spouse`: `birth_year` 1985, `birth_month` 6, no income
* Expenses: `childSupport` $9,000/yearly
* Current benefits: none
**Calculation**: Countable income = $43,281 > $43,280, the two-person limit. Deducting the $9,000 expense gives $34,281 and wrongly returns Eligible.
**Why this matters**: Confirms paid child support is not deducted from countable income.

### Scenario 16: Eight-person household at the eight-person limit — Eligible, $7,475
**What we're checking**: the largest household the current screener can accept, at its exact limit.
**Expected**: Eligible — $7,475
**Household size**: `8`
**Steps**:
* Location: ZIP `66603`, county `Shawnee County`
* Person 1 — `headOfHousehold`: `birth_year` 1981, `birth_month` 1, income `wages` $111,440/yearly
* Person 2 — `spouse`: `birth_year` 1983, `birth_month` 3, no income
* Person 3 — `child`: `birth_year` 2009, `birth_month` 1, no income
* Person 4 — `child`: `birth_year` 2011, `birth_month` 1, no income
* Person 5 — `child`: `birth_year` 2013, `birth_month` 1, no income
* Person 6 — `child`: `birth_year` 2015, `birth_month` 1, no income
* Person 7 — `child`: `birth_year` 2017, `birth_month` 1, no income
* Person 8 — `child`: `birth_year` 2019, `birth_month` 1, no income
* Current benefits: none
**Calculation**: $111,440 = $111,440, the eight-person limit.
**Why this matters**: Pins the eight-person poverty-table row at the top of the currently enterable range.

---

## Research Sources

| Snapshot | Tier | Title | URL | Retrieved |
|---|---|---|---|---|
| `2026-08-26--42-usc-6862` | 1 | 42 U.S.C. 6862 — Definitions (Weatherization Assistance Program) | https://www.govinfo.gov/content/pkg/USCODE-2023-title42/html/USCODE-2023-title42-chap81-subchapIII-partA-sec6862.htm | 2026-08-26 |
| `2026-08-26--doe-wap-poverty-income-guidelines-index` | 2 | DOE — WAP Poverty Income Guidelines (index) | https://www.energy.gov/cmei/scep/wap/poverty-income-guidelines | 2026-08-26 |
| `2026-08-26--doe-wpn-22-5-v3-hud-categorical` | 2 | DOE WPN 22-5 v3 — Categorical eligibility for HUD means-tested programs | https://www.energy.gov/sites/default/files/2022-09/wpn-22-5_v3.pdf | 2026-08-26 |
| `2026-08-26--doe-wpn-25-3-poverty-income-guidelines` | 2 | DOE WPN 25-3 — 2025 Federal Poverty Guidelines and Definition of Income | https://www.energy.gov/sites/default/files/2025-04/wap-wpn-25-3_041625_0.pdf | 2026-08-26 |
| `2026-08-26--doe-wpn-25-4-usda-categorical` | 2 | DOE WPN 25-4 — Categorical eligibility for select USDA means-tested programs (effective 2024-12-30) | https://www.energy.gov/sites/default/files/2024-12/wap-wpn-25-4.pdf | 2026-08-26 |
| `2026-08-26--doe-wpn-index` | 2 | DOE — Weatherization Program Notices and Memorandums (index) | https://www.energy.gov/cmei/scep/wap/weatherization-program-notices-and-memorandums | 2026-08-26 |
| `2026-08-26--hhs-2026-poverty-guidelines` | 2 | HHS ASPE — 2026 Poverty Guidelines (detailed) | https://aspe.hhs.gov/sites/default/files/documents/b1bfa16b20ae9b89d525bc35de7c1643/detailed-guidelines-2026.pdf | 2026-08-26 |
| `2026-08-26--kcc-utility-weatherization-north-central` | 2 | Kansas Corporation Commission — Utility & Weatherization Related Assistance Programs in North Central Kansas | https://www.kcc.ks.gov/public-affairs-and-consumer-protection/utility-weatherization-related-assistance-programs-in-north-central-kansas | 2026-08-26 |
| `2026-08-26--keesm-13000-lieap` | 2 | KS DCF KEESM 13000 — Low Income Energy Assistance Program (LIEAP) | https://content.dcf.ks.gov/ees/keesm/current/keesm13000.htm | 2026-08-26 |
| `2026-08-26--keesm-13500-k-wap` | 2 | KS DCF KEESM 13500 — The Kansas Weatherization Assistance Program (K-WAP) | https://content.dcf.ks.gov/ees/keesm/current/keesm13500.htm | 2026-08-26 |
| `2026-08-26--khrc-online-weatherization-application` | 2 | Kansas Weatherization Assistance Program — online application form | https://kansasepp.formstack.com/forms/weatherization_application_ps | 2026-08-26 |
| `2026-08-26--khrc-public-hearing-2026-state-plan` | 2 | KHRC — Public Hearing: 2026 Weatherization State Plan | https://kshousingcorp.org/events/public-hearing-2026-weatherization-state-plan/ | 2026-08-26 |
| `2026-08-26--khrc-standardized-wx-application-2026-02-23` | 2 | KHRC Standardized Weatherization Application (2026-02-23) | https://kshousingcorp.org/wp-content/uploads/2024/06/Standardized-Weatherization-Application-2.23.26.pdf | 2026-08-26 |
| `2026-08-26--khrc-weatherization-assistance` | 2 | KHRC — Weatherization Assistance | https://kshousingcorp.org/weatherization-assistance/ | 2026-08-26 |
| `2026-08-26--khrc-weatherization-flyer-2026-02-24` | 2 | KHRC Weatherization flyer (2026-02-24) | https://kshousingcorp.org/wp-content/uploads/2025/08/Weatherization-Flyer-2.24.2026.pdf | 2026-08-26 |
| `2026-08-26--khrc-wx-subrecipient-manual-2025v3` | 2 | KHRC Kansas WAP Subrecipient Procedure Manual 2025 v3 | https://kshousingcorp.org/wp-content/uploads/2025/09/final-2025v3-Wx-Subrecipient-Procedure-Manual.pdf | 2026-08-26 |
| `2026-08-26--ks-weatherization-state-plan-2025-draft` | 2 | Kansas Weatherization State Plan 2025 (Draft) | https://kshousingcorp.org/wp-content/uploads/2025/03/2025-Weatherization-State-Plan-Draft.pdf | 2026-08-26 |
| `2026-08-26--sckedd-kwap-application-2026` | 3 | SCKEDD — Kansas Weatherization Assistance Program application (2026) | https://www.sckedd.org/wp-content/uploads/2026/04/2026-KWAP-Application.pdf | 2026-08-26 |
| `2026-09-02--10-cfr-440-14` | 1 | 10 CFR 440.14 | https://www.govinfo.gov/content/pkg/CFR-2025-title10-vol4/xml/CFR-2025-title10-vol4-sec440-14.xml | 2026-09-02 |
| `2026-09-02--10-cfr-440-16` | 1 | 10 CFR 440.16 | https://www.govinfo.gov/content/pkg/CFR-2025-title10-vol4/xml/CFR-2025-title10-vol4-sec440-16.xml | 2026-09-02 |
| `2026-09-02--10-cfr-440-18` | 1 | 10 CFR 440.18 | https://www.govinfo.gov/content/pkg/CFR-2025-title10-vol4/xml/CFR-2025-title10-vol4-sec440-18.xml | 2026-09-02 |
| `2026-09-02--10-cfr-440-22` | 1 | 10 CFR 440.22 | https://www.govinfo.gov/content/pkg/CFR-2025-title10-vol4/xml/CFR-2025-title10-vol4-sec440-22.xml | 2026-09-02 |
| `2026-09-02--10-cfr-440-3` | 1 | 10 CFR 440.3 — Definitions (Weatherization Assistance Program) | https://www.govinfo.gov/content/pkg/CFR-2025-title10-vol4/xml/CFR-2025-title10-vol4-sec440-3.xml | 2026-09-02 |
