# Child Care Assistance Program (KS) — Program Spec

- **Program key**: `ks_ccap` (proposed — `programs/programs/cross_white_label/ccdf/ks.py`, class `KsCcap`)
- **Base federal program**: CCDF (Child Care and Development Fund)
- **White label**: KS
- **Engine**: MFB custom (recommended)
- **Added to MFB**: not implemented
- **Spec last updated**: 2026-09-09
- **Sources verified as of**: 2026-09-09

## Covered Eligibility Criteria

All five criteria must hold (1 **and** 2 **and** 3 **and** 4 **and** 5). Criteria 3, 4 and 5 are each
bypassed for households meeting their own sourced exemptions.

Kansas residence and capacity to act are stated conditions on the parent, guardian or caretaker,
but neither is enumerated below: residence is enforced structurally — the program row is scoped by
`white_label` (Program, ForeignKey), matched against `white_label` (Screen, ForeignKey), so a
non-Kansas screen never reaches this program — and the screener has no field for capacity to act,
which is an administrative determination rather than a screenable condition.

- Source: KEESM 2810 — "who resides in Kansas and is able to act on his or her own behalf may be determined eligible" — [snapshot `2026-09-02--keesm-2810-child-care-general`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2810-child-care-general/content.md), accessed 2026-09-02

The unit for criteria 4 and 5 is the KEESM 4410 **child care nuclear family**, not MFB's whole
screen. See the implementation notes on those criteria: the substitution changes both the income
limit column and the deduction band.

Kansas runs two types of child care assistance off the same unit, and the split matters for
criterion 3. **Income Eligible (Non-TANF) Child Care** (KEESM 2835) governs a nuclear family where no one
receives TANF, and it is the only type that carries the 20-hour and minimum-wage activity test.
**TANF Child Care** (KEESM 2831) governs a nuclear family where any member receives TANF and states
no hours or wage requirement at all. Criterion 3 is scoped accordingly; criteria 1, 2 and 5 apply to
both types, and criterion 4 is waived outright for a TANF household.

- Source: KEESM 2835 — "available to child care nuclear families (as defined in KEESM 4410) where no one receives TANF" — [snapshot `2026-09-02--keesm-2835-income-eligible-child-care`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2835-income-eligible-child-care/content.md), accessed 2026-09-02
- Source: KEESM 2831 — "TANF Child Care is used when any member of the nuclear family (as defined in KEESM 4410) receives TANF" — [snapshot `2026-09-02--keesm-2830-child-care-tanf-nontanf`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2830-child-care-tanf-nontanf/content.md), accessed 2026-09-02

1. **A child in the household is under 13 — from birth through the last month of the eligibility period in which the child turns 13 — or is 13 through 18 and physically or mentally incapable of self-care or under court supervision**
   - Evaluation scope: `member`
   - Captured via: `birth_year_month` (HouseholdMember, DateField) via accessor `calc_age` (HouseholdMember); the caretaking relationship via `relationship` (HouseholdMember, CharField); the incapacity branch via `disabled` (HouseholdMember, BooleanField), `long_term_disability` (HouseholdMember, BooleanField) and `visually_impaired` (HouseholdMember, BooleanField) through accessor `has_disability` (HouseholdMember)
   - Implementation note: age is `calc_age()`, which is month-granular — the under-13 boundary falls on the first of the birth month, not the birthday. When `birth_year_month` and `age` are both null, treat the member as not an eligible child rather than erroring.
   - Implementation note: the 13–18 branch uses accessor `has_disability`, which tests all three booleans including `visually_impaired`. Court supervision has no screener field, so this branch is disability-only (Data Gap 5).
   - Implementation note: the eligible children are `child`, `stepChild`, `fosterChild`, `grandChild`, `sisterOrBrother`, `stepSisterOrBrother` and `relatedOther`, per KEESM 4410's catch-all. Every other relationship counts toward family size but is not an eligible child. `il_ccap`'s set omits `relatedOther` — do not copy it. Whether an adult on the case primary-caretakes a given child is unobservable and assumed (Data Gap 16).
   - Source: KEESM 4410 — "The minor biological and/or adopted children of the adults on the case who reside in the same household, as well as other children who reside in the household and for whom an adult on the case is the primary caretaker." — [snapshot `2026-09-02--keesm-4400-assistance-unit`](../../../sources/ks/ks_ccap/2026-09-02--keesm-4400-assistance-unit/content.md), accessed 2026-09-02
   - Source: KEESM 2810 — "child from birth through the last month of the eligibility period in which the child's 13th birthday has been reached" — [snapshot `2026-09-02--keesm-2810-child-care-general`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2810-child-care-general/content.md), accessed 2026-09-02
   - Source: KEESM 2810 — "Initial eligibility for a 13 year old shall not be established unless the child meets this criteria." — [snapshot `2026-09-02--keesm-2810-child-care-general`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2810-child-care-general/content.md), accessed 2026-09-02
   - Source: KEESM 2810 — "physically or mentally incapable of caring for him or herself or if the child is under court supervision" — [snapshot `2026-09-02--keesm-2810-child-care-general`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2810-child-care-general/content.md), accessed 2026-09-02
   - Source: 45 CFR 98.20(a)(1)(i) — "Be under 13 years of age; or," — [snapshot `2026-09-02--45-cfr-98-20-lii`](../../../sources/ks/ks_ccap/2026-09-02--45-cfr-98-20-lii/content.md), accessed 2026-09-02

2. **The child who receives the care is a US citizen or a qualifying non-citizen — the citizenship or immigration status of the parent or caretaker is not relevant**
   - Evaluation scope: `config`
   - Captured via: config `legal_status_required` (Program, M2M to `LegalStatus`) — results-display metadata. The screener collects no per-member immigration status, and the backend never applies this field as an eligibility gate: it is read into a list and emitted in the response payload (`screener/views.py`) for the frontend to filter on.
   - Implementation note: `legal_status_required` is a program-level visibility filter, not an eligibility gate, and cannot express "the child only". The row carries all six user-selected statuses — `["citizen", "non_citizen", "refugee", "gc_5plus", "gc_5less", "otherWithWorkPermission"]` — so the program stays visible to an undocumented parent whose citizen or qualified child is eligible. A config approximation, never a data gap.
   - Source: KEESM 2140 — "NOTE: For cases in which assistance is provided on behalf of a child, such as child care, only the citizenship or non-citizen status of the child who is the primary beneficiary is relevant" — [snapshot `2026-09-02--keesm-2140-citizenship-alien-status`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2140-citizenship-alien-status/content.md), accessed 2026-09-02
   - Source: Kansas DCF, Child Care Assistance Program — "To qualify for Child Care Assistance, the child must be a U.S. citizen or a qualifying non-citizen." — [snapshot `2026-09-03--dcf-child-care-assistance-program`](../../../sources/ks/ks_ccap/2026-09-03--dcf-child-care-assistance-program/content.md), accessed 2026-09-03

3. **The family has a personal need for child care — one of the eight approved need reasons — and none of the three no-personal-need determinations applies**
   - Evaluation scope: `household`
   - Captured via: see the Maintain Employment sub-rules below; every other pathway is a data gap or a proxy, enumerated in the need-reason note below
   - Implementation note: per KEESM 4410 the test reaches only the head of household and their `spouse` or `domesticPartner`. Any other adult — `grandParent`, `parent`, `sisterOrBrother`, `relatedOther`, `roommate`, `boyfriendOrGirlfriend` — counts toward family size but is never tested. Iterating every adult on the screen denies households Kansas approves.
   - Implementation note: of KEESM 2820's eight need reasons only **Maintain Employment** is modelable. Work Program Participation is redundant with TANF receipt (its post-closure window is Data Gap 13); the remaining six are Data Gaps 4, 7, 9, 10, 11 and 12.
   - Implementation note: a non-TANF family meets this criterion **only** through Maintain Employment. The other seven reasons are not establishable from any screener field and are **not** assumed met, so a household whose only reason is one of them is screened out here. That exclusionary surface is deliberate — falling open wherever an unobservable pathway might apply would remove this criterion's screening power — and is disclosed in the Data Gaps preamble.
   - **Maintain Employment — the modelable pathway.** For **Income Eligible (Non-TANF)** child care, every adult included on the case must be employed an average of at least 20 hours per week, **and** every adult must be earning at least the federal minimum wage per hour. The two halves carry different exceptions: the 20-hour requirement is excused for an adult not capable of meeting it due to a documented physical or mental condition; **the wage floor carries no such incapacity exception in any captured source.** Both halves are scoped to this type of child care — see the TANF note below.
     - Captured via: whether the adult is employed at all, from the presence of a `wages` or `selfEmployment` row in `income_streams` (IncomeStream, `type` CharField); `hours_worked` (IncomeStream, IntegerField) summed per **tested** adult (head plus `spouse`/`domesticPartner`, per the unit note above) across that adult's `hourly`-frequency wage streams; `amount` (IncomeStream, DecimalField) as the hourly wage on those same streams; the incapacity exception via `disabled` / `long_term_disability` / `visually_impaired` (HouseholdMember, BooleanField)
     - Constant: `FEDERAL_MINIMUM_WAGE = 7.25` (class attribute)
   - Implementation note: `hours_worked` is populated only on `hourly`-frequency streams, so both halves of the test are evaluable only from those, where `amount` is the hourly wage. An adult paid at any other frequency is not screened out (Data Gap 6), and a null `hours_worked` falls open the same way.
   - Implementation note: a tested adult holding **no** `wages` and no `selfEmployment` stream at any frequency **fails** this criterion — they are observably not employed rather than unevaluable — unless the incapacity exemption reaches them or the household receives TANF. Data Gap 6 covers only non-hourly *earners*, not non-earners.
   - Implementation note: the wage floor is the tested adult's average across their hourly streams, `Σ(amount × hours_worked) ÷ Σ(hours_worked)`, not a test of each stream on its own. With a single stream this is exactly `amount`.
   - Implementation note: do **not** reuse `TotalHoursWorkedDependency`. Its imputation for non-hourly streams fixes the implied hourly wage at exactly the federal minimum, making a wage-floor test circular, and it floors reported hours at 40 for every member aged 16 or over — which would make the 20-hour test unfailable.
   - Implementation note: self-employment is measured on **net** income and tipped work on wages plus tips, and the screener collects neither (Data Gap 6). All five sourced exemptions from the 20-hour requirement are unscreenable (Data Gaps 8 and 13), and the federal Work Study route is not an exemption but an alternative way to establish the reason itself (Data Gap 7).
   - Implementation note: when `has_base_benefit("tanf")` (Screen) is true this criterion is met through TANF Child Care and **neither** the hours test nor the wage floor is applied. Treating TANF receipt as establishing the criterion is over-inclusive by design: KEESM 2831 still requires one of its listed need reasons and MFB cannot see which.
   - Source: KEESM 2810 — "The client must have a personal and, for certain categories of child care, a financial need" — [snapshot `2026-09-02--keesm-2810-child-care-general`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2810-child-care-general/content.md), accessed 2026-09-02
   - Source: KEESM 2820 — "Personal needs of the client may include:" — [snapshot `2026-09-02--keesm-2810-child-care-general`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2810-child-care-general/content.md), accessed 2026-09-02
   - Source: KEESM 2820 — "To be eligible at initial application and review, the client must have a personal need for child care" — [snapshot `2026-09-02--keesm-2810-child-care-general`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2810-child-care-general/content.md), accessed 2026-09-02
   - Source: KEESM 2835 — "A primary purpose of the child care program is to support employment for adults employed an average of at least 20 hours per week and earning at least the federal minimum wage per hour." — [snapshot `2026-09-02--keesm-2835-income-eligible-child-care`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2835-income-eligible-child-care/content.md), accessed 2026-09-02
   - Source: KEESM 2820 — "For Income Eligible (Non-TANF) child care, if employment is the reason for child care, the adult(s) must be employed at least 20 hours per week and earning at least the federal minimum wage per hour." — [snapshot `2026-09-02--keesm-2810-child-care-general`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2810-child-care-general/content.md), accessed 2026-09-02
   - Source: KEESM 2820 — "For TANF related child care, there is no minimum number of hours of employment required to qualify for child care." — [snapshot `2026-09-02--keesm-2810-child-care-general`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2810-child-care-general/content.md), accessed 2026-09-02
   - Source: KEESM 2831 — "Maintain Employment - TANF recipients who need child care for employment." — [snapshot `2026-09-02--keesm-2830-child-care-tanf-nontanf`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2830-child-care-tanf-nontanf/content.md), accessed 2026-09-02
   - Source: KEESM 2835 — "All adults must be earning at least the federal minimum wage per hour for either regular employment or self-employment, and for tipped professions, the adult’s combined wages plus tips must equal at least the federal minimum wage per hour" — [snapshot `2026-09-02--keesm-2835-income-eligible-child-care`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2835-income-eligible-child-care/content.md), accessed 2026-09-02
   - Source: KEESM 2835 — "All adults included on a child care case must meet the 20 hour per week work requirement unless they are not capable of meeting it due to a documented physical or mental condition." — [snapshot `2026-09-02--keesm-2835-income-eligible-child-care`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2835-income-eligible-child-care/content.md), accessed 2026-09-02
   - Source: KEESM 2835 — "Individuals who are self-employed must be working an average of at least 20 hours per week with net income equivalent to the federal minimum wage per hour." — [snapshot `2026-09-02--keesm-2835-income-eligible-child-care`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2835-income-eligible-child-care/content.md), accessed 2026-09-02
   - Source: KEESM 2835 — "for tipped professions, the adult’s combined wages plus tips must equal at least the federal minimum wage per hour" — [snapshot `2026-09-02--keesm-2835-income-eligible-child-care`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2835-income-eligible-child-care/content.md), accessed 2026-09-02
   - Source: KEESM 2835 — "An employed teen parent who is working on completion of a high school diploma or GED is not required to meet the 20 hours per week employment requirement" — [snapshot `2026-09-02--keesm-2835-income-eligible-child-care`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2835-income-eligible-child-care/content.md), accessed 2026-09-02
   - Source: KEESM 2835 — "hours of actual participation in the federal Work Study Program if the student is participating at least 15 hours per week (average)" — [snapshot `2026-09-02--keesm-2835-income-eligible-child-care`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2835-income-eligible-child-care/content.md), accessed 2026-09-02
   - Source: KEESM 2835 — "Former TANF recipients who need child care for employment when their TANF case has closed and earned income is a factor in the closure shall receive child care under Income Eligible Child Care and the Maintain Employment reason code without meeting the minimum work requirement and without a family share deduction for the remaining child care eligibility period." — [snapshot `2026-09-02--keesm-2835-income-eligible-child-care`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2835-income-eligible-child-care/content.md), accessed 2026-09-02
   - Source: KEESM 4410 — "An adult who resides with a child or children for whom that adult is the primary caretaker." — [snapshot `2026-09-02--keesm-4400-assistance-unit`](../../../sources/ks/ks_ccap/2026-09-02--keesm-4400-assistance-unit/content.md), accessed 2026-09-02
   - Source: KEESM 4410 — "Adults who are not married to each other but reside together as boyfriend/girlfriend, regardless of whether or not they have common children, if one of the adults is the primary caretaker of the child for whom assistance is requested." — [snapshot `2026-09-02--keesm-4400-assistance-unit`](../../../sources/ks/ks_ccap/2026-09-02--keesm-4400-assistance-unit/content.md), accessed 2026-09-02
   - Source: KEESM 2820 — "they are not required to do so" — [snapshot `2026-09-02--keesm-2810-child-care-general`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2810-child-care-general/content.md), accessed 2026-09-02
   - Source: KEESM 2835 — "The Primary Applicant is not required to meet the 20 hour per week work requirement in these situations." — [snapshot `2026-09-02--keesm-2835-income-eligible-child-care`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2835-income-eligible-child-care/content.md), accessed 2026-09-02
   - Source: KEESM 2810 — "the personal need criteria would not be met in situations where the mother of the children is employed, but the father of the children is not employed. The father would be expected to provide care." — [snapshot `2026-09-02--keesm-2810-child-care-general`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2810-child-care-general/content.md), accessed 2026-09-02
   - Source: KEESM 2810 — "child care can be approved at initial application or review based on the mother's employment if both the mother and step-father are employed at least 20 hours per week" — [snapshot `2026-09-02--keesm-2810-child-care-general`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2810-child-care-general/content.md), accessed 2026-09-02
   - Source: US DOL Wage and Hour Division — "The federal minimum wage is $7.25 per hour effective July 24, 2009." — [snapshot `2026-09-02--dol-federal-minimum-wage`](../../../sources/ks/ks_ccap/2026-09-02--dol-federal-minimum-wage/content.md), accessed 2026-09-02

