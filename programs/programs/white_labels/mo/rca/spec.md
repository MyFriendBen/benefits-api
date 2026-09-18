# Refugee Cash Assistance (MO) — Program Spec

- **Program key**: `mo_rca` (`programs/programs/white_labels/mo/rca`, class `MoRca`)
- **Base federal program**: Refugee Cash Assistance (ORR, 45 CFR part 400 subpart E — public/private RCA)
- **White label**: MO
- **Engine**: MFB custom
- **Added to MFB**: not yet added
- **Spec last updated**: 2026-09-10
- **Sources verified as of**: 2026-09-10

## Covered Eligibility Criteria

Criteria 1, 2 and 4 are gates and must all hold. Criterion 3 is the sourced carve-out to criterion
2's SSI limb; because MFB observes SSI *receipt* rather than SSI *eligibility*, it requires no
separate implementation — see its note. Criterion 5 is satisfied by construction. Criterion 6
determines the assistance unit against which criterion 4 and the benefit value are evaluated.

1. **Eligibility for refugee cash assistance is limited to those who meet the immigration status
   and identification requirements of 45 CFR part 400 subpart D, or who are the dependent
   children of, and part of the same family unit as, individuals who meet those requirements.**
   - Evaluation scope: `config`
   - Captured via: `Program.legal_status_required` = `["refugee", "otherWithWorkPermission", "gc_5less"]` (config)
   - Implementation note: `legal_status_required` is a screen-level filter over MFB's six
     user-selected statuses; it is the only status mechanism available and does not verify a
     qualifying ORR status. `refugee` is MFB's merged Refugee/Asylee bucket;
     `otherWithWorkPermission` is the broad "Other Lawful" bucket covering the relevant lawful
     and parole categories; `gc_5less` is included to reach the § 400.43(a)(6) pathway — a person
     admitted for permanent residence who previously held a qualifying status — for whom a green
     card under five years is the recently-arrived case. `gc_5less` is over-inclusive: it also
     covers ordinary recent LPRs who are not RCA-eligible. `gc_5plus`, `citizen`, and
     `non_citizen` are excluded. That over-inclusiveness is a limitation of the config filter —
     the six statuses MFB collects do not map one-to-one onto the ORR-eligible categories — and
     not a missing screener input, so it is recorded here rather than as a data gap. The
     administering agency confirms the applicant's exact status at intake.
     **On the five-year bar:** `gc_5less` is guarded in the repo —
     `test_bare_gc_5less_is_not_claimed_by_a_bar_subject_program`
     (`programs/management/commands/tests/test_five_year_bar_legal_statuses.py`) forbids the bare
     label on bar-subject programs. RCA is **not** in that test's `BAR_SUBJECT_PROGRAMS` and must
     not be added: § 400.43(a)(6) above affirmatively makes an LPR who previously held a
     qualifying status ORR-eligible, granting the eligibility the bar would otherwise remove.
   - Source: 45 CFR 400.53(a)(3) — "Meet immigration status and identification requirements in subpart D of this part or are the dependent children of, and part of the same family unit as, individuals who meet the requirements in subpart D, subject to the limitation in § 400.208 with respect to nonrefugee children" — [snapshot `2026-08-31--45-cfr-400-53`](../../../sources/mo/mo_rca/2026-08-31--45-cfr-400-53/), accessed 2026-08-31
   - Source: 45 CFR 400.43(a)(2) — "Admitted as a refugee under section 207 of the Act;" — [snapshot `2026-08-31--45-cfr-400-43`](../../../sources/mo/mo_rca/2026-08-31--45-cfr-400-43/), accessed 2026-08-31
   - Source: 45 CFR 400.43(a)(6) — "Admitted for permanent residence, provided the individual previously held one of the statuses identified above." — [snapshot `2026-08-31--45-cfr-400-43`](../../../sources/mo/mo_rca/2026-08-31--45-cfr-400-43/), accessed 2026-08-31

2. **Eligibility is limited to those who are ineligible for TANF, SSI, OAA, AB, APTD, and AABD
   programs.** In Missouri only the TANF and SSI limbs operate; the OAA, AB, APTD and AABD limbs
   apply only in Guam, Puerto Rico, and the Virgin Islands. The test is applied to the RCA
   applicant and their case, not to the wider household — separate cases within one household may
   be served under different programs.
   - Evaluation scope: `member`
   - Captured via: `type` (`IncomeStream`, CharField) value `sSI`, read per member via accessor `HouseholdMember.calc_gross_income(frequency, ["sSI"])`; `type` (`IncomeStream`, CharField) value `cashAssistance`, read per member via accessor `HouseholdMember.calc_gross_income(frequency, ["cashAssistance"])`
   - Implementation note: a member with a reported `sSI` payment, or a reported `cashAssistance`
     payment, is removed from their own RCA case; other members and other cases in the same
     household are unaffected. `cashAssistance` is the screener's TANF income option and
     `cashAssistanceOther` is any other cash aid, so only the former evidences TANF receipt —
     reuse `receipt.TANF_INCOME_TYPE` and `receipt.SSI_INCOME_TYPE`
     (`programs/framework/pe_dependencies/receipt.py`) rather than repeating the literals, and
     follow `receipt.member_reports_ssi_amount()` for the per-member read; no TANF twin of that
     helper exists yet, so add one beside it. Both limbs are read per member because the rule
     applies per case, which a screen-level check cannot express: `CurrentBenefit` is
     household-scoped and names no recipient, so a household that ticks a tile without reporting
     an amount identifies nobody and removes nobody — the inclusive direction. What remains
     unobservable is TANF *eligibility* for a member who reports no TANF income, and TANF
     assistance-unit membership; see Data Gap 3. Do not use `Screen.has_benefit("tanf")` or
     `has_benefit("ssi")` — `has_benefit` is an exact `name_abbreviated` read, so a bare `"tanf"`
     literal does not resolve against Missouri's `mo_tanf` row. Use `Screen.has_base_benefit(name)`
     if household-level receipt is ever needed.
   - Source: 45 CFR 400.53(a)(2) — "Are ineligible for TANF, SSI, OAA, AB, APTD, and AABD programs" — [snapshot `2026-08-31--45-cfr-400-53`](../../../sources/mo/mo_rca/2026-08-31--45-cfr-400-53/), accessed 2026-08-31
   - Source: 45 CFR 400.51(b)(2) — "OAA, AB, APTD, or AABD. In Guam, Puerto Rico, and the Virgin Islands—" — [snapshot `2026-08-31--45-cfr-400-51`](../../../sources/mo/mo_rca/2026-08-31--45-cfr-400-51/), accessed 2026-08-31
   - Source: ORR-PL-21-04 § I.A — "A client may not receive federal cash assistance from two programs (e.g., RCA and SSI) for the same time period." — [snapshot `2026-09-01--orr-pl-21-04-public-private-rca`](../../../sources/mo/mo_rca/2026-09-01--orr-pl-21-04-public-private-rca/), accessed 2026-09-01
   - Source: 45 CFR 400.51(a) — "For refugees determined ineligible for cash assistance under the TANF program, the State or its designee must determine eligibility for refugee cash assistance in accordance with §§ 400.53 and 400.59 in the case of the public/private RCA program" — [snapshot `2026-08-31--45-cfr-400-51`](../../../sources/mo/mo_rca/2026-08-31--45-cfr-400-51/), accessed 2026-08-31
   - Source: ORR-PL-21-04 § I.A footnote 5 — "Splitting prior to enrollment would primarily be done if:" … "d) Members of the household will be served under different programs." — [snapshot `2026-09-01--orr-pl-21-04-public-private-rca`](../../../sources/mo/mo_rca/2026-09-01--orr-pl-21-04-public-private-rca/), accessed 2026-09-01
   - Source: ORR-PL-21-04 § I.A footnote 5 — "Splitting prior to enrollment would primarily be done if:" … "b)   Particular members of the case are ineligible for RCA (e.g., a family member receives SSI)," — [snapshot `2026-09-01--orr-pl-21-04-public-private-rca`](../../../sources/mo/mo_rca/2026-09-01--orr-pl-21-04-public-private-rca/), accessed 2026-09-01

3. **Pathway — an applicant aged 65 or older, or who is blind or disabled, who has been referred
   to SSI may receive refugee cash assistance until SSI cash assistance is provided.**
   - Evaluation scope: `member`
   - Captured via: `birth_year_month` (`HouseholdMember`, DateField) via accessor `calc_age()`; `visually_impaired` (`HouseholdMember`, BooleanField); `disabled` (`HouseholdMember`, BooleanField); `long_term_disability` (`HouseholdMember`, BooleanField)
   - Implementation note: this carves out criterion 2's SSI limb — a person eligible for SSI is
     not "ineligible for SSI", and § 400.51(b)(1)(ii) requires RCA to continue until SSI cash is
     provided. It needs no separate implementation: criterion 2's gate fires only on a **reported**
     `sSI` amount, i.e. only once SSI cash has been provided, which is exactly when this pathway
     stops applying. The operative instruction is therefore the negative one — **no member is
     excluded on age, blindness, or disability**; a member is removed only under criterion 2, on a
     reported `sSI` amount. Never implement this as an age, blindness, or disability exclusion.
     Every field named above is nullable, and null must fail open.
   - Source: ORR-PL-21-04 § I.A — "A client that is eligible for Supplemental Security Income (SSI) may only receive RCA and RCA differential payments until cash assistance under the SSI program is provided, at which point the client is ineligible for RCA." — [snapshot `2026-09-01--orr-pl-21-04-public-private-rca`](../../../sources/mo/mo_rca/2026-09-01--orr-pl-21-04-public-private-rca/), accessed 2026-09-01
   - Source: 45 CFR 400.51(b)(1)(i) — "The State agency or its designee must refer refugees who are 65 years of age or older, or who are blind or disabled, promptly to the Social Security Administration to apply for cash assistance under the SSI program." — [snapshot `2026-08-31--45-cfr-400-51`](../../../sources/mo/mo_rca/2026-08-31--45-cfr-400-51/), accessed 2026-08-31
   - Source: 45 CFR 400.51(b)(1)(ii) — "If the State agency or its designee determines that a refugee who is 65 years of age or older, or blind or disabled, is eligible for refugee cash assistance, it must furnish such assistance until eligibility for cash assistance under the SSI program is determined, provided the conditions of eligibility for refugee cash assistance continue to be met." — [snapshot `2026-08-31--45-cfr-400-51`](../../../sources/mo/mo_rca/2026-08-31--45-cfr-400-51/), accessed 2026-08-31

