# Commodity Supplemental Food Program (KS) — Program Spec

- **Program key**: `ks_csfp` (proposed — `programs/programs/cross_white_label/csfp/ks.py`, class `KsCsfp`)
- **Base federal program**: Commodity Supplemental Food Program (U.S. Department of Agriculture), 7 CFR part 247
- **White label**: KS
- **Engine**: PolicyEngine
- **Added to MFB**: not yet added
- **Spec last updated**: 2026-09-28
- **Sources verified as of**: 2026-09-28 (Kansas income table effective 2026-03-01; DCF overview, FAQs, agency pages and both config links re-fetched 2026-09-27/28)

## Covered Eligibility Criteria

Criterion 1 must hold, and criterion 2 **or** criterion 3 must hold — categorical certification
displaces the income test rather than adding to it — and criterion 4 must hold as well. Whether an
applicant's local agency serves them is a separate determination the screener cannot make; it is
Missing Eligibility Criteria 1.

1. **The individual is at least 60 years of age.**
   - Evaluation scope: `member`
   - Captured via: `age` (HouseholdMember, PositiveIntegerField) read through accessor `HouseholdMember.calc_age()`, which returns `age` when `birth_year_month` is absent and otherwise derives the age from `birth_year_month` (HouseholdMember, DateField) against `Screen.get_reference_date()`
   - Implementation note: the floor is inclusive — a person aged exactly 60 qualifies. The month is inclusive: a person whose birth month equals the month of the screen's reference date has reached that age. No pathway for women, infants or children remains in the current rule — 7 CFR 247.9 conditions eligibility on age and income alone.
   - Source: 7 CFR 247.9(a) — "To be eligible for CSFP, individuals must be at least 60 years of age and meet the income eligibility requirements outlined in paragraph (b) of this section." — [snapshot `2026-08-27--7-cfr-247-9`](../../../sources/ks/ks_csfp/2026-08-27--7-cfr-247-9/content.md), accessed 2026-08-27
   - Source: Kansas CSFP State Plan, effective 2025-04-11, "Income Eligibility Standards and Options" — "Adults 60 years of age or older are eligible for CSFP if their household income is at or below" — [snapshot `2026-08-27--ks-dcf-csfp-state-plan`](../../../sources/ks/ks_csfp/2026-08-27--ks-dcf-csfp-state-plan/content.md), accessed 2026-08-27
   - Source: Kansas DCF, CSFP overview — "CSFP serves a food package to persons 60 years of age or older with income less than 150% of the Federal Poverty Level." — [snapshot `2026-08-27--ks-dcf-csfp-overview`](../../../sources/ks/ks_csfp/2026-08-27--ks-dcf-csfp-overview/content.md), accessed 2026-08-27

