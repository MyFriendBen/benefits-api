# Refugee Cash Assistance (KS) — Program Spec

- **Program key**: `ks_rca` (`programs/programs/white_labels/ks/rca/calculator.py`, class `KsRca`)
- **Base federal program**: none (state-administered federal ORR program)
- **White label**: KS
- **Engine**: MFB custom
- **Added to MFB**: not implemented — Discovery only
- **Spec last updated**: 2026-09-04
- **Sources verified as of**: 2026-09-04

## Covered Eligibility Criteria

Kansas operates the **public/private (PPP)** RCA model, so 45 CFR §§ 400.56–400.63 govern
eligibility and payment levels and § 400.66 (publicly-administered) does not apply. All three
criteria below must hold.

No source states Kansas residence as a condition on the applicant, so it is not a criterion. It
is enforced structurally: the program row is scoped by `white_label` (Program, ForeignKey),
matched against `white_label` (Screen, ForeignKey), so a non-Kansas screen never reaches this
program.

- Source: ORR Annual Report to Congress FY 2020, p. 19 — "All Replacement Designees (RDs) opted to use the PPP model" — [snapshot `2026-09-02--orr-annual-report-congress-fy2020`](../../../sources/ks/ks_rca/2026-09-02--orr-annual-report-congress-fy2020/content.md), accessed 2026-09-02
- Source: ORR Annual Report to Congress FY 2020, p. 19 — "In FY 2020, RDs administered the Refugee Resettlement Program in the states of Alaska, Kentucky, Kansas, Maine, Missouri, Nevada, Tennessee, and Texas" — [snapshot `2026-09-02--orr-annual-report-congress-fy2020`](../../../sources/ks/ks_rca/2026-09-02--orr-annual-report-congress-fy2020/content.md), accessed 2026-09-02
- Source: Kansas Office for Refugees, home page — "replacement designee that administers refugee services and benefits in Kansas" — [snapshot `2026-09-02--ksor-home`](../../../sources/ks/ks_rca/2026-09-02--ksor-home/content.md), accessed 2026-09-02
- Source: KEES Web Help, Refugee Cash Assistance (RCA) — "Do not register any RCA program blocks in KEES." — [snapshot `2026-09-02--kees-webhelp-rca`](../../../sources/ks/ks_rca/2026-09-02--kees-webhelp-rca/content.md), accessed 2026-09-02
- Source: 45 CFR 400.66 (heading) — "Eligibility and payment levels in a publicly-administered RCA program." — [snapshot `2026-09-02--45-cfr-400-66`](../../../sources/ks/ks_rca/2026-09-02--45-cfr-400-66/content.md), accessed 2026-09-02

1. **The applicant has an ORR-eligible immigration status or category, or is a qualifying dependent child in the same family unit under § 400.53(a)(3) and § 400.208**
   - Evaluation scope: `config`
   - Captured via: config `legal_status_required` (Program, M2M to `LegalStatus`) — results-display metadata. The screener collects no per-member immigration status, and the backend never applies this field as an eligibility gate: it is read into a list and emitted in the response payload for the frontend to filter on.
   - Implementation note: 45 CFR 400.43(a) enumerates the federal statuses; KSOR's published list is broader and names the populations Kansas actually serves, including its open-ended tail ("and other vulnerable populations"), which the config cannot represent — `legal_status_required` carries only the named statuses.
   - Implementation note: the ORR-eligible population is not a single regulatory list. 45 CFR 400.43(a) supplies the core regulatory categories, and later congressional designations add others: ORR's own reporting lists Iraqi and Afghan Special Immigrant Visa holders, trafficking victims, Amerasians, SIJS and U-visa holders and further populations as Congress designates them, and its current policy letters treat Afghans paroled through Operation Allies Welcome as ORR-eligible under section 412(b)(1) of the INA. MFB collects no per-member immigration status, so `legal_status_required` can only be expressed in MFB's six user-selected `LegalStatus` values: refugees and asylees → `refugee` (MFB's merged Refugee/Asylee bucket); parolees, Cuban and Haitian entrants and trafficking survivors → `otherWithWorkPermission` (MFB's work-authorized lawfully-present catch-all); SIV holders, who are admitted *as* lawful permanent residents, and anyone who has since adjusted to LPR → `gc_5plus` and `gc_5less`. `citizen` and `non_citizen` are excluded: citizens are not ORR-eligible, and MFB's `non_citizen` denotes undocumented status. The committed row is `["refugee", "otherWithWorkPermission", "gc_5plus", "gc_5less"]`.
   - Implementation note: three of those four MFB buckets are **broader than the federal categories they stand in for** — `otherWithWorkPermission` covers work-authorized lawfully-present people who are not an ORR-eligible category at all, and `gc_5plus`/`gc_5less` cover LPRs generally. The row is therefore the committed **inclusive MFB platform approximation**, not a claim that everyone it reaches qualifies for RCA; the administering agency makes the status determination. The two green-card buckets are retained because § 400.43(a)(6) makes an LPR ORR-eligible only if they previously held a qualifying status, and MFB cannot tell whether a given LPR did — excluding them would hide the program from every adjusted refugee, asylee and SIV holder.
   - Implementation note: Federal funding is available for a unit of refugee parent(s) plus their nonrefugee children, but not for a nonrefugee adult, nor for nonrefugee children where one parent in the unit is a nonrefugee (§ 400.208). This list is what `legal_status_required` must carry.
   - Source: 45 CFR 400.43(a)(6) — "Admitted for permanent residence, provided the individual previously held one of the statuses identified above." — [snapshot `2026-09-02--45-cfr-400-43`](../../../sources/ks/ks_rca/2026-09-02--45-cfr-400-43/content.md), accessed 2026-09-02
   - Source: 45 CFR 400.53(a)(3) — "Meet immigration status and identification requirements in subpart D of this part or are the dependent children of, and part of the same family unit as, individuals who meet the requirements in subpart D, subject to the limitation in § 400.208 with respect to nonrefugee children; and" — [snapshot `2026-09-02--45-cfr-400-53`](../../../sources/ks/ks_rca/2026-09-02--45-cfr-400-53/content.md), accessed 2026-09-02
   - Source: 45 CFR 400.208(b) — "Federal funding is not available for a State's expenditures for assistance and services provided to a nonrefugee adult member of a family unit or to a nonrefugee child or children in a family unit if one parent in the family unit is a nonrefugee." — [snapshot `2026-09-02--45-cfr-400-208`](../../../sources/ks/ks_rca/2026-09-02--45-cfr-400-208/content.md), accessed 2026-09-02
   - Source: 45 CFR 400.43(a)(2) — "Admitted as a refugee under section 207 of the Act;" — [snapshot `2026-09-02--45-cfr-400-43`](../../../sources/ks/ks_rca/2026-09-02--45-cfr-400-43/content.md), accessed 2026-09-02
   - Source: ORR Annual Report to Congress FY 2020, p. 4, n.1 — "ORR is authorized to provides services to refugees and other populations, including asylees, Cuban/Haitian Entrants, Iraqi and Afghan special immigrant visa holders, Amerasians, Victims of Trafficking, Special Immigration Juvenile Status holders, U-visa status holders, and other populations as designated by Congress." — [snapshot `2026-09-02--orr-annual-report-congress-fy2020`](../../../sources/ks/ks_rca/2026-09-02--orr-annual-report-congress-fy2020/content.md), accessed 2026-09-02
   - Source: ORR Policy Letter 23-04 (revised 2026-02-02), n.3 — "ORR uses the term “refugees” to include those ORR-eligible populations who are refugees and additional individuals (e.g., certain Afghans who arrived through Operation Allies Welcome) who are eligible for initial resettlement services as authorized by section 412(b)(1) of the Immigration and Nationality Act." — [snapshot `2026-09-03--orr-pl-23-04-income-disregards-pir`](../../../sources/ks/ks_rca/2026-09-03--orr-pl-23-04-income-disregards-pir/content.md), accessed 2026-09-03
   - Source: Kansas Office for Refugees, Frequently Asked Questions — "Kansas Office for Refugees serves Refugees, Asylees, Survivors of Human Trafficking, Holders of Special Immigrant Visas, Cuban and Haitian Entrants, Humanitarian Parolees, and other vulnerable populations." — [snapshot `2026-09-02--ksor-faq`](../../../sources/ks/ks_rca/2026-09-02--ksor-faq/content.md), accessed 2026-09-02

