# Housing Choice Voucher Program (Section 8) (KS) — Program Spec

- **Program key**: `ks_hcv` — `programs/programs/white_labels/ks/hcv`, class `KsHcv`
- **Base federal program**: Housing Choice Voucher (Section 8), 24 CFR part 982
- **White label**: KS
- **Engine**: MFB Custom — Python
- **Geographic scope**: statewide
- **Policy/data year**: FY2026 (Fair Market Rents, income limits) and CY2026 (HUD inflation-adjusted amounts)
- **Added to MFB**: not yet implemented — no `programs/programs/white_labels/ks/hcv` at benefits-api `3b87b908`
- **Spec last updated**: 2026-09-09
- **Sources verified as of**: 2026-09-09

## Covered Eligibility Criteria

All three criteria must hold (plain conjunction).

1. **To be income-eligible the applicant must be a family in one of six admission categories, of which only one — a "very low income" family — carries no additional qualifying condition.**
   - Evaluation scope: `household`
   - Captured via: accessor `hud_client.get_screen_il_ami(screen, "50%", year)` (`integrations/clients/hud_income_limits/client.py`); countable income from `member.calc_gross_income("yearly", ["earned"|"unearned"], exclude=EXCLUDED_INCOME_TYPES)` aggregated per member; `household_size` (`Screen`, int), `county` (`Screen`, str), `zipcode` (`Screen`, str)
   - Code divergence: D1 — the calculator applies the very-low-income limit to every applicant, gating out households the five conditional categories would admit (see review-notes.md)
   - Implementation note: `"50%"` is one of three tiers the client accepts; the set is enforced at runtime by `SECTION8_CATEGORIES`, which raises `HudIncomeClientError` otherwise. The `year` argument takes the program year period, derived as the siblings do. No static income-limit table is checked in.
   - Source: 24 CFR 982.201(b)(1) — "To be income-eligible, the applicant must be a family in any of the following categories:" — [snapshot `2026-09-09--24-cfr-982-201`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-982-201/content.md), accessed 2026-09-09
   - Source: 24 CFR 982.201(b)(1)(i), the sole unconditional category — "(i) A “very low income” family;" — [snapshot `2026-09-09--24-cfr-982-201`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-982-201/content.md), accessed 2026-09-09
   - Source: 24 CFR 982.201(b)(1)(v), the moderate-income route and the displacement condition it carries — "(v) A low-income or moderate-income family that is displaced as a result of the prepayment of the mortgage or voluntary termination of an insurance contract on eligible low-income housing as defined in § 248.101 of this title;" — [snapshot `2026-09-09--24-cfr-982-201`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-982-201/content.md), accessed 2026-09-09
   - Source: 24 CFR 982.201(d)(1), defining the "continuously assisted" category at (b)(1)(ii) whose status MFB cannot observe — "An applicant is continuously assisted under the 1937 Housing Act if the family is already receiving assistance under any 1937 Housing Act program when the family is admitted to the voucher program." — [snapshot `2026-09-09--24-cfr-982-201`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-982-201/content.md), accessed 2026-09-09
   - Source: 24 CFR 248.101, definition of *Moderate Income Families*, the tier (v) reaches — "Families or persons whose incomes are between 80 percent and 95 percent of median area income, as determined by the Commissioner, with adjustments for smaller and larger families." — [snapshot `2026-09-09--24-cfr-248-101`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-248-101/content.md), accessed 2026-09-09
   - Source: Wichita Housing Authority HCV Administrative Plan, § 3-II.A, closing the (b)(1)(iii) PHA-discretion route — "The PHA has not established any additional categories of eligible low-income families." — [snapshot `2026-09-09--wichita-hcv-admin-plan-2026`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--wichita-hcv-admin-plan-2026/content.md), accessed 2026-09-09

   **FY2026 Very Low (50%) Income Limits, 1–8 person** — reference figures for the scenarios below; the calculator fetches them at runtime.

   | Area | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
   |---|---|---|---|---|---|---|---|---|
   | Wichita, KS HUD Metro FMR Area | 33,800 | 38,600 | 43,450 | 48,250 | 52,150 | 56,000 | 59,850 | 63,700 |
   | Topeka, KS MSA | 34,600 | 39,550 | 44,500 | 49,400 | 53,400 | 57,350 | 61,300 | 65,250 |
   | Kansas City, MO-KS HUD Metro FMR Area | 39,700 | 45,400 | 51,050 | 56,700 | 61,250 | 65,800 | 70,350 | 74,850 |

   - Source: HUD USER FY2026 Income Limits Summary, Wichita, KS HUD Metro FMR Area — "Very Low (50%) Income Limits ($) 33,800 38,600 43,450 48,250 52,150 56,000 59,850 63,700" — [snapshot `2026-09-09--hud-fy2026-income-limits-wichita`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--hud-fy2026-income-limits-wichita/content.md), accessed 2026-09-09
   - Source: HUD USER FY2026 Income Limits Summary, Topeka, KS MSA — "Very Low (50%) Income Limits ($) 34,600 39,550 44,500 49,400 53,400 57,350 61,300 65,250" — [snapshot `2026-09-09--hud-fy2026-income-limits-topeka`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--hud-fy2026-income-limits-topeka/content.md), accessed 2026-09-09
   - Source: HUD USER FY2026 Income Limits Summary, Kansas City, MO-KS HUD Metro FMR Area — "Very Low (50%) Income Limits ($) 39,700 45,400 51,050 56,700 61,250 65,800 70,350 74,850" — [snapshot `2026-09-09--hud-fy2026-income-limits-kansas-city`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--hud-fy2026-income-limits-kansas-city/content.md), accessed 2026-09-09

   **Income counted for this test is § 5.609(b)-adjusted, not raw gross.** Five exclusions are applied per member, in this order — (b)(3) and (b)(14) overlap and the order decides the result:
   1. Earned income of a member under 18 — excluded in full, uncapped (§ 5.609(b)(3)). The exclusion does not reach the head of household or the spouse of the head, whose income counts in full whatever their age (§ 5.609(a)(1)); IL carves them out the same way in `IlHcv._countable_earned_income`. `HEAD_RELATIONSHIPS` also carries `domesticPartner`, so MFB applies the carve-out to a co-head that (a)(1)'s text does not name — § 5.403 authorises the co-head substitution for the elderly/disabled flag, and it is carried here to a section that does not.
   2. Earned income of a dependent full-time student aged 18 or over, above $500/year (§ 5.609(b)(14)). The threshold is defined as the § 5.611 dependent deduction, so it tracks that figure rather than being chosen.
   3. A foster-care or kinship/guardianship care payment on the `fosterChild`-relationship member (§ 5.609(b)(4)). This has no mechanism distinct from exclusion 5 — (b)(8) already removes every dollar on that member — so it is listed for regulatory completeness rather than as separate logic, which Scenario 10 records against the payment itself.
   4. Income reported under `workersComp` (§ 5.609(b)(5)).
   5. All remaining income of a member whose `relationship` is `fosterChild` (§ 5.609(b)(8)).
   - Evaluation scope: `member`
   - Captured via: `birth_year_month` (`HouseholdMember`, date) via `calc_age()` against the pinned reference date; `student_full_time` (`HouseholdMember`, bool); `relationship` (`HouseholdMember`, str); accessor `member.calc_gross_income("yearly", [...], exclude=EXCLUDED_INCOME_TYPES)` with `EARNED_INCOME_TYPES = frozenset(("wages", "selfEmployment"))`
   - Code divergence: D2 — (b)(8) is applied to every `fosterChild`-relationship member, though the regulation reaches only a confirmed foster child (see review-notes.md)
   - Implementation note: must aggregate per member, never a single `Screen.calc_gross_income(..., exclude=[...])` — one shared exclude list strips income from the wrong members. Excluding a member's income never removes them from `household_size`, `family_size`, the dependent count or the bedroom lookup.
   - Source: 24 CFR 5.609(a)(1), scoping every exclusion below and carving out the head and spouse by age — "All amounts, not specifically excluded in paragraph (b) of this section, received from all sources by each member of the family who is 18 years of age or older or is the head of household or spouse of the head of household, plus unearned income by or on behalf of each dependent who is under 18 years of age" — [snapshot `2026-09-09--24-cfr-5-609`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-609/content.md), accessed 2026-09-09
   - Source: 24 CFR 5.609(b)(3) — "Earned income of children under the 18 years of age." — [snapshot `2026-09-09--24-cfr-5-609`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-609/content.md), accessed 2026-09-09
   - Source: 24 CFR 5.609(b)(14) — "Earned income of dependent full-time students in excess of the amount of the deduction for a dependent in § 5.611." — [snapshot `2026-09-09--24-cfr-5-609`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-609/content.md), accessed 2026-09-09
   - Source: 24 CFR 5.609(b)(4) — "Payments received for the care of foster children or foster adults, or State or Tribal kinship or guardianship care payments." — [snapshot `2026-09-09--24-cfr-5-609`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-609/content.md), accessed 2026-09-09
   - Source: 24 CFR 5.609(b)(5) — "Insurance payments and settlements for personal or property losses, including but not limited to payments through health insurance, motor vehicle insurance, and workers' compensation." — [snapshot `2026-09-09--24-cfr-5-609`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-609/content.md), accessed 2026-09-09
   - Source: 24 CFR 5.609(b)(8) — "Income of a live-in aide, foster child, or foster adult as defined in §§ 5.403 and 5.603, respectively." — [snapshot `2026-09-09--24-cfr-5-609`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-609/content.md), accessed 2026-09-09
   - Source: HUD 2026 Inflation-Adjusted Values (Table 1), giving the CY2026 amount for this exclusion — "24 CFR § 5.609(b)(14)    $500" — [snapshot `2026-09-09--hud-cy2026-inflation-adjusted-values`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--hud-cy2026-inflation-adjusted-values/content.md), accessed 2026-09-09

   **`family_size` equals `household_size`.** HUD distinguishes household from family — the family excludes live-in aides and foster children — but MFB's `fosterChild` enum cannot confirm the status, so no subtraction is applied. Wichita states the same asymmetry as policy.
   - Source: Form HUD-50058 Family Report Instruction Booklet, Section 3 General Rules — "Note that “household” and “family” are not" / "synonyms. The household includes everyone" / "who lives in the unit, while the family includes" / "all household members except live-in aides and" / "foster children and adults. The number of" / "household members is used to determine unit" / "size. The number and characteristics of family" / "members are used to calculate housing" / "subsidies and payments." (one passage; the booklet is set in two columns, so `pdftotext` interleaves unrelated right-column text between these line fragments) — [snapshot `2026-09-09--hud-50058-instruction-booklet-2024`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--hud-50058-instruction-booklet-2024/content.md), accessed 2026-09-09
   - Source: 24 CFR 5.603, definition of *Dependent* — "A member of the family (which excludes foster children and foster adults) other than the family head or spouse who is under 18 years of age, or is a person with a disability, or is a full-time student." — [snapshot `2026-09-09--24-cfr-5-603`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-603/content.md), accessed 2026-09-09
   - Source: Wichita Housing Authority HCV Administrative Plan, Using Income Limits for Eligibility [24 CFR 982.201 and Notice PIH 2023-27] — "Income and net family assets of household members are excluded when determining income" / "eligibility; however, household members are considered for purposes of unit size and subsidy" / "standards." — [snapshot `2026-09-09--wichita-hcv-admin-plan-2026`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--wichita-hcv-admin-plan-2026/content.md), accessed 2026-09-09

2. **To be eligible, an applicant must be a "family"; HUD's definition is open-ended and includes a single person.**
   - Evaluation scope: `household`
   - Captured via: `household_size` (`Screen`, int) — rule: ≥ 1
   - Implementation note: § 5.403's definition is "includes, but is not limited to", so `household_size >= 1` is a sufficient test. `birth_year_month`, `has_disability()` and `relationship` are read in Benefit Value, not here.
   - Source: 24 CFR 982.201(a), making "family" status one of the three basic admission requirements — "To be eligible, an applicant must be a “family;” must be income-eligible in accordance with paragraph (b) of this section and 24 CFR part 5, subpart F; and must be a citizen or a noncitizen who has eligible immigration status as determined in accordance with 24 CFR part 5, subpart E." — [snapshot `2026-09-09--24-cfr-982-201`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-982-201/content.md), accessed 2026-09-09
   - Source: 24 CFR 5.403, definition of *Family* — "Family includes, but is not limited to, the following, regardless of actual or perceived sexual orientation, gender identity, or marital status:" — the open-ended framing is why `household_size >= 1` is a sufficient test — [snapshot `2026-09-09--24-cfr-5-403`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-403/content.md), accessed 2026-09-09
   - Source: 24 CFR 5.403, definition of *Elderly family*, used by the Benefit Value deduction — "Elderly family means a family whose head (including co-head), spouse, or sole member is a person who is at least 62 years of age." — [snapshot `2026-09-09--24-cfr-5-403`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-403/content.md), accessed 2026-09-09
   - Source: 24 CFR 5.403, definition of *Disabled family*, the other half of the same Benefit Value deduction flag — "Disabled family means a family whose head (including co-head), spouse, or sole member is a person with a disability." — [snapshot `2026-09-09--24-cfr-5-403`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-403/content.md), accessed 2026-09-09