4. **The family's non-exempt monthly gross income is within the income limit for its family size — income above 85% of State Median Income is not eligible**
   - Evaluation scope: `household`
   - Captured via: per-member iteration over `income_streams` at monthly frequency — the `calc_gross_income` accessor (Screen) cannot express this rule on its own, because its `exclude` argument filters income *types*, not members, and both exemptions below turn on the **earner** rather than the stream: age for the child-earnings exemption, SSI receipt for the other; family size from `household_size` (Screen, IntegerField, **nullable**) — see the family-size note below
   - Constant: the Appendix F-1 income-limit column, keyed on family size — `2 → $5,439`, `3 → $6,719`, `4 → $7,998`, `5 → $9,278`, `6 → $10,558`, `7 → $10,798`, `8 → $11,038`. Each figure is the upper bound of that family size's top (85% SMI) Family Share Deduction band in the Benefit Value grid, so these are not two tables but one table read two ways — keep them in step.
   - Implementation note: the unit is the KEESM 4410 nuclear family and `household_size` is a proxy for it — a non-caretaker grandparent, an adult sibling or a roommate sits outside the nuclear family but inside the count. The error direction is not uniform: such a member raises the income limit and adds income at the same time.
   - Implementation note: family size is `household_size`, and it is the same number for the income limit and for the Family Share Deduction — never compute the two separately. It is user-entered and independent of the member list; neither `num_children` nor a count of `household_members` stands in for it. When it is null the program is **dropped from results** — `household_size` is a declared dependency, so `can_calc` fails and the eligibility loop omits the program rather than substituting a different number. A member count is not a recovery of the missing input, and guessing it wrong silently picks a different Appendix F-1 row, moving both the ceiling and the deduction.
   - Implementation note: the implemented rows are sizes 2 through 8, and the ceiling is a deliberate cap rather than the end of the source. **Appendix F-1 publishes sizes 2 through 11**; the screener form validates `.lte(8)`, so sizes 9–11 are reachable only on the API path and are clamped to 8 instead of carried. Below 2 is unreachable because criterion 1 requires an eligible child, whose relationship is never `headOfHousehold`. If the form cap is ever raised, add the 9, 10 and 11 rows from the F-1 snapshot before it ships.
   - Implementation note: the FPL bands inside F-1 set the Family Share Deduction only — they are **not** a second eligibility ceiling. DCF's 2021 memo set child-care income eligibility at 250% FPL, but SMI growth has overtaken it and every 2026 F-1 limit now sits above 250%. The single operative ceiling is 85% SMI, which is also the federal CCDF ceiling; do not add a 250% FPL gate.
   - Implementation note: `calc_gross_income` is not KEESM "nonexempt gross income". Exclude every income stream whose member is under 18, or under 19 with `student` true (KEESM 6410). `student` is nullable and a null reads as **`True`**, the inclusive direction. The sourced exception — a child legally responsible for another member — is unobservable (Data Gap 14).
   - Implementation note: exclude **every** stream belonging to a member who holds an `sSI` stream — that member's wages as well as the SSI itself (KEESM 6410, KEESM 4420). `has_base_benefit("ssi")` must **not** be used: it is household-level and cannot say whose income to exempt. Omitting this is exclusionary — an SSI recipient's wages inflate countable income and raise the deduction band.
   - Implementation note: quantise countable monthly income to the cent (`ROUND_HALF_UP`) before any Appendix F-1 comparison, and read the quantised figure for both the band lookup and the limit test. Without it every hourly-derived amount lands a fraction of a cent low and no household can sit exactly on a published bound.
   - Implementation note: the income test is waived entirely for three sourced cases — a household with a TANF recipient (`has_base_benefit("tanf")`), an unemployed food assistance work program participant (Data Gap 9), and children needing care to prevent abuse or neglect (Data Gap 10).
   - Source: Appendix F-1 — "Families with income above 85% of the State Median Income (SMI) are not eligible for the Child Care Assistance subsidy program." — [snapshot `2026-09-02--appendix-f-1-income-and-family-share-schedule`](../../../sources/ks/ks_ccap/2026-09-02--appendix-f-1-income-and-family-share-schedule/content.md), accessed 2026-09-02
   - Source: KEESM 7540 — "A family is income eligible when the nonexempt gross income of the family members is within the income limits established annually by the agency." — [snapshot `2026-09-02--keesm-7540-child-care-income-eligibility`](../../../sources/ks/ks_ccap/2026-09-02--keesm-7540-child-care-income-eligibility/content.md), accessed 2026-09-02
   - Source: KEESM 7540 — "unless someone in the household is a TANF recipient, he or she is an unemployed food assistance work program participant, or the children need child care to prevent abuse and/or neglect" — [snapshot `2026-09-02--keesm-7540-child-care-income-eligibility`](../../../sources/ks/ks_ccap/2026-09-02--keesm-7540-child-care-income-eligibility/content.md), accessed 2026-09-02
   - Source: KEESM 6410 — "For Child Care, the earnings of any child under age 18 (or age 19 if the child is working toward the attainment of a high school diploma or its equivalent) are exempt unless the child is legally responsible for another person in the nuclear family." — [snapshot `2026-09-02--keesm-6410-exempt-income`](../../../sources/ks/ks_ccap/2026-09-02--keesm-6410-exempt-income/content.md), accessed 2026-09-02
   - Source: KEESM 6410 — "SSI (All Programs Except Food Assistance) - Income of an SSI recipient (including 1619(b) recipients) and retroactive SSI benefits (even if the individual receiving the benefit is no longer an SSI recipient) are exempt as income in the month received and as a resource in the following months." — [snapshot `2026-09-02--keesm-6410-exempt-income`](../../../sources/ks/ks_ccap/2026-09-02--keesm-6410-exempt-income/content.md), accessed 2026-09-02
   - Source: KEESM 4420 — "SSI is exempt income." — [snapshot `2026-09-02--keesm-4400-assistance-unit`](../../../sources/ks/ks_ccap/2026-09-02--keesm-4400-assistance-unit/content.md), accessed 2026-09-02
   - Source: KEESM 4410 — "An 18-year-old child in the home who is still in high school will continue to be included in the assistance plan through the month in which he or she turns age 19." — [snapshot `2026-09-02--keesm-4400-assistance-unit`](../../../sources/ks/ks_ccap/2026-09-02--keesm-4400-assistance-unit/content.md), accessed 2026-09-02
   - Source: KEESM 4410 — "An unborn is not considered a child and is not part of the nuclear family or included in the household for family share deduction purposes." — [snapshot `2026-09-02--keesm-4400-assistance-unit`](../../../sources/ks/ks_ccap/2026-09-02--keesm-4400-assistance-unit/content.md), accessed 2026-09-02
   - Source: DCF Implementation Memo 2021-07-01 — "income eligibility for the child care assistance program is being expanded to include families with incomes up to 250% of the Federal Poverty Level" — [snapshot `2026-09-02--dcf-memo-2021-07-01-250-percent-fpl`](../../../sources/ks/ks_ccap/2026-09-02--dcf-memo-2021-07-01-250-percent-fpl/content.md), accessed 2026-09-02
   - Source: DCF Implementation Memo 2021-07-01 — "the maximum allowable income for households size seven and larger is less than 250% of the FPL" — [snapshot `2026-09-02--dcf-memo-2021-07-01-250-percent-fpl`](../../../sources/ks/ks_ccap/2026-09-02--dcf-memo-2021-07-01-250-percent-fpl/content.md), accessed 2026-09-02
   - Source: 45 CFR 98.20(a)(2)(i) — "Reside with a family whose income does not exceed 85 percent of the State's median income (SMI), which must be based on the most recent SMI data that is published by the Bureau of the Census, for a family of the same size; and" — [snapshot `2026-09-02--45-cfr-98-20-lii`](../../../sources/ks/ks_ccap/2026-09-02--45-cfr-98-20-lii/content.md), accessed 2026-09-02

5. **The non-exempt resources of all members of the child care family group do not exceed $10,000**
   - Evaluation scope: `household`
   - Captured via: `household_assets` (Screen, DecimalField); the TANF exemption via accessor `has_base_benefit` (Screen); the SSI exemption via `type` (IncomeStream, CharField) equal to `sSI` on every member of criterion 1's eligible-child set
   - Constant: `RESOURCE_LIMIT = 10_000` (class attribute)
   - Implementation note: the limit is inclusive at exactly $10,000. `household_assets` is nullable; when it is null do **not** screen the household out. The unit is the KEESM 4410 nuclear family, with the same proxy caveat as criterion 4.
   - Implementation note: six sourced categories are exempt from the limit entirely, and two of them are screenable.
     - A household where a member receives TANF (`has_base_benefit("tanf")`).
     - The case where criterion 1's eligible-child set is non-empty and **every** member of it holds an `sSI` stream — tested **per member**, never through `has_base_benefit("ssi")`, which is set from *any* member's SSI and would waive the limit off an SSI *parent*. The eligible-child set stands in for KEESM 5140's "children receiving child care assistance" (Data Gap 17).
     - The other four are Data Gaps 13, 9, 10 and 12, so a household that might fall in one is not screened out on resources.
   - Implementation note: KEESM 4420's matching SSI income rule changes nothing MFB can observe — where only an SSI child needs care, only that child's own non-exempt income counts, and criterion 4's KEESM 6410 rule already exempts it. Recorded rather than implemented.
   - Implementation note: the federal CCDF asset ceiling is $1,000,000 and is **not** the Kansas limit. `il_ccap` uses the federal figure — a calculator inheriting it would apply a limit 100 times too high.
   - Source: KEESM 5140 — "The maximum allowable non-exempt resources of all members of the family group shall not exceed ten thousand dollars ($10,000). This limit applies to all persons who are included in the child care case." — [snapshot `2026-09-02--keesm-5000-resources`](../../../sources/ks/ks_ccap/2026-09-02--keesm-5000-resources/content.md), accessed 2026-09-02
   - Source: KEESM 5140 — "the only children receiving child care assistance are also receiving SSI, families in which at least one member receives TANF, families in the first two months following the loss of TANF eligibility, families receiving Food Assistance when an adult in the household who is unemployed is participating in the Food Assistance E&T program, families receiving child care for a qualified social service reason, and for families participating in the Kansas Early Head Start/Child Care Partnership program" — [snapshot `2026-09-02--keesm-5000-resources`](../../../sources/ks/ks_ccap/2026-09-02--keesm-5000-resources/content.md), accessed 2026-09-02
   - Source: KEESM 4420 — "only the child's non-exempt income will be considered" — [snapshot `2026-09-02--keesm-4400-assistance-unit`](../../../sources/ks/ks_ccap/2026-09-02--keesm-4400-assistance-unit/content.md), accessed 2026-09-02
   - Source: Kansas DCF, Child Care Assistance Program — "Families must not have more than ten thousand dollars ($10,000) of countable resources." — [snapshot `2026-09-03--dcf-child-care-assistance-program`](../../../sources/ks/ks_ccap/2026-09-03--dcf-child-care-assistance-program/content.md), accessed 2026-09-03
   - Source: 45 CFR 98.20(a)(2)(ii) — "Whose family assets do not exceed $1,000,000 (as certified by such family member)" — [snapshot `2026-09-02--45-cfr-98-20-lii`](../../../sources/ks/ks_ccap/2026-09-02--45-cfr-98-20-lii/content.md), accessed 2026-09-02

## Missing Eligibility Criteria (Data Gaps)

Most gaps are handled inclusively — the household is not screened out on them — but **criterion 3
is the exception, and it is a large one.** Seven of the eight KEESM 2820 need reasons cannot be
established from any screener field, and criterion 3 does not assume them met, so a non-TANF
household whose only need reason is one of the seven is screened out. Every gap carrying such a
limb is labelled `cannot-apply — exclusionary` on that limb: **Gaps 4, 7, 8, 9, 10, 11 and 12.**
Where the same gap also carries a resource, income or family-share consequence, that limb really is
inclusive and is labelled `assumed-met` separately — the two are split inside each entry rather
than averaged into one label.

Why the exclusionary reading is deliberate: MFB can never rule an unobservable pathway *out*, so
falling open wherever one might apply would delete criterion 3's screening power and stop Scenarios
8, 8d and 9 from failing. The surface is disclosed here and nowhere the affected household can see:
an ineligible program is filtered off the results page, so the program description does not reach a
household this criterion drops. See criterion 3's note on that asymmetry.

One gap is exclusionary outside criterion 3: **Gap 15**, the minor-teen-parent assistance unit,
which counts income and resources criteria 4 and 5 would otherwise exclude.

And two gaps run the other way hard enough to be worth naming here. **Gap 16**, primary
caretaking: its inclusive handling can *establish* a verdict rather than only raise a figure —
a child admitted to criterion 1 through KEESM 4410's catch-all is assumed to be caretaken by an
adult on the case, and where that child is the household's only one, the assumption is what
carries criterion 1. **Gap 17**, which children care is actually requested for: it is the
assumption behind the value's sum over every eligible child, and through criterion 5's SSI
exemption it can move a verdict in either direction.

Gaps 1 and 2 are value-estimation gaps rather than eligibility gaps; they gate the figure the spec
commits to, not the verdict. No committed scenario's *denial* turns on a gap: every scenario that
denies on criterion 3 does so on the Maintain Employment test, and every scenario that denies on
criteria 4 or 5 does so on an observable income or asset figure.