2. **The applicant is ineligible for TANF**
   - Evaluation scope: `household`
   - Captured via: strict dependency `program_eligible("ks_tanf")` (ProgramCalculator), plus accessor `has_base_benefit("tanf")` (Screen) for reported receipt
   - Implementation note: the sourced rule is *ineligibility*, not non-receipt, and it is stated of the individual applicant; MFB carries no per-member TANF signal, because both halves of the test are household-scoped in MFB — `ks_tanf` is an SPM-unit determination and the current-benefit tile is collected for the household. Kansas routes refugee families with children to TANF rather than RCA, so in practice RCA reaches households TANF cannot.
   - Implementation note: the eligible-but-not-receiving half is `program_eligible("ks_tanf")`, which is **strict**. `self.data` holds only the programs already calculated, so an absent `ks_tanf` result raises `DependencyError` and `ks_rca` is left out of the results rather than reported on a guess: for an exclusionary upstream, treating "not calculated" as "not eligible" offers the program to a household whose TANF answer is unknown. Two consequences for the calculator: `ks_tanf` must be listed in `screener/views.py` `CALC_ORDER` ahead of `ks_rca`, since unlisted programs sort last in arbitrary relative order; and `ks_rca` declares `ks_tanf`'s own screener dependencies — `age`, `county`, `income_type`, `income_amount`, `income_frequency` — alongside its own, so the two become uncalculable together rather than RCA answering where TANF cannot. `cesn_energy_ebt` is the shipped shape of the same gate.
   - Implementation note: reported receipt is `has_base_benefit("tanf")`, which matches a base program across white-label variants and so covers KS's `ks_tanf` row. A generic `cashAssistance` income stream is deliberately not read: MFB labels it "Cash Assistance Grant", which is broader than TANF, while the source excludes people ineligible for or receiving TANF specifically.
   - Implementation note: 45 CFR 400.53(a)(2) also names OAA, AB, APTD and AABD; 45 CFR 400.51(b)(2) scopes those four to the territories, so they are inoperative in Kansas.
   - Source: 45 CFR 400.53(a)(2) — "Are ineligible for TANF, SSI, OAA, AB, APTD, and AABD programs;" — [snapshot `2026-09-02--45-cfr-400-53`](../../../sources/ks/ks_rca/2026-09-02--45-cfr-400-53/content.md), accessed 2026-09-02
   - Source: 45 CFR 400.51(b)(2) — "(2) OAA, AB, APTD, or AABD. In Guam, Puerto Rico, and the Virgin Islands—" — [snapshot `2026-09-02--45-cfr-400-51`](../../../sources/ks/ks_rca/2026-09-02--45-cfr-400-51/content.md), accessed 2026-09-02
   - Source: KEES Web Help, Refugee Cash Assistance (RCA) — "If an RCA applicant has children, the user should process the case under the TANF program." — [snapshot `2026-09-02--kees-webhelp-rca`](../../../sources/ks/ks_rca/2026-09-02--kees-webhelp-rca/content.md), accessed 2026-09-02

3. **The applicant is not receiving SSI cash assistance**
   - Evaluation scope: `member`
   - Captured via: accessor `member_reports_ssi_amount(member)` (`programs/framework/pe_dependencies/receipt.py`), which reads that member's own `sSI` income amount; plus `screen_reports_ssi_without_amount(screen)` read against `household_size` (Screen, IntegerField) for the one-member case
   - Implementation note: SSI disqualifies on receipt, never on eligibility. § 400.51(b)(1)(ii) and ORR PL 21-04 § I.A both keep RCA in payment for an SSI-eligible applicant until SSI cash assistance actually begins, so a dependency on MFB's SSI eligibility result would deny RCA to every aged, blind or disabled applicant awaiting a determination — the opposite of what the regulation requires.
   - Implementation note: the exclusion is the member's, not the household's. A member reporting an `sSI` amount drops out of the RCA case and the rest of the household keeps its eligibility, which is the case-splitting ORR PL 21-04 § I.A n.5 provides for. Where no member survives the test, `Eligibility.condition(one_member_eligible)` makes the household ineligible.
   - Implementation note: a ticked SSI current-benefit tile with no reported amount is read against the household's size, because the ambiguity it carries is a function of that size. With more than one member the tile names no recipient and nothing in the screener tells them apart (`screen_reports_ssi_without_amount`), so no member is excluded — MFB does not deny a household on a tile it cannot attribute. Where `household_size` is 1 there is no ambiguity to preserve: the tile identifies the sole member as the recipient. Committed behavior: a member-reported `sSI` amount excludes that member; a tile with no amount in a one-person household excludes the sole member; a tile with no amount in a household of two or more excludes nobody.
   - Source: ORR Policy Letter 21-04, § I.A — "A client that is eligible for Supplemental Security Income (SSI) may only receive RCA and RCA differential payments until cash assistance under the SSI program is provided, at which point the client is ineligible for RCA." — [snapshot `2026-09-02--orr-pl-21-04-public-private-rca`](../../../sources/ks/ks_rca/2026-09-02--orr-pl-21-04-public-private-rca/content.md), accessed 2026-09-02
   - Source: 45 CFR 400.51(b)(1)(ii) — "it must furnish such assistance until eligibility for cash assistance under the SSI program is determined, provided the conditions of eligibility for refugee cash assistance continue to be met." — [snapshot `2026-09-02--45-cfr-400-51`](../../../sources/ks/ks_rca/2026-09-02--45-cfr-400-51/content.md), accessed 2026-09-02
   - Source: 45 CFR 400.53(a)(2) — "Are ineligible for TANF, SSI, OAA, AB, APTD, and AABD programs;" — [snapshot `2026-09-02--45-cfr-400-53`](../../../sources/ks/ks_rca/2026-09-02--45-cfr-400-53/content.md), accessed 2026-09-02
   - Source: ORR Policy Letter 21-04, § I.A n.5 — "b) Particular members of the case are ineligible for RCA (e.g., a family member receives SSI)," — [snapshot `2026-09-02--orr-pl-21-04-public-private-rca`](../../../sources/ks/ks_rca/2026-09-02--orr-pl-21-04-public-private-rca/content.md), accessed 2026-09-02

