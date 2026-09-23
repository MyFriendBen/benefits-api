# Child Care Subsidy (MO) — Program Spec

- **Program key**: `mo_ccs` (proposed — `programs/programs/cross_white_label/ccdf/mo.py`, class `MoChildCareSubsidy`, parented on `ProgramCalculator`)
- **Base federal program**: CCDF (Child Care and Development Fund)
- **White label**: MO
- **Engine**: MyFriendBen (MFB) custom
- **Spec lands at**: `programs/programs/cross_white_label/ccdf/specs/mo.md` on implementation — the shipped convention places a spec inside its calculator package, as `ccdf/specs/ks.md` and `aca/specs/mo.md` do
- **Added to MFB**: not implemented
- **Spec last updated**: 2026-09-21
- **Sources verified as of**: 2026-09-21

## Covered Eligibility Criteria

Two routes reach eligibility.

The **ordinary route** requires criteria 1 through 8 below to all hold.

The **Protective Services route** is an alternative eligibility determination made at the time of
application. A child in Children's Division juvenile-court custody, subject to a current adoption
or guardianship subsidy agreement, or with an active family-centered or intensive in-home service
case qualifies without demonstrating financial need, and is not subject to the income maximums
(criterion 7) or the net-worth test (criterion 8). The child's Protective Service status is itself
the valid need, so criterion 5 does not apply either. **Criterion 3 — the child's citizenship —
still applies.** MFB cannot observe Protective Services status, so this route is never asserted;
it is recorded once as Data Gap 1.

- Source: 5 CSR 25-200.060(7)(A) — "The following categories of children are eligible for" — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md), accessed 2026-09-03
- Source: 5 CSR 25-200.060(7)(B) — "These categories of children, or their parent(s), shall not be required to demonstrate a financial need for Child Care Subsidy under this subsection and are not subject to the eligibility unit’s income maximums." — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md), accessed 2026-09-03
- Source: 5 CSR 25-200.060(7)(B) — "The child’s Protective Service status shall be the valid need for child care." — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md), accessed 2026-09-03

1. **The applicant is a Missouri resident, and so is the child**
   - Evaluation scope: `assumed-met`
   - Captured via: residence is located by `zipcode` (Screen, CharField, nullable) and `county` (Screen, CharField, nullable), and the program is scoped to the Missouri white label; **intent to remain** has no screener field
   - Implementation note: `white_label` (Program, ForeignKey) matched against `white_label` (Screen, ForeignKey) scopes the program to the Missouri **site**, not to where the household lives, so residence is assumed met rather than enforced. Residency attaches to the child as well as the applicant.
   - Source: Manual 4.1 — "The applicant shall be a Missouri resident with the intent to remain at the time of application." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: 5 CSR 25-200.060(1)(A) — "(A) Residency of the applicant and the child;" — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md), accessed 2026-09-03

2. **The child resides with a parent who meets the program and financial eligibility requirements**
   - Evaluation scope: `assumed-met`
   - Captured via: nothing — MFB's household model makes members co-resident by construction
   - Source: 5 CSR 25-200.050(15) — "A child who resides with a parent who meets the program and financial eligibility requirements for the particular type of Child Care Subsidy and who—" — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md), accessed 2026-09-03
   - Source: 45 CFR 98.20(a)(3)(i) — "Reside with a parent or parents who are working or attending a job training or educational program; or" — [snapshot `2026-09-03--45-cfr-98-20-lii`](../../../sources/mo/mo_ccs/2026-09-03--45-cfr-98-20-lii/content.md), accessed 2026-09-03

3. **The child who receives the care is a U.S. citizen or a qualified alien — the immigration status of the parent or caretaker is not relevant**
   - Evaluation scope: `config`
   - Captured via: config `legal_status_required` (Program, M2M to `LegalStatus`) — results-display metadata; the screener collects no per-member immigration status
   - Constant: `legal_status_required = ["citizen", "gc_5plus", "gc_5less", "refugee", "otherWithWorkPermission", "non_citizen"]`
   - Implementation note: **the four Qualified Alien statuses cover all seven `.050(32)` limbs.** A *limb* here is one lettered sub-paragraph of a rule; the term is used that way throughout this spec. (A) lawful permanent residence → `gc_5plus` and `gc_5less`; (B) asylum and (C) refugee → `refugee` ("Refugee/Asylee"); (D) parole of at least a year, (E) withheld deportation, (F) pre-1980 conditional entry and (G) Cuban or Haitian entrant → `otherWithWorkPermission` ("Other Lawful"). Nothing in `.050(32)` is unreachable. `citizen` maps to no limb by definition — `.050(32)` defines a Qualified Alien as a person "who is not a citizen or national of the United States" — and carries this criterion's other half, the U.S.-citizen alternative in `.050(15)` and Manual 4.2. `non_citizen` is not a qualifying status; see below.
   - Implementation note: **`gc_5less` belongs in the list and must not be removed as an over-inclusion.** `.050(32)(A)` is unqualified — lawful permanent residence, with no durational condition — and neither the regulation nor the Manual states a five-year bar. Programs that split `gc_5plus` from `gc_5less` normally do so because a federal bar applies to the shorter tenure; no such bar operates here.
   - Implementation note: **`otherWithWorkPermission` reaches substantially wider than the four limbs it carries.** Its label is "Other Lawful" and its tooltip reads "Other lawfully present noncitizens with authorization to live or work in the U.S.", which also selects temporary protected status, U- and T-visa holders, self-petitioners under the Violence Against Women Act (VAWA), derivative-visa dependants and adjustment applicants holding work authorization — **none of which is a Qualified Alien under `.050(32)`**. The widening is deliberate and inclusive, and it is large rather than marginal.
   - Implementation note: **`non_citizen` is included, and must not be removed as an over-inclusion.** The reason is the child-only scope rather than the child's own status: on the merits an undocumented child is neither a U.S. citizen nor a Qualified Alien. But `legal_status_required` is intersected with a **single household-level selection** and no per-member status is collected, so excluding it screens out every household whose *selection* is Undocumented — including the mixed-status household (an adult without status, a citizen child) that Missouri plainly serves and that 45 CFR 98.20(c) protects by forbidding any condition on the parent's status. A filtered-out program shows no card, description or warning at all. `il_ccap` and `ks_ccap` both carry all six statuses.
   - Implementation note: **the residual error is over-inclusion only, and it is the intended direction.** A household selecting Undocumented sees the program whether or not its child holds qualifying status, and the "Other Lawful" width above adds a second over-inclusive population. Both are visible-and-explained rather than silent exclusions; no under-inclusion remains.
   - Implementation note: the rule applies to Protective Services children too. `.050(15)` places citizenship at `(A)(1)`, inside limb (A), while limb (B) is the bare phrase "A protective Services Child" — so the regulation's structure alone would drop it, but the operative Manual and the Child Welfare Manual both apply it to every receiving child.
   - Source: 5 CSR 25-200.050(32) — "“Qualified Alien” means any person who is not a citizen or national of the United States who, at the time such person applies for, receives, or attempts to receive a federal public benefit, is—" — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md), accessed 2026-09-03
   - Source: 5 CSR 25-200.050(32)(A) — "(A) Lawfully admitted for permanent residence under the Immigration and Nationality Act" — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md), accessed 2026-09-03
   - Source: 5 CSR 25-200.050(32)(G) — "(G) A Cuban or Haitian entrant, as defined in section 501(e) of the Refugee Education Assistance Act of 1980" — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md), accessed 2026-09-03
   - Source: 5 CSR 25-200.050(15) — "Is a citizen of the United States of America or a qualified alien; and" — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md), accessed 2026-09-03
   - Source: Manual 4.2 — "Child Care Subsidy shall only be available to the receiving child who must be either a U.S. citizen or a qualified alien. U.S. citizenship or qualified alien status is only required for the child who is the beneficiary of the subsidy benefit." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: MO Child Welfare Manual §3.2.5 — "The child who is the intended child care recipient must be a U.S. citizen or qualified alien as defined in 5 CSR 25-200.050(32)." — [snapshot `2026-09-03--mo-child-welfare-manual-s3c2s5-protective-services-child-care`](../../../sources/mo/mo_ccs/2026-09-03--mo-child-welfare-manual-s3c2s5-protective-services-child-care/content.md), accessed 2026-09-03
   - Source: 45 CFR 98.20(c) — "may not condition a child's eligibility for services under § 98.50 based upon the citizenship or immigration status of their parent" — [snapshot `2026-09-03--45-cfr-98-20-lii`](../../../sources/mo/mo_ccs/2026-09-03--45-cfr-98-20-lii/content.md), accessed 2026-09-03

4. **The child is under 13 — or 13 through 17 with a special need, or 18 but under 19 either in school with a special need or a Protective Services child**
   - Evaluation scope: `member`
   - Captured via: `birth_year_month` (HouseholdMember, DateField) via accessor `calc_age` (HouseholdMember); special-needs status per criterion 5. The **18-but-under-19 band has two limbs and neither is asserted.** Manual 4.5(3) requires the child to be "still in elementary or secondary school" and classified as having a special need; `student` records post-secondary enrollment rather than K-12 attendance, so that condition is unobservable (Data Gap 20). Manual 4.5(4) carries **no school condition at all** — it turns only on Protective Services status — and is blocked instead by Data Gap 1
   - Constant: `BASE_AGE_LIMIT = 13`
   - Implementation note: `calc_age` is month-granular when `birth_year_month` is populated — `age_from_date` returns `today.year - birth.year` when `today.month >= birth.month`, else one less — so the boundary moves on the first of the birth month. The reference date comes from accessor `get_reference_date` (Screen): the screen's earliest validation date once frozen, otherwise the current date, which is what the scenarios' evaluation dates express. When `birth_year_month` is null `calc_age` falls back to `age` (HouseholdMember, PositiveIntegerField, nullable); with both null, treat the member as not an eligible child rather than error.
   - Implementation note: the special-needs age band runs to **under 18** for a non-student, because `.050(11)` caps the status itself there. Only the under-13 limb is fully modelable; the extension limbs depend on the status subset in criterion 5.
   - Source: Manual 4.5 — "Between birth and the day up to the child’s 13 birthday; or" — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: Manual 4.5 — "A child between the age of 13 and 18 and classified as having a special need; or" — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: Manual 4.5 — "A child between the age of 18 but under 19 and a Protective Services child." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: 5 CSR 25-200.050(11) — "means an eligible child who is under the age of eighteen (18), or under age nineteen (19) and still in school, who meets one (1) or more of the following verified criteria:" — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md), accessed 2026-09-03
   - Source: Manual 4.5(4) — "A child between the age of 18 but under 19 and a Protective Services child." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md) (accessed 2026-09-03)
   - Source: Manual 4.5(3) — "A child between the age of 18 but under 19 and still in elementary or secondary school and classified as having a special need;" — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md) (accessed 2026-09-03)
   - Source: 45 CFR 98.20(a)(1)(i) — "Be under 13 years of age; or," — [snapshot `2026-09-03--45-cfr-98-20-lii`](../../../sources/mo/mo_ccs/2026-09-03--45-cfr-98-20-lii/content.md), accessed 2026-09-03

5. **The applicant has a qualifying activity (valid need) — any one of eight pathways**
   - Evaluation scope: `household`
   - Captured via: employment via any earned `IncomeStream` (`category`, `type`, `amount`, `frequency`) on an adult member; education via `student` and `student_full_time` (HouseholdMember, BooleanField); training via `student_job_training_program` (HouseholdMember, BooleanField); applicant incapacitation via accessor `has_disability` (HouseholdMember) on an adult; homelessness not observable (Data Gap 16); the special-need child limb via `has_disability` on the child — its three underlying booleans `disabled`, `long_term_disability` and `visually_impaired` are each nullable, so all three null returns `None` rather than `False`, treated as no status — and the child's own SSI receipt via an `IncomeStream` of `type` `sSI` whose `household_member` is that child
   - Implementation note: **the source scopes valid need to the applicant** — "The applicant shall demonstrate a valid need" — while this mapping accepts a qualifying activity on any adult member. That is a deliberate widening, because MFB does not identify which member is the applicant.
   - Implementation note: **`student_full_time` does not record what its name suggests.** Its question is "Are you enrolled half-time or more in a university, college, or community college as defined by the educational institution?", so a `true` answer covers a half-time student as well as a full-time one. That is immaterial to this criterion, which needs only to know that a member studies — but it is what makes Manual 7.2's and 7.3's full-time/part-time authorization test unmodelable in Benefit Value (Data Gap 14).
   - Implementation note: Missouri's employment rule sets **no minimum-hours threshold and no wage floor for eligibility**. Manual 6.1 requires only paid work verified from the source, with a 90-day gap tolerance. Manual §7.1's 30-hour threshold governs the **amount of care authorized**, not eligibility, and is handled in Benefit Value.
   - Implementation note: the eight pathways are alternatives. **Three are wholly unobservable** — job search (Data Gap 5), homelessness (Data Gap 16) and protective services (Data Gap 1) — and **five only partly**: employment (Data Gap 8), education and training (Data Gap 4), applicant incapacitation (Data Gap 6) and the special-need child limb (Data Gaps 2 and 7). Every unobservable limb is treated inclusively, so **this criterion cannot screen a household out** and no scenario tests a failure of it. Governing principle, applied consistently: a criterion falls open where **every** limb that could satisfy it may be unobservable, and screens out where at least one limb is fully observable — which is why criteria 4 and 6 screen out and this one does not.
   - Implementation note: **special-needs status is defined by regulation and is broader than the valid-need list.** `.050(11)` confers status on six limbs — SSI, services from the Missouri Department of Mental Health (DMH), a verified physical or mental disability or delay, a Protective Service Child, an Adoption Subsidy Child, and a child under court-ordered supervision. Manual 6.7 makes the first three a valid-need pathway; Manual 6.6 makes the Protective Services categories one, including a current adoption or guardianship subsidy agreement. **Court-ordered supervision confers status but no captured source makes it an independent valid-need pathway**, so none is asserted.
   - Implementation note: the modelable status subset is the child's own SSI receipt and a verified disability or delay via
     `has_disability`, which tests `disabled`, `long_term_disability` and `visually_impaired`.
   - Implementation note: **SSI must be read per member, not per household.** `.050(11)(A)` scopes the
     limb to "A child receiving Supplemental Security Income (SSI)", so the signal is an `IncomeStream`
     of `type` `sSI` whose `household_member` is the eligible child — the same per-member route
     criterion 7 uses for the SSI income exclusion. `has_benefit` is a Screen-level accessor and
     cannot identify *which* child receives SSI, so it would confer status on every child in any
     household containing any recipient; and `has_benefit("ssi")` specifically is dead in Missouri,
     which ships the program as `mo_ssi`.
   - Source: Manual §6 — "The applicant shall demonstrate a valid need for child care due to engaging in a qualifying activity." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: Manual §6 — "Applicants with the following household factors shall also meet the qualifying activity (valid need)" — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: Manual 6.1 — "as long as the applicant works without a gap in employment that exceeds 90 calendar days." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: Manual 6.1 — "Employment shall be paid work and verified by DESE from the source." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: 5 CSR 25-200.050(11) — "(D) A Protective Service Child; (E) An Adoption Subsidy Child; or (F) A child under court-ordered supervision." — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md), accessed 2026-09-03

6. **The applicant stands in a qualifying relationship to the child**
   - Evaluation scope: `member`
   - Captured via: `relationship` (HouseholdMember, CharField, nullable), which records each member's relationship to the head of household; a null falls outside the accepted set, so the member is not an eligible child
   - Constant: accepted set `child`, `stepChild`, `fosterChild`, `grandChild`, `sisterOrBrother`, `stepSisterOrBrother`, `relatedOther`
   - Implementation note: this criterion decides **which children are eligible children**, not who is in the Eligibility Unit. A member outside the accepted set is still in the unit under criterion 7's household baseline — they raise unit size and their income counts — they simply cannot be the child for whom care is requested. Scenario 19 turns on exactly that separation.
   - Implementation note: `relatedOther` — "Other relative (aunt, uncle, cousin, in-law, etc.)" — is included because `relationship` is head-relative, so when a caregiver relative heads the household it is the **child** who carries `relatedOther` while the caretaker carries `headOfHousehold`. The caretaker is Manual 4.4(3)'s caregiver relative and `.050(17)(G)`'s Non-Parent Caretaker Relative. Members outside the accepted set count toward Eligibility Unit size but are not eligible children.
   - Implementation note: the source rule is about the **applicant's** relationship to the child, while the field records relationship to the head. The mapping holds when the applicant is the head, which MFB does not verify.
   - Source: Manual 4.4 — "A biological, adoptive, or foster (resource) parent; or" — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: Manual 4.4 — "A caregiver relative; or" — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: 5 CSR 25-200.050(17) — "The Non-Parent Caretaker Relative (NPCR) if no biological or adoptive parent or legal guardian resides in the household; and" — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md), accessed 2026-09-03

