# Housing Choice Voucher Program (Section 8) (IL) — Program Spec

- **Program key**: `il_hcv` — `programs/programs/white_labels/il/hcv`, class `IlHcv`
- **Base federal program**: Housing Choice Voucher (Section 8), 24 CFR part 982
- **White label**: IL
- **Engine**: MFB Custom — Python
- **Geographic scope**: statewide
- **Policy/data year**: FY2026 (Fair Market Rents, income limits) and CY2026 (HUD inflation-adjusted amounts)
- **Spec last updated**: 2026-08-31
- **Sources verified as of**: 2026-08-30

## Covered Eligibility Criteria

All criteria are conjunctive: every one must hold.

**MFB screening convention.** MFB uses HUD's Very Low Income limit as the statewide Housing Choice Voucher screening threshold. Federal rules permit certain households above that threshold to qualify through additional categorical or PHA-specific admission pathways, which MFB cannot identify from current screener data. Those pathways are documented as Missing Eligibility Criteria 1 and constitute a known narrowing limitation: a household the screener rejects on income may still be admissible at its local agency. The convention is used because it is the one threshold that is sufficient at every administering agency, and because MFB captures neither the administering agency nor the facts the other five routes turn on.

1. **The household's annual income does not exceed HUD's published very low income limit — nominally 50 percent of area median income — for its county and household size.**
   - Evaluation scope: `household`
   - Captured via: accessor `Screen.calc_gross_income("yearly", ["all"])`, **reduced by the 24 CFR 5.609 exclusions below**; `county` (Screen, CharField) and `household_size` (Screen, IntegerField) select the limit; the limit itself comes from HUD's Standard Section 8 Income Limits via `hud_client.get_screen_il_ami(screen, "50%", year)` (`integrations/clients/hud_income_limits`)
   - Implementation note: the comparison is inclusive (`<=`) — the regulation phrases the test as "does not exceed". The limit is HUD's published figure rather than an arithmetic 50 percent of the area median, because HUD applies high-housing-cost and non-metropolitan floor adjustments; for both Illinois areas modelled here the published figure happens to equal exactly half the area median. `county` and `household_size` are nullable, and the HUD client raises rather than returning a value when the county cannot be matched or household size falls outside 1–8; a null `household_size` must be treated inclusively rather than compared.
   - **Annual income is not raw gross income.** 24 CFR 5.609 defines it, and the definition is mandatory for every PHA — HUD Notice PIH 2026-15 Appendix A sets the compliance date for the Notice PIH 2024-38 income exclusions at "No later than July 1, 2025", unchanged by the 2027 date that applies to the rest of HOTMA sections 102 and 104. Five parts of the definition are modelable from the screener and must be applied **before** the limit comparison, because they change eligibility and not only value:
     - Only members aged 18 or over, plus the head of household and spouse, contribute their full income; for a dependent under 18 only *unearned* income counts (§ 5.609(a)(1)).
     - A child under 18 has their earned income excluded entirely (§ 5.609(b)(3)). From `age` (HouseholdMember, PositiveIntegerField) and the income type.
     - A dependent full-time student has earned income above the dependent-deduction amount excluded (§ 5.609(b)(14)); only up to that amount counts — **$500** under the convention in Benefit Value. From `student_full_time` (HouseholdMember, BooleanField) and `age`. The cap tracks whichever dependent-deduction figure is operative, so it needs no separate constant; HUD's CY2026 table lists it independently at $500 against § 5.609(b)(14), which agrees.
     - Workers' compensation is excluded (§ 5.609(b)(5)). From the `workersComp` income type on `IncomeStream`.
     - The income of a foster child or foster adult is excluded (§ 5.609(b)(8)). From `relationship == "fosterChild"` (HouseholdMember, CharField).
       - **Committed treatment:** exclude that member's income; **retain** them in `household_size`; **retain** the dependent deduction for them.
       - **Known divergence from the federal text.** 24 CFR 5.603 excludes foster children from the dependent definition, so a true foster child earns no deduction. MFB's single `fosterChild` value conflates foster placement with kinship care, and a kinship-care child *is* an ordinary dependent, so each sub-rule is resolved in the widening direction. For a genuine foster placement the subsidy is overstated — by one dependent deduction, and by one bedroom where the count crosses a band. Resolving it needs a screener distinction between foster and kinship care, or an HCV-wide convention. Note the `was_in_foster_care` tile does **not** resolve this: it asks whether a person was ever in foster care, not whether an existing `fosterChild` household member is a formal placement or a kinship arrangement. See `programs/programs/FOSTER_CARE_SCREENER_GAPS.md`.
     - Aggregation is **member-level**. Each exclusion attaches to a person, not to an income type across the household, so a global filter on `calc_gross_income` cannot express them: the same `wages` type counts for an adult and is excluded for a 16-year-old.
     - **Foster and kinship care payments — ⚠️ data gap.** § 5.609(b)(4) excludes payments received *for the care of* foster children or adults, and State or Tribal kinship or guardianship care payments. This is a different rule from the foster member's own income above. MFB has no such income type, and these payments most likely arrive as `cashAssistance`, which also carries countable benefits. **Do not globally exclude `cashAssistance`.** The payments stay countable, which overstates annual income and understates the subsidy. Resolving it needs a dedicated income type, not a calculator-side heuristic.
     - The remaining § 5.609(b) exclusions — trust distributions, insurance settlements other than workers' compensation, student financial assistance, retirement-account income, self-employment gross receipts and the rest — are not modelable, because the screener records income by broad type and not by these categories. Omitting an **exclusion** overstates annual income, which narrows results.
     - The § 5.609(a)(2) imputed return on net family assets above the published threshold runs the **other way**: it is an income *inclusion* the screener cannot compute from a single `household_assets` figure, so omitting it understates annual income and widens results. The two errors are not the same direction and partially offset; neither is quantifiable from a screen.
     - The shipped `tx_hcv` calculator already implements the minor-earned-income exclusion this way; `wa_hcv` does not, and is a compliance gap rather than a precedent.
   - Source: 24 CFR 5.609(a)(1) — "All amounts, not specifically excluded in paragraph (b) of this section, received from all sources by each member of the family who is 18 years of age or older or is the head of household or spouse of the head of household, plus unearned income by or on behalf of each dependent who is under 18 years of age" — [snapshot `2026-08-26--24-cfr-5-609`](../../../sources/il/il_hcv/2026-08-26--24-cfr-5-609/content.md), accessed 2026-08-26
   - Source: 24 CFR 5.609(b)(3) — "Earned income of children under the 18 years of age." — [snapshot `2026-08-26--24-cfr-5-609`](../../../sources/il/il_hcv/2026-08-26--24-cfr-5-609/content.md), accessed 2026-08-26
   - Source: 24 CFR 5.609(b)(14) — "Earned income of dependent full-time students in excess of the amount of the deduction for a dependent in § 5.611." — [snapshot `2026-08-26--24-cfr-5-609`](../../../sources/il/il_hcv/2026-08-26--24-cfr-5-609/content.md), accessed 2026-08-26
   - Source: 24 CFR 5.609(b)(5) — "Insurance payments and settlements for personal or property losses, including but not limited to payments through health insurance, motor vehicle insurance, and workers' compensation." — [snapshot `2026-08-26--24-cfr-5-609`](../../../sources/il/il_hcv/2026-08-26--24-cfr-5-609/content.md), accessed 2026-08-26
   - Source: 24 CFR 5.609(b)(8) — "Income of a live-in aide, foster child, or foster adult as defined in §§ 5.403 and 5.603, respectively." — [snapshot `2026-08-26--24-cfr-5-609`](../../../sources/il/il_hcv/2026-08-26--24-cfr-5-609/content.md), accessed 2026-08-26
   - Source: 24 CFR 5.609(b)(4), the separate care-payment exclusion MFB cannot model — "Payments received for the care of foster children or foster adults, or State or Tribal kinship or guardianship care payments." — [snapshot `2026-08-26--24-cfr-5-609`](../../../sources/il/il_hcv/2026-08-26--24-cfr-5-609/content.md), accessed 2026-08-26
   - Source: HUD Notice PIH 2026-15, Appendix A: Summary of Compliance Requirements — "Income exclusions," / "as described in" / "Notice PIH 2024-38" against "All PHAs" and "No later than July 1, 2025" — [snapshot `2026-08-28--hud-pih-2026-15`](../../../sources/il/il_hcv/2026-08-28--hud-pih-2026-15/content.md), accessed 2026-08-28
   - Source: 24 CFR 982.201(b)(1) — "To be income-eligible, the applicant must be a family in any of the following categories:" followed by "(i) A “very low income” family;" — [snapshot `2026-08-26--24-cfr-982-201`](../../../sources/il/il_hcv/2026-08-26--24-cfr-982-201/content.md), accessed 2026-08-26
   - Source: 24 CFR 5.603, definition of *Very low income family* — "A family whose annual income does not exceed 50 percent of the median family income for the area, as determined by HUD with adjustments for smaller and larger families" — [snapshot `2026-08-26--24-cfr-5-603`](../../../sources/il/il_hcv/2026-08-26--24-cfr-5-603/content.md), accessed 2026-08-26
   - Source: 42 U.S.C. 1437a(b)(2)(B) — "The term ‘‘very low-income families’’" / "means low-income families whose incomes do" / "not exceed 50 per centum of the median family" / "income for the area, as determined by the Secretary with adjustments for smaller and larger" / "families" (one sentence, split by PDF line breaks) — [snapshot `2026-08-26--42-usc-1437a`](../../../sources/il/il_hcv/2026-08-26--42-usc-1437a/content.md), accessed 2026-08-26
   - Source: Housing Authority of Cook County HCV Administrative Plan, "Using Income Limits for Eligibility [24 CFR 982.201]" — "To be income-eligible, a family" / "must be one of the following:" followed by "A very low-income family." — [snapshot `2026-08-29--hacc-hcv-admin-plan-2025`](../../../sources/il/il_hcv/2026-08-29--hacc-hcv-admin-plan-2025/content.md), accessed 2026-08-29
   - Source: HUD USER FY2026 Income Limits Summary, Chicago-Joliet-Naperville, IL HUD Metro FMR Area — column positions are household sizes, "Persons in Family Download .csv 1 2 3 4 5 6 7 8" — and the limits are "Chicago-Joliet-Naperville, IL HUD Metro FMR Area $121,500 Very Low (50%) Income Limits ($) 42,550 48,600 54,700 60,750 65,650 70,500 75,350 80,200" — [snapshot `2026-08-26--hud-fy2026-income-limits-chicago`](../../../sources/il/il_hcv/2026-08-26--hud-fy2026-income-limits-chicago/content.md), accessed 2026-08-26
   - Source: HUD USER FY2026 Income Limits Summary, Peoria, IL MSA — "Peoria, IL MSA $106,100 Very Low (50%) Income Limits ($) 37,150 42,450 47,750 53,050 57,300 61,550 65,800 70,050" — [snapshot `2026-08-26--hud-fy2026-income-limits-peoria`](../../../sources/il/il_hcv/2026-08-26--hud-fy2026-income-limits-peoria/content.md), accessed 2026-08-26

2. **The applicant is a "family" as the administering agency defines that term.**
   - Evaluation scope: `household`
   - Captured via: `household_size` (Screen, IntegerField) — the test is `household_size >= 1`
   - Implementation note: the term is delegated to the agency, and both Illinois definitions sourced here include a single person living alone, so the test never excludes a household the screener can submit. It is stated because 24 CFR 982.201(a) makes it a requirement. Agency definitions do carry conditions the screener cannot evaluate — a group of unrelated adults must show prior shared residence or pool its resources — and agencies retain discretion over other groupings.
   - Source: 24 CFR 982.201(a) — "To be eligible, an applicant must be a “family;”" — [snapshot `2026-08-26--24-cfr-982-201`](../../../sources/il/il_hcv/2026-08-26--24-cfr-982-201/content.md), accessed 2026-08-26
   - Source: 24 CFR 982.4, definition of *Family* — "A person or group of persons, as determined by the PHA consistent with 24 CFR 5.403, approved to reside in a unit with assistance under the program." — [snapshot `2026-08-26--24-cfr-982-4`](../../../sources/il/il_hcv/2026-08-26--24-cfr-982-4/content.md), accessed 2026-08-26
   - Source: Chicago Housing Authority HCV Administrative Plan, "Family" — "A single person, who may be an elderly person, a displaced person, a disabled person or any other" / "single person" and, on the unrelated-adults condition, "Two or more individuals who are not related by blood, marriage, adoption, or other operation of law" / "but who either can demonstrate that they have lived together previously or certify that each" / "individual’s income and other resources will be available to meet the needs of the family." — [snapshot `2026-08-26--cha-hcv-admin-plan-2026`](../../../sources/il/il_hcv/2026-08-26--cha-hcv-admin-plan-2026/content.md), accessed 2026-08-26

