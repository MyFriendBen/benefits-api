# Commodity Supplemental Food Program (CSFP) (MO) — Program Spec

- **Program key**: `mo_csfp` (proposed — `programs/programs/cross_white_label/csfp/mo.py`, class `MoCsfp`)
- **Base federal program**: Commodity Supplemental Food Program (U.S. Department of Agriculture), 7 CFR part 247
- **White label**: MO
- **Engine**: PolicyEngine
- **Added to MFB**: not yet added
- **Spec last updated**: 2026-09-28
- **Sources verified as of**: 2026-09-25
- **Scenarios last run**: 2026-09-25 — 17/17 through the calculator → PolicyEngine private API, at PE 2.5.0 (`current`) and 2.9.0 (`frontier`)

## Covered Eligibility Criteria

CSFP is a federal USDA nutrition program administered in Missouri by the Department of Health and
Senior Services through contracted Feeding America food banks, which serve as sole-source local
agencies under the State Plan.

**Scope**: new CSFP applicants age 60+ only. Missouri also serves a closed population of women, infants, and children certified on or before 2014-02-06 under pre-2014 rules (Agricultural Act of 2014, P.L. 113-79); no new certifications into that population have been possible since 2014-02-07, and it is out of scope for this calculator.

Both criteria must hold.

1. **Individuals must be at least 60 years of age.**
   - Evaluation scope: `member`
   - Captured via: `birth_year_month` (HouseholdMember, DateField, nullable); accessors `birth_year()`, `birth_month()`, `calc_age()`. Constant `gov.usda.csfp.min_age` = 60 — federal, unchanged by Missouri
   - Comparator: `>=` 60. A person turning 60 in the reference month is eligible
   - Source: 7 CFR § 247.9(a) — "To be eligible for CSFP, individuals must be at least 60 years of age" — [snapshot `2026-09-25--7-cfr-247-9`](../../../sources/mo/mo_csfp/2026-09-25--7-cfr-247-9/content.md), accessed 2026-09-25

2. **The State agency must use a household income limit at or below 150 percent of the Federal Poverty Guidelines.**
   - Evaluation scope: `household`
   - Captured via: `type`, `amount`, `frequency` (IncomeStream, CharField / DecimalField / CharField); accessor `calc_gross_income(...)`. Constant `gov.usda.csfp.fpg_limit` = 1.5
   - Comparator: `<=` — a household exactly at the limit is eligible
   - Code divergence: **D1** — PolicyEngine's CSFP chain derives countable income from the school-meals source list, which omits workers' compensation, alimony and any capital-gains term; Missouri counts all three. MFB supplies the countable-income total so the sourced rule prevails. Full entry in the companion's Divergences registry
   - Source: 7 CFR § 247.9(b) — "The State agency must use a household income limit at or below 150 percent of the U.S. Federal Poverty Guidelines" — [snapshot `2026-09-25--7-cfr-247-9`](../../../sources/mo/mo_csfp/2026-09-25--7-cfr-247-9/content.md), accessed 2026-09-25
   - Source: 7 CFR § 247.9(d)(1), CSFP's own income definition — "gross income before deductions for such items as income taxes, employees' social security taxes, insurance premiums, and bonds" — [snapshot `2026-09-25--7-cfr-247-9`](../../../sources/mo/mo_csfp/2026-09-25--7-cfr-247-9/content.md), accessed 2026-09-25
   - Source: Missouri State Plan, electing the maximum permitted level and recording that "Household income information is self-declared" — [snapshot `2026-09-25--mo-csfp-state-plan-ffy2026`](../../../sources/mo/mo_csfp/2026-09-25--mo-csfp-state-plan-ffy2026/content.md), accessed 2026-09-25
   - Source: USDA FNS, CSFP income guidelines for 2026, effective 2026-02-10 — HH1 $23,940/yr ($1,995/mo); HH2 $32,460; HH3 $40,980; HH4 $49,500; +$8,520/yr per additional member — [snapshot `2026-09-25--fns-csfp-income-guidelines`](../../../sources/mo/mo_csfp/2026-09-25--fns-csfp-income-guidelines/content.md), accessed 2026-09-25

PolicyEngine's `spm_unit_fpg` returns $15,960 (HH1) and $21,640 (HH2) for 2026, reproducing the
USDA thresholds exactly at the 1.5 multiplier.

#### Income exclusions

Missouri's State Plan elects to exclude all income sources permitted to be excluded under 7 CFR § 247.9(d)(2), plus those required to be excluded under § 247.9(d)(3).

**No screener income type currently falls in the excluded set.** Policy Manual § 2.5 lists what Missouri excludes — in-kind housing and other benefits, bartered services, volunteer payments, named federal programs, a developmental-disability stipend, and tax refunds including the EITC — and MFB collects no income type that lands in it. MFB's taxonomy (`configuration/white_labels/base.py`) has no student-financial-assistance category either, which is the principal § 247.9(d)(3) mandatory exclusion — [snapshot `2026-09-25--mo-csfp-policy-manual-02-05-income-exclusions-2017`](../../../sources/mo/mo_csfp/2026-09-25--mo-csfp-policy-manual-02-05-income-exclusions-2017/content.md), accessed 2026-09-25.

#### Countable-income category mapping

Missouri's CSFP Policy and Procedure Manual § 2.4 (Participant Income, revised 12-2005) sets out
what the local agency counts. It reaches the categories PolicyEngine's own CSFP source list omits:
"Workmen's compensation" (the Manual's term for workers' compensation), "Alimony received",
"Child support received", "Dividends or interest received", "Withdrawal from savings or
investments" and "Capital gains" — [snapshot `2026-09-25--mo-csfp-policy-manual-02-04-participant-income-2017`](../../../sources/mo/mo_csfp/2026-09-25--mo-csfp-policy-manual-02-04-participant-income-2017/content.md), accessed 2026-09-25.

**Two categories are counted net, not gross.** § 2.4 counts "Net income (gross receipts less
operating expenses)" from farming and non-farming self-employment, rental property and royalties.
MFB sends the gross amount the screener collects, so a household with `selfEmployment` or `rental`
income has its countable income overstated by its operating expenses. The direction is
**restrictive** — it can screen a household out that Missouri would certify. The screener collects
no operating-expense field, so the net figure cannot be reconstructed; see Missing Eligibility
Criteria 6.