7. **The Eligibility Unit's Missouri adjusted gross income does not exceed the lower of the published chart maximum for its size or 85% of the State Median Income**
   - Evaluation scope: `household`
   - Captured via: every `IncomeStream` on the screen at monthly frequency via `monthly()`, less the Missouri exclusions below, less `medical` `Expense` amounts via `monthly()`. `frequency` and `amount` are both nullable and `monthly()` has no fallback branch, so a stream or expense with a null `frequency` cannot be evaluated at all; `Expense.missing_fields()` requires only `type` and `amount`, so a null-frequency `medical` expense can reach this deduction through the API or a legacy row, though never from the screener form, which always submits one. The calculator skips such an expense rather than raising (see Known scenario gaps). Eligibility Unit size is the count of `HouseholdMember` rows after applying the composition rules below, each of which resolves to inclusion, and is **not** read from `household_size` (Screen, IntegerField, nullable), which is collected but never consulted. The two cannot disagree on a completed screen — the member step submits `householdSize: members.length` and the size step slices the roster to the number entered — so deriving unit size from the roster is the same arithmetic by a route that does not depend on that sync holding
   - Constant: chart maximum by Eligibility Unit size — `1 → $1,956`, `2 → $2,644`, `3 → $3,331`, `4 → $4,019`, `5 → $4,706`, `6 → $5,394`, `7 → $6,081`, `8 → $6,769`, `9 → $7,456`, `10 → $8,144`, `11 → $8,831`, `12 → $9,519`, `13 → $10,206`, `14 → $10,894`, `15 → $11,581`, `16 → $12,269`, `17 → $12,956`, `18 → $13,644`, `19 → $14,331`, `20 → $15,019`
   - Constant: 85% State Median Income by size — `1 → $4,023.26`, `2 → $5,261.22`, `3 → $6,499.10`, `4 → $7,737.05`, `5 → $8,975.01`, `6 → $10,212.89`, `7 → $10,445.01`, `8 → $10,677.13`, `9 → $10,909.25`, `10 → $11,141.38`, `11 → $11,373.50`, `12 → $11,605.62`, `13 → $11,837.67`, `14 → $12,069.79`, `15 → $12,301.91`, `16 → $12,534.03`, `17 → $12,766.15`, `18 → $12,998.27`, `19 → $13,230.39`, `20 → $13,462.44`
   - Source: DESE Child Care Eligibility Income Guidelines and Sliding Fee Chart, 85% State Median Income row, sizes 1–4 — "85% State Median Income                 $4,023.26                 $5,261.22                $6,499.10                 $7,737.05" — [snapshot `2026-09-03--dese-income-limits-and-sliding-fee-chart`](../../../sources/mo/mo_ccs/2026-09-03--dese-income-limits-and-sliding-fee-chart/content.md) (accessed 2026-09-03)
   - Implementation note: the operative test is `min(chart maximum, 85% SMI)`. **The chart maximum binds at sizes 1 through 16 and 85% SMI binds at sizes 17 through 20** — at size 17 the SMI figure is `$12,766.15` against a chart maximum of `$12,956` — so implementing either alone would be wrong in one range. **No MFB household reaches that crossover**: the screener caps a household at eight members, and at sizes 1 to 8 the chart maximum is the lower figure, so the 85%-SMI limb never binds and no scenario can pin it. Implement the rule as stated; see Known scenario gaps.
   - Implementation note: **the twenty chart maxima are not arbitrary figures — each is `round(1.5 × FPL(size) ÷ 12)` on the 2025 federal poverty guidelines, exactly, at all twenty sizes**, FPL being the federal poverty level for a household of that size, issued annually by the U.S. Department of Health and Human Services (HHS). The Missouri Department of Elementary and Secondary Education (DESE), which administers the program, states the rule on its family page as "at or below 150% of the federal poverty level" and the superseded manual page 2010.045.00 states it as mandatory, so the chart is the published expression of a 150%-FPL ceiling. **Hard-code the table above; do not derive it from `program.year`** — see `What the calculator returns`, point 8, for why the sibling's derivation reads the wrong guideline year here. The sliding-fee band **floors** are not FPL-derived: they track roughly 8.81% of State Median Income, so the chart mixes two indices and only the ceiling row and the `$5.00` band tops move with the poverty guidelines. `review-notes.md` carries the source conflict and the re-verification trigger.
   - Implementation note: **the two controlling texts scope income differently, and the spec follows the Manual.** `.050(2)` defines adjusted gross income against **the applicant's** gross income, while the incorporated Manual §5 measures "total income received by members of the eligibility unit". The spec counts unit income: the Manual governs by incorporation under `.060(1)`, and the ceiling it is compared against is itself keyed to unit size. The choice is material — under the applicant-only reading a spouse's or adult child's earnings would not count. Logged as a source conflict in `review-notes.md`.
   - Implementation note: **`calc_gross_income` must not be used unmodified**, for two reasons. Missouri computes an adjusted gross income, so the exclusions below are applied first; and `calc_gross_income` sums every member's streams, while Missouri counts only the income of Eligibility Unit members, so streams belonging to a member outside the unit are excluded too. Where `relationship` is null on a member, that member cannot be placed in or out of the unit; the committed handling is to include them, the broader reading, consistent with limbs (E) and (F).
   - Implementation note: **Missouri exclusions MFB can identify and apply.** SSI payments are excluded, identified by `IncomeStream` `type` `sSI`. The earnings of a child under 18 who is attending school are excluded; MFB identifies the age half from `birth_year_month` via `calc_age` but **not** the school half, because `student` and `student_full_time` ask about post-secondary enrollment, so a child in K-12 does not set them and a false value does not disprove attendance. School attendance is therefore **imputed from age alone** — every child under 18 is treated as attending — which is the inclusive direction, since excluding the earnings raises eligibility. Missouri's own sibling calculator takes the same position (Data Gap 20).
   - Implementation note: **the deduction is a defined list, and MFB maps all of it through one field.** Manual 5.7 allows seven items — hospital/physician insurance, MO HealthNet premiums, dental/vision insurance, Medicare supplement policies, cancer insurance, **nursing care** (not a premium at all) and other health insurance policies — and expressly disallows five: wage or income replacement, accident, life, disability and burial policies. MFB has one field for the whole list, the `medical` `Expense` type labelled "Medical Insurance Premium &/or Bills", so the full reported amount is deducted. That is deliberately **inclusive**: it may over-deduct, whereas ignoring the deduction would overstate income and falsely exclude eligible households.
   - Implementation note: **no Federal Poverty Level figure is captured in any snapshot.** The `1.5 × FPL` equivalence in the provenance note above is derived against MFB's own FPL table rather than a captured source; the committed constants are the chart maximums themselves, and the operative test remains `min(chart maximum, 85% SMI)`.
   - Implementation note: **Eligibility Unit baseline — the people living in the same household, subject to the sourced composition rules below.** `.050(17)` defines the Eligibility Unit as "people living in the same household, whose needs and income shall be considered … including" limbs (A)–(H). The list is **open**, not closed, so (A)–(H) are **composition rules applied on top of a household baseline**, not an exhaustive universe of members. Reasoning in `review-notes.md` under Resolved interpretations.
   - Implementation note: each composition rule below is applied individually against what `relationship` (HouseholdMember, CharField, nullable) and `calc_age` can establish; any membership fact MFB cannot resolve is an EU-composition gap (Data Gap 9), not a silent inclusion or exclusion.

     | Sourced composition rule | What MFB can establish | Committed treatment |
     |---|---|---|
     | `.050(17)(A)` the child for whom care is requested | the eligible child identified by criteria 4 and 6 | **in the unit** |
     | `.050(17)(B)` the child's parents, read through `.050(28)` | `.050(28)` makes "Parent" cover a biological parent whose rights are intact, a step-parent, an adoptive parent, a legal guardian, a caretaker relative, or a person in loco parentis. `relationship` carries `parent`, `stepParent`, `fosterParent`, `grandParent`, `relatedOther` and — where the child's parent heads the household — `headOfHousehold`, but **no legal-guardian and no in-loco-parentis value** (Data Gap 3). The value set is head-relative, so it identifies who *could* be a parent, never whose parent they are | **in the unit** on the baseline. `.050(28)` decides who counts as a *parent* for rule (C); it neither admits nor removes members. Rule (G) is **not** governed by it — (G) carries its own narrower list, "no biological or adoptive parent or legal guardian", which excludes the step-parent, caretaker-relative and in-loco-parentis limbs `.050(28)` covers |
     | `.050(17)(C)` the child's parent's spouse | `spouse` records a spouse **of the head**, not of an identified parent. Where the head is a parent of the eligible child the two coincide; where the head is not, no parentage link is recorded | **in the unit** on the baseline either way; the parent-scoping condition is unresolvable and is part of Data Gap 9 |
     | `.050(17)(D)` the child's siblings **under eighteen (18)** | the limb names only under-18 siblings. Manual 5.6.3(3) presupposes that some adult children sit outside the unit, but **no captured source states the test** for when they do | **in the unit** — the baseline governs where the exclusion test is unsourced. Logged as an inclusive EU-composition gap; error direction below |
     | `.050(17)(E)` the unmarried parental partner who is the parent of the child's sibling | `domesticPartner` exists, but **no parentage link between members is recorded**, so "parent of the child’s sibling" cannot be tested | **in the unit** on the baseline; the untestable condition is part of Data Gap 9 |
     | `.050(17)(F)` that partner's child under eighteen (18) | same missing parentage link; `calc_age` gives the age test | **in the unit** on the baseline |
     | `.050(17)(G)` the Non-Parent Caretaker Relative, **if no biological or adoptive parent or legal guardian resides in the household** | `grandChild` and `relatedOther` indicate the NPCR household shape; the residence condition cannot be tested. **(G) is an inclusion rule, not an exclusion rule**, so it adds no narrowing branch: under the household baseline the caretaker is already in the unit, and (G) merely names the case in which the enumeration reaches them expressly. Manual 5.6.3(3) differs in kind — it presupposes members *outside* the unit and excludes their earnings, so it is the one text implying non-membership at all. `relationship` is head-relative, so a parent who **is** the head carries `headOfHousehold`, not `parent`; the absence of a `parent`/`stepParent`/`fosterParent` member is therefore satisfied by an ordinary parent-headed household as well as a genuine NPCR one, and a legal guardian has no `relationship` value at all | **in the unit** on the baseline; the approximation is disclosed and the residual is part of Data Gap 9 |
     | `.050(17)(H)` a school-age child who is also a parent **has the option** of being a separate family unit | the screener records no election, and no parentage link identifies a teen parent | **no election modelled — one unit.** A **narrowing** branch, not an inclusive one: the election is the applicant's *option*, exercised only where it helps. A teen parent with no income who could form a separate unit with their own child is instead folded into the larger unit, whose ceiling rises far more slowly than the added income. Logged in Data Gap 9 |
     | Manual 5.5, the military member stationed away | the Manual counts that member's income sent to the unit **but excludes them from household size**. The screener records no deployment or away-station fact | **in the unit** — the exclusion cannot be detected. Widens results: MFB gives the household a larger unit, and so a higher ceiling, than Missouri would |
     | Manual 5.6.3(3), the only explicit Manual statement about EU non-membership | it is an **income** clause — it excludes the earnings of adult children *already* outside the unit — and so states a consequence of non-membership, not a test for it | see rule (D) |

   - Implementation note: on the facts MFB can establish, no composition rule above removes a member, so the committed unit equals the enumerated roster.
   - Implementation note: **the error direction is not uniform.** Including a member raises the size-keyed ceiling *and* adds their income, so for a member with no income inclusion is purely favourable. Two rules narrow instead. Rule (H): not modelling an applicant-exercised option can only cost the household, since Missouri exercises it only when it helps. Rule (D): where Missouri would place an adult child outside the unit and exclude their earnings under Manual 5.6.3(3), MFB counts both, screening out a household Missouri might accept whenever those earnings exceed the ceiling increment between sizes *n* and *n*+1. Neither branch carries a scenario (see Known scenario gaps).
   - Source: 5 CSR 25-200.050(17) — "(D) The child’s biological, step-, half-, or adopted sibling(s) under eighteen (18) years of age;" — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md), accessed 2026-09-03
   - Source: 5 CSR 25-200.050(17) — "(A) The child for whom care is requested;" — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md) (accessed 2026-09-03)
   - Source: 5 CSR 25-200.050(17) — "(B) The child’s parents (whether married or unmarried);" — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md) (accessed 2026-09-03)
   - Source: 5 CSR 25-200.050(17) — "(C) The child’s parent’s spouse;" — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md) (accessed 2026-09-03)
   - Source: 5 CSR 25-200.050(17) — "(E) The unmarried parental partner who is the parent of the child’s sibling;" — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md) (accessed 2026-09-03)
   - Source: 5 CSR 25-200.050(17) — "(F) Thechildundereighteen(18)yearsofageoftheunmarried parental partner;" — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md) (accessed 2026-09-03)
   - Source: MO ACF-118 CCDF State Plan FFY 2025–2027 Amendment #2, §2.2, reproducing 5 CSR 25-200.050(17)(F) — "(F) The child under eighteen (18) years of age of the unmarried parental partner;" — [snapshot `2026-09-03--mo-acf-118-ccdf-state-plan-ffy2025-2027-amendment-2`](../../../sources/mo/mo_ccs/2026-09-03--mo-acf-118-ccdf-state-plan-ffy2025-2027-amendment-2/content.md) (accessed 2026-09-03) (readable rendering; the Secretary of State PDF, which remains the source of record, is spaceless in this passage)
   - Source: 5 CSR 25-200.050(17) — "(H) A school age child, who is also the parent of a child in the same home, has the option of being a separate family unit for purposes of determining eligibility for Child Care Subsidy." — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md) (accessed 2026-09-03)
   - Source: 5 CSR 25-200.050(28) — "“Parent” means a child’s biological parent whose parental rights have not been terminated, a step-parent, an adoptive parent, a legal guardian, a caretaker relative, or other person standing in loco parentis for the child who has applied for Child Care Subsidy." — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md) (accessed 2026-09-03)
   - Source: MO ACF-118 CCDF State Plan FFY 2025–2027 Amendment #2, §2.2 — "The Lead Agency does not define �residing with� exclusively." — [snapshot `2026-09-03--mo-acf-118-ccdf-state-plan-ffy2025-2027-amendment-2`](../../../sources/mo/mo_ccs/2026-09-03--mo-acf-118-ccdf-state-plan-ffy2025-2027-amendment-2/content.md) (accessed 2026-09-03)
   - Source: 5 CSR 25-200.050(17) — "(G) The Non-Parent Caretaker Relative (NPCR) if no biological or adoptive parent or legal guardian resides in the household; and" — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md), accessed 2026-09-03
   - Source: Manual 5.6.3 — "Earnings of adult children of the applicant, specified relative, or guardian not included in the eligibility" — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: Manual 4.7 — "an eligibility unit’s adjusted gross income shall not" — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: Manual 4.7 — "exceed 85% of the state median income for an eligibility unit of the same size at the time of application." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: DESE Child Care Eligibility Income Guidelines and Sliding Fee Chart — "Income eligibility is determined based on income guidelines outlined in chart above not to exceed the max income amount or 85% of the State Median Income whichever is lower." — [snapshot `2026-09-03--dese-income-limits-and-sliding-fee-chart`](../../../sources/mo/mo_ccs/2026-09-03--dese-income-limits-and-sliding-fee-chart/content.md), accessed 2026-09-03
   - Source: 5 CSR 25-200.050(2) — "“Adjusted Gross Income” means the applicant’s gross income less health insurance premiums paid for by household members." — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md), accessed 2026-09-03
   - Source: Manual §5 — "Monthly gross income means the average monthly amount of total income received by members of the eligibility unit before deductions." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md) (accessed 2026-09-03)
   - Source: 5 CSR 25-200.060(1), EMERGENCY AMENDMENT — "Child Care Subsidy Eligibility Policy Manual (Manual), revised [November 2022] May 2026, which is hereby incorporated by reference and made a part of this rule" — [snapshot `2026-09-03--moreg-v51n12-june-2026-emergency-amendment`](../../../sources/mo/mo_ccs/2026-09-03--moreg-v51n12-june-2026-emergency-amendment/content.md) (accessed 2026-09-03) (the bracketed text is the amendment's own strike-through notation; the unamended CSR edition still reads November 2022, so this amendment is the link that makes the May 2026 Manual operative)
   - Source: Manual 5.7 — "(6) Nursing care; and" — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: Manual 5.7 — "The following expenses are not allowable deductions from gross income:" — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: Manual 5.7 — "(3) Life insurance policies;" — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: Manual 5.6.1 — "(14) Supplemental Security Income (SSI) payments; or" — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: Manual 5.6.3 — "Earnings of a child (under 18 years of age) in the household who is attending school are excluded as" — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: 5 CSR 25-200.050(17) — "“Eligibility Unit” means people living in the same household, whose needs and income shall be considered when determining eligibility for Child Care Subsidy, including:" — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md), accessed 2026-09-03
   - Source: Manual 4.3 — "The Eligibility Unit (EU) is considered the people living in the same household, as defined in 5 CSR 25‐200.050." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: 5 CSR 25-200.050(38) — "based on the eligibility unit’s income and household size" — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md) (accessed 2026-09-03)
   - Source: 5 CSR 25-200.060(3)(C)1 — "The sliding scale fee amount is determined by the household size and adjusted gross income." — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md) (accessed 2026-09-03)
   - Source: Manual 9.1 — "It is based on household size and adjusted gross monthly income" — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md) (accessed 2026-09-03)
   - Source: DESE, Child Care Subsidy Information for Families — "Be at or below 150% of the federal poverty level" — [snapshot `2026-09-03--dese-child-care-subsidy-families`](../../../sources/mo/mo_ccs/2026-09-03--dese-child-care-subsidy-families/content.md), accessed 2026-09-03
   - Source: 45 CFR 98.20(a)(2)(i) — "Reside with a family whose income does not exceed 85 percent of the State's median income (SMI), which must be based on the most recent SMI data that is published by the Bureau of the Census, for a family of the same size; and" — [snapshot `2026-09-03--45-cfr-98-20-lii`](../../../sources/mo/mo_ccs/2026-09-03--45-cfr-98-20-lii/content.md), accessed 2026-09-03

8. **The Eligibility Unit's net worth does not exceed $1,000,000**
   - Evaluation scope: `household`
   - Captured via: `household_assets` (Screen, DecimalField), which records **gross** household assets; constant `NET_WORTH_LIMIT = 1_000_000`
   - Implementation note: **this criterion is asymmetric, because MFB cannot compute Missouri's measure.** Missouri's test is net worth — "the value of everything owned minus any debts" — and MFB has no debt or liability input. So `household_assets ≤ $1,000,000` **establishes a pass** (gross assets at or under the limit mean net worth is too), but `household_assets > $1,000,000` **cannot establish a fail**, because debts may bring net worth under the limit. A household is therefore never screened out on this criterion from gross assets alone. See Data Gap 19.
   - Implementation note: `household_assets` is nullable; when null the proposed handling is inclusive — do not screen the household out.
   - Implementation note: this is the federal CCDF figure and it is genuinely Missouri's own limit. Verification is by applicant statement. Applicants with a protective services child are exempt from the policy criterion entirely, independently of the measurement problem above.
   - Source: Manual 4.8 — "net worth (excluding applicants with a protective services child)" — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: Manual 4.8 — "shall not exceed $1,000,000." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: Manual 4.8 — "Net Worth is the value of everything owned minus any debts." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: Manual 4.8 — "The applicant’s statement of net worth shall be accepted as verification of this requirement." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: 45 CFR 98.20(a)(2)(ii) — "Whose family assets do not exceed $1,000,000 (as certified by such family member)" — [snapshot `2026-09-03--45-cfr-98-20-lii`](../../../sources/mo/mo_ccs/2026-09-03--45-cfr-98-20-lii/content.md), accessed 2026-09-03

## Missing Eligibility Criteria (Data Gaps)

Gaps 12 through 15 affect the estimated figure only. Every other gap can change a verdict, and
each states its direction in its `Handling:` line.

1. **Protective Services status — Children's Division custody, an adoption or guardianship subsidy agreement, or an active family-centered or intensive in-home service case**
   - Why: the screener collects no Children's Division involvement field, and two candidate proxies are rejected. `relationship`'s `fosterChild`, labelled "Foster Child / Kinship Care", merges a formal placement with an informal kinship arrangement that may involve no Children's Division case at all. `was_in_foster_care` (HouseholdMember, BooleanField, nullable) is a live collected Missouri input — the base `condition_options` carries a `fosterCare` tile, Missouri overrides only `acute_condition_options`, and the frontend writes the tile straight to this field — but its own model comment reads "Ever in foster care, even briefly", a history fact rather than a current status. `.050(31)`'s first limb is bare foster-care status, but the operative route in `.060(7)(A)` and Manual 6.6 turns on **active** Children's Division involvement — custody, a subsidy agreement, or an open family-centered or intensive in-home service case — which neither field can establish. Both rejections are recorded so a later pass does not adopt them.
   - Handling: **narrows results.** The alternative eligibility route is never asserted, so a Protective Services household above the income ceiling or the net-worth limit is screened out even though Missouri would exempt it, and its mandatory `$0` sliding fee is never applied. Documented rather than described as harmless.
   - Source: Manual 6.6 — "Children in the legal custody of the Department of Social Services, Children’s Division pursuant to an order of the juvenile court; or" — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: MO Child Welfare Manual §3.2.5 — "A child placed through a Temporary Alternative Placement Agreement (TAPA) is eligible for Protective Services Child Care Subsidy" — [snapshot `2026-09-03--mo-child-welfare-manual-s3c2s5-protective-services-child-care`](../../../sources/mo/mo_ccs/2026-09-03--mo-child-welfare-manual-s3c2s5-protective-services-child-care/content.md), accessed 2026-09-03

2. **Four of the six special-needs limbs — Missouri DMH services, Protective Service Child, Adoption Subsidy Child, and court-ordered supervision**
   - Why: the screener has no field for any of the four; only SSI and a verified disability or delay are observable. `fosterChild` and `was_in_foster_care` are the nearby values and both are rejected for the reason given in Data Gap 1 — the Protective Service Child limb turns on a **current** Children's Division relationship, which a household's description of the placement and a history flag each fail to establish.
   - Handling: narrows results — a child holding status on an unobservable limb is treated as an ordinary child, losing the age extension in criterion 4 and the `$0` fee.
   - Source: 5 CSR 25-200.050(11) — "(B) A child receiving services through the Missouri Department of Mental Health;" — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md), accessed 2026-09-03

3. **A legal guardian, and a caretaker standing in loco parentis who is not a relative**
   - Why: `relationship` (HouseholdMember, CharField, nullable) has **no legal-guardian value and no in-loco-parentis value**. Manual 4.4 has four limbs — parent, **legal guardian**, caregiver relative, and other person in loco parentis — and `.050(28)` defines "Parent" to include all three of the latter. `relatedOther` covers the caregiver-relative limb; the other two have no value.
   - Handling: **narrows results.** Criterion 6 screens out a household whose only under-13 member sits outside the accepted set, as Scenario 19 demonstrates, so a child in the care of a legal guardian or a non-relative acting in loco parentis is wrongly excluded. This is the harmful direction and is not correctable from the current vocabulary.
   - Source: Manual 4.4 — "The legal guardian of the child for whom Child Care Subsidy is requested; or" — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: Manual 4.4 — "Other person standing in loco parentis (in the place of the parent)." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03

4. **Whether a member's programme of study qualifies — MFB cannot distinguish an eligible programme from excluded post-graduate study or an unapproved one**
   - Why: the student and training booleans record that a member studies, not whether the programme qualifies. Post-graduate study is expressly excluded, and a HiSET or Adult Education and Literacy (AEL) programme must be pre-approved by DESE — neither of which the booleans distinguish.
   - Handling: widens results — any studying or training adult satisfies the pathway.
   - Source: Manual 6.2 — "Post‐graduate study is not an eligible qualifying activity (valid need) component." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: Manual 6.2, HiSET/AEL — "The HiSET and AEL program shall be pre‐approved by DESE." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03

5. **Job search as a qualifying activity, and its 90-day limit**
   - Why: `needs_job_resources` (Screen, BooleanField) exists but records a request for job-search help rather than the sourced condition of being in a job-search period, and no field records how long or whether it was used in a prior period. It is not adopted as a proxy.
   - Handling: widens results — the pathway is never asserted, and because criterion 5 cannot screen a household out (see its implementation notes), no household is denied for lacking it.
   - Source: Manual §6 — "(4) Job search (90 calendar day maximum);" — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: Manual 6.4 — "A job search period is a qualifying activity (valid need)." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03

6. **Applicant incapacitation — MFB cannot distinguish a professionally verified incapacitation from a self-reported condition**
   - Why: Missouri requires an annual statement from a named class of professional; `has_disability` records a self-reported condition.
   - Handling: widens results — `has_disability` on an adult satisfies the pathway.
   - Source: Manual 6.5 — "Incapacitation/disability of the applicant is a qualifying activity (valid need) as long as a certified physician, psychologist, psychiatrist, licensed clinical social worker, licensed professional counselor, nurse practitioner, or physician’s assistant provides an annual statement verifying the need for care." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03

7. **A child's special need — MFB cannot distinguish a professionally verified condition from a self-reported one**
   - Why: `.050(11)(C)` requires the disability or delay to be "verified in writing by a medical professional or mental health professional", and Manual 6.7.1 requires an **annual statement** from a named class of professional. MFB's `has_disability` records a self-reported condition, and SSI receipt is an income stream, not a clinical statement.
   - Handling: **widens results** — special-needs status fires on self-report, which both extends criterion 4's age limit past 13 and applies the `$0` sliding fee. Scenarios 34 and 36 rest on the self-reported flag.
   - Source: 5 CSR 25-200.050(11) — "(C) A child with a physical or mental disability or delay verified in writing by a medical professional or mental health professional;" — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md), accessed 2026-09-03
   - Source: Manual 6.7.1 — "Special Need of the child is a qualifying activity (valid need) as long as a certified physician, psychologist, psychiatrist, licensed clinical social worker, licensed professional counselor, nurse practitioner, or physician’s assistant provides an annual statement verifying the need for care." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03

8. **Whether a household member is, or works for, a license-exempt "six or fewer" provider contracted with DESE**
   - Why: no screener field records provider-contract status for household members.
   - Handling: widens results — **both** of Manual 6.1's exclusions are never applied: the applicant
     who *is* such a provider (barred from using that employment for their own child) and the applicant
     who *works for* one.
   - Source: Manual 6.1 — "If the applicant is a license‐exempt, six or fewer child care provider contracted with DESE to accept subsidy payment, this employment shall not qualify for purposes of eligibility for the applicant’s own child." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md) (accessed 2026-09-03)
   - Source: Manual 6.1 — "Applicants claiming to work for a six or fewer child care provider contracted with DESE are not eligible to use employment as a qualifying activity (valid need) for care." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03