3. **Assistance is restricted to citizens and noncitizens with eligible immigration status; a family with at least one eligible member qualifies as a mixed family.**
   - Evaluation scope: `household` — enforced by program configuration, not by the calculator
   - Captured via: `legal_status_required` on the program row (`il_hcv_initial_config.json`), which the results page uses to decide whether the program is shown for the citizenship filter the user selected (`filterPrograms.ts`). The screener collects no per-member immigration status, so no calculator code evaluates this criterion.
   - Implementation note: the config lists **five** of the six user-selectable statuses — `citizen`, `gc_5plus`, `gc_5less`, `refugee`, `otherWithWorkPermission`. **`non_citizen` is excluded.** The frontend renders that value to users as **"Undocumented"** (`citizenshipFilterConfig.tsx`), so selecting it is a statement that no household member holds an eligible immigration status — precisely the case 24 CFR 5.506(b)(1) makes ineligible. Showing the program there would over-promise, not handle a gap inclusively.
   - `citizen`, both lawful-permanent-resident statuses and `refugee` are eligible under Section 214 outright. `otherWithWorkPermission` renders as "Other Lawful" and is broader than HUD's enumerated categories — it covers eligible statuses (parolee, asylee, withholding of deportation) and also work authorisation that is not itself an eligible status — but it is retained as the appropriate inclusive approximation for eligible statuses the screener cannot distinguish more finely.
   - Mixed-family treatment is a **value** issue, handled under Benefit Value, not an eligibility one: the filter is a single household-level selection, and mixed-status households are reached through the five retained values.
   - Source: 24 CFR 5.506(a) — "Financial assistance under a Section 214 covered program is restricted to:" followed by "Citizens;" and "who have eligible immigration status under one of the categories set forth in Section 214 (see 42 U.S.C. 1436a(a))." — [snapshot `2026-08-28--24-cfr-5-506`](../../../sources/il/il_hcv/2026-08-28--24-cfr-5-506/content.md), accessed 2026-08-28
   - Source: 24 CFR 5.506(b) — "A family shall not be eligible for assistance unless every member of the family residing in the unit is determined to have eligible status" and "Despite the ineligibility of one or more family members, a mixed family may be eligible for one of the three types of assistance provided in §§ 5.516 and 5.518." — [snapshot `2026-08-28--24-cfr-5-506`](../../../sources/il/il_hcv/2026-08-28--24-cfr-5-506/content.md), accessed 2026-08-28
   - Source: Chicago Housing Authority HCV Administrative Plan § 3-II.B — "A family is eligible for assistance as long as at least one member is a citizen, national or eligible" / "noncitizen. Families that include eligible and ineligible individuals are considered mixed families. Such families" / "will be given notice that their assistance will be prorated" — [snapshot `2026-08-26--cha-hcv-admin-plan-2026`](../../../sources/il/il_hcv/2026-08-26--cha-hcv-admin-plan-2026/content.md), accessed 2026-08-26

## Missing Eligibility Criteria (Data Gaps)

1. **A low-income household is also income-eligible through any of five further routes: it is continuously assisted under the 1937 Housing Act; it meets additional criteria the administering agency has set in its Administrative Plan; it is a non-purchasing family in a HOPE 1 or HOPE 2 project; it is a low-income *or moderate-income* family displaced by mortgage prepayment or termination of an insurance contract; or it is a non-purchasing family in a project under a resident homeownership program.** — ⚠️ **Data Gap**
   - Why: the screener collects no continuous-assistance history, displacement status or project residency, and the agency-set route differs by agency. The Chicago Housing Authority admits any household at or below 80 percent of area median income; the Housing Authority of Cook County admits above 50 percent only through categorical routes, adding its own for a low-income family unable to work due to age or disability. No threshold above 50 percent holds statewide, and the displacement route is not bounded by 80 percent at all because it reaches moderate-income families.
   - Handling: the omitted routes are *widening*, so leaving them out **narrows** results rather than widening them — it is the one gap here that is not handled inclusively. Treating the agency-set route as met would raise the gate to 80 percent statewide, which is unsourced for 64 of the 66 Illinois voucher agencies; the narrowing is a **Product-approved exception** to the default-inclusive handling of data gaps, accepted deliberately in preference to over-promising. The consequence is a known false-negative class: households between the very low and low income limits are screened out, which in Chicago is $60,750 to $97,200 for a four-person household. Surfaced in the program description, which must tell users that some agencies admit above the 50 percent limit and that they should check with their local agency.
   - Source: 24 CFR 982.201(b)(1) — "(ii) A low-income family that is “continuously assisted” under the 1937 Housing Act;" / "(iii) A low-income family that meets additional eligibility criteria specified in the PHA Administrative Plan." / "(iv) A low-income family that qualifies for voucher assistance as a non-purchasing family residing in a HOPE 1 (HOPE for public housing homeownership) or HOPE 2 (HOPE for homeownership of multifamily units) project." / "(v) A low-income or moderate-income family that is displaced as a result of the prepayment of the mortgage or voluntary termination of an insurance contract on eligible low-income housing as defined in § 248.101 of this title;" / "(vi) A low-income family that qualifies for voucher assistance as a non-purchasing family residing in a project subject to a resident homeownership program under § 248.173 of this title." — [snapshot `2026-08-26--24-cfr-982-201`](../../../sources/il/il_hcv/2026-08-26--24-cfr-982-201/content.md), accessed 2026-08-26
   - Source: Chicago Housing Authority HCV Administrative Plan § 3-II.A — "To be income-eligible, a family’s total income must not exceed" / "HUD’s low-income limit, or 80 percent of Area Median Income (AMI)." — [snapshot `2026-08-26--cha-hcv-admin-plan-2026`](../../../sources/il/il_hcv/2026-08-26--cha-hcv-admin-plan-2026/content.md), accessed 2026-08-26
   - Source: Housing Authority of Cook County HCV Administrative Plan, "Using Income Limits for Eligibility" — "A low income family who is unable to work due to age or disability." — [snapshot `2026-08-29--hacc-hcv-admin-plan-2025`](../../../sources/il/il_hcv/2026-08-29--hacc-hcv-admin-plan-2025/content.md), accessed 2026-08-29
   - Source: HUD USER FY2026 Income Limits Summary, Chicago-Joliet-Naperville, IL HUD Metro FMR Area, the low income limits bounding the false-negative class — "Low (80%) Income Limits ($) 68,050 77,800 87,500 97,200 105,000 112,800 120,550 128,350" — [snapshot `2026-08-26--hud-fy2026-income-limits-chicago`](../../../sources/il/il_hcv/2026-08-26--hud-fy2026-income-limits-chicago/content.md), accessed 2026-08-26

2. **The agency must deny admission on any of six federally mandated grounds: eviction from federally assisted housing for drug-related criminal activity within the last three years; current illegal drug use by a household member; reasonable cause to believe a member's drug use or pattern of use may threaten other residents' health, safety or peaceful enjoyment; any member ever convicted of manufacturing or producing methamphetamine on federally assisted premises; any member subject to a lifetime State sex-offender registration requirement; and reasonable cause to believe a member's abuse or pattern of abuse of alcohol may threaten other residents' health, safety or peaceful enjoyment.** — ⚠️ **Data Gap**
   - Why: the screener collects no criminal history, no drug or alcohol use, no eviction history and no registry status. None of the six is observable, and the three-year drug-eviction bar additionally carries agency-determined exceptions — completion of an approved supervised rehabilitation programme, or the circumstances having ceased to exist — which are equally unobservable.
   - Handling: `assumed-met` (code comment). Widens results for households subject to any mandatory denial. The permissive grounds in § 982.553(a)(2)(ii) are separate and are covered by Missing Eligibility Criteria 3.
   - Source: 24 CFR 982.553(a)(1)(i) — "The PHA must prohibit admission to the program of an applicant for three years from the date of eviction if a household member has been evicted from federally assisted housing for drug-related criminal activity." with the exceptions "That the evicted household member who engaged in drug-related criminal activity has successfully completed a supervised drug rehabilitation program approved by the PHA; or" / "That the circumstances leading to eviction no longer exist" — [snapshot `2026-08-26--24-cfr-982-553`](../../../sources/il/il_hcv/2026-08-26--24-cfr-982-553/content.md), accessed 2026-08-26
   - Source: 24 CFR 982.553(a)(1)(ii) — "The PHA must establish standards that prohibit admission if:" followed by "The PHA determines that any household member is currently engaging in illegal use of a drug;", "The PHA determines that it has reasonable cause to believe that a household member's illegal drug use or a pattern of illegal drug use may threaten the health, safety, or right to peaceful enjoyment of the premises by other residents; or" and "Any household member has ever been convicted of drug-related criminal activity for manufacture or production of methamphetamine on the premises of federally assisted housing." — [snapshot `2026-08-26--24-cfr-982-553`](../../../sources/il/il_hcv/2026-08-26--24-cfr-982-553/content.md), accessed 2026-08-26
   - Source: 24 CFR 982.553(a)(2)(i) — "The PHA must establish standards that prohibit admission to the program if any member of the household is subject to a lifetime registration requirement under a State sex offender registration program." — [snapshot `2026-08-26--24-cfr-982-553`](../../../sources/il/il_hcv/2026-08-26--24-cfr-982-553/content.md), accessed 2026-08-26
   - Source: 24 CFR 982.553(a)(3) — "The PHA must establish standards that prohibit admission to the program if the PHA determines that it has reasonable cause to believe that a household member's abuse or pattern of abuse of alcohol may threaten the health, safety, or right to peaceful enjoyment of the premises by other residents." — [snapshot `2026-08-26--24-cfr-982-553`](../../../sources/il/il_hcv/2026-08-26--24-cfr-982-553/content.md), accessed 2026-08-26
   - Source: Chicago Housing Authority, Do I Qualify for Housing? — "CHA will check your background for criminal convictions within the past six months as well as permanent bans for certain crimes." — [snapshot `2026-08-26--cha-do-i-qualify`](../../../sources/il/il_hcv/2026-08-26--cha-do-i-qualify/content.md), accessed 2026-08-26

3. **The agency may deny admission on any of ten discretionary grounds — violation of family obligations, eviction from federally assisted housing in the last five years, any prior termination of assistance, fraud or bribery in a federal housing program, rent or other amounts currently owed to any PHA, failure to reimburse a PHA for amounts paid to an owner, breach of a repayment agreement, abusive or violent behaviour toward PHA personnel, welfare-to-work non-compliance, and criminal activity or alcohol abuse.** — ⚠️ **Data Gap**
   - Why: the screener records no rental history, no debt owed to a housing program, no prior assistance termination and no conduct history. None of the ten grounds is observable.
   - Handling: `assumed-met` (code comment). Widens results for households subject to any of them. Stated from the federal rule rather than from any one agency's plan, because a local restatement of grounds (v)–(vii) does not generalise to the other 65 Illinois agencies.
   - Source: 24 CFR 982.552(c)(1) — "The PHA may at any time deny program assistance for an applicant, or terminate program assistance for a participant, for any of the following grounds:" followed by "If the family violates any family obligations under the program", "If any member of the family has been evicted from federally assisted housing in the last five years;", "If a PHA has ever terminated assistance under the program for any member of the family.", "If any member of the family has committed fraud, bribery, or any other corrupt or criminal act in connection with any Federal housing program", "If the family currently owes rent or other amounts to the PHA or to another PHA in connection with Section 8 or public housing assistance under the 1937 Act.", "If the family has not reimbursed any PHA for amounts paid to an owner under a HAP contract for rent, damages to the unit, or other amounts owed by the family under the lease.", "If the family breaches an agreement with the PHA to pay amounts owed to a PHA, or amounts paid to an owner by a PHA.", "If the family has engaged in or threatened abusive or violent behavior toward PHA personnel." and "If the family has been engaged in criminal activity or alcohol abuse as described in § 982.553." — [snapshot `2026-08-29--24-cfr-982-552`](../../../sources/il/il_hcv/2026-08-29--24-cfr-982-552/content.md), accessed 2026-08-29
   - Source: Chicago Housing Authority, Do I Qualify for Housing?, one agency's restatement of the debt ground — "If you owe money to CHA or another housing program, you will need to pay that money back before you can qualify for another CHA program." — [snapshot `2026-08-26--cha-do-i-qualify`](../../../sources/il/il_hcv/2026-08-26--cha-do-i-qualify/content.md), accessed 2026-08-26