MFB computes the CSFP countable total and sends it as `school_meal_countable_income`. The shared
`CsfpCountableIncomeDependency` (benefits-api, MFB-1879) builds it as
`calc_gross_income("yearly", ["all"])`, so **every screener income type counts** and there is no
per-type list to maintain.

Every category below is therefore counted by construction. The routing column records which PE
variable the money *would* have travelled through had PolicyEngine derived the total, and whether
PE's own CSFP source list would have counted it — the right-hand column is why the override exists.

| MFB category | If PE derived the total | PE would count it | Note |
| --- | --- | --- | --- |
| `wages` | `employment_income` | Yes | |
| `selfEmployment` | `self_employment_income` | Yes | |
| `rental` | `rental_income` | Yes | |
| `pension` | `pension_income` | Yes | |
| `veteran` | `pension_income`, or `veterans_benefits` | Yes | Routing is moot under the override — MFB counts the stream once, from `veteran` |
| `sSDisability`, `sSRetirement`, `sSSurvivor`, `sSDependent` | `social_security` | Yes | |
| `sSI` | `ssi` | Yes | MFB counts the household's **reported** SSI. No receipt contract is needed: a fixed total suppresses PE's simulated SSI entirely |
| `cashAssistance` (TANF) | `tanf` | Yes | Since MFB-1697 (#1735, 2026-09-03) this MFB key is the **TANF-only** field — `receipt.py`'s `TANF_INCOME_TYPE` |
| `cashAssistanceOther` | `financial_assistance` | Yes | Added by MFB-1697. MFB never sends `gi_cash_assistance` |
| `childSupport` | `child_support_received` | Yes | PE added it 2026-08-14 (#9279) — Scenario 8 |
| `unemployment` | `unemployment_compensation` | Yes | Scenario 11 |
| `deferredComp` | `taxable_ira_distributions` → `retirement_distributions` | Yes | Scenario 12 |
| `gifts` | `miscellaneous_income` | Yes | |
| `workersComp` | `workers_compensation` | **No** — absent from PE's CSFP source list | **Only counted because MFB supplies the total** — Scenario 9 |
| `alimony` | `alimony_income` | **No** — absent from PE's CSFP source list | **Only counted because MFB supplies the total** — Scenario 10 |
| `investment` | `long_term_capital_gains` | **No** — no capital-gains term in the CSFP chain | **Only counted because MFB supplies the total** — Scenario 13 |
| `boarder` | no PE variable in this chain | — | Counted as gross income under § 247.9(d)(1) — see Data Gap 5, whose residual is household membership, not the payment |

Every Missouri income type is counted, `boarder` included. What remains a data gap is not the
payment but the payer — see Missing Eligibility Criteria 5.

#### `investment` — countable in full

MFB combines interest, dividends, and stock-sale profits into one income type. **The missing
subtype is not load-bearing**, because Missouri counts every subtype it could represent: the
Policy Manual § 2.4 counts "Dividends or interest received" on page 1, and on page 2 counts
"Withdrawal from savings or investments" and "Capital gains" as other cash income — [snapshot
`2026-09-25--mo-csfp-policy-manual-02-04-participant-income-2017`](../../../sources/mo/mo_csfp/2026-09-25--mo-csfp-policy-manual-02-04-participant-income-2017/content.md), accessed 2026-09-25. 7 CFR
§ 247.9(d)(1) is consistent, defining CSFP income as "gross income before deductions for such
items as income taxes, employees' social security taxes, insurance premiums, and bonds."

Whichever subtype an MFB `investment` amount represents, the policy-correct result is to count it,
so the whole bucket goes into the CSFP total. Counting it via the total also avoids the
alternative MFB could not safely take — re-routing the bucket to `dividend_income` or
`interest_income`, which are shared tax inputs in the same PE situation, so mis-categorising
capital gains through them would alter other programs' results on the same screen.

### Rules that do not apply

- **No citizenship or immigration-status gate.** CSFP falls under 8 U.S.C. § 1615, which neither requires nor prohibits state coverage of non-qualified immigrants, and Missouri's State Plan and DHSS eligibility page impose no such gate. `configs/mo/mo_csfp.initial_config.json` sets all six user-selectable `legal_status_required` values, which is the unrestricted pattern.
- **No asset test.** None is imposed by federal rule or modeled by PE.
- **One site at a time is an agency duty, not an applicant criterion.** Missouri's application asks whether the household already participates at another site, but the State Plan places detection on the local agency: Missouri State Plan § 9, Detection of Dual Participation — "Local agencies are required to establish safeguards against dual participation at more than one CSFP site at the same time by establishing procedures that identify participants who are participating in two different distribution sites." — [snapshot `2026-09-25--mo-csfp-state-plan-ffy2026`](../../../sources/mo/mo_csfp/2026-09-25--mo-csfp-state-plan-ffy2026/content.md), accessed 2026-09-25. Classified the same way as KS CSFP. MFB does not ask, and `show_in_has_benefits_step` stays `false`.
- **No adjunctive/categorical income-eligibility pathway for initial applicants.** 7 CFR § 247.9(b)(1)–(2) permits states to accept participation in SNAP, FDPIR, SSI, Low Income Subsidy, or a Medicare Savings Program as evidence of income eligibility, but Missouri's 2026 State Plan establishes that pathway only in the annual informal certification process for existing participants, not for initial certification. Apply the ordinary 150% FPG test.
  - **Watch upstream.** PolicyEngine's *federal* CSFP formula now ORs a categorical term into the income test unconditionally — `income_eligible | person("ks_dcf_csfp_categorically_eligible", period)` — and Missouri is held out of it only by `defined_for = StateCode.KS` on that variable, not by anything in the federal formula. Missouri is unaffected today. If that guard is removed or the variable generalised, Missouri would silently gain a pathway this spec says it does not have, and no scenario here would catch it.

## Missing Eligibility Criteria (Data Gaps)

Citations here are four-part, as everywhere else in this spec.

1. **The unit whose income is measured is the CSFP household — those who customarily purchase food and prepare meals together — which is not always everyone on the screen.**
   - Why: 7 CFR 250.2 defines the CSFP household by purchase-and-prepare, so a senior living with others but buying and cooking separately is their own household and only their own income counts. The screener collects no purchase-and-prepare field, and none is being added, so MFB necessarily measures everyone on the screen.
   - Handling: inclusive in effect — MFB does not reconstruct the household and does not override PolicyEngine's grouping. PolicyEngine aggregates at the SPM unit, which is family/co-residency based rather than purchase-and-prepare, so the pooled reading is **usually** the restrictive one. It is not always: pooling raises measured income *and* household size together, and the threshold rises $8,520 per additional member (2026). Whenever a co-resident's own income is **at or below that increment**, pooling raises the threshold by more than it raises income, and MFB is permissive — a senior whose own income is over the one-person limit is scored eligible and shown the card, and the local agency then measures the smaller purchase-and-prepare household and denies. Worked: senior $25,000, co-resident $0 → MFB reads $25,000 against the two-person $32,460 and passes, where the senior alone is $1,060 over the $23,940 one-person limit. A boarder is one member of that class (gap 5), not the only one — any low-income co-resident does it. Surfaced in `program.description`, which tells a senior living with a higher-earning relative to apply and say so rather than be deterred.
   - Source: 7 CFR § 250.2, defining the household — "any of the following individuals or groups of individuals, exclusive of boarders or residents of an institution" — [snapshot `2026-09-25--7-cfr-250-2`](../../../sources/mo/mo_csfp/2026-09-25--7-cfr-250-2/content.md), accessed 2026-09-25
   - Source: 7 CFR § 250.2, confirming the definition reaches CSFP — "Household programs means CSFP, FDPIR, and TEFAP." — [snapshot `2026-09-25--7-cfr-250-2`](../../../sources/mo/mo_csfp/2026-09-25--7-cfr-250-2/content.md), accessed 2026-09-25
   - Source: PolicyEngine, `commodity_supplemental_food_program_eligible`, reading `person.spm_unit("school_meal_fpg_ratio", period)` under the in-source annotation "Assume resources are counted at the SPM unit level." — read at `b8ca61a2`, 2026-09-10

2. **Missouri may certify on the household's average income over the previous 12 months where current income is not representative.**
   - Why: MFB observes only the income reported in the current screener. It holds no income history, and it cannot determine whether Missouri's "When warranted" condition applies.
   - Handling: MFB counts current income only. It does not invent a prior-period amount and does not choose which period controls, so its estimate may be either stricter or more generous than the local agency's determination. Surfaced in `program.description`.
   - Source: Missouri State Plan, income determination — "When warranted, all local agencies consider the household’s average income during the previous 12 months and current household income to determine which more accurately reflects the household’s status per 7 CFR 247.9(d)(4)." — [snapshot `2026-09-25--mo-csfp-state-plan-ffy2026`](../../../sources/mo/mo_csfp/2026-09-25--mo-csfp-state-plan-ffy2026/content.md), accessed 2026-09-25
   - Source: 7 CFR § 247.9(d)(4), the federal option this implements — [snapshot `2026-09-25--7-cfr-247-9`](../../../sources/mo/mo_csfp/2026-09-25--7-cfr-247-9/content.md), accessed 2026-09-25

3. **Eligibility requires residence within a local agency's service area, and no source publishes county-to-service-area boundaries.**
   - Why: the operative rule is service-area residency, not a fixed county list. `zipcode` and `county` (both `Screen`) establish Missouri location but cannot establish local-agency service-area membership, and Missouri expressly permits agencies to serve residents of counties outside their normal area.
   - Handling: inclusive — county of residence never causes a denial, and no `MoCountyDependency` is added. PolicyEngine has no Missouri county branch: `commodity_supplemental_food_program_eligible` selects a county test only for KS, MA and IL and defaults to `True` otherwise. Surfaced in `program.description`, which tells the applicant the local agency confirms where they can collect. Scenario 14 asserts the corollary the spec commits to.
   - Source: Missouri State Plan, Residency Requirement — "Persons eligible for Missouri’s CSFP must reside in the state of Missouri and within the service area of the local agency. There are no duration or fixed residency requirements. Migrant and seasonal farm workers shall be considered as meeting the residency requirement. Local agencies are authorized to serve residents from counties outside their normal service area as long as the area served does not overlap another local agency’s service area." — [snapshot `2026-09-25--mo-csfp-state-plan-ffy2026`](../../../sources/mo/mo_csfp/2026-09-25--mo-csfp-state-plan-ffy2026/content.md), accessed 2026-09-25
   - Source: PolicyEngine removed a short-lived Missouri county allowlist in `fe1cb9ab45` on 2026-08-14, on the rationale that the program covers all Missouri counties — verified absent from the deployed API 2026-09-10

4. **Participants living in nursing homes are ineligible, and MFB does not collect institutional-residence status.**
   - Why: the screener has no nursing-home or institutional-residence field.
   - Handling: inclusive — assume the applicant satisfies the requirement; never deny on this criterion. Surfaced in `program.description`.
   - Source: Missouri State Plan, Residency Requirement — "Participants living in nursing homes are not eligible for CSFP benefits." — [snapshot `2026-09-25--mo-csfp-state-plan-ffy2026`](../../../sources/mo/mo_csfp/2026-09-25--mo-csfp-state-plan-ffy2026/content.md), accessed 2026-09-25

5. **Boarders are excluded from the CSFP household, and no screener field identifies one — ⚠️ Data Gap (MO-CSFP-BOARDER).** Partial: the income half is measurable and committed below; only the membership half is a gap.
   - Why: the criterion has two halves, and only one is screenable. **The money is:** MFB collects a `boarder` income stream with amount and frequency, so the payment itself is fully observable. **The person is not:** 7 CFR § 250.2 excludes a boarder from household membership, and MFB's fifteen `relationship` options contain no `boarder` or `lodger` — the nearest, `roommate`, describes someone who shares costs rather than pays for room and meals. So when a boarder is entered on the screen, MFB cannot exclude them from the unit.
   - Handling, committed: **count the payment; do not attempt to reconstruct the unit.** The payment is ordinary gross income under § 247.9(d)(1). A State agency's discretion to exclude is a closed two-item list — military basic allowance for housing off-installation, and the value of in-kind housing and benefits — and cash from a boarder is neither, so no Missouri election could make it non-countable. The shipped all-types total therefore already does the policy-correct thing, and `benefits-api`'s note that `boarder` "arguably belongs in `rental_income`" points the same way: `rental` is counted without qualification.
   - Residual limitation, and its direction: where the boarder is **also entered on the screen**, two errors run in opposite directions — their own income is pooled in, which is restrictive, while they raise household size and so raise the FPG threshold, which is permissive. Neither is correctable without a field, and the net direction is not signable in general. **Not separately surfaced in `program.description`**, and deliberately so: the permissive half puts the household in front of the card, where the copy's existing "The site where you apply makes the final decision" already covers it, and the restrictive half screens the household out, where no description can reach them. This is the residual of gap 1 as it applies to boarders specifically.
   - Source: Missouri CSFP Policy and Procedure Manual § 2.4 and § 2.5 — boarder income appears in neither the list of income the local agency counts nor the list it excludes, which is the silence this gap records — [snapshot `2026-09-25--mo-csfp-policy-manual-02-04-participant-income-2017`](../../../sources/mo/mo_csfp/2026-09-25--mo-csfp-policy-manual-02-04-participant-income-2017/content.md) and [snapshot `2026-09-25--mo-csfp-policy-manual-02-05-income-exclusions-2017`](../../../sources/mo/mo_csfp/2026-09-25--mo-csfp-policy-manual-02-05-income-exclusions-2017/content.md), accessed 2026-09-25
   - Source: 7 CFR § 250.2, defining the household and excluding boarders from it — "Household means any of the following individuals or groups of individuals, exclusive of boarders or residents of an institution" — [snapshot `2026-09-25--7-cfr-250-2`](../../../sources/mo/mo_csfp/2026-09-25--7-cfr-250-2/content.md), accessed 2026-09-25
   - Source: 7 CFR § 247.9(d)(1), the income definition that governs the payment — "Income means gross income before deductions for such items as income taxes, employees' social security taxes, insurance premiums, and bonds" — [snapshot `2026-09-25--7-cfr-247-9`](../../../sources/mo/mo_csfp/2026-09-25--7-cfr-247-9/content.md), accessed 2026-09-25
   - Source: 7 CFR § 247.9(d)(2), the closed list of what a State agency may elect to exclude — "may exclude from consideration the following sources of income: (i) Any basic allowance for housing received by military services personnel residing off military installations; and (ii) The value of inkind housing and other inkind benefits." — [snapshot `2026-09-25--7-cfr-247-9`](../../../sources/mo/mo_csfp/2026-09-25--7-cfr-247-9/content.md), accessed 2026-09-25
6. **Self-employment and rental income are counted gross, where Missouri counts them net of operating expenses.**
   - Why: Policy Manual § 2.4 counts "Net income (gross receipts less operating expenses)" from farming self-employment, non-farming self-employment, rental property and royalties. The screener collects an income amount and frequency but no operating-expense field, so MFB cannot compute the net figure and sends the gross amount.
   - Handling: count gross, and never treat the resulting figure as the local agency's determination. The direction is **restrictive**: a household with deductible operating expenses has its countable income overstated and may be screened out where Missouri would certify. **Not surfaced in `program.description`**, because the direction forbids it: the household this gap harms is screened out and never sees the card, so the copy would reach only applicants already found eligible on gross, for whom the net figure changes nothing.
   - Source: Missouri CSFP Policy and Procedure Manual § 2.4, Participant Income (revised 12-2005) — "Net income (gross receipts less operating expenses) from:" — [snapshot `2026-09-25--mo-csfp-policy-manual-02-04-participant-income-2017`](../../../sources/mo/mo_csfp/2026-09-25--mo-csfp-policy-manual-02-04-participant-income-2017/content.md), accessed 2026-09-25

## Priority Criteria

Per the Missouri State Plan (§ 247.6(c)(10)): when applications exceed the assigned CSFP caseload level, homebound participants are given priority over non-homebound participants. This is a local-agency waitlist rule. It does not affect calculator eligibility or value and needs no test scenario or ranking logic.

## Benefit Value

- **Value**: $651/year per eligible participant (= national FY2026 appropriation ÷ national caseload slots, $460,000,000 ÷ 707,000 = $650.64 → $651)
- **`value_format`**: `null` — annualised. `configs/mo/mo_csfp.initial_config.json` leaves it unset, deferring to MFB's default frontend formatter, which sums the annual value across eligible members, divides the household total by 12, and formats to whole dollars. Not a one-time benefit; the package is distributed monthly
- **Variation axes**: flat — the amount is federal, set at `gov.usda.csfp.amount` under `gov.usda` rather than `gov.states.mo`, so Missouri neither sets nor varies it. The only axis is the **number of eligible participants**, which is exercised by Scenarios 4 and 7
- **Source**: USDA FNS, CSFP Caseload Assignments for the 2026 Caseload Cycle (memo dated 2025-12-19) — "which provides $460 million for the CSFP for fiscal year (FY) 2026" and "FNS is issuing a final national caseload allocation of 707,000 slots for the 2026 caseload cycle (January 1, 2026 to December 31, 2026)" — [snapshot `2026-09-25--fns-csfp-caseload-2026`](../../../sources/mo/mo_csfp/2026-09-25--fns-csfp-caseload-2026/content.md), accessed 2026-09-25
- **Justification**: the dollar figure is a **valuation estimate of a monthly in-kind food package**, not a cash benefit, a participant entitlement, or a promise that a participant receives $651 of retail food. PolicyEngine derives it as appropriation ÷ slots, which is the only published basis for a per-participant figure.

**Per person, not per household.** `commodity_supplemental_food_program` is a Person-entity
variable, `defined_for = "commodity_supplemental_food_program_eligible"`. Value is computed and
summed per eligible member, with no one-per-household cap.

**Sum first, then divide.** Do not round each member's monthly value and then sum.

| Eligible participants | Annual valuation | MFB display |
| ---: | ---: | ---: |
| 1 | $651/year | $54/month |
| 2 | $1,302/year | $109/month |

$1,302 ÷ 12 = $108.50 → **$109**. Rounding per person first and summing gives $108, which is
wrong. Do not build a custom monthly-conversion rule or a bespoke `value_format` for this program.

## Test Scenarios

Scenarios 8–13 and 15 share one structure: $21,600 of `wages` plus $3,000 of one further income
type, totalling $24,600 against the $23,940 one-person limit, so the type under test is solely
responsible for the result. Each scenario states its own location.

**Coverage map**

| Rule / variation axis | Scenarios |
|---|---|
| Age ≥ 60, evaluated per member | 2 (59, just under), 5 (exactly 60), 7 (only the senior qualifies) |
| The age gate resolves to the month, not the year | 17 (turns 60 in the reference month) |
| Income ≤ 150% FPG, one-person limit | 1 (under), 6 (exactly at), 3 (one dollar over → fail) |
| The limit rises with household size | 16 (two-person, $28,000 — between the one- and two-person limits, so it fails if the threshold stops scaling) |
| Income counted is gross, before deductions | 3, 8–13, 15 |
| MFB supplies the countable-income total, not PolicyEngine | 9, 10, 13 — the three categories PE's own source list omits |
| Each income type reaches the countable total | 8 (`childSupport`), 9 (`workersComp`), 10 (`alimony`), 11 (`unemployment`), 12 (`deferredComp`), 13 (`investment`), 15 (`cashAssistanceOther`); `wages` throughout |
| No receipt contract is needed | 6 — passes at exactly the limit with no phantom SSI |
| Value is per qualifying individual, uncapped | 4 (two qualify → $1,302), 7 (one of two → $651) |
| Household display sums first, then divides by 12 | 4 ($1,302 ÷ 12 → $109, not $54 × 2) |
| County never causes a denial | 14 (declared-inputs assertion) |
| `state_code` reaches PolicyEngine as `MO` | all — asserted on the request in every scenario |
| Missouri | all — every scenario is a Missouri screen |

**Known scenario gaps.** Nine things are unscreened. Items 1, 7 and 9 are screenable with
current fields and have no scenario; items 2–6 and 8 cannot be screened at all.

1. **Twelve of the twenty income types have no scenario** — `selfEmployment`, `rental`,
   `pension`, `veteran`, `sSDisability`, `sSSurvivor`, `sSRetirement`, `sSDependent`, `sSI`,
   `cashAssistance` (TANF), `gifts` and `boarder`. The shipped dependency counts all types from one
   accessor, so there is no per-type entry to delete and these are covered by the same code path
   the written scenarios exercise. `sSRetirement` and `sSI` remain the most consequential to get
   right, being the commonest income sources in a 60+ population.
2. The § 250.2 purchase-and-prepare household (Missing Eligibility Criteria 1) cannot be screened —
   no field distinguishes a shared food budget from a separate one, so every scenario pools the
   whole screen.
3. The prior-12-month income comparison (gap 2) cannot be screened — the screener holds no income
   history, so every scenario is measured on current income.
4. Local-agency service-area membership (gap 3) cannot be screened. Scenario 14 asserts the
   corollary the spec does commit to, that county alone never disqualifies.
5. Nursing-home residence (gap 4) cannot be screened — no field exists.
6. Gap 5's membership half gets no scenario, by the same rule as gaps 2–6: **data gaps are not
   scenario-tested.** Its income half is untested for the ordinary reason in item 1 — one accessor,
   one code path — and not because anything about it is open.
7. **"No asset test" has no scenario, and needs none.** `MoCsfp` sends `age`, the countable-income
   total and `state_code`; no asset variable is sent and PolicyEngine's formula reads none, so
   there is nothing for a scenario to hold in place.
8. **Self-employment and rental counted gross rather than net (gap 6) cannot be screened** — the
   screener collects no operating-expense field, so the net figure Missouri uses cannot be formed.
9. **"No adjunctive/categorical pathway for initial applicants" has no scenario.** A Missouri
   scenario cannot defend it: every categorical program sits below 150% FPG (SNAP at 130%, the
   Medicare Savings QI level at 135%), so anyone categorically eligible is already income-eligible
   for CSFP and the branch changes no result. The one case that would discriminate — a household
   over CSFP's gross limit but SNAP-eligible on net income after a senior's medical deductions —
   needs expense fields no scenario here exercises. See the upstream note under Rules that do not
   apply.

Legal status is not scenario-tested: `program.legal_status_required` is config metadata read after
calculator eligibility is determined and is never passed into the calculation, so it is a config
check rather than a screening branch. See Research Sources.

### Scenario 1: Single senior under the limit — Eligible, $651

**What we're checking**: the baseline path end to end — PolicyEngine's eligibility formula and its per-person valuation.

**Expected**: Eligible — $651/year, displayed as $651 ÷ 12 = **$54/month**

**Steps**:
* Location: ZIP `65201`, county `Boone County`
* Person 1: born June 1960 (age 66 in 2026), head of household, `birth_year_month` `1960-06-01`
* Income: `wages` $1,500/month ($18,000/yr)


---

### Scenario 2: Age 59 — Ineligible (age)

**What we're checking**: the age gate at the boundary, one year under, with the income gate satisfied.

**Expected**: Ineligible (age) — 59 < 60

**Steps**:
* Location: ZIP `65201`, county `Boone County`
* Person 1: born January 1967 (age 59 in 2026), head of household, `birth_year_month` `1967-01-01`
* Income: `wages` $1,500/month ($18,000/yr)


---

### Scenario 3: Income one dollar over the limit — Ineligible (income)

**What we're checking**: the income comparator is exclusive above the limit.

**Expected**: Ineligible (income) — $23,941 > $23,940

**Steps**:
* Location: ZIP `65201`, county `Boone County`
* Person 1: born June 1960 (age 66 in 2026), head of household, `birth_year_month` `1960-06-01`
* Income: `wages` $23,941/yr

**Why this matters**: does not test Missouri's unobservable prior-12-month comparison — only the income MFB can observe.

---

### Scenario 4: Two seniors — Eligible, $1,302

**What we're checking**: the value is per eligible person, and the household display sums before dividing.

**Expected**: Eligible — $651 × 2 = **$1,302/year**, displayed as $1,302 ÷ 12 = $108.50 → **$109/month**

**Steps**:
* Location: ZIP `65201`, county `Boone County`
* Person 1: born March 1958 (age 68 in 2026), head of household, `birth_year_month` `1958-03-01`, no income
* Person 2: born September 1960 (age 66 in 2026), spouse, `birth_year_month` `1960-09-01`
* Income: Person 2 `wages` $1,500/month ($18,000/yr)

**Why this matters**: confirms the benefit is computed per eligible person rather than capped at one per household, and that household-level display rounds sum-then-divide ($1,302 ÷ 12 = $108.50 → $109), not divide-then-sum ($108).

Person 2's income is $18,000 so both seniors qualify whether treated as two HH1 units or one HH2 unit. The expected result therefore does not hinge on the unobservable § 250.2 purchase/prepare fact.

---

### Scenario 5: Exactly age 60 — Eligible, $651

**What we're checking**: the age comparator is inclusive at 60, not strictly greater than.

**Expected**: Eligible — $651/year, displayed as **$54/month**

**Steps**:
* Location: ZIP `65201`, county `Boone County`
* Person 1: born January 1966 (age 60 in 2026), head of household, `birth_year_month` `1966-01-01`
* Income: `wages` $1,500/month ($18,000/yr)


---

### Scenario 6: Income exactly at the limit — Eligible, $651

**What we're checking**: the income comparator is inclusive at the limit, and that no receipt contract is needed.

**Expected**: Eligible — $23,940 = $23,940, so $651/year, displayed as **$54/month**

**Steps**:
* Location: ZIP `65201`, county `Boone County`
* Person 1: born June 1960 (age 66 in 2026), head of household, `birth_year_month` `1960-06-01`
* Income: `wages` $23,940/yr

**Why this matters**: confirms the modeled income comparator is inclusive (`<= 150% FPG`) when applied to the income reported through the MFB screener. It does not test the local agency's prior-12-month comparison. It also pins why no receipt contract is needed: because MFB supplies the total, PolicyEngine's simulated SSI never enters. Were MFB to stop supplying it *without* adding the receipt contract, PE would add $468 here and the scenario would flip to Ineligible.

---

### Scenario 7: One senior, one younger adult — Eligible, $651

**What we're checking**: the benefit is awarded per eligible person, not per household.

**Expected**: Eligible — $651/year for Person 1 only, not $1,302; displayed as **$54/month**

**Steps**:
* Location: ZIP `65201`, county `Boone County`
* Person 1: born June 1960 (age 66 in 2026), head of household, `birth_year_month` `1960-06-01`, no income
* Person 2: born April 1986 (age 40 in 2026), adult child, `birth_year_month` `1986-04-01`
* Income: Person 2 `wages` $1,200/month ($14,400/yr)

**Why this matters**: Person 2 fails the age gate and must not generate a benefit even though the household passes the income gate. The senior is income-eligible whether treated as an HH1 or HH2 unit, so the result does not hinge on the purchase/prepare fact.

---

### Scenario 8: Child support counted — Ineligible (income)

**What we're checking**: that `childSupport` reaches the CSFP countable-income total.

**Expected**: Ineligible (income) — countable income $21,600 + $3,000 = **$24,600**, above the $23,940 one-person limit

**Steps**:
* Location: ZIP `65201`, county `Boone County`
* Person 1: born June 1960 (age 66 in 2026), head of household, `birth_year_month` `1960-06-01`
* Income: `wages` $21,600/yr and `childSupport` $3,000/yr

**Why this matters**: `childSupport` is an existing MFB income type and PE counts `child_support_received`, so this is a mapping regression, not a data gap. Before MFB-1879 only the $21,600 reached PE and this returned a false Eligible.

---

### Scenario 9: Workers' compensation counted — Ineligible (income)

**What we're checking**: that `workersComp` reaches the CSFP countable-income total.

**Expected**: Ineligible (income) — countable income $21,600 + $3,000 = **$24,600**, above the $23,940 one-person limit

**Steps**:
* Location: ZIP `65201`, county `Boone County`
* Person 1: born June 1960 (age 66 in 2026), head of household, `birth_year_month` `1960-06-01`
* Income: `wages` $21,600/yr and `workersComp` $3,000/yr

**Why this matters**: Missouri's Policy Manual § 2.4 counts "Workmen's compensation", and PE's CSFP source list does not include `workers_compensation`: were PolicyEngine to derive the total, countable income would stay at $21,600 and the household would be found eligible. This is one of the three categories that only pass **because** MFB supplies the total. It is the regression test for the override: narrow the countable total back to the school-meals list and this scenario fails.

---

### Scenario 10: Alimony counted — Ineligible (income)

**What we're checking**: that `alimony` reaches the CSFP countable-income total.

**Expected**: Ineligible (income) — countable income $21,600 + $3,000 = **$24,600**, above the $23,940 one-person limit

**Steps**:
* Location: ZIP `65201`, county `Boone County`
* Person 1: born June 1960 (age 66 in 2026), head of household, `birth_year_month` `1960-06-01`
* Income: `wages` $21,600/yr and `alimony` $3,000/yr

**Why this matters**: Missouri's Policy Manual § 2.4 counts "Alimony received", and `alimony_income` is absent from PE's CSFP source list, the same mechanism as Scenario 9. Distinct from Scenario 9 because it is a different income type; both must reach the total for both to pass.

---

### Scenario 11: Unemployment counted — Ineligible (income)

**What we're checking**: that `unemployment` reaches the CSFP countable-income total.

**Expected**: Ineligible (income) — countable income $21,600 + $3,000 = **$24,600**, above the $23,940 one-person limit

**Steps**:
* Location: ZIP `65201`, county `Boone County`
* Person 1: born June 1960 (age 66 in 2026), head of household, `birth_year_month` `1960-06-01`
* Income: `wages` $21,600/yr and `unemployment` $3,000/yr

**Why this matters**: unemployment is one of the categories PolicyEngine's own source list would have counted anyway, so this scenario distinguishes the list's completeness from the override's necessity — it fails if `unemployment` stops reaching the total, but it would still pass if the override were removed. Contrast Scenarios 9, 10 and 13, which need both.

---

### Scenario 12: Deferred compensation counted — Ineligible (income)

**What we're checking**: that `deferredComp` reaches the CSFP countable-income total.

**Expected**: Ineligible (income) — countable income $21,600 + $3,000 = **$24,600**, above the $23,940 one-person limit

**Steps**:
* Location: ZIP `65201`, county `Boone County`
* Person 1: born June 1960 (age 66 in 2026), head of household, `birth_year_month` `1960-06-01`
* Income: `wages` $21,600/yr and `deferredComp` $3,000/yr

**Why this matters**: pins the committed `deferredComp` → `taxable_ira_distributions` mapping.

---

### Scenario 13: Investment income counted — Ineligible (income)

**What we're checking**: that `investment` reaches the CSFP countable-income total.

**Expected**: Ineligible (income) — countable income $21,600 + $3,000 = **$24,600**, above the $23,940 one-person limit

**Steps**:
* Location: ZIP `65201`, county `Boone County`
* Person 1: born June 1960 (age 66 in 2026), head of household, `birth_year_month` `1960-06-01`
* Income: `wages` $21,600/yr and `investment` $3,000/yr

**Why this matters**: `investment` is an existing MFB income field, and Missouri counts every subtype it can represent — dividends, interest, withdrawals from savings or investments, and capital gains (Policy Manual § 2.4). The expected result is therefore deterministic and does not depend on knowing which subtype the amount is, so this is a modelable branch rather than a data gap. PE's CSFP source list has no capital-gains term: were PolicyEngine to derive the total, countable income would stay at $21,600 and the household would be found eligible. Like Scenarios 9 and 10, it passes only because MFB supplies the total.

---

### Scenario 14: Harrison County — Eligible, $651

**What we're checking**: county of residence never causes a denial.

**Expected**: Eligible — $651/year, identical to Scenario 1; and `MoCsfp.pe_inputs` declares no `CountyDependency`

**Steps**:
* Location: ZIP `64424`, county `Harrison County` — Scenario 1 is ZIP `65201`, `Boone County`
* Person 1: born June 1960 (age 66 in 2026), head of household, `birth_year_month` `1960-06-01`
* Income: `wages` $1,500/month ($18,000/yr)

**Why this matters**: pins the committed rule that county never denies. Assert it on **this calculator's declared inputs**, not on the request body — that `MoCsfp.pe_inputs` contains no `CountyDependency`, that it *does* declare `MoStateCodeDependency`, and that varying the screener county leaves the `mo_csfp` result unchanged.

> **Do not assert that the request carries no county field.** The PolicyEngine request body is the **union payload** — "every program's inputs in one household" (`programs/framework/pe_dependencies/payload.py:174`) — so a field this calculator never declares still reaches PolicyEngine when any sibling on the screen declares it. `MoAca.pe_inputs` includes `MoCountyDependency` (`programs/programs/cross_white_label/aca/mo.py:47`) and `mo_aca_ptc` ships active, so on a Missouri screen where MO ACA runs, `county_str` **is** in the payload. Be precise about when that is: `calc_pe_eligibility` filters on `can_calc()` **before** payload assembly (`integrations/clients/policyengine/policy_engine.py:58-62`), and `CountyDependency` declares `dependencies = ["county"]` (`pe_dependencies/household.py:49`), so on a screen with no county `MoAca` drops out and takes `county_str` with it. `MoAca` is the **only** shipped MO program declaring county, so it alone decides. `state_code` behaves differently and the two must not be reasoned about together: `StateCode` (`household.py:6`) declares **no** dependencies, so `can_calc()` can never fail on it, and fourteen MO programs supply it. The 2026-09-25 harness observed no county field only because it ran `mo_csfp` alone; that observation is an artefact of the isolated harness, not a property of production. The `state_code` half is load-bearing, but **not** for the reason it is tempting to give. PolicyEngine's CSFP formula branches on `state_code` for Texas's 130% income test and the Kansas, Massachusetts and Illinois county gates, with Missouri falling to the default — so the value matters. It does **not** follow that omitting the input would make PolicyEngine substitute its own default state: fourteen shipped Missouri programs declare `MoStateCodeDependency` (`snap`, `ssi`, `medicaid`, `chip`, `msp`, `tanf`, `wic`, `nslp`, `head_start`, `early_head_start`, `lifeline`, `aca`, `pts`, `wftc`), so on any real screen a sibling supplies `MO` whatever `mo_csfp` declares. The reason to declare it is the sibling-dependence hazard itself — undeclared, this program's answer would depend on which other Missouri programs happened to share the bucket, which is a correctness property of the screen rather than of this calculator. Asserting only that both return Eligible is decorative: it would pass even if PolicyEngine re-added a Missouri county branch. PolicyEngine carried a Missouri allowlist in source between June and August 2026, so this is a live regression shape, not a hypothetical. The residual risk, and why it is accepted, is recorded in `review-notes.md`.

---

### Scenario 15: Non-TANF cash assistance counted — Ineligible (income)

**What we're checking**: that `cashAssistanceOther` reaches the CSFP countable-income total.

**Expected**: Ineligible (income) — countable income $21,600 + $3,000 = **$24,600**, above the $23,940 one-person limit

**Steps**:
* Location: ZIP `65201`, county `Boone County`
* Person 1: born June 1960 (age 66 in 2026), head of household, `birth_year_month` `1960-06-01`
* Income: `wages` $21,600/yr and `cashAssistanceOther` $3,000/yr

**Why this matters**: `cashAssistanceOther` — General Assistance, another state's TANF, a local
fund — was split out of `cashAssistance` by MFB-1697 (#1735) on 2026-09-03. It routes to PE's
`financial_assistance`, which is in the CSFP source list, so it counts today with no new plumbing.
This scenario pins that, and distinguishes it from the TANF-only `cashAssistance` key. Both are
distinct screener types and both must reach the countable total.

---

### Scenario 16: Two seniors between the one- and two-person limits — Eligible, $1,302

**What we're checking**: the income limit scales with household size, not just that a two-person household is handled.

**Expected**: Eligible — $28,000 ≤ $32,460 (two-person limit), so $651 × 2 = **$1,302/year**, displayed as **$109/month**

**Steps**:
* Location: ZIP `65201`, county `Boone County`
* Person 1: born June 1960 (age 66 in 2026), head of household, `birth_year_month` `1960-06-01`
* Person 2: born March 1958 (age 68 in 2026), spouse, `birth_year_month` `1958-03-01`, no income
* Income: Person 1 `wages` $28,000/yr

**Why this matters**: $28,000 sits between the one-person limit ($23,940) and the two-person limit
($32,460), so this is the only scenario whose result depends on the threshold scaling. Scenarios 4
and 7 are also two-person but at $18,000 and $14,400, both under the one-person limit, so they
return Eligible whether or not the limit scales. A calculator that applied the one-person limit to
every household would pass every other scenario in this suite and fail only this one.

---

### Scenario 17: Turns 60 in the reference month — Eligible, $651

**What we're checking**: the age gate resolves to the month, not just the year.

**Expected**: Eligible — $651/year, displayed as **$54/month**

**Steps**:
* Location: ZIP `65201`, county `Boone County`
* Person 1: born September 1966, head of household, `birth_year_month` `1966-09-01`
* Income: `wages` $1,500/month ($18,000/yr)

**Why this matters**: ages are derived from `birth_year_month` at month precision — `calc_age()`
returns the year difference when the reference month is at or after the birth month, and one less
otherwise. On a reference date of 2026-09-17 this person is exactly 60; under a strict
greater-than they would be 59 and the scenario would flip to Ineligible. Scenario 5 calls itself
"exactly age 60" but is born in January, so it returns 60 either way and cannot detect the
mutation. This is the scenario that pins the committed rule that a person turning 60 in the
reference month is eligible.

---

## Research Sources

Every source cited in this spec was captured on 2026-09-25, and every quote has been verified
verbatim against its snapshot.

| Snapshot | Tier | Title | URL | Retrieved |
|---|---|---|---|---|
| `2026-09-25--7-cfr-247-9` | 1 | 7 CFR § 247.9 — CSFP eligibility requirements | https://www.ecfr.gov/current/title-7/section-247.9 | 2026-09-25 |
| `2026-09-25--7-cfr-250-2` | 1 | 7 CFR § 250.2 — definitions, incl. the CSFP household | https://www.ecfr.gov/current/title-7/section-250.2 | 2026-09-25 |
| `2026-09-25--8-usc-1615` | 1 | 8 U.S.C. § 1615 — non-qualified immigrant coverage | https://www.law.cornell.edu/uscode/text/8/1615 | 2026-09-25 |
| `2026-09-25--mo-csfp-state-plan-ffy2026` | 2 | Missouri CSFP State Plan Amendment, FFY2026 (amended Nov 2025) | https://health.mo.gov/sites/health/files/media/pdf/2026/06/missouri-state-plan-ada.pdf | 2026-09-25 |
| `2026-09-25--mo-csfp-policy-manual-02-04-participant-income-2017` | 2 | Missouri CSFP Policy and Procedure Manual § 02.04 — Participant Income (rev. 12-2005) | Internet Archive, capture of 2017-02-03 | 2026-09-25 |
| `2026-09-25--mo-csfp-policy-manual-02-05-income-exclusions-2017` | 2 | Missouri CSFP Policy and Procedure Manual § 02.05 — Income Exclusions | Internet Archive, capture of 2017-02-12 | 2026-09-25 |
| `2026-09-25--mo-csfp-participant-application-2025` | 2 | Missouri CSFP Participant Application, form MO 580-2554 | Internet Archive, capture of 2025-11-01 | 2026-09-25 |
| `2026-09-25--mo-dhss-csfp-program-page` | 2 | Missouri DHSS — Commodity Supplemental Food Program | https://health.mo.gov/food-nutrition/food-programs/commodity-supplemental-food-program | 2026-09-25 |
| `2026-09-25--fns-csfp-income-guidelines` | 2 | USDA FNS — CSFP income guidelines (2026 table) | https://www.fns.usda.gov/csfp/income-guidelines | 2026-09-25 |
| `2026-09-25--fns-csfp-caseload-2026` | 2 | USDA FNS — CSFP: Caseload Assignments for the 2026 Caseload Cycle and Administrative Grants | https://www.usda.gov/sites/default/files/guidance-documents/FNS.csfp-caseload-2026.pdf | 2026-09-25 |

**Three documents are withdrawn from their publishers and were recovered from the Internet
Archive**, which is recorded in each manifest: Policy Manual § 02.04 and § 02.05, and the
Participant Application. The two Manual sections are 2017 captures of a section revised 12-2005, so
they evidence Missouri's stated counting and exclusion rules as of that revision rather than a
current edition; the live site no longer publishes the Manual at all. They are nonetheless the
state's own documents and they carry the rules D1 and Scenarios 9, 10 and 13 depend on, which until
now rested on a reviewer-reported reading.

**Two capture routes are non-obvious, for anyone re-running this.** `ecfr.gov` web pages return a
CAPTCHA to automated fetches, so both CFR sections were taken unmodified from its versioner API.
And `usda.gov` and `fns.usda.gov` reject the capture script's user-agent with 403: the caseload
memo and the income guidelines were fetched out-of-band with browser headers and a `fns.usda.gov`
referer, which returns them at 200. The caseload memo's own landing page renders client-side and
exposes nothing to a plain fetch — the PDF link in its markup is the way in. Capturing it needs a browser.

Two notes on capture routes, for anyone re-running this: `ecfr.gov` web pages return a CAPTCHA to
automated fetches, so both CFR sections were taken unmodified from its versioner API; and
`fns.usda.gov` rejects the capture script's user-agent with 403, so the income guidelines were
fetched out-of-band and captured from file.

Two cautions. The DHSS program page publishes a $1,955/mo one-person figure and a +$8,250/yr
increment that contradict both its own annual figures and USDA's 2026 table; USDA's table controls.
And `health.mo.gov/book/export/html/4426` ("Income to Report") ranks highly for CSFP income searches
but is Summer Food Service Program guidance — **do not cite it**.

Code pointers — PolicyEngine variables and parameters, `benefits-api` dependencies, the
`benefits-calculator` formatter — are not research sources and live in `review-notes.md`, with the
load-bearing ones recorded under divergence D1.