2. **The household's income is at or below 150 percent of the federal poverty guidelines for its size.**
   - Evaluation scope: `household`
   - Captured via: income streams (`IncomeStream.amount` and `frequency`, one row per source per HouseholdMember), aggregated by `Screen.calc_gross_income` over the household.
     - Carrier: `CsfpCountableIncomeDependency`, an `SpmUnit` dependency in `CommoditySupplementalFoodProgram.pe_inputs` — the base list `KsCsfp` extends, since criterion 4 adds two Kansas entries.
     - What it sends: `calc_gross_income("yearly", ["all"])` as `school_meal_countable_income`. `["all"]` counts every income type the screener collects, with no exclusions.
     - What PolicyEngine does with it: forms `school_meal_fpg_ratio` against `spm_unit_fpg` and compares it to `gov.usda.csfp.fpg_limit` (1.5 from 2025-01-01).
     - Not transmitted: `household_size` (Screen, IntegerField). No poverty table is indexed MFB-side — the calculator performs no eligibility arithmetic of its own.
     - Unit measured: the single `spm_unit` MFB builds from every household member (`programs/framework/pe_dependencies/payload.py`, `_household_shape`).
   - Implementation note:
     - The comparison is inclusive. Every source phrases the test as "at or below", and the figure Kansas publishes for a one-person household *is* the 150 percent value and is published as qualifying.
     - Income counted is gross income before deductions, so every income type the screener collects counts unless a source excludes it. 7 CFR 247.9(d)(2) lets a state exclude a military basic allowance for housing and the value of in-kind benefits; 7 CFR 247.9(d)(3) requires excluding sources excluded by statute — an expressly non-exhaustive list, of which the Kansas screener collects none of the enumerated entries.
     - Gifts and contributions count. Kansas's "Income Eligibility Standards and Options" records an election under 247.9(b)(1) and none under (d)(2), and its participant application names contributions from relatives as reportable income alongside wages and Social Security. The screener's `gifts` field ("Gifts or Contributions (Received)") does not separate cash from in-kind, and no exclusion is elected, so the whole stream counts.
     - Which income the local agency measures is part of the determination. 7 CFR 247.9(d)(4) lets Kansas authorize a local agency to weigh the household's average income over the previous 12 months against current income and use whichever better reflects the household, and Kansas does so — its participant application asks for both. The screener holds only current income streams and annualizes them, so it applies the current-income reading; an applicant just over the limit on current income may still be certified on the 12-month average.
     - The unit measured is the CSFP household defined at 7 CFR 250.2 — those who customarily purchase and prepare meals together — not, in general, everyone on the screen. The screener collects no purchase-and-prepare field, so it measures the whole screen: Missing Eligibility Criteria 2.
     - Kansas fixes no poverty table of its own. It adopts whichever FNS memorandum is current, so the edition is a configuration value (the program row's `year`) rather than a constant in the rule.
   - Engine note: PolicyEngine's Kansas branch also carries `ks_dcf_csfp_categorically_eligible`, which adds `[ssi, receives_ssi, snap, receives_snap, fdpir, msp]` — four of them amounts PolicyEngine computes rather than reported receipt. Those computed amounts are only meaningful when the request carries the household's real income variables, so `KsCsfp` declares them itself rather than relying on sibling programs sharing the payload: `receipt_contract` holds `ssi` and `snap` to reported receipt, and `Msp.pe_inputs` supplies the income, asset and Medicare inputs `msp` is computed from. Measured 2026-09-28 at policyengine-us 2.5.0 and 2.9.0: sent alone with only age, countable income, state and county, scenario 3's household computes $0-income SSI, SNAP and MSP and returns $651. Where CSFP's all-types total differs from NSLP's narrower school-meals total for the same field, the payload splitter serves CSFP its own request; that pairing is an expected conflict and is logged rather than raised. Verified 2026-09-25 on `benefits-api` `da92994e` at policyengine-us 2.9.0: all 14 scenarios return this spec's expected value.
   - Declaring `ReceivesSnapDependency` and `ReceivesSsiDependency` (via `receipt_contract`) is required, not optional: it makes the SNAP and SSI routes rest on reported certification rather than on PolicyEngine's computed benefit.
   - Source: 7 CFR 247.9(b) — "The State agency must use a household income limit at or below 150 percent of the U.S. Federal Poverty Guidelines published annually by the U.S. Department of Health and Human Services (HHS)." — [snapshot `2026-08-27--7-cfr-247-9`](../../../sources/ks/ks_csfp/2026-08-27--7-cfr-247-9/content.md), accessed 2026-08-27
   - Source: 7 CFR 247.9(d)(1), defining income — "Income means gross income before deductions for such items as income taxes, employees' social security taxes, insurance premiums, and bonds." — [snapshot `2026-08-27--7-cfr-247-9`](../../../sources/ks/ks_csfp/2026-08-27--7-cfr-247-9/content.md), accessed 2026-08-27
   - Source: Kansas CSFP State Plan, "Income Eligibility Standards and Options", restating the same definition — "Household income refers to gross income before deductions for items such as income taxes," — [snapshot `2026-08-27--ks-dcf-csfp-state-plan`](../../../sources/ks/ks_csfp/2026-08-27--ks-dcf-csfp-state-plan/content.md), accessed 2026-08-27
   - Source: 7 CFR 247.9(d)(4), on which income the local agency may measure — "The State agency may authorize local agencies to consider the household's average income during the previous 12 months and current household income to determine which more accurately reflects the household's status." — [snapshot `2026-08-27--7-cfr-247-9`](../../../sources/ks/ks_csfp/2026-08-27--7-cfr-247-9/content.md), accessed 2026-08-27
   - Source: Kansas DCF CSFP participant application, collecting both figures — "income during the previous 12 months." — [snapshot `2026-08-27--ks-dcf-csfp-participant-application`](../../../sources/ks/ks_csfp/2026-08-27--ks-dcf-csfp-participant-application/content.md), accessed 2026-08-27
   - Source: Kansas DCF CSFP participant application, naming contributions among countable income — "contributions from relatives, etc." — listed under *Other Income* beside Gross Salary/Wages, Social Security, Public Assistance, Child Support, Pensions/Retirement, Self-Employment and Unemployment — [snapshot `2026-08-27--ks-dcf-csfp-participant-application`](../../../sources/ks/ks_csfp/2026-08-27--ks-dcf-csfp-participant-application/content.md), accessed 2026-08-27
   - Source: 7 CFR 247.9(c), on which edition applies — "Each year, FNS will notify State agencies, by memorandum, of adjusted income guidelines by household size at 150 percent and 100 percent of the U.S. Federal Poverty Guidelines published annually by HHS." — [snapshot `2026-08-27--7-cfr-247-9`](../../../sources/ks/ks_csfp/2026-08-27--7-cfr-247-9/content.md), accessed 2026-08-27
   - Source: Kansas CSFP State Plan, "Income Eligibility Standards and Options", confirming Kansas keeps no table of its own — "Kansas updates eligibility guidelines immediately upon receipt of notification from Food and Nutrition Service (FNS)." — [snapshot `2026-08-27--ks-dcf-csfp-state-plan`](../../../sources/ks/ks_csfp/2026-08-27--ks-dcf-csfp-state-plan/content.md), accessed 2026-08-27
   - Source: Kansas DCF, CSFP income guidelines, "Income guidelines are effective March 1, 2026", giving the operative annual limits for household sizes 1 through 8 and the increment — "23,940", "32,460", "40,980", "49,500", "58,020", "66,540", "75,060", "83,580", "8,520" — [snapshot `2026-08-27--ks-dcf-csfp-income-guidelines`](../../../sources/ks/ks_csfp/2026-08-27--ks-dcf-csfp-income-guidelines/content.md), accessed 2026-08-27
   - Source: HHS ASPE, 2026 poverty guidelines, identifying that table's edition — the one-person figure "15,960" multiplied by 1.5 gives the $23,940 Kansas publishes, and the "5,680" per-person increment gives Kansas's $8,520 — [snapshot `2026-08-27--hhs-2026-poverty-guidelines`](../../../sources/ks/ks_csfp/2026-08-27--hhs-2026-poverty-guidelines/content.md), accessed 2026-08-27

3. **The applicant is certified as fully eligible for SNAP, FDPIR, SSI, the Low Income Subsidy Program, or a Medicare Savings Program.**
   - Evaluation scope: `member`
   - Captured via: accessors `Screen.has_base_benefit("snap")`, `Screen.has_base_benefit("ssi")` and `Screen.has_base_benefit("medicare_savings")`, backed by `CurrentBenefit` (screen ↔ program join) and resolved through each joined program row's `base_program`; SSI additionally reaches the screener as an income stream of type `sSI`
   - Implementation note:
     - This criterion replaces criterion 2 rather than supplementing it. An applicant certified in one of these programs is not measured against the income limit at all.
     - The rule is about the applicant, not the household. 7 CFR 247.9(b)(1) reaches an applicant who documents that *they* are certified, and the State Plan grants it to *participants in* the five programs.
     - The screener's accessors are screen-level, so the natural mapping propagates one member's certification to the whole household — broader than the rule. For the three individually-held routes (SSI, the Low Income Subsidy Program, a Medicare Savings Program) it would make a high-income 68-year-old categorically eligible because an adult child receives SSI. SNAP is held household-wide and so is unaffected. That broadening is **not** accepted: an implementation may propagate a certification household-wide only if it preserves which applicant is certified, and otherwise must evaluate the three individually-held routes per member.
     - The engine is PolicyEngine, not MFB. The calculator is a pass-through reading PolicyEngine's own eligibility variable, so MFB must **not** layer a categorical branch on top of it. PolicyEngine evaluates the routes via `ks_dcf_csfp_categorically_eligible`, present from 2.4.2 and verified at 2.9.0.
     - Kansas elected five routes and no sixth. 7 CFR 247.9(b)(2) offers a sixth — participation in State-administered programs that themselves verify income — and the State Plan lists only the five federal programs, so Kansas has not elected it. Temporary Assistance for Needy Families is not one of the five.
     - The screener observes three of the five. It collects no field for FDPIR or the Low Income Subsidy Program, so an applicant qualifying *only* through one of those is measured against criterion 2 instead. That is a limit on MFB's coverage of the rule, not on the rule.
     - Two of the three observable routes can carry reported certification; the third cannot.
       - `gov.states.ks.dcf.csfp.categorical_eligibility` adds `[ssi, receives_ssi, snap, receives_snap, fdpir, msp]`. SNAP and SSI have reported-receipt inputs (`ReceivesSnapDependency`, `ReceivesSsiDependency`), so a screener-reported certification reaches PolicyEngine for those two.
       - **Medicare Savings cannot.** `msp` is an amount PolicyEngine computes, and no `receives_msp` input exists, so the route rests on a computed entitlement standing in for a certification. It diverges both ways: an applicant computed-eligible but never certified gets the route, and an applicant certified whose computed `msp` is $0 does not.
       - Measured 2026-09-25 at policyengine-us 2.9.0: a 68-year-old with $15,600/yr in a household over the income limit is categorically eligible on a computed `msp` of $202.90/month, with no certification of any kind on the screen.
       - Accepted rather than worked around. Direction is predominantly over-inclusion and it is confined to seniors whose own income is already below the Medicare Savings tiers. Closing it needs a `receives_msp` input from PolicyEngine. FDPIR has the same shape, but the screener collects no FDPIR field, so it never arises.
     - All three observable routes depend on `base_program`. The accessors match on `Program.base_program` rather than the Kansas program names, which makes them portable; the field is nullable, and if unset the route returns false silently rather than erroring. It is set on all three Kansas rows in the seed configs `benefits-api` ships (`ks_snap` → `snap`, `ks_ssi` → `ssi`, `ks_msp` → `medicare_savings`). A later CMS edit could clear one without changing those files.
   - Source: Kansas CSFP State Plan, "Income Eligibility Standards and Options" — "Kansas adheres to the income eligibility standards outlined in 7 CFR 247.9 and permits" categorical eligibility for "Supplemental Nutrition Assistance Program (SNAP),", "Food Distribution Program on Indian Reservations (FDPIR),", "Supplemental Security Income (SSI),", "Low Income Subsidy Program, or" and "Medicare Savings Programs" — [snapshot `2026-08-27--ks-dcf-csfp-state-plan`](../../../sources/ks/ks_csfp/2026-08-27--ks-dcf-csfp-state-plan/content.md), accessed 2026-08-27
   - Source: 7 CFR 247.9(b)(1) — "The State agency may accept as income-eligible for CSFP benefits any applicant that documents that they are certified as fully eligible for the following Federal programs: the Supplemental Nutrition Assistance Program, the Food Distribution Program on Indian Reservations, Supplemental Security Income (SSI), the Low Income Subsidy Program, or the Medicare Savings Programs." — [snapshot `2026-08-27--7-cfr-247-9`](../../../sources/ks/ks_csfp/2026-08-27--7-cfr-247-9/content.md), accessed 2026-08-27
   - Source: 7 CFR 247.9(b)(3), on the displacement — "Applicants who are adjunctively income eligible, as set forth in paragraphs (b)(1) and (2) of this section, shall not be subject to the income limits established under paragraph (b) of this section." — [snapshot `2026-08-27--7-cfr-247-9`](../../../sources/ks/ks_csfp/2026-08-27--7-cfr-247-9/content.md), accessed 2026-08-27

4. **The applicant is in Kansas.**
   - Evaluation scope: `config`
   - Captured via: `KsStateCodeDependency`, declared in `KsCsfp.pe_inputs`. White-label routing decides which programs run for a screen; it does **not** tell PolicyEngine where the household is. `commodity_supplemental_food_program_eligible` branches on `state_code`, and `state_code` reaches PolicyEngine only from a `StateCode` dependency subclass declared in some program's `pe_inputs` (`programs/framework/pe_dependencies/household.py`, class `StateCode`) — there is no other writer of that field in `programs/` or `integrations/`. This criterion is therefore not `assumed-met` in the calculator: it is an input the calculator has to send.
   - Implementation note:
     - This is not a county restriction. Kansas imposes no durational or fixed residency requirement, and which local agency serves an applicant is Missing Eligibility Criteria 1 rather than a narrowing of this criterion.
     - `KsCsfp` must declare `KsCountyDependency` alongside `KsStateCodeDependency`, following `MaCsfp` — the only sibling whose PolicyEngine branch carries a county gate, and whose test asserts both inputs (`programs/programs/cross_white_label/csfp/tests/test_ma.py`). Both classes exist and are in use by `KsAca` (`programs/programs/cross_white_label/aca/ks.py`).
     - Declaring them is load-bearing, not defensive. `build_pe_input` assembles **one shared household per PolicyEngine request** (`programs/framework/pe_dependencies/payload.py`), so `state_code` and `county_str` can arrive from another Kansas program sharing the request even when `KsCsfp` declares neither — making this program's answer depend on which other programs ran and how the payload was split.
     - The failure mode is silent and worse than the rule it expresses. With `state_code` set to KS and no county sent, PolicyEngine defaults the household to `ALLEN_COUNTY_KS`, which is not covered, so the program returns $0 across **all 105** Kansas counties rather than only the 45 without a distribution site.
     - `KsCountyDependency` also settles the skip semantics. It declares `county` (`CountyDependency.dependencies`), so `can_calc()` skips the program when county is unknown instead of returning an affirmative ineligible result.
   - Source: Kansas CSFP State Plan, "Authority" — "The Commodity Supplemental Food Program (CSFP) is administered by the Kansas Department" for Children and Families — [snapshot `2026-08-27--ks-dcf-csfp-state-plan`](../../../sources/ks/ks_csfp/2026-08-27--ks-dcf-csfp-state-plan/content.md), accessed 2026-08-27
   - Source: 7 CFR 247.5(b)(6), on residency being a state-agency option rather than a federal requirement — "Establishing nutritional risk criteria and a residency requirement for participants, if such criteria are to be used;" — [snapshot `2026-08-27--7-cfr-247-5`](../../../sources/ks/ks_csfp/2026-08-27--7-cfr-247-5/content.md), accessed 2026-08-27
   - Source: Kansas CSFP State Plan, "Caseload and Participant Service Plans", on the scope Kansas actually operates — "Local agencies have designated service areas and may serve eligible individuals within those" areas — [snapshot `2026-08-27--ks-dcf-csfp-state-plan`](../../../sources/ks/ks_csfp/2026-08-27--ks-dcf-csfp-state-plan/content.md), accessed 2026-08-27

## Missing Eligibility Criteria (Data Gaps)

1. **Kansas local agencies have designated service areas and may, but need not, serve residents outside them — so whether a given applicant is served is a local-agency determination.**
   - Why: whether an applicant is served depends on a local agency's acceptance decision, which the screener cannot observe. `county` (Screen, CharField) and `zipcode` (Screen, CharField) are partial evidence of the ordinary route only — they can show that an applicant lives where distribution sites already operate, but they cannot establish that an applicant living elsewhere will be refused, because Kansas permits local agencies to serve people outside their normal service area.
   - Handling: ⚠️ **Data Gap — restrictive, by accepted approximation, and unmitigated.** PolicyEngine denies a Kansas applicant whose county holds no distribution site, and MFB takes PolicyEngine's answer. **This gap cannot be mitigated by the program description** (corrected 2026-09-28): the affected applicant is scored ineligible, and `filterPrograms.ts::isProgramBasicallyVisible` requires `program.eligible && programValue(program) > 0`, so the card never renders and no sentence inside it is ever read. `ProgramPage` resolves against the same filtered array and redirects on a miss. The service-area sentence was accordingly removed from the description rather than left as a mitigation that reaches nobody. Missouri's sibling spec keeps its equivalent sentence because `commodity_supplemental_food_program_eligible` computes `county_eligible = select([in_ks, in_ma, in_il], ..., default=True)` — Missouri is absent from that select, so it shows the card statewide and its local agency may still refuse. Same federal rule, opposite reachability.
   - Approximations: MFB reports $0 for an otherwise-eligible senior in any of the 45 Kansas counties without a distribution site, though the evidenced rule does not permit denial on county alone. `commodity_supplemental_food_program_eligible` ANDs `ks_dcf_csfp_county_eligible` into its result, so the county list is an absolute gate with no weaker expression available, and this program reads PolicyEngine's eligibility variable directly. PolicyEngine declined to relax it, citing Kansas DCF's FAQ ("You must reside in one of the covered counties in order to qualify") over the approved State Plan and asking for DCF clarification first. Accepted as a deliberate deviation rather than worked around: overriding PolicyEngine's eligibility MFB-side would fork this program's answer from the engine the spec names and leave the divergence untestable. Direction is **under-inclusion** — false negatives only. Revisit if DCF confirms the permissive reading in writing.
   - Source: Kansas CSFP State Plan, "Caseload and Participant Service Plans" — "residents outside their normal service area, provided that coordination occurs among relevant" local agencies — [snapshot `2026-08-27--ks-dcf-csfp-state-plan`](../../../sources/ks/ks_csfp/2026-08-27--ks-dcf-csfp-state-plan/content.md), accessed 2026-08-27
   - Source: 7 CFR 247.9(e)(2), making any service-area requirement a state option and forbidding a durational form — "The State agency may require that an individual reside within the service area of the local agency at the time of application for CSFP benefits. However, the State agency may not require that an individual reside within the area for any fixed period of time." — [snapshot `2026-08-27--7-cfr-247-9`](../../../sources/ks/ks_csfp/2026-08-27--7-cfr-247-9/content.md), accessed 2026-08-27
   - Source: Kansas DCF, CSFP FAQs, stating the ordinary expectation more flatly than the State Plan does — "You must reside in one of the covered counties in order to qualify." — [snapshot `2026-08-27--ks-dcf-csfp-faqs`](../../../sources/ks/ks_csfp/2026-08-27--ks-dcf-csfp-faqs/content.md), accessed 2026-08-27

2. **The unit whose income is measured is the CSFP household — the people who customarily purchase food and prepare meals together — which is not always everyone on the screen.**
   - Why: 7 CFR 250.2 defines the CSFP household by purchase-and-prepare, so an applicant living with others but buying and cooking separately is their own household and only their own income counts. Nothing on `Screen` or `HouseholdMember` distinguishes a shared food budget from a separate one, so MFB cannot tell which arrangement applies and measures everyone on the screen.
   - Handling: ⚠️ **Data Gap — direction depends on the co-resident's income; both directions occur.** The pooled measurement is the default because it is the only one the screener supports, and the separate-food-budget case is surfaced in the program description. **Corrected 2026-09-28 — the previous text read "the pooled reading is the *restrictive* one, so this gap produces false negatives only", which is false.** Pooling raises the measured income *and* the threshold, which rises **$8,520 per additional person** at 150% FPG in 2026, so MFB is **permissive** whenever a co-resident's own income falls below that increment. Worked case: a senior on $25,000 living with a co-resident on $0 is pooled to $25,000 against the two-person limit $32,460 and scored **eligible**, while the true 7 CFR 250.2 household is the senior alone — $25,000 against $23,940, **$1,060 over**. The card is shown and the local agency then denies on the smaller unit. Above the $8,520 increment the gap is restrictive as originally described. The description's sentence therefore earns its place for the *permissive* case, not for the higher-earning-relative case the previous text cited, which cannot reach the user at all.
   - Source: 7 CFR 250.2, defining the household — "means any of the following individuals or groups of individuals, exclusive of boarders or residents of an institution" — [snapshot `2026-09-10--7-cfr-250-2`](../../../sources/ks/ks_csfp/2026-09-10--7-cfr-250-2/content.md), accessed 2026-09-10
   - Source: 7 CFR 250.2, the separate-purchase branch — "(2) An individual living with others, but customarily purchasing food and preparing meals for home consumption separate and apart from the others;" — [snapshot `2026-09-10--7-cfr-250-2`](../../../sources/ks/ks_csfp/2026-09-10--7-cfr-250-2/content.md), accessed 2026-09-10
   - Source: 7 CFR 250.2, the common-purchase branch — "A group of individuals living together who customarily purchase and prepare meals in common for home consumption" — [snapshot `2026-09-10--7-cfr-250-2`](../../../sources/ks/ks_csfp/2026-09-10--7-cfr-250-2/content.md), accessed 2026-09-10
   - Source: 7 CFR 250.2, confirming the definition reaches CSFP — "means CSFP, FDPIR, and TEFAP." (defining *Household programs*) — [snapshot `2026-09-10--7-cfr-250-2`](../../../sources/ks/ks_csfp/2026-09-10--7-cfr-250-2/content.md), accessed 2026-09-10
   - Source: 7 CFR 247.1, confirming part 247 states no competing definition — its definitions list defines neither *household* nor *income*, and incorporates part 250 by reference: "means the Department's regulations pertaining to the donation of foods for use in USDA food distribution programs." (defining *7 CFR part 250*). 247.9 is the only section of part 247 stating an eligibility rule, so the 250.2 definition governs unopposed — [snapshot `2026-09-11--7-cfr-247-1`](../../../sources/ks/ks_csfp/2026-09-11--7-cfr-247-1/content.md), accessed 2026-09-11

## Priority Criteria

None. Kansas operates no prioritization tiers within CSFP: neither the State Plan nor 7 CFR part
247 establishes target populations served first or more deeply, across all 37 sections of part 247
and all 19 sections of the State Plan. Two nearby rules are not prioritization — the
nutritional-risk option at 7 CFR 247.9(e)(1) is an *eligibility* option Kansas declined, and the
order people come off a waiting list under 7 CFR 247.11(b) is availability sequencing rather than
prioritization within the program.

- Source: 7 CFR 247.9(e)(1), establishing the option Kansas declined — "(1) The State agency may require that an individual be at nutritional risk, as determined by a physician or by local agency staff." — [snapshot `2026-08-27--7-cfr-247-9`](../../../sources/ks/ks_csfp/2026-08-27--7-cfr-247-9/content.md), accessed 2026-08-27
- Source: Kansas CSFP State Plan, "Nutritional Risk Criteria" — "Kansas does not establish additional nutritional risk criteria for CSFP eligibility beyond federal" income requirements — [snapshot `2026-08-27--ks-dcf-csfp-state-plan`](../../../sources/ks/ks_csfp/2026-08-27--ks-dcf-csfp-state-plan/content.md), accessed 2026-08-27
- Source: 7 CFR 247.11(b), showing the waiting-list order is availability sequencing and not prioritization within the program — "The local agency must certify eligible individuals from the waiting list consistent with civil rights requirements at § 247.37. For example, a local agency may certify eligible individuals from the waiting list based on the date the application was received on a first-come, first-served basis." — [snapshot `2026-08-27--7-cfr-247-11`](../../../sources/ks/ks_csfp/2026-08-27--7-cfr-247-11/content.md), accessed 2026-08-27

## Related Programs

7 CFR 247.14(a) names four programs the local agency must give applicants written information on and
refer them to, and the Kansas State Plan adopts the same four. None bears on this program's
eligibility or value. Three of them are also the observable categorical routes in criterion 3, which
is why the tie-back is not "none needed" for those: an applicant told to apply for SNAP, SSI or a
Medicare Savings Program may thereby become categorically eligible for CSFP itself.

- **Supplemental Security Income (Title XVI)** — own eligibility: federal SSA rules. MFB screens it in
  Kansas. Also a criterion 3 categorical route.
  - Program description tie-back: already present — the description names SSI as a route.
  - Source: 7 CFR 247.14(a)(1) — "Supplemental security income benefits provided under Title XVI of the Social Security Act" — [snapshot `2026-08-27--7-cfr-247-14`](../../../sources/ks/ks_csfp/2026-08-27--7-cfr-247-14/content.md), accessed 2026-08-27
  - Source: Kansas CSFP State Plan, "Other Public Assistance Programs" — "Supplemental Security Income benefits under Title XVI of the Social Security Act;" — [snapshot `2026-08-27--ks-dcf-csfp-state-plan`](../../../sources/ks/ks_csfp/2026-08-27--ks-dcf-csfp-state-plan/content.md), accessed 2026-08-27
- **Medicaid (Title XIX), including the Qualified Medicare Beneficiary group** — own eligibility: set by
  Kansas. MFB screens both in Kansas. QMB is one tier of the Medicare Savings Programs, so this overlaps
  criterion 3's fifth route; Medicaid on its own is **not** a categorical route, which is the confusion
  scenario 10 exists to pin.
  - Program description tie-back: already present — the description names Medicare Savings as a route.
  - Source: 7 CFR 247.14(a)(2) — "including medical assistance provided to a qualified Medicare beneficiary" — [snapshot `2026-08-27--7-cfr-247-14`](../../../sources/ks/ks_csfp/2026-08-27--7-cfr-247-14/content.md), accessed 2026-08-27
  - Source: Kansas CSFP State Plan, "Other Public Assistance Programs" — "Medical assistance provided under Title XIX of the Social Security Act, including medical assistance provided to a qualified Medicare beneficiary;" — [snapshot `2026-08-27--ks-dcf-csfp-state-plan`](../../../sources/ks/ks_csfp/2026-08-27--ks-dcf-csfp-state-plan/content.md), accessed 2026-08-27
- **Supplemental Nutrition Assistance Program** — own eligibility: set by Kansas under federal rules.
  MFB screens it in Kansas. Also a criterion 3 categorical route.
  - Program description tie-back: already present — the description names SNAP as a route.
  - Source: 7 CFR 247.14(a)(3) — "The Supplemental Nutrition Assistance Program" — [snapshot `2026-08-27--7-cfr-247-14`](../../../sources/ks/ks_csfp/2026-08-27--7-cfr-247-14/content.md), accessed 2026-08-27
  - Source: Kansas CSFP State Plan, "Other Public Assistance Programs" — "The Supplemental Nutrition Assistance Program; and" — [snapshot `2026-08-27--ks-dcf-csfp-state-plan`](../../../sources/ks/ks_csfp/2026-08-27--ks-dcf-csfp-state-plan/content.md), accessed 2026-08-27
- **Senior Farmers' Market Nutrition Program** — a separate USDA program that CSFP local agencies must tell applicants about and refer them to. Own eligibility: set by the operating state agency, not by CSFP. Not part of this program's eligibility or value.
  - Program description tie-back: none needed.
  - Source: 7 CFR 247.14(a) — "The local agency must provide applicants with written information on the following programs, and make referrals, as appropriate:" including the "Senior Farmers' Market Nutrition Program" — [snapshot `2026-08-27--7-cfr-247-14`](../../../sources/ks/ks_csfp/2026-08-27--7-cfr-247-14/content.md), accessed 2026-08-27

## Benefit Value

- Value: $651/year per qualifying individual (= the national CSFP per-slot figure for 2026: program cost $460,000,000 ÷ 707,000 funded slots = $650.64, rounded to $651), which is `gov.usda.csfp.amount` exactly. Both inputs are stated in the FNS caseload memorandum, captured 2026-09-11.
- Source: FNS, *CSFP Caseload Assignments for the 2026 Caseload Cycle and Administrative Grants*, on the appropriation — "which provides $460 million for the CSFP for fiscal year (FY) 2026" — and on the denominator — "FNS is issuing a final national caseload allocation of 707,000 slots for the 2026 caseload cycle (January 1, 2026 to December 31, 2026)" — [snapshot `2026-09-11--fns-csfp-caseload-2026-memo`](../../../sources/ks/ks_csfp/2026-09-11--fns-csfp-caseload-2026-memo/content.md), accessed 2026-09-11
- Source: the same memorandum, establishing that the denominator counts authorized slots and not observed participation — "because some States did not fully use their 2025 assigned caseload, total calculated national base caseload is 700,155 slots, leaving 6,845 additional caseload slots available for allocation" — [snapshot `2026-09-11--fns-csfp-caseload-2026-memo`](../../../sources/ks/ks_csfp/2026-09-11--fns-csfp-caseload-2026-memo/content.md), accessed 2026-09-11
- `value_format`: **`null`** (the default) — corrected 2026-09-28. The seed config previously carried `estimated_annual`; it was changed because `FormattedValue.tsx` pairs that token with the label "Average Annual Savings", which misdescribes an in-kind food box, while the default divides by 12 and labels the figure "Estimated Annual Value". Kansas was also the only CSFP setting the token — `il`, `ma` and `tx` omit it and `wa` sets `null` — so the same $651 rendered $651/year here and $54/month everywhere else. The benefit is recurring, not one-time — one package of USDA Foods every month for as long as the participant remains certified.
- Variation axes: number of qualifying individuals in the household — not household size, county, or income bracket.
- Source: 7 CFR 247.10(a), on what is actually received — "The local agency must distribute a package of USDA Foods to participants each month, or a two-month supply of USDA Foods to participants every other month, in accordance with the food package guide rates established by FNS." — [snapshot `2026-08-27--7-cfr-247-10`](../../../sources/ks/ks_csfp/2026-08-27--7-cfr-247-10/content.md), accessed 2026-08-27
- Source: Kansas DCF, CSFP overview, on the contents of that package — "CSFP distributes a monthly food package containing 10 food groups including: cheese, shelf stable milk, nonfat dry milk (every other month), peanut butter or dry beans, cereal, meat, vegetables, fruits, juice, and instant potatoes, rice or pasta." — [snapshot `2026-08-27--ks-dcf-csfp-overview`](../../../sources/ks/ks_csfp/2026-08-27--ks-dcf-csfp-overview/content.md), accessed 2026-08-27
- Source: 7 CFR 247.14(b), on how the value interacts with other programs — "The value of benefits received in CSFP may not be considered as income or resources of participants or their families for any purpose under Federal, State, or local laws, including laws relating to taxation and public assistance programs." — [snapshot `2026-08-27--7-cfr-247-14`](../../../sources/ks/ks_csfp/2026-08-27--7-cfr-247-14/content.md), accessed 2026-08-27
- Justification: CSFP pays no cash — its benefit is a monthly box of USDA Foods, so any dollar figure estimates what that box is worth. The figure adopted is the national CSFP appropriation divided by the caseload slots it funds, the basis PolicyEngine's `gov.usda.csfp.amount` uses, so MFB carries the same derivation rather than a competing estimate. Read it as cost per participant rather than the retail value of the groceries: it averages across all states and includes the cost of delivering the box. Expect it to move each year with the appropriation and the caseload.
  - What the number is and is not: administrative funding is $106.03 per slot per year ($74,963,202 nationally), so roughly $545 of the $651 is food and the balance is delivery. MFB carries the undecomposed $651 because that is what PolicyEngine's parameter carries; the split is recorded so nobody has to re-derive it.
  - The denominator is authorized slots, not people served, and slots run unfilled — cost per *actual* participant is $460,000,000 ÷ 700,953 = $656 against $651 per slot, a difference too small to change the displayed value.

## Test Scenarios

**Coverage map**

| Rule / variation axis | Scenarios |
|---|---|
| Age ≥ 60 (member scope) | 1 (boundary, turns 60 in the reference month), 4 (boundary, turns 60 the month after), 7 (only the 61-year-old qualifies) |
| Age derived from `birth_year_month`, month-inclusive, against a pinned reference date | 1, 4 |
| Income ≤ 150% FPL, one-person limit | 1 (under), 2 (at limit), 3 (just over → fail) |
| Income limit rises with household size (+$8,520) | 5 (at the two-person limit), 6 (just over → fail), 7 |
| Income counted is gross, not net of expenses | 3 |
| Income counted is gross across types, not a selected subset | 12 (unemployment), 14 (gifts and contributions) |
| Categorical certification displaces the income test | 8 (SNAP), 9 (SSI), 10 (Medicare Savings, on PolicyEngine's computed entitlement), 11 (TANF is not a route → fail) |
| Certification is the applicant's own, not propagated household-wide | 15 |
| Value is per qualifying individual | 5 (two qualify → $1,302), 7, 9, 10 (one of two qualifies → $651) |
| County gate denies (accepted approximation, not the evidenced rule) | 13 |
| Income is measured over one pooled CSFP household | 9, 10 (assumption stated; the separate-purchase branch is unscreenable) |
| Kansas (criterion 4) | all — every scenario is a Kansas screen |

**Known scenario gaps.** Four things are deliberately unscreened:

1. Whether an applicant's local agency serves them (Missing Eligibility Criteria 1) cannot be
   screened. Scenario 13 asserts MFB's accepted approximation instead — that PolicyEngine's county
   gate denies. The evidenced rule, that county alone does not disqualify, is not what MFB computes
   and so is not asserted anywhere.
2. Two of the five categorical routes, FDPIR and the Low Income Subsidy Program, have no screener
   field. Of the three the screener does observe, only SNAP and SSI can reach PolicyEngine as a
   *reported* certification — scenarios 8 and 9. Scenario 10 exercises PolicyEngine's computed
   entitlement instead; see criterion 3.
3. Every fixture is measured on current income. Whether a local agency would instead certify on the
   12-month average, under the option in criterion 2, is not screenable — the screener holds no
   income history.
4. Every fixture pools the whole screen into one CSFP household, so no fixture exercises the
   separate-purchase branch of 7 CFR 250.2 (Missing Eligibility Criteria 2). Scenarios 9 and 10
   state the pooling assumption explicitly, because it is what makes their households
   income-ineligible and therefore what makes them test criterion 3 at all.

### Scenario 1: Applicant turns 60 in the reference month — Eligible, $651
**What we're checking**: the age floor is inclusive, at the birth-month edge, and the basic income pathway.
**Expected**: Eligible — $651 (1 qualifying individual × $651)
**Steps**:
* Screen reference date: `2026-08-27`
* Location: ZIP `67214`, county `Sedgwick County`
* Person 1: born 60 years before the reference date, in the same calendar month — August 1966 for this screen — head of household, Social Security retirement $1,400/month
**Why this matters**: primary regression test — $16,800/yr is comfortably under the one-person limit of $23,940 — and it pins the hardest bound in the program from below. A `> 60` mutation, or one that treated the birth month as not yet reached, fails here.

### Scenario 2: Income exactly at the one-person limit — Eligible, $651
**What we're checking**: the comparison is `<=`, not `<`, and the limit comes from the currently published guideline year.
**Expected**: Eligible — $651 (income $23,940/yr = 1.5 × $15,960 exactly)
**Steps**:
* Location: ZIP `67214`, county `Sedgwick County`
* Person 1: born March 1958 (age 68), head of household, Social Security retirement $1,995/month
**Why this matters**: kills an off-by-one that would reject applicants at the threshold Kansas itself publishes, and pins the guideline year — measured against the prior year's table this household would be wrongly rejected.

### Scenario 3: Income $1/month over the limit, with rent declared — Ineligible
**What we're checking**: the ceiling binds just above the boundary, and the income compared is gross, not net of expenses.
**Expected**: Ineligible (gross income $23,952/yr > $23,940 limit; no categorical certification)
**Steps**:
* Location: ZIP `67214`, county `Sedgwick County`
* Person 1: born March 1958 (age 68), head of household, Social Security retirement $1,996/month
* Expenses: rent $900/month
**Why this matters**: two mutations at once. The $12/yr margin kills threshold rounding; and an implementation deducting expenses would see $13,152 and wrongly pay $651, which no other scenario in this set would catch.

### Scenario 4: Applicant turns 60 the month after the reference month — Ineligible
**What we're checking**: the lower age bound at the birth-month edge.
**Expected**: Ineligible (no member aged 60 or over — age 59 at the reference date)
**Steps**:
* Screen reference date: `2026-08-27`
* Location: ZIP `67214`, county `Sedgwick County`
* Person 1: born 60 years before the reference date, in the *following* calendar month — September 1966 for this screen, so age 59 — head of household, Social Security retirement $1,400/month
**Why this matters**: paired with scenario 1 this pins the boundary to the month. The household is comfortably income-eligible, so age is the only thing failing, and a month-rounding error in the age derivation flips it.

### Scenario 5: Two seniors exactly at the two-person limit — Eligible, $1,302
**What we're checking**: the limit rises by $8,520 for the second person, and the value is paid per qualifying individual.
**Expected**: Eligible — $1,302 (2 qualifying individuals × $651; income $32,460/yr = $23,940 + $8,520 exactly)
**Steps**:
* Location: ZIP `67214`, county `Sedgwick County`
* Person 1: born May 1965 (age 61), head of household, Social Security retirement $1,505/month
* Person 2: born January 1959 (age 67), spouse, Social Security retirement $1,200/month
**Why this matters**: kills two mutations at once — a calculator that always used the one-person limit would reject this household, and one paying a flat household benefit would return $651. Sitting exactly on the two-person limit also pins the increment, which a round-number fixture would leave open.

### Scenario 6: Two seniors $1/month over the two-person limit — Ineligible
**What we're checking**: the household-size increment binds from above as well as below.
**Expected**: Ineligible (gross income $32,472/yr > $32,460 limit; no categorical certification)
**Steps**:
* Location: ZIP `67214`, county `Sedgwick County`
* Person 1: born May 1965 (age 61), head of household, Social Security retirement $1,506/month
* Person 2: born January 1959 (age 67), spouse, Social Security retirement $1,200/month
**Why this matters**: with scenario 5 this brackets the two-person limit to $12/yr. An increment of anything other than $8,520 fails one of the pair.

### Scenario 7: One senior and one younger adult — Eligible, $651
**What we're checking**: only members aged 60 or over generate a benefit, while every member counts toward household size.
**Expected**: Eligible — $651 (1 qualifying individual × $651; income $32,400/yr under the two-person limit of $32,460)
**Steps**:
* Location: ZIP `67214`, county `Sedgwick County`
* Person 1: born May 1965 (age 61), head of household, Social Security retirement $1,500/month
* Person 2: born June 1986 (age 40), adult child, wages $1,200/month
**Why this matters**: the only scenario distinguishing the member test from the household test. A calculator paying every member would return $1,302; one sizing the income limit by qualifying members rather than household members would apply the one-person limit and reject at $32,400.

### Scenario 8: Household over the income limit receives SNAP — Eligible, $651
**What we're checking**: categorical certification displaces the income test entirely.
**Expected**: Eligible — $651 (1 qualifying individual × $651)
**Steps**:
* Location: ZIP `67214`, county `Sedgwick County`
* Person 1: born March 1958 (age 68), head of household, Social Security retirement $2,000/month
* Expenses: rent $1,400/month
* Current benefits: SNAP
**Why this matters**: $24,000/yr is $60 over the one-person limit, so this household is eligible only through criterion 3. A calculator applying the income test to everyone rejects it. The rent is what makes the fixture coherent rather than decorative: SNAP exempts a household with an elderly member from its gross income test but not from its net test at 100 percent of the guidelines, so without substantial shelter costs this household could not hold the SNAP certification the scenario asserts. CSFP counts gross income and ignores the rent, which is why the two tests disagree.

### Scenario 9: Senior on SSI in a household over the income limit — Eligible, $651
**What we're checking**: SSI is a categorical route in its own right, not only SNAP, and it is the applicant's own certification that carries it.
**Expected**: Eligible — $651 (1 qualifying individual × $651; household gross $43,800/yr > the two-person limit of $32,460)
**Steps**:
* Location: ZIP `67214`, county `Sedgwick County`
* Person 1: born March 1958 (age 68), head of household, SSI $900/month
* Person 2: born June 1986 (age 40), adult child, wages $2,750/month
* Person 1 and person 2 customarily purchase food and prepare meals together, so they are one CSFP household under 7 CFR 250.2
* Current benefits: SSI
**Why this matters**: an implementation reading only SNAP survives scenario 8 and fails here — Kansas names five routes, not one. The household shape is load-bearing twice over. It is the only shape in which the SSI route is reachable: SSI's federal benefit rate is under $1,000/month, so a senior with enough income to fail criterion 2 cannot be receiving SSI, and the income pushing this household over the limit must belong to someone else. And person 2's wages alone ($33,000/yr) clear the two-person limit, so the household fails criterion 2 whether or not SSI counts as income — which matters because a fixture relying on the SSI amount alone to cross the limit would stop testing this criterion the moment anything changed how that one stream is counted.
**Note**: the signal carrying this route is person 1's reported `sSI` income stream, not the Current Benefits tile — measured 2026-09-25, it returns $651 with the tile removed. Scenario 8's SNAP tile *is* load-bearing (removing it returns $0), so the two rest on reported certification by different fields.

### Scenario 10: Senior on a Medicare Savings Program in a household over the income limit — Eligible, $651
**What we're checking**: the third categorical route, as MFB can actually exercise it — PolicyEngine's computed Medicare Savings entitlement, not a reported certification.
**Expected**: Eligible — $651 (1 qualifying individual × $651; household gross $48,600/yr > the two-person limit of $32,460)
**Steps**:
* Location: ZIP `67214`, county `Sedgwick County`
* Person 1: born March 1958 (age 68), head of household, Social Security retirement $1,300/month
* Person 2: born June 1986 (age 40), adult child, wages $2,750/month
* Person 1 and person 2 customarily purchase food and prepare meals together, so they are one CSFP household under 7 CFR 250.2
* Current benefits: Medicare Savings Program
**Why this matters**: Medicare Savings is the route most specific to this program's population and the one most easily confused with Medicaid, which is not a route. It takes scenario 9's two-person shape for the same reason: the Medicare Savings tiers key to the same poverty guidelines as CSFP but sit below its 150 percent, so a senior whose own income fails criterion 2 is unlikely to hold the certification. Person 1's $15,600/yr is below 100 percent of the one-person guideline ($15,960) — the strictest and most widely available tier — so the fixture holds without depending on where Kansas sets the higher tiers, which this spec has not sourced. The household's gross is half again over the limit, the configuration in which displacement actually changes an answer.
**Note**: the Current Benefits tile is not load-bearing here — measured 2026-09-25, this scenario returns $651 with the tile removed. See criterion 3 on why no fixture can test an MSP certification.

### Scenario 11: Household over the income limit receives TANF — Ineligible
**What we're checking**: the categorical list is closed at the five programs Kansas named.
**Expected**: Ineligible (gross income $24,000/yr > $23,940 limit; TANF is not one of the five routes)
**Steps**:
* Location: ZIP `67214`, county `Sedgwick County`
* Person 1: born March 1958 (age 68), head of household, Social Security retirement $2,000/month
* Current benefits: TANF
**Why this matters**: the only fail case for criterion 3, and the mutation is live — Kansas collects both TANF and Medicaid in its current-benefits step, and MFB-1043's implementation note wrongly lists TANF as a route. Without this scenario an implementation ORing in `has_base_benefit("tanf")` would pass all twelve others.

### Scenario 12: Two income types together cross the limit — Ineligible
**What we're checking**: income is gross across every type the screener collects, not a selected subset.
**Expected**: Ineligible (gross income $24,000/yr > $23,940 limit; no categorical certification)
**Steps**:
* Location: ZIP `67214`, county `Sedgwick County`
* Person 1: born March 1958 (age 68), head of household, Social Security retirement $1,200/month + unemployment $800/month
**Why this matters**: neither stream crosses the limit alone, so this fails if anything narrows the income total to a selected subset of types. `unemployment` is the marker because it sits outside the school-meals list a narrowing change would most plausibly revert to: with that list the engine is handed $14,400/yr and wrongly returns $651.

### Scenario 13: Senior in a county with no distribution site — Ineligible (accepted approximation)
**What we're checking**: MFB's accepted approximation on service area — that the county gate denies, and that it is the *only* thing denying.
**Expected**: Ineligible — $0 (income and age both pass; `ks_dcf_csfp_county_eligible` is false)
**Steps**:
* Location: ZIP `66749`, county `Allen County`
* Person 1: born March 1958 (age 68), head of household, Social Security retirement $1,400/month
**Why this matters**: this asserts what MFB does, not what the rule says — see the approximation on Missing Eligibility Criteria 1. Allen County appears in neither Kansas DCF's provider table nor its *CSFP Sites by Jurisdiction* spreadsheet ([snapshot `2026-08-27--ks-dcf-csfp-sites-by-jurisdiction`](../../../sources/ks/ks_csfp/2026-08-27--ks-dcf-csfp-sites-by-jurisdiction/content.md), accessed 2026-08-27), so this is a genuine no-site county. Kansas permits local agencies to serve residents outside their normal service area, so the evidenced rule would not deny this household — PolicyEngine's absolute county gate does, and MFB accepts it. The fixture is deliberately identical to scenario 1 except for county, so the $0 can only come from the county gate: if it ever returns $651 the approximation has been lifted upstream and the spec needs revisiting; if it returns $0 while scenario 1 also fails, something other than county is denying and this proves nothing.

### Scenario 14: Gifts and contributions cross the limit — Ineligible
**What we're checking**: gifts and contributions count as income like any other type — the one type with a statutory argument for being excluded.
**Expected**: Ineligible (gross income $25,200/yr > $23,940 limit; no categorical certification)
**Steps**:
* Location: ZIP `67214`, county `Sedgwick County`
* Person 1: born March 1958 (age 68), head of household, Social Security retirement $1,900/month + gifts and contributions $200/month
**Why this matters**: Social Security alone is $22,800/yr, under the one-person limit, so the gifts stream is the only thing denying. 7 CFR 247.9(d)(2) lets a state exclude the value of in-kind benefits, and `gifts` is the only screener income type that clause could reach — making "carve out gifts" the one plausible future misreading of criterion 2. Measured: with `gifts` excluded from the total the engine is handed $22,800 and wrongly pays $651, and scenario 12 does not catch it. This is the only scenario in the suite that does.

### Scenario 15: The adult child, not the senior, holds the SSI certification — Ineligible
**What we're checking**: a certification is the applicant's own — one member's SSI does not make another member categorically eligible.
**Expected**: Ineligible (gross income $54,000/yr > the two-person limit of $32,460; the SSI certification belongs to person 2, who is under 60)
**Steps**:
* Location: ZIP `67214`, county `Sedgwick County`
* Person 1: born March 1958 (age 68), head of household, Social Security retirement $2,000/month
* Person 2: born June 1986 (age 40), adult child, wages $1,600/month and SSI $900/month
* Person 1 and person 2 customarily purchase food and prepare meals together, so they are one CSFP household under 7 CFR 250.2
* Current benefits: SSI
**Why this matters**: criterion 3 is applicant-scoped, and the screener's Current Benefits tile is screen-level — so a household-wide propagation would make this 68-year-old categorically eligible on their adult child's SSI, the broadening the criterion explicitly refuses. Two things keep the denial attributable. Person 2's wages alone ($19,200) put the household over the limit alongside person 1's $24,000, so it does not depend on the SSI stream being counted. And person 1's income sits above every Medicare Savings tier (QI is 135 percent of the guidelines, $21,546): at $15,600 PolicyEngine computes an MSP entitlement of $202.90/month and the categorical branch fires on that computed amount, which would make this fixture pass for a reason unrelated to propagation.

## Research Sources

| Snapshot | Tier | Title | URL | Retrieved |
|---|---|---|---|---|
| `2026-08-27--7-cfr-247-5` | 1 | 7 CFR 247.5 — State and local agency responsibilities (CSFP) | https://www.ecfr.gov/api/versioner/v1/full/2026-08-25/title-7.xml?subtitle=B&chapter=II&subchapter=A&part=247&section=247.5 | 2026-08-27 |
| `2026-08-27--7-cfr-247-9` | 1 | 7 CFR 247.9 — Eligibility requirements (CSFP) | https://www.ecfr.gov/api/versioner/v1/full/2026-08-25/title-7.xml?subtitle=B&chapter=II&subchapter=A&part=247&section=247.9 | 2026-08-27 |
| `2026-08-27--7-cfr-247-10` | 1 | 7 CFR 247.10 — Distribution and use of USDA Foods (CSFP) | https://www.ecfr.gov/api/versioner/v1/full/2026-08-25/title-7.xml?subtitle=B&chapter=II&subchapter=A&part=247&section=247.10 | 2026-08-27 |
| `2026-08-27--7-cfr-247-11` | 1 | 7 CFR 247.11 — Applicants exceed caseload levels (CSFP waiting lists) | https://www.ecfr.gov/api/versioner/v1/full/2026-08-25/title-7.xml?subtitle=B&chapter=II&subchapter=A&part=247&section=247.11 | 2026-08-27 |
| `2026-08-27--7-cfr-247-14` | 1 | 7 CFR 247.14 — Other public assistance programs (CSFP) | https://www.ecfr.gov/api/versioner/v1/full/2026-08-25/title-7.xml?subtitle=B&chapter=II&subchapter=A&part=247&section=247.14 | 2026-08-27 |
| `2026-08-27--7-cfr-247-16` | 1 | 7 CFR 247.16 — Certification period (CSFP) | https://www.ecfr.gov/api/versioner/v1/full/2026-08-25/title-7.xml?subtitle=B&chapter=II&subchapter=A&part=247&section=247.16 | 2026-08-27 |
| `2026-09-10--7-cfr-250-2` | 1 | 7 CFR 250.2 — Definitions (household, for CSFP/FDPIR/TEFAP) | https://www.ecfr.gov/api/versioner/v1/full/2026-08-25/title-7.xml?subtitle=B&chapter=II&subchapter=A&part=250&section=250.2 | 2026-09-10 |
| `2026-09-11--7-cfr-247-1` | 1 | 7 CFR 247.1 — Definitions (CSFP) | https://www.ecfr.gov/api/versioner/v1/full/2026-08-25/title-7.xml?subtitle=B&chapter=II&subchapter=A&part=247&section=247.1 | 2026-09-11 |
| `2026-09-11--7-cfr-247-19` | 1 | 7 CFR 247.19 — Dual participation (CSFP) | https://www.ecfr.gov/api/versioner/v1/full/2026-08-25/title-7.xml?subtitle=B&chapter=II&subchapter=A&part=247&section=247.19 | 2026-09-11 |
| `2026-08-27--hhs-2026-poverty-guidelines` | 1 | HHS ASPE — Poverty Guidelines (2026) | https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines | 2026-08-27 |
| `2026-08-27--ks-dcf-csfp-state-plan` | 2 | Kansas CSFP State Plan | https://www.dcf.ks.gov/services/ees/Documents/Food_Distribution_Programs/CSFPStatePlan.pdf | 2026-08-27 |
| `2026-08-27--ks-dcf-csfp-overview` | 2 | Kansas DCF — Commodity Supplemental Food Program overview | https://www.dcf.ks.gov/services/ees/Pages/USDA-Commodity-Programs/CSFP/CSFP.aspx | 2026-08-27 |
| `2026-08-27--ks-dcf-csfp-income-guidelines` | 2 | Kansas DCF — CSFP income guidelines | https://www.dcf.ks.gov/services/ees/Pages/USDA-Commodity-Programs/CSFP/CSFP-Income-Guidelines.aspx | 2026-08-27 |
| `2026-08-27--ks-dcf-csfp-faqs` | 2 | Kansas DCF — CSFP FAQs (county coverage, application, verification) | https://www.dcf.ks.gov/services/ees/pages/usda-commodity-programs/csfp/csfp-faqs.aspx | 2026-08-27 |
| `2026-08-27--ks-dcf-csfp-sites-by-jurisdiction` | 2 | Kansas DCF — CSFP Sites by Jurisdiction (spreadsheet) | https://content.dcf.ks.gov/ees/KEESM/Intranet/CSFPSitesbyJurisdiction.xlsx | 2026-08-27 |
| `2026-08-27--ks-dcf-csfp-participant-application` | 2 | Kansas DCF — CSFP participant application (A2, Ver 1) | https://www.dcf.ks.gov/services/ees/Documents/CSFP/A2%20Participant%20CSFP%20Application%20Ver%201.pdf | 2026-08-27 |
| `2026-08-27--fns-csfp-program-page` | 2 | USDA FNS/FNA — Commodity Supplemental Food Program | https://www.fns.usda.gov/csfp/commodity-supplemental-food-program | 2026-08-27 |
| `2026-08-27--fns-csfp-caseload-assignments-2026` | 2 | USDA FNA — CSFP Caseload Assignments for the 2026 Caseload Cycle and Administrative Grants (index page) | https://www.fns.usda.gov/csfp/caseload-assignments-2026 | 2026-08-27 |
| `2026-09-11--fns-csfp-caseload-2026-memo` | 2 | USDA FNS — CSFP Caseload Assignments for the 2026 Caseload Cycle and Administrative Grants (memorandum PDF) | https://www.usda.gov/sites/default/files/guidance-documents/FNS.csfp-caseload-2026.pdf | 2026-09-11 |
| `2026-08-27--kansas-food-bank-feeding-seniors` | 3 | Kansas Food Bank — Feeding Seniors (CSFP county list) | https://kansasfoodbank.org/feeding-seniors/ | 2026-08-27 |
| `2026-08-27--umod-food-ministry` | 3 | United Methodist Open Door — Food Ministry (CSFP local agency) | https://umopendoor.org/how-we-help/food-ministry/ | 2026-08-27 |
| `2026-09-25--usda-prwora-federal-public-benefit-notice` | 1 | USDA — PRWORA; Interpretation of "Federal Public Benefit" (90 FR 30621) — names CSFP among the programs administered under the superseding provisions of 8 U.S.C. 1615 | https://www.federalregister.gov/documents/full_text/text/2025/07/10/2025-12691.txt | 2026-09-25 |
| `2026-09-28--usda-national-hunger-hotline` | 1 | USDA FNA — National Hunger Hotline (backup food resource; captured for the config's waiting-list warning) | https://www.fna.usda.gov/national-hunger-hotline | 2026-09-28 |