4. **Net countable income, after Missouri's disregards, must be under the RCA Maximum Payment
   level designated for the family size.** Missouri does not use a federal poverty level standard.
   Earned income receives a $90 standard work exemption and a three-fourths disregard; no
   disregard applies to unearned income.
   - Evaluation scope: `household`
   - Captured via: accessor `HouseholdMember.calc_gross_income(frequency, ["earned"])` and `...(["unearned"], exclude=["cashAssistanceOther", "gifts"])`; `IncomeStream.amount` (`IncomeStream`, DecimalField), `IncomeStream.frequency` (`IncomeStream`, CharField) via accessor `IncomeStream.monthly()`; constants `RCA_MAX_PAYMENT` (tabulated sizes 1–5) and `ADDITIONAL_MEMBER_AMOUNT`, read through `rca_max_payment(case_size)` (see Benefit Value)
   - Implementation note: the $90 work exemption is per earning member, applied before the
     three-fourths disregard, and clamped at zero so a member earning under $90 contributes no
     negative amount. Unearned income is counted in full except for `cashAssistanceOther` and
     `gifts`, which are excluded through `calc_gross_income`'s `exclude` parameter per Data Gap 5.
     The RCA Maximum Payment serves as both the eligibility threshold and the benefit base.
     Comparison is strict: net income must be **under** the standard.
   - Source: Missouri Refugee Program State Plan FY2024, p. 27 — "MO-ORA does not utilize federal poverty level standards to determine income eligibility, but instead allows earned income disregards to be applied to a refugee’s gross income." — [snapshot `2026-09-01--mo-state-plan-fy2024`](../../../sources/mo/mo_rca/2026-09-01--mo-state-plan-fy2024/), accessed 2026-09-01
   - Source: Missouri Refugee Program State Plan FY2024, p. 28 — "Earned income disregards, which are applied for the duration of a case’s enrollment in RCA, include a $90 standard work exemption and a three-fourths earned income disregard. No disregards are applied to unearned income." — [snapshot `2026-09-01--mo-state-plan-fy2024`](../../../sources/mo/mo_rca/2026-09-01--mo-state-plan-fy2024/), accessed 2026-09-01
   - Source: Missouri Refugee Program State Plan FY2024, p. 27 — "once the disregard is applied to an RCA participant’s gross income, the resulting net income must then be under the RCA Maximum Payment level (eligibility standard) designated for the family size to be considered eligible for an RCA Payment." — [snapshot `2026-09-01--mo-state-plan-fy2024`](../../../sources/mo/mo_rca/2026-09-01--mo-state-plan-fy2024/), accessed 2026-09-01
   - Source: 45 CFR 400.59(a) — "Eligibility for refugee cash assistance under the public/private program is limited to those who meet the income eligibility standard established by the State after consultation with local resettlement agencies in the State." — [snapshot `2026-08-31--45-cfr-400-59`](../../../sources/mo/mo_rca/2026-08-31--45-cfr-400-59/), accessed 2026-08-31

5. **Resources remaining in the applicant's country of origin, and a sponsor's income and
   resources attributable solely to sponsorship, are not counted in determining income
   eligibility.**
   - Evaluation scope: `assumed-met`
   - Captured via: not applicable — the screener collects neither item, so no exclusion logic is required
   - Implementation note: `Screen.household_assets` carries no location dimension, so
     country-of-origin resources cannot enter the calculation at all. Only `HouseholdMember` rows
     carry `IncomeStream`, so no sponsor outside the household can contribute income. A sponsor who
     is also a household member is out of scope for this rule — their income counts as a household
     member's, not as a sponsor's.
   - Source: 45 CFR 400.59(b) — "Any resources remaining in the applicant's country of origin may not be considered in determining income eligibility." — [snapshot `2026-08-31--45-cfr-400-59`](../../../sources/mo/mo_rca/2026-08-31--45-cfr-400-59/), accessed 2026-08-31
   - Source: 45 CFR 400.59(c) — "A sponsor's income and resources may not be considered to be accessible to a refugee solely because the person is serving as a sponsor." — [snapshot `2026-08-31--45-cfr-400-59`](../../../sources/mo/mo_rca/2026-08-31--45-cfr-400-59/), accessed 2026-08-31

6. **An adult child aged 18 or over is treated as a separate refugee cash assistance case from the
   rest of the arriving household, and a married individual joining a spouse already in the United
   States is not treated as single.**
   - Evaluation scope: `household`
   - Captured via: `relationship` (`HouseholdMember`, CharField, qualifying values `child`, `stepChild`, `fosterChild`, `grandChild`); `birth_year_month` (`HouseholdMember`, DateField) via accessor `calc_age()`
   - Implementation note: the case split determines the size used for both the criterion-4
     threshold and the benefit value, so a household may resolve into more than one case. The
     spouse rule is satisfied by construction — MFB counts every household member's income within
     a case, so a later-arriving spouse is never evaluated as a single person. `calc_age()` returns
     `None` when neither `birth_year_month` nor `age` is set; a member of unknown age does not
     split, staying in the primary case, which is the inclusive direction. `calc_age()` compares
     birth month to reference month, so a member is 18 from the first day of their birth month in
     their eighteenth year. Two elements here are MFB modelling choices the source does not
     determine: that the separated case is **single-member**, and that `stepChild`, `fosterChild`
     and `grandChild` are treated alongside `child` — the latter following existing repo
     convention rather than this spec alone.
   - Source: ORR-PL-21-04 § I.A — "An adult child age 18 years or older should be treated as a separate case." — [snapshot `2026-09-01--orr-pl-21-04-public-private-rca`](../../../sources/mo/mo_rca/2026-09-01--orr-pl-21-04-public-private-rca/), accessed 2026-09-01
   - Source: ORR-PL-21-04 § I.A footnote 5 — "Splitting prior to enrollment would primarily be done if:" … "a)   The case includes parent/s with dependent children 18 or over," — [snapshot `2026-09-01--orr-pl-21-04-public-private-rca`](../../../sources/mo/mo_rca/2026-09-01--orr-pl-21-04-public-private-rca/), accessed 2026-09-01
   - Source: ORR-PL-21-04 § I.A — "A married individual joining a spouse in the U.S. should not be treated as single. The income and resources of the spouse who first arrived to the U.S should be considered when determining eligibility of the later arriving spouse." — [snapshot `2026-09-01--orr-pl-21-04-public-private-rca`](../../../sources/mo/mo_rca/2026-09-01--orr-pl-21-04-public-private-rca/), accessed 2026-09-01

## Missing Eligibility Criteria (Data Gaps)

1. **An individual is eligible for up to 8 months of refugee cash assistance measured from their
   ORR eligibility date.**
   - Why: the screener collects no ORR eligibility date, entry date, or arrival date;
     `HouseholdMember` carries only `birth_year_month`.
   - Handling: `assumed-met` (comment in code) — no household is screened out on duration, and the
     value assumes the full 8-month period remains, which is what makes 8 the value multiplier
     (Benefit Value). A household already part-way through its period has fewer months left, so
     the figure is an upper bound in this respect as well. Surfaced in the program description.
   - Source: 45 CFR 400.53(a)(1) — "Are new arrivals who have resided in the U.S. less than the RCA eligibility period determined by the ORR Director in accordance with § 400.211;" — [snapshot `2026-08-31--45-cfr-400-53`](../../../sources/mo/mo_rca/2026-08-31--45-cfr-400-53/), accessed 2026-08-31
   - Source: 91 FR 43107, 43108 — "ORR-eligible individuals whose eligibility date is on or after January 1, 2026, will be eligible for up to 8 months of RCA and RMA, provided they meet all applicable eligibility requirements under 45 CFR part 400 Subparts E and G." — [snapshot `2026-09-01--fr-2026-14095-rca-rma-8-months`](../../../sources/mo/mo_rca/2026-09-01--fr-2026-14095-rca-rma-8-months/), accessed 2026-09-01

2. **Applicants must not be full-time students in institutions of higher education.**
   - Why: `HouseholdMember.student` and `student_full_time` exist, but no field distinguishes an
     institution of higher education from secondary or other schooling.
   - Handling: `assumed-met` (comment in code) — no member is excluded on student status. Both
     fields are nullable and null fails open, consistent with this handling.
   - Source: 45 CFR 400.53(a)(4) — "Are not full-time students in institutions of higher education, as defined by the Director." — [snapshot `2026-08-31--45-cfr-400-53`](../../../sources/mo/mo_rca/2026-08-31--45-cfr-400-53/), accessed 2026-08-31

3. **Ineligibility for TANF is a condition of refugee cash assistance eligibility, determined for
   the applicant's case.**
   - Why: reported TANF *receipt* is observable per member through the `cashAssistance` income
     option and is applied as a criterion-2 gate. What is not observable is TANF *eligibility* for
     a member who reports no TANF income, and which other members belong to the same TANF
     assistance unit: `CurrentBenefit` carries `screen` and `program` foreign keys and no member
     reference, so a ticked tile names no recipient, and the screener asks nobody whether they
     would qualify for TANF. Because an adult child aged 18 or over forms a separate case and
     household members may be served under different programs, neither fact can be inferred from
     the household.
   - Handling: `assumed-met` (comment in code) — members and cases that report no TANF income are
     assumed TANF-ineligible, which is the inclusive direction; their actual TANF eligibility is
     determined during RCA intake. Surfaced in the program description.
   - Source: 45 CFR 400.51(a) — "For refugees determined ineligible for cash assistance under the TANF program, the State or its designee must determine eligibility for refugee cash assistance in accordance with §§ 400.53 and 400.59 in the case of the public/private RCA program" — [snapshot `2026-08-31--45-cfr-400-51`](../../../sources/mo/mo_rca/2026-08-31--45-cfr-400-51/), accessed 2026-08-31
   - Source: ORR-PL-21-04 § I.A footnote 5 — "Splitting prior to enrollment would primarily be done if:" … "d)   Members of the household will be served under different programs." — [snapshot `2026-09-01--orr-pl-21-04-public-private-rca`](../../../sources/mo/mo_rca/2026-09-01--orr-pl-21-04-public-private-rca/), accessed 2026-09-01
   - Source: Missouri Refugee Program State Plan FY2024, p. 26 — "reviews the Intake and Assessment completed on each household and provides a listing of" … "programs the client(s) appears eligible to participate in, including TANF and SSI." — [snapshot `2026-09-01--mo-state-plan-fy2024`](../../../sources/mo/mo_rca/2026-09-01--mo-state-plan-fy2024/), accessed 2026-09-01