9. **Eligibility Unit composition facts MFB cannot resolve**
   - Why: the unit's baseline is the household, but `.050(17)`'s composition rules turn on facts the screener does not record. **No parentage link between members exists**, so `.050(17)(C)`'s "The child’s parent’s spouse" cannot be scoped to a parent (`spouse` records a spouse of the head), and `.050(17)(E)`/(F)'s unmarried parental partner cannot be tested for being "the parent of the child's sibling". `.050(17)(G)`'s "no biological or adoptive parent or legal guardian resides in the household" is approximated by the absence of an accepted-parent relationship, a different test — `relationship` has no legal-guardian value (Data Gap 3). `.050(17)(H)`'s school-age-parent **option** has no election mechanism and no way to identify a teen parent. Manual 5.6.3(3) presupposes some adult children sit outside the unit but states no test for when. Manual 5.5 excludes a military member stationed away from household size, and no field records that.
   - Handling: **widens results on unit size** — every unresolved condition resolves to inclusion, so MFB's unit is at least as large as Missouri's and its ceiling at least as high. Two branches can narrow instead, rules (D) and (H); criterion 7's error-direction note states both and is the single home for that analysis.
   - Source: 5 CSR 25-200.050(17) — "(E) The unmarried parental partner who is the parent of the child’s sibling;" — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md) (accessed 2026-09-03)
   - Source: 5 CSR 25-200.050(17) — "(H) A school age child, who is also the parent of a child in the same home, has the option of being a separate family unit for purposes of determining eligibility for Child Care Subsidy." — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md) (accessed 2026-09-03)
   - Source: 5 CSR 25-200.050(17) — "(G) The Non-Parent Caretaker Relative (NPCR) if no biological or adoptive parent or legal guardian resides in the household; and" — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md) (accessed 2026-09-03)
   - Source: Manual 5.5 — "However, the military EU member stationed away from the residence shall not be included in determining household size." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md) (accessed 2026-09-03)
   - Source: Manual 5.5 — "Military income sent to the eligibility unit from an EU member stationed away from the residence of the EU shall be counted as gross monthly income to the EU." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md) (accessed 2026-09-03)
   - Source: Manual 5.6.3 — "Earnings of adult children of the applicant, specified relative, or guardian not included in the eligibility" — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md) (accessed 2026-09-03)

10. **Most of Missouri's income exclusions**
   - Why: Missouri excludes fifteen categories of agency benefit plus resource payments, in-kind income, loans and several others. MFB's income vocabulary identifies only two — SSI, and the earnings of a child under 18 attending school — both applied in criterion 7. Foster-care payments, adoption-subsidy maintenance, Workforce Investment Act and Job Corps allowances, Vocational Rehabilitation payments, energy assistance, veterans' education portions, in-kind income, SNAP value, housing allowances, tax refunds, capital gains and non-recurring lump sums have no distinguishing MFB income type.
   - Handling: **narrows results.** Income Missouri would exclude remains counted, overstating adjusted gross income and screening out households Missouri would accept. This is the harmful direction and cannot be made inclusive, because MFB cannot identify what to exclude. `cashAssistanceOther` ("Cash Assistance - Other") is available on Missouri screens and does **not** narrow this gap: Manual 5.6.1's excluded categories are specific named payment types, and a generic other-cash-aid bucket cannot distinguish an excluded one (an Adoption Subsidy maintenance payment) from a counted one (General Assistance, another state's TANF, local cash aid).
   - Source: Manual 5.6.1 — "(15) Foster Care payments (IV‐E or HDN) are excluded." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: Manual 5.6.4 — "In‐kind income is to be excluded in determining monthly gross income." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03

11. **Which of Manual 5.7's allowable and disallowed items the reported `medical` expense contains**
   - Why: MFB's single field is labelled "Medical Insurance Premium &/or Bills", so the amount may mix Manual 5.7's seven allowable items with non-premium bills and with the five expressly disallowed policy types.
   - Handling: widens results — the full amount is deducted, which may over-deduct. Chosen deliberately, because ignoring the deduction would overstate income and falsely exclude eligible households.
   - Source: 5 CSR 25-200.050(2) — "“Adjusted Gross Income” means the applicant’s gross income less health insurance premiums paid for by household members." — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md), accessed 2026-09-03

12. **The child's functional age**
   - Why: no screener field expresses it; it is a documented clinical determination.
   - Handling: narrows/widens results — no verdict effect; chronological age is the committed proxy and the direction is not uniform. See Benefit Value.
   - Source: MO ACF-118 CCDF State Plan FFY 2025–2027 Amendment #2, §2.3.1 — "Child care rates for children classified as having special needs are paid at the rate of the child" — [snapshot `2026-09-03--mo-acf-118-ccdf-state-plan-ffy2025-2027-amendment-2`](../../../sources/mo/mo_ccs/2026-09-03--mo-acf-118-ccdf-state-plan-ffy2025-2027-amendment-2/content.md), accessed 2026-09-03
   - Source: Manual 9.4 — "Rates paid by DESE are based on the child’s functional age." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md) (accessed 2026-09-03)

13. **The provider type, and whether that provider holds an approved rate differential**
   - Why: neither is collected.
   - Handling: narrows results — no verdict effect; the estimate assumes a Licensed Center with no approved differential, so a household using an approved provider receives more than shown. See Benefit Value.
   - Source: DESE, Child Care Subsidy Payments — "Providers can only receive one of these two rate enhancements." — [snapshot `2026-09-03--dese-child-care-subsidy-payments`](../../../sources/mo/mo_ccs/2026-09-03--dese-child-care-subsidy-payments/content.md), accessed 2026-09-03

14. **The authorized care pattern — hours per day, days per month, and time of week, on every qualifying-activity pathway**
   - Why: the screener collects no care schedule, and **Missouri sets the daily time category by a different rule on each of criterion 5's eight pathways** — Manual 7.1 through 7.8, one per pathway. None of the eight is modelable. **Employment** (7.1) keys on hours worked, which MFB does not reliably populate across employment types, `hours_worked` existing on hourly income streams only. **Education and training** (7.2, 7.3) key on full-time versus part-time student status, which `student_full_time` cannot express — its "half-time or more" question covers Missouri's part-time student as well as its full-time one (criterion 5). **Job search** (6.4, 7.4) is expressly part-time as an initial qualifying activity and needs no missing fact, but the pathway itself is unobservable (Data Gap 5). **Incapacitation, protective services and a child's special need** (7.6, 7.7, 7.8) are each authorized from a professional's or an applicant's statement, and all three are unobservable (Data Gaps 6, 1 and 7). **Homelessness** (7.5) is the eighth — full-time care, or the child's school schedule where the child is school-age — and is unobservable too (Data Gap 16).
   - Handling: narrows/widens results — no verdict effect; Full day, Daytime and 21 days are assumed on every pathway, and across the gap as a whole the direction depends on the household's actual authorization. **On the daily time category alone the direction is one-way**: Full day is Missouri's most generous category, so wherever Missouri would authorize part-time or half-time the estimate is overstated — a job-search applicant and a part-time student or trainee being the named cases. The day count and the time of week keep the mixed direction. See Benefit Value.
   - Source: Manual 7.4 — "An applicant shall be authorized for part‐time daytime authorization for job search when used as the initial qualifying activity and full‐time following the loss of a qualifying activity for 90 days." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: DESE, Child Care Subsidy Payments — "Number of days in the month the child can receive child care subsidy" — [snapshot `2026-09-03--dese-child-care-subsidy-payments`](../../../sources/mo/mo_ccs/2026-09-03--dese-child-care-subsidy-payments/content.md), accessed 2026-09-03
   - Source: DESE, Child Care Subsidy Payments — "The state will not pay for more hours or days of care than stated in the Authorization Letter." — [snapshot `2026-09-03--dese-child-care-subsidy-payments`](../../../sources/mo/mo_ccs/2026-09-03--dese-child-care-subsidy-payments/content.md), accessed 2026-09-03
   - Source: MO ACF-118 CCDF State Plan FFY 2025–2027 Amendment #2, §4.3.3 — "The Lead Agency has a 15% rate differential for evening and weekend care." — [snapshot `2026-09-03--mo-acf-118-ccdf-state-plan-ffy2025-2027-amendment-2`](../../../sources/mo/mo_ccs/2026-09-03--mo-acf-118-ccdf-state-plan-ffy2025-2027-amendment-2/content.md), accessed 2026-09-03

15. **The provider's actual charge for care**
   - Why: Missouri caps payment at the lesser of the state maximum plus differentials or the provider's actual charge, and MFB's `childCare` `Expense` records a household cost rather than a per-child provider rate.
   - Handling: widens results — no verdict effect; the charge is assumed at least the state maximum, so the estimate is too high for a household whose provider charges less.
   - Source: 5 CSR 25-200.060(3)(B) — "for child care services shall not exceed the maximum base rate plus any rate differentials or the actual charges by the child care provider, whichever is less." — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md), accessed 2026-09-03
   - Source: 5 CSR 25-200.060(3)(B) — "Maximum payment by the department for child care services shall not exceed the maximum base rate plus any rate differentials or the actual charges by the child care provider, whichever is less." — [snapshot `2026-09-03--lii-5-csr-25-200-060-quotation-bridge`](../../../sources/mo/mo_ccs/2026-09-03--lii-5-csr-25-200-060-quotation-bridge/content.md), accessed 2026-09-03

16. **Whether the household is experiencing homelessness**
   - Why: Missouri's definition is specific — lacking a fixed, regular and adequate nighttime residence, with shelter, domestic-violence-shelter and community-agency pathways expressly covered. MFB has two candidate fields and neither is executable input on a Missouri screen. `needs_homeless_services` (Screen, BooleanField) expresses a need for homeless services rather than the sourced condition — the same objection that rules out `needs_job_resources` in Data Gap 5. `housing_situation` (Screen, CharField, nullable) is not collected on a Missouri screen at all: it appears in no screener serializer, and Missouri inherits the base step directory, which has no housing step and which Missouri does not override; even if it were collected it records a housing *type*, not Missouri's definition.
   - Handling: **widens results** on eligibility — the pathway is never asserted and no household is screened out for lacking it. The consequences the spec does **not** apply, each retained as sourced policy: the authorization — full-time care, or the child's own school schedule where the child is school-age, Manual 7.5 carrying both (Benefit Value) — the `$0` sliding-fee waiver (Benefit Value), and waitlist priority category 2 (Priority Criteria).
   - Source: Manual 6.8 — "The term homeless is defined as an individual or family who lacks a fixed, regular, and adequate nighttime residence." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03

17. **An unpaid sliding fee, an outstanding debt owed to a contracted provider, or an unresolved child care overpayment, any of which bars eligibility**
   - Why: the screener records no provider debt, no prior-subsidy fee history and no overpayment history. Missouri bars the application on all three: Manual 9.3 and `.060(3)(C)5` on the unpaid fee and provider debt, and Manual 2.7(2) on an unresolved overpayment.
   - Handling: widens results — the bar is never applied, so a household Missouri would reject on this ground is shown as eligible.
   - Source: Manual 9.3 — "An applicant may have a Child Care Subsidy application rejected if the applicant has an outstanding debt owed" — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: 5 CSR 25-200.060(3)(C)5 — "care participants who failed to pay the required sliding scale" — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md), accessed 2026-09-03
   - Source: Manual 2.7 — "The applicant has a child care overpayment and has not agreed to, or is non‐compliant with, a repayment plan in accordance with 5 CSR 25‐200.100 Child Care Provider Overpayments." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md) (accessed 2026-09-03)

18. **Self-employment overhead deductions**
   - Why: Missouri computes self-employment income from the prior year's tax return and allows seven overhead categories to be deducted. MFB records a `selfEmployment` income type but no overhead figures, so criterion 7 counts gross receipts.
   - Handling: **narrows results** — a self-employed household is measured on receipts Missouri would net down, overstating income and screening some out. The harmful direction, and not correctable from screener data.
   - Source: Manual 5.4 — "Self‐employment income is verified through the previous year’s tax return/documentation." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
   - Source: Manual 5.4 — "The previous year’s tax forms may be used to verify self‐employment expenses. The following overhead" — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03

19. **The debts needed to compute Missouri net worth**
   - Why: Missouri's asset test is net worth — everything owned minus debts — and MFB collects only `household_assets`, a gross figure, with no liability input anywhere in the screener.
   - Handling: **widens results.** Gross assets above $1,000,000 cannot establish ineligibility, so criterion 8 never screens a household out; only a pass can be established. Treating gross assets as net worth would falsely exclude households whose debts bring net worth under the limit, which is the error the inclusive default exists to prevent.
   - Source: Manual 4.8 — "Net Worth is the value of everything owned minus any debts." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03

20. **Whether a child is attending K-12 school**
   - Why: `student` and `student_full_time` (HouseholdMember, BooleanField, nullable) record post-secondary enrollment — the field text is "Student at a college, university, or other post-secondary institution like a job-training program" — so a child in K-12 does not set them, and a false value does not disprove attendance. (`student_full_time`'s "half-time or more" wording is a separate limitation, bearing on Benefit Value rather than on this gap; see criterion 5 and Data Gap 14.) Missouri's own sibling calculator records the same limitation about the same flag.
   - Handling: three directions, because the same imputation feeds three rules. **Widens** for the income exclusion, where attendance is imputed from age alone so every under-18 child's earnings are excluded (criterion 7). **Understates the estimate** for the school-age authorization: Manual 7.9's half-day-plus-five-days basis is scoped to "children enrolled in school" while MFB applies it to every child `calc_age` 5 or over inside the window, and a school-age child not actually enrolled would draw Manual 7.1's Full day instead — $651.00 against $518.125 in Region 1. **Narrows** for criterion 4's 18-but-under-19 special-needs limb, which requires "still in school" and is therefore not asserted.
   - Source: 5 CSR 25-200.050(15) — "Is under age nineteen (19) and still in school and classified as having a special need; or" — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md), accessed 2026-09-03
   - Source: Manual 5.6.3 — "Earnings of a child (under 18 years of age) in the household who is attending school are excluded as" — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03

## Priority Criteria

Missouri implemented a waiting list on 2026-03-01. It governs **availability**, not eligibility: an
eligible household may be placed on it rather than served. Position is set by application date and
priority category, in the order below. No committed scenario asserts a priority position.

- Source: DESE, Child Care Subsidy Program Information — "a waitlist was implemented on March 1, 2026, to help maintain program sustainability." — [snapshot `2026-09-03--dese-child-care-subsidy-program-information`](../../../sources/mo/mo_ccs/2026-09-03--dese-child-care-subsidy-program-information/content.md) (accessed 2026-09-03)
- Source: Manual 3.1 — "The position of an application on the waiting list is determined by the date of application submission and priority category." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md) (accessed 2026-09-03)
- Source: Missouri Register Vol. 51 No. 12, EMERGENCY AMENDMENT to 5 CSR 25-200.060(8)(B) — "The department’s waiting list shall utilize a priority ranking system for participants, in the following order:" — [snapshot `2026-09-03--moreg-v51n12-june-2026-emergency-amendment`](../../../sources/mo/mo_ccs/2026-09-03--moreg-v51n12-june-2026-emergency-amendment/content.md) (accessed 2026-09-03)

- Children with special needs as defined in 5 CSR 25-200.050 (CSR being Missouri's Code of State Regulations), except that an adoption subsidy child or a protective service child may not be placed on the waitlist at all — captured: partially, via the child's own `IncomeStream` of `type` `sSI` and accessor `has_disability` (HouseholdMember); the other four status limbs and the adoption-subsidy and protective-service carve-outs are not observable (Data Gaps 1 and 2)
  - Program description tie-back: **done** — the description says Missouri helps some families first and names children with special needs among them. The waiting list itself is carried by the `mo_ccs_waitlist` warning message, which renders above the description on the same page; the description said it too until 2026-09-21, when the duplication was removed
  - Source: Missouri Register Vol. 51 No. 12, EMERGENCY AMENDMENT to 5 CSR 25-200.060(8)(B)1 — "Children with special needs as defined in 5 CSR 25- 200.050, except that an adoption subsidy child and a protective service child may not be placed on the waitlist;" — [snapshot `2026-09-03--moreg-v51n12-june-2026-emergency-amendment`](../../../sources/mo/mo_ccs/2026-09-03--moreg-v51n12-june-2026-emergency-amendment/content.md) (accessed 2026-09-03)
- Children classified as homeless as defined in the McKinney-Vento Homeless Assistance Act — captured: not captured, unmodelable with current screener data (Data Gap 16)
  - Program description tie-back: **done** — the description names homeless families among those Missouri helps first
  - Source: Missouri Register Vol. 51 No. 12, EMERGENCY AMENDMENT to 5 CSR 25-200.060(8)(B)2 — "Children classified as homeless as defined in the McKinney-Vento Homeless Assistance Act;" — [snapshot `2026-09-03--moreg-v51n12-june-2026-emergency-amendment`](../../../sources/mo/mo_ccs/2026-09-03--moreg-v51n12-june-2026-emergency-amendment/content.md) (accessed 2026-09-03)
- Eligibility units with an adjusted gross income under 100% of the Federal Poverty Level — captured: computable but not asserted. Criterion 7 yields Missouri adjusted gross income, and the Federal Poverty Level is available in MFB — `programs/models.py` ships `_FPL_DEFAULTS` for 2023 through 2026 behind `FederalPoveryLimit.get_limit`, and `cross_white_label/ccdf/il.py` already reads it. No figure is asserted here because waitlist position governs **availability**, not qualification, and no scenario claims one
  - Program description tie-back: **done** — the description names families with very low income among those Missouri helps first
  - Source: Missouri Register Vol. 51 No. 12, EMERGENCY AMENDMENT to 5 CSR 25-200.060(8)(B)3 — "Eligibility units with an adjusted gross income under one hundred (100) percent of the Federal Poverty Level;" — [snapshot `2026-09-03--moreg-v51n12-june-2026-emergency-amendment`](../../../sources/mo/mo_ccs/2026-09-03--moreg-v51n12-june-2026-emergency-amendment/content.md) (accessed 2026-09-03)
- Eligibility units with an adjusted gross income of 100% of the Federal Poverty Level or greater — captured: computable but not asserted, for the same reason as the preceding category
  - Program description tie-back: **done**, and carried by the waiting-list warning message rather than by the description: “Your place is set by the date you apply and your priority group.” The warning's `calculator` is `_show`, which resolves to the base `WarningCalculator` in `programs/warnings/base.py` — its `eligible()` returns `True`, its `county_eligible()` returns `True` when no counties are set, and its `dependencies` is an empty tuple — so every household that sees the program sees the sentence. The description alone says only that some families are served sooner than others
  - Source: Missouri Register Vol. 51 No. 12, EMERGENCY AMENDMENT to 5 CSR 25-200.060(8)(B)4 — "Eligibility units with an adjusted gross income of one hundred (100) percent of the Federal Poverty Level or greater." — [snapshot `2026-09-03--moreg-v51n12-june-2026-emergency-amendment`](../../../sources/mo/mo_ccs/2026-09-03--moreg-v51n12-june-2026-emergency-amendment/content.md) (accessed 2026-09-03)

## Related Programs

- **Transitional Child Care** — a Missouri benefit program with its own income bands above the traditional maximum and its own funding percentages, open only to families already receiving the subsidy whose income rises. Own eligibility: continuing receipt of Child Care Subsidy plus income above the traditional maximum, within the published transitional bands. Manual 11.1 states all three levels with their bands and funding percentages — 151–185% of the Federal Poverty Level at 80%, 186–215% at 60%, 216–242% at 50% — and the current chart records Level 3 removed on 2026-07-01, leaving two. Outside the population MFB screens, so it carries no criterion, no value branch and no scenario.
  - Program description tie-back: none needed — the program MFB would surface is the traditional subsidy
  - Source: 5 CSR 25-200.050(41) — "means a benefit program assisting families currently receiving Child Care Subsidy" — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md) (accessed 2026-09-03)
  - Source: DESE Child Care Eligibility Income Guidelines and Sliding Fee Chart — "Note: Transitional Level 3 removed July 1, 2026." — [snapshot `2026-09-03--dese-income-limits-and-sliding-fee-chart`](../../../sources/mo/mo_ccs/2026-09-03--dese-income-limits-and-sliding-fee-chart/content.md) (accessed 2026-09-03)
  - Source: Manual 11.1 — "Income eligibility for Transitional Child Care Level 1 (TCC1) shall be one hundred fifty‐one percent (151%) of the federal poverty level but not to exceed one hundred eighty‐five percent (185%) of the federal poverty level." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md) (accessed 2026-09-03)
  - Source: Manual 11.1 — "DESE shall fund eighty percent (80%) of the remaining state base rate." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md) (accessed 2026-09-03)
- **Missouri Head Start and Early Head Start** (`mo_head_start`, `mo_early_head_start`) — sibling early-childhood programs. Missouri's approved CCDF plan connects **Early Head Start** to this one: subsidy-eligible children qualify for its contracted infant-and-toddler slots. No captured source states a comparable connection for Head Start; it is named here because it shares the `child_care` program category. Own eligibility: each has its own income and age rules, determined separately from this program. Not part of this program's eligibility or value.
  - Program description tie-back: none needed
  - Source: MO ACF-118 CCDF State Plan FFY 2025–2027 Amendment #2, §4.5.1 — "Subsidy eligible children qualify for slots for children participating in Early Head Start." — [snapshot `2026-09-03--mo-acf-118-ccdf-state-plan-ffy2025-2027-amendment-2`](../../../sources/mo/mo_ccs/2026-09-03--mo-acf-118-ccdf-state-plan-ffy2025-2027-amendment-2/content.md) (accessed 2026-09-03)

## Benefit Value