3. **Assistance is restricted to citizens and noncitizens with eligible immigration status; a mixed family with at least one eligible member may still be assisted.**
   - Evaluation scope: `config`
   - Captured via: config `legal_status_required` = `citizen`, `gc_5plus`, `gc_5less`, `refugee`, `otherWithWorkPermission` (five of the six user-selectable values; `non_citizen` correctly omitted)
   - Implementation note: scoped so a household selecting only ineligible statuses is excluded outright rather than prorated toward $0. Per-member status is not collected, so the gate is evaluated household-wide. `otherWithWorkPermission` is broader than HUD's enumerated list and is kept deliberately — removing it would create definite false negatives for qualifying parolees and trafficking-survivor visa holders, with no more precise bucket available.
   - Source: 24 CFR 5.506(a), the eligible-status restriction — "Financial assistance under a Section 214 covered program is restricted to:" / "(1) Citizens; or" / "(2) Noncitizens who have eligible immigration status under one of the categories set forth in Section 214 (see 42 U.S.C. 1436a(a))." — [snapshot `2026-09-09--24-cfr-5-506`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-506/content.md), accessed 2026-09-09
   - Source: 24 CFR 5.506(b)(1), the hard gate this criterion implements — "A family shall not be eligible for assistance unless every member of the family residing in the unit is determined to have eligible status, as described in paragraph (a) of this section, or unless the family meets the conditions set forth in paragraph (b)(2) of this section." — [snapshot `2026-09-09--24-cfr-5-506`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-506/content.md), accessed 2026-09-09
   - Source: 24 CFR 5.506(b)(2), the mixed-family exception — it is what relaxes (b)(1)'s every-member rule to the at-least-one-eligible-member gate this criterion implements — "Despite the ineligibility of one or more family members, a mixed family may be eligible for one of the three types of assistance provided in §§ 5.516 and 5.518." — [snapshot `2026-09-09--24-cfr-5-506`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-506/content.md), accessed 2026-09-09

## Missing Eligibility Criteria (Data Gaps)

1. **Five of the six § 982.201(b)(1) admission categories reach households above the very-low-income limit.**
   - Why: (ii) continuous 1937-Act assistance, (iii) PHA-adopted categories, (iv) HOPE 1/2 non-purchasing status, (v) displacement by mortgage prepayment or FHA termination, and (vi) § 248.173 non-purchasing status each turn on a fact no screener field captures. (iii) is closed in Wichita by PHA policy; (ii) is unobservable because MFB carries `base_program` `section_8` but no `public_housing`, and a household already reporting Section 8 is dropped from the results page rather than from the calculation — `eligibility_results` (`screener/views.py`) sets `already_has` from `screen.has_benefit(program.name_abbreviated)` after both calculator methods have run, on an exact `name_abbreviated` match rather than `base_program` `section_8`, and the frontend filters on that flag.
   - Handling: surfaced in program description (D1) — narrows results. This inverts MFB's usual inclusive convention, so the description carries the caveat in the narrowing direction and must be re-checked in the same pass if the income tier ever moves.
   - Source: 24 CFR 982.201(b)(1)(v), the moderate-income route and the displacement condition it carries — "(v) A low-income or moderate-income family that is displaced as a result of the prepayment of the mortgage or voluntary termination of an insurance contract on eligible low-income housing as defined in § 248.101 of this title;" — [snapshot `2026-09-09--24-cfr-982-201`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-982-201/content.md), accessed 2026-09-09
   - Source: 24 CFR 982.201(d)(1), defining the "continuously assisted" category at (b)(1)(ii) whose status MFB cannot observe — "An applicant is continuously assisted under the 1937 Housing Act if the family is already receiving assistance under any 1937 Housing Act program when the family is admitted to the voucher program." — [snapshot `2026-09-09--24-cfr-982-201`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-982-201/content.md), accessed 2026-09-09

2. **A PHA must deny admission for specified criminal activity and may deny for other drug-related, violent or alcohol-related activity.**
   - Why: no screener field collects criminal history, drug use, or alcohol-related conduct.
   - Handling: `assumed-met` — widens results. Not surfaced in the description: applies to virtually every applicant regardless of program.
   - Source: 24 CFR 982.553(a)(1)(ii)(A) and (C), the mandatory bars — "The PHA must establish standards that prohibit admission if:" / "(A) The PHA determines that any household member is currently engaging in illegal use of a drug;" / "(C) Any household member has ever been convicted of drug-related criminal activity for manufacture or production of methamphetamine on the premises of federally assisted housing." — [snapshot `2026-09-09--24-cfr-982-553`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-982-553/content.md), accessed 2026-09-09
   - Source: 24 CFR 982.552(c)(2)(i), the mitigating-circumstances layer that applies across Criteria 4–6 — "In determining whether to deny or terminate assistance because of action or failure to act by members of the family:" — [snapshot `2026-09-09--24-cfr-982-552`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-982-552/content.md), accessed 2026-09-09
   - Source: 24 CFR 982.552(c)(1)(x), the tenth denial ground, which routes this conduct to § 982.553 rather than setting its own standard — "(x) If the family has been engaged in criminal activity or alcohol abuse as described in § 982.553." — [snapshot `2026-09-09--24-cfr-982-552`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-982-552/content.md), accessed 2026-09-09

3. **A PHA may deny admission for a debt to any PHA, a prior termination, fraud, unreimbursed HAP damages, a breached repayment agreement, or abusive behavior toward PHA staff.**
   - Why: no screener field collects any of these; they are verified from PHA records and HUD's EIV system at application.
   - Handling: `assumed-met` — widens results. Not surfaced in the description: legally dense, and raising it pre-screening risks reading as accusatory. Ground (i), violation of a family obligation "including PHA-adopted Administrative Plan screening", is omitted from the rule above for two reasons: it is a locally-set standard rather than one this spec can state, and § 982.551's family obligations are administrative compliance rather than a substantive fact about the household. Ground (ii) is data gap 4 and ground (x) is data gap 2; ground (ix), a welfare-to-work family's failure to meet its WTW obligations, applies only after admission and is not an admission rule.
   - Source: 24 CFR 982.552(c)(1), the discretionary grounds enumerated above — "The PHA may at any time deny program assistance for an applicant, or terminate program assistance for a participant, for any of the following grounds:" — [snapshot `2026-09-09--24-cfr-982-552`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-982-552/content.md), accessed 2026-09-09

4. **A PHA must deny admission for three years after eviction from federally-assisted housing for drug-related criminal activity, and may deny for any eviction within five years.**
   - Why: no screener field collects eviction history; both waivers (completed supervised rehabilitation, changed circumstances) are equally unobservable.
   - Handling: `assumed-met` — widens results. Not surfaced in the description: sensitive personal history.
   - Source: 24 CFR 982.553(a)(1)(i), the mandatory three-year drug-eviction bar and its two waivers — "The PHA must prohibit admission to the program of an applicant for three years from the date of eviction if a household member has been evicted from federally assisted housing for drug-related criminal activity." / "(A) That the evicted household member who engaged in drug-related criminal activity has successfully completed a supervised drug rehabilitation program approved by the PHA; or" / "(B) That the circumstances leading to eviction no longer exist" — [snapshot `2026-09-09--24-cfr-982-553`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-982-553/content.md), accessed 2026-09-09

5. **A student enrolled in higher education, under 24, unmarried, without a dependent child and not a veteran is barred from Section 8 assistance unless disabled, assisted as of 30 November 2005, individually income-eligible, or with income-eligible parents.**
   - Why: § 5.612 is seven conjunctive conditions, (a)–(g). Conditions (f) and (g) turn on disability-plus-2005-assistance history and parental income eligibility — neither is collected. `student`, `student_full_time` and `student_job_training_program` exist but cannot establish (f) or (g).
   - Handling: `assumed-met` — no student gate is applied at all, rather than a partial one. Widens results. Not surfaced in the description: narrow edge case.
   - Source: 24 CFR 5.612, opening restriction and the two negative conditions — "No assistance shall be provided under section 8 of the 1937 Act to any individual who:" / "(f) Is not a person with disabilities, as such term is defined in section 3(b)(3)(E) of the 1937 Act and was not receiving assistance under section 8 of the 1937 Act as of November 30, 2005; and" / "(g) Is not otherwise individually eligible, or has parents who, individually or jointly, are not eligible on the basis of income to receive assistance under section 8 of the 1937 Act." — [snapshot `2026-09-09--24-cfr-5-612`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-612/content.md), accessed 2026-09-09

6. **Net family assets over the CPI-adjusted threshold, or ownership of suitable residential property, make a family ineligible.**
   - Why: `household_assets` (`Screen`) is a single undifferentiated total, not HUD's "net family assets" — a defined term excluding retirement accounts, necessary personal property, unsellable real property, FSS accounts and recent tax refunds. There is no property-ownership field: `is_home_owner`/`is_renter` are on `EnergyCalculatorScreen`, not `Screen`. HUD Notice PIH 2026-15 defers enforcement of HOTMA §§ 102/104 to 2027-01-01, so the restriction is codified but not universally live in 2026.
   - Handling: `assumed-met` — no asset or property gate applied. Widens results. Surfaced in the description: it says an asset or homeownership limit may apply. IL applies no gate for the same reason; WA and TX both gate `asset_limit = 100_000` against the raw total, which compares two different quantities.
   - Source: HUD Notice PIH 2026-15 — "This notice announces that, starting on January 1, 2027, HUD will enforce compliance" / "with sections 102 and 104 of the Housing Opportunity Through Modernization Act of" / "2016 (HOTMA) for all public housing agencies (PHAs), except PHAs who participate in" / "the Moving to Work (MTW) demonstration and PHAs who currently exclusively use the" / "HUD Family Reporting Software (FRS)." — [snapshot `2026-09-09--hud-pih-2026-15`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--hud-pih-2026-15/content.md), accessed 2026-09-09
   - Source: 24 CFR 5.618(a)(1)(i), the statutory base figure the CY2026 amount adjusts — "The family's net assets (as defined in § 5.603) exceed $100,000, which amount will be adjusted annually by HUD in accordance with the Consumer Price Index for Urban Wage Earners and Clerical Workers" — [snapshot `2026-09-09--24-cfr-5-618`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-618/content.md), accessed 2026-09-09
   - Source: HUD 2026 Inflation-Adjusted Values (Table 1), the CY2026 adjusted amount — "restriction on net" / "$105,574" — and the instruction that non-complying agencies must not apply it — "Note: If your agency/property/program administrator is not yet complying with Sections 102 and 104 of HOTMA, you" / "will not utilize this table." — [snapshot `2026-09-09--hud-cy2026-inflation-adjusted-values`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--hud-cy2026-inflation-adjusted-values/content.md), accessed 2026-09-09

7. **§ 5.609(b)(8) excludes the income of a foster child as defined in §§ 5.403 and 5.603 — a confirmed placement.**
   - Why: `relationship` value `fosterChild` is labelled "Foster Child / Kinship Care" and covers both formal state placement and informal kinship care, which HUD treats differently. `HouseholdMember.was_in_foster_care` does not close this: it records "ever in foster care, even briefly" about the member themselves, is nullable, and acting on it would push toward exclusion.
   - Handling: the exclusion is applied to every `fosterChild` member (D2) and the member is retained in `family_size` and the dependent count — widens results in both directions the asymmetry can move.
   - Source: 24 CFR 5.609(b)(8) — "Income of a live-in aide, foster child, or foster adult as defined in §§ 5.403 and 5.603, respectively." — [snapshot `2026-09-09--24-cfr-5-609`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-609/content.md), accessed 2026-09-09
   - Source: 24 CFR 5.603, definition of *Dependent* — "A member of the family (which excludes foster children and foster adults) other than the family head or spouse who is under 18 years of age, or is a person with a disability, or is a full-time student." — [snapshot `2026-09-09--24-cfr-5-603`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-603/content.md), accessed 2026-09-09

8. **Several § 5.609(b) exclusions cannot be reached by the screener's income taxonomy.**
   - Why: (b)(4) foster/kinship care payments have no dedicated income type, so they are excluded only when reported *on* the foster member rather than on the caregiver who receives them; (b)(15) adoption assistance has no income type and no adopted-child field; (b)(28) counts *net* self-employment income where `selfEmployment` collects gross; (b)(26) excludes nonperiodic retirement withdrawals but every frequency option is periodic; (b)(24) excludes milestone gifts and tax refunds where `gifts` is one undifferentiated periodic stream; (b)(17) excludes VA aid-and-attendance where `veteran` cannot separate it from an ordinary pension; (b)(9) and (b)(16) have no dedicated types.
   - Handling: `assumed-met` — none are applied; the income is counted as reported. Narrows results in every case. All 28 § 5.609(b) exclusions were walked; those not listed here or applied above cannot be carried by any screener income type at all, so there is no risk of counting them.
   - Source: 24 CFR 5.609(b)(15) — "Adoption assistance payments for a child in excess of the amount of the deduction for a dependent in § 5.611." — [snapshot `2026-09-09--24-cfr-5-609`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-609/content.md), accessed 2026-09-09
   - Source: 24 CFR 5.609(b)(28), on gross versus net self-employment income — "Gross income a family member receives through self-employment or operation of a business; except that the following shall be considered income to a family member:" / "(i) Net income from the operation of a business or profession." — [snapshot `2026-09-09--24-cfr-5-609`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-609/content.md), accessed 2026-09-09
   - Source: 24 CFR 5.609(b)(26), whose carve-back is why `pension` is correctly counted — "Income received from any account under a retirement plan recognized as such by the Internal Revenue Service, including individual retirement arrangements (IRAs), employer retirement plans, and retirement plans for self-employed individuals; except that any distribution of periodic payments from such accounts shall be income at the time they are received by the family." — [snapshot `2026-09-09--24-cfr-5-609`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-609/content.md), accessed 2026-09-09
   - Source: 24 CFR 5.609(b)(24), the nonrecurring-income exclusion and its gift limb — "Gifts for holidays, birthdays, or other significant life events or milestones" — [snapshot `2026-09-09--24-cfr-5-609`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-609/content.md), accessed 2026-09-09