4. **Federal funding is not available for a nonrefugee adult member of a family unit, or for
   nonrefugee children where one parent in the family unit is a nonrefugee — so the payment unit
   may be smaller than the case.**
   - Why: the screener stores no per-member immigration status. `Program.legal_status_required` is
     a screen-level filter and cannot express member-level status.
   - Handling: `assumed-met` (comment in code) — all members of a case are counted in its size.
     This is the MFB screening estimate; the administering agency may use a smaller payment unit,
     so the displayed estimate may be high. Surfaced in the program description.
   - Source: 45 CFR 400.208(a) — "Federal funding is available for a State's expenditures for assistance and services to a family unit which includes a refugee parent or two refugee parents and one or more of their children who are nonrefugees, including children who are United States citizens." — [snapshot `2026-08-31--45-cfr-400-208`](../../../sources/mo/mo_rca/2026-08-31--45-cfr-400-208/), accessed 2026-08-31
   - Source: 45 CFR 400.208(b) — "Federal funding is not available for a State's expenditures for assistance and services provided to a nonrefugee adult member of a family unit or to a nonrefugee child or children in a family unit if one parent in the family unit is a nonrefugee." — [snapshot `2026-08-31--45-cfr-400-208`](../../../sources/mo/mo_rca/2026-08-31--45-cfr-400-208/), accessed 2026-08-31

5. **Cash grants received under Reception and Placement, and under ORR's Program of Initial
   Resettlement, are excluded from the income eligibility determination.** PIR replaced R&P from
   2026-01-01 and ORR-PL-23-04 as revised 2026-02-02 states the equivalence directly; that
   revision also removed the earlier cap tying the disregard to the R&P grant amount. The
   disregard does not reach every ORR-eligible population — the policy letter's own definition of
   "refugees" covers those eligible for initial resettlement services and expressly excludes
   asylees, Cuban/Haitian entrants, victims of human trafficking, and Ukrainian humanitarian
   parolees.
   - Why: a user can report such a grant through the generic `IncomeStream.type` values
     `cashAssistanceOther` (the "any other cash aid" option — General Assistance, another state's
     TANF, a local fund) or `gifts` (contributions received), but no field identifies the income's
     source, so MFB cannot distinguish a qualifying initial-resettlement grant from other cash aid.
   - Handling: broadens results — `cashAssistanceOther` and `gifts` are excluded from countable
     RCA income, the inclusive handling of an income source MFB cannot identify. `cashAssistance`
     is **not** excluded here: it is the screener's TANF option, handled as a criterion-2 gate, so
     it never reaches this calculation for a member who remains in a case. The exclusion
     over-reaches in two directions — it drops ordinary non-PIR amounts in those two buckets, and
     it applies to every household regardless of status even though the disregard reaches only the
     initial-resettlement population, which MFB cannot isolate because `legal_status_required` is
     a screen-level filter and `refugee` is the merged Refugee/Asylee bucket (criterion 1). So
     eligibility and value are overstated for the households it over-reaches. Surfaced in the
     program description.
   - Source: 45 CFR 400.59(d) — "Any cash grant received by a refugee under the Department of State or Department of Justice Reception and Placement programs may not be considered in determining income eligibility." — [snapshot `2026-08-31--45-cfr-400-59`](../../../sources/mo/mo_rca/2026-08-31--45-cfr-400-59/), accessed 2026-08-31
   - Source: ORR-PL-23-04 § II (revised 2026-02-02) — "ORR interprets 45 C.F.R. §§ 400.66(d) and 400.59(d) to require States to disregard cash grants that a refugee receives under a program equivalent to R&P, as well as R&P itself." — [snapshot `2026-09-04--orr-pl-23-04-income-disregards-rca-rev-2026`](../../../sources/mo/mo_rca/2026-09-04--orr-pl-23-04-income-disregards-rca-rev-2026/), accessed 2026-09-04
   - Source: ORR-PL-23-04 § I (revised 2026-02-02) — "because the Department of State’s R&P program has ended and has been replaced by ORR’s Program of Initial Resettlement (PIR), the regulation does not address the services refugees are currently receiving." — [snapshot `2026-09-04--orr-pl-23-04-income-disregards-rca-rev-2026`](../../../sources/mo/mo_rca/2026-09-04--orr-pl-23-04-income-disregards-rca-rev-2026/), accessed 2026-09-04
   - Source: ORR-PL-23-04 § II (revised 2026-02-02) — "Now that R&P has ended and the substantive services of initial resettlement have transferred to ORR, ORR considers its Program of Initial Resettlement (PIR) as equivalent." — [snapshot `2026-09-04--orr-pl-23-04-income-disregards-rca-rev-2026`](../../../sources/mo/mo_rca/2026-09-04--orr-pl-23-04-income-disregards-rca-rev-2026/), accessed 2026-09-04
   - Source: ORR-PL-23-04 § II (revised 2026-02-02) — "In conducting a refugee’s income eligibility determination for RCA, States must disregard cash grants a refugee receives from PIR." — [snapshot `2026-09-04--orr-pl-23-04-income-disregards-rca-rev-2026`](../../../sources/mo/mo_rca/2026-09-04--orr-pl-23-04-income-disregards-rca-rev-2026/), accessed 2026-09-04
   - Source: ORR-PL-23-04 n.3 (revised 2026-02-02) — "The term “refugees” here does not include asylees, Cuban/Haitian Entrants, victims of human trafficking, humanitarian parolees from Ukraine, or other ORR-eligible populations who are not eligible for initial resettlement services under ORR’s Program of Initial Resettlement." — [snapshot `2026-09-04--orr-pl-23-04-income-disregards-rca-rev-2026`](../../../sources/mo/mo_rca/2026-09-04--orr-pl-23-04-income-disregards-rca-rev-2026/), accessed 2026-09-04
   - Source: ORR Program of Initial Resettlement — "Following a Presidential Determination to consolidate domestic refugee resettlement functions under a single federal agency, ORR assumed PIR responsibilities on January 1, 2026." — [snapshot `2026-09-01--orr-program-of-initial-resettlement`](../../../sources/mo/mo_rca/2026-09-01--orr-program-of-initial-resettlement/), accessed 2026-09-01

## Priority Criteria

None identified as of 2026-09-10.

## Related Programs

- **Refugee Medical Assistance (RMA)** — short-term medical coverage for ORR-eligible people found
  ineligible for Medicaid, on the same 8-month clock as RCA. Own eligibility: the State must
  determine RMA eligibility where the applicant is not eligible for Medicaid or SCHIP under the
  State plans. In Missouri it is administered by a separate Medical Replacement Designee, USCRI —
  not by MO-ORA. Not part of this program's eligibility or value.
  - Program description tie-back: none needed
  - Source: 45 CFR 400.94(d) — "If the appropriate State agency determines that the refugee applicant is not eligible for Medicaid or SCHIP under its State plans, the State must determine the applicant's eligibility for refugee medical assistance." — [snapshot `2026-09-01--45-cfr-400-94-rma-eligibility`](../../../sources/mo/mo_rca/2026-09-01--45-cfr-400-94-rma-eligibility/), accessed 2026-09-01
  - Source: 91 FR 43107, 43108 — "ORR-eligible individuals whose eligibility date is on or after January 1, 2026, will be eligible for up to 8 months of RCA and RMA" — [snapshot `2026-09-01--fr-2026-14095-rca-rma-8-months`](../../../sources/mo/mo_rca/2026-09-01--fr-2026-14095-rca-rma-8-months/), accessed 2026-09-01
  - Source: ACF ORR DCL 18-03 — "Medical Replacement Designee (MRD): U.S. Committee for Refugees and Immigrants (USCRI)" — [snapshot `2026-09-01--acf-missouri-replacement-designees`](../../../sources/mo/mo_rca/2026-09-01--acf-missouri-replacement-designees/), accessed 2026-09-01
- **MO-RTAC (Missouri Refugee Temporary Assistance Connections)** — Missouri's Wilson-Fish/TANF
  coordination grant. It serves TANF-eligible refugee families — the population the criterion-2
  rule excludes from RCA. MFB gates on *reported* TANF receipt per member (criterion 2); what it
  cannot observe, and so does not screen on, is TANF *eligibility* for a member who reports no
  TANF income (Data Gap 3).
  Own eligibility: TANF-eligible families with children under 18 who have been in the U.S. not more
  than 36 months. Not part of this program's eligibility or value.
  - Program description tie-back: none needed
  - Source: Missouri Refugee Program State Plan FY2024, p. 45 — "The Wilson Fish/ TANF Coordination grant is known within the state as Missouri Refugee Temporary Assistance Connections (MO-RTAC). MO-RTAC identifies refugee families with children under 18, who are TANF-eligible and have been in the U.S. for not more than 36 months" — [snapshot `2026-09-01--mo-state-plan-fy2024`](../../../sources/mo/mo_rca/2026-09-01--mo-state-plan-fy2024/), accessed 2026-09-01

## Benefit Value

- Value: `(rca_max_payment(case_size) − net_countable_income) × 8` per case, summed across the
  cases in a household (= the monthly Missouri RCA payment × the allowable number of months of RCA
  eligibility, which 91 FR 43107 sets at 8 for eligibility dates on or after 2026-01-01)
- `value_format`: `lump_sum` — the total a household can receive over its eligibility period, not
  a recurring annual figure. `lump_sum` renders the stored value with no divisor and no period
  suffix (`benefits-calculator`, `src/Components/Results/FormattedValue.tsx`, `useValueFormats`),
  which is the only format that neither divides an 8-month total by 12 nor labels it "/year".
- Variation axes: case size (payment standard table); earned income (per-member $90 exemption then
  three-fourths disregard); unearned income (counted in full); assistance-unit split — each appears
  in Test Scenarios
- Missouri RCA Maximum Payment, by case size:

  | Case size | 1 | 2 | 3 | 4 | 5 | each additional |
  |---|---|---|---|---|---|---|
  | Monthly | $537 | $726 | $915 | $1,104 | $1,217 | +$113 |

- Net countable income = Σ over the case's members of `(max(monthly earned − 90, 0) × 0.25)` +
  Σ monthly unearned income, excluding `cashAssistanceOther` and `gifts` per Data Gap 5.
- **The calculator rounds at no intermediate step, and commits its value to the cent.** The $90
  exemption, the quarter-countable disregard, the unearned sum and the subtraction from the
  payment standard all carry full precision — Scenarios 6 and 13 kill a whole-dollar mutation at
  those steps — and the ×8 result is committed to the cent, not to the dollar. Do not add a
  rounding step to make the arithmetic "tidy". Most committed values are whole dollars only
  because whole-dollar earned inputs leave net income on a $0.25 grid; that is a property of those
  inputs and not a guarantee, and a cent-valued unearned stream yields a cent-valued award
  (Scenario 20).