**The contract.** `$N/year per household`, returned as `int(monthly × 12)` — **the calculator returns an annual figure** and MFB's results card divides it by twelve for display. `value_format` is null, the model's Default (Monthly); that label names the display cadence, not the returned units, so the returned value must be annual. See `What the calculator returns`, point 2, for the formatter path and why neither other option works. Both sibling CCDF calculators annualize the same way: `cross_white_label/ccdf/ks.py` returns `int(monthly * 12)` and `cross_white_label/ccdf/il.py` returns `monthly_rate * 12`. Missouri pays on a day-based cycle inside monthly authorizations, so a recurring monthly display is the right presentation. Not a one-time benefit.

**How the value is computed**, in calculation order. Every step below is detailed in the subsection it names; this ladder is the whole procedure, and the subsections exist for when a developer needs the reasoning behind a step.

1. **Geographic grouping** — from the household's county → *Geographic grouping*
2. **Age category** for each eligible child — Infant, Preschool or School age from `calc_age`, then the school-year hold → *Age category and the school-year hold*
3. **Daily time category** — Full day for every household, except a school-age child inside the school year → *The authorized care pattern*
4. **Daily rate** — read the cell for that grouping, age category and time category → *The rates*
5. **Daily sliding fee** — by Eligibility Unit size and Missouri adjusted gross income, applying waiver, then `$1`-per-year, then daily chart, in that fixed order → *The sliding fee*, *Precedence*
6. **Assemble the monthly figure** — Σ over eligible children of `max(0, authorized daily rate − applicable daily sliding fee) × 21`, where a school-age child inside the school year instead contributes `max(0, half-day rate − half-unit fee) × 21 + max(0, full-day rate − full-unit fee) × 5/8`; then, where the annual band governs, the gross rate sum less `$1 ÷ 12` once per household — exactly Missouri's `$1` a year on annualization. Annualize as `int(monthly × 12)` → *The fixed proxy assumptions*, *What the calculator returns*

- Variation axes: geographic grouping | child age category | school-year hold | daily time category | Eligibility Unit size × Missouri adjusted gross income (sliding-fee band) | sliding-fee waiver status — each axis appears in Test Scenarios
- Source: 5 CSR 25-200.060(3)(B) — "for child care services shall not exceed the maximum base rate plus any rate differentials or the actual charges by the child care provider, whichever is less." — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md), accessed 2026-09-03
- Source: 5 CSR 25-200.060(3)(B) — "Maximum payment by the department for child care services shall not exceed the maximum base rate plus any rate differentials or the actual charges by the child care provider, whichever is less." — [snapshot `2026-09-03--lii-5-csr-25-200-060-quotation-bridge`](../../../sources/mo/mo_ccs/2026-09-03--lii-5-csr-25-200-060-quotation-bridge/content.md), accessed 2026-09-03
- Source: 5 CSR 25-200.060(3)(C)2 — "The maximum child care subsidy payment shall be the maximum base rate minus the applicable sliding scale fee amount, if any." — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md), accessed 2026-09-03
- Source: DESE, Child Care Subsidy Rates and Sliding Fees — "provider payments will be calculated as follows: the state base rate plus any differential pay minus the sliding fee amount." — [snapshot `2026-09-03--dese-child-care-subsidy-rates-and-sliding-fees`](../../../sources/mo/mo_ccs/2026-09-03--dese-child-care-subsidy-rates-and-sliding-fees/content.md), accessed 2026-09-03
- Justification: Missouri pays a per-child daily rate to the provider, set by geographic grouping, provider type, the child's age category and the daily time category, and subtracts the family's sliding fee from the base rate. Grouping and age category are derivable from screener data and are modelled; provider type, the care pattern and provider differential approval are not collected, so each is held at one committed assumption and disclosed below. The number MFB shows estimates the state's monthly payment to the provider on the household's behalf, not a payment to the household.

### The rates

Rates come from DESE's published workbook, which DESE currently labels as the live rate table:

- Source: DESE, Child Care Subsidy Payments — "Child Care Payment Rate Tables (Current)" — [snapshot `2026-09-03--dese-child-care-subsidy-payments`](../../../sources/mo/mo_ccs/2026-09-03--dese-child-care-subsidy-payments/content.md), accessed 2026-09-03

**The same workbook carries an end date that has passed.** Its own sheet title reads:

- Source: DESE 2025 Rates Held Harmless 2.0, sheet "Daytime Rates 2025" — "2025 Daytime Rates effective October 1, 2025 to June 30, 2026" — [snapshot `2026-09-03--dese-subsidy-provider-rates-2025-held-harmless`](../../../sources/mo/mo_ccs/2026-09-03--dese-subsidy-provider-rates-2025-held-harmless/content.md), accessed 2026-09-03

DESE presents the table as current while the table describes itself as expired on 2026-06-30, and no successor is published. This spec uses it because it is the only workbook DESE publishes and DESE labels it current — **not** because it is unambiguously in force. Every value below inherits that qualification, and the treatment stands until DESE publishes a successor workbook.

#### Committed daily rates — Licensed Center, Daytime

Read from the workbook's "Daytime Rates 2025" sheet, Licensed Center row of each grouping.
Each grouping's citation below quotes the Licensed Center row through the school-age half-time
cell, so **all four committed values are inside the quoted span**. The column pattern is **not uniform across age categories**: Infant Toddler carries six columns
(base and 25%-enhanced twin, for full, half and part time), while Preschool and School Age each
carry nine (a base at the 65th percentile, a PS rate at market, and a PS rate at market plus 25%,
for each of the three time categories). Counting from the first numeric cell, the four committed
values are cells 1 (Infant full), 7 (Preschool full), 16 (School Age full) and 19 (School Age
half) — always the plain, unenhanced rate. The workbook stores
several as binary floats — the school-age half-time cells read `34.905000000000001` and
`22.515000000000001` — and the table states the exact decimal. Criterion 7's chart-maximum and
85%-SMI tables and the sliding-fee bands are likewise anchored to the cited chart snapshot.

| Grouping | Infant full | Preschool full | School age full | School age half |
|---|---|---|---|---|
| Region 1 Dense Urban | $96.00 | $50.00 | $36.00 | $27.00 |
| Region 2 Metro | $71.60 | $37.00 | $34.00 | $25.50 |
| Region 3 Urban | $79.00 | $40.00 | $46.54 | $34.905 |
| Region 4 Micropolitan | $58.50 | $32.50 | $30.00 | $22.50 |
| Region 5 Rural | $58.50 | $31.00 | $30.02 | $22.515 |

- Source: DESE 2025 Rates Held Harmless 2.0, sheet "Daytime Rates 2025", Region 1 Dense Urban Licensed Center row — "| Licensed Center | 96 | 120 | 72 | 90 | 48 | 60 | 50 | 71.569999999999993 | 89.462499999999991 | 37.5 | 53.677499999999995 | 67.096874999999997 | 25 | 35.784999999999997 | 44.731249999999996 | 36 | 55 | 68.75 | 27" — [snapshot `2026-09-03--dese-subsidy-provider-rates-2025-held-harmless`](../../../sources/mo/mo_ccs/2026-09-03--dese-subsidy-provider-rates-2025-held-harmless/content.md), accessed 2026-09-03
- Source: DESE 2025 Rates Held Harmless 2.0, sheet "Daytime Rates 2025", Region 2 Metro Licensed Center row — "| Licensed Center | 71.599999999999994 | 89.5 | 53.699999999999996 | 67.125 | 35.799999999999997 | 44.75 | 37 | 64.66 | 80.824999999999989 | 27.75 | 48.494999999999997 | 60.618749999999999 | 18.5 | 32.33 | 40.412499999999994 | 34 | 46.18 | 57.725000000000001 | 25.5" — [snapshot `2026-09-03--dese-subsidy-provider-rates-2025-held-harmless`](../../../sources/mo/mo_ccs/2026-09-03--dese-subsidy-provider-rates-2025-held-harmless/content.md), accessed 2026-09-03
- Source: DESE 2025 Rates Held Harmless 2.0, sheet "Daytime Rates 2025", Region 3 Urban Licensed Center row — "| Licensed Center | 79 | 98.75 | 59.25 | 74.0625 | 39.5 | 49.375 | 40 | 40.409999999999997 | 50.512499999999996 | 30 | 30.307499999999997 | 37.884374999999999 | 20 | 20.204999999999998 | 25.256249999999998 | 46.54 | 40 | 50 | 34.905000000000001" — [snapshot `2026-09-03--dese-subsidy-provider-rates-2025-held-harmless`](../../../sources/mo/mo_ccs/2026-09-03--dese-subsidy-provider-rates-2025-held-harmless/content.md), accessed 2026-09-03
- Source: DESE 2025 Rates Held Harmless 2.0, sheet "Daytime Rates 2025", Region 4 Micropolitan Licensed Center row — "| Licensed Center | 58.5 | 73.125 | 43.875 | 54.84375 | 29.25 | 36.5625 | 32.5 | 69 | 86.25 | 24.375 | 51.75 | 64.6875 | 16.25 | 34.5 | 43.125 | 30 | 55 | 68.75 | 22.5" — [snapshot `2026-09-03--dese-subsidy-provider-rates-2025-held-harmless`](../../../sources/mo/mo_ccs/2026-09-03--dese-subsidy-provider-rates-2025-held-harmless/content.md), accessed 2026-09-03
- Source: DESE 2025 Rates Held Harmless 2.0, sheet "Daytime Rates 2025", Region 5 Rural Licensed Center row — "| Licensed Center | 58.5 | 73.125 | 43.875 | 54.84375 | 29.25 | 36.5625 | 31 | 55.42 | 69.275000000000006 | 23.25 | 41.564999999999998 | 51.956249999999997 | 15.5 | 27.71 | 34.637500000000003 | 30.02 | 53.11 | 66.387500000000003 | 22.515000000000001" — [snapshot `2026-09-03--dese-subsidy-provider-rates-2025-held-harmless`](../../../sources/mo/mo_ccs/2026-09-03--dese-subsidy-provider-rates-2025-held-harmless/content.md), accessed 2026-09-03

The row order within each grouping is Registered Center, 6 or Fewer, Licensed Center, Licensed
Family Home, Group Home; the quoted cells above are Infant full, Infant PS-enhanced, then the
remaining age and time columns in sheet order. Each quoted prefix occurs exactly once in the
snapshot, so it identifies its grouping unambiguously and cannot be confused with the
Evening/Weekend sheet.

- Source: DESE 2025 Rates Held Harmless 2.0, sheet "Daytime Rates 2025" — "St. Charles, St. Louis County, and St. Louis City, Jefferson, Clay, Jackson & Platte, MSA001C1 REGION 1 DENSE URBAN" — [snapshot `2026-09-03--dese-subsidy-provider-rates-2025-held-harmless`](../../../sources/mo/mo_ccs/2026-09-03--dese-subsidy-provider-rates-2025-held-harmless/content.md), accessed 2026-09-03

### Geographic grouping

The grouping is county-based, and MFB has the county: `county` (Screen, CharField,
nullable) plus `counties_by_zipcode` in `configuration/white_labels/mo.py`, which maps 1,126
Missouri ZIPs onto 115 county strings. Under the committed
assumptions the five groupings produce five distinct Preschool rates, so none collapse. Infant
rates do collapse — Regions 4 and 5 are both $58.50 — so geographic coverage is proven on
Preschool, not Infant.

**The groupings**, from the workbook's "Breakdown Of Counties" sheet. It carries 115 entries — all
114 Missouri counties plus St. Louis City — which is exactly the set `counties_by_zipcode` can
produce, so no screen can present a county the lists do not name and the Region 5 default below is
unreachable. DESE's spellings are reproduced here; the normalization that reaches them from MFB's
follows.

- **Region 1 Dense Urban** (7): Clay, Jackson, Jefferson, Platte, St Charles, St Louis, St Louis City
- **Region 2 Metro** (17): Andrew, Bates, Bollinger, Caldwell, Callaway, Clinton, Cooper, Dallas, Franklin, Howard, Lafayette, Lincoln, Moniteau, Osage, Polk, Warren, Webster
- **Region 3 Urban** (10): Boone, Buchanan, Cape Girardeau, Cass, Christian, Cole, Greene, Jasper, Newton, Ray
- **Region 4 Micropolitan** (22): Adair, Audrain, Butler, Dunklin, Howell, Johnson, Laclede, Marion, Mississippi, Nodaway, Pettis, Phelps, Pulaski, Ralls, Randolph, Schuyler, Scott, St Francois, Stoddard, Stone, Taney, Vernon
- **Region 5 Rural** (59): Atchison, Barry, Barton, Benton, Camden, Carroll, Carter, Cedar, Chariton, Clark, Crawford, Dade, Daviess, Dekalb, Dent, Douglas, Gasconade, Gentry, Grundy, Harrison, Henry, Hickory, Holt, Iron, Knox, Lawrence, Lewis, Linn, Livingston, Macon, Madison, Maries, McDonald, Mercer, Miller, Monroe, Montgomery, Morgan, New Madrid, Oregon, Ozark, Pemiscot, Perry, Pike, Putnam, Reynolds, Ripley, Sainte Genevieve, Saline, Scotland, Shannon, Shelby, St Clair, Sullivan, Texas, Washington, Wayne, Worth, Wright

**Matching is not string equality, and the normalization is an MFB commitment.** MFB's `county`
values carry a "County" suffix DESE's do not (`Greene County` against `Greene`), and the two sets
also differ on periods, on case and on one abbreviation, so on raw strings **zero** of the 115
match. The committed rule is a rule about the *class* of difference, not a list of exceptions:
**strip a trailing ` County`, remove every period, read a leading `Ste ` as `Sainte `, then
casefold.** That matches all 115 with none left over. **The order matters**: written with the
`Ste ` substitution after the casefold it never fires, because the cased literal cannot match a
folded string, and `Ste. Genevieve County` falls through unmatched. That failure is invisible to
testing — Ste. Genevieve is itself Region 5, so the unmatched county takes the Region 5 default and
returns the correct rate, and no scenario or mutation can distinguish the broken path from the
working one.

An exception list is expressly **not** used, because it is what fails here. Naming only the three
obvious divergences — `St. Louis City`, `Ste. Genevieve County`, `DeKalb County` — leaves
**`St. Charles County`, `St. Louis County`, `St. Francois County` and `St. Clair County`**
unmatched on the period alone. Two of those four are Region 1, the highest-paying grouping in the
state, so each would silently take the Region 5 default: a St. Louis County preschool child would
be priced at $31.00 a day rather than $50.00, worth $546.00 a month against $945.00. Scenario 51
pins St. Louis County for that reason, and no scenario keyed on St. Louis **City** can stand in
for it, that being one of the three an exception list would have caught.

A null `county` leaves the rate unselectable. It cannot arise on a completed screen, and the
committed handling is to declare `county` a calculator dependency — see *What the calculator
returns* — so the program is withheld rather than priced at a guessed grouping.

- Source: DESE 2025 Rates Held Harmless 2.0, sheet "Breakdown Of Counties", grouping header row — "Dense Urban Grouping 1 : |  |  | Metro Grouping 2: |  |  | Urban Grouping 3: |  |  | Micro Grouping 4: |  |  | Rural Grouping 5:" — [snapshot `2026-09-03--dese-subsidy-provider-rates-2025-held-harmless`](../../../sources/mo/mo_ccs/2026-09-03--dese-subsidy-provider-rates-2025-held-harmless/content.md), accessed 2026-09-03
- Source: DESE 2025 Rates Held Harmless 2.0, sheet "Breakdown Of Counties", first county row — "Clay |  |  | Andrew | Howard |  | Boone |  |  | Adair | Pulaski |  | Atchison | Henry | Ozark" — [snapshot `2026-09-03--dese-subsidy-provider-rates-2025-held-harmless`](../../../sources/mo/mo_ccs/2026-09-03--dese-subsidy-provider-rates-2025-held-harmless/content.md), accessed 2026-09-03

### Age category and the school-year hold

The categories are Infant (newborn to 2), Preschool (2 to 5) and School age (5 and over), taken
from DESE's published payment categories and keyed off `calc_age` (HouseholdMember). DESE's published endpoints **overlap** — "Infant (newborn to 2 years)" and "Preschool (2 years to
5 years)" both name 2 — so the spec commits the shared endpoint to **Preschool**: a child aged 2
years and ten days at screening is Preschool, not Infant. That is an **MFB commitment** resolving an
ambiguous source, not a published rule, and it is pinned by the boundary pair in Scenarios 43 and 44.

**DESE's categories overlap twice, and both shared endpoints resolve the same way — upward, to the
older category. Only one of the two is an MFB commitment.** "Preschool (2 years to 5 years)" and
"School age (5 and over)" both name 5, exactly as Infant and Preschool both name 2. **At age 5 the
regulation settles it**: `.050(37)` defines School Age as an eligible child "at least five (5) years
of age", so a child whose `calc_age` is 5 is School age by definition and the published pages' overlap
is resolved by the rule rather than by this spec. **At age 2 there is no such definition** — `.050`
defines neither Infant nor Preschool — so that edge is the MFB commitment stated above. The age-5
assignment is subject to the school-year hold immediately below, which is what moves a held
five-year-old back to the Preschool rate. Scenarios 43/44 pin the age-2 edge and Scenarios 12, 14
and 35 the age-5 one.

- Source: 5 CSR 25-200.050(37) — "“School Age” means an eligible child at least five (5) years of age." — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md) (accessed 2026-09-03)

Missouri's *transition-timing* rule at Manual 8.8 — the rate change made the first day of the month following the 2nd and 5th birthdays — governs an **existing case**, not which category a first-time applicant's child falls in, so this spec does not apply it and the published categories above govern. It is recorded in `review-notes.md` as continuing-case behaviour.

A school-year hold sits on top of the five-year boundary: a child not yet 5 before August 1 stays
at the Preschool rate for that school year, so the operative boundary there is **birth month July
versus birth month August**. MFB commits the hold's window as August 1 through July 31 — the
"school year" the DESE sentence names — which is an **MFB commitment**, not a published date range;
a held child therefore keeps the Preschool rate until the following August 1.

The hold's input is `birth_year_month` (HouseholdMember, DateField, nullable) — **not** `calc_age`,
which returns 5 on both sides of the July/August edge. Where `birth_year_month` is null the hold
cannot be determined, and the committed handling is to **apply it**, keeping the child at the
Preschool rate: that is the inclusive direction, because Preschool out-pays School age in four of
the five groupings, and it is worth $426.875 a month in Region 1. `calc_age`'s `age` fallback still
supplies the category itself.

- Source: DESE, Child Care Subsidy Payments — "Infant (newborn to 2 years)" — [snapshot `2026-09-03--dese-child-care-subsidy-payments`](../../../sources/mo/mo_ccs/2026-09-03--dese-child-care-subsidy-payments/content.md), accessed 2026-09-03
- Source: DESE, Child Care Subsidy Payments — "Preschool (2 years to 5 years)" — [snapshot `2026-09-03--dese-child-care-subsidy-payments`](../../../sources/mo/mo_ccs/2026-09-03--dese-child-care-subsidy-payments/content.md), accessed 2026-09-03
- Source: DESE, Child Care Subsidy Payments — "School age (5 years and over)" — [snapshot `2026-09-03--dese-child-care-subsidy-payments`](../../../sources/mo/mo_ccs/2026-09-03--dese-child-care-subsidy-payments/content.md), accessed 2026-09-03
- Source: DESE, Child Care Subsidy Payments — "Effective May 2026, children who are not yet age 5 before August 1 will be paid at the preschool rate for the school year." — [snapshot `2026-09-03--dese-child-care-subsidy-payments`](../../../sources/mo/mo_ccs/2026-09-03--dese-child-care-subsidy-payments/content.md), accessed 2026-09-03

Two facts about direction, which must not be conflated. **At the daily-rate level** Preschool
exceeds School age in four of the five Licensed Center full-day cells; Region 3 Urban is the
exception, where School age pays $46.54 against Preschool's $40.00. **At the monthly-value level,
however, the hold raises the estimate in all five groupings**, because a school-age child in the
school year is authorized at the half-day rate rather than the full-day rate (see the care pattern
below). In Region 3 the hold is worth `+$44.2825` a month net of the committed fee (the $5.00 full-unit and $3.25 half-unit amounts introduced with the fee bands below) — the smallest of the five — precisely
because that grouping's school-age rate is the strongest.

### The authorized care pattern

**Missouri defines the daily time categories by hours of care, and those definitions are sourced —
MFB selects a bracket, it does not invent one.** The chart and the DESE Payments page state the same
three brackets in different words.

- Source: DESE Child Care Eligibility Income Guidelines and Sliding Fee Chart — "Full time care is five hours of care up to twelve hours" — [snapshot `2026-09-03--dese-income-limits-and-sliding-fee-chart`](../../../sources/mo/mo_ccs/2026-09-03--dese-income-limits-and-sliding-fee-chart/content.md) (accessed 2026-09-03)
- Source: DESE Child Care Eligibility Income Guidelines and Sliding Fee Chart — "Half time care is three hours of care up to five hours of care" — [snapshot `2026-09-03--dese-income-limits-and-sliding-fee-chart`](../../../sources/mo/mo_ccs/2026-09-03--dese-income-limits-and-sliding-fee-chart/content.md) (accessed 2026-09-03)
- Source: DESE, Child Care Subsidy Payments — "Full day (5 to 12 hours per day)" — [snapshot `2026-09-03--dese-child-care-subsidy-payments`](../../../sources/mo/mo_ccs/2026-09-03--dese-child-care-subsidy-payments/content.md) (accessed 2026-09-03)
- Source: DESE, Child Care Subsidy Payments — "Half day (3 to 4 hours and 59 minutes per day)" — [snapshot `2026-09-03--dese-child-care-subsidy-payments`](../../../sources/mo/mo_ccs/2026-09-03--dese-child-care-subsidy-payments/content.md) (accessed 2026-09-03)

Missouri authorizes an amount of care, and three observable categories determine it.

**School-age children during the school year** are authorized for before-and-after-school care plus
a fixed allowance of full-time days, so the full-day rate is the wrong basis for them:

- Source: Manual 7.9 — "shall include five full‐time days of care September" — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03