## Missing Eligibility Criteria (Data Gaps)

1. **Income at or below the RCA income eligibility standard established for Kansas, after the required exclusions and any approved disregards**
   - Why: under the public/private model the standard is proposed by the administering agency and approved by ORR, and recorded in the state plan. Kansas's standard is not published, so there is no threshold to evaluate — a source gap, not a screener gap. The required exclusions (resources in the country of origin, sponsor income, and the initial-resettlement cash grants § 400.59(d) names — which ORR now reads to cover its Program of Initial Resettlement, the successor to the Department of State's Reception and Placement program) and any approved disregards would modify a threshold that is itself unknown.
   - Handling: MFB does not exclude an otherwise qualifying household on this basis. The administering RCA agency makes the final income-eligibility determination. This is an MFB inclusivity assumption, not a claim about Kansas policy. KSOR also describes RCA recipients as "not yet self-sufficient". Published sources do not show how Kansas operationalizes that condition separately from its unpublished RCA income rules, so MFB handles it inclusively as part of this same unresolved financial-eligibility gap.
   - Source: Kansas Office for Refugees, Programs — "who are not eligible for Temporary Assistance for Needy Families or other cash assistance programs and who are not yet self-sufficient" — [snapshot `2026-09-02--ksor-programs`](../../../sources/ks/ks_rca/2026-09-02--ksor-programs/content.md), accessed 2026-09-02
   - Source: ORR Policy Letter 21-04, § I — "Economic self-sufficiency means earning a total family income at a level that enables a family unit to support itself without receipt of a cash assistance grant." — [snapshot `2026-09-02--orr-pl-21-04-public-private-rca`](../../../sources/ks/ks_rca/2026-09-02--orr-pl-21-04-public-private-rca/content.md), accessed 2026-09-02
   - Source: 45 CFR 400.59(a) — "Eligibility for refugee cash assistance under the public/private program is limited to those who meet the income eligibility standard established by the State after consultation with local resettlement agencies in the State." — [snapshot `2026-09-02--45-cfr-400-59`](../../../sources/ks/ks_rca/2026-09-02--45-cfr-400-59/content.md), accessed 2026-09-02
   - Source: 45 CFR 400.59(b) — "Any resources remaining in the applicant's country of origin may not be considered in determining income eligibility." — [snapshot `2026-09-02--45-cfr-400-59`](../../../sources/ks/ks_rca/2026-09-02--45-cfr-400-59/content.md), accessed 2026-09-02
   - Source: 45 CFR 400.59(c) — "A sponsor's income and resources may not be considered to be accessible to a refugee solely because the person is serving as a sponsor." — [snapshot `2026-09-02--45-cfr-400-59`](../../../sources/ks/ks_rca/2026-09-02--45-cfr-400-59/content.md), accessed 2026-09-02
   - Source: 45 CFR 400.59(d) — "Any cash grant received by a refugee under the Department of State or Department of Justice Reception and Placement programs may not be considered in determining income eligibility." — [snapshot `2026-09-02--45-cfr-400-59`](../../../sources/ks/ks_rca/2026-09-02--45-cfr-400-59/content.md), accessed 2026-09-02
   - Source: ORR Policy Letter 23-04 (revised 2026-02-02), § I — "because the Department of State’s R&P program has ended and has been replaced by ORR’s Program of Initial Resettlement (PIR), the regulation does not address the services refugees are currently receiving." — [snapshot `2026-09-03--orr-pl-23-04-income-disregards-pir`](../../../sources/ks/ks_rca/2026-09-03--orr-pl-23-04-income-disregards-pir/content.md), accessed 2026-09-03
   - Source: ORR Policy Letter 23-04 (revised 2026-02-02), § II — "In conducting a refugee’s income eligibility determination for RCA, States must disregard cash grants a refugee receives from PIR." — [snapshot `2026-09-03--orr-pl-23-04-income-disregards-pir`](../../../sources/ks/ks_rca/2026-09-03--orr-pl-23-04-income-disregards-pir/content.md), accessed 2026-09-03
   - Source: ORR Policy Letter 21-04, § I.B — "The proposed income eligibility standard is subject to ORR approval." — [snapshot `2026-09-02--orr-pl-21-04-public-private-rca`](../../../sources/ks/ks_rca/2026-09-02--orr-pl-21-04-public-private-rca/content.md), accessed 2026-09-02

2. **The applicant is a new arrival still within the ORR eligibility period — 8 months for those whose ORR eligibility date is on or after 2026-01-01**
   - Why: the screener collects no ORR eligibility date, status-grant date, or US entry date, so the window cannot be evaluated.
   - Handling: inclusive — the window is not applied as a gate; the program description carries the time limit so a user past it understands why they may be turned away.
   - Source: 91 FR 43108 (2026-07-14) — "ORR-eligible individuals whose eligibility date is on or after January 1, 2026, will be eligible for up to 8 months of RCA and RMA," — [snapshot `2026-09-02--fr-2026-eligibility-period-8-months`](../../../sources/ks/ks_rca/2026-09-02--fr-2026-eligibility-period-8-months/content.md), accessed 2026-09-02
   - Source: 45 CFR 400.53(a)(1) — "Are new arrivals who have resided in the U.S. less than the RCA eligibility period determined by the ORR Director in accordance with § 400.211;" — [snapshot `2026-09-02--45-cfr-400-53`](../../../sources/ks/ks_rca/2026-09-02--45-cfr-400-53/content.md), accessed 2026-09-02
   - Source: Kansas Office for Refugees, Programs — "for a period no greater than eight (8) months" — [snapshot `2026-09-02--ksor-programs`](../../../sources/ks/ks_rca/2026-09-02--ksor-programs/content.md), accessed 2026-09-02

3. **The applicant is not a full-time student in an institution of higher education**
   - Why: the screener asks whether the member is enrolled "half-time or more in a university, college, or community college as defined by the educational institution" and stores the answer in `student_full_time` (HouseholdMember, BooleanField). Higher education is captured, but half-time and full-time enrolment collapse into the same `true`, and RCA excludes only full-time students.
   - Handling: inclusive — not applied as a gate.
   - Source: 45 CFR 400.53(a)(4) — "Are not full-time students in institutions of higher education, as defined by the Director." — [snapshot `2026-09-02--45-cfr-400-53`](../../../sources/ks/ks_rca/2026-09-02--45-cfr-400-53/content.md), accessed 2026-09-02