4. **A household may be denied assistance where its net family assets exceed the published limit, or where it holds a present ownership interest in, a legal right to reside in, and the effective legal authority to sell real property suitable for occupancy as its residence.** — ⚠️ **Data Gap**
   - **Committed treatment:** MFB applies **no asset or property eligibility gate**; `assumed-met` (code comment). Widens results for households an implementing agency would deny on either prong.
   - Why neither prong is observable: `household_assets` (Screen, DecimalField) is not HUD's *net family assets*. The screener asks "How much does your whole household have right now in cash, checking or savings accounts, stocks, bonds, or mutual funds?", which omits real property, retirement and trust interests and applies none of the § 5.603 exclusions — so comparing it against the § 5.618 threshold would compare two different quantities. `housing_situation` (Screen, CharField) records a housing situation, not an ownership interest coupled with a right to reside and authority to sell, and the regulation's exceptions are not represented.
   - Applicability also varies by agency through 2026: § 5.618 is a HOTMA § 102 provision, and Notice PIH 2026-15 enforces §§ 102 and 104 from 2027-01-01 for PHAs that are neither Moving to Work nor FRS agencies, with no date yet for the rest. HUD's CY2026 table gives $105,574 but does not apply to an agency not yet complying. Peoria states it is implementing in 2026; the Chicago Housing Authority is Initial MTW and still states a flat $100,000; the Housing Authority of Cook County ties adoption to HUD guidance.
   - Surfaced in the program description, which must tell users that some agencies limit savings and property.
   - Source: 24 CFR 5.618(a)(1)(i) — "The family's net assets (as defined in § 5.603) exceed $100,000, which amount will be adjusted annually by HUD in accordance with the Consumer Price Index for Urban Wage Earners and Clerical Workers" — [snapshot `2026-08-26--24-cfr-5-618`](../../../sources/il/il_hcv/2026-08-26--24-cfr-5-618/content.md), accessed 2026-08-26
   - Source: 24 CFR 5.618(a)(1)(ii) — "The family has a present ownership interest in, a legal right to reside in, and the effective legal authority to sell, based on State or local laws of the jurisdiction where the property is located, real property that is suitable for occupancy by the family as a residence" — [snapshot `2026-08-26--24-cfr-5-618`](../../../sources/il/il_hcv/2026-08-26--24-cfr-5-618/content.md), accessed 2026-08-26
   - Source: HUD, 2026 HUD Inflation-Adjusted Values (Table 1) — "Note: If your agency/property/program administrator is not yet complying with Sections 102 and 104 of HOTMA, you" / "will not utilize this table." — [snapshot `2026-08-28--hud-cy2026-inflationary-adjustments`](../../../sources/il/il_hcv/2026-08-28--hud-cy2026-inflationary-adjustments/content.md), accessed 2026-08-28
   - Source: Peoria Housing Authority FY2026 Annual Plan, one agency implementing — "Implementation of asset limitations as mandated by HUD" — [snapshot `2026-08-28--peoria-annual-plan-fy2026`](../../../sources/il/il_hcv/2026-08-28--peoria-annual-plan-fy2026/content.md), accessed 2026-08-28
   - Source: Chicago Housing Authority HCV Administrative Plan § 3-II.A, an Initial MTW agency still stating the un-indexed base — "HUD requires CHA to deny assistance based on the following asset limitations:" followed by "Applicants whose assets are in excess of $100,000." — [snapshot `2026-08-26--cha-hcv-admin-plan-2026`](../../../sources/il/il_hcv/2026-08-26--cha-hcv-admin-plan-2026/content.md), accessed 2026-08-26

5. **The head of household must have the legal capacity to enter into a lease.** — ⚠️ **Data Gap**
   - Why: `age` (HouseholdMember, PositiveIntegerField) is collected, but the rule turns on legal capacity, not on a numeric age, and no screener field records emancipation or contractual capacity. Both sourced Illinois agencies frame it as capacity; Chicago Housing Authority additionally admits an emancipated minor as head of household, so no numeric age gate may be substituted for this rule.
   - Handling: `assumed-met` (code comment). Widens results marginally.
   - Source: Chicago Housing Authority HCV Administrative Plan, "Head of Household" — "Head of Household is an adult family member or an emancipated minor who has the legal capacity to enter" / "into a lease and is considered the head for purposes of determining income eligibility and rent." — [snapshot `2026-08-26--cha-hcv-admin-plan-2026`](../../../sources/il/il_hcv/2026-08-26--cha-hcv-admin-plan-2026/content.md), accessed 2026-08-26
   - Source: Housing Authority of Cook County HCV Administrative Plan — "The tenant must have legal capacity to enter a lease under state and local law." — [snapshot `2026-08-29--hacc-hcv-admin-plan-2025`](../../../sources/il/il_hcv/2026-08-29--hacc-hcv-admin-plan-2025/content.md), accessed 2026-08-29

6. **No section 8 assistance may be provided to an individual who meets all seven conditions of 24 CFR 5.612: enrolled at an institution of higher education; under 24; not a veteran; unmarried; without a dependent child; not a person with disabilities who was receiving section 8 assistance as of 30 November 2005; and not otherwise individually eligible, or having parents who are not eligible on the basis of income.** — ⚠️ **Data Gap**
   - Evaluation scope of the sourced rule: `member` — it attaches to the individual student, not to the household. It is a bar on assisting that individual, not on the household's income eligibility.
   - Why: `age`, `veteran` (HouseholdMember, BooleanField), `student` and `student_full_time` (HouseholdMember, BooleanField), accessor `is_married()` and accessor `has_disability()` reach six of the seven conditions, but two facts inside them are unavailable. The screener holds no income for a parent living outside the household, which is the operative test in condition (g); and it records no history of section 8 receipt as of 30 November 2005, which condition (f) turns on. Because the conditions are conjunctive, failing to evaluate either one leaves the whole test unresolvable.
   - Handling: `assumed-met` (code comment). Widens results for the narrow class of students the rule reaches.
   - Source: 24 CFR 5.612 — "No assistance shall be provided under section 8 of the 1937 Act to any individual who:" followed by "Is enrolled as a student at an institution of higher education, as defined under section 102 of the Higher Education Act of 1965 (20 U.S.C. 1002);", "Is under 24 years of age;", "Is not a veteran of the United States military;", "Is unmarried;", "Does not have a dependent child;", "Is not a person with disabilities, as such term is defined in section 3(b)(3)(E) of the 1937 Act and was not receiving assistance under section 8 of the 1937 Act as of November 30, 2005; and" and "Is not otherwise individually eligible, or has parents who, individually or jointly, are not eligible on the basis of income to receive assistance under section 8 of the 1937 Act." — [snapshot `2026-08-30--24-cfr-5-612`](../../../sources/il/il_hcv/2026-08-30--24-cfr-5-612/content.md), accessed 2026-08-30
   - Source: Housing Authority of Cook County HCV Administrative Plan § 3-II.E, one agency's restatement — "If a student enrolled at an institution of higher education is under the age of 24, is not a veteran," / "is not married, and does not have a dependent child, the student’s eligibility must be examined" / "along with the income eligibility of the student’s parents." — [snapshot `2026-08-29--hacc-hcv-admin-plan-2025`](../../../sources/il/il_hcv/2026-08-29--hacc-hcv-admin-plan-2025/content.md), accessed 2026-08-29

## Priority Criteria

Selection order among eligible households on a waiting list. These change when a household is served, never whether it qualifies. Each agency sets its own; the Chicago Housing Authority's are below.

- **Six selection preferences, in order: targeted funding; special or emergency circumstances; HEARTH-Act homelessness referred through Chicago's Coordinated Entry System; HEARTH-Act homelessness where the household are victims or survivors of gender-based violence; working families, which includes a head, spouse or co-head aged 62 or older or a person with disabilities; and veterans, active or inactive military personnel and their immediate family members.** — screener capture: none; surfaced in the program description
  - Program description tie-back: the description must state that agencies serve some groups ahead of others, naming households experiencing homelessness, working families, and veterans, so a user understands that qualifying is not the same as being served.
  - Source: Chicago Housing Authority HCV Administrative Plan § 4-III.C — "CHA will select families in order of preference as follows [24 CFR 982.207]:" then "(1) Families that meet the criteria under targeted funding;" / "(2) Special/emergency circumstances, such as:" / "(3) Families or individuals that meet HUD’s definition of homelessness under the HEARTH Act and are" / "referred by the City of Chicago or Chicago’s Continuum of Care through the Coordinated Entry System." / "(4) Families or individuals that meet HUD’s definition of homelessness under the HEARTH Act, that are" / "(5) Working Families:" / "An applicant shall be given the benefit of the working preference when the head and co-" / "head spouse are age 62 or older and/or a person with disabilities; and" / "(6) Veterans, Active or Inactive Military Personnel and Immediate Family Members of both." — [snapshot `2026-08-26--cha-hcv-admin-plan-2026`](../../../sources/il/il_hcv/2026-08-26--cha-hcv-admin-plan-2026/content.md), accessed 2026-08-26

- **Within each preference tier, households are selected by a randomly assigned lottery number.** — screener capture: none; surfaced in the program description
  - Program description tie-back: none needed — the warning message's statement that waits can be long, together with the description's statement that some groups are served first, already conveys that position is not first-come, first-served.
  - Source: Chicago Housing Authority HCV Administrative Plan § 4-II.A — "Once each application has been randomly assigned a number, the applications" — and § 4-III.C — "Families that qualify for the above preferences will be selected within each preference by their assigned lottery" — [snapshot `2026-08-26--cha-hcv-admin-plan-2026`](../../../sources/il/il_hcv/2026-08-26--cha-hcv-admin-plan-2026/content.md), accessed 2026-08-26

- **At least 75 percent of the households an agency admits from its waiting list in a fiscal year must be extremely low income; under the Chicago Housing Authority's Moving to Work agreement the same 75 percent threshold is set at the very low income limit instead, and lower-income households are selected ahead of others to meet it.** — screener capture: none; surfaced in the program description
  - Program description tie-back: the description must say that agencies must fill most openings with the lowest-income households, so a household nearer the income limit understands it is less likely to be reached.
  - Source: 24 CFR 982.201(b)(2)(i) — "Not less than 75 percent of the families admitted to a PHA's HCV program during the PHA fiscal year from the PHA waiting list shall be extremely low income families." — [snapshot `2026-08-26--24-cfr-982-201`](../../../sources/il/il_hcv/2026-08-26--24-cfr-982-201/content.md), accessed 2026-08-26
  - Source: Chicago Housing Authority HCV Administrative Plan § 4-III.C, Income Targeting Requirement — "Under the Moving to Work program, HUD requires that very low-income families (Defined by HUD as annual" / "incomes at or below 50 percent of the area median income) make up at least 75 percent of families admitted" / "to the HCV program annually." / "Very low-income families will be selected ahead of other eligible families on an as-needed basis to ensure" / "income-targeting requirements are met." — [snapshot `2026-08-26--cha-hcv-admin-plan-2026`](../../../sources/il/il_hcv/2026-08-26--cha-hcv-admin-plan-2026/content.md), accessed 2026-08-26

## Related Programs

- **Public Housing, Project-Based Vouchers, and Project-Based Rental Assistance** — the other three subsidised housing programs the Chicago Housing Authority runs, each with its own eligibility and its own waiting list. Their waiting lists are open while the tenant-based voucher list is not, which makes them the actionable alternative for a household that qualifies here. Not a separate eligibility path in MFB.
  - Config tie-back: carried by the `il_hcv_waitlist_closed` **warning message**, not the description — it must tell a user that the voucher waiting list is closed but that the same agency's public housing and project-based lists accept applications. Relocated 2026-08-31: waitlist status is live information, and the warning message can be updated independently of the description when it changes.
  - Source: Chicago Housing Authority, Do I Qualify for Housing? — "CHA offers four types of subsidized housing opportunities: Public Housing, Housing Choice Vouchers (HCV), Project Based Vouchers (PBV), and Project Based Rental Assistance (PBRA)." and "Public Housing and Project-Based Voucher waitlists are always open." — [snapshot `2026-08-26--cha-do-i-qualify`](../../../sources/il/il_hcv/2026-08-26--cha-do-i-qualify/content.md), accessed 2026-08-26

- **Special-purpose voucher streams — HUD-VASH, Family Unification Program, Foster Youth to Independence, Mainstream, and non-elderly disabled vouchers** — tenant-based vouchers admitted by referral from a partner agency rather than from the general waiting list, each with its own qualifying population. A household reaching one of these is not selected from the list at all, so they remain available while the general list is closed. Not a separate eligibility path in MFB.
  - Program description tie-back: none needed — these are reached through the referring agency (a Veterans Affairs medical centre, a child-welfare agency, a continuum of care), not through this program's application.
  - Source: Chicago Housing Authority FY2026 MTW Annual Plan § II-C, Description of Partially Opened Waitlists — "f) A family that qualifies for a targeted funding voucher (e.g., VASH, NED, FUP, EHV, etc.)." — [snapshot `2026-08-26--cha-mtw-annual-plan-fy2026`](../../../sources/il/il_hcv/2026-08-26--cha-mtw-annual-plan-fy2026/content.md), accessed 2026-08-26
  - Source: Chicago Housing Authority HCV Administrative Plan § 4-III.C — "Family Unification Program (FUP) and Foster Youth to Independence (FYI) participants whose" / "subsidy is expiring;" — [snapshot `2026-08-26--cha-hcv-admin-plan-2026`](../../../sources/il/il_hcv/2026-08-26--cha-hcv-admin-plan-2026/content.md), accessed 2026-08-26

## Benefit Value