Manual 7.9 attaches "September through April" to the **five full-time days**, not to the school year itself, so the source states no window. **MFB commits September through April as the window — eight months — inferred from the span the five-day allowance covers.** That inference is the denominator of the `5/8` figure below, and it is an MFB commitment rather than a Missouri rule.

- Source: Manual 7.9 — "through April to allow for payment of days when school is not in session." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03

Committed treatment: the before-and-after-school unit is priced at the **half-day** rate — an MFB
proxy, because exact school-care hours are not collected — for 21 days, plus the five full-time
days spread evenly across the eight school-year months at `5/8` of a full day per month.

**Households experiencing homelessness** are authorized full-time — **except that where the child is
school-age the authorization follows the child's own school schedule instead.** Manual 7.5 carries
both halves in consecutive sentences, and the qualification matters: for a school-age child it is
the second sentence, not the first, that governs. Note the two scopes are worded differently —
Manual 7.9 reaches "children enrolled in school" and 7.5's qualification reaches "a school‐aged
child" — so the spec asserts no equivalence between them. Both are sourced policy that the estimate does **not** apply,
because Missouri's screener flow populates no field expressing homelessness (Data Gap 16):

- Source: Manual 7.5 — "The child of an applicant experiencing homelessness shall be authorized for full‐time care." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
- Source: Manual 7.5 — "If the child is a school‐aged child, the authorization shall be based on the school schedule of the child." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03

**Every other household** is priced at Full day, Daytime — one committed assumption applied across
all eight qualifying-activity pathways. **Missouri does not set the daily time category the same way
for all eight.** The Manual pairs each pathway in §6 with its own authorization rule in §7, and only
the employment rule turns on hours worked.

| Pathway | Missouri's authorization rule | Why it is not modelled |
|---|---|---|
| Employment | 7.1 — over 30 hours full-time, under 30 part-time or half-time | `hours_worked` (IncomeStream, IntegerField, nullable) is read only on an hourly stream, by `IncomeStream._hour_to_month` and nothing else, so weekly hours are not available across employment types |
| Education | 7.2 — a full-time student draws full-time care, a part-time student part-time or half-time | `student_full_time` asks "enrolled **half-time or more**", so `true` spans Missouri's full-time *and* part-time student alike — the cut Missouri makes is not the cut the field records |
| Training | 7.3 — the same full-time/part-time student test | the same field and the same limit |
| Job search | 6.4 and 7.4 — **part-time** where job search is the initial qualifying activity | the rule needs no fact MFB lacks, but the pathway itself is unobservable (Data Gap 5), so a job-search household cannot be told from any other and reaches eligibility through criterion 5 falling open |
| Incapacitation | 7.6 — from the medical provider's and the applicant's statements | no published category to select; unobservable (Data Gap 6) |
| Protective services | 7.7 — from the applicant's statement | unobservable (Data Gap 1) |
| A child's special need | 7.8 — from a medical professional's statement naming the hours per day and days per week | unobservable (Data Gap 7); Scenarios 36 and 39 price special-needs school-age children on Manual 7.9's basis for this reason |
| Homelessness | 7.5 — full-time, or the child's school schedule where the child is school-age | unobservable (Data Gap 16); stated above |

**Direction: Full day is Missouri's most generous daily category, so the assumption overstates the
estimate wherever Missouri would authorize part-time or half-time** — a job-search applicant and a
part-time student or trainee being the two named cases. Data Gap 14 owns this analysis.

- Source: Manual 7.1 — "A participant working more than 30 hours shall be authorized for full‐time care based on their statement and" — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
- Source: Manual 7.1 — "A participant working less than 30 hours will be authorized for part‐time or half‐time care based on their" — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
- Source: Manual 7.2 — "A participant attending school as a full‐time student will be authorized for full‐time care based on their statement and the need verification they provide. A participant attending school as a part‐time student will be authorized for part‐time or half‐time care based on their statement and the need" — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
- Source: Manual 7.3 — "An applicant attending training as a full‐time student will be authorized for full‐time care based on their statement and the need verification they provide." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
- Source: Manual 6.4 — "At the time of application, if the applicant has no other qualifying activity, job search can be authorized as an initial qualifying activity as a part‐time authorization." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
- Source: Manual 7.4 — "An applicant shall be authorized for part‐time daytime authorization for job search when used as the initial qualifying activity and full‐time following the loss of a qualifying activity for 90 days." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
- Source: Manual 7.6 — "An applicant who is incapacitated/disabled shall be authorized based on the medical provider’s statement and the applicant’s statements." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
- Source: Manual 7.7 — "The child receiving protective services shall be authorized based on the statement of the applicant (e.g., foster parent/Children’s Division staff), unless DESE has information contradicting the applicant’s stated need, at which time DESE shall request written documentation." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
- Source: Manual 7.8 — "The child with a special need for child care shall be authorized based on the medical professional statement that includes the reason care is needed, the number of hours of care needed per day, the number of days per week child care is needed, and the anticipated duration of the need for care." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03

### The sliding fee

The fee is a daily amount per child in care, keyed on Eligibility Unit size and Missouri adjusted
gross income, and it varies by the daily time category — so a half-day authorization draws the
half-unit fee, not the full-unit fee.

- Source: Manual 9.1 — "The sliding fee varies by the amount of care (full, half, and part time)." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03

**Committed fee bands.** The three fee amounts are the same at every Eligibility Unit size; only
the income range that selects a band moves with size. **Every published size is stated below**, so
no size sends Implement back to the chart. Sizes 1 through 8 are the whole of what a screen can
produce, the screener capping a household at eight members; sizes 9 through 20 are the rest of what
DESE publishes and are retained unreachable for the same reason criterion 7 keeps its rows 9–20 —
they are Missouri's published figures and the cap is an MFB form limit, not a statement about the
program. A unit above the published range takes the size-20 row, which is unreachable twice over.

| Fee: full / half / part unit | Size 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| `$1.00 per year` (see below) | up to $417 | up to $545 | up to $674 | up to $802 | up to $930 | up to $1,058 | up to $1,082 | up to $1,106 | up to $1,130 | up to $1,154 |
| `$0.50 / $0.35 / $0.25` | $418 – $500 | $546 – $654 | $675 – $808 | $803 – $962 | $931 – $1,116 | $1,059 – $1,270 | $1,083 – $1,299 | $1,107 – $1,328 | $1,131 – $1,356 | $1,155 – $1,385 |
| `$0.75 / $0.50 / $0.35` | $501 – $583 | $655 – $763 | $809 – $943 | $963 – $1,122 | $1,117 – $1,302 | $1,271 – $1,482 | $1,300 – $1,515 | $1,329 – $1,549 | $1,357 – $1,582 | $1,386 – $1,616 |
| `$1.00 / $0.65 / $0.45` | $584 – $667 | $764 – $872 | $944 – $1,078 | $1,123 – $1,283 | $1,303 – $1,488 | $1,483 – $1,693 | $1,516 – $1,732 | $1,550 – $1,770 | $1,583 – $1,808 | $1,617 – $1,847 |
| `$2.00 / $1.30 / $0.90` | $668 – $750 | $873 – $981 | $1,079 – $1,212 | $1,284 – $1,443 | $1,489 – $1,674 | $1,694 – $1,905 | $1,733 – $1,948 | $1,771 – $1,991 | $1,809 – $2,034 | $1,848 – $2,078 |
| `$3.00 / $1.95 / $1.35` | $751 – $834 | $982 – $1,090 | $1,213 – $1,347 | $1,444 – $1,604 | $1,675 – $1,860 | $1,906 – $2,117 | $1,949 – $2,165 | $1,992 – $2,213 | $2,035 – $2,261 | $2,079 – $2,309 |
| `$4.00 / $2.60 / $1.80` | $835 – $917 | $1,091 – $1,199 | $1,348 – $1,482 | $1,605 – $1,764 | $1,861 – $2,046 | $2,118 – $2,328 | $2,166 – $2,381 | $2,214 – $2,434 | $2,262 – $2,487 | $2,310 – $2,539 |
| `$5.00 / $3.25 / $2.25` | $918 – $1,956 | $1,200 – $2,644 | $1,483 – $3,331 | $1,765 – $4,019 | $2,047 – $4,706 | $2,329 – $5,394 | $2,382 – $6,081 | $2,435 – $6,769 | $2,488 – $7,456 | $2,540 – $8,144 |

| Fee: full / half / part unit | Size 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 |
|---|---|---|---|---|---|---|---|---|---|---|
| `$1.00 per year` (see below) | up to $1,179 | up to $1,203 | up to $1,227 | up to $1,251 | up to $1,275 | up to $1,299 | up to $1,323 | up to $1,347 | up to $1,371 | up to $1,395 |
| `$0.50 / $0.35 / $0.25` | $1,180 – $1,414 | $1,204 – $1,443 | $1,228 – $1,472 | $1,252 – $1,501 | $1,276 – $1,529 | $1,300 – $1,559 | $1,324 – $1,587 | $1,348 – $1,616 | $1,372 – $1,645 | $1,396 – $1,674 |
| `$0.75 / $0.50 / $0.35` | $1,415 – $1,650 | $1,444 – $1,684 | $1,473 – $1,717 | $1,502 – $1,751 | $1,530 – $1,784 | $1,560 – $1,818 | $1,588 – $1,852 | $1,617 – $1,885 | $1,646 – $1,919 | $1,675 – $1,953 |
| `$1.00 / $0.65 / $0.45` | $1,651 – $1,886 | $1,685 – $1,924 | $1,718 – $1,962 | $1,752 – $2,001 | $1,785 – $2,039 | $1,819 – $2,078 | $1,853 – $2,116 | $1,886 – $2,155 | $1,920 – $2,193 | $1,954 – $2,232 |
| `$2.00 / $1.30 / $0.90` | $1,887 – $2,121 | $1,925 – $2,165 | $1,963 – $2,208 | $2,002 – $2,251 | $2,040 – $2,294 | $2,079 – $2,338 | $2,117 – $2,381 | $2,156 – $2,424 | $2,194 – $2,467 | $2,233 – $2,511 |
| `$3.00 / $1.95 / $1.35` | $2,122 – $2,357 | $2,166 – $2,405 | $2,209 – $2,453 | $2,252 – $2,501 | $2,295 – $2,549 | $2,339 – $2,598 | $2,382 – $2,646 | $2,425 – $2,694 | $2,468 – $2,742 | $2,512 – $2,790 |
| `$4.00 / $2.60 / $1.80` | $2,358 – $2,593 | $2,406 – $2,646 | $2,454 – $2,698 | $2,502 – $2,751 | $2,550 – $2,804 | $2,599 – $2,857 | $2,647 – $2,910 | $2,695 – $2,963 | $2,743 – $3,016 | $2,791 – $3,068 |
| `$5.00 / $3.25 / $2.25` | $2,594 – $8,831 | $2,647 – $9,519 | $2,699 – $10,206 | $2,752 – $10,894 | $2,805 – $11,581 | $2,858 – $12,269 | $2,911 – $12,956 | $2,964 – $13,644 | $3,017 – $14,331 | $3,069 – $15,019 |

- Source: DESE Child Care Eligibility Income Guidelines and Sliding Fee Chart, `$5.00` band row — "$ 5.00 $ 3.25 $ 2.25              $    918   -    $ 1,956   $ 1,200   -    $ 2,644   $ 1,483   -    $ 3,331" — [snapshot `2026-09-03--dese-income-limits-and-sliding-fee-chart`](../../../sources/mo/mo_ccs/2026-09-03--dese-income-limits-and-sliding-fee-chart/content.md) (accessed 2026-09-03)
- Source: DESE Child Care Eligibility Income Guidelines and Sliding Fee Chart, `$5.00` band row, sizes 11–20 — "$ 5.00 $ 3.25 $ 2.25              $ 2,594    -    $ 8,831   $ 2,647   -    $ 9,519   $ 2,699   -    $ 10,206" — [snapshot `2026-09-03--dese-income-limits-and-sliding-fee-chart`](../../../sources/mo/mo_ccs/2026-09-03--dese-income-limits-and-sliding-fee-chart/content.md) (accessed 2026-09-03)

The top of each `$5.00` range is that unit size's chart maximum, so the band table and criterion
7's **chart-maximum table** close on the same figure at every one of the twenty published sizes —
which is the cross-check that the two transcriptions agree. Note it is the chart-maximum table and
not criterion 7's operative ceiling: that ceiling is `min(chart maximum, 85% SMI)`, and 85% SMI is
the lower of the two at sizes 17 through 20, so above size 16 a band top exceeds the income at
which the household is still eligible.

**The $1.00-per-year band.** Below the daily bands, Missouri charges an annual dollar rather than a
daily fee, and two sourced routes reach it:

- Source: Manual 9.1 — "If an eligibility unit’s only income is Temporary Assistance, or, if the total gross income falls below" — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
- Source: Manual 9.1 — "25% of the state median income level, the participant is required to pay $1 annually to meet the sliding fee" — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
- Source: DESE Child Care Eligibility Income Guidelines and Sliding Fee Chart — "Families in this income group shall pay $1.00 per year which constitutes the periodic payment for the eligibility period" — [snapshot `2026-09-03--dese-income-limits-and-sliding-fee-chart`](../../../sources/mo/mo_ccs/2026-09-03--dese-income-limits-and-sliding-fee-chart/content.md), accessed 2026-09-03

Manual 9.1 states the annual-dollar rule and then, in the **immediately following paragraph**,
defers the determination of the fee amount to the published chart:

- Source: Manual 9.1 — "The amount of the sliding fee paid by the eligibility unit is determined by using the Child Care Eligibility Income" — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03
- Source: Manual 9.1 — "It is based on household size and adjusted gross monthly income." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03

So the operative structure is: Manual 9.1 supplies the rule, and the chart supplies the amounts —
keyed, as 9.1 itself specifies, on household size and adjusted gross monthly income. The current
DESE chart is that published operational fee schedule.

**The two instructions conflict on the income-based `$1`-per-year threshold.** Read literally, 9.1's 25%-of-State-Median-Income limb reaches $2,275.60 for an Eligibility Unit of 4, while the chart's published `$1.00 Per Year` band for that size tops out at $802. Two published DESE instruments give different answers for the same household.

**Committed treatment: the chart governs the income-based sliding-fee bands**, because 9.1 itself directs the chart for the amount and specifies the keys the chart uses, and because the chart is internally consistent with its own SMI row in a way the 25% figure is not. The supporting arithmetic is in `review-notes.md` under Source conflicts.

**Manual 9.1's Temporary-Assistance-only limb is retained and applied as written**, because it
keys on a categorical fact rather than an income threshold and so does not conflict with the chart.

The 25%-SMI reading clears only if DESE changes its published Manual or chart. **Direction of the modelling error, stated:**
choosing $802 over $2,275.60 charges a daily fee where the literal 9.1 reading would charge $1 a
year, so this treatment **understates** the benefit for households between the two figures.

#### Precedence

The waiver, the annual-dollar band and the daily chart can all reach the same household, so they
are applied in a fixed order. This precedence is binding on every scenario below.

1. **A sourced waiver applies** — the child has a special need, is a Protective Services child, or
   the household is experiencing homelessness → the sliding fee for that child is **`$0`**. Of the
   three, only the special-needs subset is observable, so only it fires in estimates; the other two
   are recorded as policy the estimate cannot apply (Data Gaps 1 and 16).
2. **Otherwise, if the Eligibility Unit's only income is Temporary Assistance, or its Missouri
   adjusted gross income falls in the chart's published `$1.00 Per Year` band** → the household
   obligation is Missouri's **`$1` annually**, expressed for MFB's monthly estimate as
   **`$1 ÷ 12` subtracted once per household**. (Manual 9.1's 25%-SMI trigger is not used — see
   the conflict noted under the sliding fee below.)
   Captured via `IncomeStream` `type` `cashAssistance`. That option is **TANF-specific** — its label is "Cash Assistance - TANF", with a separate `cashAssistanceOther` carrying any other cash aid — so the mapping onto Manual 9.1's "only income is Temporary Assistance" is **exact**. The mapping is stated because it was wider than the sourced rule under the earlier generic cash-assistance option, and the committed treatment depends on which of the two options a Missouri screen presents.
3. **Otherwise** → the applicable full-, half- or part-day sliding-fee amount from the current
   chart, per child in care, for each of the 21 care days.

Two consequences of the ordering, both exercised by scenarios:

- Rule 1 is **per child**, so in a household where one child is waived and another is not, the
  waived child contributes no fee while the other is charged under rule 2 or 3.
- Rule 2 is **per household**, so where it governs, the `$1 ÷ 12` is subtracted **once**, never once
  per child — and where every child in the household is waived under rule 1, no fee is subtracted
  at all.

**`$1 ÷ 12` is only MFB's cadence conversion. Missouri's actual rule is `$1` annually.** Missouri
does not bill a monthly fraction, and no daily equivalent of this fee exists or is manufactured
here.

#### The waivers are mandatory

The incorporated Manual states the waiver as a prohibition, not a permission, and it covers two
populations:

- Source: Manual 9.1 — "A sliding fee shall not be charged to children with a special need for child care or Protective Service children." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md), accessed 2026-09-03

A third population has its co-payment waived under Missouri's approved CCDF plan:

- Source: MO ACF-118 CCDF State Plan FFY 2025–2027 Amendment #2, §3.3.1 — "[x] Yes. If yes, identify and describe which family contributions/co-payments waived." — [snapshot `2026-09-03--mo-acf-118-ccdf-state-plan-ffy2025-2027-amendment-2`](../../../sources/mo/mo_ccs/2026-09-03--mo-acf-118-ccdf-state-plan-ffy2025-2027-amendment-2/content.md), accessed 2026-09-03
- Source: MO ACF-118 CCDF State Plan FFY 2025–2027 Amendment #2, §3.3.1(iii) — "[x]Families experiencing homelessness." — [snapshot `2026-09-03--mo-acf-118-ccdf-state-plan-ffy2025-2027-amendment-2`](../../../sources/mo/mo_ccs/2026-09-03--mo-acf-118-ccdf-state-plan-ffy2025-2027-amendment-2/content.md), accessed 2026-09-03
- Source: MO ACF-118 CCDF State Plan FFY 2025–2027 Amendment #2, §3.3.1(vi) — "A sliding fee shall not be charged to families who meet the definition of protective services or have children with special needs." — [snapshot `2026-09-03--mo-acf-118-ccdf-state-plan-ffy2025-2027-amendment-2`](../../../sources/mo/mo_ccs/2026-09-03--mo-acf-118-ccdf-state-plan-ffy2025-2027-amendment-2/content.md) (accessed 2026-09-03)
- Source: MO ACF-118 CCDF State Plan FFY 2025–2027 Amendment #2, §3.3.1(iv) — "[x]Families with children with disabilities." — [snapshot `2026-09-03--mo-acf-118-ccdf-state-plan-ffy2025-2027-amendment-2`](../../../sources/mo/mo_ccs/2026-09-03--mo-acf-118-ccdf-state-plan-ffy2025-2027-amendment-2/content.md) (accessed 2026-09-03)

**The homelessness limb rests on a single source** — the checked box at §3.3.1(iii), which carries no describe-text of its own; see `review-notes.md`. It is moot in estimates either way, because homelessness is unobservable (Data Gap 16).

So the fee is `$0` for a child with special needs, for a Protective Services child, and for a
household experiencing homelessness. **Only the special-needs subset is applied in estimates** —
the Protective Services and homelessness waivers are stated as binding policy but cannot be
triggered from screener data (Data Gaps 1 and 16). **The waiver is per child**, not household-wide:

- Source: 5 CSR 25-200.060(3)(C)4 — "The sliding scale fee may be waived for a child with special needs." — [snapshot `2026-09-03--csr-5-25-200-child-care-subsidy`](../../../sources/mo/mo_ccs/2026-09-03--csr-5-25-200-child-care-subsidy/content.md), accessed 2026-09-03

`.060(3)(C)4` is **permissive** where the incorporated Manual 9.1 is mandatory. The spec relies on the regulation only for the waiver's **per-child scope** and follows Manual 9.1 on mandatoriness; see `review-notes.md`.

### The fixed proxy assumptions

| Assumption | Committed value | Effect on the estimate |
|---|---|---|
| Provider type | Licensed Center | a modelling choice, not an empirical claim; a licensed family home or group home draws a lower rate at every grouping |
| Children in care | every eligible child | **an MFB modelling choice, not a Missouri rule.** `.050(17)(A)` is singular — "The child for whom care is requested" — and the fee chart is headed "DAILY SLIDING FEE PER CHILD IN CARE", but which children a household asks for care for is not collected, so the estimate prices care for all of them. This is the one proxy whose error is **multiplicative**: a household with three eligible children needing care for one is shown three times what it would receive. `cross_white_label/ccdf/ks.py` sums over its eligible children for the same reason and says so |
| Care days per month | 21 | **an MFB full-time weekday estimate, not a Missouri rule**; actual authorized days may be fewer or more. Missouri sets this figure **per authorization**, not by published schedule — the Authorization Letter states the number for each child and caps payment at it — so no source can supply a constant here and the proxy cannot be replaced by a citation |
| Daily time category | Full day | applied on all eight qualifying-activity pathways, though Manual 7.1 through 7.8 set it a different way on each; Full day is Missouri's most generous category, so this **overstates** wherever Missouri would authorize part-time or half-time (Data Gap 14) |
| Before-and-after-school unit | half day | **an MFB bracket selection**, not an MFB definition: Missouri defines the half-time bracket as three to five hours of care, and MFB assumes a before-and-after-school need falls inside it. Missouri sizes the authorization to the applicant's actual need |
| Time of week | Daytime | the 15% non-traditional-hours differential is never applied |
| Provider's actual charge | at least the state maximum | so the actual-charge cap binds at the state rate; where a provider charges less, Missouri pays the lower amount and this estimate is too high |
| Approved rate differentials | none | the 20% accreditation, 30% disproportionate-share, 25% special-needs and 15% non-traditional-hours differentials are all excluded |
| Five full-time school-year days | `5/8` of a full day per month, September–April | **an MFB smoothing, not a Missouri rule** — Missouri authorizes the five days as needed, so a household using them in fewer months is understated in those months and overstated in the rest |
| Functional age | chronological age | see below |