4. **An employable applicant has not, without good cause, voluntarily quit employment or refused an offer of appropriate employment within the 30 days before applying, or within a longer applicable disqualification period under § 400.82(c)(2)**
   - Why: the screener collects no prior voluntary-quit or refused-employment history.
   - Handling: inclusive — not applied as a gate.
   - Source: 45 CFR 400.77(a) — "an employable applicant may not, without good cause, within 30 consecutive calendar days immediately prior to the application for assistance (or such longer period required by § 400.82(c)(2), if applicable), have voluntarily quit employment or have refused to accept an offer of employment determined to be appropriate by the State agency or its designee" — [snapshot `2026-09-02--45-cfr-400-77`](../../../sources/ks/ks_rca/2026-09-02--45-cfr-400-77/content.md), accessed 2026-09-02

5. **The RCA case is composed by ORR family-unit rules rather than by MFB household composition**
   - Why: an adult child aged 18 or over of a parent in the case is a separate RCA case, and a case is also split where members live in separate households or are individually ineligible. MFB holds each member's age and their relationship to the primary member, but relationships are recorded only against that member, so full sub-unit membership cannot be reconstructed — an adult child's own spouse or children, or an adult child of a parent who is not the primary member, are invisible. ORR PL 21-04's split examples are not exhaustive, and MFB does not have a verified Kansas-specific rule set sufficient to reconstruct the RCA case from the screener household. Splitting only the head-to-adult-child pair would model otherwise similar multigenerational households inconsistently. Co-residing adult siblings are reached by none of the letter's triggers, which is the composition the multi-person value scenarios assume.
   - Handling: inclusive — the case is taken as the household MFB can see, minus any member excluded under criterion 3. Effect: for a household containing an adult child the composition MFB uses may differ from the RCA case, so the committed value may not match what the split cases would pay.
   - Source: ORR Policy Letter 21-04, § I.A — "An adult child age 18 years or older should be treated as a separate case." — [snapshot `2026-09-02--orr-pl-21-04-public-private-rca`](../../../sources/ks/ks_rca/2026-09-02--orr-pl-21-04-public-private-rca/content.md), accessed 2026-09-02
   - Source: ORR Policy Letter 21-04, § I.A n.5 — "a) The case includes parent/s with dependent children 18 or over," — [snapshot `2026-09-02--orr-pl-21-04-public-private-rca`](../../../sources/ks/ks_rca/2026-09-02--orr-pl-21-04-public-private-rca/content.md), accessed 2026-09-02
   - Source: ORR Policy Letter 21-04, § I.A n.5 — "c) The members of the case live in separate households, or" — [snapshot `2026-09-02--orr-pl-21-04-public-private-rca`](../../../sources/ks/ks_rca/2026-09-02--orr-pl-21-04-public-private-rca/content.md), accessed 2026-09-02

## Priority Criteria

None identified as of 2026-09-04.

## Related Programs

- **Refugee Medical Assistance (RMA)** — the medical sibling on the same ORR clock, administered by KSOR alongside RCA. Own eligibility: short-term medical coverage for refugees who are ineligible for Medicaid. Not part of this program's eligibility or value.
  - Source: ORR — Cash and Medical Assistance — "RMA provides short-term medical coverage to refugees ineligible for Medicaid. The benefits are generally similar to Medicaid." — [snapshot `2026-09-02--orr-cma-program`](../../../sources/ks/ks_rca/2026-09-02--orr-cma-program/content.md), accessed 2026-09-02
- **RCA differential payment** — a top-up an approved PPP agency may pay to an ORR-eligible TANF recipient where the state TANF rate is below the § 400.60 rate. Own eligibility: requires ORR approval of the administering agency's request, including a waiver of § 400.53(a)(2), and an agreement with the state TANF office. Kansas has no evidenced approval, so it is not modelled here.
  - Source: ORR Policy Letter 21-04, § II — "An RCA differential payment is a payment through a PPP RCA program to an eligible TANF recipient in those states where the TANF payment rate is lower than the payment rate listed" — [snapshot `2026-09-02--orr-pl-21-04-public-private-rca`](../../../sources/ks/ks_rca/2026-09-02--orr-pl-21-04-public-private-rca/content.md), accessed 2026-09-02
  - Source: ORR Policy Letter 21-04, § II.B — "recipients, and request a waiver of 45 CFR § 400.53(a)(2)." — [snapshot `2026-09-02--orr-pl-21-04-public-private-rca`](../../../sources/ks/ks_rca/2026-09-02--orr-pl-21-04-public-private-rca/content.md), accessed 2026-09-02

## Benefit Value

- Value: **the lowest Kansas TANF payment standard for the size of the RCA case** — $168 (1), $263 (2), $349 (3), $421 (4), $482 (5), $543 (6), $604 (7), $665 (8), plus $61 for each additional person beyond 8. The case is the household's members minus any member excluded under criterion 3.
- `value_format`: `null` — "Default (Monthly)". RCA is a recurring monthly payment, time-limited to the ORR eligibility period; it is not annualized because the number of months a household receives depends on its ORR eligibility date, which MFB does not collect (Data Gap 2).
- Variation axes: RCA case size
- Source: 45 CFR 400.60(b) — "States and local resettlement agencies may not make payments to refugees that are lower than the State's TANF payment for the same sized family unit." — [snapshot `2026-09-02--45-cfr-400-60`](../../../sources/ks/ks_rca/2026-09-02--45-cfr-400-60/content.md), accessed 2026-09-02
- Source (corroborative — plan content, not the operative rule): 45 CFR 400.58(a)(3) — "Assurance that the payment levels established are not lower than the comparable State TANF amounts;" — [snapshot `2026-09-02--45-cfr-400-58`](../../../sources/ks/ks_rca/2026-09-02--45-cfr-400-58/content.md), accessed 2026-09-02
- Source: State of Kansas TANF State Plan FFY 2024–2026, Appendix 1 p. 29, Shared Living Arrangements, Rural County column — "1 $168 $170 $175 $186" — [snapshot `2026-09-02--ks-tanf-state-plan-ffy2024-2026`](../../../sources/ks/ks_rca/2026-09-02--ks-tanf-state-plan-ffy2024-2026/content.md), accessed 2026-09-02
- Source: State of Kansas TANF State Plan FFY 2024–2026, Appendix 1 — "2 $263 $265 $271 $284" — [snapshot `2026-09-02--ks-tanf-state-plan-ffy2024-2026`](../../../sources/ks/ks_rca/2026-09-02--ks-tanf-state-plan-ffy2024-2026/content.md), accessed 2026-09-02
- Source: State of Kansas TANF State Plan FFY 2024–2026, Appendix 1 — "3 $349 $352 $359 $375" — [snapshot `2026-09-02--ks-tanf-state-plan-ffy2024-2026`](../../../sources/ks/ks_rca/2026-09-02--ks-tanf-state-plan-ffy2024-2026/content.md), accessed 2026-09-02
- Source: State of Kansas TANF State Plan FFY 2024–2026, Appendix 1 — "4 $421 $425 $432 $449" — [snapshot `2026-09-02--ks-tanf-state-plan-ffy2024-2026`](../../../sources/ks/ks_rca/2026-09-02--ks-tanf-state-plan-ffy2024-2026/content.md), accessed 2026-09-02
- Source: State of Kansas TANF State Plan FFY 2024–2026, Appendix 1 p. 29, Shared Living Arrangements — "5+ Add $61 for each additional person" — [snapshot `2026-09-02--ks-tanf-state-plan-ffy2024-2026`](../../../sources/ks/ks_rca/2026-09-02--ks-tanf-state-plan-ffy2024-2026/content.md), accessed 2026-09-02
- Monthly reduction: ORR requires the payment to be reduced month to month by the recipient's income from employment and other sources, after applicable disregards. MFB does not apply the reduction — the schedule and the disregards are part of Kansas's ORR-approved plan, which is not published, so the arithmetic cannot be reproduced — so a household with income may receive less than the figure shown.
- Source: ORR Policy Letter 21-04, § I.C — "On a monthly basis, the PPP-administering agency must also determine continued eligibility for RCA on the basis of income. RCA payments must be reduced on the basis of income from employment and other sources after factoring in applicable disregards." — [snapshot `2026-09-02--orr-pl-21-04-public-private-rca`](../../../sources/ks/ks_rca/2026-09-02--orr-pl-21-04-public-private-rca/content.md), accessed 2026-09-02
- Justification: Kansas's actual RCA payment levels are proposed by KSOR, approved by ORR, and recorded in a state plan that is not published, so MFB cannot show the amount a household will actually receive. The committed figure is a conservative MFB baseline estimate, not Kansas's RCA award: § 400.60(b) and § 400.58(a)(3) forbid RCA payments below the comparable Kansas TANF amount for the same family size, so MFB takes the lowest Kansas TANF standard for each size (Shared Living Arrangements, Rural County), which holds statewide without depending on county-tier or shared-living inputs. Sizes 5 and above apply the plan's own "Add $61 for each additional person" rule to the size-4 figure of $421. **Kansas's approved starting payment level may be higher than the figure shown**, and an individual recipient's monthly payment after the unknown income reduction may be lower.