- **The `float` cast is load-bearing, and a scenario's value is met to the cent.**
  `IncomeStream.monthly()` computes in `Decimal` and `HouseholdMember.calc_gross_income` casts the
  member total to `float`, so both the below-the-standard comparison and the award are computed in
  float. That cast is what makes Scenario 13 land exactly: `Decimal(2.175)` is
  `2.17499999999999982…`, so a pure-`Decimal` chain gives $1,866.000000000000213, and only
  `float(1304.999999999999893…) == 1305.0` produces the committed $1,866.00. Where cents are
  involved the float result carries representation error in its last places —
  `(537 − 400.33) × 8` evaluates to `1093.3600000000001` — so a committed value is met when it
  agrees **to the cent**, never by float identity.
- **The stored value reaches the user undivided.** `ProgramEligibilitySnapshot.estimated_value` is
  a `DecimalField(decimal_places=2)` and receives the value unrounded, so the cents reach the
  database; every display path formats with `maximumFractionDigits: 0`, so the user sees whole
  dollars. Under `lump_sum` the card reads the stored total directly — no divisor stands between
  the committed value and what is displayed. The calculator must not pre-empt any of this.
  `review-notes.md` records what the admin validation view and the assistant do with the figure;
  neither is this calculator's behaviour to work around.
- Employment incentives are excluded from the modelled value: they are discretionary rather than
  an entitlement, and their amount is not determinable from screener data.
- Source: Missouri Refugee Program State Plan FY2024, p. 28 — "Case Size 1 2 3 4 5 RCA Max Payment $537 $726 $915 $1104 $1217*" — [snapshot `2026-09-01--mo-state-plan-fy2024`](../../../sources/mo/mo_rca/2026-09-01--mo-state-plan-fy2024/), accessed 2026-09-01
- Source: Missouri Refugee Program State Plan FY2024, p. 28 — "*For RCA case sizes above 5, add $113 for each additional member." — [snapshot `2026-09-01--mo-state-plan-fy2024`](../../../sources/mo/mo_rca/2026-09-01--mo-state-plan-fy2024/), accessed 2026-09-01
- Source: Missouri Refugee Program State Plan FY2024, p. 27 — "The net income is then subtracted from the appropriate RCA maximum payment" — [snapshot `2026-09-01--mo-state-plan-fy2024`](../../../sources/mo/mo_rca/2026-09-01--mo-state-plan-fy2024/), accessed 2026-09-01
- Source: Missouri Refugee Program State Plan FY2024, p. 29 — "This analysis afforded MO-ORA the opportunity to meet the RCA payment ceilings as written in DCL 22-01 and in accordance with 45 CFR §§400.56 – 400.63." — [snapshot `2026-09-01--mo-state-plan-fy2024`](../../../sources/mo/mo_rca/2026-09-01--mo-state-plan-fy2024/), accessed 2026-09-01
- Source: 86 FR 54466 — "Using ORR's original formula in relation to the 2021 HHS poverty guidelines, the adjusted PPP RCA payment ceilings are:" … "1....................................................... $537" … "2....................................................... 726" … "3....................................................... 915" … "4....................................................... 1,104" — [snapshot `2026-09-01--fr-2021-21369-ppp-rca-inflationary-increase`](../../../sources/mo/mo_rca/2026-09-01--fr-2021-21369-ppp-rca-inflationary-increase/), accessed 2026-09-01
- Source: 86 FR 54466 — "Where family units are greater than four people, the monthly payment ceiling is increased by $113 for each additional person." — [snapshot `2026-09-01--fr-2021-21369-ppp-rca-inflationary-increase`](../../../sources/mo/mo_rca/2026-09-01--fr-2021-21369-ppp-rca-inflationary-increase/), accessed 2026-09-01
- Source: 45 CFR 400.60(a) — "For family units greater than 4 persons, the payment ceiling may be increased by $70 for each additional person." — [snapshot `2026-08-31--45-cfr-400-60`](../../../sources/mo/mo_rca/2026-08-31--45-cfr-400-60/), accessed 2026-08-31
- Source: 45 CFR 400.60(d) — "If the Director determines that the payment ceilings need to be adjusted for inflation, the Director will publish a document in the" … "announcing the new payment ceilings." — [snapshot `2026-08-31--45-cfr-400-60`](../../../sources/mo/mo_rca/2026-08-31--45-cfr-400-60/), accessed 2026-08-31
- Source: 86 FR 54466 — "in accordance with ORR regulations at 45 CFR 400.60(d), the ORR Director has determined that the PPP RCA payment ceilings need to be adjusted for inflation." — [snapshot `2026-09-01--fr-2021-21369-ppp-rca-inflationary-increase`](../../../sources/mo/mo_rca/2026-09-01--fr-2021-21369-ppp-rca-inflationary-increase/), accessed 2026-09-01
- Source: 86 FR 54466 — "When ORR established the current PPP RCA monthly" … "payment ceilings, it used the 1998 HHS Poverty Guidelines with the" … "Where family units were" … "greater than four people, the monthly payment ceiling was increased by" … "$70 for each additional person." — [snapshot `2026-09-01--fr-2021-21369-ppp-rca-inflationary-increase`](../../../sources/mo/mo_rca/2026-09-01--fr-2021-21369-ppp-rca-inflationary-increase/), accessed 2026-09-01
- Source: 45 CFR 400.60(b) — "States and local resettlement agencies may not make payments to refugees that are lower than the State's TANF payment for the same sized family unit." — [snapshot `2026-08-31--45-cfr-400-60`](../../../sources/mo/mo_rca/2026-08-31--45-cfr-400-60/), accessed 2026-08-31
- Source: Missouri Refugee Program State Plan FY2024, p. 28 — "MO TANF Standard                $136         $234         $292       $342    $388" — [snapshot `2026-09-01--mo-state-plan-fy2024`](../../../sources/mo/mo_rca/2026-09-01--mo-state-plan-fy2024/), accessed 2026-09-01
- Source: ORR-PL-21-04 § I.E — "An incentive is not an entitlement, but the agency may use it to encourage early" … "employment." — [snapshot `2026-09-01--orr-pl-21-04-public-private-rca`](../../../sources/mo/mo_rca/2026-09-01--orr-pl-21-04-public-private-rca/), accessed 2026-09-01
- Source: ORR-PL-21-04 § I.C — "On a monthly basis, the PPP-administering agency must also determine continued eligibility for RCA on the basis of income. RCA payments must be reduced on the basis of income from employment and other sources after factoring in applicable disregards." — [snapshot `2026-09-01--orr-pl-21-04-public-private-rca`](../../../sources/mo/mo_rca/2026-09-01--orr-pl-21-04-public-private-rca/), accessed 2026-09-01
- Source: Missouri Refugee Program State Plan FY2024, p. 27 — "Gross monthly employment income is calculated, and applicable $90 work exemption and 3/4 income disregard are factored in, subtracted from the maximum RCA benefit level for the family size." — [snapshot `2026-09-01--mo-state-plan-fy2024`](../../../sources/mo/mo_rca/2026-09-01--mo-state-plan-fy2024/), accessed 2026-09-01
- Source: MO-ORA, Cash Assistance — "Refugee Cash Assistance (RCA) is a short-term monthly payment program." — [snapshot `2026-09-01--moora-cash-assistance`](../../../sources/mo/mo_rca/2026-09-01--moora-cash-assistance/), accessed 2026-09-01
- Justification: Missouri's payment standard is the benefit base, and the monthly payment is that
  standard less net countable income. Missouri set its standards at the ORR ceiling — the FY2024
  plan records that its cost-benefit analysis let MO-ORA meet the RCA payment ceilings of DCL
  22-01 — and those standards match the ceilings tabulated in 86 FR 54466 for sizes 1–4, with size
  5 following from the quoted +$113 extension. The ceiling table printed at 45 CFR 400.60(a) is
  superseded: it still carries the +$70 increment ORR set from the 1998 poverty guidelines, and
  45 CFR 400.60(d) provides for adjustment by Federal Register document, which 86 FR 54466 is.
  The 45 CFR 400.60(b) floor never binds in Missouri, whose TANF maximums run from $136 at one
  person to $388 at five — below the RCA standard at every size.

  **Why the multiplier is 8 and the format is `lump_sum`.** RCA is paid monthly and MFB stores a
  single figure, so the stored value must represent some span of months. The eligibility period
  supplies it: 45 CFR 400.53(a)(1) limits RCA to new arrivals within "the RCA eligibility period
  determined by the ORR Director", which 91 FR 43107 sets at 8 months for eligibility dates on or
  after 2026-01-01. A household can receive at most 8 monthly payments, so `monthly × 8` is the
  largest total it can lawfully receive. `lump_sum` is the only format that carries that total
  undistorted, and is what the repo already uses for time-limited multi-month assistance
  (`ks_lieap`, `mo_liheap`, `wa_liheap`, `il_cbrap`); its "Estimated One-Time Payment" label is
  imprecise for a benefit paid in instalments. `review-notes.md` B2 records the alternatives
  considered and why each was rejected.

  **The figure is a ceiling, not an expectation.** ORR-PL-21-04 § I.C requires the agency to
  redetermine eligibility monthly and reduce the payment as income rises, so a household that goes
  to work receives less than 8 × its screening-time award; and Data Gap 1's assumption that the
  full 8-month period remains is what makes 8 the multiplier, so a household already part-way
  through its period has fewer months left. Both effects run the same way: the stored value is an
  upper bound. The monthly rate belongs in the config description, not in the value field, which
  holds only one number.

## Test Scenarios

All ages are as of the screen reference date 2026-09-01. Legal-status filtering is applied by the
program-level `legal_status_required` config and is outside the calculator's test universe, so no
scenario asserts it. Every **committed** dollar value below — each scenario's Expected value — is
the stored figure, the monthly award × 8, the
most a household can receive across the 8-month eligibility period, per Benefit Value — and rests
on the Missouri FY2024 payment schedule.

**Coverage map**