9. **§ 5.617 requires an earned-income disallowance for a qualified family that includes a person with disabilities.**
   - Why: the population is identifiable — `has_disability()` (`HouseholdMember`) ORs `disabled`, `visually_impaired` and `long_term_disability` — but the qualifying event is not. § 5.617(b) reaches a family only where a disabled member's income rises after a year or more of unemployment, during a self-sufficiency or job-training programme, or within six months of TANF. `student_job_training_program` is a student flag, not this, and `cashAssistance` carries no start or end date. The disallowance also needs a pre-increase baseline income, which nothing supplies.
   - Handling: `assumed-met` — omitted. Narrows results (counts income a PHA would disregard). § 5.617(b) additionally reaches only a family already assisted under HOME, HOPWA, SHP or HCV; MFB has no field for the first three and suppresses the fourth, so the affected population is one MFB largely does not screen.
   - Source: 24 CFR 982.201(b)(3), mandating the EID within the income determination and scoping it to families including a person with disabilities — "In determining annual income of an applicant family that includes a person with disabilities, the determination must include the disallowance of increase in annual income as provided in 24 CFR 5.617, if applicable." — [snapshot `2026-09-09--24-cfr-982-201`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-982-201/content.md), accessed 2026-09-09
   - Source: 24 CFR 5.617(a) and (b), the four applicable programs and the qualified-family definition that scopes them — "The disallowance of earned income provided by this section is applicable only to the following programs: HOME Investment Partnerships Program (24 CFR part 92); Housing Opportunities for Persons with AIDS (24 CFR part 574); Supportive Housing Program (24 CFR part 583); and the Housing Choice Voucher Program (24 CFR part 982)." / "Qualified family. A family residing in housing assisted under one of the programs listed in paragraph (a) of this section or receiving tenant-based rental assistance under one of the programs listed in paragraph (a) of this section." — [snapshot `2026-09-09--24-cfr-5-617`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-617/content.md), accessed 2026-09-09
   - Source: 24 CFR 5.617(b), the three qualifying routes and their unobservable conditions — "Whose annual income increases as a result of employment of a family member who is a person with disabilities and who was previously unemployed for one or more years prior to employment;" / "during participation in any economic self-sufficiency or other job training program;" / "during or within six months after receiving assistance, benefits or services under any state program for temporary assistance for needy families" — [snapshot `2026-09-09--24-cfr-5-617`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-617/content.md), accessed 2026-09-09
   - Source: Wichita Housing Authority HCV Administrative Plan, § 6-I.E, confirming the local PHA applies it — "6-I.E. EARNED INCOME DISALLOWANCE FOR PERSONS WITH DISABILITIES" — [snapshot `2026-09-09--wichita-hcv-admin-plan-2026`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--wichita-hcv-admin-plan-2026/content.md), accessed 2026-09-09

10. **§§ 5.609(a)(2) and (b)(1) impute a return on net family assets above the CY2026 threshold.**
    - Why: actual asset income is already captured through the `investment` and `rental` income types and is counted. Only the imputed return on non-income-producing assets is missed, which is immaterial at passbook rates.
    - Handling: `assumed-met` — the imputation is omitted. Narrows results. The trigger is § 5.609's own threshold — $50,000 as codified, $52,787 for CY2026 — and not § 5.618's asset limit, which is a different rule at a different amount (data gap 6). The imputation therefore reaches about twice the households the asset limit does.
   - Source: 24 CFR 5.609(a)(2), the imputation rule and its threshold — "When the value of net family assets exceeds $50,000 (which amount HUD will adjust annually in accordance with the Consumer Price Index for Urban Wage Earners and Clerical Workers) and the actual returns from a given asset cannot be calculated, imputed returns on the asset based on the current passbook savings rate, as determined by HUD." — [snapshot `2026-09-09--24-cfr-5-609`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-609/content.md), accessed 2026-09-09
   - Source: 24 CFR 5.609(b)(1), the mirror exclusion below the same threshold — "Any imputed return on an asset when net family assets total $50,000 or less" — [snapshot `2026-09-09--24-cfr-5-609`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-609/content.md), accessed 2026-09-09
   - Source: HUD 2026 Inflation-Adjusted Values (Table 1), the CY2026 imputation threshold against the sections it adjusts — distinct from the § 5.618(a)(1)(i) asset limit of $105,574 in the row above it — "Threshold above" / "which imputed" / "returns must be" / "24 CFR §§ 5.609(a)(2)" / "and (b)(1)" / "$52,787" (one table row; the columns interleave in `pdftotext`) — [snapshot `2026-09-09--hud-cy2026-inflation-adjusted-values`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--hud-cy2026-inflation-adjusted-values/content.md), accessed 2026-09-09

## Priority Criteria

Local preferences affect waitlist position, not eligibility. § 982.207 sets them PHA-by-PHA through each Administrative Plan, so none is a statewide entitlement.

- Displaced by government action (10 pts, Wichita) — captured: description text
  - Program description tie-back: "Some move certain households up the list, such as people who are homeless or displaced."
- Literally or formerly homeless, re-entry, or FSS participant (1 pt, limited 20% referral, Wichita) — captured: description text
  - Program description tie-back: "Some move certain households up the list, such as people who are homeless or displaced."
- Residency in the PHA's jurisdiction (1 pt, Wichita) — captured: not captured (flag)
  - Program description tie-back: "Ask your local housing authority which priorities it uses." `zipcode` and `county` are collected but cannot map to a PHA jurisdiction.
- Emergency Housing Voucher transition; Foster Youth to Independence Bridge (10 pts each, Wichita) — captured: not captured (flag)
  - Program description tie-back: none — no screener signal for either.
- Elderly, displaced, or homeless single person or person with a disability; disabled family; working family; DV/dating-violence/sexual-assault/stalking survivor — captured: not captured (flag)
  - Program description tie-back: none. These are HUD's permissible illustrative categories under § 982.207(b), not adopted Kansas preferences; displacement, homelessness, work status and survivor status have no screener field.
- COFA citizens are entitled by regulation to receive local preferences — captured: not captured (flag)
  - Program description tie-back: none needed. Unlike the PHA-adopted preferences above this one is conferred federally, but no legal-status option identifies COFA status and `otherWithWorkPermission` would not distinguish it.
  - Source: 24 CFR 982.207(b)(1), confirming residency preferences are PHA-adopted and geographically scoped rather than uniform — "A residency preference is a preference for admission of persons who reside in a specified geographic area (“residency preference area”). A county or municipality may be used as a residency preference area." — [snapshot `2026-09-09--24-cfr-982-207`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-982-207/content.md), accessed 2026-09-09
  - Source: Wichita Housing Authority HCV Administrative Plan, § 4-III.C (p. 4-9), the adopted local preferences — "PHA Policy The PHA will use the following local preferences:" / "1. Displaced by government action (10 pts)" / "3. The PHA will offer a limited (20%) referral-based preference to individuals and families" / "(1pt): literally homeless, formerly homeless under a move-on strategy, those that have" / "completed a re-entry transitional housing program; or those FYI from FSS." / "additional preference point. (1pt)." / "preference points on the Waiting List. (10pts)." / "involved in or graduated from the FSS program. (10pts)" — [snapshot `2026-09-09--wichita-hcv-admin-plan-2026`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--wichita-hcv-admin-plan-2026/content.md), accessed 2026-09-09
  - Source: 24 CFR 5.506(c), the preference entitlement — "Citizens of the Republic of Marshall Islands, the Federated States of Micronesia, and the Republic of Palau who are eligible for assistance under paragraph (a)(2) of this section are entitled to receive local preferences for housing assistance" — [snapshot `2026-09-09--24-cfr-5-506`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-506/content.md), accessed 2026-09-09

Special admission under § 982.203 lets a PHA admit HUD-targeted families ahead of the waitlist. It governs admission order rather than eligibility and depends on PHA-specific funding designations the screener cannot observe.

## Benefit Value

- Value: `max(1, monthly HAP × 12)` where monthly HAP = `max(0, min(payment_standard, gross_rent_proxy) − TTP)` — an estimated prospective subsidy, not a predicted HAP for a specific unit
- `value_format`: `estimated_annual` (annualized)
- Variation axes: county/ZIP payment standard · bedroom size (household size) · household income · dependent count · elderly-or-disabled family status · reported rent — each appears in Test Scenarios
- Justification: the PHA pays the Housing Assistance Payment directly to the landlord each month, so the household's benefit is the annual monetary equivalent of that payment. The payment standard is modelled at 100% of the applicable FMR or SAFMR; a PHA may set its own between 90% and 110% without HUD approval, so the figure is an estimate of a range MFB cannot resolve without knowing the administering PHA.

**Payment standard.** 100% of the FY2026 FMR, or the ZIP-level Small Area FMR where HUD designates the metro mandatory-SAFMR. Wichita, KS HMFA and Kansas City, MO-KS HMFA are both marked `+` in the FY2026 schedule; Topeka, KS MSA is not and uses the area FMR.

`MANDATORY_SAFMR_AREA_NAMES` in `hud_client` does not currently include Kansas. **Committed implementation**: add `Wichita, KS HUD Metro FMR Area` and `Kansas City, MO-KS HUD Metro FMR Area`. Both strings are confirmed against two independent published HUD sources — the FY2026 SAFMR file and the FY2026 Income Limits summary pages — but the runtime comparison is exact string equality against `area_name` from the HUD FMR API response, which is neither of those files, so confirm them against a live API response before release.

| Bedroom size | Wichita ZIP 67202 (SAFMR) | Kansas City ZIP 66103 (SAFMR) | Topeka (area FMR) |
|---|---|---|---|
| 0BR | $840 | $1,080 | $792 |
| 1BR | $910 | $1,180 | $820 |
| 2BR | $1,180 | $1,340 | $1,057 |
| 3BR | $1,550 | $1,750 | $1,392 |
| 4BR | $1,920 | $2,080 | $1,411 |

Kansas City's area-wide FY2026 FMR ($1,095 / $1,197 / $1,358 / $1,769 / $2,103) must not be used for a mandatory-SAFMR ZIP.

  - Source: 24 CFR 888.113(c)(3), making SAFMR use mandatory rather than optional in a designated area — "If a metropolitan area meets the criteria of paragraph (c)(1) of this section, Small Area FMRs will apply to the metropolitan area and all PHAs administering HCV programs in that area will be required to use Small Area FMRs." — [snapshot `2026-09-09--24-cfr-888-113`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-888-113/content.md), accessed 2026-09-09
  - Source: 24 CFR 888.113(c)(5), confirming the designation is scoped to tenant-based HCV assistance — the tenure this estimate models — "Small Area FMRs only apply to tenant-based assistance under the HCV program." — [snapshot `2026-09-09--24-cfr-888-113`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-888-113/content.md), accessed 2026-09-09
  - Source: HUD HCV Program Guidebook, Payment Standards (June 2025, the HOTMA-updated edition), restating the same ZIP-level selection criterion — "areas (ZIP Codes) where the SAFMR is more than 110 percent of the metropolitan FMR area;" — [snapshot `2026-09-09--hud-hcv-guidebook-payment-standards`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--hud-hcv-guidebook-payment-standards/content.md), accessed 2026-09-09
  - Source: 24 CFR 982.503(c), the basic range — "A basic range payment standard amount is any dollar amount that is in the range from 90 percent up to 110 percent of the published FMR for a unit size." — [snapshot `2026-09-09--24-cfr-982-503`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-982-503/content.md), accessed 2026-09-09
  - Source: 24 CFR 982.503(d), amounts above the basic range — "An exception payment standard amount is a dollar amount that exceeds 110 percent of the published FMR." — [snapshot `2026-09-09--24-cfr-982-503`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-982-503/content.md), accessed 2026-09-09
  - Source: HUD FY2026 FMR Schedule, the mandatory-SAFMR `+` designations and Topeka's absence of one — "+Wichita, KS HMFA" / "+Kansas City, MO-KS HMFA" / "Topeka, KS MSA" — [snapshot `2026-09-09--hud-fy2026-fmr-schedule`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--hud-fy2026-fmr-schedule/content.md), accessed 2026-09-09
  - Source: HUD FY2026 Small Area FMRs, ZIP 67202, the full published row (0BR/1BR/2BR/3BR/4BR, each followed by its 90% and 110% payment-standard columns) — "67202 METRO48620M48620 Wichita, KS HUD Metro FMR Area 840 756 924 910 819 1001 1180 1062 1298 1550 1395 1705 1920 1728 2112" — [snapshot `2026-09-09--hud-fy2026-safmrs`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--hud-fy2026-safmrs/content.md), accessed 2026-09-09
  - Source: HUD FY2026 Small Area FMRs, ZIP 66103, the full published row — "66103 METRO28140M28140 Kansas City, MO-KS HUD Metro FMR Area 1080 972 1188 1180 1062 1298 1340 1206 1474 1750 1575 1925 2080 1872 2288" — [snapshot `2026-09-09--hud-fy2026-safmrs`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--hud-fy2026-safmrs/content.md), accessed 2026-09-09
  - Source: HUD FY2026 FMR Schedule, Topeka's area-wide 0–4BR figures and Kansas City's — "Topeka, KS MSA.................................... 792           820    1057   1392   1411" / "+Kansas City, MO-KS HMFA.......................... 1095         1197    1358   1769   2103" — [snapshot `2026-09-09--hud-fy2026-fmr-schedule`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--hud-fy2026-fmr-schedule/content.md), accessed 2026-09-09

**Bedroom size.** One statewide default; § 982.402(b)(1) leaves the standard to each PHA. The 1-person → 0BR row follows TX (`BEDROOM_MAP {1: 0, ...}`); WA and IL both map a single person to 1BR. Sizes 2–8 are identical across all three.

| Household size | 1 | 2 | 3–4 | 5–6 | 7–8 |
|---|---|---|---|---|---|
| Bedrooms | 0BR | 1BR | 2BR | 3BR | 4BR |