- Value: **$10,740/year** for the reference household (= monthly housing assistance payment $895 × 12, for a four-person Cook County household at the extremely low income limit). The value is computed per household, not fixed: **annual value = 12 × max(0, min(payment standard, gross rent) − total tenant payment)**.
  - **Every dollar figure in this section and in Test Scenarios is an MFB estimated value, not a claim about what any administering agency would actually pay.** The federal formula is exact, but two of its inputs are MFB statewide estimation conventions rather than sourced statewide rules — the payment standard and the voucher bedroom size, both below. Illinois has 66 voucher agencies, each setting its own payment standard and subsidy standard, and no statewide schedule exists for either. Where an agency's own schedule was captured it differs from the convention materially, and in both directions.
  - **Payment standard** = 100 percent of the Fair Market Rent for the household's FMR area at the voucher bedroom size, via `hud_client.get_screen_payment_standard(screen, bedrooms, year)`, which reads `zipcode` (Screen, CharField) and `county`.
    - **MFB statewide estimation convention**, not any agency's payment standard. MFB does not capture the administering agency, and Illinois has 66 of them with overlapping service areas — in Cook County alone, two agencies apply different rules. Actual standards vary, so the estimate carries error in **both directions**:
      - *Understates* where an agency sets a higher standard. Peoria set FY2026 standards at 110 percent of FMR effective 2026-01-01 — a one-bedroom standard of $899 against the $818 the convention uses.
      - *Overstates or understates* by ZIP where an agency bands its standards. The Housing Authority of Cook County's 2026 schedule runs $1,310 to $2,570 for two bedrooms against a $1,781 metro figure.
    - **Small Area FMRs are not used.** Chicago-Joliet-Naperville is a HUD-designated mandatory Small Area FMR metro, but HUD exempts Moving to Work agencies operating under an approved alternative payment-standard policy. The Chicago Housing Authority is an MTW agency and states it has not adopted them; the Housing Authority of Cook County, in the same metro, publishes its own ZIP bands. With the agency unknown, no ZIP-level rule is more correct than the metro figure. `HudIncomeClient.MANDATORY_SAFMR_AREA_NAMES` is deliberately left without Chicago for this program.
    - No agency schedule is read by the calculator. They are recorded to bound the error, not to feed it.

  - **Voucher bedroom size** = one bedroom per two people, rounded up: `{1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 4, 8: 4}` from `household_size` (Screen, IntegerField).
    - **MFB statewide estimation convention**, corroborated by no current Illinois agency plan captured for this spec. It is retained because it is the only formulation computable from `household_size` alone.
    - Every captured current agency rule departs from it **upward**, so the convention under-counts bedrooms and **understates** the subsidy. The Housing Authority of Cook County gives the head of household their own room before pairing, with further exceptions for married couples and domestic partners, live-in aides, opposite-sex children aged 6 and older, and members of a different generation. The Peoria Housing Authority pairs, but allocates separate bedrooms to opposite-sex adults 18 or older and opposite-sex children over six. The Chicago Housing Authority's wording admits the same head-first reading.
    - A pregnant woman with no other persons must be treated as a two-person family (24 CFR 982.402(b)(5)). `pregnant` (HouseholdMember, BooleanField) is collected, so this is applied; under the `⌈n/2⌉` map it changes no bedroom count, because one and two people both map to 1BR.
    - The sex-, relationship- and composition-based exceptions are **unmodelable**: no screener field records a member's sex, and none records a live-in aide. See Test Scenarios, Known scenario gaps.

  - **Total tenant payment** = the highest of 30 percent of monthly adjusted income, 10 percent of monthly income (annual income as defined in criterion 1, divided by 12), and the agency's minimum rent, then rounded to the nearest whole dollar **half-up** — `.50` rounds up, `.49` rounds down, per HUD's Form HUD-50058 instructions. Implementations must not use a banker's-rounding primitive: Python's `round()` would turn a $1,188.50 tenant payment into $1,188 rather than $1,189. A minimum rent of **$0** is modelled.
    - **MFB estimation convention.** 24 CFR 5.630(a)(2) lets a voucher PHA set a floor up to $50, and both non-MTW Illinois agencies sourced here charge $50 — but § 5.630(b)(1) makes the hardship exemption mandatory, and whether a household qualifies, requests it, or is granted it is unobservable. The inclusive floor is therefore zero.
    - Where a household's payment would otherwise be set by the floor, the subsidy is **overstated** by up to the agency's minimum rent: $50 at the Housing Authority of Cook County and Peoria, $75 at the Chicago Housing Authority under Moving to Work.

  - **Adjusted income** = annual income − $500 per dependent − $550 where the household is an elderly or disabled family, floored at zero. **Both figures are MFB statewide conventions for the HOTMA transition**: 24 CFR 5.611(a) states un-indexed bases of $480 and $525, HUD's published CY2026 values are $500 and $550, and Illinois agencies differ on which they apply. The published values are used because they are the inclusive choice on the value side — larger deductions mean a lower tenant payment and a higher subsidy, so a household at an agency still on the un-indexed bases sees a modestly overstated figure rather than being under-served in the estimate. A dependent is a family member other than the head or spouse who is under 18, a person with a disability, or a full-time student, excluding foster children and foster adults; from `relationship`, `age`, `student_full_time` and accessor `has_disability()` (HouseholdMember). An elderly or disabled family is one whose head, co-head, spouse or sole member is at least 62 or is a person with a disability. Two further mandatory deductions are not modelled — see the limitation below.
  - **Gross rent proxy** = `Screen.calc_expenses("monthly", ["rent"])` when that is greater than zero, otherwise the payment standard. **`mortgage` is excluded.** 24 CFR 982.4 defines gross rent as rent to owner plus the utility allowance for the assisted unit; a current mortgage payment is not a proxy for the rent of a future tenant-based voucher unit, and including it would put an owner household's mortgage into a rental formula. The fallback to the payment standard keeps the estimate defined for a household that reports no rent — someone currently homeless, doubled up, or living rent-free — for whom the standard arm governs anyway.
    - **This is an MFB estimation convention.** The household's current rent is not the assisted unit's gross rent: MFB does not know which unit the household will lease, what its rent to owner will be, or which PHA utility allowance applies. The utility component is the utility-allowance limitation below. The proxy is retained because § 982.505(b) genuinely takes the lower of two arms, and dropping the rent arm entirely would leave that branch untested and systematically raise every estimate.
  - **Monthly housing assistance payment** = `max(0, min(payment standard, gross rent proxy) − total tenant payment)`.
  - **The payment standard is taken at the family unit size.** 24 CFR 982.505(b)(1) sets it at the lower of "The payment standard amount for the family unit size" and "The payment standard amount for the size of the dwelling unit rented by the family". MFB cannot know the size of the unit a household will eventually lease, so the committed convention is to **assume the assisted unit matches the family unit size**, making the first arm govern. Where a household in fact rents a smaller unit than its voucher allows, the second arm would govern and the real payment standard would be lower, so this convention **overstates** the subsidy for that household. The branch is unobservable and gets no scenario.
  - **The tenant's share of rent is adjusted by a utility allowance covering tenant-paid utilities.**
    - Why: the screener records utility expenses but not which utilities are the tenant's responsibility under the lease, which is what the allowance schedule keys on.
    - Handling: omitted from the value computation, which understates the subsidy for households paying their own utilities. Affects Benefit Value only, not eligibility.
    - Source: Chicago Housing Authority HCV Administrative Plan § 16-II.C — "An established utility allowance schedule is used in determining family share and subsidy." — [snapshot `2026-08-26--cha-hcv-admin-plan-2026`](../../../sources/il/il_hcv/2026-08-26--cha-hcv-admin-plan-2026/content.md), accessed 2026-08-26
  - **Adjusted income is reduced by two further mandatory deductions: unreimbursed health, medical, attendant-care and auxiliary-apparatus expenses above 10 percent of annual income for an elderly or disabled family, and reasonable child care expenses that enable a member to work or study.**
    - Why: `Expense` records a `medical` type and `childCare` and `dependentCare` types, but the regulation's tests turn on whether the expense is unreimbursed, whether it enables employment or education, and whether the household is an elderly or disabled family — none of which the screener captures.
    - Handling: omitted from the value computation, which overstates adjusted income and therefore **understates** the subsidy for households with medical or child care costs. Affects Benefit Value only, not eligibility.
    - Source: 24 CFR 5.611(a) Mandatory deductions — "(3) The sum of the following, to the extent the sum exceeds ten percent of annual income:" / "(i) Unreimbursed health and medical care expenses of any elderly family or disabled family; and" and "(4) Any reasonable child care expenses necessary to enable a member of the family to be employed or to further his or her education." — [snapshot `2026-08-26--24-cfr-5-611`](../../../sources/il/il_hcv/2026-08-26--24-cfr-5-611/content.md), accessed 2026-08-26
  - **The total tenant payment is also floored by a welfare rent where a household receives welfare assistance of which a part is specifically designated for housing costs.**
    - Why: the screener records `cashAssistance` income but not whether any portion of it is designated by the paying agency to meet housing costs, which is the test.
    - Handling: omitted from the total tenant payment computation, which can overstate the subsidy for households in that position. Affects Benefit Value only, not eligibility.
    - Source: 24 CFR 5.628(a)(3) — "If the family is receiving payments for welfare assistance from a public agency and a part of those payments, adjusted in accordance with the family's actual housing costs, is specifically designated by such agency to meet the family's housing costs, the portion of those payments which is so designated;" — [snapshot `2026-08-26--24-cfr-5-628`](../../../sources/il/il_hcv/2026-08-26--24-cfr-5-628/content.md), accessed 2026-08-26
  - **Mixed-family proration is not applied.** Where a household contains both members with eligible immigration status and members without, the federal rule multiplies the housing assistance payment by the eligible share of members. The screener collects no per-member immigration status, so the share is unknowable and the payment is computed unprorated. **Committed handling: pay the unprorated amount** — the same inclusive treatment Covered Eligibility Criterion 3 gives the eligibility side, and the only one computable from a screen. The consequence is that the value is **overstated** for a mixed household, in proportion to the share of ineligible members: a four-person household with two eligible members receives half the modelled figure. Surfaced in the program description, which must tell users that households with both eligible and ineligible members can still get help at a reduced amount.