| Rule / variation axis | Scenarios |
|---|---|
| Criterion 1 — ORR status (config filter) | all scenarios (config-level; no calculator branch) |
| Criterion 2 — member-level SSI receipt removes that member only | 11 |
| Criterion 2 — member-level TANF receipt (`cashAssistance`) removes that member | 10 |
| Criterion 2 — a household-level TANF report gates nothing | 19 |
| Criterion 3 — none of age 65+, `disabled`, `visually_impaired`, `long_term_disability` excludes | 12 |
| Criterion 4 — $90 work exemption, per earning member | 2, 9 |
| Criterion 4 — three-fourths earned disregard | 2, 9 |
| Criterion 4 — `max(earned − 90, 0)` clamped at zero | 14 |
| Criterion 4 — unearned counted in full, no disregard | 5, 6, 20 |
| Criterion 4 — `wages` is earned; `selfEmployment` is earned | 2 (wages), 9 (selfEmployment) |
| Criterion 4 — non-monthly frequency normalised via `IncomeStream.monthly()` | 13 |
| Criterion 4 — strict below-the-standard boundary | 3 (at → fail), 4 ($1 under → pass) |
| Criterion 6 — adult child 18+ forms a separate case | 15 |
| Criterion 6 — age-18 boundary exactly | 15 (18 splits, 17 does not) |
| Criterion 6 — a non-`child` relationship value splits | 15 (`stepChild`); `fosterChild` / `grandChild` follow repo convention, untested |
| Criterion 6 — later-arriving spouse counted within the case, never as a single | 9, 16 |
| Criterion 4 — income summed per case, not pooled across the household | 16 |
| Value — an ineligible case contributes nothing; a sibling case is still served | 17 |
| Value — the monthly award is stored × 8, the allowable months | every eligible scenario |
| Value — case size 1 | 1, 2, 4, 5, 11, 12, 13, 14, 15, 16, 17, 20 |
| Value — case size 2 | 9, 16, 19 |
| Value — case size 3 | 15 (parent case) |
| Value — case size 4 | 6 |
| Value — case size 5 | 7 |
| Value — case size 6 (+$113 extension) | 8 |
| Value — case size 7 (+$113 applied per additional member) | 18 |
| Value — zero income yields the full standard, not $0 | 1, 7, 8, 19 |
| Value — the award is carried to the cent, not rounded to the dollar | 20 |
| Framework mapping — a member of a case that fails the standard is marked ineligible | 17 |
| Framework mapping — a member removed from their case is marked ineligible | 10, 11 |
| Framework mapping — members of payable cases are marked eligible | 11, 15, 16, 19 |
| Framework mapping — the award sits in `household_value()`, not `member_value()` | 6, 7, 8 (a per-member award would multiply by case size) |
| Registration — `program_code = "mo_rca"` | no scenario; the registry build raises without it (Acceptance Criterion 14) |

**Known scenario gaps.**

- The data gaps get no scenario, because the screener cannot express the facts they turn on: the
  8-month clock (no ORR eligibility date), the higher-education student exclusion (no institution
  type), TANF eligibility and assistance-unit membership (no member reference on
  `CurrentBenefit`), and the § 400.208 mixed-status payment unit (no per-member status). Data Gap
  3's *handling* is tested separately: who belongs to a TANF assistance unit is unobservable, but
  the committed inclusive response to a household reporting TANF with no `cashAssistance` amount
  is observable, and Scenario 19 pins it.
- **Data Gap 5's income-source proxy is deliberately untested.** Excluding `cashAssistanceOther`
  and `gifts` is a proxy for an unidentifiable income source, not a sourced rule, so a scenario
  asserting it would dress the workaround up as verified policy; an Acceptance Criterion pins it
  instead. Scenario 5 proves the neighbouring rule — a non-excluded unearned stream
  (`childSupport`) is still counted in full.
- **No scenario discriminates a payment table that stops at size 4 and extrapolates with +$113.**
  $1,104 + $113 = $1,217 and $1,104 + 2 × $113 = $1,330, so that model is behaviourally identical
  to the tabulated one at every size. The distinction is unobservable rather than untested.
- **Case size 3 rests on Scenario 15's parent case alone** — no independent zero-income scenario
  of the kind Scenarios 1, 7, 8 and 19 give sizes 1, 5, 6 and 2, so at that size the payment
  standard is pinned only in combination with an income calculation.
- `fosterChild` and `grandChild` splitting alongside `child` is MFB's mapping, asserted on repo
  convention rather than by a scenario; Scenario 15 exercises `stepChild` only.
- No scenario is possible or needed for: criterion 5 (the screener collects no country-of-origin
  resources and no sponsor income, so there is no branch); registration (the registry raises
  before any scenario could run — Acceptance Criterion 14); the unknown-age guard (the screener
  always collects an age or a birth month, so `calc_age()` returning `None` is unreachable from a
  screen); and the incomplete-income-stream path (all three fields are declared dependencies, so
  `can_calc()` suppresses the program rather than reaching a calculation branch).
- **Every dollar value in this table rests on the FY2024 Missouri payment schedule** (snapshot
  `2026-09-01--mo-state-plan-fy2024`), taken as current by a recorded decision rather than
  confirmed by MO-ORA; `review-notes.md` B1 states what that accepts and what re-opens it.

### Scenario 1: Single adult refugee with no income — Eligible, $4,296.00
**What we're checking**: the case-size-1 payment standard with a zero-income household.
**Expected**: Eligible — $4,296.00 (net countable income $0; $537 − $0 = $537.00/month;
$537.00 × 8 = $4,296.00)
**Steps**:
* Location: ZIP `63118`, county `St. Louis City`
* Person 1: born June 1996 (age 30), head of household, no income
**Why this matters**: kills a wrong size-1 payment standard, and kills an implementation that
returns $0 when there is no income to subtract.

### Scenario 2: Single adult with wages — Eligible, $2,476.00
**What we're checking**: the $90 work exemption and the three-fourths earned disregard together,
on a `wages` income stream.
**Expected**: Eligible — $2,476.00 (earned $1,000.00/month; ($1,000 − $90) × 0.25 = $227.50
countable; $227.50 < $537 so eligible; $537 − $227.50 = $309.50/month; $309.50 × 8 = $2,476.00)
**Steps**:
* Location: ZIP `63118`, county `St. Louis City`
* Person 1: born June 1996 (age 30), head of household, `wages` $1,000/month
**Why this matters**: kills omission of the $90 exemption (which gives $2,296.00), kills applying
the disregard before the exemption instead of after (which gives $3,016.00), and kills a wrong
disregard fraction.

### Scenario 3: Single adult whose net income exactly equals the payment standard — Ineligible
**What we're checking**: the boundary is strict — net income must fall below the standard, not merely reach it.
**Expected**: Ineligible (earned $2,238.00/month; ($2,238 − $90) × 0.25 = $537.00 countable;
$537.00 is not under $537, so not eligible)
**Steps**:
* Location: ZIP `63118`, county `St. Louis City`
* Person 1: born June 1996 (age 30), head of household, `wages` $2,238/month
**Why this matters**: kills a `<=` comparison where the source requires "under".

### Scenario 4: Single adult one dollar under the standard — Eligible, $8.00
**What we're checking**: the eligible side of the same boundary, and that a tiny benefit is still
returned rather than rounded away.
**Expected**: Eligible — $8.00 (earned $2,234.00/month; ($2,234 − $90) × 0.25 = $536.00 countable;
$536.00 < $537 so eligible; $537 − $536.00 = $1.00/month; $1.00 × 8 = $8.00)
**Steps**:
* Location: ZIP `63118`, county `St. Louis City`
* Person 1: born June 1996 (age 30), head of household, `wages` $2,234/month
**Why this matters**: pairs with Scenario 3 to pin the boundary exactly, and kills a floor that
suppresses small awards.

### Scenario 5: Single adult with unearned income only — Eligible, $1,096.00
**What we're checking**: unearned income receives no disregard, and a `childSupport` stream is not
caught by Data Gap 5's exclusion.
**Expected**: Eligible — $1,096.00 (unearned $400.00/month counted in full; $400 < $537 so
eligible; $537 − $400.00 = $137.00/month; $137.00 × 8 = $1,096.00)
**Steps**:
* Location: ZIP `64110`, county `Jackson County`
* Person 1: born June 1996 (age 30), head of household, `childSupport` $400/month
**Why this matters**: kills applying the earned-income disregard to all income — that mutation
gives ($400 − $90) × 0.25 = $77.50 countable and a $3,676.00 value. It also kills an
over-broad Data Gap 5 exclusion that drops every unearned stream rather than only
`cashAssistanceOther` and `gifts`, which would return the full $4,296.00.

### Scenario 6: Family of four, earned and unearned income — Eligible, $5,012.00
**What we're checking**: the case-size-4 standard with both income kinds in one case.
**Expected**: Eligible — $5,012.00 (earned $1,200.00/month → ($1,200 − $90) × 0.25 = $277.50;
unearned $200.00/month counted in full; net $477.50 < $1,104 so eligible;
$1,104 − $477.50 = $626.50/month; $626.50 × 8 = $5,012.00)
**Steps**:
* Location: ZIP `63118`, county `St. Louis City`
* Person 1: born June 1996 (age 30), head of household, `wages` $1,200/month
* Person 2: born March 1998 (age 28), spouse, no income
* Person 3: born May 2018 (age 8), child, no income
* Person 4: born January 2021 (age 5), child, `childSupport` $200/month
**Why this matters**: kills a wrong size-4 standard and kills summing the two income kinds before
applying the disregard.

### Scenario 7: Family of five with no income — Eligible, $9,736.00
**What we're checking**: the size-5 payment standard.
**Expected**: Eligible — $9,736.00 (net countable income $0; $1,217 − $0 = $1,217.00/month;
$1,217.00 × 8 = $9,736.00)
**Steps**:
* Location: ZIP `65806`, county `Greene County`
* Person 1: born June 1996 (age 30), head of household, no income
* Person 2: born March 1998 (age 28), spouse, no income
* Person 3: born May 2018 (age 8), child, no income
* Person 4: born January 2021 (age 5), child, no income
* Person 5: born February 2023 (age 3), child, no income
**Why this matters**: pins the size-5 value $1,217. It does not discriminate a
stops-at-size-4-plus-$113 model, which coincides here and at every larger size — see Known
scenario gaps.

### Scenario 8: Family of six with no income — Eligible, $10,640.00
**What we're checking**: the +$113-per-additional-member rule beyond the tabulated sizes.
**Expected**: Eligible — $10,640.00 ($1,217 + $113 = $1,330.00/month; $1,330.00 × 8 = $10,640.00)
**Steps**:
* Location: ZIP `65806`, county `Greene County`
* Person 1: born June 1996 (age 30), head of household, no income
* Person 2: born March 1998 (age 28), spouse, no income
* Person 3: born May 2018 (age 8), child, no income
* Person 4: born January 2021 (age 5), child, no income
* Person 5: born February 2023 (age 3), child, no income
* Person 6: born April 2025 (age 1), child, no income
**Why this matters**: kills a lookup that caps at size 5 (which gives $9,736.00), and kills a
wrong increment.