**Pregnancy adjustment.** Applies only where `household_size == 1` and that sole member's `pregnant` flag is true, and only to the bedroom lookup (0BR → 1BR). § 982.402(b)'s lead-in scopes every requirement beneath it to the determination of *family unit size*, which (a)(2)–(3) define as the bedroom count entered on the voucher — so this is the regulation's own scope, not a conservative reading. `household_size` for the income-limit comparison is unchanged. A pregnant member of a household of two or more triggers no adjustment.

  - Source: 24 CFR 982.402(b)(5), the sole pregnancy rule — "A family that consists of a pregnant woman (with no other persons) must be treated as a two-person family." — [snapshot `2026-09-09--24-cfr-982-402`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-982-402/content.md), accessed 2026-09-09
  - Source: 24 CFR 982.402(b), the lead-in that scopes every requirement beneath it to subsidy standards — "The following requirements apply when the PHA determines family unit size under the PHA subsidy standards:" — [snapshot `2026-09-09--24-cfr-982-402`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-982-402/content.md), accessed 2026-09-09
  - Source: 24 CFR 982.402(a)(2)–(3), defining *family unit size* as the bedroom count entered on the voucher — "For each family, the PHA determines the appropriate number of bedrooms under the PHA subsidy standards (family unit size)." / "The family unit size number is entered on the voucher issued to the family." — [snapshot `2026-09-09--24-cfr-982-402`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-982-402/content.md), accessed 2026-09-09
  - Source: 24 CFR 982.402(b)(1), confirming the bedroom-size table below is a PHA-discretionary standard rather than a federal schedule — "The PHA must establish subsidy standards that determine the number of bedrooms needed for families of different sizes and compositions." — [snapshot `2026-09-09--24-cfr-982-402`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-982-402/content.md), accessed 2026-09-09

**Formula.**

```
payment_standard  = HUD FMR/SAFMR for the household's bedroom size
reported_rent     = Screen.calc_expenses("monthly", ["rent"])   # mortgage excluded
gross_rent_proxy  = min(payment_standard, reported_rent) if reported_rent > 0
                    else payment_standard
Monthly HAP       = max(0, gross_rent_proxy − rounded TTP)
Annual value      = max(1, int(Monthly HAP × 12))   # truncated, not rounded
```

**The annualized product is truncated, not rounded** — `max(1, int(hap * 12))`, as `IlHcv.household_value` returns. It only bites on a fractional monthly rent: `Screen.calc_expenses("monthly", ["rent"])` returns a non-integer for a rent reported weekly or biweekly. Every scenario below reports whole-dollar monthly rent, so none of them discriminates truncation from rounding.

**`mortgage` is excluded.** WA and TX read `["rent", "mortgage"]`; IL reads `["rent"]` and states why — gross rent is rent to owner plus the utility allowance (§ 982.4), and an owner's mortgage payment is not a proxy for the rent of a future tenant-based unit. KS follows IL. This estimate models tenant-based assistance throughout, and no tenure gate exists, so a homeowner can reach it; capping their estimate with a mortgage payment would compound that.

**The reported rent is a proxy, and it is not gross rent.** § 982.4 defines gross rent as rent to owner plus any utility allowance for the assisted unit. The screener's reported rent is the household's *current* housing cost, carries no utility allowance, and is not the unit they will lease. It is used as a proxy and the output is labelled an estimate; because it only ever *caps* HAP and never raises it above the payment standard, the error is one-directional. This is a limit on the value, not on eligibility.
  - Source: 24 CFR 982.4, definition of *Gross rent* — the basis for both the reported-rent proxy and IL's exclusion of `mortgage` — "Gross rent. The sum of the rent to owner plus any utility allowance." — [snapshot `2026-09-09--24-cfr-982-4`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-982-4/content.md), accessed 2026-09-09

**The annual value floors at $1, not $0 (D3).** `benefits-calculator` filters the results page on `programValue(program) > 0` (`src/Components/Results/Filter/filterPrograms.ts` :: `isProgramBasicallyVisible`, where it is one of four conjuncts — the others being eligible legal status, `program.eligible`, and `!program.already_has`), so a program computing exactly $0 is removed from results entirely. Such a household is genuinely eligible — it holds a voucher and nets no subsidy at its current income — but at $0 would never see the program listed. IL HCV and MO CHIP floor at $1 for the same reason. The floor does not apply to a HUD-data failure, which returns $0 unfloored: a value the calculator could not compute, where hiding the program is the honest outcome.

The outcome arises wherever 40 × the payment standard is at or below the applicable income limit, less $20 because half-up rounding reaches it at PS − $0.50. It is an area property, not a household-size one, and reaches far more than one metro — the per-area windows are tabulated under D3 in `review-notes.md`.

  - Source: 24 CFR 982.505(b), the HAP formula — "The PHA shall pay a monthly housing assistance payment on behalf of the family that is equal to the lower of:" / "(1) The payment standard for the family minus the total tenant payment; or" / "(2) The gross rent minus the total tenant payment." — [snapshot `2026-09-09--24-cfr-982-505`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-982-505/content.md), accessed 2026-09-09
  - Source: Form HUD-50058 Instruction Booklet, Form Conventions — "Rounding: Round each monetary amount up" / "when a number is .50 or above; down when a" / "number is .49 or below." (two-column layout; fragments are consecutive left-column lines) — [snapshot `2026-09-09--hud-50058-instruction-booklet-2024`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--hud-50058-instruction-booklet-2024/content.md), accessed 2026-09-09
  - Source: HUD HCV Program Guidebook, Calculating Rent and HAP Payments § 3.1, tier-2 corroboration of the same formula and of why this spec's figure is an estimate — "The actual HAP can be calculated only after the family has selected a unit and t" / "is the lower of:" / "• The payment standard for the family minus the TTP, or" — (November 2019 edition, pre-HOTMA; corroboration only, not relied on for any HOTMA-era figure) — [snapshot `2026-09-09--hud-hcv-guidebook-rent-and-hap`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--hud-hcv-guidebook-rent-and-hap/content.md), accessed 2026-09-09

**Total Tenant Payment.** The greatest of four components, rounded to the nearest dollar. The fifth, § 5.628(a)(5), is the alternative non-public-housing rent "for public housing only" and cannot reach a tenant-based HCV household by its own terms.

1. 30% of monthly adjusted income
2. 10% of monthly income — the § 5.609 annual income above divided by twelve, **not** raw gross. Every exclusion applied at Criterion 1 has already been taken off this figure, as `IlHcv` computes it.
3. Welfare rent — **$0, sourced.** Wichita states welfare rent does not apply in this locality, so the $0 is stated PHA policy rather than an unobservable assumption.
4. Minimum rent — **$0.** Wichita sets the local minimum at $0 outright, so no § 5.630(b) hardship determination is needed to reach it. IL also models $0; WA uses $50 and TX $25, each following its own PHAs.

**Rounding.** § 5.628(a) requires nearest-dollar rounding but does not break an exact $0.50 tie; the HUD-50058 Form Conventions section resolves it as round-half-up. Implement with `Decimal` and `ROUND_HALF_UP`, **not** Python's built-in `round()`, which is banker's rounding and breaks ties toward even — it returns $742 where HUD requires $743. TX's `int(ttp + 0.5)` is half-up but carries float-precision error; WA does not round TTP at all; IL uses `Decimal`/`ROUND_HALF_UP` and documents the failure.

**Compute each prong from the annual figure, not from a monthly one.** 30% of monthly adjusted income is the annual adjusted income over 40, and 10% of monthly income is the annual over 120 — the form `IlHcv._total_tenant_payment` uses, and the reason it uses it. Dividing by twelve first and then taking a percentage destroys an exact half-dollar before the rounding rule can see it: at an adjusted income of $20,020 the exact 30% of monthly adjusted income is $500.50 and must round up to $501, but `0.30 × ($20,020 ÷ 12)` lands a hair under it and rounds down to $500 — under float and under `Decimal` alike, because a repeating twelfth is inexact in both. `ROUND_HALF_UP` alone does not save it; the `/40` and `/120` form is part of the requirement. No committed scenario separates the two forms: Scenario 12's adjusted income is divisible by twelve, so both give $742.50.

  - Source: 24 CFR 5.628(a)(2), the second prong and its base — the reg says "monthly income", which § 5.611 defines through § 5.609, so it is the excluded-adjusted figure and not raw gross — "(2) 10 percent of the family's monthly income;" — [snapshot `2026-09-09--24-cfr-5-628`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-628/content.md), accessed 2026-09-09
  - Source: 24 CFR 5.628(a) — "Total tenant payment is the highest of the following amounts, rounded to the nearest dollar:" — [snapshot `2026-09-09--24-cfr-5-628`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-628/content.md), accessed 2026-09-09
  - Source: Form HUD-50058 Instruction Booklet, Section 9 (line 9j) — "Total tenant payment (line 9j) is the highest of the" / "following amounts, rounded to the nearest dollar:" / "10 percent of the family's monthly income (line" / "30 percent of the family’s monthly adjusted" / "A portion of the family’s welfare assistance," (two-column layout; note the booklet mixes a straight apostrophe in the 10-percent line with curly apostrophes in the two following it) — [snapshot `2026-09-09--hud-50058-instruction-booklet-2024`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--hud-50058-instruction-booklet-2024/content.md), accessed 2026-09-09
  - Source: 24 CFR 5.628(a)(5), the unmodeled fifth component and its public-housing-only scope — "For public housing only, the alternative non-public housing rent, as determined in accordance with § 960.102 of this title." — [snapshot `2026-09-09--24-cfr-5-628`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-628/content.md), accessed 2026-09-09
  - Source: 24 CFR 5.630(a)(2), the minimum-rent ceiling — "For the public housing program and the section 8 moderate rehabilitation or voucher programs, the PHA may establish a minimum rent of up to $50." — [snapshot `2026-09-09--24-cfr-5-630`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-630/content.md), accessed 2026-09-09
  - Source: Wichita Housing Authority HCV Administrative Plan, minimum rent — "The minimum rent for this locality is $0." — [snapshot `2026-09-09--wichita-hcv-admin-plan-2026`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--wichita-hcv-admin-plan-2026/content.md), accessed 2026-09-09
  - Source: Wichita Housing Authority HCV Administrative Plan, welfare rent — "Welfare rent does not apply in this locality." — [snapshot `2026-09-09--wichita-hcv-admin-plan-2026`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--wichita-hcv-admin-plan-2026/content.md), accessed 2026-09-09

**Deductions.** Adjusted income = gross income − ($500 × dependents) − $550 if the head, co-head or spouse is 62+ or has a disability. A dependent is any member other than the head or spouse who is under 18, a full-time student, or has a disability; a `fosterChild`-relationship member counts, and a member capped under (b)(14) still counts. The elderly/disabled deduction is a family-level flag, taken once, not a per-member count.

`domesticPartner` is treated as a co-head: `HEAD_RELATIONSHIPS = ("headOfHousehold", "spouse", "domesticPartner")`, matching IL. `screener/models.py` treats `domesticPartner` as spouse-equivalent in `relationship_map()`/`is_spouse()` and returns False early in `is_dependent()`. Disability is read through `member.has_disability()`, which ORs `disabled`, `visually_impaired` and `long_term_disability` — never the `disabled` field alone.

**These figures overstate the benefit against current Kansas practice (D4).** $500/$550 are HUD's CY2026 inflation-adjusted amounts and follow IL. HUD's own table instructs agencies not yet complying with HOTMA §§ 102/104 not to use it, and PIH 2026-15 defers enforcement to 2027-01-01, so Kansas PHAs are pre-HOTMA in 2026: Wichita currently deducts $480 per dependent and $400 for an elderly or disabled family. A statewide $500/$550 therefore deducts more than the PHA will, lowering TTP and raising the estimate. Committed for consistency with IL, since one statewide figure cannot track each PHA's transition date.

  - Source: 24 CFR 5.611(a)(1)–(2), the statutory base amounts and the annual-adjustment mandate — "(a) Mandatory deductions. (1) $480 for each dependent, which amount will be adjusted by HUD annually in accordance with the Consumer Price Index for Urban Wage Earners and Clerical Workers, rounded to the next lowest multiple of $25;" / "(2) $525 for any elderly family or disabled family, which amount will be adjusted by HUD annually in accordance with the Consumer Price Index for Urban Wage Earners and Clerical Workers, rounded to the next lowest multiple of $25;" — [snapshot `2026-09-09--24-cfr-5-611`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-611/content.md), accessed 2026-09-09
  - Source: HUD 2026 Inflation-Adjusted Values (Table 1), effective January 1, 2026, giving the CY2026 amounts against the section each adjusts — "2026 HUD Inflation-Adjusted Values (Table 1): Effective January 1, 2026" / "24 CFR § 5.611(a)(1)    $500" / "24 CFR § 5.611(a)(2)    $550" — [snapshot `2026-09-09--hud-cy2026-inflation-adjusted-values`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--hud-cy2026-inflation-adjusted-values/content.md), accessed 2026-09-09
  - Source: Form HUD-50058 Instruction Booklet, line 8q, the dependent-count exclusion list — "Do not count head of household, spouse," / "co-head, foster child/adult or live-in aide):" / "The total number of dependents who live in the" / "household and are under 18 years of age, have a" / "disability, or are full-time students of any age." — [snapshot `2026-09-09--hud-50058-instruction-booklet-2024`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--hud-50058-instruction-booklet-2024/content.md), accessed 2026-09-09
  - Source: Wichita Housing Authority HCV Administrative Plan, § 6-III.B, the dependent allowance currently applied — "An allowance of $480 is deducted from annual income for each dependent (which amount will" — [snapshot `2026-09-09--wichita-hcv-admin-plan-2026`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--wichita-hcv-admin-plan-2026/content.md), accessed 2026-09-09
  - Source: Wichita Housing Authority HCV Administrative Plan, § 6-III.C, the elderly/disabled allowance currently applied and its HOTMA successor — "Currently, $400, once HOTMA is implemented, a single deduction of $525 is taken for any" — [snapshot `2026-09-09--wichita-hcv-admin-plan-2026`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--wichita-hcv-admin-plan-2026/content.md), accessed 2026-09-09
  - Source: 24 CFR 5.611(a)(4), the child-care deduction and its single condition — "Any reasonable child care expenses necessary to enable a member of the family to be employed or to further his or her education." — [snapshot `2026-09-09--24-cfr-5-611`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-611/content.md), accessed 2026-09-09