## Test Scenarios

**Coverage map**

| Rule / variation axis | Scenarios |
|---|---|
| Criterion 1 — ORR-eligible immigration status | none — see Known scenario gaps |
| Criterion 2 — TANF ineligibility dependency | pass: 1–6; fail: 7 (TANF-eligible, not receiving) |
| Criterion 2 — TANF receipt | pass: 1–6; fail: 8 (isolated: household is TANF-ineligible) |
| Criterion 3 — SSI receipt, member scope | pass: 1–6, 11, 12; fail: 9 (sole member excluded), 10 (one of two members excluded), 13 (sole member excluded on the tile) |
| Criterion 3 — receipt only, never SSI eligibility | pass: 12 (SSI-eligible, not receiving) |
| Criterion 3 — SSI tile with no reported amount | pass: 11 (two members — the tile names no recipient); fail: 13 (one member — the tile identifies them) |
| Value — tabulated case sizes | 1 (size 1), 2 (size 2), 3 (size 3), 4 (size 4, last tabulated) |
| Value — extrapolated case sizes | 5 (size 5, first increment), 6 (size 9, repeated increment) |
| Value — case size after a member exclusion | 10 ($168 from a two-member household) |
| Value — unaffected by income | 3 (earned income $2,000/month, value unchanged) |

**Known scenario gaps**:
- **Criterion 1** has no scenario in either direction. Immigration status is carried by the program row's `legal_status_required`, which the screener does not collect and the backend does not evaluate — it is emitted to the frontend as results-display metadata. The config row carries it instead.
- **Kansas residence** is enforced by white-label scoping of the program row rather than by a criterion, so no scenario can falsify it; a non-Kansas screen never reaches this program.
- Data Gaps 1–5 are not scenario subjects: they are handled inclusively and change no verdict. Scenario 3 exercises the *consequences* of Data Gap 1 and of the Benefit Value commitment that income does not reduce the figure shown, which is program behavior rather than a gap test.

### Scenario 1: Single ORR-eligible adult, no other cash assistance — Eligible, $168
**What we're checking**: the baseline eligible path and the table floor for a one-person household.
**Expected**: Eligible — $168 (household size 1 → Kansas TANF minimum standard $168)
**Steps**:
* Location: ZIP `67214`, county `Sedgwick County`
* Person 1: `birth_year` 1994, `birth_month` 3 (born March 1994), head of household, no income
* Current benefits: none
**Why this matters**: kills a calculator that returns $0, that annualizes the monthly figure, or that reads the wrong column of the Kansas TANF table.

---

### Scenario 2: Two adults sharing a home — Eligible, $263
**What we're checking**: the size-2 row of the value table, an independent constant.
**Expected**: Eligible — $263 (household size 2 → Kansas TANF minimum standard $263)
**Steps**:
* Location: ZIP `67214`, county `Sedgwick County`
* Person 1: `birth_year` 1994, `birth_month` 3 (born March 1994), head of household, no income
* Person 2: `birth_year` 1996, `birth_month` 6 (born June 1996), spouse, no income
* Current benefits: none
**Why this matters**: kills a mutation to the $263 row alone, which every other scenario survives.

---

### Scenario 3: Three adult siblings sharing a home — Eligible, $349
**What we're checking**: an interior row of the value table, and that earned income neither gates eligibility nor reduces the displayed value.
**Expected**: Eligible — $349 (household size 3 → Kansas TANF minimum standard $349)
**Steps**:
* Location: ZIP `67214`, county `Sedgwick County`
* Person 1: `birth_year` 1994, `birth_month` 3 (born March 1994), head of household, income stream `wages` (category `employment`) $2,000/month
* Person 2: `birth_year` 1996, `birth_month` 6 (born June 1996), `sisterOrBrother`, no income
* Person 3: `birth_year` 1999, `birth_month` 1 (born January 1999), `sisterOrBrother`, no income
* Current benefits: none
**Why this matters**: kills a transposed interior table entry, an invented income cap (Data Gap 1 is handled inclusively), and a value reduced by income — Benefit Value commits to the baseline estimate without applying Kansas's unpublished income-reduction formula, so a calculator that reduces the displayed figure by the $2,000 fails here.

---

### Scenario 4: Four adults sharing a home — Eligible, $421
**What we're checking**: the last tabulated household size, where the table ends and extrapolation begins.
**Expected**: Eligible — $421 (household size 4 → Kansas TANF minimum standard $421)
**Steps**:
* Location: ZIP `67214`, county `Sedgwick County`
* Person 1: `birth_year` 1994, `birth_month` 3 (born March 1994), head of household, no income
* Person 2: `birth_year` 1996, `birth_month` 6 (born June 1996), spouse, no income
* Person 3: `birth_year` 1999, `birth_month` 1 (born January 1999), `sisterOrBrother`, no income
* Person 4: `birth_year` 2001, `birth_month` 8 (born August 2001), `sisterOrBrother`, no income
* Current benefits: none
**Why this matters**: kills a truncated value table, and pins the boundary between tabulated and extrapolated sizes.