### Scenario 9: Two earning adults, one on self-employment — Eligible, $3,768.00
**What we're checking**: the $90 work exemption applies per earning member rather than once per
case, and `selfEmployment` counts as earned income.
**Expected**: Eligible — $3,768.00 (Person 1 ($600 − $90) × 0.25 = $127.50; Person 2
($600 − $90) × 0.25 = $127.50; net $255.00 < $726 so eligible; $726 − $255.00 = $471.00/month;
$471.00 × 8 = $3,768.00)
**Steps**:
* Location: ZIP `64110`, county `Jackson County`
* Person 1: born June 1996 (age 30), head of household, `wages` $600/month
* Person 2: born March 1998 (age 28), spouse, `selfEmployment` $600/month
**Why this matters**: kills applying the $90 exemption once to combined case earnings (which gives
$3,588.00), and kills treating `selfEmployment` as unearned (which gives net $727.50, over the
$726 standard, and so Ineligible).

### Scenario 10: Single adult reporting TANF cash — Ineligible
**What we're checking**: a member reporting `cashAssistance` — the screener's TANF income option —
is removed from their RCA case on TANF receipt.
**Expected**: Ineligible (Person 1 reports `cashAssistance` $400/month and is removed from their
case, taking their income with them; no member remains, so the household resolves to no RCA case
and no value; Person 1 marked ineligible)
**Steps**:
* Location: ZIP `63118`, county `St. Louis City`
* Person 1: born June 1996 (age 30), head of household, `cashAssistance` $400/month
**Why this matters**: a single-member case makes the result fully discriminating without asserting
anything about other members' TANF assistance-unit membership, which MFB cannot observe (Data Gap
3). Treating `cashAssistance` as ordinary unearned income leaves the member in the case with $400
countable, under the $537 standard, and returns Eligible at $1,096.00. Excluding it from income
without gating on it — the handling Data Gap 5 gives `cashAssistanceOther` — returns Eligible at
$4,296.00, so this scenario also kills a calculator that confuses the two options.

### Scenario 11: Two-person household where one member receives SSI — Eligible, $4,296.00
**What we're checking**: a member with a reported SSI payment is removed from the case, and the
remaining member is still served.
**Expected**: Eligible — $4,296.00 (Person 2 is removed from the case on SSI receipt, along with
their income, and forms no case of their own; remaining case size 1, net countable income $0;
$537 − $0 = $537.00/month; $537.00 × 8 = $4,296.00; Person 1 marked eligible, Person 2
ineligible)
**Steps**:
* Location: ZIP `63118`, county `St. Louis City`
* Person 1: born June 1996 (age 30), head of household, no income
* Person 2: born March 1998 (age 28), spouse, `sSI` $400/month
**Why this matters**: separates three models that a larger SSI amount would collapse together.
A household-wide SSI exclusion returns Ineligible. Leaving the SSI member in the case gives size 2
with $400 unearned — under the $726 standard — and so $2,608.00. Giving the removed member their
own single-member case adds ($537 − $400) × 8 = $1,096.00, for $5,392.00. Each differs from the
expected $4,296.00, and ORR-PL-21-04 forecloses that third model: an SSI recipient is ineligible
for RCA once SSI cash is provided, so no separate payable case can arise for them.

### Scenario 12: Adult aged 67, blind, and disabled, not receiving SSI — Eligible, $4,296.00
**What we're checking**: the SSI-pending pathway — age, blindness and disability do not exclude,
across every field criterion 3 names.
**Expected**: Eligible — $4,296.00 (net countable income $0; $537 − $0 = $537.00/month;
$537.00 × 8 = $4,296.00)
**Steps**:
* Location: ZIP `63118`, county `St. Louis City`
* Person 1: born March 1959 (age 67), head of household, `disabled` true, `visually_impaired` true,
  `long_term_disability` true, no income, no current benefits
**Why this matters**: kills an implementation that treats age 65+, blindness, or disability as an
exclusion rather than a referral trigger — the inversion 45 CFR 400.51(b)(1)(ii) forbids. All four
signals sit on one single-member case, so an exclusion on any one flips this to Ineligible; a
failure names the case, not the field, so a per-field regression needs four single-signal cases.

### Scenario 13: Single adult paid biweekly — Eligible, $1,866.00
**What we're checking**: a non-monthly income frequency is normalised before the disregard.
**Expected**: Eligible — $1,866.00 (`wages` $600.00 biweekly × 2.175 = $1,305.00/month via
`IncomeStream.monthly()`; ($1,305 − $90) × 0.25 = $303.75 countable; $303.75 < $537 so eligible;
$537 − $303.75 = $233.25/month; $233.25 × 8 = $1,866.00)
**Steps**:
* Location: ZIP `63118`, county `St. Louis City`
* Person 1: born June 1996 (age 30), head of household, `wages` $600 biweekly
**Why this matters**: every other scenario states income already in dollars per month, so a
calculator reading `IncomeStream.amount` raw passes all of them. Here that mutation gives
($600 − $90) × 0.25 = $127.50 countable and a $3,276.00 value.

### Scenario 14: Single adult earning less than the work exemption — Eligible, $4,296.00
**What we're checking**: the earned-income calculation is clamped at zero.
**Expected**: Eligible — $4,296.00 (earned $50.00/month; max($50 − $90, 0) = $0.00, so countable
$0.00; $537 − $0.00 = $537.00/month; $537.00 × 8 = $4,296.00)
**Steps**:
* Location: ZIP `63118`, county `St. Louis City`
* Person 1: born June 1996 (age 30), head of household, `wages` $50/month
**Why this matters**: without the `max(..., 0)` clamp the countable amount is −$10.00, which raises
the award above the payment standard to $547.00/month and $4,376.00 — a benefit larger than the
maximum. No other scenario has an earner below $90.

### Scenario 15: Household with an 18-year-old and a 17-year-old child — Eligible, $11,616.00
**What we're checking**: an adult child aged 18 or over forms a separate case, exactly at the
age-18 boundary, while a 17-year-old remains in the parents' case.
**Expected**: Eligible — $11,616.00 (parents' case includes the 17-year-old → size 3 →
$915.00/month → $7,320.00; the 18-year-old forms a separate size-1 case → $537.00/month →
$4,296.00; household total $1,452.00/month → $11,616.00; all four members marked eligible, since
both cases are payable) — the four child relationship enums are an MFB implementation mapping, not
an ORR enumeration
**Steps**:
* Location: ZIP `63118`, county `St. Louis City`
* Person 1: born June 1996 (age 30), head of household, no income
* Person 2: born March 1998 (age 28), spouse, no income
* Person 3: born September 2008 (age 18), `stepChild`, no income
* Person 4: born October 2008 (age 17), child, no income
**Why this matters**: kills treating the household as a single size-4 case, which gives
$1,104.00/month and $8,832.00. The two children sit on either side of the boundary in the
reference month, so a `> 18` or `>= 19` threshold splits neither and returns the same $8,832.00,
and a threshold that also split the 17-year-old would give three cases and a different total again.

### Scenario 16: Multi-case household where only the adult child earns — Eligible, $8,284.00
**What we're checking**: income is summed over each case's own members, not pooled across the
household.
**Expected**: Eligible — $8,284.00 (parents' case size 2, net countable income $0 →
$726.00/month → $5,808.00; the 18-year-old's separate case size 1, ($1,000 − $90) × 0.25 = $227.50
countable → $537 − $227.50 = $309.50/month → $2,476.00; household total $8,284.00; all three
members marked eligible)
**Steps**:
* Location: ZIP `63118`, county `St. Louis City`
* Person 1: born June 1996 (age 30), head of household, no income
* Person 2: born March 1998 (age 28), spouse, no income
* Person 3: born September 2008 (age 18), child, `wages` $1,000/month
**Why this matters**: Scenario 15 splits cases but gives every member zero income, so a calculator
that splits correctly and then pools income across the whole household survives it. Here that
mutation charges the child's $227.50 against the parents' case too, giving $498.50/month there and
a household total of $6,464.00.

### Scenario 17: Multi-case household where one case is over the standard — Eligible, $4,296.00
**What we're checking**: an ineligible case contributes nothing while a separable eligible case in
the same household is still served.
**Expected**: Eligible — $4,296.00 (parents' case size 2, ($3,000 − $90) × 0.25 = $727.50
countable, which is not under $726, so that case is ineligible and contributes $0; the 18-year-old's
separate case size 1, no income → $537.00/month → $4,296.00; Person 1 and Person 2 marked
ineligible, Person 3 eligible)
**Steps**:
* Location: ZIP `63118`, county `St. Louis City`
* Person 1: born June 1996 (age 30), head of household, `wages` $3,000/month
* Person 2: born March 1998 (age 28), spouse, no income
* Person 3: born September 2008 (age 18), child, no income
**Why this matters**: the other ineligible scenarios are single-member households, so nothing else
distinguishes a household-wide ineligibility rule from per-case judgement. It is also the only
scenario discriminating the **case-income limb** of `member_eligible()`: an implementation marking
a member ineligible only on removal, never on their case failing the standard, returns this same
verdict and this same $4,296.00, diverging solely in the marks — which is what the results page
renders. It does not probe the `<` boundary; only Scenario 3 does.

### Scenario 18: Family of seven with no income — Eligible, $11,544.00
**What we're checking**: the +$113 increment applies once per additional member beyond five, not
once in total.
**Expected**: Eligible — $11,544.00 ($1,217 + $113 × 2 = $1,443.00/month; $1,443.00 × 8 =
$11,544.00)
**Steps**:
* Location: ZIP `65806`, county `Greene County`
* Person 1: born June 1996 (age 30), head of household, no income
* Person 2: born March 1998 (age 28), spouse, no income
* Person 3: born May 2018 (age 8), child, no income
* Person 4: born January 2021 (age 5), child, no income
* Person 5: born February 2023 (age 3), child, no income
* Person 6: born April 2025 (age 1), child, no income
* Person 7: born July 2017 (age 9), child, no income
**Why this matters**: Scenario 8 is the only other case above size 5 and tests size 6 alone, so a
lookup that adds $113 a single time — $1,330 for every size above five — returns Scenario 8's
$10,640.00 correctly and survives. Here that mutation gives $10,640.00 against the expected
$11,544.00.

### Scenario 19: Two adults reporting TANF on the current-benefits tile — Eligible, $5,808.00
**What we're checking**: a household-level TANF report removes nobody and gates no case —
criterion 2's TANF limb reads a per-member `cashAssistance` income stream and nothing else.
**Expected**: Eligible — $5,808.00 (the ticked tile names no recipient, so no member is removed;
case size 2, net countable income $0; $726 − $0 = $726.00/month; $726.00 × 8 = $5,808.00; both
members marked eligible)
**Steps**:
* Location: ZIP `63118`, county `St. Louis City`
* Person 1: born June 1996 (age 30), head of household, no income
* Person 2: born March 1998 (age 28), spouse, no income
* Current benefits: `has_benefits` true, `current_benefits` includes `mo_tanf`; no member reports a
  `cashAssistance` income stream