1. **The type of provider the family uses — licensed child care centre, licensed home, out-of-home relative, or in-home relative**
   - Why: the screener collects no provider type, and the DCF benefit rate is set by it. Kansas pays four different hourly rates and the licensed centre is the **highest**: for a preschooler in Johnson County, `$5.51` centre against `$4.23` licensed home, `$2.81` out-of-home relative and `$2.42` in-home relative.
   - Handling: **pinned, and deliberately left pinned** — the estimate uses the licensed-centre rate and is disclosed in Benefit Value as an MFB estimate. Never screens a household out.
   - This gap **cannot be closed by further research on published sources.** C-18's 75th-percentile note explains how DCF sets each rate; it says nothing about which type CCAP families use. That is administrative data DCF holds and no snapshot carries. Closing it needs DCF's provider mix, not another document.
   - Error direction, quantified against Scenario 1's household: a licensed home returns roughly 1.3x less than shown, an out-of-home relative roughly 2.0x less, an in-home relative roughly 2.3x less. The estimate is therefore an **upper** bound on the rate axis, and the reviewer should read every committed value as "a centre-rate household".
   - Source: Appendix C-18 — "MAXIMUM HOURLY CHILD CARE BENEFIT RATES**" — [snapshot `2026-09-02--appendix-c-18-provider-rate-chart`](../../../sources/ks/ks_ccap/2026-09-02--appendix-c-18-provider-rate-chart/content.md), accessed 2026-09-02

2. **Travel time and the child's school schedule — the two inputs to KEESM 7620's hours-needed estimate that remain unobservable after the block is derived**
   - Why: **the primary input is no longer missing.** 7620 sets hours needed from the adults' weekly work schedule plus travel time plus the child's school schedule. The work schedule *is* recorded, on `hours_worked`, so the block is derived from it (see Benefit Value). What is still missing is the other two terms: no field records commute time, and none records whether a child is in school or for how many hours.
   - Handling: `assumed-absent` — both are omitted from the derivation, which reads the work schedule alone. Never screens a household out.
   - The two pull in **opposite** directions, so the residual error is two-sided rather than systematic. Travel time is counted by 7620 and would raise hours needed, pushing a household nearer the 215 block; a school-age child's school hours would lower them, pushing the other way. 7620's own example of a child needing the full block is "a four year old who is **not** in pre-school, Head Start or pre-kindergarten", which is exactly the case where the school term is zero.
   - A third limb is structural rather than missing: `hours_worked` exists only on hourly streams, so a household with any non-hourly earner among the adults on the case falls back to the 129-hour block. That is the same population Data Gap 6 covers for the activity test.
   - Source: KEESM 7620 — "EES staff shall establish a reasonable estimate of the hours needed for child care by determining with the parent(s) their average weekly work schedule." — [snapshot `2026-09-02--keesm-7610-child-care-plan-duration`](../../../sources/ks/ks_ccap/2026-09-02--keesm-7610-child-care-plan-duration/content.md), accessed 2026-09-02

3. **The three determinations under which personal need is not met — the caretaker's work or school hours falling inside the child's regular school hours, a TANF assistance unit member whose needs are met for caring for the child, or another legally responsible person at home available to provide care**
   - Why: the screener collects no work or school schedule, no TANF caretaker-payee detail, and no availability status for other adults.
   - Handling: `assumed-met` — none of the three exclusions is applied, so the spec is **over-inclusive** here. That is the safe direction for a screener, but it means some households shown as eligible would be denied by DCF for lack of personal need. KEESM 2820's respite-care NOTE excludes a fourth case on the same footing; it needs no separate handling, because a household requesting care with no adult working 20 hours already fails criterion 3.
   - Source: KEESM 2820 — "regular school hours (which includes homeschool, private school, virtual school, or any lessons counting as credit towards graduation)" — [snapshot `2026-09-02--keesm-2810-child-care-general`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2810-child-care-general/content.md), accessed 2026-09-02
   - Source: KEESM 2820 — "there are individuals in the TANF assistance unit whose needs are met on the basis of their responsibility for caring for the child; or there is another legally responsible person in the home who is available to provide care." — [snapshot `2026-09-02--keesm-2810-child-care-general`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2810-child-care-general/content.md), accessed 2026-09-02

4. **The Teen-Parent Education and Training need reason, and the academic conditions on it and on Post-Secondary Education — a 2.0 cumulative GPA, and passing grades or adequate progress for a teen parent in high school**
   - Why: this reason turns on the member being a **parent**, and `relationship` is recorded relative to the head of household, so a teen parent's own child reads as `grandChild` and the parent-child link between two members is unobservable (the same limitation as Data Gap 14). The `student` booleans establish enrolment and work-study status only, and the screener collects no grades or academic standing.
   - Handling: **two limbs.** The need reason itself is `cannot-apply — exclusionary` — an enrolled teen parent working under 20 hours a week is screened out on criterion 3, which Kansas would not do. The academic conditions are `assumed-met`: neither pathway is screened out on academic progress. Only the first limb is named in the program description, by its "Child care can also be approved if you are in school or job training or facing a crisis" sentence; the GPA condition is a narrow education-pathway detail and belongs here rather than in user-facing copy.
   - Source: KEESM 2835 — "The client must maintain   a 2.0 cumulative GPA on a 4.0 scale or its equivalent in another grading system." — [snapshot `2026-09-02--keesm-2835-income-eligible-child-care`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2835-income-eligible-child-care/content.md), accessed 2026-09-02
   - Source: KEESM 2835 — "Teen parents enrolled in high school are required to make passing grades or adequate progress as established by the educational institution." — [snapshot `2026-09-02--keesm-2835-income-eligible-child-care`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2835-income-eligible-child-care/content.md), accessed 2026-09-02

5. **Court supervision, the non-disability route by which a child aged 13 to 18 remains eligible**
   - Why: the screener collects no court-supervision status.
   - Handling: `assumed-met` within its own branch — the 13–18 extension is applied on the disability booleans alone, which is narrower than the sourced rule. A 13–18 child under court supervision without a disability is not surfaced.
   - Source: KEESM 2810 — "physically or mentally incapable of caring for him or herself or if the child is under court supervision" — [snapshot `2026-09-02--keesm-2810-child-care-general`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2810-child-care-general/content.md), accessed 2026-09-02

6. **Weekly hours and hourly earnings for an adult who *is* employed but whose income is not recorded at hourly frequency, net income for the self-employed, and combined wages plus tips for tipped work**
   - Why: `hours_worked` (IncomeStream) is populated only for `hourly`-frequency streams, so neither the 20-hour average nor the wage floor can be derived for salaried, weekly, biweekly, semimonthly or yearly earners. Self-employment is measured on **net** income and tipped work on wages plus tips; the screener records neither.
   - Handling: `assumed-met` — such adults are not screened out on either the hours test or the wage floor. The circular `monthly() / 7.25 / 4` imputation in `TotalHoursWorkedDependency` is deliberately not used. This gap reaches only adults who **hold** an earned-income stream; an adult with no `wages` or `selfEmployment` stream at all is observably not employed and fails criterion 3, per that criterion's committed handling.
   - Source: KEESM 2835 — "All adults must be earning at least the federal minimum wage per hour for either regular employment or self-employment, and for tipped professions, the adult’s combined wages plus tips must equal at least the federal minimum wage per hour" — [snapshot `2026-09-02--keesm-2835-income-eligible-child-care`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2835-income-eligible-child-care/content.md), accessed 2026-09-02

7. **The Post-Secondary Education pathway — the reason itself, the federal Work Study route into Maintain Employment, and the pathway's limits: a lifetime 24 months per adult, no second associate's or bachelor's degree, no degree above a bachelor's, a 15-hour paid-employment floor, and no child care where both adults in a two-adult household are in school at once**
   - Why: an approved education plan is the load-bearing fact for all three, and the screener records nothing about one. It also collects no education history, prior-degree or months-used data. The `student` booleans give enrolment but not an approved plan.
   - Why (the Work Study route specifically): KEESM 2835 allows Maintain Employment to be met through work-study hours **only** for a student whose education plan has been approved, at 15 hours a week or more, and only where care is not needed for school hours. `student_has_work_study` (HouseholdMember, BooleanField) is a boolean and carries no hours, so the 15-hour average is not derivable, and neither of the other two conditions has a field.
   - Why (continued): this route is **not** an exemption from the 20-hour requirement — it is an alternative way to establish the reason — and it is recorded here rather than beside criterion 3's exemptions.
   - Handling: **two limbs.** The reason itself, including the Work Study route into it, is `cannot-apply — exclusionary` — a post-secondary student working under 20 hours a week is screened out on criterion 3. The pathway's limits are `assumed-met`: nothing is screened out on months used, prior degrees or the both-adults-in-school prohibition.
   - Source: KEESM 2835 — "For post-secondary education students whose education plan has been approved, child care may also be provided with this reason for hours of actual participation in the federal Work Study Program if the student is participating at least 15 hours per week (average) in the Work Study Program or a combination of the Work Study Program and private employment and does not need child care for their school hours." — [snapshot `2026-09-02--keesm-2835-income-eligible-child-care`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2835-income-eligible-child-care/content.md), accessed 2026-09-02
   - Source: KEESM 2835 — "Child care for post-secondary education will be allowed for a lifetime maximum of 24 months per adult." — [snapshot `2026-09-02--keesm-2835-income-eligible-child-care`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2835-income-eligible-child-care/content.md), accessed 2026-09-02
   - Source: KEESM 2835 — "DCF will not provide child care for the pursuit of a second associate’s degree or a second bachelor’s degree. Child care will not be allowed for the pursuit of a degree higher than a bachelor’s." — [snapshot `2026-09-02--keesm-2835-income-eligible-child-care`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2835-income-eligible-child-care/content.md), accessed 2026-09-02
   - Source: KEESM 2835 — "The client must be engaged in paid employment for a minimum of 15 hours per week." — [snapshot `2026-09-02--keesm-2835-income-eligible-child-care`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2835-income-eligible-child-care/content.md), accessed 2026-09-02
   - Source: KEESM 2835 — "In a two-parent/adult household, child care would not be allowed if both parents/adults are attending a formal education or training program at the same time." — [snapshot `2026-09-02--keesm-2835-income-eligible-child-care`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2835-income-eligible-child-care/content.md), accessed 2026-09-02

8. **The four exemptions from the 20-hour requirement — Job Corps participation; an employed teen parent completing a high school diploma or GED; the Primary Applicant on a minor teen parent's case; and the case where the only children receiving benefits are the children of a minor parent completing high school or a GED**
   - Why: the screener collects no Job Corps participation and cannot identify whose children are receiving the benefit. The two teen-parent limbs turn on identifying a parent among the members, which head-relative `relationship` cannot express (Data Gap 14), and on whether a minor is "able to act in their own behalf", which has no field at all. The `student` booleans establish enrolment, never parenthood.
   - Handling: `cannot-apply — exclusionary` — none of the four exemptions can be applied, so an affected household whose tested adults fail the hours test is screened out on criterion 3. Applying them from enrolment alone would exempt every employed student from the hours test, which is broader than the sourced rule and would leave Scenario 8 unkillable for any household containing a student.
   - Source: KEESM 2835 — "An employed teen parent who is working on completion of a high school diploma or GED is not required to meet the 20 hours per week employment requirement" — [snapshot `2026-09-02--keesm-2835-income-eligible-child-care`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2835-income-eligible-child-care/content.md), accessed 2026-09-02
   - Source: KEESM 2835 — "Job Corps participants are not required to meet the 20-hour work requirement." — [snapshot `2026-09-02--keesm-2835-income-eligible-child-care`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2835-income-eligible-child-care/content.md), accessed 2026-09-02
   - Source: KEESM 2835 — "the adult parents included on the cases are not required to meet the 20-hour-per-week work requirement" — [snapshot `2026-09-02--keesm-2835-income-eligible-child-care`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2835-income-eligible-child-care/content.md), accessed 2026-09-02

9. **Food Assistance Employment and Training participation — a need reason, a resource-test exemption, an income-test waiver, and a family-share waiver**
   - Why: the screener records SNAP receipt and `unemployed`, but not E&T participation.
   - Handling: **two limbs.** The need reason is `cannot-apply — exclusionary` — an E&T participant not employed 20 hours a week is screened out on criterion 3, which Kansas would not do. The resource test is `assumed-met` (not screened out on resources), and the income and family-share waivers cannot be applied, which understates the benefit for an affected household that clears criterion 3 another way.
   - Source: KEESM 2835 — "No family share will be assigned to food assistance work program participants." — [snapshot `2026-09-02--keesm-2835-income-eligible-child-care`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2835-income-eligible-child-care/content.md), accessed 2026-09-02

10. **The Social Services (temporary emergency need) pathway, which waives both the income and resource tests and assesses no family share deduction**
    - Why: the screener collects no crisis, protective-services or emergency-need status.
    - Handling: **two limbs.** The need reason is `cannot-apply — exclusionary` — a family in crisis with no adult working 20 hours a week is screened out on criterion 3, and this is the gap most likely to cost a household a result it deserves. The income and resource waivers and the family-share waiver are `assumed-met` in the sense that no extra gate is added, but they cannot be applied, so an affected family that clears criterion 3 another way has its benefit understated.
    - Source: KEESM 2835 — "Financial eligibility tests including income and resources are waived for families using this need reason except as noted below and there will be no family share deduction assessed." — [snapshot `2026-09-02--keesm-2835-income-eligible-child-care`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2835-income-eligible-child-care/content.md), accessed 2026-09-02

11. **The Foster Care child care pathway, which is provided under the social service need reason with a different assistance unit and no 12-month limit**
    - Why: `relationship` records `fosterChild`, but the screener cannot identify a foster-care child care case, for whom care is requested, or a placement date. Kansas includes only the adults and the foster children needing care on such a case, and waives the financial tests under the social service reason.
    - `was_in_foster_care` (HouseholdMember, BooleanField, added by MFB-1587) does **not** close this gap. It backs the tile "Ever in foster care, even briefly" — a history fact about the person answering, not a current placement, and not a statement about whom care is requested for. `programs/programs/FOSTER_CARE_SCREENER_GAPS.md` says so directly: formal placement versus informal kinship care is "a question about an existing `fosterChild` household member", which added granularity on that tile would not answer.
    - Handling: **two limbs.** The need reason is `cannot-apply — exclusionary` — a foster-care case is not recognised as such, so it must clear criterion 3 on its own adults' employment like any other household. Under criteria 1, 4 and 5 a `fosterChild` is `assumed-met` and treated as an ordinary eligible child, which understates the benefit for a genuine foster-care case (whose financial tests would be waived) and may screen one out on income or resources Kansas would not apply.
    - Source: KEESM 2810 — "Child Care for Children in Foster Care" — [snapshot `2026-09-02--keesm-2810-child-care-general`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2810-child-care-general/content.md), accessed 2026-09-02
    - Source: KEESM 4420 — "For Foster Care Child Care cases, only the adults in the household and the foster children needing care are included on the case." — [snapshot `2026-09-02--keesm-4400-assistance-unit`](../../../sources/ks/ks_ccap/2026-09-02--keesm-4400-assistance-unit/content.md), accessed 2026-09-02