---

### Scenario 5: Five adults sharing a home — Eligible, $482
**What we're checking**: the first extrapolated household size — "Add $61 for each additional person" at its first application.
**Expected**: Eligible — $482 ($421 for size 4 + $61 × 1 additional person)
**Steps**:
* Location: ZIP `66502`, county `Riley County`
* Person 1: `birth_year` 1994, `birth_month` 3 (born March 1994), head of household, no income
* Person 2: `birth_year` 1996, `birth_month` 6 (born June 1996), spouse, no income
* Person 3: `birth_year` 1999, `birth_month` 1 (born January 1999), `sisterOrBrother`, no income
* Person 4: `birth_year` 2001, `birth_month` 8 (born August 2001), `sisterOrBrother`, no income
* Person 5: `birth_year` 2003, `birth_month` 4 (born April 2003), `sisterOrBrother`, no income
* Current benefits: none
**Why this matters**: kills an off-by-one in where extrapolation starts — a calculator that extrapolates from size 5 instead of size 4, or that caps the value at $421.

---

### Scenario 6: Nine adults sharing a home — Eligible, $726
**What we're checking**: repeated application of the per-person increment.
**Expected**: Eligible — $726 ($421 for size 4 + $61 × 5 additional persons)
**Steps**:
* Location: ZIP `67214`, county `Sedgwick County`
* Person 1: `birth_year` 1991, `birth_month` 10 (born October 1991), head of household, no income
* Person 2: `birth_year` 1994, `birth_month` 3 (born March 1994), spouse, no income
* Person 3: `birth_year` 1996, `birth_month` 6 (born June 1996), `sisterOrBrother`, no income
* Person 4: `birth_year` 1999, `birth_month` 1 (born January 1999), `sisterOrBrother`, no income
* Person 5: `birth_year` 2001, `birth_month` 8 (born August 2001), `sisterOrBrother`, no income
* Person 6: `birth_year` 2003, `birth_month` 4 (born April 2003), `sisterOrBrother`, no income
* Person 7: `birth_year` 2004, `birth_month` 7 (born July 2004), `sisterOrBrother`, no income
* Person 8: `birth_year` 2005, `birth_month` 2 (born February 2005), `sisterOrBrother`, no income
* Person 9: `birth_year` 2006, `birth_month` 5 (born May 2006), `sisterOrBrother`, no income
* Current benefits: none
**Why this matters**: kills a wrong increment multiplier — a single flat addition instead of $61 per person — which a size-5 scenario alone would not catch.

---

### Scenario 7: Parent with two children, no income, not receiving TANF — Ineligible
**What we're checking**: criterion 2's harder half — ineligibility for TANF, not merely non-receipt.
**Expected**: Ineligible (the household qualifies for TANF, so RCA is not available even though no TANF is currently received)
**Steps**:
* Location: ZIP `67214`, county `Sedgwick County`
* Person 1: `birth_year` 1994, `birth_month` 3 (born March 1994), head of household, no income
* Person 2: `birth_year` 2018, `birth_month` 1 (born January 2018), child
* Person 3: `birth_year` 2021, `birth_month` 5 (born May 2021), child
* Household assets: $0
* Current benefits: none
**Why this matters**: kills a calculator that tests only current receipt and pays RCA to a TANF-eligible family — the population Kansas routes to TANF instead.

---

### Scenario 8: Childless adult reporting TANF receipt — Ineligible
**What we're checking**: criterion 2 — the TANF *receipt* test, isolated from the eligibility dependency.
**Expected**: Ineligible (receiving TANF)
**Steps**:
* Location: ZIP `67214`, county `Sedgwick County`
* Person 1: `birth_year` 1994, `birth_month` 3 (born March 1994), head of household, no income
* Household assets: $0
* Current benefits: the `ks_tanf` current-benefit tile
**Why this matters**: the household has no dependent child, so KS TANF eligibility is false and the dependency cannot fire — only `has_base_benefit("tanf")`, matching `ks_tanf` through its `tanf` `base_program`, can produce this verdict. Deleting the receipt check flips this scenario to Eligible. Kansas TANF ordinarily requires a child in the household, an unborn child included, so the childless fixture is deliberately a case where MFB's own present-household TANF calculation is false: it tests reported current-benefit receipt, not a claim that a childless non-pregnant adult ordinarily qualifies for Kansas TANF. The tile is the branch under test.

---

### Scenario 9: Single older adult receiving SSI — Ineligible
**What we're checking**: criterion 3 at member scope in a household where the excluded member is the only member.
**Expected**: Ineligible (the sole member reports an SSI amount, so no member remains in the RCA case)
**Steps**:
* Location: ZIP `67214`, county `Sedgwick County`
* Person 1: `birth_year` 1959, `birth_month` 3 (born March 1959), head of household, not disabled, income stream `sSI` $700/month
* Household assets: $0
* Current benefits: none
**Why this matters**: this isolates actual SSI receipt at member scope. Under the intended RCA implementation, deleting the receipt exclusion flips this scenario to Eligible. Scenario 12 separately guards against reintroducing an SSI-eligibility dependency.

---

### Scenario 10: Two older siblings, one receiving SSI — Eligible, $168
**What we're checking**: that the SSI exclusion is the member's rather than the household's, and that the value follows the RCA case rather than household size.
**Expected**: Eligible — $168 (the sibling reporting SSI is excluded, leaving a case of 1 → Kansas TANF minimum standard $168)
**Steps**:
* Location: ZIP `67214`, county `Sedgwick County`
* Person 1: `birth_year` 1958, `birth_month` 3 (born March 1958), head of household, no income
* Person 2: `birth_year` 1959, `birth_month` 6 (born June 1959), `sisterOrBrother`, income stream `sSI` $700/month
* Household assets: $0
* Current benefits: none
**Why this matters**: the regression test for member scope. A household-wide SSI exclusion returns Ineligible here, and a value read off `household_size` returns $263 — this is the only scenario that fails under either.

---

### Scenario 11: Two older siblings, SSI tile ticked with no amount — Eligible, $263
**What we're checking**: the tile-only branch where the recipient cannot be identified — both siblings are 65 or over, so either could be the recipient, and no reported amount attributes the tile to one of them.
**Expected**: Eligible — $263 (nobody is excluded, leaving a case of 2 → Kansas TANF minimum standard $263)
**Steps**:
* Location: ZIP `67214`, county `Sedgwick County`
* Person 1: `birth_year` 1958, `birth_month` 3 (born March 1958), head of household, no income
* Person 2: `birth_year` 1959, `birth_month` 6 (born June 1959), `sisterOrBrother`, no income
* Household assets: $0
* Current benefits: the `ks_ssi` current-benefit tile, with no `sSI` income amount reported for either member
**Why this matters**: kills excluding a member the screener cannot identify — guessing either sibling returns $168 and reading the tile as a household exclusion returns Ineligible. Scenario 13 is the other side of this boundary: the same tile in a one-member household does exclude.