- Source: MO ACF-118 CCDF State Plan FFY 2025–2027 Amendment #2, §4.3.3 — "The Lead Agency has a 15% rate differential for evening and weekend care." — [snapshot `2026-09-03--mo-acf-118-ccdf-state-plan-ffy2025-2027-amendment-2`](../../../sources/mo/mo_ccs/2026-09-03--mo-acf-118-ccdf-state-plan-ffy2025-2027-amendment-2/content.md), accessed 2026-09-03

**On the 21 days.** 21 is an **MFB estimation proxy**. It is not derived from Missouri's rules and
must not be presented as though it were. Its provenance is MFB's own modelling at Discovery —
252 assumed working days a year ÷ 12 — and **neither input is validated by any Missouri instrument**:
no captured source states 252, a year carries roughly 261 weekdays rather than 252, and nothing
records how the figure was arrived at. What Missouri actually does is state the authorized number of
days on each child's Authorization Letter and pay no more than that; it publishes no standard
monthly figure. MFB's own platform constant would give `5 × 4.35 = 21.75` for raw weekdays, which is
no better founded here and which no source distinguishes from 21. The proxy is retained on that
basis — an explicitly labelled MFB estimate, with its direction disclosed — and the question is
settled rather than open.

**On the excluded differentials.** Because the estimate assumes no approved provider rate
differential, it understates payment relative to an otherwise identical case where a differential
applies. Other proxy assumptions may cause the overall estimate to be higher or lower than the
household's actual subsidy.

- Source: DESE, Child Care Subsidy Rates and Sliding Fees — "20 percent for accredited programs, 30 percent for accredited programs with at least half of the children subsidy-eligible, and 25 percent for programs serving children with special needs." — [snapshot `2026-09-03--dese-child-care-subsidy-rates-and-sliding-fees`](../../../sources/mo/mo_ccs/2026-09-03--dese-child-care-subsidy-rates-and-sliding-fees/content.md), accessed 2026-09-03

**On functional age.** A child with special needs is paid at the rate of their functional age, which
no screener field expresses, so chronological age is the committed proxy and the estimate is not the
exact Missouri rate where the two differ. No single direction can be stated: a functional age
falling into the Infant category always raises the true rate, because Infant is the highest-paying
category in every published cell, but a shift from School age to Preschool can raise or lower it —
and under the committed Licensed Center assumptions Region 3 Urban is a grouping where it lowers.

- Source: MO ACF-118 CCDF State Plan FFY 2025–2027 Amendment #2, §2.3.1 — "Child care rates for children classified as having special needs are paid at the rate of the child" — [snapshot `2026-09-03--mo-acf-118-ccdf-state-plan-ffy2025-2027-amendment-2`](../../../sources/mo/mo_ccs/2026-09-03--mo-acf-118-ccdf-state-plan-ffy2025-2027-amendment-2/content.md), accessed 2026-09-03
- Source: Manual 9.4 — "Rates paid by DESE are based on the child’s functional age." — [snapshot `2026-09-03--dese-eligibility-policy-manual-may-2026`](../../../sources/mo/mo_ccs/2026-09-03--dese-eligibility-policy-manual-may-2026/content.md) (accessed 2026-09-03)

### What the calculator returns

Eight points, all verified against `benefits-api` `origin/main` `634b7f2f` and
`benefits-calculator` `origin/main` `9eff7d80`. Points 1, 7 and 8 break the program **silently** if
they are missed — the wrong cadence ships one twelfth of the benefit, an undeclared
`dependencies` ships always-calculate by accident, and an FPL-derived ceiling raises every
income limit above the published chart without raising an error. Point 6 is the only one that breaks it
**loudly**, at registry build.

1. **Return the annual figure, not the monthly one.** `household_value()` returns
   `int(monthly × 12)`. The monthly formula throughout this section is the derivation, not the
   return value. A monthly return would display as **one twelfth** of the benefit.
2. **`value_format` stays `null`.** Its model label is `Default (Monthly)`, and that names the
   **display** cadence: `FormattedValue.tsx`'s `default` formatter renders
   `programValue(program) / 12` with a `/month` suffix, and `ProgramPage.tsx` renders the
   undivided figure under "Estimated Annual Value". Neither other option works — `lump_sum` renders
   "Estimated One-Time Payment" for a recurring benefit, and `estimated_annual` renders "/year"
   under "Average Annual Savings", which is both the wrong cadence and the wrong noun, since this
   value is a payment to the provider rather than a household saving.
3. **Truncate inside the calculator.** MFB *rounds* on display — `formatToUSD` is
   `Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD', maximumFractionDigits: 0})`,
   whose default mode is half-expand, so a computed $1,039.50 displays as **$1,040**. The
   `math.trunc` in `screener/views.py` touches the payload's `estimated_value`, which the
   household-facing card value never reads — the card sums `household_value` and the member values
   through `programValue`, and neither is truncated. `estimated_value` *is* read elsewhere in the
   frontend — `calculateTotalValue` for a program inside a category cap, and the admin-view
   validation paths in `ProgramCard.tsx` and `ProgramPage.tsx` — but none of those is reachable
   for Missouri, because category caps are defined only in `programs/categories/co/caps.py`.
   Returning a whole-dollar `int`, as `cross_white_label/ccdf/ks.py` does, makes the returned
   figure, the payload and the card agree.
4. **Put the whole figure in `household_value`, with no member values.** The `$1`-a-year obligation
   under precedence rule 2 is charged once per household and cannot be expressed once the value is
   split across members — the same reason `ks.py` returns its whole figure this way, and the shape
   `il_ccap` could not express its clamp in.
5. **A `$0` return would be invisible.** `filterPrograms.ts` drops a program whose `programValue` is
   not greater than zero from the results page entirely, so the household would see no card at all
   rather than an eligible one worth nothing. Missouri cannot reach `$0` here — the `max(0, …)`
   clamp is unreachable on both fee columns (see Known scenario gaps), and `ProgramCalculator.eligible`
   sets `e.condition(one_member_eligible)`, so an eligible household with no eligible child and
   therefore an empty value sum cannot arise either — so no visibility floor is applied. This is a
   deliberate divergence from `cross_white_label/ccdf/ks.py`, which returns `max(1, annual)` because
   its own clamp *is* reachable: the Kansas family share is income-scaled and can exceed the benefit.
   Recorded because it binds the moment a rate or fee change makes Missouri's clamp reachable.
6. **Declare `program_code = "mo_ccs"` on the class.** `programs/framework/base.py`'s
   `ProgramCalculator` requires every subclass to declare either `program_code` — the
   `Program.name_abbreviated` of the row it backs — or `abstract=True`, and raises when the registry
   is built if it declares neither. Every CCDF sibling does: `ks.py` `"ks_ccap"`, `il.py` `"il_ccap"`,
   `co.py` `"cccap"`, `ma.py` `"ma_ccdf"`. Without it the calculator is not reachable at all.
7. **Declare `dependencies`.** `ProgramCalculator.dependencies` defaults to an empty tuple in
   `programs/framework/base.py`, and `can_calc` returns
   `not missing_dependencies.has(*self.dependencies)` — so a calculator declaring nothing always
   runs, on whatever nulls the screen happens to carry, and silence ships that behaviour by
   accident rather than by decision. The committed list is
   `["age", "relationship", "county", "income_amount", "income_frequency"]`: the fields without
   which no verdict and no value can be formed. Two omissions are deliberate, on the pattern
   `cross_white_label/ccdf/ks.py` sets out in its own comment. **`household_assets` is not
   declared**, because criterion 8 is committed to falling open on a null and declaring it would
   drop the program from results before that test could run. **`household_size` is not declared**,
   because criterion 7 derives Eligibility Unit size from the member roster and never consults it.
   The vocabulary is fixed by `Screen.missing_fields` and `HouseholdMember.missing_fields` in
   `screener/models.py`. Declaring `county` is also what makes the null-`county` case safe: the
   program is withheld rather than priced at a guessed grouping, which is where a `$0` value would
   land it anyway through `filterPrograms.ts`, but reached deliberately instead of by a crash.
   Three of the four CCDF siblings declare the attribute, and the two other custom ones both
   declare a geography: `ks.py` and `il.py` `county`, `co.py` `zipcode`.
8. **Do not derive the income ceiling from `program.py`'s FPL.** The twenty chart maxima in
   criterion 7 are hard-coded constants transcribed from DESE's chart. They happen to equal
   `round(1.5 × FPL(size) ÷ 12)` on the **2025** guidelines, and `cross_white_label/ccdf/il.py`
   computes its own CCDF ceiling that way — `self.fpl_percent * self.program.year.get_limit(...)`.
   That is the one place MO must **not** follow the sibling: the config pins `"year": 2026`, so the
   same expression here reads the 2026 table and raises every ceiling by $39 to $466 a month above
   the chart Missouri actually publishes. Transcribe the table; see criterion 7.

Scenario values below state the monthly derivation, with the annual return and the displayed figure
alongside each one.

The family separately owes the sliding fee to the provider, plus any charge the provider makes above
the state rate.

- Source: DESE, Child Care Subsidy Rates and Sliding Fees — "which cannot exceed the non-subsidy rate charged by the child care program" — [snapshot `2026-09-03--dese-child-care-subsidy-rates-and-sliding-fees`](../../../sources/mo/mo_ccs/2026-09-03--dese-child-care-subsidy-rates-and-sliding-fees/content.md), accessed 2026-09-03

## Test Scenarios

**Coverage map**

| Rule / variation axis | Scenarios |
|---|---|
| Criterion 1 — Missouri residency | none — `assumed-met`, no calculator branch |
| Criterion 2 — child resides with a qualifying parent | none — `assumed-met`, no calculator branch |
| Criterion 3 — child citizenship (`config`) | none — config axis, not a calculator branch |
| Criterion 4 — child under 13, `BASE_AGE_LIMIT` and month granularity | pass: 31; fail: 32 (boundary pair 31/32) |
| Criterion 4 — special-needs age extension (13–17) | pass: 36; fail: 32; upper edge pinned by 39/40 |
| Criterion 5 — qualifying activity | pass: all; fail: none — cannot screen out (see criterion 5) |
| Criterion 6 — relationship accepted set | pass: 18; fail: 19 |
| Criterion 7 — chart maximum by Eligibility Unit size | pass: 6; boundary: 6/7; size varied: 33, 50 |
| Criterion 7 — `min(chart, 85% SMI)` ceiling value and crossover size | none — unreachable: the screener caps a household at 8 members, so the 85%-SMI limb never binds and the crossover size cannot be reached (see Known scenario gaps) |
| Criterion 7 — Eligibility Unit composition model | 37 — the only scenario that discriminates the household baseline from a closed-enumeration reading of `.050(17)` ($824.25 vs $798.00) |
| Criterion 7 — health-insurance deduction | pass: 8; fail: 9 |
| Criterion 7 — SSI exclusion | pass: 10 |
| Criterion 7 — child-earnings exclusion | pass: 15; fail: 16 |
| Criterion 7 — frequency conversion | boundary: 17 |
| Criterion 8 — net worth $1,000,000, asymmetric | pass at the limit: 20; above the limit and fail: neither — the asymmetry rests on the missing debt input, so that side is a data gap (Data Gap 19) |
| Value — geographic grouping (five distinct outcomes) | 1 (R1), 2 (R2), 3 (R3), 4 (R4), 5 (R5) |
| Value — county normalization, the period class | 51 — `St. Louis County` → Region 1; $945.00 against $546.00 under an exception-list match |
| Value — age category, Infant | Infant/Preschool boundary pair: 43/44; the Infant rate read in four of the five groupings: 44 (R1), 45 (R2), 46 (R3), 47 (R4) — R5's cell goes unread, publishing the same $58.50 as R4, so Scenario 47 pins the value both use but not the cell |
| Value — school-year preschool hold, July/August boundary | boundary: 11/12 and 13/14 |
| Value — daily time category (full day vs half day + `5/8`) | 11, 12, 14, 35 |
| Value — school-age school-year authorization | 12, 14; window opening boundary: 12/35; window closing boundary: 41/42 |
| Value — fee band edges | 21/22 ($4.0 / $5.0, pinned to the dollar); band-floor read at 30; mid-band reads at 33, 37 and 50 (size 2, 3, 4 and 5 columns exercised) |
| Value — daily rate constants, grouping × age category | Preschool: 1–5 (all five groupings). Infant: 44 (R1), 45 (R2), 46 (R3), 47 (R4) — four of five cells, R5's sharing R4's published value. School age: 12 (R1), 14 (R3) only. Thirteen of the twenty published Licensed Center Daytime cells are read — see Known scenario gaps for the seven that are not |
| Value — sliding-fee bands, full unit (all eight read) | `$1.00 per year`: 25, 26, 27, 29 · `$0.50`: 30 · `$0.75`: 37 · `$1.00`: 48 · `$2.00`: 33 · `$3.00`: 49 · `$4.00`: 21 · `$5.00`: 1–5 and most others |
| Value — sliding-fee half unit (school-age authorization) | `$3.25` only: 12, 14, 31, 41. The other six half-unit amounts are unread — see Known scenario gaps |
| Value — fee precedence rule 1 (waiver) | 23 (SSI limb), 34 (`has_disability` limb), 24, 36 |
| Value — fee precedence rule 3 charged **per child in care** | 38 — two unwaived children, $1,890.0 against $1,995.0 if charged once per household |
| Value — fee precedence rule 2 ($1/year band, once per household) | 25, 26, 27; rule-2/rule-3 threshold pinned to the dollar by 25/30 ($802 / $803) |
| Value — fee precedence rule 1 over rule 2 | 28, 29 |
| Value — per-child waiver scope | 24, 29 |
| Value — homelessness (full-time + waived fee) | none — unmodelable, see Data Gap 16 |

**Known scenario gaps**

- Criterion 3 is a configuration axis with no calculator branch and no observable per-member status, so nothing is testable.
- Criterion 5 cannot screen a household out, because three of its eight pathways are wholly unobservable and the remaining five only partly so. No failing case exists, and an imported minimum-hours test would survive the set.
- The Protective Services route (Data Gap 1) and four special-needs limbs (Data Gap 2) have no observable input, so neither the route nor the Protective Services `$0` fee can be exercised.
- The both-age-fields-null guard in criterion 4, and the null `county` and null `household_assets` fall-open paths, are unreachable from a completed screen. A null `household_size` is simply not consulted — criterion 7 derives unit size from the member roster.
- `calc_age`'s fallback to `age` is unreachable the same way, because the member form requires a birth month and a birth year on every member, so `birth_year_month` is always populated on a screen a user completes. The branch is not dead code — the API serializer accepts a member without those two fields, and legacy rows may carry a bare `age` — but no scenario can be written for it from screener input.
- The `max(0, …)` clamp in the value formula is unreachable on both fee columns: the lowest Licensed Center full-day rate is $30.00 against a maximum full-unit fee of $5.00, and the lowest half-day rate is $22.50 against a maximum half-unit fee of $3.25.
- The absent-county fallback to Region 5 is unreachable on both sides of the match. The "Breakdown Of Counties" sheet carries 115 entries — all 114 Missouri counties plus St. Louis City — and `counties_by_zipcode` in `configuration/white_labels/mo.py` produces exactly 115 distinct county strings across its 1,126 ZIPs, so neither set holds a value the other lacks. What *is* reachable, and what the committed normalization in Benefit Value exists to prevent, is a county falling to the default because the match was written as an exception list rather than as a rule about the class of difference: four counties differ from DESE's spelling by a period alone, two of them in Region 1. Scenario 51 is the test — it is keyed on `St. Louis County`, which an exception list naming `St. Louis City` would not have covered.
- A null `relationship` and the three all-null disability booleans are unreachable for the same reason as the guards above, since `relationship`, `disabled`, `long_term_disability` and `visually_impaired` are all required for a complete screen.
- **No Eligibility Unit larger than 8 is reachable at all**, because the screener caps a household at eight members — the size step validates the count as at most 8 and slices the member roster to it — so the committed unit size can never exceed 8. Three things follow.
  - The 85%-SMI limb of criterion 7's `min(chart maximum, 85% SMI)` **never binds**: at every reachable size the chart maximum is the lower of the two figures ($1,956 against $4,023.26 at size 1; $6,769 against $10,677.13 at size 8), so the crossover the two tables assert at size 17 cannot be exercised and no scenario pins it.
  - Rows 9 through 20 of criterion 7's two constant tables, and rows 9 through 20 of the sliding-fee band table, are unreachable. All are retained because they are Missouri's published figures and the cap is an MFB form limit that can change, not a statement about the program. The two run out together: DESE publishes the fee chart and the income ceiling to size 20 alike, the fee chart in two blocks — sizes 1–10 and sizes 11–20 — on the same sheet.
  - The committed handling above the published range — the size-20 row, for the ceiling and the fee band alike — is unreachable twice over. It takes the largest published row, which is the inclusive direction, since ceiling and band edges alike rise with size.
  - Implement must still carry the `min(...)` rule rather than the chart alone, because it is the operative Missouri test and only the form limit hides it.
- Criterion 7's two narrowing branches, rules (D) and (H), carry no scenario because the tests that would decide them are unsourced.
- The part-unit fee column is never selected, because the committed care pattern is Full day or the school-age half day.
- **The R5 Infant cell cannot be distinguished from R4's**, because both groupings publish $58.50. Scenario 47 pins the value both use, and no scenario could tell a mutation swapping the two cells apart.
- **Seven of the twenty rate cells are deliberately left unread**, and the reason is worth stating because it is a trade, not an oversight. Preschool is read in every grouping (Scenarios 1–5) and Infant in four (Scenarios 44–47), **R5's Infant cell going unread** because it shares R4's published $58.50; **School age is read only in Regions 1 and 3**, so Regions 2, 4 and 5 each have an unread full and half cell. The seven are therefore the R5 Infant cell plus those six, and the half-unit fee column is read at `$3.25` alone. Reading any of them requires a school-age child inside the school year, which is the one value path that depends on imputing K-12 enrolment from age (Data Gap 20) — so each such scenario would add another result resting on that imputation, on top of the nine that already do. The judgement made here is that the Infant cells were worth covering because they carry the highest rates and add no gap dependence, while the remaining school-age cells were not worth further Data Gap 20 exposure. A transcription error in one of the seven unread cells would not be caught by this set; **those constants are anchored instead by the quoted workbook rows in Benefit Value**, which is a weaker check than a scenario and is named as such.
- **The full-unit fee bands do not share that constraint, and all eight are read.** A fee band is selected by Eligibility Unit size and adjusted gross income alone, so any Preschool child reads one; the Data Gap 20 trade above applies to the school-age rate cells and the half-unit column, not to this column. Scenarios 48 and 49 close the `$1.00` and `$3.00` bands, which were the two left unread.
- The Transitional Child Care bands are out of scope entirely (see Related Programs).

An `Expense` whose `frequency` is null makes `monthly()` raise, and `Expense.missing_fields()`
does not require `frequency`. The screener form cannot produce one — it requires a frequency and
defaults it to monthly — so the state arises only through the API or a legacy row. The calculator
skips such an expense rather than failing the whole response, forgoing its deduction; no scenario
asserts it.

Every scenario states **raw screener inputs** and lets the calculator derive Missouri adjusted
gross income; none supplies adjusted income directly. All values are monthly, computed under the
committed proxy — Licensed Center, Daytime, 21 care days, provider charging at least the state
maximum, no approved rate differential — and stated as the monthly derivation, with the annual
value the calculator returns and the figure MFB displays alongside each one.

### Scenario 1: Region 1 Dense Urban, preschool child — Eligible, $945.00/month
**What we're checking**: the Region 1 rate is selected from the household's county.
**Expected**: Eligible — `($50.00 − $5.00) × 21 = $945.00`; returns `$11,340` a year, displayed as `$945`/month
**Steps**:
* Location: ZIP `63101`, county `St. Louis City`
* Person 1: born March 1991 (age 35), head of household, employed, wages $2,000/month
* Person 2: born March 2023 (age 3), `relationship` `child` — the eligible child, rule (A)
* Person 3: born June 1990 (age 36), `relationship` `spouse`, no income — in the unit on the household baseline
* Person 4: born March 2011 (age 15), `relationship` `child`, no income — in the unit, and **deliberately not an eligible child**: at 15 they are past the base age limit and hold no observable special-needs status, so they count toward Eligibility Unit size without adding a value term
* Eligibility Unit size **4** — the household baseline; all four members are on the roster and no sourced
  composition rule removes any of them; `household_assets` $500
**Why this matters**: kills a mutation that maps St. Louis City to any other grouping.

### Scenario 2: Region 2 Metro, preschool child — Eligible, $672.00/month
**What we're checking**: Region 2 produces its own distinct rate.
**Expected**: Eligible — `($37.00 − $5.00) × 21 = $672.00`; returns `$8,064` a year, displayed as `$672`/month
**Steps**: as Scenario 1 but Location ZIP `63084`, county `Franklin County`
**Why this matters**: $672.00 is unique to Region 2 under this proxy, so a grouping mix-up fails.

### Scenario 3: Region 3 Urban, preschool child — Eligible, $735.00/month
**What we're checking**: Region 3 produces its own distinct rate.
**Expected**: Eligible — `($40.00 − $5.00) × 21 = $735.00`; returns `$8,820` a year, displayed as `$735`/month
**Steps**: as Scenario 1 but Location ZIP `65806`, county `Greene County`
**Why this matters**: distinguishes Region 3 from Regions 1, 2, 4 and 5.