**Why this matters**: the mutation is the one nearest to hand. `programs/framework/pe_dependencies/receipt.py`
— the module criterion 2 sends the implementer to for `TANF_INCOME_TYPE` — also exports
`screen_reports_tanf()`, which is
`has_base_benefit("tanf") or calc_gross_income("yearly", ["cashAssistance"]) > 0`. Reusing that
neighbouring helper gates the household on the tile and returns Ineligible here, against Data Gap
3's committed inclusive handling. Scenario 10 does not catch it: its member reports an amount and
is removed under either reading. This is also the only zero-income scenario at case size 2, so it
pins the $726 standard independently of any income calculation.

### Scenario 20: Single adult with cent-valued unearned income — Eligible, $1,093.36
**What we're checking**: an award that is not a whole number of dollars is carried to the cent
rather than rounded or truncated.
**Expected**: Eligible — $1,093.36 (unearned $400.33/month counted in full; $400.33 < $537 so
eligible; $537 − $400.33 = $136.67/month; $136.67 × 8 = $1,093.36, met to the cent — the float
path evaluates it as $1,093.3600000000001)
**Steps**:
* Location: ZIP `64110`, county `Jackson County`
* Person 1: born June 1996 (age 30), head of household, `childSupport` $400.33/month
**Why this matters**: every other committed value is a whole dollar, so a calculator that rounds
or truncates its final value to the dollar passes the entire rest of the suite. This is the only
scenario separating $1,093.36 from $1,093.00. It pairs with Scenario 5, the same stream type at a
whole-dollar amount.

## Research Sources