---

### Scenario 12: Single disabled adult, SSI-eligible but not receiving — Eligible, $168
**What we're checking**: that SSI disqualifies on receipt only, never on eligibility — RCA continues while SSI eligibility is being determined.
**Expected**: Eligible — $168 (case size 1 → Kansas TANF minimum standard $168)
**Steps**:
* Location: ZIP `67214`, county `Sedgwick County`
* Person 1: `birth_year` 1980, `birth_month` 6 (born June 1980), head of household, `disabled` true, no earned or unearned income
* Household assets: $0
* Current benefits: none — no SSI tile, and no `sSI` income amount for any member
**Why this matters**: the fixture is built so MFB's own `ks_ssi` would return this member eligible — disability, no income, no countable resources — so reintroducing an SSI *eligibility* dependency alongside the receipt test flips this scenario to Ineligible. That is the regression 45 CFR 400.51(b)(1)(ii) forbids, and the one a scenario built on a working-age non-disabled applicant cannot catch.

---

### Scenario 13: Single older adult, SSI tile ticked with no amount — Ineligible
**What we're checking**: the one-member end of the tile boundary, where a household-scoped tile necessarily identifies the household's only member.
**Expected**: Ineligible (`household_size` is 1, so the tile identifies the sole member as the SSI recipient and no member remains in the RCA case)
**Steps**:
* Location: ZIP `67214`, county `Sedgwick County`
* Person 1: `birth_year` 1959, `birth_month` 3 (born March 1959), head of household, no income
* Household assets: $0
* Current benefits: the `ks_ssi` current-benefit tile, with no `sSI` income amount reported
**Why this matters**: kills carrying the multi-member ambiguity rule into a household that has no ambiguity — treating this tile as unattributable returns Eligible, $168. Paired with Scenario 11, it pins the boundary at `household_size` 1.

---

## Research Sources