### Scenario 4: Region 4 Micropolitan, preschool child — Eligible, $577.50/month
**What we're checking**: Region 4 produces its own distinct rate.
**Expected**: Eligible — `($32.50 − $5.00) × 21 = $577.50`; returns `$6,930` a year, displayed as `$578`/month
**Steps**: as Scenario 1 but Location ZIP `65401`, county `Phelps County`
**Why this matters**: Region 4 and Region 5 share an Infant rate, so this pair must be proven on Preschool; the displayed value rounds to $578.

### Scenario 5: Region 5 Rural, preschool child — Eligible, $546.00/month
**What we're checking**: Region 5 as a distinct rate.
**Expected**: Eligible — `($31.00 − $5.00) × 21 = $546.00`; returns `$6,552` a year, displayed as `$546`/month
**Steps**: as Scenario 1 but Location ZIP `65483`, county `Texas County`
**Why this matters**: Region 5 is also the fallback for counties absent from the published lists, so it must be pinned on an age category where it is distinct.

### Scenario 6: income exactly at the Eligibility-Unit-4 maximum — Eligible, $735.00/month
**What we're checking**: the ceiling is inclusive, as "shall not exceed" requires.
**Expected**: Eligible — adjusted gross income $4,019.00 equals the $4,019 ceiling; `($40.00 − $5.00) × 21 = $735.00`; returns `$8,820` a year, displayed as `$735`/month
**Steps**: Region 3 as Scenario 3; Person 1 wages `$4,019/month`; no `medical` expense
**Why this matters**: kills an exclusive comparison at the boundary.

### Scenario 7: income one dollar above the maximum — Ineligible
**What we're checking**: the other side of the same boundary.
**Expected**: Ineligible — criterion 7; adjusted gross income $4,020.00 exceeds $4,019
**Steps**: as Scenario 6 with wages `$4,020/month`
**Why this matters**: with Scenario 6, fixes the ceiling to the exact dollar.

### Scenario 8: health-insurance deduction brings the household under the ceiling — Eligible, $735.00/month
**What we're checking**: the `medical` deduction is applied to gross income.
**Expected**: Eligible — gross $4,100.00 less `medical` $200.00 = $3,900.00, under $4,019; `($40.00 − $5.00) × 21 = $735.00`; returns `$8,820` a year, displayed as `$735`/month
**Steps**: Region 3 as Scenario 3; Person 1 wages `$4,100/month`; `medical` expense `$200/month`
**Why this matters**: kills a mutation that ignores the deduction.

### Scenario 9: same gross income, no deduction — Ineligible
**What we're checking**: that Scenario 8's verdict is caused by the deduction and nothing else.
**Expected**: Ineligible — criterion 7; gross $4,100.00 with no deduction exceeds $4,019
**Steps**: as Scenario 8 with **no** `medical` expense; gross income held constant at `$4,100/month`
**Why this matters**: this is the real control for Scenario 8. Because gross is identical in both, no income-ceiling value can satisfy both scenarios — only an implementation that actually applies the deduction passes.

### Scenario 10: SSI is excluded from Missouri adjusted gross income — Eligible, $735.00/month
**What we're checking**: Missouri's SSI exclusion, from raw streams.
**Expected**: Eligible — wages $3,900.00 plus SSI $700.00, SSI excluded, so adjusted gross income is $3,900.00; `($40.00 − $5.00) × 21 = $735.00`; returns `$8,820` a year, displayed as `$735`/month
**Steps**: Region 3 as Scenario 3; Person 1 wages `$3,900/month`; **Person 3, the `spouse`**, `IncomeStream` type `sSI` `$700/month` — the SSI recipient is deliberately an adult rather than the eligible child, so the exclusion is tested independently of any age rule, and — like every member of the roster under the household baseline — inside the Eligibility Unit, so the stream is counted and then excluded by Missouri's SSI rule, and the special-needs waiver is not engaged
**Why this matters**: an implementation summing all streams reaches $4,600.00 and screens the household out, so the exclusion changes the verdict rather than only the arithmetic.

### Scenario 11: school-year hold, born August — Eligible, $945.00/month
**What we're checking**: a child not yet 5 before August 1 is held at the Preschool rate.
**Expected**: Eligible — Preschool rate applies; `($50.00 − $5.00) × 21 = $945.00`; returns `$11,340` a year, displayed as `$945`/month
**Steps**: Region 1 as Scenario 1; Person 2 born **August 2021**; evaluation date 2026-09-04
**Why this matters**: with Scenario 12, fixes the boundary at birth month August rather than September, killing an off-by-one.

### Scenario 12: school-year hold boundary, born July — Eligible, $518.125/month
**What we're checking**: a child already 5 before August 1 moves to School age.
**Expected**: Eligible — School age, school-year authorization; `($27.00 − $3.25) × 21 + ($36.00 − $5.00) × 5/8 = $498.75 + $19.375 = $518.125`; returns `$6,217` a year, displayed as `$518`/month
**Steps**: as Scenario 11 with Person 2 born **July 2021**; evaluation date 2026-09-04
**Why this matters**: the $426.875 gap from Scenario 11 is the hold's value in Region 1, and the July/August pair pins the boundary exactly. It also rules out the wrong basis: pricing this school-age child at 21 full days would give `($36.00 − $5.00) × 21 = $651.00`, which Missouri's before-and-after-school authorization does not support.

### Scenario 13: Region 3, school-year hold, born August — Eligible, $735.00/month
**What we're checking**: the hold in the grouping where its value is smallest.
**Expected**: Eligible — held at Preschool; `($40.00 − $5.00) × 21 = $735.00`; returns `$8,820` a year, displayed as `$735`/month
**Steps**: Region 3 as Scenario 3; Person 2 born **August 2021**; evaluation date 2026-09-04
**Why this matters**: with Scenario 14 this measures the school-year hold in the one grouping where School age out-pays Preschool, at `+$44.2825` — the narrowest of the five, against $426.875 in Region 1, because Region 3 has the strongest school-age rate — so an implementation that drops the hold shows its smallest error here and still fails.

### Scenario 14: Region 3, born July, School age — Eligible, $690.7175/month
**What we're checking**: the Region 3 school-age authorization, where School age out-pays Preschool.
**Expected**: Eligible — `($34.905 − $3.25) × 21 + ($46.54 − $5.00) × 5/8 = $664.755 + $25.9625 = $690.7175`; returns `$8,288` a year, displayed as `$691`/month
**Steps**: as Scenario 13 with Person 2 born **July 2021**
**Why this matters**: Region 3 is the one grouping whose school-age daily rate ($46.54) beats its Preschool rate ($40.00), yet the monthly value is still lower than Scenario 13's, because school-age care is authorized at the half-day rate. This scenario is what keeps the daily-rate and monthly-value directions from being conflated.

### Scenario 15: an under-18 child's earnings are excluded — Eligible, $735.00/month
**What we're checking**: Missouri's child-earnings exclusion, with attendance imputed from age.
**Expected**: Eligible — wages $3,900.00 plus a 17-year-old's $400.00, the latter excluded, so adjusted gross income is $3,900.00; `($40.00 − $5.00) × 21 = $735.00`; returns `$8,820` a year, displayed as `$735`/month
**Steps**: Region 3 as Scenario 3; **Person 4** (`relationship` `child`) born **October 2008**, so `calc_age` returns 17 at evaluation 2026-09-04, wages `$400/month`; Person 1 wages `$3,900/month`; Eligibility Unit size 4 — Person 4 is on the roster and so in the unit
**Why this matters**: an implementation counting all earners reaches $4,300.00 and screens the household out.

### Scenario 16: the same teenager one month past 18 — Ineligible
**What we're checking**: the exclusion's age boundary, which is where it turns now that attendance is imputed.
**Expected**: Ineligible — criterion 7; **Person 4** born **September 2008** is 18 at evaluation 2026-09-04, so Missouri's under-18 child-earnings exclusion lapses and the $400.00 is counted. Person 4 remains in the Eligibility Unit — the baseline is the household, and Manual 5.6.3(3)'s adult-child exclusion states no test MFB can apply — so the unit stays at **4** and the ceiling at $4,019, which adjusted gross income of `$3,900.00 + $400.00 = $4,300.00` exceeds
**Steps**: as Scenario 15 with Person 4 born **September 2008**; Eligibility Unit size 4
**Why this matters**: one month apart from Scenario 15 with the opposite verdict, so it pins the under-18 cut and kills an off-by-one in the month comparison. Eligibility Unit size is **4** in both halves of the pair, so the verdict is attributable to the child-earnings exclusion alone — no unit-size confound.

### Scenario 17: annual wage converted to monthly at the boundary — Eligible, $735.00/month
**What we're checking**: frequency conversion.
**Expected**: Eligible — `$48,228/year ÷ 12 = $4,019.00/month`, exactly at the ceiling; `($40.00 − $5.00) × 21 = $735.00`; returns `$8,820` a year, displayed as `$735`/month
**Steps**: Region 3 as Scenario 3; Person 1 wages `$48,228` with `frequency` `yearly`
**Why this matters**: kills a mutation in the annual-to-monthly conversion, which a monthly-only set cannot detect.

### Scenario 18: caregiver relative as head — Eligible, $945.00/month
**What we're checking**: `relatedOther` is inside the accepted relationship set.
**Expected**: Eligible — Eligibility Unit size 3 puts $2,000.00 in the $5.00 band (ceiling $3,331); `($50.00 − $5.00) × 21 = $945.00`; returns `$11,340` a year, displayed as `$945`/month
**Steps**: Location ZIP `63101`, county `St. Louis City`; Person 1 born March 1985 (age 41), head of household, an aunt, employed, wages `$2,000/month`; Person 2 born March 2023 (age 3), `relationship` `relatedOther` — **the only member both in criterion 6's accepted set and under 13** (Person 3 is also `relatedOther`, and is excluded by criterion 4's age limit, not by criterion 6); Person 3 born March 2011 (age 15), `relationship` `relatedOther`, no income; Eligibility Unit size 3 — the household baseline, all three members on the roster. The `.050(17)(G)` NPCR shape holds (no accepted-parent relationship on the roster), but under the baseline it changes no membership
**Why this matters**: Missouri's caregiver-relative limb is a real pathway; omitting `relatedOther` would wrongly screen this household out.

### Scenario 19: household member outside the accepted set — Ineligible
**What we're checking**: members outside criterion 6's accepted set are in the Eligibility Unit but are not eligible children.
**Expected**: Ineligible — criteria 4 and 6 together; no member satisfies both. Person 2 is under 13 but `roommate` is outside criterion 6's accepted set; Person 4 is inside the set but 15, past criterion 4's age limit. Eligibility Unit size is **4** — the roommate is in the unit under the household baseline — but with no eligible child there is no value to compute
**Steps**: Region 1 as Scenario 1; Person 2 born March 2023 (age 3), `relationship` `roommate`
**Why this matters**: kills a mutation treating any under-13 member as an eligible child.

### Scenario 20: gross assets exactly at the limit establish a pass — Eligible, $945.00/month
**What we're checking**: `household_assets ≤ $1,000,000` establishes the pass side of criterion 8, inclusively.
**Expected**: Eligible — `household_assets` $1,000,000 does not exceed $1,000,000; `($50.00 − $5.00) × 21 = $945.00`; returns `$11,340` a year, displayed as `$945`/month
**Steps**: as Scenario 1 with `household_assets` `$1,000,000`
**Why this matters**: kills a mutation importing a low state asset limit from a sibling state, which would screen this household out. There is deliberately **no** paired ineligible scenario and none above the limit: criterion 8 is asymmetric because MFB has no debt input, so only a pass can be established, which makes the above-limit branch a data gap rather than a testable one (Data Gap 19).

### Scenario 21: top of the $4.00 fee band — Eligible, $756.00/month
**What we're checking**: the fee-band edge, lower side.
**Expected**: Eligible — adjusted gross income $1,764.00 is the top of the $4.00 band; `($40.00 − $4.00) × 21 = $756.00`; returns `$9,072` a year, displayed as `$756`/month
**Steps**: Region 3 as Scenario 3; Person 1 wages `$1,764/month`
**Why this matters**: with Scenario 22, fixes a band edge to the dollar. Five other scenarios also sit on a band edge rather than mid-band: 22, this scenario's own pair; 25 and 30, which pin the rule-2/rule-3 threshold; and 6 and 17, whose identical $4,019.00 at Eligibility Unit size 4 sits on the ceiling that closes the `$5.00` band. Every scenario outside that set of six sits mid-band.

### Scenario 22: bottom of the $5.00 fee band — Eligible, $735.00/month
**What we're checking**: the fee-band edge, upper side.
**Expected**: Eligible — adjusted gross income $1,765.00 falls in the $5.00 band; `($40.00 − $5.00) × 21 = $735.00`; returns `$8,820` a year, displayed as `$735`/month
**Steps**: as Scenario 21 with wages `$1,765/month`
**Why this matters**: the $21.00 step between Scenarios 21 and 22 is the band boundary.

### Scenario 23: special-needs child, fee waived — Eligible, $1,050.00/month
**What we're checking**: fee precedence rule 1 for a child with special needs.
**Expected**: Eligible — fee `$0`; `($50.00 − $0.00) × 21 = $1,050.00`; returns `$12,600` a year, displayed as `$1,050`/month
**Steps**: Region 1 as Scenario 1; Person 2 born March 2023 (age 3) receiving SSI (`IncomeStream` type `sSI`, `$700/month`, excluded from income per Scenario 10)
**Why this matters**: kills a mutation charging the ordinary fee to a special-needs child. The 25% differential is **not** applied, per the committed proxy.

### Scenario 24: the waiver is per child, not per household — Eligible, $1,995.00/month
**What we're checking**: waiver scope.
**Expected**: Eligible — waived child `($50.00 − $0.00) × 21 = $1,050.00` plus unwaived child `($50.00 − $5.00) × 21 = $945.00`, total `$1,995.00`; returns `$23,940` a year, displayed as `$1,995`/month
**Steps**: Region 1 as Scenario 1; Person 2 born March 2023 (age 3) receiving SSI; **Person 3 restated as `relationship` `child`**, born March 2023 (age 3), no SSI, `disabled` false — the base roster fixes Person 3 as `spouse`, so the value must be overridden for them to be an eligible child. Eligibility Unit size stays **4**
**Why this matters**: a household-wide waiver yields $2,100.00, so this scenario discriminates the two readings.

### Scenario 25: income inside the chart's $1.00-per-year band — Eligible, $1,049.9167/month
**What we're checking**: fee precedence rule 2 on the chart's published band.
**Expected**: Eligible — adjusted gross income $802.00 is exactly the `$1.00 Per Year` band ceiling for size 4, so the household owes `$1` annually; `($50.00 × 21) − ($1 ÷ 12) = $1,050.00 − $0.0833 = $1,049.9167`; returns `$12,599` a year, displayed as `$1,050`/month
**Steps**: Region 1 as Scenario 1; Person 1 wages `$802/month` — the band ceiling to the dollar
**Why this matters**: the band has no daily fee figure at all, so an implementation that looks for one either errors or silently charges `$0` and returns $1,050.00. Only the annual-to-monthly conversion produces $1,049.9167.

### Scenario 26: only income is Temporary Assistance — Eligible, $1,049.9167/month
**What we're checking**: fee precedence rule 2, first limb.
**Expected**: Eligible — `($50.00 × 21) − ($1 ÷ 12) = $1,050.00 − $0.0833 = $1,049.9167`; returns `$12,599` a year, displayed as `$1,050`/month
**Steps**: Region 1 as Scenario 1; Person 1 `IncomeStream` type `cashAssistance` `$1,000/month` as the household's only income
**Why this matters**: $1,000 is **above** the size-4 `$1.00 Per Year` band ceiling of $802, so the chart limb cannot fire and only the Temporary Assistance limb reaches rule 2. Without that limb the $0.75 band governs and the value is `($50.00 − $0.75) × 21 = $1,034.25`, so the two readings give different answers.

### Scenario 27: two children in the $1/year band — Eligible, $2,099.9167/month
**What we're checking**: the annual fee is a single household obligation.
**Expected**: Eligible — `2 × ($50.00 × 21) − ($1 ÷ 12) = $2,100.00 − $0.0833 = $2,099.9167`; returns `$25,199` a year, displayed as `$2,100`/month
**Steps**: Region 1 as Scenario 1; Person 2 born March 2023 (age 3), `relationship` `child`; **Person 3 restated as `relationship` `child`**, born March 2023 (age 3) — overriding the base roster's `spouse`; Person 1 wages `$700/month`; Eligibility Unit size stays **4**
**Why this matters**: an implementation subtracting `$1 ÷ 12` per child yields $2,099.8333, and one charging a daily fee per child yields far less. Only a single household subtraction matches.

### Scenario 28: waiver takes precedence over the $1/year band — Eligible, $1,050.00/month
**What we're checking**: rule 1 outranks rule 2 when both would apply.
**Expected**: Eligible — the only child is waived, so no fee of any kind is subtracted; `($50.00 − $0.00) × 21 = $1,050.00`; returns `$12,600` a year, displayed as `$1,050`/month
**Steps**: Region 1 as Scenario 1 (Person 4 retained, so **Eligibility Unit size 4**); Person 1 wages `$700/month`; Person 2 born March 2023 (age 3) receiving SSI (`IncomeStream` type `sSI`, `$700/month`, excluded from income); Person 2 is the only eligible child. Size 4 is required for the test to bite: the `$1.00 Per Year` band tops at $802 at size 4 but at only $674 at size 3, so at size 3 the $700 would fall in the `$0.50` band and rule 2 would never compete
**Why this matters**: an implementation applying rule 2 as well returns $1,049.9167. The precedence must be strict.

### Scenario 29: mixed household in the $1/year band — Eligible, $2,099.9167/month
**What we're checking**: rule 1 per child, rule 2 once per household, together.
**Expected**: Eligible — the waived child contributes no fee; the unwaived child triggers the single household obligation; `2 × ($50.00 × 21) − ($1 ÷ 12) = $2,099.9167`; returns `$25,199` a year, displayed as `$2,100`/month
**Steps**: Region 1 as Scenario 1; Person 1 wages `$700/month`; Person 2 born March 2023 (age 3), `relationship` `child`, receiving SSI; **Person 3 restated as `relationship` `child`**, born March 2023 (age 3), no SSI — overriding the base roster's `spouse`; Eligibility Unit size stays **4**
**Why this matters**: with Scenarios 27 and 28 this fixes the interaction — the household fee is neither doubled nor waived away by one child's waiver.

### Scenario 30: the $0.50 fee band — Eligible, $1,039.50/month
**What we're checking**: the lowest daily fee band above the annual-dollar band.
**Expected**: Eligible — adjusted gross income $803.00 is the **first dollar** of the size-4 $0.50 band ($803–$962), one dollar above Scenario 25's band ceiling; `($50.00 − $0.50) × 21 = $1,039.50`; returns `$12,474` a year, displayed as `$1,040`/month
**Steps**: Region 1 as Scenario 1; Person 1 wages `$803/month` — one dollar above Scenario 25, the only difference across the pair
**Why this matters**: with Scenario 25 this pins the rule-2/rule-3 threshold to the dollar — $802 annual, $803 daily. A mutation placing the cut anywhere else in that range fails one of the pair, and a mutation collapsing the $0.50 band into the annual band or into the $0.75 band fails here.

### Scenario 31: child aged 12 at the birth-month edge — Eligible, $518.125/month
**What we're checking**: `BASE_AGE_LIMIT = 13` and `calc_age`'s month granularity.
**Expected**: Eligible — born October 2013, so at evaluation 2026-09-04 `calc_age` is 12; School age, school year; `($27.00 − $3.25) × 21 + ($36.00 − $5.00) × 5/8 = $518.125`; returns `$6,217` a year, displayed as `$518`/month
**Steps**: Region 1 as Scenario 1; Person 2 born **October 2013**; evaluation date 2026-09-04
**Why this matters**: with Scenario 32 this pins the age limit to 13 rather than anywhere between 6 and 13, and pins the boundary to the first of the birth month.

### Scenario 32: child aged 13 at the birth-month edge — Ineligible
**What we're checking**: the other side of the age boundary.
**Expected**: Ineligible — criterion 4; born September 2013, so at evaluation 2026-09-04 `calc_age` is 13, and no observable special-needs status extends it
**Steps**: as Scenario 31 with Person 2 born **September 2013**; `disabled`, `long_term_disability`, `visually_impaired` and `student` all **false**, no SSI — every special-needs and school signal cleared, so only the age differs
**Why this matters**: one month apart from Scenario 31 with the opposite verdict, so an off-by-one in the month comparison fails.

### Scenario 33: Eligibility Unit size changes the fee band at the same income — Eligible, $798.00/month
**What we're checking**: the fee chart and the income ceiling are keyed on Eligibility Unit size, not fixed at size 4.
**Expected**: Eligible — at **Eligibility Unit size 2**, adjusted gross income $900.00 sits in the $2.00 band ($873–$981); `($40.00 − $2.00) × 21 = $798.00`; returns `$9,576` a year, displayed as `$798`/month
**Steps**: Location ZIP `65806`, county `Greene County`; Person 1 born March 1991 (age 35), head of household, employed, wages `$900/month`; Person 2 born March 2023 (age 3), `relationship` `child`; Eligibility Unit size **2** — limbs (A) and (B) only; `household_assets` $500
**Why this matters**: the identical $900 income at size 4 falls in the $0.50 band and would yield $829.50. Scenario 37 is the only other size-varying valued scenario; together they exercise the size-2, size-3 and size-4 fee columns, so an implementation hardcoding the size-4 column fails both.

### Scenario 34: special-needs waiver via a verified disability — Eligible, $1,050.00/month
**What we're checking**: the `has_disability` limb of the special-needs status subset.
**Expected**: Eligible — fee `$0`; `($50.00 − $0.00) × 21 = $1,050.00`; returns `$12,600` a year, displayed as `$1,050`/month
**Steps**: Region 1 as Scenario 1; Person 2 born March 2023 (age 3), `disabled` true, **no SSI stream**
**Why this matters**: Scenarios 23, 24, 28 and 29 all take the SSI limb; this is the minimal `has_disability` case, isolated from criterion 4's age extension, so it separates the two waiver limbs cleanly.