| Snapshot | Tier | Title | URL | Retrieved |
|---|---|---|---|---|
| `2026-08-31--45-cfr-400-208` | 1 | 45 CFR 400.208 - Federal funding for nonrefugee children in a family unit | https://www.ecfr.gov/api/versioner/v1/full/2026-08-28/title-45.xml?part=400&section=400.208 | 2026-08-31 |
| `2026-08-31--45-cfr-400-211` | 1 | 45 CFR 400.211 - Federal funding for RCA and RMA eligibility period | https://www.ecfr.gov/api/versioner/v1/full/2026-08-28/title-45.xml?part=400&section=400.211 | 2026-08-31 |
| `2026-08-31--45-cfr-400-40` | 1 | 45 CFR 400.40 - Scope (Subpart D, immigration status) | https://www.ecfr.gov/api/versioner/v1/full/2026-08-28/title-45.xml?part=400&section=400.40 | 2026-08-31 |
| `2026-08-31--45-cfr-400-41` | 1 | 45 CFR 400.41 - Definitions (Subpart D) | https://www.ecfr.gov/api/versioner/v1/full/2026-08-28/title-45.xml?part=400&section=400.41 | 2026-08-31 |
| `2026-08-31--45-cfr-400-43` | 1 | 45 CFR 400.43 - Requirements for documentation of refugee status | https://www.ecfr.gov/api/versioner/v1/full/2026-08-28/title-45.xml?part=400&section=400.43 | 2026-08-31 |
| `2026-08-31--45-cfr-400-50` | 1 | 45 CFR 400.50 - Opportunity to apply for cash assistance | https://www.ecfr.gov/api/versioner/v1/full/2026-08-28/title-45.xml?part=400&section=400.50 | 2026-08-31 |
| `2026-08-31--45-cfr-400-51` | 1 | 45 CFR 400.51 - Determination of eligibility under other programs | https://www.ecfr.gov/api/versioner/v1/full/2026-08-28/title-45.xml?part=400&section=400.51 | 2026-08-31 |
| `2026-08-31--45-cfr-400-53` | 1 | 45 CFR 400.53 - General eligibility requirements | https://www.ecfr.gov/api/versioner/v1/full/2026-08-28/title-45.xml?part=400&section=400.53 | 2026-08-31 |
| `2026-08-31--45-cfr-400-56` | 1 | 45 CFR 400.56 - Structure (public/private RCA) | https://www.ecfr.gov/api/versioner/v1/full/2026-08-28/title-45.xml?part=400&section=400.56 | 2026-08-31 |
| `2026-08-31--45-cfr-400-58` | 1 | 45 CFR 400.58 - Content and submission of public/private RCA plan | https://www.ecfr.gov/api/versioner/v1/full/2026-08-28/title-45.xml?part=400&section=400.58 | 2026-08-31 |
| `2026-08-31--45-cfr-400-59` | 1 | 45 CFR 400.59 - Eligibility for the public/private RCA program | https://www.ecfr.gov/api/versioner/v1/full/2026-08-28/title-45.xml?part=400&section=400.59 | 2026-08-31 |
| `2026-08-31--45-cfr-400-60` | 1 | 45 CFR 400.60 - Payment levels | https://www.ecfr.gov/api/versioner/v1/full/2026-08-28/title-45.xml?part=400&section=400.60 | 2026-08-31 |
| `2026-08-31--45-cfr-400-62` | 1 | 45 CFR 400.62 - Treatment of eligible secondary migrants, asylees, and Cuban/Haitian entrants | https://www.ecfr.gov/api/versioner/v1/full/2026-08-28/title-45.xml?part=400&section=400.62 | 2026-08-31 |
| `2026-08-31--45-cfr-400-66` | 1 | 45 CFR 400.66 - Eligibility and payment levels in a publicly-administered RCA program | https://www.ecfr.gov/api/versioner/v1/full/2026-08-28/title-45.xml?part=400&section=400.66 | 2026-08-31 |
| `2026-09-01--45-cfr-400-94-rma-eligibility` | 1 | 45 CFR 400.94 - Determination of eligibility for Medicaid | https://www.ecfr.gov/api/versioner/v1/full/2026-08-28/title-45.xml?part=400&section=400.94 | 2026-09-01 |
| `2026-09-01--45-cfr-401-2-cuban-haitian-entrant` | 1 | 45 CFR 401.2 - Definitions (Cuban/Haitian entrant), the definition incorporated by 45 CFR 400.43(a)(4) | https://www.ecfr.gov/api/versioner/v1/full/2026-08-28/title-45.xml?part=401&section=401.2 | 2026-09-01 |
| `2026-09-01--acf-missouri-replacement-designees` | 1 | ACF ORR - Missouri Replacement Designees policy guidance | https://acf.gov/orr/policy-guidance/missouri-replacement-designees | 2026-09-01 |
| `2026-09-01--eo-14163-realigning-usrap` | 1 | Executive Order 14163 - Realigning the United States Refugee Admissions Program (90 FR 8459, 2025-01-30) | https://www.govinfo.gov/content/pkg/FR-2025-01-30/html/2025-02011.htm | 2026-09-01 |
| `2026-09-01--fr-2021-21369-ppp-rca-inflationary-increase` | 1 | 86 FR 54466 - Public/Private Refugee Cash Assistance Inflationary Increase (new RCA monthly payment ceilings), published 2021-10-01 | https://www.govinfo.gov/content/pkg/FR-2021-10-01/html/2021-21369.htm | 2026-09-01 |
| `2026-09-01--fr-2025-04839-rca-rma-4-months` | 1 | 90 FR 13370 - ORR Notice of Change of Eligibility (4-month period) - SUPERSEDED by 91 FR 43107 | https://www.govinfo.gov/content/pkg/FR-2025-03-21/html/2025-04839.htm | 2026-09-01 |
| `2026-09-01--fr-2026-14095-rca-rma-8-months` | 1 | 91 FR 43107 - ORR Notice: Change in Eligibility Period for RCA and RMA (4 to 8 months), published 2026-07-14 | https://www.govinfo.gov/content/pkg/FR-2026-07-14/html/2026-14095.htm | 2026-09-01 |
| `2026-09-01--mo-hb11-fy2026-budget-notes-dss-family-support` | 2 | Missouri Senate FY2026 Budget Notes - HB 11, DSS Division of Family Support (After Veto); Section 11.127 Office of Refugee Resettlement | https://www.senate.mo.gov/25info/Comm/BudgetNotes/BudgetNotes/HB%2011%20-%20DSS%202%20-%20Family%20Support%20(After%20Veto).pdf | 2026-09-01 |
| `2026-09-01--mo-state-plan-fy2024` | 1 | Missouri Refugee Program State Plan FY2024 (MO-ORA, final) - the approved public/private RCA plan under 45 CFR 400.58 | https://moora.org/s/SP_Missouri-Final-Plan_FY24-m3pe.pdf | 2026-09-01 |
| `2026-09-01--mo-ta-appendix-c-max-grant-amounts` | 2 | Missouri DSS Temporary Assistance Appendix C - Maximum Grant Amounts and Maximum Cash Diversion Amounts (08/2024) | https://dssmanuals.mo.gov/wp-content/uploads/2024/09/TA-AppendixC.pdf | 2026-09-01 |
| `2026-09-01--moora-cash-assistance` | 2 | MO-ORA - Cash Assistance (Refugee Cash Assistance) program page | https://moora.org/programs/cash-assistance | 2026-09-01 |
| `2026-09-01--moora-contact` | 2 | MO-ORA - Contact | https://moora.org/contact | 2026-09-01 |
| `2026-09-01--moora-data-reports` | 2 | MO-ORA - Data & Reports (index page linking the Missouri State Plan FY24) | https://moora.org/data-reports | 2026-09-01 |
| `2026-09-01--moora-faq` | 2 | MO-ORA - FAQ | https://moora.org/faq | 2026-09-01 |
| `2026-09-01--moora-our-partners` | 2 | MO-ORA - Our Partners (contracted resettlement agencies) | https://moora.org/ourpartners | 2026-09-01 |
| `2026-09-01--moora-who-we-serve` | 2 | MO-ORA - Who We Serve | https://moora.org/who-we-serve | 2026-09-01 |
| `2026-09-01--orr-cash-and-medical-assistance-program` | 1 | ORR - Cash and Medical Assistance (CMA) program page (the destination of MO-ORA's only Learn More link on its RCA page) | https://acf.gov/orr/programs/refugees/cma | 2026-09-01 |
| `2026-09-01--orr-dcl-22-01-rca-payment-ceilings` | 1 | ORR DCL 22-01 - PPP RCA maximum payment ceilings (effective 2021-10-01) | https://acf.gov/sites/default/files/documents/orr/ORR-DCL-22-01-PPP-RCA-maximum-payment-ceilings.pdf | 2026-09-01 |
| `2026-09-01--orr-dcl-22-12-rca-rma-12-months` | 1 | ORR DCL 22-12 - Expansion of RCA and RMA Eligibility Period (8 to 12 months) - SUPERSEDED by 91 FR 43107 | https://acf.gov/sites/default/files/documents/orr/ORR-DCL-22-12-Expansion-of-RCA-and-RMA-Eligibility-Period.pdf | 2026-09-01 |
| `2026-09-01--orr-dcl-22-20-uhp-rca-rma` | 1 | ORR DCL 22-20 - Clarification Related to Ukrainian Humanitarian Parolees Eligibility for RCA and RMA | https://acf.gov/sites/default/files/documents/orr/DCL-22-20-Clarification-Related-to-UHPs-Eligibility-for-RCA-RMA.pdf | 2026-09-01 |
| `2026-09-01--orr-key-state-contacts` | 1 | ORR - Key State Contacts (State Refugee Coordinator directory) | https://acf.gov/orr/grant-funding/key-state-contacts | 2026-09-01 |
| `2026-09-01--orr-pl-21-04-public-private-rca` | 1 | ORR-PL-21-04 - Guidance for Public-Private Refugee Cash Assistance Programs | https://acf.gov/sites/default/files/documents/orr/ORR-PL-21-04-Public-Private-RCA-Programs.pdf | 2026-09-01 |
| `2026-09-01--orr-pl-21-07-si-sq-parole` | 1 | ORR-PL-21-07 - Additional Form of Documentation for Iraqi and Afghan Special Immigrants - SUPERSEDED: rescinded by ORR-PL-22-02 | https://acf.gov/sites/default/files/documents/orr/ORR-PL-21-07-SI-SQ-Parole-8.3.2021.pdf | 2026-09-01 |
| `2026-09-01--orr-pl-22-01-afghan-humanitarian-parolees` | 1 | ORR-PL-22-01 - ORR Authority to Serve Afghan Humanitarian Parolees (arrival timeframe) | https://acf.gov/sites/default/files/documents/orr/ORR-PL-22-01-ORR-Authority-to-Serve-Afghan-Humanitarian-Parolees.pdf | 2026-09-01 |
| `2026-09-01--orr-pl-22-02-afghan-categories-revised` | 1 | ORR-PL-22-02 (Revised) - Additional ORR-Eligible Statuses and Categories and Documentation Requirements for Afghan Nationals | https://acf.gov/sites/default/files/documents/orr/ORR-PL-22-02-Additional-ORR-Eligibility-Categories-and-Documentation-Requirements-for-Afghan-Nationals-Revised.pdf | 2026-09-01 |
| `2026-09-01--orr-pl-22-13-ukrainian-humanitarian-parolees` | 1 | ORR-PL-22-13 - Ukrainian Humanitarian Parolees Eligible for ORR Benefits and Services | https://acf.gov/orr/policy/policy-letters/22-13 | 2026-09-01 |
| `2026-09-01--orr-pl-23-04-expanding-income-disregards-rca` | 1 | ORR-PL-23-04 - Expanding Income Disregards for Refugee Cash Assistance | https://acf.gov/sites/default/files/documents/orr/pl-23-04-expanding-income-disregards-for-rca.pdf | 2026-09-01 |
| `2026-09-01--orr-pl-25-04-rss-recipients-fy2026` | 1 | ORR-PL-25-04 - Changes to ORR Refugee Support Services Recipients Beginning in FY2026 | https://acf.gov/orr/policy/policy-letters/25-04 | 2026-09-01 |
| `2026-09-01--orr-program-of-initial-resettlement` | 1 | ORR - Program of Initial Resettlement (PIR), which replaced the Department of State Reception and Placement program from 2026-01-01 | https://acf.gov/orr/programs/refugees/pir | 2026-09-01 |
| `2026-09-01--orr-state-of-missouri-programs-by-locality` | 1 | ORR - State of Missouri: Programs and Services by City | https://acf.gov/orr/policy-guidance/state-missouri-programs-and-services-locality | 2026-09-01 |
| `2026-09-01--rpc-admissions-and-arrivals` | 2 | Refugee Processing Center (RPC/WRAPS) - Admissions and Arrivals data index | https://www.rpc.state.gov/admissions-and-arrivals/ | 2026-09-01 |
| `2026-09-04--orr-pl-23-04-income-disregards-rca-rev-2026` | 1 | ORR-PL-23-04 - Income Disregards for Refugee Cash Assistance (Revised February 2, 2026) | https://acf.gov/sites/default/files/documents/orr/ORR-PL-23-04---Income-Disregards-for-RCA.pdf | 2026-09-04 |

**Supersede chain.** `2026-09-01--orr-pl-23-04-expanding-income-disregards-rca` (ORR-PL-23-04 as
revised 2025-02-10) is **superseded by**
`2026-09-04--orr-pl-23-04-income-disregards-rca-rev-2026` (as revised 2026-02-02, served from a
different acf.gov filename). The later revision names ORR's Program of Initial Resettlement
directly and removes the cap limiting the disregard to the R&P grant amount. Both remain listed;
no criterion, data gap, or value statement cites the superseded copy.

## Implementation

Build requirements not already stated by the criteria, Benefit Value, or Acceptance Criteria.
Calculator: `programs/programs/white_labels/mo/rca`, class `MoRca`.

**Constants.** `WORK_EXEMPTION = 90`. `EARNED_DISREGARD = 0.75` is the fraction **disregarded**, so
the countable fraction every formula in this spec writes as `× 0.25` is `1 − EARNED_DISREGARD`;
multiplying post-exemption earnings by `EARNED_DISREGARD` itself inverts the rule and flips
Scenario 2 to Ineligible. `ELIGIBILITY_PERIOD_MONTHS = 8` is the value multiplier.
`RCA_MAX_PAYMENT` holds the tabulated sizes 1–5 only, `ADDITIONAL_MEMBER_AMOUNT = 113` the
increment.

**Calculation order.** Resolve the household into cases *before anything else* — the split
determines both the criterion-4 threshold and the value. Reach the payment standard only through
`rca_max_payment(case_size)`, never by subscripting `RCA_MAX_PAYMENT`, which has no entry at the
sizes Scenarios 8 and 18 exercise.

**Two prohibitions.** Do not reuse `Screen.num_children(child_relationship=[…])` for the split: it
compares the deprecated `age` column rather than `calc_age()`, which would move the age-18 boundary
off the birth month Scenario 15 pins. Do not return the award from both value hooks —
`Eligibility.value` is `household_value` plus the sum of the eligible members' values, so the split
Acceptance Criterion 12 requires is what stops the award being counted twice.

**Framework mapping.** The per-case assistance unit is not native to `ProgramCalculator`.
`eligible()` accumulates "at least one member eligible" and passes it to `Eligibility.condition()`
before `household_eligible()` runs (`programs/framework/base.py`), so **≥ 1 eligible member ⇔ ≥ 1
payable case**: household eligibility follows from Acceptance Criterion 12's per-member marks
rather than being computed separately. Scenario 17 returns Eligible on exactly this path; Scenario
10 returns Ineligible because its only member is removed. Those marks are user-visible on the
results card, so they are part of the calculator's contract — `review-notes.md` records how
`ProgramCard` renders them.

**Income dependencies.** `dependencies = ["income_type", "income_amount", "income_frequency"]` on
`MoRca`. `income_type` is the non-obvious one: a null `type` does **not** raise the way a null
`amount` or `frequency` does, because `calc_gross_income` matches unearned as
`type not in EARNED_INCOME_TYPES`, which `None` satisfies — so left undeclared it would be silently
counted as unearned in full, the exclusionary direction.
`programs/programs/cross_white_label/family_planning/tx.py` declares the same three.

## Acceptance Criteria

1. `rca_max_payment(case_size)` returns the Benefit Value table's figures for case sizes 1–5, and
   `$1,217 + $113 × (n − 5)` for n greater than 5; it is a function, and no code path subscripts
   `RCA_MAX_PAYMENT` directly, which holds sizes 1–5 only.
2. Earned income is computed per member: the $90 exemption applies once per earning member, never
   once per case, then the quarter-countable disregard, clamped at zero. A member earning
   $1,000.00/month contributes $227.50, one earning $600.00/month contributes $127.50, and one
   earning $50.00/month contributes $0.00 — never a negative amount. `selfEmployment` counts as
   earned, and a non-monthly `IncomeStream.frequency` is normalised through
   `IncomeStream.monthly()` before the exemption is applied.
3. Unearned income is added to net countable income without any exemption or disregard, except
   that `cashAssistanceOther` and `gifts` are excluded entirely; `childSupport` and every other
   unearned type are still counted in full.
4. A case whose net countable income equals `rca_max_payment(case_size)` exactly is **ineligible**;
   a case one dollar below is eligible and returns a positive value.
5. A member with a reported `sSI` income stream, or a reported `cashAssistance` income stream, is
   removed from their case together with their income; the remaining members of that household are
   still evaluated, and a case left with no members contributes nothing.
6. No member or case that reports no TANF income is made ineligible on the basis of TANF-unit
   membership or predicted TANF eligibility, and the calculator makes no `CurrentBenefit` or
   `has_benefit` read for TANF.
7. No member is excluded on age 65 or over, blindness, or disability while not receiving SSI — a
   null `disabled`, `visually_impaired`, or `long_term_disability` does not exclude either — nor on
   `student` or `student_full_time`, nor on elapsed time since arrival.
8. A member aged 18 or over whose `relationship` is a child type forms a separate single-member
   case; a member aged 17 does not; a member whose `calc_age()` is `None` does not. Each case's
   value is computed against its own size, income is summed per case rather than pooled across the
   household, an ineligible case contributes nothing, and the household value is the sum of the
   eligible cases.
9. The stored value equals the household's monthly RCA award multiplied by 8, and `value_format`
   is `lump_sum`, so the stored total reaches the results card undivided.
10. No intermediate step rounds or truncates: a member earning $1,305.00/month contributes
    $303.75 countable, a case at $477.50 net against the $1,104 standard returns $626.50/month,
    and a case with $400.33/month of unearned income returns $136.67/month and a value of
    $1,093.36. The value is committed to the cent and never rounded to the dollar.
11. A screen carrying an income stream with a missing `type`, `amount` or `frequency` is
    suppressed rather than valued: `can_calc()` returns False because all three are declared
    dependencies, `calc()` raises `DependencyError`, and the eligibility loop omits the program
    from the results. A test asserts the `DependencyError`, not the absence of one.
12. A member is marked ineligible in exactly two situations — they were removed from their case on
    a reported `sSI` or `cashAssistance` stream, or their case's net countable income is not under
    that case's payment standard — and every other member is marked eligible. The household award
    is returned from `household_value()` alone, with `member_value()` returning 0.
13. Every scenario in Test Scenarios returns its stated verdict, its stated per-member
    eligibility marks, and, where eligible, its stated dollar value agreeing to the cent.
14. `MoRca` declares `program_code = "mo_rca"`, so the registry builds.