| Snapshot | Tier | Title | URL | Retrieved |
|---|---|---|---|---|
| `2026-09-02--45-cfr-400-43` | 1 | 45 CFR 400.43 — Requirements for documentation of refugee status | https://www.ecfr.gov/api/versioner/v1/full/2026-08-31/title-45.xml?part=400&section=400.43 | 2026-09-02 |
| `2026-09-02--45-cfr-400-51` | 1 | 45 CFR 400.51 — Determination of eligibility under other programs | https://www.ecfr.gov/api/versioner/v1/full/2026-08-31/title-45.xml?part=400&section=400.51 | 2026-09-02 |
| `2026-09-02--45-cfr-400-53` | 1 | 45 CFR 400.53 — General eligibility requirements | https://www.ecfr.gov/api/versioner/v1/full/2026-08-31/title-45.xml?part=400&section=400.53 | 2026-09-02 |
| `2026-09-02--45-cfr-400-56` | 1 | 45 CFR 400.56 — Structure | https://www.ecfr.gov/api/versioner/v1/full/2026-08-31/title-45.xml?part=400&section=400.56 | 2026-09-02 |
| `2026-09-02--45-cfr-400-57` | 1 | 45 CFR 400.57 — Planning and consultation process | https://www.ecfr.gov/api/versioner/v1/full/2026-08-31/title-45.xml?part=400&section=400.57 | 2026-09-02 |
| `2026-09-02--45-cfr-400-58` | 1 | 45 CFR 400.58 — Content and submission of public/private RCA plan | https://www.ecfr.gov/api/versioner/v1/full/2026-08-31/title-45.xml?part=400&section=400.58 | 2026-09-02 |
| `2026-09-02--45-cfr-400-59` | 1 | 45 CFR 400.59 — Eligibility for the public/private RCA program | https://www.ecfr.gov/api/versioner/v1/full/2026-08-31/title-45.xml?part=400&section=400.59 | 2026-09-02 |
| `2026-09-02--45-cfr-400-60` | 1 | 45 CFR 400.60 — Payment levels | https://www.ecfr.gov/api/versioner/v1/full/2026-08-31/title-45.xml?part=400&section=400.60 | 2026-09-02 |
| `2026-09-02--45-cfr-400-61` | 1 | 45 CFR 400.61 — Services to public/private RCA recipients | https://www.ecfr.gov/api/versioner/v1/full/2026-08-31/title-45.xml?part=400&section=400.61 | 2026-09-02 |
| `2026-09-02--45-cfr-400-62` | 1 | 45 CFR 400.62 — Treatment of eligible secondary migrants, asylees, and Cuban/Haitian entrants | https://www.ecfr.gov/api/versioner/v1/full/2026-08-31/title-45.xml?part=400&section=400.62 | 2026-09-02 |
| `2026-09-02--45-cfr-400-63` | 1 | 45 CFR 400.63 — Preparation of local resettlement agencies | https://www.ecfr.gov/api/versioner/v1/full/2026-08-31/title-45.xml?part=400&section=400.63 | 2026-09-02 |
| `2026-09-02--45-cfr-400-66` | 1 | 45 CFR 400.66 — Eligibility and payment levels in a publicly-administered RCA program | https://www.ecfr.gov/api/versioner/v1/full/2026-08-31/title-45.xml?part=400&section=400.66 | 2026-09-02 |
| `2026-09-02--45-cfr-400-70` | 1 | 45 CFR 400.70 — Scope (employability services and employment) | https://www.ecfr.gov/api/versioner/v1/full/2026-08-31/title-45.xml?part=400&section=400.70 | 2026-09-02 |
| `2026-09-02--45-cfr-400-71` | 1 | 45 CFR 400.71 — Employability services | https://www.ecfr.gov/api/versioner/v1/full/2026-08-31/title-45.xml?part=400&section=400.71 | 2026-09-02 |
| `2026-09-02--45-cfr-400-72` | 1 | 45 CFR 400.72 — Criteria for administration of employability services | https://www.ecfr.gov/api/versioner/v1/full/2026-08-31/title-45.xml?part=400&section=400.72 | 2026-09-02 |
| `2026-09-02--45-cfr-400-75` | 1 | 45 CFR 400.75 — Participant employment obligations | https://www.ecfr.gov/api/versioner/v1/full/2026-08-31/title-45.xml?part=400&section=400.75 | 2026-09-02 |
| `2026-09-02--45-cfr-400-76` | 1 | 45 CFR 400.76 — Failure to comply | https://www.ecfr.gov/api/versioner/v1/full/2026-08-31/title-45.xml?part=400&section=400.76 | 2026-09-02 |
| `2026-09-02--45-cfr-400-77` | 1 | 45 CFR 400.77 — Effect of quitting employment or failing or refusing to participate in required services | https://www.ecfr.gov/api/versioner/v1/full/2026-08-31/title-45.xml?part=400&section=400.77 | 2026-09-02 |
| `2026-09-02--45-cfr-400-79` | 1 | 45 CFR 400.79 — Good cause | https://www.ecfr.gov/api/versioner/v1/full/2026-08-31/title-45.xml?part=400&section=400.79 | 2026-09-02 |
| `2026-09-02--45-cfr-400-81` | 1 | 45 CFR 400.81 — Conciliation and fair hearings | https://www.ecfr.gov/api/versioner/v1/full/2026-08-31/title-45.xml?part=400&section=400.81 | 2026-09-02 |
| `2026-09-02--45-cfr-400-82` | 1 | 45 CFR 400.82 — Notice and hearing procedures | https://www.ecfr.gov/api/versioner/v1/full/2026-08-31/title-45.xml?part=400&section=400.82 | 2026-09-02 |
| `2026-09-02--45-cfr-400-83` | 1 | 45 CFR 400.83 — Availability of employability services | https://www.ecfr.gov/api/versioner/v1/full/2026-08-31/title-45.xml?part=400&section=400.83 | 2026-09-02 |
| `2026-09-02--45-cfr-400-208` | 1 | 45 CFR 400.208 — Claims involving family units which include both refugees and nonrefugees | https://www.ecfr.gov/api/versioner/v1/full/2026-08-31/title-45.xml?part=400&section=400.208 | 2026-09-02 |
| `2026-09-02--45-cfr-400-211` | 1 | 45 CFR 400.211 — Methodology to be used to determine time-eligibility of refugees | https://www.ecfr.gov/api/versioner/v1/full/2026-08-31/title-45.xml?part=400&section=400.211 | 2026-09-02 |
| `2026-09-02--fr-2021-rca-payment-ceilings` | 1 | 86 FR 54466 — Public/Private Refugee Cash Assistance Inflationary Increase | https://www.federalregister.gov/documents/full_text/text/2021/10/01/2021-21369.txt | 2026-09-02 |
| `2026-09-02--fr-2022-rca-8-to-12-months` | 1 | 87 FR — Extending Refugee Cash Assistance and Refugee Medical Assistance From 8 Months to 12 Months | https://www.federalregister.gov/documents/full_text/text/2022/03/28/2022-06356.txt | 2026-09-02 |
| `2026-09-02--fr-2025-eligibility-period-reduction` | 1 | 90 FR — ORR Notice of Change of Eligibility (RCA/RMA period reduced to 4 months) | https://www.federalregister.gov/documents/full_text/text/2025/03/21/2025-04839.txt | 2026-09-02 |
| `2026-09-02--fr-2026-eligibility-period-8-months` | 1 | 91 FR 43107–43108 — Change in Eligibility Period for Refugee Cash Assistance and Refugee Medical Assistance | https://www.federalregister.gov/documents/full_text/text/2026/07/14/2026-14095.txt | 2026-09-02 |
| `2026-09-02--orr-pl-21-04-public-private-rca` | 2 | ORR Policy Letter 21-04 — Guidance for Public-Private Refugee Cash Assistance Programs | https://acf.gov/sites/default/files/documents/orr/ORR-PL-21-04-Public-Private-RCA-Programs.pdf | 2026-09-02 |
| `2026-09-02--orr-pl-23-04-income-disregards` | 2 | ORR Policy Letter 23-04 — Expanding Income Disregards for Refugee Cash Assistance | https://acf.gov/sites/default/files/documents/orr/pl-23-04-expanding-income-disregards-for-rca.pdf | 2026-09-02 |
| `2026-09-03--orr-pl-23-04-income-disregards-pir` | 2 | ORR Policy Letter 23-04 — Income Disregards for Refugee Cash Assistance (revised 2026-02-02) | https://acf.gov/sites/default/files/documents/orr/ORR-PL-23-04---Income-Disregards-for-RCA.pdf | 2026-09-03 |
| `2026-09-02--orr-cma-program` | 2 | ORR — Cash and Medical Assistance (CMA) | https://acf.gov/orr/programs/refugees/cma | 2026-09-02 |
| `2026-09-02--orr-annual-report-congress-fy2020` | 2 | ORR Annual Report to Congress, Fiscal Year 2020 | https://www.govinfo.gov/content/pkg/CMR-HE25-00183248/pdf/CMR-HE25-00183248.pdf | 2026-09-02 |
| `2026-09-02--ks-tanf-state-plan-ffy2024-2026` | 2 | State of Kansas TANF State Plan FFY 2024–2026 | https://www.dcf.ks.gov/services/ees/Documents/Reports/TANF%20State%20Plan%20FFY%202024%20-%202026.pdf | 2026-09-02 |
| `2026-09-02--keesm-1111-program-descriptions` | 2 | KEESM 1111 — Program Descriptions | https://content.dcf.ks.gov/ees/keesm/Current/keesm1111_1.htm | 2026-09-02 |
| `2026-09-02--kees-webhelp-rca` | 2 | KEES Web Help — Refugee Cash Assistance (RCA) | https://content.dcf.ks.gov/ees/KEESWebHelp/NonMedical-KEESWebHelp/Refugee_Cash_Assistance_(RCA).htm | 2026-09-02 |
| `2026-09-02--dcf-cash-assistance-index` | 2 | Kansas DCF — Cash Assistance programs index | https://www.dcf.ks.gov/services/ees/Pages/Cash/CashAssistance.aspx | 2026-09-02 |
| `2026-09-02--ksor-programs` | 3 | Kansas Office for Refugees — Programs | https://www.ksor.org/kansas-office-for-refugees-ksor-programs/ | 2026-09-02 |
| `2026-09-02--ksor-programs-archived-2023-03-25` | 3 | Kansas Office for Refugees — Programs (Wayback capture 2023-03-25) | http://web.archive.org/web/20230325101422id_/https://www.ksor.org/kansas-office-for-refugees-ksor-programs/ | 2026-09-02 |
| `2026-09-02--ksor-programs-archived-2026-01-19` | 3 | Kansas Office for Refugees — Programs (Wayback capture 2026-01-19) | http://web.archive.org/web/20260119033459id_/https://www.ksor.org/kansas-office-for-refugees-ksor-programs/ | 2026-09-02 |
| `2026-09-02--ksor-home` | 3 | Kansas Office for Refugees — Home | https://www.ksor.org/ | 2026-09-02 |
| `2026-09-02--ksor-faq` | 3 | Kansas Office for Refugees — Frequently Asked Questions | https://www.ksor.org/frequently-asked-questions/ | 2026-09-02 |
| `2026-09-02--ksor-resources` | 3 | Kansas Office for Refugees — Resources | https://www.ksor.org/resources/ | 2026-09-02 |
| `2026-09-02--ksor-resource-guide` | 3 | Kansas Office for Refugees — KSOR Resource Guide | https://www.ksor.org/ksor-resource-guide/ | 2026-09-02 |
| `2026-09-02--ksor-contact` | 3 | Kansas Office for Refugees — Contact | https://www.ksor.org/contact/ | 2026-09-02 |