### Scenario 35: school-age child outside the school year — Eligible, $651.00/month
**What we're checking**: the May–August treatment for a school-age child.
**Expected**: Eligible — outside September–April the before-and-after-school pattern does not apply, so the default Full day governs; `($36.00 − $5.00) × 21 = $651.00`; returns `$7,812` a year, displayed as `$651`/month
**Steps**: Region 1 as Scenario 1; Person 2 born July 2021; **evaluation date 2026-08-15**, at which `calc_age` returns 5 (School age) and the month is outside the September–April window
**Why this matters**: with Scenario 12 this pins MFB's committed September-through-April window, which the spec labels an inference from Manual 7.9's five-day allowance rather than a stated span. An implementation applying the half-day plus `5/8` pattern all twelve months returns $518.125 here and fails.

### Scenario 36: special-needs age extension past 13 — Eligible, $762.0925/month
**What we're checking**: criterion 4's 13-through-17 limb as a **pass**, not merely a fail.
**Expected**: Eligible — born March 2012 (age 14), `disabled` true, so the special-needs extension applies; School age, school year, fee waived; `($34.905 − $0.00) × 21 + ($46.54 − $0.00) × 5/8 = $733.005 + $29.0875 = $762.0925`; returns `$9,145` a year, displayed as `$762`/month
**Steps**: Region 3 as Scenario 3; Person 2 born **March 2012**, `disabled` true; **evaluation date 2026-09-04**, inside the September–April school year
**Why this matters**: Scenario 32 proves only that 13 without status fails. This proves the extension actually admits a 14-year-old, and an implementation that drops the extension entirely returns Ineligible here.

### Scenario 37: a member outside every `.050(17)` limb changes the fee band — Eligible, $824.25/month
**What we're checking**: the committed Eligibility Unit model against the closed-enumeration reading it discriminates.
**Expected**: Eligible — Eligibility Unit size 3 under the household baseline, so adjusted gross income $900.00 sits in the size-3 `$0.75` band ($809–$943); `($40.00 − $0.75) × 21 = $824.25`; returns `$9,891` a year, displayed as `$824`/month
**Steps**: Location ZIP `65806`, county `Greene County` — Region 3 Urban; Person 1 born March 1991 (age 35), head of household, employed, wages `$900/month`; Person 2 born March 2023 (age 3), `relationship` `child` — the eligible child; Person 3 born March 1988 (age 38), `relationship` `roommate`, **no income**; `household_assets` $500
**Why this matters**: this is the only scenario that discriminates the committed unit model. Person 3 falls under no `.050(17)` limb, so a closed-enumeration reading of `.050(17)` would put the unit at 2, where $900.00 sits in the size-2 `$2.00` band and the value is `($40.00 − $2.00) × 21 = $798.00`. The household baseline gives $824.25. A $26.25 gap, and because Person 3 has no income there is nothing to confound it, so the direction is unambiguous. It does **not** also test the roster against `household_size`: the screener syncs the two, so they cannot disagree (see criterion 7).

### Scenario 38: the daily fee is charged per child, not once per household — Eligible, $1,890.00/month
**What we're checking**: fee-precedence rule 3's per-child scope, with two unwaived children.
**Expected**: Eligible — two eligible children, neither waived, adjusted gross income $2,000.00 at Eligibility Unit size 4 giving the `$5.00` full-unit fee; `2 × ($50.00 − $5.00) × 21 = $1,890.00`; returns `$22,680` a year, displayed as `$1,890`/month
**Steps**: Region 1 as Scenario 1; Person 1 wages `$2,000/month`; Person 2 born March 2023 (age 3), `relationship` `child`, no SSI, `disabled` false; **Person 3 restated as `relationship` `child`**, born March 2023 (age 3), no SSI, `disabled` false — overriding the base roster's `spouse`; Person 4 retained, so Eligibility Unit size stays **4**
**Why this matters**: Scenario 24 cannot make this discrimination — with one child waived, per-child and per-household arithmetic coincide at $1,995.00. Here they separate: charging the daily fee once per household yields `2 × ($50.00 × 21) − ($5.00 × 21) = $1,995.00`, so a $105.00 gap kills the mutation. The chart's own heading is "DAILY SLIDING FEE PER CHILD IN CARE".

### Scenario 39: special-needs extension at its upper edge, still eligible — Eligible, $589.50/month
**What we're checking**: criterion 4's extension limb runs **to under 18**, pinned at the birth-month edge.
**Expected**: Eligible — born October 2008, so at evaluation 2026-09-04 `calc_age` is 17; `disabled` true waives the fee; School age inside the school year, `($27.00 − $0.00) × 21 + ($36.00 − $0.00) × 5/8 = $567.00 + $22.50 = $589.50`; returns `$7,074` a year, displayed as `$590`/month
**Steps**: Region 1 as Scenario 1; Person 2 born **October 2008**, `disabled` true; evaluation date 2026-09-04
**Why this matters**: Scenario 36 proves only that a 14-year-old is admitted. Nothing pinned the top of the band, so a mutation running the extension to 19 — or stopping it at 16 — survived the whole set.

### Scenario 40: one month past the special-needs extension — Ineligible
**What we're checking**: the upper edge as a fail.
**Expected**: Ineligible — criterion 4; born September 2008, so `calc_age` is 18 at evaluation 2026-09-04, and the extension limb reaches only to under 18 regardless of `disabled`
**Steps**: as Scenario 39 with Person 2 born **September 2008**; `disabled` stays **true** and `student` is **false**, so only the age differs
**Why this matters**: one month apart from Scenario 39 with the opposite verdict, and `disabled` stays true across the pair, so the verdict is attributable to the age edge alone rather than to the status.

### Scenario 41: the school-year pattern still applies in April — Eligible, $518.125/month
**What we're checking**: the closing edge of MFB's committed September–April window.
**Expected**: Eligible — born March 2019 so `calc_age` is 7 at evaluation 2026-04-15, inside the window; `($27.00 − $3.25) × 21 + ($36.00 − $5.00) × 5/8 = $498.75 + $19.375 = $518.125`; returns `$6,217` a year, displayed as `$518`/month
**Steps**: Region 1 as Scenario 1; Person 2 born **March 2019**; **evaluation date 2026-04-15**
**Why this matters**: Scenarios 12 and 35 bound only the window's opening. Nothing tested its close, so a mutation running the window through May survived.

### Scenario 42: the school-year pattern lapses in May — Eligible, $651.00/month
**What we're checking**: the other side of the April/May edge.
**Expected**: Eligible — same child on 1 May, outside the window, so the default Full day governs; `($36.00 − $5.00) × 21 = $651.00`; returns `$7,812` a year, displayed as `$651`/month
**Steps**: as Scenario 41 with **evaluation date 2026-05-01**
**Why this matters**: with Scenario 41 this pins the window's close to 30 April, a $132.875 swing. Note the window itself is an MFB inference from Manual 7.9's five-day allowance, not a sourced date range — these two scenarios pin what MFB committed, not what Missouri published.

### Scenario 43: a child who has just turned 2 is Preschool — Eligible, $945.00/month
**What we're checking**: the Infant/Preschool category boundary, on the Preschool side of DESE's overlapping endpoints.
**Expected**: Eligible — born September 2024, so at evaluation 2026-09-04 `calc_age` returns 2 and the committed reading puts the shared endpoint in Preschool; `($50.00 − $5.00) × 21 = $945.00`; returns `$11,340` a year, displayed as `$945`/month
**Steps**: Region 1 as Scenario 1; Person 2 born **September 2024**; evaluation date 2026-09-04
**Why this matters**: with Scenario 44 this is the only pair that pins the age-2 cut. Without it a mutation running Infant to age 3 passes every other scenario in the set, because the nearest neighbours are age 1 and age 3, and it would overpay this household by $966.00 a month.

### Scenario 44: one month younger is still Infant — Eligible, $1,911.00/month
**What we're checking**: the other side of the same boundary, at the birth-month edge.
**Expected**: Eligible — born October 2024, so at evaluation 2026-09-04 `calc_age` returns 1 (the month comparison has not yet turned); Infant, `($96.00 − $5.00) × 21 = $1,911.00`; returns `$22,932` a year, displayed as `$1,911`/month
**Steps**: as Scenario 43 with Person 2 born **October 2024**
**Why this matters**: one month apart from Scenario 43 with a $966.00 swing, so the pair pins both the category cut and `calc_age`'s month granularity at the same edge. Infant is the highest-paying category in every grouping, so an off-by-one here is the largest single-child error the value model can make.

### Scenario 45: Region 2 infant — Eligible, $1,398.60/month
**What we're checking**: the Region 2 Infant rate, which no other scenario reads.
**Expected**: Eligible — `($71.60 − $5.00) × 21 = $1,398.60`; returns `$16,783` a year, displayed as `$1,399`/month
**Steps**: as Scenario 2 (Region 2 Metro, ZIP `63084`, county `Franklin County`); Person 2 born **March 2025**, so `calc_age` returns 1 at evaluation 2026-09-04
**Why this matters**: Infant was pinned in Region 1 alone, so a transcription error in any other grouping's Infant cell changed no scenario's value. Infant is the highest-paying category in every grouping, which makes these the costliest cells to get wrong.

### Scenario 46: Region 3 infant — Eligible, $1,554.00/month
**What we're checking**: the Region 3 Infant rate.
**Expected**: Eligible — `($79.00 − $5.00) × 21 = $1,554.00`; returns `$18,648` a year, displayed as `$1,554`/month
**Steps**: as Scenario 3 (Region 3 Urban, ZIP `65806`, county `Greene County`); Person 2 born **March 2025**
**Why this matters**: completes the Infant row alongside Scenarios 44, 45 and 47; Region 3's $79.00 is distinct from every other grouping's Infant rate, so a grouping mix-up inside the Infant category fails here.

### Scenario 47: Region 4 infant — Eligible, $1,123.50/month
**What we're checking**: the Infant rate Regions 4 and 5 share.
**Expected**: Eligible — `($58.50 − $5.00) × 21 = $1,123.50`; returns `$13,482` a year, displayed as `$1,124`/month
**Steps**: as Scenario 4 (Region 4 Micropolitan, ZIP `65401`, county `Phelps County`); Person 2 born **March 2025**
**Why this matters**: Regions 4 and 5 publish the same $58.50 Infant rate, so this pins the value both groupings use. No scenario can distinguish the two cells from each other — that limit is stated in Known scenario gaps rather than papered over with a second scenario that would assert the same number.

### Scenario 48: the $1.00 fee band — Eligible, $1,029.00/month
**What we're checking**: the `$1.00` full-unit sliding-fee amount, which no other scenario reads.
**Expected**: Eligible — adjusted gross income $1,200.00 sits inside the size-4 `$1.00` band ($1,123 – $1,283), above the `$1.00 Per Year` ceiling of $802 so precedence rule 3 governs; `($50.00 − $1.00) × 21 = $1,029.00`; returns `$12,348` a year, displayed as `$1,029`/month
**Steps**: as Scenario 1 (Region 1, ZIP `63101`, county `St. Louis City`, Eligibility Unit **4**) but Person 1's wages **$1,200/month**
**Why this matters**: the `$1.00` band was one of two fee constants no scenario read. It needs no school-age child — a band is selected by unit size and income alone — so it closes a constant gap without adding another result that rests on the Data Gap 20 K-12 imputation. $1,029.00 is asserted by no other scenario, so a transcription error in this band row fails here.

### Scenario 49: the $3.00 fee band — Eligible, $987.00/month
**What we're checking**: the `$3.00` full-unit sliding-fee amount, the other previously unread band.
**Expected**: Eligible — adjusted gross income $1,500.00 sits inside the size-4 `$3.00` band ($1,444 – $1,604); `($50.00 − $3.00) × 21 = $987.00`; returns `$11,844` a year, displayed as `$987`/month
**Steps**: as Scenario 1 (Region 1, ZIP `63101`, county `St. Louis City`, Eligibility Unit **4**) but Person 1's wages **$1,500/month**
**Why this matters**: completes the full-unit fee column — all eight bands are now read. Paired with Scenario 48 it also shows the fee moving with income while every other input is held, so a mutation that keyed the band off the wrong column of the chart fails on one or both.

### Scenario 50: the fee band at an Eligibility Unit of five — Eligible, $1,008.00/month
**What we're checking**: the sliding-fee band is read from the household's own size column at a size above four.
**Expected**: Eligible — at **Eligibility Unit size 5**, adjusted gross income $1,600.00 sits in the size-5 `$2.00` band ($1,489 – $1,674); `($50.00 − $2.00) × 21 = $1,008.00`; returns `$12,096` a year, displayed as `$1,008`/month
**Steps**: Region 1 as Scenario 1; Person 1 wages `$1,600/month`; Person 5 added, born **March 2010** (age 16), `relationship` `child`, no income — so the roster is five and no composition rule removes any of them; `household_assets` $500
**Why this matters**: every other valued scenario sits at Eligibility Unit size 2, 3 or 4, so nothing exercised the chart above the size-4 column and an implementation carrying only the three transcribed columns would have had no row to read. The income is chosen so the neighbouring columns give different answers that are *also* wrong in a visible way: the same $1,600.00 reads the `$3.00` band at size 4 and the `$1.00` band at size 6, worth $987.00 and $1,029.00 — each of which is another scenario's committed value, so an off-by-one in the column index fails here rather than coinciding with a passing result.

### Scenario 51: St. Louis County is Region 1 — Eligible, $945.00/month
**What we're checking**: the county normalization committed in Benefit Value, on the class of difference an exception list misses.
**Expected**: Eligible — `St. Louis County` normalises to DESE's `St Louis` and selects Region 1 Dense Urban; `($50.00 − $5.00) × 21 = $945.00`; returns `$11,340` a year, displayed as `$945`/month
**Steps**: as Scenario 1 but Location ZIP `63011`, county **`St. Louis County`**
**Why this matters**: MFB's county strings differ from DESE's by a trailing "County", and four of them differ by a period as well — `St. Charles County`, `St. Louis County`, `St. Francois County` and `St. Clair County`. Two of those four are Region 1. An implementation that strips the suffix and then patches the three obvious spellings (`St. Louis City`, `Ste. Genevieve County`, `DeKalb County`) leaves this household unmatched, so it takes the Region 5 default and is priced at `($31.00 − $5.00) × 21 = $546.00` — a $399.00 monthly understatement on one of the state's most populous counties, silently. **Scenario 1 cannot catch it**, because `St. Louis City` is one of the three such an exception list would have covered. This scenario asserts the same $945.00 as Scenario 1 and is deliberately kept alongside it: the two pin different rules, and only this one discriminates the normalization.

## Research Sources

| Snapshot | Tier | Title | URL | Retrieved |
|---|---|---|---|---|
| `2026-09-03--csr-5-25-200-child-care-subsidy` | 1 | 5 CSR 25-200 — Child Care Subsidy (Office of Childhood), CSR edition stamped 6/30/25 | https://www.sos.mo.gov/cmsimages/adrules/csr/current/5csr/5c25-200.pdf | 2026-09-03 |
| `2026-09-03--dese-child-care-subsidy-brochure` | 1 | DESE Child Care Subsidy Brochure (06.29.2026) | https://dese.mo.gov/sites/g/files/zuston521/files/media/pdf/2026/07/Child%20Care%20Subsidy%20Brochure%2006.29.2026.pdf | 2026-09-03 |
| `2026-09-03--dese-child-care-subsidy-families` | 1 | DESE — Child Care Subsidy Information for Families | https://dese.mo.gov/childhood/child-care-subsidy/families | 2026-09-03 |
| `2026-09-03--dese-child-care-subsidy-payments` | 1 | DESE — Child Care Subsidy Payments (rate structure and Subsidy Rate Enhancements) | https://dese.mo.gov/childhood/child-care-subsidy/payments | 2026-09-03 |
| `2026-09-03--dese-child-care-subsidy-program-information` | 1 | DESE — Child Care Subsidy Program Information (waitlist notice) | https://dese.mo.gov/childhood/child-care-subsidy/child-care-subsidy-program-information | 2026-09-03 |
| `2026-09-03--dese-child-care-subsidy-providers` | 1 | DESE — Child Care Subsidy Providers (sliding fee range and enhanced-rate eligibility) | https://dese.mo.gov/childhood/child-care-subsidy/providers | 2026-09-03 |
| `2026-09-03--dese-child-care-subsidy-rates-and-sliding-fees` | 1 | DESE — Child Care Subsidy Rates and Sliding Fees (the 25% special-needs rate differential and the payment formula) | https://dese.mo.gov/childhood/child-care-subsidy/child-care-subsidy-rates-and-sliding-fees | 2026-09-03 |
| `2026-09-03--dese-eligibility-policy-manual-may-2026` | 1 | DESE Child Care Subsidy Eligibility Policy Manual, REVISED MAY 2026 (23 pp.) | https://dese.mo.gov/sites/g/files/zuston521/files/media/pdf/2026/05/Child%20Care%20Subsidy%20Eligibility%20Policy%20Manual_May%202026_0.pdf | 2026-09-03 |
| `2026-09-03--dese-income-limits-and-sliding-fee-chart` | 1 | DESE Child Care Eligibility Income Guidelines and Sliding Fee Chart (asset updated 6.29.26; footer 'Updated 7/01/2026') | https://dese.mo.gov/sites/g/files/zuston521/files/media/pdf/2026/07/Income%20Elig%20_Updated%206.29.26.pdf | 2026-09-03 |
| `2026-09-03--dese-legacy-manual-2010-020-child-with-special-needs` | 1 | DESE legacy web manual 2010.020.00 CHILD WITH SPECIAL NEEDS (SUPERSEDED by `2026-09-03--dese-eligibility-policy-manual-may-2026` — captured as the stale side of a logged source conflict) | https://dese.mo.gov/childhood/quality-programs/child-care-subsidy/child-care-manual/2010/020/00 | 2026-09-03 |
| `2026-09-03--dese-legacy-manual-2010-045-income-eligibility-guidelines` | 1 | DESE legacy web manual 2010.045.00 INCOME ELIGIBILITY GUIDELINES (SUPERSEDED by `2026-09-03--dese-eligibility-policy-manual-may-2026` Manual 4.7 plus `2026-09-03--dese-income-limits-and-sliding-fee-chart` — the page PolicyEngine cites) | https://dese.mo.gov/childhood/quality-programs/child-care-subsidy/child-care-manual/2010/045/00 | 2026-09-03 |
| `2026-09-03--dese-subsidy-family-eligibility-flyer` | 1 | DESE Child Care Subsidy Program for Families — application checklist flyer (05-29-2026) | https://dese.mo.gov/sites/g/files/zuston521/files/media/pdf/2026/06/Subsidy%20Family%20Eligibility%20Flyer%2005-29-2026.pdf | 2026-09-03 |
| `2026-09-03--dese-subsidy-provider-rates-2025-held-harmless` | 1 | DESE 2025 Rates Held Harmless 2.0 — subsidy provider rate workbook (sheets: Daytime Rates 2025, EW Rates 2025, Breakdown Of Counties) | https://dese.mo.gov/sites/g/files/zuston521/files/media/file/2025/12/2025%20Rates%20Held%20Harmless%202.0.xlsx | 2026-09-03 |
| `2026-09-03--mo-500-3469-child-care-subsidy-application` | 1 | MO 500-3469 — Application for Child Care Subsidy for Children and Families (rev. 02/26) | https://dese.mo.gov/sites/g/files/zuston521/files/media/pdf/2026/04/MO_500_3469_Application_for_Child_Care_Subsidy_for_children_and_families_02_26_Accessible_AOD.pdf | 2026-09-03 |
| `2026-09-03--mo-acf-118-ccdf-state-plan-ffy2025-2027-amendment-2` | 1 | Missouri ACF-118 CCDF State Plan FFY 2025-2027, Amendment #2 — Approved by ACF 3.26.2026 (191 pp.) | https://dese.mo.gov/sites/g/files/zuston521/files/media/pdf/2026/04/ACF-118%20CCDF%20FFY%202025-2027%20For%20Missouri%20-%20Approved%203.26.2026.pdf | 2026-09-03 |
| `2026-09-03--mo-child-welfare-manual-s3c2s5-protective-services-child-care` | 1 | MO Child Welfare Manual, Section 3 Chapter 2 Subsection 5 — Protective Services Child Care Subsidy Authorizations for FCS Cases | https://dssmanuals.mo.gov/child-welfare-manual/section-3-chapter-2-family-centered-services-subsection-5-protective-services-child-care-subsidy-authorizations-for-family-centered-services-cases/ | 2026-09-03 |
| `2026-09-03--moreg-v51n12-june-2026-emergency-amendment` | 1 | Missouri Register Vol. 51 No. 12 (June 15, 2026) — EMERGENCY AMENDMENT and PROPOSED AMENDMENT to 5 CSR 25-200.060 | https://www.sos.mo.gov/CMSImages/AdRules/moreg/2026/v51n12June15/v51n12.pdf | 2026-09-03 |
| `2026-09-04--dese-subsidy-monthly-report-july-2026` | 1 | DESE Child Care Subsidy Monthly Report, July 2026 (5 pp.; database as of August 10, 2026) | https://dese.mo.gov/sites/g/files/zuston521/files/media/pdf/2026/08/Subsidy%20Monthly%20Report%20July%202026.pdf | 2026-09-04 |
| `2026-09-03--45-cfr-98-20-lii` | 2 | 45 CFR 98.20 — A child's eligibility for child care services (Cornell LII) | https://www.law.cornell.edu/cfr/text/45/98.20 | 2026-09-03 |
| `2026-09-03--lii-5-csr-25-200-060-quotation-bridge` | 2 | 5 CSR 25-200.060 Eligibility and Authorization for Child Care Subsidy (Cornell LII) — TIER 2 QUOTATION BRIDGE | https://www.law.cornell.edu/regulations/missouri/5-CSR-25-200-060 | 2026-09-03 |