12. **Participation in the Kansas Early Head Start / Child Care Partnership programme — a need reason, a resource-test exemption, a family-share waiver, and a 215-hour plan**
    - Why: the screener collects no KEHS/CC Partnership participation.
    - Handling: **two limbs.** The need reason is `cannot-apply — exclusionary` — a KEHS/CC Partnership family with no adult working 20 hours a week is screened out on criterion 3. The resource-test exemption is `assumed-met`, and the family-share waiver and the 215-hour plan cannot be applied, so an affected family's benefit is understated.
    - Source: KEESM 2835 — "No family share deduction will be assigned to families in which any of the children requesting child care assistance are participating in the partnerships." — [snapshot `2026-09-02--keesm-2835-income-eligible-child-care`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2835-income-eligible-child-care/content.md), accessed 2026-09-02
    - Source: KEESM 7620 — "For children who are participating in the Kansas Early Head Start/Child Care (KEHS/CC) Partnerships, all plans will be written for 215 hours per month unless" — [snapshot `2026-09-02--keesm-7610-child-care-plan-duration`](../../../sources/ks/ks_ccap/2026-09-02--keesm-7610-child-care-plan-duration/content.md), accessed 2026-09-02

13. **Whether the household is within the first two months following loss of TANF eligibility, which exempts it from the resource test, the minimum-hours test and any family share deduction**
    - Why: the screener records current benefit receipt but no benefit end date, so a recently-closed TANF case is indistinguishable from one closed years ago. `CurrentBenefit` carries only the screen and the program.
    - Handling: `assumed-met` on resources and hours; the family share deduction is assessed normally, which understates the benefit for a household inside the window.
    - Source: KEESM 5140 — "families in the first two months following the loss of TANF eligibility" — [snapshot `2026-09-02--keesm-5000-resources`](../../../sources/ks/ks_ccap/2026-09-02--keesm-5000-resources/content.md), accessed 2026-09-02

14. **Whether a child under 18 (or under 19 while in school) is legally responsible for another person in the nuclear family — the sourced exception that removes the child-earnings income exemption**
    - Why: `relationship` (HouseholdMember, CharField) is recorded relative to the head of household, not between members, so a minor parent's own child reads as `grandChild` of the head rather than as that minor's child. No screener field expresses legal responsibility between members.
    - Handling: `assumed-not-applicable` — the child-earnings exemption is applied unconditionally, so a minor who *is* legally responsible has their earnings excluded where Kansas would count them. The error direction is over-inclusive: it lowers countable income, which raises the benefit and the chance of clearing the income ceiling. Safe direction for a screener.
    - Source: KEESM 6410 — "For Child Care, the earnings of any child under age 18 (or age 19 if the child is working toward the attainment of a high school diploma or its equivalent) are exempt unless the child is legally responsible for another person in the nuclear family." — [snapshot `2026-09-02--keesm-6410-exempt-income`](../../../sources/ks/ks_ccap/2026-09-02--keesm-6410-exempt-income/content.md), accessed 2026-09-02

15. **The minor-teen-parent assistance unit, on which the caretaker counts toward family size but their income and resources are excluded from the means test**
    - Why: this is the KEESM 4420 exception for a minor teen parent under 18 who is the only parent in the home and not able to act in their own behalf. Identifying it needs the parent-child link between two members, which head-relative `relationship` cannot express (Data Gap 14), and the "able to act in their own behalf" determination, which has no screener field. It cannot be inferred from a teenager plus `student`.
    - Handling: `cannot-apply — exclusionary` — the caretaker's income and resources are counted like any other adult's. The error direction is exclusionary in both criteria: counting that income raises the deduction band and can push the household over criterion 4's ceiling, and counting those resources can breach criterion 5's $10,000 limit. Both are outcomes Kansas would not reach for such a case. No scenario, per the rule against testing data gaps.
    - Source: KEESM 2835 — "will be included in the family composition count, although their income and resources are not used in the means test" — [snapshot `2026-09-02--keesm-2835-income-eligible-child-care`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2835-income-eligible-child-care/content.md), accessed 2026-09-02
    - Source: KEESM 4420 — "the non-exempt income of the minor parent, other parent (biological or adoptive) of the teen parent’s child who also lives in the home and child is considered" — [snapshot `2026-09-02--keesm-4400-assistance-unit`](../../../sources/ks/ks_ccap/2026-09-02--keesm-4400-assistance-unit/content.md), accessed 2026-09-02

16. **Which adult on the case, if any, is the primary caretaker of a given child — the condition KEESM 4410's catch-all attaches to every child who is not a biological or adopted child of an adult on the case**
    - Why: `relationship` (HouseholdMember, CharField) is recorded relative to the head of household and records no caretaking. The screener has no field expressing which adult cares for which child, the same structural limitation as Data Gaps 14 and 15.
    - Handling: `assumed-met` — every member in criterion 1's relationship set is treated as primary-caretaken by an adult on the case. The direction is **over-inclusive, and unusually so: it can establish the verdict, not merely raise the value.**
    - A `grandChild`, a minor `sisterOrBrother`, `stepSisterOrBrother` or `relatedOther` whom nobody on the case actually caretakes is counted as an eligible child, and where they are the only such child the household passes criterion 1 where DCF would not open a case. Inclusive is the safe direction for a screener, and the alternative — demanding a caretaking fact MFB can never see — would deny every household whose only child in care is not the head's own.
    - Criterion 3's unit note carries the mirror image of this gap on the adult side: KEESM 4410 puts a cohabiting `boyfriendOrGirlfriend` on the case when one of the two adults primary-caretakes, and MFB cannot tell which. Both are the same missing fact, disclosed in both places.
    - Source: KEESM 4410 — "as well as other children who reside in the household and for whom an adult on the case is the primary caretaker" — [snapshot `2026-09-02--keesm-4400-assistance-unit`](../../../sources/ks/ks_ccap/2026-09-02--keesm-4400-assistance-unit/content.md), accessed 2026-09-02

17. **Which children in the household are children for whom child care is actually requested — the set Kansas authorizes care for, which is narrower than the set that meets criterion 1**
    - Why: the screener collects no statement of whom care is needed for. Criterion 1 establishes that a child *may* receive care, from age and relationship; Kansas authorizes hours for the children a family asks for care for, and a `childCare` expense row is a single household figure with no per-child decomposition.
    - Handling: `assumed-met` — **every** child meeting criterion 1 is treated as a child for whom care is requested. That assumption is what makes the value's sum run over the whole eligible-child set, and it is the largest single multiplier in the estimate.
    - The direction is **over-inclusive on the value**: a school-age child who needs no paid care still contributes a full 129-hour block, so a household with one preschooler and one ten-year-old is estimated at roughly twice the amount Kansas would authorize. Data Gap 2 governs how many hours each child is authorized; this gap governs which children are counted at all.
    - It runs **both ways on criterion 5**. The KEESM 5140 SSI exemption turns on "the only children receiving child care assistance" also receiving SSI, and this spec tests criterion 1's eligible-child set in its place. A household whose SSI preschooler is the only child in care, but which also contains a school-age sibling needing none, fails that test where DCF would exempt it; the mirror case wrongly exempts. Scenario 20 sits on the clean case, where the eligible-child set and the requested set coincide.
    - Source: KEESM 4410 — "if one of the adults is the primary caretaker of the child for whom assistance is requested" — [snapshot `2026-09-02--keesm-4400-assistance-unit`](../../../sources/ks/ks_ccap/2026-09-02--keesm-4400-assistance-unit/content.md), accessed 2026-09-02
    - Source: Kansas DCF, Child Care Assistance Program — "proof of citizenship and date of birth for all children for whom assistance is requested" — [snapshot `2026-09-03--dcf-child-care-assistance-program`](../../../sources/ks/ks_ccap/2026-09-03--dcf-child-care-assistance-program/content.md), accessed 2026-09-03

## Priority Criteria

Kansas ranks families for child care service. MFB does not rank results, so these are carried in
the program description and never applied as eligibility — a fully eligible low-priority family
may still wait.

- Priority Code #1 — families in Work Programs receiving TANF or food assistance, and Tribal TANF recipients — captured: description text
- Priority Code #2 — families receiving child care for a qualified Social Service reason — captured: description text
- Priority Code #3 — families no longer eligible for TANF transitioning to employment with income at or below 85% SMI — captured: description text
- Priority Code #4 — teen parents completing high school or a GED — captured: description text
- Priority Code #5 — families who claim to be homeless, self-declaration accepted, needing care to maintain employment or an approved education plan — captured: description text. `needs_homeless_services` (Screen, BooleanField) is collected and would allow this tier to be identified, but it is not read here because priority ranking is not eligibility. (`housing_situation` also exists on the model but is absent from `screener/serializers.py` and never populated for real screens.)
- Priority Code #6 — employed families with income at or below 85% SMI — captured: description text
- Program description tie-back: the description says in one sentence that DCF serves families in priority order when child care funds are limited, so a user who qualifies but waits understands why. The individual tiers are **not** named in user-facing copy — they are recorded here. The funding-contingent framing is DCF's own; no captured source uses the words "waiting list".
- Source: KEESM 2840 — "The agency has established the following priorities for families receiving child care assistance:" — [snapshot `2026-09-02--keesm-2840-child-care-service-priorities`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2840-child-care-service-priorities/content.md), accessed 2026-09-02
- Source: KEESM 2840 — "Priority Code #5 - Families who claim to be homeless (self-declaration is accepted) and need child care to maintain employment or participate in an approved educational plan." — [snapshot `2026-09-02--keesm-2840-child-care-service-priorities`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2840-child-care-service-priorities/content.md), accessed 2026-09-02
- Source: Kansas DCF, Child Care Assistance Program — "Child Care Assistance may continue as long as the family remains eligible and child care funds are available." — [snapshot `2026-09-03--dcf-child-care-assistance-program`](../../../sources/ks/ks_ccap/2026-09-03--dcf-child-care-assistance-program/content.md), accessed 2026-09-03

## Related Programs

- **Kansas Early Head Start / Child Care Partnership** — a separate programme with its own eligibility regime, and simultaneously a CCAP need reason, resource-test exemption and family-share waiver (Data Gap 12). MFB already ships `ks_early_head_start` and `ks_head_start` under the same `child_care` category.
- **Foster Care child care** — administered under the social service need reason with its own assistance unit and no 12-month limit (Data Gap 11). Not folded into this spec's criteria.
- Source: KEESM 2835 — "all other aspects of eligibility shall be determined by the Early Head Start grantees based on Early Head Start eligibility standards" — [snapshot `2026-09-02--keesm-2835-income-eligible-child-care`](../../../sources/ks/ks_ccap/2026-09-02--keesm-2835-income-eligible-child-care/content.md), accessed 2026-09-02

## Benefit Value

Kansas sets the benefit from its own maximum hourly rate, not from what the family actually pays:
a provider charging less than the DCF rate may raise its charge to a DCF family up to that rate.
The monthly benefit is the rate for each eligible child times that child's authorized monthly
hours, less one Family Share Deduction for the household.

DCF can compute this exactly because it knows the provider type and the authorized care schedule.
**MFB observes neither**, so the figure below is an **MFB-owned estimate**, not an amount Kansas
publishes or guarantees. It **pins the licensed-centre rate** and **derives the authorized
hours block** from the household's reported work schedule.

It also pins **which children are in the sum**. Kansas authorizes hours for the children a family
requests care for; MFB cannot see that set and sums over every child meeting criterion 1 instead.
That is Data Gap 17, and it is over-inclusive: a school-age child who needs no paid care still
contributes a full block. Of the three pinned axes it is the one that scales the figure by whole
multiples rather than shifting it.

- Value: `max( 1, 12 × max( Σ_children (centre rate for the child's age band and county group × authorized hours) − FSD, 0 ) )` per year — where authorized hours is 129 or 215 per the block rule below — where FSD is the single Appendix F-1 Family Share Deduction for the household's family size and income band, deducted **once per household**, not per child. The inner `max(…, 0)` is the policy clamp; the outer `max( 1, … )` is a visibility floor, not a benefit claim — see the note below
- `value_format`: `estimated_annual`
- Variation axes: county group (3) · child age band (4) · number of eligible children · family size × income band (the FSD table) · the FSD-exempt pathways — each appears in Test Scenarios
- Constant: county group from `county` (Screen) — Group #1 = Johnson; Group #2 = Butler, Douglas, Ellis, Geary, Greeley, Harvey, Jefferson, Leavenworth, Miami, Pottawatomie, Riley, Rush, Scott, Sedgwick, Seward, Shawnee, Wyandotte; Group #3 = all other counties
- Constant: centre hourly rate by age band in months, banded on accessor `calc_age` (HouseholdMember) — `0–11 months (age 0) → 7.33 / 6.28 / 6.28`, `12–35 (ages 1–2) → 6.25 / 5.28 / 5.26`, `36–59 (ages 3–4) → 5.51 / 4.13 / 4.27`, `60+ (age 5 and older) → 4.81 / 3.65 / 3.16` for Groups #1 / #2 / #3
- Constant: Family Share Deduction from Appendix F-1, by family size and monthly gross income band. Each cell gives the band's **upper** bound and the deduction that applies within it; a band's lower bound is one cent above the previous band's upper bound, and the first band starts at `$0`. The comparison is inclusive at the upper bound.

| FPL band | Family of 2 | Family of 3 | Family of 4 | Family of 5 | Family of 6 | Family of 7 | Family of 8 |
|---|---|---|---|---|---|---|---|
| Up to 100% FPL | ≤$1,803 → $0 | ≤$2,277 → $0 | ≤$2,750 → $0 | ≤$3,223 → $0 | ≤$3,697 → $0 | ≤$4,170 → $0 | ≤$4,643 → $0 |
| Up to 110% FPL | ≤$1,984 → $54 | ≤$2,504 → $68 | ≤$3,025 → $83 | ≤$3,546 → $97 | ≤$4,066 → $111 | ≤$4,587 → $125 | ≤$5,108 → $139 |
| Up to 120% FPL | ≤$2,164 → $60 | ≤$2,732 → $75 | ≤$3,300 → $91 | ≤$3,868 → $106 | ≤$4,436 → $122 | ≤$5,004 → $138 | ≤$5,572 → $153 |
| Up to 130% FPL | ≤$2,344 → $65 | ≤$2,960 → $82 | ≤$3,575 → $99 | ≤$4,190 → $116 | ≤$4,806 → $133 | ≤$5,421 → $150 | ≤$6,036 → $167 |
| Up to 140% FPL | ≤$2,525 → $70 | ≤$3,187 → $89 | ≤$3,850 → $107 | ≤$4,513 → $126 | ≤$5,175 → $144 | ≤$5,838 → $163 | ≤$6,501 → $181 |
| Up to 150% FPL | ≤$2,705 → $76 | ≤$3,415 → $96 | ≤$4,125 → $116 | ≤$4,835 → $135 | ≤$5,545 → $155 | ≤$6,255 → $175 | ≤$6,965 → $195 |
| Up to 160% FPL | ≤$2,885 → $81 | ≤$3,643 → $102 | ≤$4,400 → $124 | ≤$5,157 → $145 | ≤$5,915 → $166 | ≤$6,672 → $188 | ≤$7,429 → $209 |
| Up to 170% FPL | ≤$3,066 → $87 | ≤$3,870 → $109 | ≤$4,675 → $132 | ≤$5,480 → $155 | ≤$6,284 → $177 | ≤$7,089 → $200 | ≤$7,894 → $223 |
| Up to 180% FPL | ≤$3,246 → $92 | ≤$4,098 → $116 | ≤$4,950 → $140 | ≤$5,802 → $164 | ≤$6,654 → $189 | ≤$7,506 → $213 | ≤$8,358 → $237 |
| Up to 185% FPL | ≤$3,336 → $97 | ≤$4,212 → $123 | ≤$5,088 → $149 | ≤$5,963 → $174 | ≤$6,839 → $200 | ≤$7,715 → $225 | ≤$8,590 → $251 |
| Up to 85% SMI | ≤$5,439 → $167 | ≤$6,719 → $211 | ≤$7,998 → $254 | ≤$9,278 → $298 | ≤$10,558 → $342 | ≤$10,798 → $386 | ≤$11,038 → $430 |