- `value_format`: annualized (`estimated_annual`). The subsidy is an ongoing monthly payment, not a one-time benefit.
- Variation axes: county (FMR area), household size (bedroom count), household income, household composition (dependent and elderly deductions), and rent relative to the payment standard — each appears in Test Scenarios.
- Source: 24 CFR 982.4, definition of *Gross rent*, the quantity the proxy stands in for — "The sum of the rent to owner plus any utility allowance." — [snapshot `2026-08-26--24-cfr-982-4`](../../../sources/il/il_hcv/2026-08-26--24-cfr-982-4/content.md), accessed 2026-08-26
- Source: 24 CFR 982.505(b) — "The PHA shall pay a monthly housing assistance payment on behalf of the family that is equal to the lower of:" followed by "(1) The payment standard for the family minus the total tenant payment; or" / "(2) The gross rent minus the total tenant payment." — [snapshot `2026-08-26--24-cfr-982-505`](../../../sources/il/il_hcv/2026-08-26--24-cfr-982-505/content.md), accessed 2026-08-26
- Source: 24 CFR 982.503(c) — "A basic range payment standard amount is any dollar amount that is in the range from 90 percent up to 110 percent of the published FMR for a unit size." — [snapshot `2026-08-26--24-cfr-982-503`](../../../sources/il/il_hcv/2026-08-26--24-cfr-982-503/content.md), accessed 2026-08-26
- Source: 24 CFR 982.503(a)(1), on which FMR is the applicable one — "Within each of these FMR areas, the applicable FMR is:" / "(i) The HUD-published Small Area FMR for:" / "(A) Any metropolitan area designated as a Small Area FMR area by HUD in accordance with 24 CFR 888.113(c)(1)." / "(ii) The HUD-published metropolitan FMR for any other metropolitan area." — [snapshot `2026-08-26--24-cfr-982-503`](../../../sources/il/il_hcv/2026-08-26--24-cfr-982-503/content.md), accessed 2026-08-26
- Source: 24 CFR 888.113(c)(3), on the effect of designation — "If a metropolitan area meets the criteria of paragraph (c)(1) of this section, Small Area FMRs will apply to the metropolitan area and all PHAs administering HCV programs in that area will be required to use Small Area FMRs." — [snapshot `2026-08-26--24-cfr-888-113`](../../../sources/il/il_hcv/2026-08-26--24-cfr-888-113/content.md), accessed 2026-08-26
- Source: HUD, Metropolitan Areas Required to Administer a Voucher Program with Small Area FMRs, listing Chicago — "11. ***Chicago-Joliet-Naperville, IL Counties: Cook, DuPage, Kane, Lake, McHenry, Will" — [snapshot `2026-08-26--hud-safmr-required-metro-areas-2023`](../../../sources/il/il_hcv/2026-08-26--hud-safmr-required-metro-areas-2023/content.md), accessed 2026-08-26
- Source: Chicago Housing Authority HCV Administrative Plan § 16-II.B, stating the contrary practice — "The FMR is set at the 50th percentile of rents within the Chicago metropolitan area." / "CHA has not adopted the use of Small Area Fair Market Rents." / "CHA’s payment standards are the same across the entire service area and are within HUD’s “basic range”: between 90 and 110 percent of the published FMR." — [snapshot `2026-08-26--cha-hcv-admin-plan-2026`](../../../sources/il/il_hcv/2026-08-26--cha-hcv-admin-plan-2026/content.md), accessed 2026-08-26
- Source: 24 CFR 5.628(a) — "Total tenant payment is the highest of the following amounts, rounded to the nearest dollar:" followed by "(1) 30 percent of the family's monthly adjusted income;" / "(2) 10 percent of the family's monthly income;" / "(4) The minimum rent, as determined in accordance with § 5.630; or" (paragraph (a)(3), the welfare rent, is the limitation below) — [snapshot `2026-08-26--24-cfr-5-628`](../../../sources/il/il_hcv/2026-08-26--24-cfr-5-628/content.md), accessed 2026-08-26
- Source: 24 CFR 5.520(c)(2), the voucher-program proration method — "For a tenancy under the voucher program, the PHA must prorate the family's assistance as follows:" then "Determine the amount of the pre-proration housing assistance payment." / "Multiply the amount determined in paragraph (c)(2)(i) (Step 1) by a fraction for which:" / "The numerator is the number of family members who have established eligible immigration status; and" / "The denominator is the total number of family members." — [snapshot `2026-08-28--24-cfr-5-520`](../../../sources/il/il_hcv/2026-08-28--24-cfr-5-520/content.md), accessed 2026-08-28
- Source: 24 CFR 5.630(a)(2) — "For the public housing program and the section 8 moderate rehabilitation or voucher programs, the PHA may establish a minimum rent of up to $50." — [snapshot `2026-08-26--24-cfr-5-630`](../../../sources/il/il_hcv/2026-08-26--24-cfr-5-630/content.md), accessed 2026-08-26
- Source: 24 CFR 5.630(b)(1), the mandatory hardship exemption that makes the floor unobservable — "The responsible entity must grant an exemption from payment of minimum rent if the family is unable to pay the minimum rent because of financial hardship, as described in the responsible entity's written policies." — [snapshot `2026-08-26--24-cfr-5-630`](../../../sources/il/il_hcv/2026-08-26--24-cfr-5-630/content.md), accessed 2026-08-26
- Source: 24 CFR 982.505(b)(1), the two payment-standard arms — "The payment standard amount for the family unit size; or" / "The payment standard amount for the size of the dwelling unit rented by the family." — [snapshot `2026-08-26--24-cfr-982-505`](../../../sources/il/il_hcv/2026-08-26--24-cfr-982-505/content.md), accessed 2026-08-26
- Source: Chicago Housing Authority HCV Administrative Plan § 6-II.A, the Moving to Work variation — "A minimum rent of $75 as allowed by CHA’s MTW Plan." — [snapshot `2026-08-26--cha-hcv-admin-plan-2026`](../../../sources/il/il_hcv/2026-08-26--cha-hcv-admin-plan-2026/content.md), accessed 2026-08-26
- Source: Housing Authority of Cook County HCV Administrative Plan § 6-III, Minimum Rent [24 CFR 5.630] — "The minimum rent for this locality is $50.00." — [snapshot `2026-08-29--hacc-hcv-admin-plan-2025`](../../../sources/il/il_hcv/2026-08-29--hacc-hcv-admin-plan-2025/content.md), accessed 2026-08-29
- Source: Peoria Housing Authority Administrative Plan — "The minimum rent for this locality is $50" — [snapshot `2026-08-28--peoria-hcv-admin-plan`](../../../sources/il/il_hcv/2026-08-28--peoria-hcv-admin-plan/content.md), accessed 2026-08-28
- Source: Peoria Housing Authority Administrative Plan § 5-II.B, the subsidy standard and its exceptions — "The PHA will assign one bedroom for each two persons within the household, except in" / "the following circumstances:" then "Persons 18 years of age or older of the opposite sex other than spouses and" / "cohabitating adults, will be allocated separate bedrooms." / "Children of the opposite sex over the age of six (6) will be allocated separate" / "bedrooms." / "Live-in aides will be allocated a separate bedroom." / "Single person families will be allocated one bedroom." — [snapshot `2026-08-28--peoria-hcv-admin-plan`](../../../sources/il/il_hcv/2026-08-28--peoria-hcv-admin-plan/content.md), accessed 2026-08-28
- Source: Housing Authority of Cook County HCV Administrative Plan, effective 1/1/2025, its current subsidy standard — "Head of Household (HOH) gets his/her own room and then 2 people per bedroom thereafter with" / "the exception of the following:" then "Married couples and domestic partners receive one bedroom", "Live-in aid (LIA) receives his/her own room", "Children of the opposite sex aged 6 and older receive their own room" and "Household members of a different generation, defined as an 18-year age difference," / "receive their own room" — [snapshot `2026-08-29--hacc-hcv-admin-plan-2025`](../../../sources/il/il_hcv/2026-08-29--hacc-hcv-admin-plan-2025/content.md), accessed 2026-08-29
- Source: Peoria Housing Authority, Public Notice — Proposed Payment Standard Changes (2025-09-04) — "These Payment Standards represent 110% of the FMR’s for Peoria County, IL." / "The attached payment standards will be put into effect beginning January 1st, 2026." with the one-bedroom standard "$899" — [snapshot `2026-08-28--peoria-payment-standards-fy2026`](../../../sources/il/il_hcv/2026-08-28--peoria-payment-standards-fy2026/content.md), accessed 2026-08-28
- Source: Housing Authority of Cook County Payment Standards, effective 2026-01-01, the ZIP-band schedule bounding the estimate. Its 26 bands run from A26 to Z26; the two-bedroom row spans $1,310 to $2,570. **Image-only snapshot** — the PDF is a scanned image with no text layer, so it carries no quotable text and is cited as corroboration only — [snapshot `2026-08-29--hacc-payment-standards-2026`](../../../sources/il/il_hcv/2026-08-29--hacc-payment-standards-2026/), accessed 2026-08-29
- Source: Peoria Housing Authority, HCV Payment Standards 2025 and Board Resolution 123024-01 (2024-12-30), adopting standards at 120 percent of the published FMR effective 2025-01-01. **Image-only snapshot** — the PDF is a scanned image with no text layer, so it carries no quotable text and is cited as corroboration only, not as a quoted authority — [snapshot `2026-08-28--peoria-hcv-payment-standards-2025`](../../../sources/il/il_hcv/2026-08-28--peoria-hcv-payment-standards-2025/), accessed 2026-08-28
- Source: 24 CFR 5.611(a), the un-indexed base amounts the published values adjust — "(1) $480 for each dependent" / "(2) $525 for any elderly family or disabled family" — [snapshot `2026-08-26--24-cfr-5-611`](../../../sources/il/il_hcv/2026-08-26--24-cfr-5-611/content.md), accessed 2026-08-26
- Source: 24 CFR 5.603, definition of *Dependent* — "A member of the family (which excludes foster children and foster adults) other than the family head or spouse who is under 18 years of age, or is a person with a disability, or is a full-time student." — [snapshot `2026-08-26--24-cfr-5-603`](../../../sources/il/il_hcv/2026-08-26--24-cfr-5-603/content.md), accessed 2026-08-26
- Source: 24 CFR 5.403, definitions of *Elderly family* and *Disabled family* — "Elderly family means a family whose head (including co-head), spouse, or sole member is a person who is at least 62 years of age." / "Disabled family means a family whose head (including co-head), spouse, or sole member is a person with a disability." — [snapshot `2026-08-26--24-cfr-5-403`](../../../sources/il/il_hcv/2026-08-26--24-cfr-5-403/content.md), accessed 2026-08-26
- Source: 24 CFR 982.402(b)(1), the federal frame the agency standards implement — "The subsidy standards must provide for the smallest number of bedrooms needed to house a family without overcrowding." — [snapshot `2026-08-26--24-cfr-982-402`](../../../sources/il/il_hcv/2026-08-26--24-cfr-982-402/content.md), accessed 2026-08-26
- Source: HUD FY2026 Schedule of Metropolitan & Non-Metropolitan Fair Market Rents, Illinois — column positions are bedroom counts, "METROPOLITAN FMR AREAS                                  0 BR    1 BR    2 BR   3 BR   4 BR   Counties of FMR AREA within STATE" — and the two areas modelled are "+Chicago-Joliet-Naperville, IL HMFA............... 1480         1581    1781   2294   2653   Cook, DuPage, Kane, Lake, McHenry, Will" and "Peoria, IL MSA.................................... 758           818    1039   1346   1449   Marshall, Peoria, Stark, Tazewell, Woodford" — [snapshot `2026-08-26--hud-fy2026-fmr-schedule`](../../../sources/il/il_hcv/2026-08-26--hud-fy2026-fmr-schedule/content.md), accessed 2026-08-26
- Source: HUD USER FY2026 Income Limits Summary, Chicago-Joliet-Naperville, IL HUD Metro FMR Area, the extremely low income limits the reference household sits at — "Extremely Low Income Limits ($)* 25,550 29,200 32,850 36,450 39,400 44,360 50,040 55,720" — [snapshot `2026-08-26--hud-fy2026-income-limits-chicago`](../../../sources/il/il_hcv/2026-08-26--hud-fy2026-income-limits-chicago/content.md), accessed 2026-08-26
- Justification: the subsidy is the gap between what a household can afford — the total tenant payment, which federal rule sets at roughly 30 percent of adjusted income — and the local cost of a modestly priced unit of the size the household needs. Both ends of that gap are published annually by HUD per county and bedroom count, so the formula is computed deterministically — but from proxy inputs (a statewide payment-standard convention, a bedroom-size convention, and the household's current rent standing in for a future assisted unit), so the output remains an estimate. The reference figure is corroborated independently: the Chicago Housing Authority reports paying $648 million in assistance annually across 47,000 assisted families, a blended average on the order of $14,000 per family per year across its voucher and project-based programs.
- Source: Chicago Housing Authority, HCV At a Glance (Spring 2025) — "PAID IN" / "ASSISTANCE" / "ANNUALLY" against "648m", and "FAMILIES" / "RECEIVING" / "ASSISTANCE" against "47k" — [snapshot `2026-08-26--cha-hcv-at-a-glance-2025`](../../../sources/il/il_hcv/2026-08-26--cha-hcv-at-a-glance-2025/content.md), accessed 2026-08-26

## Test Scenarios

**Coverage map**

| Rule / variation axis | Scenarios |
|---|---|
| Income within the very low income limit (criterion 1) | 1 (under), 2 (exactly at limit), 3 (one dollar over → fails the modelled gate) |
| Income limit is the household's own county's (criterion 1) | 4 (Peoria, under), 5 (Peoria, over the modelled gate — the same income is under Chicago's limit) |
| Income is summed across all members (criterion 1) | 2 (two earners), 1 (single earner) |
| Annual income excludes a minor's earned income (criterion 1, § 5.609(b)(3)) | 12 (17-year-old with wages) |
| Annual income caps a dependent full-time student's earned income (criterion 1, § 5.609(b)(14)) | 13 (student earning above the cap) |
| Annual income excludes workers' compensation (criterion 1, § 5.609(b)(5)) | 15 (household whose only other income is workers' compensation) |
| Annual income excludes a foster child's income, without shrinking the household (criterion 1, § 5.609(b)(8)) | 16 (foster child with unearned income, counted for household size and as a dependent) |
| Value axis — county / FMR area | 1–3, 6–10, 12–16 (Cook), 4, 5, 11, 17 (Peoria) |
| Value axis — bedroom count | 4, 10, 11 (1 person → 1BR), 14 (2 → 1BR), 13 (3 → 2BR), 1 (4 → 2BR), 6 (5 → 3BR), 7 (7 → 4BR), 17 (8 → 4BR) |
| Value axis — dependent deduction | 1 (2 minor dependents), 6 (3), 7 (5, one of them an adult full-time student), 16 (foster child still counted) |
| Value axis — elderly deduction | 10 (elderly, with income so the deduction moves the result), 4 (non-elderly counterpart) |
| Value axis — elderly or disabled family reached by disability | 14 (head with a disability), 10 (reached by age instead) |
| Value axis — dependent reached by disability | 14 (22-year-old with a disability), 7 (reached by full-time study), 1 (reached by age) |
| Value axis — gross-rent proxy relative to the payment standard | 1 (rent above → standard governs), 8 (rent below → rent governs), 9 (rent so low the computed payment falls to zero and the $1 floor applies) |
| Value axis — zero-income floor | 11 (no income and no deductible remainder, so TTP is $0) |
| TTP — 10 percent of monthly income prong | 17 (eight-person household where the 10 percent prong governs) |

**Known scenario gaps**

- Criterion 2 has no scenario. `household_size >= 1` is true of every screen the frontend can submit, so the criterion is not falsifiable and no scenario would fail if it were removed.
- Criterion 3 has no scenario. It is enforced by the program row's `legal_status_required` and the results-page citizenship filter, not by the calculator, so no calculator scenario can exercise it. It belongs to config acceptance testing instead.
- **Reference date.** Every scenario's ages are stated as of **2026-08-29**. Tests must freeze the screen reference date to that value; `HouseholdMember.age` is derived from `birth_year_month` against the current date, so an unpinned suite drifts silently as birthdays pass.
- No scenario exercises the asset or property restriction (data gap 4), because MFB applies no such gate. The removal of the former asset-boundary pair is deliberate: `household_assets` is not HUD's net family assets, so no boundary on it would have tested a real rule.
- No scenario exercises non-duplication. A household already holding a voucher is filtered centrally by the results layer's `already_has` flag, not by this calculator, so there is no calculator behaviour to test.
- No scenario exercises the pregnant-single-person subsidy rule. Under the `⌈n/2⌉` map one and two people both map to 1BR, so the rule is not falsifiable here; it would become testable only if the bedroom map changed.
- Data gaps 1 through 6 have no scenarios: each is a rule the screener cannot evaluate, and a test asserting the assumed branch would only restate the assumption. Data gap 1 in particular means no scenario exercises a household between the very low and low income limits. Scenario 3 places a household just inside that band and asserts only that the modelled gate rejects it — a calculator-behaviour claim. Whether such a household is *actually* eligible is unobservable here, and at the Chicago Housing Authority it generally is; that known false-negative class is the accepted cost recorded in data gap 1, not a result any scenario verifies.
- The 10-percent-of-monthly-income prong is reachable and Scenario 17 exercises it. It wins only where deductions exceed two thirds of annual income while that income is large enough for a tenth of it to clear 30 percent of the remainder — a window the largest modelled deduction of $4,050 opens at around $6,000 of annual income.
- Household size 6 has no scenario; the bedroom map is exercised at 1, 2, 3, 4, 5, 7 and 8, which covers every distinct bedroom count it produces.
- **Every scenario value is an MFB estimated value.** The payment standard and the bedroom size are estimation conventions, not agency rules — see Benefit Value. No scenario asserts what an agency would actually pay.
- **The agencies' sex-, relationship- and composition-based bedroom exceptions are unmodelable and deliberately uncovered.** No screener field records a member's sex or a live-in aide, so none of them can be evaluated from a screen; a test asserting the assumed branch would only restate the assumption. The error direction is known: the convention under-counts bedrooms and understates the subsidy.
- Both Cook County agencies give the head of household their own room before pairing, so each Cook County scenario's payment standard is one bedroom size lower than those agencies would assign at most household sizes. A disclosed error bound, not an open question; `household_size` alone cannot reproduce their formulation.
- **No scenario covers ZIP-level payment-standard variation, and none is required.** The convention applies one metro-wide figure, so there is no implemented branch to exercise. The variation is real — the FY2026 two-bedroom Small Area FMR is $1,320 in ZIP 60623 against $2,470 in ZIP 60622 — and is recorded in Benefit Value as an error bound, not a coverage gap.
- Income is stated as a monthly amount only in scenario 2. No scenario exercises weekly or biweekly frequency conversion.

### Scenario 1: Cook County family at the extremely low income limit — Eligible, $10,740
**What this tests**: the reference case — income well within the limit, and the full value computation with dependent deductions.
**Expected**: Eligible — $10,740 (voucher size 2BR for 4 people; payment standard $1,781; adjusted income $36,450 − 2 × $500 = $35,450, monthly $2,954.17; TTP = highest of $886, $304, $0 = $886; rent exceeds the payment standard so the standard governs; HAP = $1,781 − $886 = $895/month × 12)
**Household inputs**:
* Location: ZIP `60623`, county `Cook`
* Person 1: birth_year 1990, birth_month 3 (age 36), head of household, income: wages $36,450/year
* Person 2: birth_year 1991, birth_month 6 (age 35), spouse, no income
* Person 3: birth_year 2014, birth_month 4 (age 12), child, no income
* Person 4: birth_year 2018, birth_month 9 (age 7), child, no income
* Expenses: rent $1,900/month
* Household assets: $2,000
* Current benefits: none
**Why this matters**: kills a calculator that skips the $500 dependent deduction, or that uses gross rather than adjusted income for the 30 percent test.

---

### Scenario 2: Cook County family exactly at the income limit, income split across two earners and reported monthly — Eligible, $3,444
**What this tests**: three things at once — the income boundary is inclusive, income is summed across all members rather than read from the head, and a monthly-reported amount is converted before it meets an annual limit.
**Expected**: Eligible — $3,444 (two earners at $2,531.25/month each total $5,062.50/month = $60,750/year, exactly the very low income limit for a 4-person household in the Chicago-Joliet-Naperville HMFA; adjusted income $59,750, monthly $4,979.17; TTP = highest of $1,494, $506, $0 = $1,494; HAP = $1,781 − $1,494 = $287/month × 12)
**Household inputs**:
* Location: ZIP `60623`, county `Cook`
* Person 1: birth_year 1990, birth_month 3 (age 36), head of household, income: wages $2,531.25/month
* Person 2: birth_year 1991, birth_month 6 (age 35), spouse, income: wages $2,531.25/month
* Person 3: birth_year 2014, birth_month 4 (age 12), child, no income
* Person 4: birth_year 2018, birth_month 9 (age 7), child, no income
* Expenses: rent $1,900/month
* Household assets: $2,000
* Current benefits: none
**Why this matters**: kills a calculator using `<` instead of `<=` on the income limit, one reading only the head of household's income, and one comparing a monthly figure against an annual limit.

---

### Scenario 3: Cook County family one dollar over the modelled income gate — Ineligible under the modelled gate
**What this tests**: that the modelled statewide gate is applied at the right boundary — not that this household is ineligible for the program.
**Expected**: Ineligible under the modelled statewide 50 percent very low income gate (criterion 1 — $60,751 exceeds the $60,750 very low income limit for a 4-person household). This is a statement about the calculator, not about the household's federal eligibility: exceeding the very low income limit does not establish that a household fails all six routes in 24 CFR 982.201(b)(1), and at the Chicago Housing Authority a household at this income is admissible under the 80 percent limit. See Missing Eligibility Criteria 1.
**Household inputs**:
* Location: ZIP `60623`, county `Cook`
* Person 1: birth_year 1990, birth_month 3 (age 36), head of household, income: wages $60,751/year
* Person 2: birth_year 1991, birth_month 6 (age 35), spouse, no income
* Person 3: birth_year 2014, birth_month 4 (age 12), child, no income
* Person 4: birth_year 2018, birth_month 9 (age 7), child, no income
* Expenses: rent $1,900/month
* Household assets: $2,000
* Current benefits: none
**Why this matters**: kills a calculator that fails to apply the modelled gate at all, or that applies it with the wrong comparison — the boundary partner to Scenario 2. It deliberately does not assert that the household is ineligible for the Housing Choice Voucher program; the known false-negative band this scenario sits in is recorded in Missing Eligibility Criteria 1.

---

### Scenario 4: Single adult in Peoria County — Eligible, $4,416
**What this tests**: a second FMR area and the smallest bedroom size.
**Expected**: Eligible — $4,416 (voucher size 1BR for 1 person; Peoria, IL MSA payment standard $818; income $18,000 is within the $37,150 very low income limit for a 1-person household in that MSA; no dependents and not an elderly or disabled family, so adjusted income is $18,000, monthly $1,500; TTP = highest of $450, $150, $0 = $450; HAP = $818 − $450 = $368/month × 12)
**Household inputs**:
* Location: ZIP `61604`, county `Peoria`
* Person 1: birth_year 1996, birth_month 7 (age 30), head of household, income: wages $18,000/year
* Expenses: rent $900/month
* Household assets: $500
* Current benefits: none
**Why this matters**: kills a calculator that hardcodes Chicago's FMRs statewide, and one that maps a single-person household to zero bedrooms.

---

### Scenario 5: Single adult in Peoria County over that county's modelled income gate — Ineligible under the modelled gate
**What this tests**: that the income limit is looked up for the household's own county rather than a statewide figure — not that this household is ineligible for the program.
**Expected**: Ineligible under the modelled statewide 50 percent very low income gate (criterion 1 — $40,000 exceeds Peoria's $37,150 very low income limit for a 1-person household; the same income is within Chicago's $42,550). As in Scenario 3, this asserts calculator behaviour, not federal ineligibility — see Missing Eligibility Criteria 1.
**Household inputs**:
* Location: ZIP `61604`, county `Peoria`
* Person 1: birth_year 1996, birth_month 7 (age 30), head of household, income: wages $40,000/year
* Expenses: rent $900/month
* Household assets: $500
* Current benefits: none
**Why this matters**: kills a calculator that hardcodes Chicago's income limits statewide — the one mutation Scenario 4 cannot catch, because $18,000 is within both counties' limits. The county-specific lookup is what is under test; the ineligible outcome is a property of the modelled gate, not a policy finding.

---

### Scenario 6: Five-person Cook County household — Eligible, $16,152
**What this tests**: the three-bedroom band of the voucher size map.
**Expected**: Eligible — $16,152 (voucher size 3BR for 5 people; payment standard $2,294; income $39,400 is within the $65,650 very low income limit for a 5-person household; adjusted income $39,400 − 3 × $500 = $37,900, monthly $3,158.33; TTP = highest of $948, $328, $0 = $948; HAP = $2,294 − $948 = $1,346/month × 12)
**Household inputs**:
* Location: ZIP `60623`, county `Cook`
* Person 1: birth_year 1988, birth_month 3 (age 38), head of household, income: wages $39,400/year
* Person 2: birth_year 1989, birth_month 6 (age 37), spouse, no income
* Person 3: birth_year 2013, birth_month 4 (age 13), child, no income
* Person 4: birth_year 2016, birth_month 8 (age 10), child, no income
* Person 5: birth_year 2019, birth_month 5 (age 7), child, no income
* Expenses: rent $2,400/month
* Household assets: $2,000
* Current benefits: none
**Why this matters**: kills a bedroom map that assigns one bedroom per person, which would put this household at 5BR — a size the FMR table does not publish.

---

### Scenario 7: Seven-person Cook County household including an adult full-time student — Eligible, $17,568
**What this tests**: the top of the bedroom map, and that a dependent may be 18 or over.
**Expected**: Eligible — $17,568 (voucher size 4BR for 7 people; payment standard $2,653; income $50,040 is within the $75,350 very low income limit for a 7-person household; five dependents — four minor children and a 19-year-old full-time student — so adjusted income $50,040 − 5 × $500 = $47,540, monthly $3,961.67; TTP = highest of $1,189, $417, $0 = $1,189; HAP = $2,653 − $1,189 = $1,464/month × 12)
**Household inputs**:
* Location: ZIP `60623`, county `Cook`
* Person 1: birth_year 1985, birth_month 3 (age 41), head of household, income: wages $50,040/year
* Person 2: birth_year 1986, birth_month 6 (age 40), spouse, no income
* Person 3: birth_year 2007, birth_month 1 (age 19), child, full-time student, no income
* Person 4: birth_year 2012, birth_month 4 (age 14), child, no income
* Person 5: birth_year 2014, birth_month 8 (age 12), child, no income
* Person 6: birth_year 2017, birth_month 5 (age 9), child, no income
* Person 7: birth_year 2020, birth_month 2 (age 6), child, no income
* Expenses: rent $2,800/month
* Household assets: $2,000
* Current benefits: none
**Why this matters**: kills a bedroom map that caps below four bedrooms, and a dependent count that includes only members under 18 — which would drop the 19-year-old student and raise the tenant payment.

---

### Scenario 8: Cook County family renting below the payment standard — Eligible, $7,368
**What this tests**: the rent arm of the housing assistance payment formula.
**Expected**: Eligible — $7,368 (rent $1,500 is below the $1,781 payment standard, so rent governs; TTP $886 as in Scenario 1; HAP = $1,500 − $886 = $614/month × 12)
**Household inputs**:
* Location: ZIP `60623`, county `Cook`
* Person 1: birth_year 1990, birth_month 3 (age 36), head of household, income: wages $36,450/year
* Person 2: birth_year 1991, birth_month 6 (age 35), spouse, no income
* Person 3: birth_year 2014, birth_month 4 (age 12), child, no income
* Person 4: birth_year 2018, birth_month 9 (age 7), child, no income
* Expenses: rent $1,500/month
* Household assets: $2,000
* Current benefits: none
**Why this matters**: kills a calculator that computes the payment from the payment standard alone and never reads the household's rent — which returns $10,740 here, and passes every scenario where rent exceeds the standard. This tests the **MFB gross-rent proxy**, not an exact § 982.505 gross rent: the household's current rent stands in for a future assisted unit's rent to owner plus utility allowance, which MFB cannot know.

---

### Scenario 9: Cook County family whose rent is below its own tenant payment — Eligible, $1
**What this tests**: the payment floors rather than going negative, and that the floor is a visible one.
**Expected**: Eligible — $1 (rent $1,200 governs; TTP $1,494 as in Scenario 2 exceeds it, so the unfloored payment would be −$294/month; the computed annual value is $0, floored to **$1**). The household qualifies but nets no subsidy at this rent.
**Amended 2026-09-01, during implementation.** The value floor is $1, not $0. `Eligibility.value` drives the results page's own visibility filter — `filterPrograms.ts` drops any program whose value is not greater than zero — so returning $0 here would hide Section 8 from a household that genuinely qualifies for it, which is the opposite of the intended outcome. A nominal dollar keeps the program, its waitlist warning and its apply link in front of exactly the household the rule reaches. The floor applies only to a value the formula computed at zero; a value MFB could not compute at all (a HUD lookup failure) still returns $0, because hiding the program is the honest outcome there.
**Household inputs**:
* Location: ZIP `60623`, county `Cook`
* Person 1: birth_year 1990, birth_month 3 (age 36), head of household, income: wages $60,750/year
* Person 2: birth_year 1991, birth_month 6 (age 35), spouse, no income
* Person 3: birth_year 2014, birth_month 4 (age 12), child, no income
* Person 4: birth_year 2018, birth_month 9 (age 7), child, no income
* Expenses: rent $1,200/month
* Household assets: $2,000
* Current benefits: none
**Why this matters**: kills a calculator that reports a negative benefit, and one that returns an unfloored $0 and so silently drops an eligible household from results. As with the preceding scenario, the rent figure is the MFB gross-rent proxy rather than an exact § 982.505 gross rent.

---

### Scenario 10: Elderly single adult in Cook County with income — Eligible, $13,740
**What this tests**: the $550 elderly or disabled family deduction, in a case where it changes the result.
**Expected**: Eligible — $13,740 (voucher size 1BR; payment standard $1,581; the sole member is 62 or over so the household is an elderly family; adjusted income $18,000 − $550 = $17,450, monthly $1,454.17; TTP = highest of $436, $150, $0 = $436; HAP = $1,581 − $436 = $1,145/month × 12)
**Household inputs**:
* Location: ZIP `60623`, county `Cook`
* Person 1: birth_year 1956, birth_month 1 (age 70), head of household, income: wages $18,000/year
* Expenses: rent $1,700/month
* Household assets: $500
* Current benefits: none
**Why this matters**: kills a calculator that omits the $550 deduction, which would give a tenant payment of $450 and a value of $13,572. The tenant payment here is set by the 30 percent prong, so the result does not depend on which minimum rent the agency charges.

---

### Scenario 11: Elderly single adult in Peoria County with no income — Eligible, $9,816
**What this tests**: the zero-income floor — that a household with no income and no deductible remainder is assigned a total tenant payment of zero under the modelled $0 minimum rent, and receives the full payment standard.
**Expected**: Eligible — $9,816 (voucher size 1BR; Peoria payment standard $818; adjusted income $0 after the $550 deduction is floored at zero; 30 percent of adjusted income, 10 percent of monthly income and the modelled $0 minimum rent are all $0, so TTP = $0; HAP = $818 − $0 = $818/month × 12)
**Household inputs**:
* Location: ZIP `61604`, county `Peoria`
* Person 1: birth_year 1956, birth_month 1 (age 70), head of household, no income
* Expenses: rent $900/month
* Household assets: $0
* Current benefits: none
**Why this matters**: kills a calculator that lets the $550 deduction drive adjusted income negative — which would produce a negative tenant payment and a payment above the standard — and one that reinstates a non-zero minimum rent contrary to the modelled convention. Sited in Peoria rather than Chicago because agency minimum rents differ ($50 at Peoria and the Housing Authority of Cook County, $75 at the Chicago Housing Authority under Moving to Work), and the $0 convention departs from all of them; Peoria keeps the departure to a single documented figure.

---

### Scenario 12: Cook County family with a working 17-year-old — Eligible, $5,172
**What this tests**: that a child under 18 has their earned income excluded from annual income (24 CFR 5.609(b)(3)) — at an income where including it would flip the household to ineligible.
**Expected**: Eligible — $5,172 (the 17-year-old's $9,000 of wages is excluded, so countable annual income is $55,000, within the $60,750 very low income limit for a 4-person household; voucher size 2BR; payment standard $1,781; two dependents, so adjusted income $55,000 − 2 × $500 = $54,000, monthly $4,500.00; TTP = highest of $1,350, $458, $0 = $1,350; rent exceeds the payment standard so the standard governs; HAP = $1,781 − $1,350 = $431/month × 12)
**Household inputs**:
* Location: ZIP `60623`, county `Cook`
* Person 1: birth_year 1990, birth_month 3 (age 36), head of household, income: wages $55,000/year
* Person 2: birth_year 1991, birth_month 6 (age 35), spouse, no income
* Person 3: birth_year 2009, birth_month 4 (age 17), child, income: wages $9,000/year
* Person 4: birth_year 2018, birth_month 9 (age 7), child, no income
* Expenses: rent $1,900/month
* Household assets: $2,000
* Current benefits: none
**Why this matters**: kills a calculator that passes raw `calc_gross_income` to the income gate. That calculator sees $64,000, exceeds the $60,750 limit and reports **Ineligible** — an eligibility flip, not a value error. The 17-year-old still counts as a dependent for the deduction, which is a separate rule; a calculator that conflates the two drops the deduction as well.

---

### Scenario 13: Cook County family with a dependent full-time student earning above the exclusion cap — Eligible, $12,516
**What this tests**: that a dependent full-time student's earned income counts only up to the dependent-deduction amount, with the excess excluded (24 CFR 5.609(b)(14)) — distinguishing that from both counting all of it and excluding all of it.
**Expected**: Eligible — $12,516 (the 21-year-old full-time student earns $5,000; only the dependent-deduction amount of it counts, so countable annual income is $30,000 + $500 = $30,500, within the $54,700 very low income limit for a 3-person household; voucher size 2BR; payment standard $1,781; two dependents — the full-time student and the 14-year-old — so adjusted income $30,500 − 2 × $500 = $29,500, monthly $2,458.33; TTP = highest of $738, $254, $0 = $738; HAP = $1,781 − $738 = $1,043/month × 12)
**Household inputs**:
* Location: ZIP `60623`, county `Cook`
* Person 1: birth_year 1980, birth_month 5 (age 46), head of household, income: wages $30,000/year
* Person 2: birth_year 2005, birth_month 2 (age 21), child, full-time student, income: wages $5,000/year
* Person 3: birth_year 2012, birth_month 8 (age 14), child, no income
* Expenses: rent $1,900/month
* Household assets: $2,000
* Current benefits: none
**Why this matters**: the cap is a third behaviour, and this scenario separates all three. Counting the student's full $5,000 gives $11,172; excluding all of it gives $12,672; applying the cap gives $12,516. A calculator that reuses the minor-income rule for students, or that ignores the student rule entirely, lands on one of the other two figures.

---

### Scenario 14: Cook County household reaching both deductions through disability rather than age — Eligible, $12,084
**What this tests**: the two disability routes the other scenarios never exercise — a household qualifying as an elderly or disabled family through the head's disability rather than age, and an adult dependent qualifying through disability rather than being under 18 or a student.
**Expected**: Eligible — $12,084 (income $24,000 is within the $48,600 very low income limit for a 2-person household; voucher size 1BR; payment standard $1,581; the head is a person with a disability so the household is a disabled family, and the 22-year-old is a dependent by disability; adjusted income $24,000 − $500 − $550 = $22,950, monthly $1,912.50; TTP = highest of $574, $200, $0 = $574; HAP = $1,581 − $574 = $1,007/month × 12)
**Household inputs**:
* Location: ZIP `60623`, county `Cook`
* Person 1: birth_year 1981, birth_month 4 (age 45), head of household, has a disability, income: wages $24,000/year
* Person 2: birth_year 2004, birth_month 3 (age 22), child, has a disability, no income
* Expenses: rent $1,700/month
* Household assets: $500
* Current benefits: none
**Why this matters**: kills a calculator that tests the elderly-or-disabled family only by age — which drops the $550 and returns $11,916 — and one that counts only members under 18 as dependents, which drops the $500 and returns $11,940. Scenario 10 reaches the same deduction by age and Scenario 7 reaches the dependent definition through a full-time student, so neither catches these.

---

### Scenario 15: Cook County household whose second income is workers' compensation — Eligible, $15,372
**What this tests**: that workers' compensation is excluded from annual income (24 CFR 5.609(b)(5)), which the screener can observe through the `workersComp` income type.
**Expected**: Eligible — $15,372 (the head's $14,400 of workers' compensation is excluded, so countable annual income is the spouse's $21,000, within the $60,750 very low income limit for a 4-person household; voucher size 2BR; payment standard $1,781; two minor dependents, so adjusted income $21,000 − 2 × $500 = $20,000, monthly $1,666.67; TTP = highest of $500, $175, $0 = $500; the gross-rent proxy $1,900 exceeds the payment standard so the standard governs; HAP = $1,781 − $500 = $1,281/month × 12)
**Household inputs**:
* Location: ZIP `60623`, county `Cook`
* Person 1: birth_year 1988, birth_month 2 (age 38), head of household, income: workers' compensation $14,400/year
* Person 2: birth_year 1990, birth_month 9 (age 35), spouse, income: wages $21,000/year
* Person 3: birth_year 2013, birth_month 5 (age 13), child, no income
* Person 4: birth_year 2017, birth_month 11 (age 8), child, no income
* Expenses: rent $1,900/month
* Household assets: $2,000
* Current benefits: none
**Why this matters**: kills a calculator that sums every income type. Counting the workers' compensation gives countable income of $35,400, a tenant payment of $860 and a value of $11,052 — a $4,320 error on a household of four. This exclusion is **type-specific and not member-specific**: § 5.609(b)(5) excludes workers' compensation whoever receives it, so a global filter on the `workersComp` type expresses it correctly. The exclusions that genuinely require member-level evaluation are the age-, student- and relationship-dependent ones — Scenarios 12, 13 and 16.

---

### Scenario 16: Cook County household with a foster/kinship-care child receiving unearned income — Eligible, $17,772
**What this tests**: three things the foster convention decides at once — that a foster child's income is excluded (24 CFR 5.609(b)(8)), that the foster child is still counted in household size, and that the dependent deduction is still allowed for them. The child's income is **unearned** deliberately: a minor's *earned* income is already excluded by § 5.609(b)(3), so wages could not distinguish the foster rule from the minor rule, and a calculator that had never implemented § 5.609(b)(8) would still pass. Unearned income received on behalf of a dependent under 18 counts under § 5.609(a)(1), so only the foster exclusion removes it.
**This scenario asserts an MFB approximation, not the federal rule.** 24 CFR 5.603 defines a dependent as "A member of the family (which excludes foster children and foster adults) other than the family head or spouse who is under 18 years of age, or is a person with a disability, or is a full-time student" — federally, a foster child earns no dependent deduction. MFB's single `fosterChild` relationship value conflates foster placement with kinship care, and a kinship-care child *is* an ordinary dependent, so the spec resolves each sub-rule in the widening direction. The expected value below is therefore the correct output of the committed MFB convention, and deliberately not what a PHA would compute for a genuine foster placement.
**Expected**: Eligible — $17,772 (the foster child's $7,200 of child support is excluded, so countable annual income is $34,000, within the $65,650 very low income limit for a 5-person household; voucher size 3BR for 5 people; payment standard $2,294; three dependents — two minor children and the foster child — so adjusted income $34,000 − 3 × $500 = $32,500, monthly $2,708.33; TTP = highest of $813, $283, $0 = $813; HAP = $2,294 − $813 = $1,481/month × 12)
**Household inputs**:
* Location: ZIP `60623`, county `Cook`
* Person 1: birth_year 1985, birth_month 6 (age 41), head of household, income: wages $34,000/year
* Person 2: birth_year 1987, birth_month 3 (age 39), spouse, no income
* Person 3: birth_year 2011, birth_month 8 (age 15), child, no income
* Person 4: birth_year 2015, birth_month 1 (age 11), child, no income
* Person 5: birth_year 2010, birth_month 4 (age 16), foster child, income: child support $600/month
* Expenses: rent $2,400/month
* Household assets: $2,000
* Current benefits: none
**Why this matters**: each part of the convention fails to a distinct value, so the scenario pins all three. Counting the child support gives $15,612 — where a calculator implementing only the minor-earned-income exclusion lands, since § 5.609(b)(3) does not reach unearned income. Dropping the dependent deduction gives $17,628. Shrinking the household to four, which drops the voucher from 3BR to 2BR, gives $11,472.

---

### Scenario 17: Eight-person Peoria household where the 10-percent prong sets the tenant payment — Eligible, $16,776
**What this tests**: the 10-percent-of-monthly-income prong of the total tenant payment — the only arm of 24 CFR 5.628(a) no other scenario reaches — together with the largest household size and the top of the bedroom map.
**Expected**: Eligible — $16,776 (voucher size 4BR for 8 people; Peoria payment standard $1,449; income $6,060 is within the $70,050 very low income limit for an 8-person household in the Peoria MSA; the head is a person with a disability and there are seven dependents, so deductions are 7 × $500 + $550 = $4,050 and adjusted income is $6,060 − $4,050 = $2,010, monthly $167.50; the three prongs are 30 percent of monthly adjusted income $50.25, 10 percent of monthly income $50.50, and the modelled $0 minimum rent — the 10 percent prong governs, and half-up rounding gives TTP = $51; HAP = $1,449 − $51 = $1,398/month × 12)
**Household inputs**:
* Location: ZIP `61604`, county `Peoria`
* Person 1: birth_year 1979, birth_month 2 (age 47), head of household, has a disability, income: Social Security disability $505/month
* Person 2: birth_year 2009, birth_month 5 (age 17), child, no income
* Person 3: birth_year 2011, birth_month 1 (age 15), child, no income
* Person 4: birth_year 2013, birth_month 7 (age 13), child, no income
* Person 5: birth_year 2015, birth_month 3 (age 11), child, no income
* Person 6: birth_year 2017, birth_month 9 (age 8), child, no income
* Person 7: birth_year 2019, birth_month 6 (age 7), child, no income
* Person 8: birth_year 2021, birth_month 4 (age 5), child, no income
* Expenses: rent $1,600/month
* Household assets: $0
* Current benefits: none
**Why this matters**: a calculator implementing only the 30-percent prong returns $16,788, taking TTP as $50 rather than $51. A one-dollar-a-month gap is exactly why this branch survives untested without a dedicated scenario. It also covers the last household size the bedroom map produces, and confirms that seven dependents and the elderly-or-disabled allowance stack.

---

## Research Sources

| Snapshot | Tier | Title | URL | Retrieved |
|---|---|---|---|---|
| `2026-08-26--24-cfr-5-403` | 1 | 24 CFR 5.403 — Definitions (family, elderly family, disabled family) | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=5&section=5.403 | 2026-08-26 |
| `2026-08-26--24-cfr-5-603` | 1 | 24 CFR 5.603 — Definitions (annual income, adjusted income, TTP, family) | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=5&section=5.603 | 2026-08-26 |
| `2026-08-26--24-cfr-5-609` | 1 | 24 CFR 5.609 — Annual income | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=5&section=5.609 | 2026-08-26 |
| `2026-08-26--24-cfr-5-611` | 1 | 24 CFR 5.611 — Adjusted income | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=5&section=5.611 | 2026-08-26 |
| `2026-08-26--24-cfr-5-618` | 1 | 24 CFR 5.618 — Restrictions on assistance to families with assets | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=5&section=5.618 | 2026-08-26 |
| `2026-08-26--24-cfr-5-628` | 1 | 24 CFR 5.628 — Total tenant payment | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=5&section=5.628 | 2026-08-26 |
| `2026-08-26--24-cfr-5-630` | 1 | 24 CFR 5.630 — Minimum rent | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=5&section=5.630 | 2026-08-26 |
| `2026-08-26--24-cfr-888-113` | 1 | 24 CFR 888.113 — Fair market rents: methodology and Small Area FMR designation | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=888&section=888.113 | 2026-08-26 |
| `2026-08-26--24-cfr-982-201` | 1 | 24 CFR 982.201 — Eligibility and targeting | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=982&section=982.201 | 2026-08-26 |
| `2026-08-26--24-cfr-982-4` | 1 | 24 CFR 982.4 — Definitions (HCV program) | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=982&section=982.4 | 2026-08-26 |
| `2026-08-26--24-cfr-982-402` | 1 | 24 CFR 982.402 — Subsidy standards | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=982&section=982.402 | 2026-08-26 |
| `2026-08-26--24-cfr-982-503` | 1 | 24 CFR 982.503 — Payment standard areas, schedule, and amounts | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=982&section=982.503 | 2026-08-26 |
| `2026-08-26--24-cfr-982-505` | 1 | 24 CFR 982.505 — How to calculate housing assistance payment | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=982&section=982.505 | 2026-08-26 |
| `2026-08-26--24-cfr-982-553` | 1 | 24 CFR 982.553 — Denial of admission and termination for criminals and alcohol abusers | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=982&section=982.553 | 2026-08-26 |
| `2026-08-26--42-usc-1437a` | 1 | 42 U.S.C. 1437a — Rental payments; definitions (2024 edition, govinfo) | https://www.govinfo.gov/content/pkg/USCODE-2024-title42/pdf/USCODE-2024-title42-chap8-subchapI-sec1437a.pdf | 2026-08-26 |
| `2026-08-26--cha-apply-online-portal` | 2 | Chicago Housing Authority — Apply Online / waitlist application portal | https://applyonline.thecha.org/home | 2026-08-26 |
| `2026-08-26--cha-do-i-qualify` | 2 | Chicago Housing Authority — Do I Qualify for Housing? | https://www.thecha.org/do-i-qualify-housing | 2026-08-26 |
| `2026-08-26--cha-hcv-admin-plan-2026` | 2 | Chicago Housing Authority — Housing Choice Voucher Program Administrative Plan (FY2026, board-approved) | https://www.thecha.org/sites/default/files/2025-10/2026AdministrativePlan_10.25_BoardApprovedPolicies_0.pdf | 2026-08-26 |
| `2026-08-26--cha-hcv-at-a-glance-2025` | 2 | Chicago Housing Authority — HCV At a Glance (May 2025) | https://www.thecha.org/sites/default/files/2025-05/HCV-At-A-Glance-05.25_HCV.pdf | 2026-08-26 |
| `2026-08-26--cha-mtw-annual-plan-fy2026` | 2 | Chicago Housing Authority — FY2026 Moving to Work (MTW) Annual Plan, HUD-approved 2026-01-27 | https://www.thecha.org/sites/default/files/2026-02/FY2026-MTW-Annual-Plan-Hud-Approved_02.26_MTW.pdf | 2026-08-26 |
| `2026-08-26--cha-waitlist-status` | 2 | Chicago Housing Authority — Waitlist & Applicant Information | https://www.thecha.org/transparency-action-cha-data-impact-hub/waitlist | 2026-08-26 |
| `2026-08-26--fr-fy2026-fmr-notice` | 1 | 90 FR — Fair Market Rents for the Housing Choice Voucher Program … Fiscal Year 2026; Revised (2026-04-21) | https://www.govinfo.gov/content/pkg/FR-2026-04-21/pdf/2026-07741.pdf | 2026-08-26 |
| `2026-08-26--hacc-hcv-admin-plan-2022` | 2 | Housing Authority of Cook County — HCV Administrative Plan (2022) | https://thehacc.org/app/uploads/2021/07/Admin-Plan-2022-Post.pdf | 2026-08-26 |
| `2026-08-26--hud-fy2026-fmr-schedule` | 2 | HUD — FY2026 Schedule of Metropolitan & Nonmetropolitan Fair Market Rents | https://www.huduser.gov/portal/datasets/fmr/fmr2026/FY2026_FMR_Schedule.pdf | 2026-08-26 |
| `2026-08-26--hud-fy2026-income-limits-chicago` | 2 | HUD USER — FY2026 Income Limits Summary, Chicago-Joliet-Naperville, IL HUD Metro FMR Area (Cook County) | https://www.huduser.gov/datasets/il/il2026/summary?year=2026&reporttype=county&states=17&counties=1703199999&hmfa=METRO16980M16980 | 2026-08-26 |
| `2026-08-26--hud-fy2026-income-limits-peoria` | 2 | HUD USER — FY2026 Income Limits Summary, Peoria, IL MSA (Peoria County) | https://www.huduser.gov/datasets/il/il2026/summary?year=2026&reporttype=county&states=17&counties=1714399999 | 2026-08-26 |
| `2026-08-26--hud-housing-choice-vouchers-overview` | 2 | HUD — Housing Choice Vouchers (program overview and how to apply) | https://www.hud.gov/helping-americans/housing-choice-vouchers | 2026-08-26 |
| `2026-08-26--hud-il-pha-voucher-counts` | 2 | HUD Open Data — Public Housing Authorities layer, Illinois agencies administering Section 8 vouchers (name, code, voucher count, county) | https://services.arcgis.com/VTyQ9soqVukalItT/ArcGIS/rest/services/Public_Housing_Authorities/FeatureServer/0/query?where=STD_ST%3D%27IL%27+AND+SECTION8_UNITS_CNT%3E0&outFields=FORMAL_PARTICIPANT_NAME,PARTICIPANT_CODE,SECTION8_UNITS_CNT,CURCNTY_NM&orderByFields=SECTION8_UNITS_CNT+DESC&returnGeometry=false&f=json | 2026-08-26 |
| `2026-08-26--hud-open-data-catalog` | 2 | HUD Data Catalog — datasets published by HUD | https://data.hud.gov/datasets | 2026-08-26 |
| `2026-08-26--hud-pha-contacts` | 2 | HUD — PHA Contact Information (find your local public housing agency) | https://www.hud.gov/contactus/public-housing-contacts | 2026-08-26 |
| `2026-08-26--hud-safmr-required-metro-areas-2023` | 2 | HUD — Metropolitan Areas Required to Administer a Voucher Program Using Small Area Fair Market Rents (2023 designation) | https://archives.hud.gov/news/2023/List_Required_Metropolitan_Areas.pdf | 2026-08-26 |
| `2026-08-28--24-cfr-5-506` | 1 | 24 CFR 5.506 — General | https://www.ecfr.gov/api/versioner/v1/full/2026-08-26/title-24.xml?part=5&section=5.506 | 2026-08-28 |
| `2026-08-28--24-cfr-5-520` | 1 | 24 CFR 5.520 — Proration of assistance | https://www.ecfr.gov/api/versioner/v1/full/2026-08-26/title-24.xml?part=5&section=5.520 | 2026-08-28 |
| `2026-08-28--hacc-payment-standards-2025` | 2 | Housing Authority of Cook County — Payment Standards, Effective January 1, 2025 (ZIP-code rate bands) | https://thehacc.org/app/uploads/2024/12/Payment-Standards-Eff-1-2025.pdf | 2026-08-28 |
| `2026-08-28--hud-cy2026-inflationary-adjustments` | 1 | HUD — 2026 HUD Inflation-Adjusted Values (Table 1): Effective January 1, 2026 | https://www.huduser.gov/portal/sites/default/files/datasets/inflationary-adjustments/CY2026-Revised-Amounts-And-Passbook-Rate.pdf | 2026-08-28 |
| `2026-08-28--hud-pih-2026-15` | 1 | HUD Notice PIH 2026-15 — Compliance Date for Sections 102 and 104 of HOTMA | https://www.hud.gov/sites/default/files/hudclips/documents/PIH-2026-15.pdf | 2026-08-28 |
| `2026-08-28--peoria-annual-plan-fy2026` | 2 | Peoria Housing Authority — FY2026 Annual Plan | https://www.peoriahousing.org/news.aspx#2026-annual-plan | 2026-08-28 |
| `2026-08-28--peoria-hcv-admin-plan` | 2 | Peoria Housing Authority — Housing Choice Voucher Administrative Plan | https://www.peoriahousing.org/documents/HCV/adminPlan.pdf | 2026-08-28 |
| `2026-08-28--peoria-hcv-payment-standards-2025` | 2 | Peoria Housing Authority — HCV Payment Standards 2025 (120% of FMR) and Board Resolution 123024-01 | https://www.peoriahousing.org/documents/HCV/hcvPaymentStandards2025.pdf | 2026-08-28 |
| `2026-08-28--peoria-payment-standards-fy2026` | 2 | Peoria Housing Authority — Public Notice, Proposed Payment Standard Changes (FY2026, 110% of FMR, effective 2026-01-01) | https://www.peoriahousing.org/news.aspx#fy2026-payment-standards | 2026-08-28 |
| `2026-08-29--24-cfr-982-552` | 1 | 24 CFR 982.552 — PHA denial or termination of assistance for family | https://www.ecfr.gov/api/versioner/v1/full/2026-08-26/title-24.xml?part=982&section=982.552 | 2026-08-29 |
| `2026-08-29--hacc-hcv-admin-plan-2025` | 2 | Housing Authority of Cook County — HCV Administrative Plan, effective 1/1/2025 | https://thehacc.org/app/uploads/2024/03/Administrative-Plan-2025.pdf | 2026-08-30 |
| `2026-08-29--hacc-payment-standards-2026` | 2 | Housing Authority of Cook County — Payment Standards, Effective January 1, 2026 (ZIP-code rate bands) | https://thehacc.org/app/uploads/2025/11/Payment-Standard-Eff-1-2026.pdf | 2026-08-30 |
| `2026-08-30--24-cfr-5-612` | 1 | 24 CFR 5.612 — Assistance to students enrolled at an institution of higher education | https://www.ecfr.gov/api/versioner/v1/full/2026-08-26/title-24.xml?part=5&section=5.612 | 2026-08-30 |