Ages are derived from `birth_year_month` via `calc_age()` / `age_from_date()` against the pinned reference date, never from the raw `age` field, which the serializer backfills at create time and which does not move with a reference date. No shipped HCV calculator does this — WA, TX and IL all read `member.age`, IL through an `_is_minor` wrapper — so KS departs from all three deliberately and has no sibling test to borrow the freezing pattern from. `age_from_date` compares month granularity only, and `calc_age()` falls back to the raw field when `birth_year_month` is null.

**The § 5.611(a)(3) and (a)(4) deductions are not modelled**, and their conditions differ. (a)(3) medical and attendant-care applies only to an elderly or disabled family, counts only unreimbursed expenses, and only above ten percent of annual income — the `medical` amount establishes none of the three. (a)(4) child care carries one condition only, that the expense be reasonable and necessary to enable employment or education — substantially met by `childCare` plus per-member income and `student` flags, so it is not omitted for want of data. Both are omitted for consistency with the three shipped HCV calculators, none of which computes either and each of whose specs commits the omission as deliberate rather than pending. Modelling either in KS alone would give a different estimate from its siblings for an identical household, making it a cross-program decision rather than a KS one. Both omissions narrow results.

**Mixed-family proration is not modelled**, and the full computed HAP is shown regardless of household composition. § 5.506 prorates assistance for a mixed-status family, but per-member immigration status is not collected, so the proportion of eligible members cannot be computed. This widens the value for mixed-status households specifically. It is not surfaced in the description, for the same reason Criterion 3's status question is not: naming it pre-screening could discourage mixed-status families from applying, and HUD's SAVE system verifies at application. IL states the same omission — "Not modelled (Benefit Value only, not eligibility): … and mixed-family proration — the payment is computed unprorated."
  - Source: 24 CFR 5.506(b)(2), the mixed-family exception the proration implements — "Despite the ineligibility of one or more family members, a mixed family may be eligible for one of the three types of assistance provided in §§ 5.516 and 5.518." — [snapshot `2026-09-09--24-cfr-5-506`](../program-maintenance/sources/ks/ks_hcv/2026-09-09--24-cfr-5-506/content.md), accessed 2026-09-09

**Silent degradation.** `get_screen_payment_standard` falls through to the metro FMR with no exception, no log and no flag when either the household's ZIP is absent from the SAFMR table (which is also what happens for a blank ZIP) or the `area_name` string fails to match — so a HUD rename would downgrade every ZIP in the metro at once. Both entry points produce the same wrong answer, and it is the error Scenario 15 exists to catch, produced without any visible failure. Separately, all three siblings catch `HudIncomeClientError` and bare `Exception` in both `household_eligible` and `household_value`, degrading to "not eligible" and $0 — a HUD outage presents as a clean negative rather than an error, and the branch is reachable with no network call when the program's `year` is unset. The program `year` must therefore be verified as set at deploy; the seed config sets `"2026"`.

## Test Scenarios

All ages are computed as of the pinned reference date **2026-08-27**. `Screen.get_reference_date()` falls back to the current date for an unfrozen screen, so tests must freeze or pass this date rather than relying on the ambient clock.

Each scenario's **Current Benefits** line is a results-layer condition, not a calculator input. `eligibility_results` sets `already_has` from `screen.has_benefit("ks_hcv")` *after* `household_eligible` and `household_value` have run, and the frontend filter reads it; neither calculator method consults it. A unit test of `KsHcv` will not exercise that line.

**Coverage map**

| Rule / variation axis | Scenarios |
|---|---|
| Income limit — under | 1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 15, 16, 18, 19, 21, 22 |
| Income limit — at the limit (`<=`) | 13 |
| Income limit — over (boundary, +$1) | 20 |
| Income limit — over (wide margin) | 14 |
| Income tier is 50% VLI, not 80% LI | 20 |
| Bedroom size 0BR / 1BR / 2BR / 3BR / 4BR | 2, 5, 6, 9 / 4, 11, 15, 16, 18, 22 / 1, 3, 7, 10, 17, 19, 21 / 12, 13 / 8 |
| Pregnancy adjustment (bedroom lookup only) | 16 |
| SAFMR routing (Wichita / Kansas City) vs area FMR (Topeka) | 1 / 15 / 8, 9, 10 |
| Dependent deduction, $500 per dependent | 1, 3, 8, 10, 12, 13, 17, 19, 21 |
| Dependent count excludes a non-minor, non-student, non-disabled adult | 7 |
| Elderly-or-disabled deduction, once per family | 22 (the only scenario with two qualifying members) · 5, 6 (applies) · 8 (does not — neither head nor spouse) |
| Disability read via `has_disability()` | 6 |
| § 5.609(b)(3) minor earned income | 12 |
| § 5.609(b)(5) workers' compensation | 11 |
| § 5.609(b)(8) foster member income, counts retained | 10 |
| § 5.609(b)(14) dependent full-time student cap | 18 |
| `family_size` not reduced for `fosterChild` | 17 |
| TTP half-up rounding vs banker's rounding | 12 |
| Gross-rent arm caps HAP | 19 |
| `mortgage` excluded from the gross-rent proxy | 21 |
| Payment-standard arm governs (no rent reported) | 1 |
| $1 nominal floor / $0-HAP-but-eligible | 4 |
| Minimum rent $0 (not $50) | 9 |

**Known scenario gaps.** Every data gap in the section above is `assumed-met` by definition, and none has a scenario written to test it. Beyond those:

- **Legal-status gate (Criterion 3)** — config-level behaviour with no KS-specific calculator logic.
- **`has_disability()`'s `visually_impaired` limb, and its plain `disabled` limb** — Scenario 6 records its member's disability as `long_term_disability` precisely so that it discriminates, which leaves `disabled` exercised nowhere.
- **The `domesticPartner` co-head mapping**, and MFB's extension of the § 5.609(a)(1) carve-out to it.
- **`_count_dependents`' adult-disabled-dependent limb** — it counts a non-head/spouse member who is a minor **or** a full-time student **or** has a disability; the first two are covered, the third is not.
- **Criterion 1's § 5.609(a)(1) carve-out** — a head or spouse contributes income in full whatever their age. Would need a minor head of household to get a scenario.
- **The § 5.628(a)(2) 10%-of-income arm** — the 30% arm wins in all 20 valued cases, so deleting the prong would pass the suite. It binds only where deductions exceed two-thirds of income, needing an implausibly low income at a large household size (eight people at roughly $6,000/year, a $12/year difference).
- **The `/40` and `/120` prong form versus divide-by-twelve-then-percentage** — the difference shows only on an exact half-dollar tie, and Scenario 12, the suite's only tie, has an adjusted income divisible by twelve, so both forms produce its $742.50.
- **The `area_name` string match and the program `year` being set** — deploy-time checks, not scenario-testable.

Scenario 21 is the one place a gap's handling is load-bearing rather than merely assumed: its household reports a mortgage, observable evidence of the homeownership data gap 6 declines to gate on, so its **Eligible** verdict rests on that gap's inclusive handling and would flip if a property gate were added.

### Scenario 1: Single Mother with Two Children, Wichita Golden Path — Eligible, $7,980

**What we're checking**: Baseline golden path — single parent, two dependent children, income well below the VLI limit. Core regression test for eligibility, 2BR payment standard, and the dependent deduction. No housing expense is reported, so the payment-standard arm of the HAP formula governs; Scenario 19 is the same household with rent reported.

**Expected**: Eligible — **$7,980/year** — Wichita, KS HMFA (ZIP 67202) FY2026 SAFMR 2BR proxy $1,180/mo (3-person household → 2BR). Gross annual income $21,600 ($1,800/mo). 2 dependents (children under 18) × $500 = $1,000/yr deduction → adjusted annual income $20,600 → monthly adjusted $1,716.67. TTP = max(0.30 × $1,716.67 = $515, 0.10 × $1,800 = $180, $0 min rent) = $515/mo. HAP = $1,180 − $515 = $665/mo × 12 = **$7,980/yr**. (Divergence D4)

**Steps**:
- **Location**: ZIP code `67202`, county `Sedgwick`
- **Household**: `3` people
- **Person 1**: Birth month/year `March 1991` (age 35), Relationship: Head of Household, Has income: Yes, Employment income: `$1,800/month`
- **Person 2**: Birth month/year `September 2016` (age 9), Relationship: Child, Has income: No
- **Person 3**: Birth month/year `January 2020` (age 6), Relationship: Child, Has income: No
- **Current Benefits**: Section 8 / HCV: No

**Why this matters**: A calculator using the wrong dependent-deduction amount fails here: at $480 the deduction is $960, adjusted income $20,640, TTP $516 and the value $7,968 — not $7,980. Also the baseline regression for 2BR routing and per-member income aggregation. Tests MFB simplification, not verified policy (D4): the $500 dependent deduction this scenario turns on is D4's CY2026 figure, which exceeds what Kansas PHAs deduct today.

### Scenario 2: Single Adult, Low Income, 0BR Payment Standard — Eligible, $3,600

**What we're checking**: Validates the single-person → 0BR bedroom default; same income as Scenario 1 but different household size produces a different bedroom tier and value, confirming household size drives the lookup, not income.