- Implementation note: the formula's **shape** is sourced, not inferred — the hours block is per child (KEESM 7620, KEESM 10200), the deduction is one per household (KEESM 7540, KEESM 7541), and the annualisation is × 12 (KEESM 7610). The citations below carry the shape as well as the magnitudes.
- Implementation note: the FSD grid and criterion 4's income limit are the same table — a family size's top-band upper bound *is* its income limit, so a household above the last band is ineligible rather than falling through to the top deduction.
- Implementation note: the grid above stops at family size 8 by choice, not because F-1 does. **Appendix F-1 publishes sizes 2 through 11** — a family of 9 is capped at $11,278 with a $473 deduction, 10 at $11,518 / $517, and 11 at $11,758 / $561. Those three rows are deliberately not carried: the screener form validates `.lte(8)`, so no form-submitted screen can reach them, and an API-path screen above 8 is clamped to the family-of-8 row. See criterion 4's note on raising the cap.
- Implementation note: the grid above is authoritative. Appendix F-1 carries five printing slips and the grid resolves all of them; one is load-bearing — the family-of-3 180% bound prints `$3,870.10` where the ascending sequence implies `$3,870.01` (Scenario 16 pins the resolution). Do not transcribe F-1 literally and do not edit the snapshots.
- Implementation note: Appendix C-18 and C-18a misspell "Greely" for Greeley and "Pottawatomi" for Pottawatomie. Use the KS white label's spellings — a literal transcription fails to match both counties and silently drops them into Group #3.
- Implementation note: band the rate on accessor `calc_age`, which is exactly equivalent to banding on months for the centre columns. The licensed-*home* bands are not aligned this way, so the equivalence would not survive a change of pinned provider type.
- Implementation note: rates are **not** monotonic in county group — Group #3's 36–59 month centre rate ($4.27) exceeds Group #2's ($4.13), as printed in C-18a. Do not derive Group #3 by scaling Group #2.
- Implementation note: the rate is set by the **provider's** county, not the family's. MFB observes only the family's county and uses it as a proxy; for an out-of-state provider Kansas caps the rate at the nearest signing region's county.
- Source: KEESM 10240 — "may not be more than the rate of the county in the Region signing the Agreement for Purchase of DCF Child Care that is nearest to the provider." — [snapshot `2026-09-02--keesm-10200-child-care-payments`](../../../sources/ks/ks_ccap/2026-09-02--keesm-10200-child-care-payments/content.md), accessed 2026-09-02
- Implementation note: the outer `max( 1, … )` is a visibility floor, not a claim that Kansas pays $1 — an eligible program valued at `$0` is dropped from the results page entirely. The inner `max( …, 0 )` is the policy clamp, and DCF genuinely pays such a household nothing.
- Implementation note: the authorized block is **derived, not pinned**. KEESM 7620 sets hours needed from the adults' weekly work schedule (including travel time) plus the child's school schedule, and authorizes 129 hours where that comes to 108 or fewer and 215 where it comes to more. The work schedule is the one input the screener records — `hours_worked`, on hourly streams — so the block follows it: `min(weekly hours across the adults on the case) × 4.35 > 108 → 215, else 129`. The `4.35` is the same weeks-per-month factor the screener's own income conversion uses, so a week of work and a week of care are counted alike. The turnover falls between 24 and 25 reported hours a week.
- Implementation note: the block reads the **least**-working adult on the case, not the head and not the most. Care is needed only while every adult is away, and with no actual schedules the overlap between two adults cannot exceed the shorter of them — so the minimum is that overlap's upper bound. Staggered shifts need less care than this allows, never more. KEESM 2810 grounds the direction: it denies the household where one parent works and the other does not, the non-employed parent being expected to provide the care.
- Implementation note: the derivation is **all-or-nothing per household**. `hours_worked` exists only on hourly streams, so one salaried, weekly or biweekly adult on the case makes the household's minimum unknowable, and the estimate falls back to the 129-hour block rather than reading the remaining adult's hours as if they were the household's. Same fallback where no adult on the case has any derivable hours.
- Implementation note: two of KEESM 7620's own inputs remain unobservable and pull in opposite directions. **Travel time** is counted by 7620 and raises hours needed; the **child's school schedule** lowers them, which is why 7620's example of a child needing the 215-hour block is "a four year old who is **not** in pre-school, Head Start or pre-kindergarten". Neither is collected, so the derivation reads the work schedule alone. See Data Gap 2.
  - Source: KEESM 7620 — "The weekly work schedule (including travel time) and the child’s school schedule (if applicable) will be entered into the system to obtain a reasonable estimate of the monthly hours to be authorized for benefits." — [snapshot `2026-09-02--keesm-7610-child-care-plan-duration`](../../../sources/ks/ks_ccap/2026-09-02--keesm-7610-child-care-plan-duration/content.md), accessed 2026-09-02
- Source: KEESM 7620 — "215 hours per month for children who need more than 108 hours of care per month (i.e. a four year old who is not in pre-school, Head Start or pre-kindergarten)" — [snapshot `2026-09-02--keesm-7610-child-care-plan-duration`](../../../sources/ks/ks_ccap/2026-09-02--keesm-7610-child-care-plan-duration/content.md), accessed 2026-09-02
- Implementation note: the whole figure is returned from `household_value()`, with no member values, because both `max` operations are on the household total. `il_ccap` splits the same shape across `member_value()` and a negative `household_value()`; in that shape the clamp cannot be expressed at all.
- Implementation note: truncate the annual figure to whole dollars **inside** `household_value()`, which the framework types `int`. The `math.trunc` in `screener/views.py` is not sufficient — it touches only the payload's `estimated_value`, while the results card reads `household_value` and **rounds** it. Six scenarios below turn on that cent.
- Implementation note: FSD is `$0` for five sourced cases — TANF receipt (`has_base_benefit("tanf")`), a former TANF recipient inside the post-closure window, an unemployed food assistance work program participant, the Social Services need reason, and a child requesting care who participates in the KEHS/CC Partnership. Only the first is observable; the rest are Data Gaps 13, 9, 10 and 12, so the deduction is assessed normally for them.
- Implementation note: four sourced elements are deliberately excluded because MFB cannot observe what they turn on — enrollment-fee assistance (up to $50 per child per case), the Enhanced Rate for Special Care ($7.34/hour), the $0-month rule, and proration of the first month from the application date.
- Source: KEESM 10240 — "The DCF rates are used to determine client benefit levels. If providers charge less than the DCF rate, they may choose to charge families receiving DCF child care benefits up to the DCF rate." — [snapshot `2026-09-02--keesm-10200-child-care-payments`](../../../sources/ks/ks_ccap/2026-09-02--keesm-10200-child-care-payments/content.md), accessed 2026-09-02
- Source: KEESM 10240 — "Provider rates are assigned according to the provider's county of residence in Kansas." — [snapshot `2026-09-02--keesm-10200-child-care-payments`](../../../sources/ks/ks_ccap/2026-09-02--keesm-10200-child-care-payments/content.md), accessed 2026-09-02
- Source: KEESM 7620 — "Once the number of hours of care needed is determined, the following blocks of time will be authorized for each child:" — [snapshot `2026-09-02--keesm-7610-child-care-plan-duration`](../../../sources/ks/ks_ccap/2026-09-02--keesm-7610-child-care-plan-duration/content.md), accessed 2026-09-02
- Source: KEESM 10200 — "a child care plan has been established for each child for each provider" — [snapshot `2026-09-02--keesm-10200-child-care-payments`](../../../sources/ks/ks_ccap/2026-09-02--keesm-10200-child-care-payments/content.md), accessed 2026-09-02
- Source: KEESM 7620 — "Part time – 129 hours per month if the hours needed is determined to be 108 or less" — [snapshot `2026-09-02--keesm-7610-child-care-plan-duration`](../../../sources/ks/ks_ccap/2026-09-02--keesm-7610-child-care-plan-duration/content.md), accessed 2026-09-02
- Source: KEESM 7620 — "Full-time – 215 hours per month if the hours needed is determined to be more than108" — [snapshot `2026-09-02--keesm-7610-child-care-plan-duration`](../../../sources/ks/ks_ccap/2026-09-02--keesm-7610-child-care-plan-duration/content.md), accessed 2026-09-02
- Source: KEESM 7540 — "The family share deduction is determined by considering the number of persons in the household and nonexempt sources of income." — [snapshot `2026-09-02--keesm-7540-child-care-income-eligibility`](../../../sources/ks/ks_ccap/2026-09-02--keesm-7540-child-care-income-eligibility/content.md), accessed 2026-09-02
- Source: KEESM 7541 — "The family share deduction is deducted prior to issuing the monthly child care benefit." — [snapshot `2026-09-02--keesm-7540-child-care-income-eligibility`](../../../sources/ks/ks_ccap/2026-09-02--keesm-7540-child-care-income-eligibility/content.md), accessed 2026-09-02
- Source: KEESM 7610 — "Initial eligibility periods shall include at least twelve full months of eligibility." — [snapshot `2026-09-02--keesm-7610-child-care-plan-duration`](../../../sources/ks/ks_ccap/2026-09-02--keesm-7610-child-care-plan-duration/content.md), accessed 2026-09-02
- Source: KEESM 7541 — "A monthly family share deduction shall be assessed for Income Eligible (Non-TANF) clients with income at or over 100% of the federal poverty level except as specified in KEESM 2835." — [snapshot `2026-09-02--keesm-7540-child-care-income-eligibility`](../../../sources/ks/ks_ccap/2026-09-02--keesm-7540-child-care-income-eligibility/content.md), accessed 2026-09-02
- Source: KEESM 7541 — "When the family share deduction exceeds the cost of care of some months, but not others during the 12-month eligibility period, the case will remain open" — [snapshot `2026-09-02--keesm-7540-child-care-income-eligibility`](../../../sources/ks/ks_ccap/2026-09-02--keesm-7540-child-care-income-eligibility/content.md), accessed 2026-09-02
- Source: KEESM 10260 — "DCF can subsidize clients up to $50 per child per case towards an enrollment fee for an approved provider if the provider charges an enrollment fee to the private sector." — [snapshot `2026-09-02--keesm-10260-child-care-benefit-computation`](../../../sources/ks/ks_ccap/2026-09-02--keesm-10260-child-care-benefit-computation/content.md), accessed 2026-09-02
- Source: KEESM 10270 — "DCF pays a standard rate for in-home child care regardless of county of residence. This rate is $2.42/hour for the State." — [snapshot `2026-09-02--keesm-10260-child-care-benefit-computation`](../../../sources/ks/ks_ccap/2026-09-02--keesm-10260-child-care-benefit-computation/content.md), accessed 2026-09-02
- Source: KEESM 7401 — "For applications filed after the first of the month, the amount of assistance is to be prorated from the date of application." — [snapshot `2026-09-02--keesm-7400-financial-eligibility`](../../../sources/ks/ks_ccap/2026-09-02--keesm-7400-financial-eligibility/content.md), accessed 2026-09-02
- Source: Appendix C-18 — "$7.34 per hour for all ages of children, for all approvable" — [snapshot `2026-09-02--appendix-c-18-provider-rate-chart`](../../../sources/ks/ks_ccap/2026-09-02--appendix-c-18-provider-rate-chart/content.md), accessed 2026-09-02
- Source: Appendix C-18 — "benefits for families using licensed home providers or child care centers are paid at approximately the 75th percentile or better" — [snapshot `2026-09-02--appendix-c-18-provider-rate-chart`](../../../sources/ks/ks_ccap/2026-09-02--appendix-c-18-provider-rate-chart/content.md), accessed 2026-09-02
- Source: Appendix C-18 — "Out of home relative providers are paid at a rate that is 65% of the rate for licensed child care homes." — [snapshot `2026-09-02--appendix-c-18-provider-rate-chart`](../../../sources/ks/ks_ccap/2026-09-02--appendix-c-18-provider-rate-chart/content.md), accessed 2026-09-02
- Source: Appendix C-18a — "Group #1 = Johnson" — [snapshot `2026-09-02--appendix-c-18a-provider-rate-county-grouping`](../../../sources/ks/ks_ccap/2026-09-02--appendix-c-18a-provider-rate-county-grouping/content.md), accessed 2026-09-02
- Justification: **one assumption remains pinned — the provider type**, and it is the estimate's largest remaining source of error. Kansas pays four different hourly rates, and the licensed centre is the **highest** of them. For a preschooler in Johnson County: licensed centre `$5.51`, licensed home `$4.23`, out-of-home relative `$2.81` (65% of the licensed-home rate), in-home relative `$2.42` flat statewide. C-18 records centre and licensed-home benefits as set at approximately the 75th percentile of surveyed market price, which makes a centre the defensible standard case — but that is a fact about how DCF sets rates, **not** evidence about which provider type CCAP families actually use. That fact lives in DCF administrative data and no captured source carries it. A household using an in-home relative is overstated by roughly 2.3x; one using a licensed home by roughly 1.3x. The pin is deliberate and stands until DCF's provider mix is available; it is not a data gap that further research on published sources could close.
- Justification: the hours block is **no longer pinned**. It was, at 129 hours, on the reasoning that the choice turned on an hours-needed estimate MFB could not observe. That reasoning was too strong: 7620 names the adults' work schedule as the primary input, and the screener records it for hourly earners. Deriving it removes the systematic understatement the pin caused for full-time-working households — under the old pin, a household on the 215 block was understated by **76%** of the shown value, not the 67% an earlier draft of this spec stated (67% is the ratio of the hours alone; because the family share is a fixed subtraction, the effect on the value is larger). What survives is narrower and disclosed above: travel time and the school schedule are still unobservable, and a household with any non-hourly earner on the case still falls back to 129.

## Test Scenarios

**Coverage map**