**Expected**: Eligible — **$3,600/year** — Wichita, KS HMFA (ZIP 67202) FY2026 SAFMR 0BR proxy $840/mo (single person → 0BR under MFB's statewide default). Gross monthly income $1,800, no dependents, not elderly/disabled — adjusted income = gross. TTP = max(0.30 × $1,800 = $540, 0.10 × $1,800 = $180, $0) = $540/mo. HAP = $840 − $540 = $300/mo × 12 = **$3,600/yr**.

**Steps**:
- **Location**: ZIP code `67202`, county `Sedgwick`
- **Household**: `1` person
- **Person 1**: Birth month/year `September 1991` (age 34), Relationship: Head of Household, Has income: Yes, Employment income: `$1,800/month`, Not currently receiving Section 8/HCV

**Why this matters**: Kills a 1-person → 1BR bedroom map. At 1BR the value would be $4,440, not $3,600 — same income as Scenario 1, so only household size can explain the difference.

### Scenario 3: Family of Four, Dual-Earner, 2BR Payment Standard — Eligible, $6,540

**What we're checking**: Validates income aggregation across two earners (combined $26,400/yr, well below the VLI limit) and that a 4-person household with children correctly maps to 2BR.

**Expected**: Eligible — **$6,540/year** — Wichita, KS HMFA (ZIP 67202) FY2026 SAFMR 2BR proxy $1,180/mo. Combined gross monthly income $2,200 ($1,500 + $700) → annual $26,400. 2 dependents × $500 = $1,000/yr deduction → adjusted annual $25,400 → monthly adjusted $2,116.67. TTP = max(0.30 × $2,116.67 = $635, 0.10 × $2,200 = $220, $0) = $635/mo. HAP = $1,180 − $635 = $545/mo × 12 = **$6,540/yr**.

**Steps**:
- **Location**: ZIP code `67202`, county `Sedgwick`
- **Household**: `4` people
- **Person 1**: Birth month/year `March 1986` (age 40), Relationship: Head of Household, Has income: Yes, Employment income: `$1,500/month`
- **Person 2**: Birth month/year `September 1988` (age 37), Relationship: Spouse, Has income: Yes, Employment income: `$700/month`
- **Person 3**: Birth month/year `January 2016` (age 10), Relationship: Child, Has income: No
- **Person 4**: Birth month/year `November 2019` (age 6), Relationship: Child, Has income: No
- **Current Benefits**: Section 8 / HCV: No

**Why this matters**: Kills a dependent deduction applied per household rather than per dependent, and confirms income aggregates across two earners.

### Scenario 4: Adult Couple at the Top of the VLI Band — Eligible, $1

**What we're checking**: That income high enough for TTP to consume the entire payment standard still returns **eligible with a nominal $1**, not ineligible and not $0. Wichita size 2 is chosen because its window is **tight** — $36,380–$38,600, a $2,220 band — which makes it a sharper regression test than a wide one: a small error in TTP, rounding or the payment standard moves the household out of the band and the test fails. The outcome is not unique to this size or area (see D3 in `review-notes.md` — Topeka has it at seven of eight sizes); this is the tightest convenient instance of it. Note the lower bound is $36,380 rather than 40 × $910 = $36,400, because half-up rounding lifts TTP to $910 once it reaches $909.50. Discriminating in two directions — a calculator that screens the household out fails, and so does one that returns a true $0, because the results page filters on `programValue(program) > 0` and the household would never see the program.

**Expected**: Eligible — **$1/year** — Wichita, KS HMFA (ZIP 67202) FY2026 SAFMR 1BR proxy $910/mo (2-person household → 1BR). Gross annual income $38,000 ($3,166.67/mo) — at or below the Wichita 2-person VLI limit of $38,600, so eligible at Criterion 1. No dependents, not elderly/disabled, so adjusted income equals gross. TTP = max(0.30 × $3,166.67 = $950, 0.10 × $3,166.67 = $316.67 → $317, $0) = $950/mo. Monthly HAP = max(0, $910 − $950) = $0, so the annual value floors at **$1/yr** rather than $0 — see the nominal-value floor under Formula and rounding. (Divergence D3)

**Steps**:
- **Location**: ZIP code `67202`, county `Sedgwick`
- **Household**: `2` people
- **Person 1**: Birth month/year `March 1988` (age 38), Relationship: Head of Household, Has income: Yes, Employment income: `$38,000/year`
- **Person 2**: Birth month/year `September 1990` (age 35), Relationship: Spouse, Has income: No
- **Current Benefits**: Section 8 / HCV: No

**Why this matters**: Kills two mutations at once: a calculator that screens this household out entirely, and one that returns a true $0 — at $0 the frontend's `programValue(program) > 0` filter drops the program and the household never sees it. Tests MFB simplification, not verified policy (D3): the $1 is MFB's nominal floor, not a HUD-computed amount.

### Scenario 5: Elderly Single Adult, Social Security Income — Eligible, $6,828

**What we're checking**: Validates Social Security income handling and the elderly/disabled deduction — low TTP produces a larger HAP than a wage earner at comparable income.

**Expected**: Eligible — **$6,828/year** — Wichita, KS HMFA (ZIP 67202) FY2026 SAFMR 0BR proxy $840/mo (single person → 0BR). Gross annual income $11,400 ($950/mo SS). Head is 76 (elderly, sole household member) → elderly/disabled family deduction $550/yr applies. Adjusted annual = $11,400 − $550 = $10,850 → monthly adjusted $904.1667. TTP = max(0.30 × $904.1667 = $271.25 → $271, 0.10 × $950 = $95, $0) = $271/mo. HAP = $840 − $271 = $569/mo × 12 = **$6,828/yr**. (Divergence D4)

**Steps**:
- **Location**: ZIP code `67202`, county `Sedgwick`
- **Household**: `1` person
- **Person 1**: Birth month/year `March 1950` (age 76), Relationship: Head of Household, Has income: Yes, Income type: Social Security (`sSRetirement`), Amount: `$950/month`, Not currently receiving Section 8/HCV

**Why this matters**: Kills an elderly/disabled deduction of $525 rather than $550, and confirms the flag is set from age alone with no disability field. Tests MFB simplification, not verified policy (D4): the $550 elderly deduction this scenario turns on is D4's CY2026 figure; Wichita currently deducts $400.

### Scenario 6: Disabled Single Adult, SSI Income — Eligible, $8,088

**What we're checking**: Validates SSI income handling and the `disabled` screener field's elderly/disabled deduction, at very low income producing a high HAP.

**Expected**: Eligible — **$8,088/year** — Wichita, KS HMFA (ZIP 67202) FY2026 SAFMR 0BR proxy $840/mo (single person → 0BR). Gross annual income $7,200 ($600/mo SSI). Head is disabled (sole household member) → elderly/disabled family deduction $550/yr applies. Adjusted annual = $7,200 − $550 = $6,650 → monthly adjusted $554.1667. TTP = max(0.30 × $554.1667 = $166.25 → $166, 0.10 × $600 = $60, $0) = $166/mo. HAP = $840 − $166 = $674/mo × 12 = **$8,088/yr**. (Divergence D4)

**Steps**:
- **Location**: ZIP code `67202`, county `Sedgwick`
- **Household**: `1` person
- **Person 1**: Birth month/year `June 1989` (age 37), Relationship: Head of Household, Has disability: Yes, recorded as `long_term_disability: true` (`disabled` left unset), Has income: Yes, Income type: SSI (`sSI`), Amount: `$600/month`, Not currently receiving Section 8/HCV

**Why this matters**: Kills reading the `disabled` field directly instead of `has_disability()`. This member's disability is recorded only as `long_term_disability`, so a calculator reading `disabled` alone finds no elderly/disabled family, loses the $550 deduction and returns $7,920 against $8,088. The field is set this way deliberately: with `disabled: true` the scenario would return $8,088 under either reading and prove nothing. Tests MFB simplification, not verified policy (D4): the $550 elderly-or-disabled deduction in this value is D4's CY2026 figure.

### Scenario 7: Multi-Generational Household, Mixed Income Sources — Eligible, $6,012

**What we're checking**: A multi-generational household (elderly grandparent on SS + adult child on wages + minor grandchild) — validates income aggregation across income types and the dependent-count rule, specifically that an adult child who is neither a minor, a full-time student nor disabled is not a dependent.

**Expected**: Eligible — **$6,012/year** — Wichita, KS HMFA (ZIP 67202) FY2026 SAFMR 2BR proxy $1,180/mo. Combined gross monthly income $2,350 ($950 SS + $1,400 wages) → annual $28,200. Head (grandparent, 68) is elderly, and the elderly/disabled deduction is a household-level flag keyed to head/co-head/spouse only — it applies here since the head themself is 62+. Dependent count excludes head/spouse: the adult child (35, no disability/student flag) is not a dependent; the grandchild (8, under 18) is 1 dependent × $500 = $500/yr. Total deductions = $550 (elderly) + $500 (dependent) = $1,050/yr. Adjusted annual = $28,200 − $1,050 = $27,150 → monthly adjusted $2,262.50. TTP = max(0.30 × $2,262.50 = $678.75 → $679, 0.10 × $2,350 = $235, $0) = $679/mo. HAP = $1,180 − $679 = $501/mo × 12 = **$6,012/yr**. (Divergence D4)

**Steps**:
- **Location**: ZIP code `67202`, county `Sedgwick`
- **Household**: `3` people
- **Person 1**: Birth month/year `March 1958` (age 68), Relationship: Head of Household, Has income: Yes, Income type: Social Security (`sSRetirement`), Amount: `$950/month`
- **Person 2**: Birth month/year `September 1990` (age 35), Relationship: Child, Has income: Yes, Employment income: `$1,400/month`
- **Person 3**: Birth month/year `January 2018` (age 8), Relationship: Grandchild, Has income: No
- **Current Benefits**: Section 8 / HCV: No

**Why this matters**: Kills counting the 35-year-old adult child as a dependent: at two dependents the adjusted income is $26,650, TTP $666 and the value $6,168 against $6,012. With only one qualifying member this scenario cannot discriminate the elderly deduction's once-per-family rule — Scenario 22 does that. Tests MFB simplification, not verified policy (D4): the $550 and $500 figures in this value are D4's CY2026 amounts.

### Scenario 8: Large 7-Person Household, 4BR Payment Standard — Eligible, $2,436

**What we're checking**: A large 7-person household, 4 earners across 3 income types — validates the 4BR bedroom tier and that non-head/spouse elderly and adult members don't incorrectly trigger deductions they're not entitled to. High TTP produces a small but positive HAP. The sibling's income is deliberately typed as pension rather than SSI, since SSI would imply an unstated disability.

**Expected**: Eligible — **$2,436/year** — Topeka, KS MSA (Shawnee County) FY2026 area FMR 4BR proxy $1,411/mo. Combined gross monthly income $4,150 ($1,400 + $1,200 + $950 + $600) → annual $49,800. Elderly/disabled deduction does not apply — the elderly parent (68) and the sibling are neither head nor spouse (head is 36, spouse is 33, neither elderly/disabled). Dependents (excluding head/spouse): the parent and sibling are adults with no stated disability/student status, so not dependents; the 3 children (12, 9, 5) are all under 18 → 3 × $500 = $1,500/yr deduction. Adjusted annual = $49,800 − $1,500 = $48,300 → monthly adjusted $4,025. TTP = max(0.30 × $4,025 = $1,207.50 → $1,208, 0.10 × $4,150 = $415, $0) = $1,208/mo. HAP = $1,411 − $1,208 = $203/mo × 12 = **$2,436/yr**.

**Steps**:
- **Location**: ZIP code `66604`, county `Shawnee`
- **Household**: `7` people
- **Person 1**: Birth month/year `March 1990` (age 36), Relationship: Head of Household, Has income: Yes, Employment income: `$1,400/month`
- **Person 2**: Birth month/year `September 1992` (age 33), Relationship: Spouse, Has income: Yes, Employment income: `$1,200/month`
- **Person 3**: Birth month/year `January 1958` (age 68), Relationship: Parent, Has income: Yes, Income type: Social Security (`sSRetirement`), Amount: `$950/month`
- **Person 4**: Birth month/year `November 1988` (age 37), Relationship: Sibling, Has income: Yes, Income type: Pension (`pension`), Amount: `$600/month`
- **Person 5**: Birth month/year `April 2014` (age 12), Relationship: Child, Has income: No
- **Person 6**: Birth month/year `July 2017` (age 9), Relationship: Child, Has income: No
- **Person 7**: Birth month/year `February 2021` (age 5), Relationship: Child, Has income: No
- **Current Benefits**: Section 8 / HCV: No

**Why this matters**: Kills a per-member elderly deduction — the elderly parent and the adult sibling are neither head nor spouse, so no elderly deduction applies at all despite one member being 68.

### Scenario 9: Zero Income Household, Full Payment Standard as HAP — Eligible, $9,504

**What we're checking**: A zero-income household — validates the HAP formula degrades gracefully to the full payment standard, and confirms the $0 minimum rent (not a $50 floor) applies. Note the $0 does not depend on hardship status being unknown — Wichita sets the local minimum rent at $0 outright, so no hardship determination is needed to reach it; see Total Tenant Payment.

**Expected**: Eligible — **$9,504/year** — Topeka, KS MSA (Shawnee County) FY2026 area FMR 0BR proxy $792/mo. Zero income → adjusted income $0. TTP = max(0.30 × $0 = $0, 0.10 × $0 = $0, $0 minimum rent) = $0/mo. HAP = $792 − $0 = $792/mo × 12 = **$9,504/yr**.

**Steps**:
- **Location**: ZIP code `66604`, county `Shawnee`
- **Household**: `1` person
- **Person 1**: Birth month/year `September 1991` (age 34), Relationship: Head of Household, Has income: No (no income from any source), Not currently receiving Section 8/HCV

**Why this matters**: Kills a $50 minimum-rent floor: with zero income TTP must be $0, giving the full payment standard as HAP.

### Scenario 10: 3-Person Household, Topeka Geographic Coverage, Foster/Kinship-Care Income Exclusion Without Dependent-Count Loss — Eligible, $6,504

**What we're checking**: The county-level FMR lookup (Topeka, not a fixed value) and Criterion 1's asymmetric `fosterChild` treatment — the member's income is excluded but they still count as a dependent. Discriminating: also excluding them from the dependent count yields $6,348/yr instead of $6,504/yr. This does not isolate § 5.609(b)(4); because the payment sits on the `fosterChild` member, the broader (b)(8) member-level exclusion would produce the same result on its own.

**Expected**: Eligible — **$6,504/year** — Topeka, KS MSA (Shawnee County) FY2026 area FMR 2BR proxy $1,057/mo. Head's gross annual income $21,600 ($1,800/mo). Person 3 has `relationship` = `fosterChild` ("Foster Child / Kinship Care") and receives a $150/month care payment reported under `cashAssistanceOther` (the non-TANF cash-assistance stream — `cashAssistance` is the TANF field specifically); it is excluded by the member-level exclusion — (b)(4) covers the payment itself and (b)(8) the member's income, and either reaches it here — so countable gross monthly income remains $1,800 (not $1,950). Both Person 2 and Person 3 count as dependents — `family_size`/dependent-count is not reduced for an unconfirmed `fosterChild`-relationship member (Criterion 1) — so 2 dependents × $500 = $1,000/yr deduction → adjusted annual $20,600 → monthly adjusted $1,716.67. TTP = max(0.30 × $1,716.67 = $515.00 → $515, 0.10 × $1,800 = $180, $0) = $515/mo. HAP = $1,057 − $515 = $542/mo × 12 = **$6,504/yr**. (Divergence D2)

**Steps**:
- **Location**: ZIP code `66604`, county `Shawnee`
- **Household**: `3` people
- **Person 1**: Birth month/year `March 1991` (age 35), Relationship: Head of Household, Has income: Yes, Employment income: `$1,800/month`
- **Person 2**: Birth month/year `September 2016` (age 9), Relationship: Child, Has income: No
- **Person 3**: Birth month/year `January 2020` (age 6), Relationship: Foster Child, Has income: Yes, Income type: Cash Assistance - Other (`cashAssistanceOther`), Amount: `$150/month` (foster-care maintenance payment)
- **Current Benefits**: Section 8 / HCV: No

**Why this matters**: Kills a calculator that counts the foster member's care payment (§ 5.609(b)(8)) or drops them from the dependent count. Excluding them from the count instead yields $6,348. Tests MFB simplification, not verified policy (D2): (b)(8) is applied to every `fosterChild`-relationship member, not only a confirmed placement.

### Scenario 11: Adult Couple, No Children, 1BR Payment Standard, Workers' Compensation Exclusion — Eligible, $5,520

**What we're checking**: The 1BR bedroom tier (2-person household — no other scenario exercises it) and that a workers' compensation payment is excluded from countable income (§ 5.609(b)(5)).

**Expected**: Eligible — **$5,520/year** — Wichita, KS HMFA (ZIP 67202) FY2026 SAFMR 1BR proxy $910/mo (2-person household → 1BR). Person 1 has $900/month employment income plus a separate $200/month workers' compensation payment; the workers' compensation amount is excluded under § 5.609(b)(5), so it does not count toward income eligibility or TTP. Countable combined gross monthly income = $900 (Person 1, wages only) + $600 (Person 2) = $1,500. No dependents, not elderly/disabled. TTP = max(0.30 × $1,500 = $450, 0.10 × $1,500 = $150, $0) = $450/mo. HAP = $910 − $450 = $460/mo × 12 = **$5,520/yr**.

**Steps**:
- **Location**: ZIP code `67202`, county `Sedgwick`
- **Household**: `2` people
- **Person 1**: Birth month/year `March 1988` (age 38), Relationship: Head of Household, Has income: Yes, Employment income: `$900/month`, Income type: Workers' compensation (`workersComp`), Amount: `$200/month`
- **Person 2**: Birth month/year `June 1990` (age 36), Relationship: Spouse, Has income: Yes, Employment income: `$600/month`
- **Current Benefits**: Section 8 / HCV: No

**Why this matters**: Kills a calculator that counts `workersComp` as income (§ 5.609(b)(5)); counting it gives $4,800.

### Scenario 12: Family of Five, 3BR Payment Standard, Minor's Earned Income Exclusion — Eligible, $9,684

**What we're checking**: The 3BR bedroom tier (5-person household — no other scenario exercises it) and that a minor's earned income is excluded from countable income (§ 5.609(b)(3)) while the minor still counts as a dependent.

**This scenario also guards the TTP rounding rule, and it is the only one that does — do not re-tune its income figures.** Its TTP lands on an exact $742.50 tie, where the required half-up rounding gives $743 and Python's default banker's `round()` gives $742, a $12/year difference in the final value. Scenario 8's TTP is also an exact tie ($1,207.50) but rounds to $1,208 under both rules, so it does not discriminate; no other scenario, including the three rebuilt ones, lands on a tie at all. Changing this household's income to test something else would silently remove the suite's only coverage of the rounding requirement without any test failing.

**Expected**: Eligible — **$9,684/year** — Wichita, KS HMFA (ZIP 67202) FY2026 SAFMR 3BR proxy $1,550/mo (5-person household → 3BR). Adult combined gross monthly income $2,600 ($1,800 + $800) → annual $31,200. Person 3 (age 13) has $200/month part-time earned income; as employment income of a household member under 18, it is excluded under § 5.609(b)(3) and does not add to countable income (countable annual income remains $31,200, not $33,600). All 3 children remain dependents regardless of the income exclusion — 3 × $500 = $1,500/yr deduction → adjusted annual $29,700 → monthly adjusted $2,475. TTP = max(0.30 × $2,475 = $742.50 → $743, 0.10 × $2,600 = $260, $0) = $743/mo. HAP = $1,550 − $743 = $807/mo × 12 = **$9,684/yr**.

**Steps**:
- **Location**: ZIP code `67202`, county `Sedgwick`
- **Household**: `5` people
- **Person 1**: Birth month/year `March 1988` (age 38), Relationship: Head of Household, Has income: Yes, Employment income: `$1,800/month`
- **Person 2**: Birth month/year `June 1990` (age 36), Relationship: Spouse, Has income: Yes, Employment income: `$800/month`
- **Person 3**: Birth month/year `March 2013` (age 13), Relationship: Child, Has income: Yes, Employment income: `$200/month` (part-time)
- **Person 4**: Birth month/year `November 2016` (age 9), Relationship: Child, Has income: No
- **Person 5**: Birth month/year `July 2020` (age 6), Relationship: Child, Has income: No
- **Current Benefits**: Section 8 / HCV: No

**Why this matters**: Kills two: counting a minor's earned income (§ 5.609(b)(3)), and Python's banker's `round()`. Its TTP is an exact $742.50 tie — half-up gives $743, `round()` gives $742. **This is the only scenario in the suite that discriminates the rounding rule; Scenario 8's $1,207.50 tie rounds to $1,208 either way. Do not re-tune this household's income.**

### Scenario 13: Family of Five Exactly at the VLI Limit — Eligible, $3,408

**What we're checking**: The `<=` comparator at the exact income limit. Household size 5 is chosen deliberately: the Wichita 5-person VLI limit ($52,150) sits *below* the income at which TTP overtakes the payment standard, so this boundary case returns a positive value rather than $0. That makes it discriminate on the comparator **and** the value math, with no overlap against Scenario 4's $0 floor.

**Expected**: Eligible — **$3,408/year** — Wichita, KS HMFA (ZIP 67202) FY2026 SAFMR 3BR proxy $1,550/mo (5-person household → 3BR). Gross annual income $52,150, exactly the Wichita 5-person FY2026 VLI limit — eligible on the `<=` comparison; at $52,151 the household is ineligible — asserted as Scenario 20 rather than left as prose here. 3 dependents (children under 18) × $500 = $1,500/yr deduction → adjusted annual $50,650 → monthly adjusted $4,220.8333. TTP = max(0.30 × $4,220.8333 = $1,266.25 → $1,266, 0.10 × $4,345.8333 = $434.58 → $435, $0) = $1,266/mo. HAP = $1,550 − $1,266 = $284/mo × 12 = **$3,408/yr**.

**Steps**:
- **Location**: ZIP code `67202`, county `Sedgwick`
- **Household**: `5` people
- **Person 1**: Birth month/year `March 1985` (age 41), Relationship: Head of Household, Has income: Yes, Employment income: `$52,150/year`
- **Person 2**: Birth month/year `September 1987` (age 38), Relationship: Spouse, Has income: No
- **Person 3**: Birth month/year `April 2012` (age 14), Relationship: Child, Has income: No
- **Person 4**: Birth month/year `November 2016` (age 9), Relationship: Child, Has income: No
- **Person 5**: Birth month/year `July 2020` (age 6), Relationship: Child, Has income: No
- **Current Benefits**: Section 8 / HCV: No

**Why this matters**: Kills a `<` comparator where the rule is `<=`. Household size 5 is chosen because its VLI limit sits below the zero-HAP point, so the boundary carries a positive value and tests the value math too.

### Scenario 14: Single Adult Above the VLI Limit — Not eligible

**What we're checking**: A household over the income gate is screened out. Ineligible counterpart to Scenario 13's at-the-limit case. Note the margin is now wide — $66,000 against a $33,800 1-person limit — because the gate moved from 95% AMI to 50%; Scenario 13 carries the tight boundary test.

**Expected**: Not eligible — Wichita, KS HMFA 1-person FY2026 VLI limit $33,800/yr. Gross annual income $66,000 ($5,500/mo) exceeds it, so the household fails Criterion 1 and no value is computed.

**Steps**:
- **Location**: ZIP code `67202`, county `Sedgwick`
- **Household**: `1` person
- **Person 1**: Birth month/year `March 1988` (age 38), Relationship: Head of Household, Has income: Yes, Employment income: `$5,500/month`
- **Current Benefits**: Section 8 / HCV: No

**Why this matters**: Confirms the income gate screens out at a wide margin, so a household far above the limit cannot slip through on a rounding or unit error.

### Scenario 15: Adult Couple, Kansas City, KS (Wyandotte County) SAFMR Coverage — Eligible, $8,040

**What we're checking**: Confirms the mandatory-SAFMR branch isn't hard-coded to Wichita alone — Kansas City, MO-KS HMFA is a second, independently HUD-designated mandatory-SAFMR area, and the calculator must select the ZIP-level SAFMR rather than the area-wide FMR.

**Expected**: Eligible — **$8,040/year** — Kansas City, MO-KS HMFA, ZIP 66103 (Wyandotte County) SAFMR 1BR proxy $1,180/mo (2-person household → 1BR) — not the area-wide Kansas City, MO-KS HMFA FY2026 FMR of $1,197/mo for 1BR. Combined gross monthly income $1,700 ($1,000 + $700) → annual $20,400, well below the Kansas City, MO-KS HMFA 2-person VLI limit of $45,400. No dependents, not elderly/disabled. TTP = max(0.30 × $1,700 = $510, 0.10 × $1,700 = $170, $0) = $510/mo. HAP = $1,180 − $510 = $670/mo × 12 = **$8,040/yr**.

**Steps**:
- **Location**: ZIP code `66103`, county `Wyandotte`
- **Household**: `2` people
- **Person 1**: Birth month/year `March 1990` (age 36), Relationship: Head of Household, Has income: Yes, Employment income: `$1,000/month`
- **Person 2**: Birth month/year `June 1992` (age 34), Relationship: Spouse, Has income: Yes, Employment income: `$700/month`
- **Current Benefits**: Section 8 / HCV: No

**Why this matters**: Kills a SAFMR branch hard-coded to Wichita, and kills the silent metro-FMR fallback: at the area-wide $1,197 the value would be $8,244, not $8,040.

### Scenario 16: Pregnant Single Person, Effective Household Size 2 for Subsidy Standard — Eligible, $6,600

**What we're checking**: A single pregnant applicant living alone — confirms § 982.402's pregnancy rule applies at the bedroom-size lookup only (maps to the 2-person/1BR tier), without changing `household_size` for the income-limit comparison (stays 1, Criterion 2).

**Expected**: Eligible — **$6,600/year** — Wichita, KS HMFA (ZIP 67202) FY2026 SAFMR 1BR proxy $910/mo (1-person household, pregnant → effective size 2 → 1BR). Gross annual income $14,400 ($1,200/mo) — `household_size` remains 1 for the income-limit comparison. No dependents (pregnancy does not itself create a dependent), not elderly/disabled. TTP = max(0.30 × $1,200 = $360, 0.10 × $1,200 = $120, $0) = $360/mo. HAP = $910 − $360 = $550/mo × 12 = **$6,600/yr**.

**Steps**:
- **Location**: ZIP code `67202`, county `Sedgwick`
- **Household**: `1` person
- **Person 1**: Birth month/year `January 1999` (age 27), Relationship: Head of Household, Pregnant: **Yes** (`pregnant: true`), Has income: Yes, Employment income: `$1,200/month`, Not currently receiving Section 8/HCV

**Why this matters**: Kills a missing pregnancy adjustment — at 0BR the payment standard is $840, TTP is unchanged at $360, and the value is $5,760 — and kills a pregnancy adjustment wrongly applied to the income limit as well as the bedroom lookup.

### Scenario 17: Household with an Unconfirmed Foster/Kinship-Care Member, `family_size` Is Not Wrongly Reduced — Eligible, $2,460

**What we're checking**: That `family_size` equals `household_size` when the household includes a `fosterChild`-relationship member. Income ($40,000) sits between the Wichita 2-person VLI limit ($38,600) and the 3-person limit ($43,450), so the two bases give opposite outcomes. Discriminating: reducing `family_size` to 2 screens the household out entirely; leaving it at 3 finds it eligible with a positive value, so a regression shows up as a real difference rather than $0-vs-$0.

**Expected**: Eligible — **$2,460/year** — Wichita, KS HMFA `family_size` = `household_size` = 3 (no reduction — see Criterion 1). Applicable VLI limit for family_size 3 = $43,450/yr; the family_size-2 limit, $38,600/yr, would have wrongly applied under the incorrect reduction and would have made this household ineligible. Gross annual income $40,000 ($3,333.33/mo, head only) is below $43,450 → eligible at Criterion 1. Bedroom size: 3-person household → 2BR, Wichita SAFMR $1,180/mo. 2 dependents (both children, including the `fosterChild`-relationship member per Criterion 1's default) × $500 = $1,000/yr deduction → adjusted annual $39,000 → monthly adjusted $3,250. TTP = max(0.30 × $3,250 = $975, 0.10 × $3,333.33 = $333.33 → $333, $0) = $975/mo. HAP = $1,180 − $975 = $205/mo × 12 = **$2,460/yr**. (Divergence D2)

**Steps**:
- **Location**: ZIP code `67202`, county `Sedgwick`
- **Household**: `3` people
- **Person 1**: Birth month/year `March 1988` (age 38), Relationship: Head of Household, Has income: Yes, Employment income: `$40,000/year`
- **Person 2**: Birth month/year `January 2016` (age 10), Relationship: Child, Has income: No
- **Person 3**: Birth month/year `January 2020` (age 6), Relationship: Foster Child, Has income: No
- **Current Benefits**: Section 8 / HCV: No

**Why this matters**: Kills a `family_size` reduced for an unconfirmed `fosterChild` member: at family_size 2 the limit is $38,600 and the household is screened out entirely, against $2,460 when the count is left alone. Tests MFB simplification, not verified policy (D2): `family_size` is left unreduced for every `fosterChild`-relationship member, not only a confirmed placement.

### Scenario 18: Dependent Full-Time Student Aged 18+, § 5.609(b)(14) Earned-Income Cap — Eligible, $7,320

**What we're checking**: That a dependent full-time student aged 18 or over has earned income counted only up to $500/year, with the excess excluded, while still counting as a dependent for the deduction. Discriminating: counting the student's full $6,000 earnings yields $5,664/yr instead of $7,320/yr, so a calculator that omits (b)(14) fails by $1,656.

**Expected**: Eligible — **$7,320/year** — Wichita, KS HMFA, ZIP 67202 SAFMR 1BR $910/mo (2-person household → 1BR). Person 2 is 20, a dependent (not head or spouse) with `student_full_time` = true, earning $500/mo = $6,000/yr; § 5.609(b)(14) counts the first $500/yr and excludes the remaining $5,500 ((b)(3) does not apply — Person 2 is over 18). Countable gross annual income = $12,000 + $500 = $12,500, below the Wichita 2-person VLI limit of $38,600 → eligible at Criterion 1. Person 2 still counts as a dependent → 1 × $500 = $500/yr deduction → adjusted annual $12,000 → monthly adjusted $1,000. TTP = max(0.30 × $1,000 = $300, 0.10 × $1,041.67 = $104.17 → $104, $0) = $300/mo. HAP = $910 − $300 = $610/mo × 12 = **$7,320/yr**.

**Steps**:
- **Location**: ZIP code `67202`, county `Sedgwick`
- **Household**: `2` people
- **Person 1**: Birth month/year `March 1985` (age 41), Relationship: Head of Household, Has income: Yes, Employment income: `$1,000/month`
- **Person 2**: Birth month/year `April 2006` (age 20), Relationship: Child, Student: Yes, Full-time student: Yes, Has income: Yes, Employment income: `$500/month`
- **Current Benefits**: Section 8 / HCV: No

**Why this matters**: Kills an omitted § 5.609(b)(14) cap — counting the student's full $6,000 gives $5,664 — and kills applying the cap to an under-18 member, who is covered in full by (b)(3) instead.

### Scenario 19: Reported Rent Below the Payment Standard, Gross-Rent Arm Caps HAP — Eligible, $4,620

**What we're checking**: The gross-rent arm of § 982.505(b). Same household as Scenario 1, with $900/month rent reported, which is below the $1,180 payment standard and therefore caps HAP. Discriminating: a calculator that ignores reported rent returns Scenario 1's $7,980 instead of $4,620 — a $3,360 overstatement.

**Expected**: Eligible — **$4,620/year** — Wichita, KS HMFA (ZIP 67202) FY2026 SAFMR 2BR proxy $1,180/mo (3-person household → 2BR). Income and deductions are identical to Scenario 1: gross annual $21,600, 2 dependents × $500 = $1,000/yr deduction → adjusted annual $20,600 → monthly adjusted $1,716.67 → TTP = max(0.30 × $1,716.67 = $515, 0.10 × $1,800 = $180, $0 min rent) = $515/mo. Reported housing cost $900/mo > $0, so `gross_rent_proxy = min($1,180, $900) = $900`. HAP = max(0, $900 − $515) = $385/mo × 12 = **$4,620/yr**.

**Steps**:
- **Location**: ZIP code `67202`, county `Sedgwick`
- **Household**: `3` people
- **Person 1**: Birth month/year `March 1991` (age 35), Relationship: Head of Household, Has income: Yes, Employment income: `$1,800/month`
- **Person 2**: Birth month/year `September 2016` (age 9), Relationship: Child, Has income: No
- **Person 3**: Birth month/year `January 2020` (age 6), Relationship: Child, Has income: No
- **Expenses**: Rent: `$900/month`
- **Current Benefits**: Section 8 / HCV: No

**Why this matters**: Kills a calculator that ignores reported rent: it would return Scenario 1's $7,980, a $3,360 overstatement. Same household as Scenario 1 with rent added, so only the gross-rent arm can explain the difference.

### Scenario 20: Family of Five One Dollar Above the VLI Limit — Not eligible

**What we're checking**: The `>` side of the income comparator at the exact boundary. Deliberately paired with Scenario 13 — identical household, one dollar more income — so the two together prove the comparator is `<=` and not `<`, and that the boundary falls where the spec says. Scenario 14 tests ineligibility at a wide margin; this tests it at the margin that could actually be coded wrong.

**Expected**: Not eligible — Wichita, KS HMFA 5-person FY2026 VLI limit $52,150/yr. Gross annual income $52,151 exceeds it by $1, so the household fails Criterion 1 and no value is computed. Scenario 13 is the same household at $52,150, which qualifies and returns $3,408/yr — an off-by-one in the comparator flips one of this pair.

**Steps**:
- **Location**: ZIP code `67202`, county `Sedgwick`
- **Household**: `5` people
- **Person 1**: Birth month/year `March 1985` (age 41), Relationship: Head of Household, Has income: Yes, Employment income: `$52,151/year`
- **Person 2**: Birth month/year `September 1987` (age 38), Relationship: Spouse, Has income: No
- **Person 3**: Birth month/year `April 2012` (age 14), Relationship: Child, Has income: No
- **Person 4**: Birth month/year `November 2016` (age 9), Relationship: Child, Has income: No
- **Person 5**: Birth month/year `July 2020` (age 6), Relationship: Child, Has income: No
- **Current Benefits**: Section 8 / HCV: No

**Why this matters**: **The only scenario that detects the income tier.** At 80% AMI the 5-person limit is $83,400 and this household is eligible; at 50% it is not. Scenario 13 does not discriminate it — at $52,150 the household qualifies under either tier with the same value. If this scenario is ever dropped, the spec's central policy decision has no test.

### Scenario 21: Homeowner With a Mortgage, No Rent Reported — Eligible, $7,980

**What we're checking**: That `mortgage` is excluded from the gross-rent proxy. Deliberately Scenario 1's household with a mortgage added and no rent, so only the mortgage can explain any difference — the same pairing idiom Scenario 19 uses for rent.

**Expected**: Eligible — **$7,980/year** — Wichita, KS HMFA (ZIP 67202) FY2026 SAFMR 2BR proxy $1,180/mo. Gross annual income $21,600. 2 dependents × $500 = $1,000 → adjusted $20,600 → monthly adjusted $1,716.67. TTP = max(0.30 × $1,716.67 = $515, 0.10 × $1,800 = $180, $0) = $515/mo. No rent is reported, so `calc_expenses("monthly", ["rent"])` returns $0 and the proxy falls back to the payment standard: HAP = $1,180 − $515 = $665/mo × 12 = **$7,980/yr**.

**Steps**:
- **Location**: ZIP code `67202`, county `Sedgwick`
- **Household**: `3` people
- **Person 1**: Birth month/year `March 1991` (age 35), Relationship: Head of Household, Has income: Yes, Employment income: `$1,800/month`
- **Person 2**: Birth month/year `September 2016` (age 9), Relationship: Child, Has income: No
- **Person 3**: Birth month/year `January 2020` (age 6), Relationship: Child, Has income: No
- **Expenses**: Mortgage: `$700/month` (no rent reported)
- **Current Benefits**: Section 8 / HCV: No

**Why this matters**: Kills a calculator that reads `["rent", "mortgage"]`, as WA and TX both do. Including the mortgage caps the proxy at $700 and returns $2,220 — a $5,760 understatement. Without this scenario a calculator copied from either sibling passes the entire suite undetected, because Scenario 19 is otherwise the only scenario reporting any expense and it reports rent.

### Scenario 22: Elderly Couple, Both 62+ — Eligible, $5,148

**What we're checking**: That the elderly/disabled deduction is taken **once per family**, not once per qualifying member. The only scenario with two qualifying head/spouse members.

**Expected**: Eligible — **$5,148/year** — Wichita, KS HMFA (ZIP 67202) FY2026 SAFMR 1BR proxy $910/mo (2-person household → 1BR). Combined gross annual income $19,800 ($950 + $700 = $1,650/mo), below the Wichita 2-person VLI limit of $38,600. No dependents. Head and spouse are both 62+, so the elderly/disabled family deduction applies **once**: adjusted annual $19,800 − $550 = $19,250 → monthly adjusted $1,604.1667. TTP = max(0.30 × $1,604.1667 = $481.25 → $481, 0.10 × $1,650 = $165, $0) = $481/mo. HAP = $910 − $481 = $429/mo × 12 = **$5,148/yr**. (Divergence D4)

**Steps**:
- **Location**: ZIP code `67202`, county `Sedgwick`
- **Household**: `2` people
- **Person 1**: Birth month/year `March 1958` (age 68), Relationship: Head of Household, Has income: Yes, Income type: Social Security (`sSRetirement`), Amount: `$950/month`
- **Person 2**: Birth month/year `June 1961` (age 65), Relationship: Spouse, Has income: Yes, Income type: Social Security (`sSRetirement`), Amount: `$700/month`
- **Current Benefits**: Section 8 / HCV: No

**Why this matters**: Kills an elderly/disabled deduction summed over qualifying head and spouse members. At $1,100 the adjusted income is $18,700, TTP $468, HAP $442 and the value $5,304 — a $156 difference. No other scenario can catch this: Scenarios 5 and 6 are sole members, Scenario 7 has one elderly head, and Scenario 8 has an elderly parent who is neither head nor spouse, so summing over head/spouse returns the identical value in all four. Tests MFB simplification, not verified policy (D4): the $550 elderly deduction taken once here is D4's CY2026 figure.

## Research Sources

| Snapshot | Tier | Title | URL | Retrieved |
|---|---|---|---|---|
| `2026-09-09--24-cfr-248-101` | 1 | 24 CFR 248.101 — Definitions (moderate income families) | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=248&section=248.101 | 2026-09-09 |
| `2026-09-09--24-cfr-5-403` | 1 | 24 CFR 5.403 — Definitions (family, elderly family, disabled family) | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=5&section=5.403 | 2026-09-09 |
| `2026-09-09--24-cfr-5-506` | 1 | 24 CFR 5.506 — General provisions (restrictions on assistance, mixed families) | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=5&section=5.506 | 2026-09-09 |
| `2026-09-09--24-cfr-5-603` | 1 | 24 CFR 5.603 — Definitions (annual income, adjusted income, dependent, net family assets) | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=5&section=5.603 | 2026-09-09 |
| `2026-09-09--24-cfr-5-609` | 1 | 24 CFR 5.609 — Annual income | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=5&section=5.609 | 2026-09-09 |
| `2026-09-09--24-cfr-5-611` | 1 | 24 CFR 5.611 — Adjusted income | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=5&section=5.611 | 2026-09-09 |
| `2026-09-09--24-cfr-5-612` | 1 | 24 CFR 5.612 — Restrictions on assistance to students enrolled in an institution of higher education | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=5&section=5.612 | 2026-09-09 |
| `2026-09-09--24-cfr-5-617` | 1 | 24 CFR 5.617 — Disallowance of increase in annual income (Earned Income Disallowance) | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=5&section=5.617 | 2026-09-09 |
| `2026-09-09--24-cfr-5-618` | 1 | 24 CFR 5.618 — Restrictions on assistance to families with assets | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=5&section=5.618 | 2026-09-09 |
| `2026-09-09--24-cfr-5-628` | 1 | 24 CFR 5.628 — Total tenant payment | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=5&section=5.628 | 2026-09-09 |
| `2026-09-09--24-cfr-5-630` | 1 | 24 CFR 5.630 — Minimum rent | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=5&section=5.630 | 2026-09-09 |
| `2026-09-09--24-cfr-888-113` | 1 | 24 CFR 888.113 — Fair market rents: methodology and Small Area FMR designation | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=888&section=888.113 | 2026-09-09 |
| `2026-09-09--24-cfr-982-4` | 1 | 24 CFR 982.4 — Definitions (gross rent, rent to owner, utility allowance) | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=982&section=982.4 | 2026-09-09 |
| `2026-09-09--24-cfr-982-201` | 1 | 24 CFR 982.201 — Eligibility and targeting | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=982&section=982.201 | 2026-09-09 |
| `2026-09-09--24-cfr-982-207` | 1 | 24 CFR 982.207 — Waiting list: Local preferences in admission to program | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=982&section=982.207 | 2026-09-09 |
| `2026-09-09--24-cfr-982-402` | 1 | 24 CFR 982.402 — Subsidy standards | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=982&section=982.402 | 2026-09-09 |
| `2026-09-09--24-cfr-982-503` | 1 | 24 CFR 982.503 — Payment standard areas, schedule, and amounts | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=982&section=982.503 | 2026-09-09 |
| `2026-09-09--24-cfr-982-505` | 1 | 24 CFR 982.505 — How to calculate housing assistance payment | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=982&section=982.505 | 2026-09-09 |
| `2026-09-09--24-cfr-982-552` | 1 | 24 CFR 982.552 — PHA denial or termination of assistance for family | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=982&section=982.552 | 2026-09-09 |
| `2026-09-09--24-cfr-982-553` | 1 | 24 CFR 982.553 — Denial of admission and termination of assistance for criminals and alcohol abusers | https://www.ecfr.gov/api/versioner/v1/full/2026-08-24/title-24.xml?part=982&section=982.553 | 2026-09-09 |
| `2026-09-09--hud-50058-instruction-booklet-2024` | 2 | Form HUD-50058 Family Report Instruction Booklet (effective January 1, 2024, updated 6/17/2026) | https://www.hud.gov/sites/default/files/PIH/documents/50058-Instruction-Booklet.pdf | 2026-09-09 |
| `2026-09-09--hud-cy2026-inflation-adjusted-values` | 2 | HUD — 2026 HUD Inflation-Adjusted Values (Table 1), effective January 1, 2026 | https://www.huduser.gov/portal/sites/default/files/datasets/inflationary-adjustments/CY2026-Revised-Amounts-And-Passbook-Rate.pdf | 2026-09-09 |
| `2026-09-09--hud-fy2026-fmr-schedule` | 2 | HUD — FY2026 Schedule of Metropolitan & Nonmetropolitan Fair Market Rents | https://www.huduser.gov/portal/datasets/fmr/fmr2026/FY2026_FMR_Schedule.pdf | 2026-09-09 |
| `2026-09-09--hud-fy2026-income-limits-wichita` | 2 | HUD USER — FY2026 Income Limits Summary, Wichita, KS HUD Metro FMR Area (Sedgwick County) | https://www.huduser.gov/datasets/il/il2026/summary?year=2026&reporttype=county&states=20&counties=2017399999 | 2026-09-09 |
| `2026-09-09--hud-fy2026-income-limits-topeka` | 2 | HUD USER — FY2026 Income Limits Summary, Topeka, KS MSA (Shawnee County) | https://www.huduser.gov/datasets/il/il2026/summary?year=2026&reporttype=county&states=20&counties=2017799999 | 2026-09-09 |
| `2026-09-09--hud-fy2026-income-limits-kansas-city` | 2 | HUD USER — FY2026 Income Limits Summary, Kansas City, MO-KS HUD Metro FMR Area (Wyandotte County) | https://www.huduser.gov/datasets/il/il2026/summary?year=2026&reporttype=county&states=20&counties=2020999999 | 2026-09-09 |
| `2026-09-09--hud-fy2026-safmrs` | 2 | HUD — FY2026 Small Area Fair Market Rents (SAFMRs), all ZIP codes | https://www.huduser.gov/portal/datasets/fmr/fmr2026/FY2026_SAFMRs.xlsx | 2026-09-09 |
| `2026-09-09--hud-hcv-guidebook-payment-standards` | 2 | HUD HCV Program Guidebook — Payment Standards (June 2025, HOTMA-updated) | https://www.hud.gov/sites/dfiles/PIH/documents/HCV_Guidebook_Payment-Standards_June-2025_final.pdf | 2026-09-09 |
| `2026-09-09--hud-hcv-guidebook-rent-and-hap` | 2 | HUD HCV Program Guidebook — Calculating Rent and Housing Assistance Payments (HAP) (November 2019) | https://www.hud.gov/sites/dfiles/PIH/documents/HCV_Guidebook_Calculating_Rent_and_HAP_Payments.pdf | 2026-09-09 |
| `2026-09-09--hud-pih-2026-15` | 2 | HUD Notice PIH 2026-15 — HOTMA Sections 102 and 104 compliance enforcement date | https://www.hud.gov/sites/default/files/hudclips/documents/PIH-2026-15.pdf | 2026-09-09 |
| `2026-09-09--wichita-hcv-admin-plan-2026` | 3 | Wichita Housing Authority — HCV Administrative Plan (approved 10/7/2025, effective 1/1/2026) | https://www.wichita.gov/DocumentCenter/View/35489/2026-Adminstrative-Plan-PDF | 2026-09-09 |