| Rule / variation axis | Scenarios |
|---|---|
| C1 child under 13 | 1 (pass); 6a (boundary, turns 13 → fail); 6b (boundary, one month younger → pass) |
| C1 13–18 disability extension | 7 (pass) |
| C1 eligible-child set is 4410's catch-all set | 14 (`grandChild` and `relatedOther` both count; `il_ccap`'s six-value set understates by $8,529) |
| C2 child citizenship (config) | not scenario-testable — see Known scenario gaps |
| C3 all adults ≥20 hrs/week | 1, 2a (pass); 8 (second adult at 19 hrs → fail) |
| C3 incapacity exempts an adult from the 20-hour test | 8c (disabled spouse at 19 hrs → pass, where Scenario 8 fails) |
| C3 unit is the nuclear family | 8b (a non-nuclear adult with no income does not fail the test) |
| C3 tested adult not employed at all | 8d (spouse with no earned-income stream → fail, where a fall-open reading returns $7,461) |
| C3 federal minimum wage floor | 9b (boundary, exactly $7.25 → pass); 9 (boundary, $7.24 → fail) |
| C3 wage floor is the adult's average across streams | 9c (two hourly jobs, one at $6.00 → pass on a $10.00 average) |
| C3 TANF bypasses the whole activity test | 19 (TANF household under both the hours and the wage floor → pass) |
| C4 income ≤ F-1 limit | 1 (pass); 4a (boundary, exactly at limit → pass); 4b (boundary, $0.01 over → fail) |
| C4 FSD band | 2a/2b (boundary pair, $0.01 moves the band); 16 (the band whose F-1 bound carries a source typo) |
| C4 FSD $0 below 100% FPL | 9b |
| C4 TANF income waiver | 12 (income above the ceiling, eligible only because of the waiver) |
| C4 child-earnings exemption | 10 |
| C4 SSI recipient's income exempt | 18 (the SSI parent's wages excluded too, not just the SSI) |
| C5 resources ≤ $10,000 | 1 (pass, exactly at the limit); 11 (boundary, $0.01 over → fail); 12 (TANF exemption bypasses) |
| C5 SSI exemption is per eligible child | 20 (only eligible child receives SSI → bypass); 18b (SSI parent, non-SSI child → no bypass) |
| C5 null assets fall open | 17 |
| Value: county group | 1 (#1); 3a (#2); 3b (#3, non-monotonic) |
| Value: age band → rate | 5a/5b (59 vs 60 months); 13 (11 and 35 month edges) |
| Value: multiple children, one FSD | 13 |
| Value: `max(…, 0)` policy clamp and `max( 1, … )` visibility floor | 15 (deduction exceeds gross → clamp to $0, floor to $1) |
| Value: truncation, not rounding | 3b, 5b, 6b, 7, 9b, 14 |
| Value: authorized block derived from reported hours | 2a (20 hrs → 129); 1 (30 hrs → 215); 15 (both adults 20 hrs → 129, which is what makes the clamp reachable); 8c (19-hr spouse pulls the household to 129); 13 (25-hr spouse, 20-hr head → 129 on the minimum) |

**Known scenario gaps**: criterion 2 has no scenario — `legal_status_required` is never applied as
an eligibility gate in the backend, so asserting an outcome on it would test the frontend, not this
program. No scenario is written for any of the seventeen data gaps. Where a gap is handled
inclusively, no committed result turns on it. Where a gap is exclusionary — the set the Data Gaps
preamble names, being the need-reason limbs of Gaps 4, 7, 8, 9, 10, 11 and 12 together with Gap 15 —
the exclusion is a limit on what the screener can see rather than a rule to assert, and the
criterion that does the screening carries the committed behaviour and its own scenarios. Three
further items carry no scenario deliberately. The **under-19 student limb** of the child-earnings
exemption shifts only the deduction band and not the verdict. The two remaining nullable-field
guards are not reachable through the screener form, which requires hours on an hourly income stream
and a birth year and month for every member, so neither can be entered: **`hours_worked` null on an
hourly stream** (treated as unevaluable, falls open) and **`birth_year_month` and `age` both null**
(treated as not an eligible child). Both are API-path robustness guards rather than screener
branches; the committed handling sits on criterion 3 and criterion 1 respectively.

All scenarios use reference date **2026-09-02**. Every ZIP is present in `counties_by_zipcode` for
the KS white label with a selectable county, so every scenario is submittable through the screener
as it stands. Where a scenario needs an exact monthly income, the head holds at least two wage
streams: one or more `hourly` streams that establish the hours and wage-floor facts for criterion 3,
plus a `monthly` stream that tunes the total for criterion 4. Each stated total is the **quantised** figure criterion 4
compares. An hourly stream can never reach a whole-cent total on its own — `_hour_to_month` multiplies
by the float-derived `Decimal(4.35)`, which is strictly below 4.35 — so criterion 4's cent
quantisation is what makes every income below exact, and what gives Scenarios 2a and 4a their bite.
Benefit values are truncated to whole dollars in the calculator, not rounded — see Benefit Value on why the truncation cannot be left to `screener/views.py`.

### Scenario 1: Baseline — Johnson County, one eligible child — Eligible, $13,147
**What we're checking**: the whole eligible path, the committed value arithmetic, and the resource limit at exactly $10,000.
**Expected**: Eligible — $13,147 (30 hrs/week × 4.35 = 130.5 hours needed, over 108, so the 215-hour block; centre rate $5.51 for 56 months in Group #1 × 215 hrs = $1,184.65/month; − $89 FSD for family of 3 in the $2,960.01–$3,187 band = $1,095.65/month; × 12 = $13,147.80 → $13,147)
**Steps**:
* Location: ZIP `66210`, county `Johnson County`
* Person 1: born March 1994 (age 32), head of household, wages `hourly` $23.00/hr, hours worked 30/week (= $3,001.50/month)
* Person 2: born January 2022 (age 4, 56 months), child
* Person 3: born May 2010 (age 16), child, no income, no disability
* Household assets: $10,000.00
**Why this matters**: the reference case every other scenario perturbs. Kills a wrong rate lookup and the 215-hour block; pins the resource limit as inclusive at exactly $10,000 (a strict `< 10_000` would deny this household); and Person 3 pins that a 16-year-old counts toward family size but is not an eligible child.

### Scenario 2a: FSD band lower edge — Eligible, $7,557
**What we're checking**: the F-1 band is read inclusively at its upper bound.
**Expected**: Eligible — $7,557 ($710.79 − $81 FSD for family of 2 in the $2,705.01–$2,885 band = $629.79/month; × 12 = $7,557.48 → $7,557)
**Steps**:
* Location: ZIP `66210`, county `Johnson County`
* Person 1: born March 1994 (age 32), head of household, wages `hourly` $10.00/hr, hours worked 20/week (= $870.00/month), plus wages `monthly` $2,015.00 (total $2,885.00)
* Person 2: born January 2022 (age 4, 56 months), child
* Household assets: $2,000
**Why this matters**: paired with 2b, pins the band comparison to the cent. Also the exactly-20-hours pass case for criterion 3.

### Scenario 2b: FSD band upper edge, one cent later — Eligible, $7,485
**What we're checking**: one cent of income moves the household into the next FSD band.
**Expected**: Eligible — $7,485 ($710.79 − $87 FSD for family of 2 in the $2,885.01–$3,066 band = $623.79/month; × 12 = $7,485.48 → $7,485)
**Steps**:
* Location: ZIP `66210`, county `Johnson County`
* Person 1: born March 1994 (age 32), head of household, wages `hourly` $10.00/hr, hours worked 20/week (= $870.00/month), plus wages `monthly` $2,015.01 (total $2,885.01)
* Person 2: born January 2022 (age 4, 56 months), child
* Household assets: $2,000
**Why this matters**: kills an off-by-one band comparison (`<` where `<=` belongs) in the F-1 lookup — the likeliest table bug, worth $72/year here.

### Scenario 3a: County group #2 — Eligible, $9,587
**What we're checking**: the county-group axis of the rate table.
**Expected**: Eligible — $9,587 (215-hour block; centre rate $4.13 in Group #2 × 215 = $887.95/month; − $89 = $798.95/month; × 12 = $9,587.40 → $9,587)
**Steps**:
* Location: ZIP `67202`, county `Sedgwick County`
* Person 1: born March 1994 (age 32), head of household, wages `hourly` $23.00/hr, hours worked 30/week (= $3,001.50/month)
* Person 2: born January 2022 (age 4, 56 months), child
* Person 3: born May 2010 (age 16), child, no income, no disability
* Household assets: $2,000
**Why this matters**: kills a single hardcoded rate table, or a county-group mapping that defaults every county to Group #1.

### Scenario 3b: County group #3 pays more than group #2 — Eligible, $9,948
**What we're checking**: the non-monotonicity — the Group #3 rate for this age band is higher than Group #2's.
**Expected**: Eligible — $9,948 (215-hour block; centre rate $4.27 in Group #3 × 215 = $918.05/month; − $89 = $829.05/month; × 12 = $9,948.60 → $9,948)
**Steps**:
* Location: ZIP `67156`, county `Cowley County`
* Person 1: born March 1994 (age 32), head of household, wages `hourly` $23.00/hr, hours worked 30/week (= $3,001.50/month)
* Person 2: born January 2022 (age 4, 56 months), child
* Person 3: born May 2010 (age 16), child, no income, no disability
* Household assets: $2,000
**Why this matters**: kills any implementation that assumes rates fall monotonically with county group, or derives Group #3 by scaling Group #2. Also a truncation case — $5,541.96 would round to $5,542.

### Scenario 4a: Income exactly at the 85% SMI limit — Eligible, $6,525
**What we're checking**: the income ceiling is inclusive at the published limit.
**Expected**: Eligible — $6,525 ($710.79 − $167 FSD for family of 2 in the $3,336.01–$5,439 band = $543.79/month; × 12 = $6,525.48 → $6,525)
**Steps**:
* Location: ZIP `66210`, county `Johnson County`
* Person 1: born March 1994 (age 32), head of household, wages `hourly` $10.00/hr, hours worked 20/week (= $870.00/month), plus wages `monthly` $4,569.00 (total $5,439.00 — exactly the family-of-2 limit)
* Person 2: born January 2022 (age 4, 56 months), child
* Household assets: $2,000
**Why this matters**: kills a strict `<` at the income ceiling, which would deny a family sitting exactly on the published limit.

### Scenario 4b: Income one cent over the limit — Ineligible
**What we're checking**: the ceiling actually bites.
**Expected**: Ineligible (criterion 4 — monthly income $5,439.01 exceeds the family-of-2 limit of $5,439)
**Steps**:
* Location: ZIP `66210`, county `Johnson County`
* Person 1: born March 1994 (age 32), head of household, wages `hourly` $10.00/hr, hours worked 20/week (= $870.00/month), plus wages `monthly` $4,569.01 (total $5,439.01)
* Person 2: born January 2022 (age 4, 56 months), child
* Household assets: $2,000
**Why this matters**: paired with 4a, kills a table that silently falls through to the top band instead of denying above it.

### Scenario 5a: Rate age band, 59 months — Eligible, $13,147
**What we're checking**: the upper edge of the 36–59 month centre band.
**Expected**: Eligible — $13,147 (215-hour block; $5.51 × 215 = $1,184.65; − $89 = $1,095.65; × 12 = $13,147.80 → $13,147)
**Steps**:
* Location: ZIP `66210`, county `Johnson County`
* Person 1: born March 1994 (age 32), head of household, wages `hourly` $23.00/hr, hours worked 30/week (= $3,001.50/month)
* Person 2: born October 2021 (age 4, 59 months), child
* Person 3: born May 2010 (age 16), child, no income, no disability
* Household assets: $2,000
**Why this matters**: paired with 5b, pins the band edge — one month of age is worth $1,083.60/year.

### Scenario 5b: Rate age band, 60 months — Eligible, $11,341
**What we're checking**: the child crosses into the 60-months-and-older band.
**Expected**: Eligible — $11,341 (215-hour block; $4.81 × 215 = $1,034.15; − $89 = $945.15; × 12 = $11,341.80 → $11,341)
**Steps**:
* Location: ZIP `66210`, county `Johnson County`
* Person 1: born March 1994 (age 32), head of household, wages `hourly` $23.00/hr, hours worked 30/week (= $3,001.50/month)
* Person 2: born September 2021 (age 5, 60 months), child
* Person 3: born May 2010 (age 16), child, no income, no disability
* Household assets: $2,000
**Why this matters**: kills an off-by-one on the band edge (`< 60` vs `<= 60`) and a table that omits the oldest band. Also a truncation case — $6,377.88 would round to $6,378.

### Scenario 6a: Child reaches 13 in the reference month — Ineligible
**What we're checking**: the age ceiling on the month boundary `calc_age` actually uses.
**Expected**: Ineligible (criterion 1 — `calc_age` returns 13 because the reference month equals the birth month, and the child has no disability)
**Steps**:
* Location: ZIP `66210`, county `Johnson County`
* Person 1: born March 1994 (age 32), head of household, wages `hourly` $23.00/hr, hours worked 30/week (= $3,001.50/month)
* Person 2: born September 2013 (age 13, 156 months), child, no disability
* Household assets: $2,000
**Why this matters**: `age_from_date` flips on the first of the birth month, not the birthday, so this kills a day-precision age test. It tests the sourced *initial*-eligibility rule rather than a simplification of it: KEESM 2810 establishes no initial eligibility for a 13-year-old unless the incapacity or court-supervision branch applies, and this child meets neither.

### Scenario 6b: Child one month younger — Eligible, $11,365
**What we're checking**: the other side of the same boundary.
**Expected**: Eligible — $11,365 (215-hour block; $4.81 × 215 = $1,034.15; − $87 FSD for family of 2 in the $2,885.01–$3,066 band = $947.15/month; × 12 = $11,365.80 → $11,365)
**Steps**:
* Location: ZIP `66210`, county `Johnson County`
* Person 1: born March 1994 (age 32), head of household, wages `hourly` $23.00/hr, hours worked 30/week (= $3,001.50/month)
* Person 2: born October 2013 (age 12, 155 months), child, no disability
* Household assets: $2,000
**Why this matters**: paired with 6a, proves the boundary sits at the month rather than a year either side of it. Note this is a two-person household, so the deduction is the family-of-2 $87, not the family-of-3 $89 used in 5a/5b. Also a truncation case.

### Scenario 7: Disabled 15-year-old — Eligible, $6,473
**What we're checking**: the 13–18 extension on the disability branch.
**Expected**: Eligible — $6,473 ($4.81 × 129 = $620.49; − $81 FSD for family of 2 in the $2,705.01–$2,885 band = $539.49/month; × 12 = $6,473.88 → $6,473)
**Steps**:
* Location: ZIP `66210`, county `Johnson County`
* Person 1: born March 1994 (age 32), head of household, wages `hourly` $10.00/hr, hours worked 20/week (= $870.00/month), plus wages `monthly` $2,015.00 (total $2,885.00)
* Person 2: born January 2011 (age 15, 188 months), child, `long_term_disability` true
* Household assets: $2,000
**Why this matters**: kills an unconditional `age < 13`, which would drop every eligible disabled teenager. Also a truncation case.

### Scenario 8: A second adult works 19 hours a week — Ineligible
**What we're checking**: the activity test applies to every adult on the case, and the threshold is 20 rather than something lower.
**Expected**: Ineligible (criterion 3 — Person 2 averages 19 hours a week, one hour below the requirement, with no documented incapacity)
**Steps**:
* Location: ZIP `66210`, county `Johnson County`
* Person 1: born March 1994 (age 32), head of household, wages `hourly` $23.00/hr, hours worked 30/week
* Person 2: born July 1993 (age 33), spouse, wages `hourly` $15.00/hr, hours worked 19/week (= $1,239.75/month)
* Person 3: born January 2022 (age 4, 56 months), child
* Household assets: $2,000
**Why this matters**: this is the scenario that separates the sourced Kansas rule from MFB's existing `il_ccap`, which tests only the head of household. At 19 hours it also pins the threshold to the hour, which a round-number stand-in would not.

### Scenario 8b: A non-working grandparent in the home does not fail the test — Eligible, $13,147
**What we're checking**: the activity test reaches the nuclear-family adults only, so an adult outside that unit is not tested.
**Expected**: Eligible — $13,147 (215-hour block from the head's 30 hrs/week — the grandparent is not on the case, so their absent schedule neither lowers the block nor is tested; centre rate $5.51 × 215 = $1,184.65/month; − $89 FSD for family of 3 = $1,095.65/month; × 12 = $13,147.80 → $13,147)
**Steps**:
* Location: ZIP `66210`, county `Johnson County`
* Person 1: born March 1994 (age 32), head of household, wages `hourly` $23.00/hr, hours worked 30/week (= $3,001.50/month)
* Person 2: born January 2022 (age 4, 56 months), child
* Person 3: born June 1958 (age 68), `grandParent`, no income, no disability
* Household assets: $2,000
**Why this matters**: paired with Scenario 8, this pins *which* adults the test reaches. Person 3 is not the child's primary caretaker and not the head's spouse or partner, so KEESM 4410 does not put them on the case and neither half of the Maintain Employment test applies to them. An implementation that iterates every adult on the screen returns Ineligible here and denies a household Kansas approves — the mirror image of `il_ccap`'s head-only error that Scenario 8 kills. Person 3 still counts toward family size, which is why the deduction is the family-of-3 $89 and the value matches Scenario 1 exactly.

### Scenario 8c: A disabled adult under 20 hours is excused — Eligible, $5,997
**What we're checking**: the sourced incapacity exemption from the 20-hour requirement, which criterion 3 commits to on the disability booleans.
**Expected**: Eligible — $5,997 (countable income $4,241.25, family of 3 in the $4,212.01–$6,719 band → $211 FSD; centre rate $5.51 for 56 months in Group #1 × 129 = $710.79/month; − $211 = $499.79/month; × 12 = $5,997.48 → $5,997)
**Steps**:
* Location: ZIP `66210`, county `Johnson County`
* Person 1: born March 1994 (age 32), head of household, wages `hourly` $23.00/hr, hours worked 30/week (= $3,001.50/month)
* Person 2: born July 1993 (age 33), spouse, wages `hourly` $15.00/hr, hours worked 19/week (= $1,239.75/month), `long_term_disability` true
* Person 3: born January 2022 (age 4, 56 months), child
* Household assets: $2,000
**Why this matters**: this is Scenario 8 with the 19-hour spouse made disabled, and it is the only scenario that reaches the exemption — the two other disability-flagged adults, in Scenarios 18 and 18b, both work 20 hours independently. An implementation that applies the 20-hour test unconditionally returns Ineligible and denies a household Kansas approves, and without this scenario nothing in the set catches it. Deliberately unconfounded: the spouse earns $15.00/hr so the wage floor stays clear, and the wage floor carries no incapacity exception of its own; assets and income both sit inside their limits. The $5,997 figure coincides with Scenario 18's first counterfactual — different households, both correct, not a copy.

### Scenario 8d: A spouse with no employment at all — Ineligible
**What we're checking**: a tested adult holding no earned-income stream is not employed, which is a failure rather than an unevaluable case.
**Expected**: Ineligible (criterion 3 — Person 2 holds no `wages` or `selfEmployment` income stream, so they are not employed an average of 20 hours a week, and they have no documented incapacity)
**Steps**:
* Location: ZIP `66210`, county `Johnson County`
* Person 1: born March 1994 (age 32), head of household, wages `hourly` $23.00/hr, hours worked 30/week (= $3,001.50/month)
* Person 2: born July 1993 (age 33), spouse, no income, no disability
* Person 3: born January 2022 (age 4, 56 months), child
* Household assets: $2,000
**Why this matters**: this is the branch Data Gap 6 does not reach. An implementation that sums `hours_worked` over an empty set of hourly streams and treats the result as unevaluable — the same fall-open Data Gap 6 directs for a salaried earner — returns Eligible at $7,461, approving the household KEESM 2810 names as ineligible outright: one parent employed, the other not, the non-employed parent expected to provide the care. Pair it with Scenario 8b, where an adult with the same absence of income is a `grandParent` outside the nuclear family and correctly not tested at all; the two together pin that the branch turns on the unit, not on the income. Deliberately unconfounded: income sits under the ceiling, assets under the limit, and Person 3 is an eligible child.

### Scenario 9: Hourly wage one cent below the federal minimum — Ineligible
**What we're checking**: the earnings floor is a separate test from the hours floor.
**Expected**: Ineligible (criterion 3 — $7.24/hour is below the federal minimum wage of $7.25, even though hours worked is 30/week)
**Steps**:
* Location: ZIP `66210`, county `Johnson County`
* Person 1: born March 1994 (age 32), head of household, wages `hourly` $7.24/hr, hours worked 30/week (= $944.82/month)
* Person 2: born January 2022 (age 4, 56 months), child
* Household assets: $2,000
**Why this matters**: kills an implementation that checks hours only — the exact failure MFB's `TotalHoursWorkedDependency` would hide, since its imputation makes every non-hourly wage $7.25 by construction.

### Scenario 9b: Wage exactly at the federal minimum, income below 100% FPL — Eligible, $7,445
**What we're checking**: two rules at once — the wage floor is inclusive at $7.25, and the F-1 `$0` deduction band below 100% FPL.
**Expected**: Eligible — $7,445 ($4.81 × 129 = $620.49; − $0 FSD for family of 2 in the $0–$1,803 band = $620.49/month; × 12 = $7,445.88 → $7,445)
**Steps**:
* Location: ZIP `66210`, county `Johnson County`
* Person 1: born March 1994 (age 32), head of household, wages `hourly` $7.25/hr, hours worked 20/week (= $630.75/month)
* Person 2: born September 2021 (age 5, 60 months), child
* Household assets: $2,000
**Why this matters**: paired with 9, pins the wage floor to the cent — a strict `> 7.25` would deny this household. It is also the only scenario in the $0 deduction band: an implementation that omits F-1's `$0–$1,803 → $0` row and falls through to the 110% row would charge this family $54 a month it does not owe.

### Scenario 9c: Two hourly jobs, one below the floor — Eligible, $13,495
**What we're checking**: the wage floor is the adult's average hourly wage across their hourly streams, not a test of each stream on its own.
**Expected**: Eligible — $13,495 (average wage ($12.00 × 20 + $6.00 × 10) ÷ 30 = $10.00/hour, above the floor; the same 30 summed hours give 130.5 hours needed → 215-hour block; countable income $2,005.00, family of 2 in the $1,984.01–$2,164 band → $60 FSD; $1,184.65 − $60 = $1,124.65/month; × 12 = $13,495.80 → $13,495)
**Steps**:
* Location: ZIP `66210`, county `Johnson County`
* Person 1: born March 1994 (age 32), head of household, wages `hourly` $12.00/hr, hours worked 20/week (= $1,044.00/month), plus wages `hourly` $6.00/hr, hours worked 10/week (= $261.00/month), plus wages `monthly` $700.00 (total $2,005.00)
* Person 2: born January 2022 (age 4, 56 months), child
* Household assets: $2,000
**Why this matters**: the second job pays $6.00/hour, below the federal minimum. An implementation that tests each hourly stream separately returns Ineligible and denies a household whose employment as a whole pays $10.00 an hour, which no captured source directs. It also pins that the hours and the wage are read on the same aggregate: hours are summed to 30, so the wage must be the weighted average over those same 30 hours. Scenarios 9 and 9b keep their bite because each has a single stream, where the average is exactly the stream's rate.

### Scenario 10: A 16-year-old's wages are exempt — Eligible, $7,545
**What we're checking**: KEESM 6410's child-earnings exemption, which a plain `calc_gross_income` call violates.
**Expected**: Eligible — $7,545 (countable income $2,960.00, the teenager's $1,200.00 excluded → $82 FSD for family of 3 in the $2,732.01–$2,960 band; $710.79 − $82 = $628.79/month; × 12 = $7,545.48 → $7,545)
**Steps**:
* Location: ZIP `66210`, county `Johnson County`
* Person 1: born March 1994 (age 32), head of household, wages `hourly` $10.00/hr, hours worked 20/week (= $870.00/month), plus wages `monthly` $2,090.00
* Person 2: born January 2022 (age 4, 56 months), child
* Person 3: born May 2010 (age 16), child, wages `monthly` $1,200.00
* Household assets: $2,000
**Why this matters**: kills the default `calc_gross_income` call, which sums every stream regardless of the earner's age. Counting the teenager's wages would give $4,160.00, the $123 deduction band, and $7,053 — a $492/year error on top of a wrong band.

### Scenario 11: Resources one cent over the limit — Ineligible
**What we're checking**: the $10,000 resource ceiling.
**Expected**: Ineligible (criterion 5 — household assets of $10,000.01 exceed the $10,000 limit, and no exemption applies)
**Steps**:
* Location: ZIP `66210`, county `Johnson County`
* Person 1: born March 1994 (age 32), head of household, wages `hourly` $23.00/hr, hours worked 30/week (= $3,001.50/month)
* Person 2: born January 2022 (age 4, 56 months), child
* Household assets: $10,000.01
**Why this matters**: paired with Scenario 1's exactly-$10,000 pass, pins the limit to the cent. Also kills a limit set at the federal CCDF $1,000,000 figure, the value MFB's `il_ccap` uses.

### Scenario 12: TANF household above the income ceiling — Eligible, $14,215
**What we're checking**: TANF receipt waives the income test, bypasses the resource limit, and zeroes the family share deduction.
**Expected**: Eligible — $14,215 (215-hour block; $1,184.65 − $0 FSD = $1,184.65/month; × 12 = $14,215.80 → $14,215), despite monthly income of $7,001.50 exceeding the family-of-3 limit of $6,719 and assets above $10,000
**Steps**:
* Location: ZIP `66210`, county `Johnson County`
* Person 1: born March 1994 (age 32), head of household, wages `hourly` $23.00/hr, hours worked 30/week (= $3,001.50/month), plus wages `monthly` $4,000.00
* Person 2: born January 2022 (age 4, 56 months), child
* Person 3: born May 2010 (age 16), child, no income, no disability
* Household assets: $12,000
* Current benefits: TANF
**Why this matters**: kills all three TANF branches at once. The income is deliberately above the ceiling so that removing the income waiver flips the verdict — without that, the waiver would have no coverage anywhere in the set.

### Scenario 13: Three eligible children at three age bands — one FSD, not three — Eligible, $25,975
**What we're checking**: the rate is per child while the deduction is per household, across three different age bands including two band edges.
**Expected**: Eligible — $25,975 (rates $7.33 for 11 months + $6.25 for 35 months + $5.51 for 56 months = $19.09/hour; × 129 = $2,462.61/month; − $298 FSD for family of 5 in the $5,963.01–$9,278 band = $2,164.61/month; × 12 = $25,975.32 → $25,975)
**Steps**:
* Location: ZIP `66210`, county `Johnson County`
* Person 1: born March 1994 (age 32), head of household, wages `hourly` $10.00/hr, hours worked 20/week (= $870.00/month), plus wages `monthly` $5,000.00
* Person 2: born July 1993 (age 33), spouse, wages `hourly` $12.00/hr, hours worked 25/week (= $1,305.00/month)
* Person 3: born October 2025 (age 0, 11 months), child
* Person 4: born October 2023 (age 2, 35 months), child
* Person 5: born January 2022 (age 4, 56 months), child
* Household assets: $2,000
**Why this matters**: kills a per-child FSD deduction, which would subtract $894 instead of $298 and understate by $7,152/year. The two younger children sit on the 11/12 and 35/36 month band edges, so a slip at either edge changes the figure by $1,671.84 or $1,145.52 a year.

### Scenario 14: A grandchild and a niece both count — Eligible, $15,906
**What we're checking**: the eligible-child set is KEESM 4410's catch-all set, not `il_ccap`'s six.
**Expected**: Eligible — $15,906 (two eligible children at $5.51 × 129 = $710.79/month each = $1,421.58/month; − $96 FSD for family of 3 in the $3,187.01–$3,415 band = $1,325.58/month; × 12 = $15,906.96 → $15,906)
**Steps**:
* Location: ZIP `66210`, county `Johnson County`
* Person 1: born March 1994 (age 32), head of household, wages `hourly` $10.00/hr, hours worked 20/week (= $870.00/month), plus wages `monthly` $2,545.00 (total $3,415.00)
* Person 2: born January 2022 (age 4, 56 months), `grandChild`
* Person 3: born January 2022 (age 4, 56 months), `relatedOther`, no income
* Household assets: $2,000
**Why this matters**: two mutations die here, and neither child is the head's own, so both are admitted through KEESM 4410's catch-all rather than its biological-or-adopted limb. Shipping `il_ccap`'s six-value set — the likeliest implementation, since this calculator's sibling sits in the same directory — drops Person 3 and returns $7,377, understating by $8,529/year; where a `relatedOther` is the *only* child in care the same bug returns Ineligible outright. Narrowing the set to `child` alone finds no eligible child and returns Ineligible. Both children count toward family size either way, so the deduction band is unaffected and the mutations are isolated to the numerator. Both are counted under Data Gap 16's assumption that an adult on the case primary-caretakes them, which MFB cannot observe for `grandChild` and `relatedOther` alike.

### Scenario 15: The deduction exceeds the gross benefit — Eligible, $1
**What we're checking**: both halves of the value floor — the policy clamp at `$0` and the outer visibility floor at `$1`.
**Expected**: Eligible — $1 (Group #3 rate $3.16 for 90 months × 129 = $407.64/month gross; the $430 FSD for family of 8 in the $8,590.01–$11,038 band exceeds it, so the policy clamp floors the monthly value at $0; × 12 = $0; the outer visibility floor then returns $1)
**Steps**:
* Location: ZIP `67156`, county `Cowley County`
* Person 1: born March 1994 (age 32), head of household, wages `hourly` $50.00/hr, hours worked 20/week (= $4,350.00/month)
* Person 2: born July 1993 (age 33), spouse, wages `hourly` $50.00/hr, hours worked 20/week (= $4,350.00/month — household total $8,700.00)
* Person 3: born March 2019 (age 7, 90 months), child
* Person 4: born May 2009 (age 17), child, no disability
* Person 5: born May 2010 (age 16), child, no disability
* Person 6: born May 2011 (age 15), child, no disability
* Person 7: born May 2012 (age 14), child, no disability
* Person 8: born May 2013 (age 13), child, no disability
* Household assets: $5,000
**Why this matters**: kills three separate mistakes. An unclamped subtraction returns a negative annual value of −$268.32 and displays as a negative benefit. Clamping at `$0` without the outer floor is worse than it looks: the household is eligible on every criterion, and Kansas genuinely pays it nothing under this spec's pinned provider assumption, but a `$0` value is dropped from the results page by `filterPrograms.ts`'s strict `programValue > 0`, so the family would see no card at all rather than an eligible one worth nothing. Returning `$12` instead of `$1` would mean the floor had been applied per month rather than once to the annual figure.
**Why this household**: the clamp is reachable only on the **129-hour block** — at 215 hours the smallest gross this program can produce is $2.42 × 215 = $520.30, above every deduction F-1 publishes. So both adults work exactly 20 hours, the criterion 3 minimum, which keeps the block part-time, and earn $50.00/hour so the household still reaches family-of-8's top band, the only band whose $430 deduction can exceed the benefit. Family size 8 is the only size at which it fires: at size 7 the top deduction is $386 against $407.64 of gross, and sizes above 8 cannot be entered. Deriving the block rather than pinning it therefore narrows this scenario's reachable population sharply, and that narrowing is the point of stating the household this precisely.

### Scenario 16: The deduction band whose F-1 bound carries a source typo — Eligible, $7,137
**What we're checking**: the resolution of Appendix F-1's family-of-3 180% bound, printed as `$3,870.10` where the ascending sequence implies `$3,870.01`.
**Expected**: Eligible — $7,137 ($710.79 − $116 FSD for family of 3 in the $3,870.01–$4,098 band = $594.79/month; × 12 = $7,137.48 → $7,137)
**Steps**:
* Location: ZIP `66210`, county `Johnson County`
* Person 1: born March 1994 (age 32), head of household, wages `hourly` $10.00/hr, hours worked 20/week (= $870.00/month), plus wages `monthly` $3,000.05 (total $3,870.05)
* Person 2: born January 2022 (age 4, 56 months), child
* Person 3: born May 2010 (age 16), child, no income, no disability
* Household assets: $2,000
**Why this matters**: $3,870.05 falls inside the gap a literal transcription of the PDF would leave unmapped ($3,870.01–$3,870.09). A table built from the printed text rather than the sequence-implied bound would find no band for this household.

### Scenario 17: Assets not provided — Eligible, $13,147
**What we're checking**: the nullable-`household_assets` guard falls open.
**Expected**: Eligible — $13,147 (criterion 5 is not applied when `household_assets` is null; value as Scenario 1)
**Steps**:
* Location: ZIP `66210`, county `Johnson County`
* Person 1: born March 1994 (age 32), head of household, wages `hourly` $23.00/hr, hours worked 30/week (= $3,001.50/month)
* Person 2: born January 2022 (age 4, 56 months), child
* Person 3: born May 2010 (age 16), child, no income, no disability
* Household assets: not provided
**Why this matters**: this is Scenario 1 with the asset figure omitted, isolating the guard. Kills both a null-as-failure reading, which would deny a household that simply skipped the question, and a crash on `None`.

### Scenario 18: An SSI parent's wages are exempt too — Eligible, $7,629
**What we're checking**: KEESM 6410 exempts the income of an SSI *recipient*, not merely the SSI payment, so the head's wages leave countable income as well.
**Expected**: Eligible — $7,629 (countable income $2,610.00 — the spouse's wages only, the head's $967.00 SSI and $870.00 of wages both excluded → $75 FSD for family of 3 in the $2,504.01–$2,732 band; $710.79 − $75 = $635.79/month; × 12 = $7,629.48 → $7,629)
**Steps**:
* Location: ZIP `66210`, county `Johnson County`
* Person 1: born March 1994 (age 32), head of household, `disabled` true, income `sSI` `monthly` $967.00, plus wages `hourly` $10.00/hr, hours worked 20/week (= $870.00/month)
* Person 2: born July 1993 (age 33), spouse, wages `hourly` $20.00/hr, hours worked 30/week (= $2,610.00/month)
* Person 3: born January 2022 (age 4, 56 months), child
* Household assets: $2,000
**Why this matters**: counting the head's income gives $4,447.00, the $211 deduction band and $5,997 — a $1,632/year error. Exempting only the `sSI` stream and keeping the head's wages gives $3,480.00, the $102 band and $7,305, so this also kills the narrow reading of the exemption. The head's `disabled` flag is not load-bearing: they independently work 20 hours at above the wage floor.

### Scenario 18b: The SSI recipient is the parent, not the child — Ineligible
**What we're checking**: the resource exemption turns on the *children* receiving SSI, so an SSI parent does not waive the $10,000 limit.
**Expected**: Ineligible (criterion 5 — household assets of $15,000 exceed the $10,000 limit; no member of criterion 1's eligible-child set holds an `sSI` stream, so the KEESM 5140 SSI exemption does not apply, and the household receives no TANF)
**Steps**:
* Location: ZIP `66210`, county `Johnson County`
* Person 1: born March 1994 (age 32), head of household, `disabled` true, income `sSI` `monthly` $967.00, plus wages `hourly` $10.00/hr, hours worked 20/week (= $870.00/month)
* Person 2: born July 1993 (age 33), spouse, wages `hourly` $20.00/hr, hours worked 30/week (= $2,610.00/month)
* Person 3: born January 2022 (age 4, 56 months), child
* Household assets: $15,000
**Why this matters**: this is Scenario 18 with the assets raised over the limit, and it kills a household-level `has_base_benefit("ssi")` reading of the exemption. That flag is true here — `_derived_current_benefit_names` sets it from the head's `sSI` stream alone — so the household-level reading would waive the resource limit and return Eligible at $7,629. Paired with Scenario 20, it pins the exemption to the eligible child.

### Scenario 19: TANF household under both the hours and the wage floor — Eligible, $6,393
**What we're checking**: TANF Child Care carries no 20-hour requirement and no minimum-wage floor, so criterion 3 is met through that pathway rather than the Maintain Employment test.
**Expected**: Eligible — $6,393 (centre rate $4.13 for 56 months in Group #2 × 129 = $532.77/month; − $0 FSD for a TANF household = $532.77/month; × 12 = $6,393.24 → $6,393)
**Steps**:
* Location: ZIP `67202`, county `Sedgwick County`
* Person 1: born March 1994 (age 32), head of household, wages `hourly` $7.00/hr, hours worked 10/week (= $304.50/month), no disability
* Person 2: born January 2022 (age 4, 56 months), child
* Household assets: $2,000
* Current benefits: TANF
**Why this matters**: the head fails both halves of the Maintain Employment test — 10 hours against the 20-hour requirement, $7.00 against the $7.25 floor — and Kansas applies neither to a TANF case. An implementation that reads criterion 3 as unconditional, or that bypasses only the hours half as an earlier draft of this spec did, returns Ineligible and denies the household outright. Deliberately unconfounded: assets sit under the limit and income under the ceiling, so nothing but the activity test can flip it. This is not the family-share-waiver test — at $304.50 for a family of 2 the deduction is $0 by the F-1 band as well as by the waiver; Scenario 12 is where the waiver bites.

### Scenario 20: The only eligible child receives SSI — Eligible, $7,689
**What we're checking**: the KEESM 5140 SSI branch of criterion 5, and that the child's SSI is not countable income.
**Expected**: Eligible — $7,689 (countable income $2,370.00, the child's $967.00 SSI excluded → $70 FSD for family of 2 in the $2,344.01–$2,525 band; $710.79 − $70 = $640.79/month; × 12 = $7,689.48 → $7,689), despite household assets of $15,000
**Steps**:
* Location: ZIP `66210`, county `Johnson County`
* Person 1: born March 1994 (age 32), head of household, wages `hourly` $10.00/hr, hours worked 20/week (= $870.00/month), plus wages `monthly` $1,500.00 (total $2,370.00)
* Person 2: born January 2022 (age 4, 56 months), child, income `sSI` `monthly` $967.00
* Household assets: $15,000
**Why this matters**: an implementation that applies the $10,000 resource limit unconditionally returns Ineligible and drops a household Kansas exempts outright. Counting the child's SSI as income instead would give $3,337.00, which lands in the top 85% SMI band at $167 and yields $6,525 — so one household kills both halves of the SSI treatment.

---

## Research Sources

| Snapshot | Tier | Fidelity | Title | URL | Retrieved |
|---|---|---|---|---|---|
| `2026-09-02--keesm-2140-citizenship-alien-status` | 2 | raw | KEESM 2140 — Citizenship and Alien Status (child care) | https://content.dcf.ks.gov/ees/keesm/Current/keesm2140.htm | 2026-09-02 |
| `2026-09-02--keesm-2810-child-care-general` | 2 | raw | KEESM 2810 — Child Care General Requirements (incl. 2820 personal need) | https://content.dcf.ks.gov/ees/keesm/Current/keesm2810.htm | 2026-09-02 |
| `2026-09-02--keesm-2830-child-care-tanf-nontanf` | 2 | raw | KEESM 2830 — Child Care for TANF and Non-TANF | https://content.dcf.ks.gov/ees/keesm/Current/keesm2830.htm | 2026-09-02 |
| `2026-09-02--keesm-2835-income-eligible-child-care` | 2 | raw | KEESM 2835 — Income Eligible (Non-TANF) Child Care | https://content.dcf.ks.gov/ees/keesm/Current/keesm2835.htm | 2026-09-02 |
| `2026-09-02--keesm-2840-child-care-service-priorities` | 2 | raw | KEESM 2840 — Child Care Service Priorities | https://content.dcf.ks.gov/ees/keesm/Current/keesm2840.htm | 2026-09-02 |
| `2026-09-02--keesm-4400-assistance-unit` | 2 | raw | KEESM 4400 — Assistance Planning for the Child Care Program (incl. 4410, 4420) | https://content.dcf.ks.gov/ees/keesm/Current/keesm4400.htm | 2026-09-02 |
| `2026-09-02--keesm-5000-resources` | 2 | raw | KEESM 5000 — Resources (incl. 5140) | https://content.dcf.ks.gov/ees/keesm/Current/keesm5000.htm | 2026-09-02 |
| `2026-09-02--keesm-6200-income-general` | 2 | raw | KEESM 6200 — Income: General | https://content.dcf.ks.gov/ees/keesm/Current/keesm6200.htm | 2026-09-02 |
| `2026-09-02--keesm-6300-countable-income` | 2 | raw | KEESM 6300 — Countable Income | https://content.dcf.ks.gov/ees/keesm/Current/keesm6300.htm | 2026-09-02 |
| `2026-09-02--keesm-6410-exempt-income` | 2 | raw | KEESM 6410 — Exempt Income | https://content.dcf.ks.gov/ees/keesm/Current/keesm6410.htm | 2026-09-02 |
| `2026-09-02--keesm-6500-income-deductions` | 2 | raw | KEESM 6500 — Income Deductions | https://content.dcf.ks.gov/ees/keesm/Current/keesm6500.htm | 2026-09-02 |
| `2026-09-02--keesm-7400-financial-eligibility` | 2 | raw | KEESM 7400 — Standards for Budgetary Requirements (incl. 7401 proration) | https://content.dcf.ks.gov/ees/keesm/Current/keesm7400.htm | 2026-09-02 |
| `2026-09-02--keesm-7540-child-care-income-eligibility` | 2 | raw | KEESM 7540 — Child Care Income Eligibility (incl. 7541 Family Share Deduction) | https://content.dcf.ks.gov/ees/keesm/Current/keesm7540.htm | 2026-09-02 |
| `2026-09-02--keesm-7600-child-care-plan` | 2 | raw | KEESM 7600 — The Child Care Plan | https://content.dcf.ks.gov/ees/keesm/Current/keesm7600.htm | 2026-09-02 |
| `2026-09-02--keesm-7610-child-care-plan-duration` | 2 | raw | KEESM 7610 — Duration of Child Care Plans (incl. 7620 Determining Scheduled Hours) | https://content.dcf.ks.gov/ees/keesm/Current/keesm7610.htm | 2026-09-02 |
| `2026-09-02--keesm-10200-child-care-payments` | 2 | raw | KEESM 10200 — Child Care Benefits (incl. 10240 DCF Rates) | https://content.dcf.ks.gov/ees/keesm/Current/keesm10200.htm | 2026-09-02 |
| `2026-09-02--keesm-10260-child-care-benefit-computation` | 2 | raw | KEESM 10260 — Special Types of Payments (incl. 10270 in-home relative rate) | https://content.dcf.ks.gov/ees/keesm/Current/keesm10260.htm | 2026-09-02 |
| `2026-09-02--appendix-f-1-income-and-family-share-schedule` | 2 | raw | KEESM Appendix F-1 — Monthly Family Income and Family Share Deduction Schedule (eff. 2026-05-01) | https://content.dcf.ks.gov/ees/KEESM/Appendix/F-1MonthlyFamilyIncomeandFamilyShareDeductionSchedule.pdf | 2026-09-02 |
| `2026-09-02--appendix-c-18-provider-rate-chart` | 2 | raw | KEESM Appendix C-18 — Maximum Hourly Child Care Benefit Rates (eff. 2024-10-01) | https://content.dcf.ks.gov/ees/KEESM/Appendix/C-18_ProviderRateCht.pdf | 2026-09-02 |
| `2026-09-02--appendix-c-18a-provider-rate-county-grouping` | 2 | raw | KEESM Appendix C-18a — Provider Rate Chart by County Grouping | https://content.dcf.ks.gov/ees/KEESM/Appendix/C-18aProviderRateCharByCountyGrouping12-23.pdf | 2026-09-02 |
| `2026-09-02--dcf-memo-2026-05-01-ccfpl-increase` | 2 | raw | DCF Implementation Memo 2026-05-01 — Child Care Poverty Level Increases | https://content.dcf.ks.gov/ees/KEESM/Implem_Memo/2026_05_01_ccfpl_increase.html | 2026-09-02 |
| `2026-09-02--dcf-memo-2021-07-01-250-percent-fpl` | 2 | raw | DCF Implementation Memo 2021-07-01 — Increase to 250 Percent (no FS) | https://content.dcf.ks.gov/ees/KEESM/Implem_Memo/2021_07_01_increaseto250percentnofs.html | 2026-09-02 |
| `2026-09-02--dcf-policy-memo-22-08-02-ending-hero-relief` | 2 | raw | DCF EES Policy Memo 22-08-02 (reissued) — Ending the Hero Relief Program | https://content.dcf.ks.gov/EES/KEESM/Policy_Memo/22-08-02ReissuedPolicyMemoOnEndingHeroRelief.pdf | 2026-09-02 |
| `2026-09-03--dcf-child-care-assistance-program` | 2 | rendered | Kansas DCF — Child Care Assistance Program | https://www.dcf.ks.gov/services/ees/Pages/Child_Care/ChildCareSubsidy.aspx | 2026-09-03 |
| `2026-09-03--dcf-self-service-portal` | 2 | raw | Kansas DCF Self-Service Portal — Apply for Benefits | https://www.dcfapp.kees.ks.gov/ | 2026-09-03 |
| `2026-09-03--dcf-contacts` | 2 | rendered | Kansas DCF — Contacts (navigator phone and email) | https://www.dcf.ks.gov/Pages/contacts.aspx | 2026-09-03 |
| `2026-09-02--45-cfr-98-20-lii` | 1 | raw | 45 CFR 98.20 — A child's eligibility for child care services (federal cross-check) | https://www.law.cornell.edu/cfr/text/45/98.20 | 2026-09-02 |
| `2026-09-02--dol-federal-minimum-wage` | 2 | raw | US DOL Wage and Hour Division — Federal Minimum Wage | https://www.dol.gov/agencies/whd/minimum-wage | 2026-09-02 |
