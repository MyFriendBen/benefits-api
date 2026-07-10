# Implement HCV (TX) Program

## Program Details

- **Program**: HCV
- **State**: TX
- **White Label**: tx
- **Research Date**: 2026-06-09

## Eligibility Criteria

**Geography (not an eligibility gate).** `zipcode`/`county` are collected from every applicant but don't determine eligibility — 24 CFR 982.353 confirms a PHA has no residency requirement for initial application (nonresident applicants are explicitly permitted). Nonresident families are confined to leasing within the initial PHA's jurisdiction for their first 12 months (absent PHA discretion or a domestic-violence/stalking exception); full nationwide portability applies afterward. These fields matter only for routing to the correct PHA and payment-standard geography (see Benefit Value).

1. **Household income must not exceed 50% of Area Median Income (AMI)** — TDHCA's "Very Low Income" ceiling for ordinary applicants. At least 75% of admissions per fiscal year must be Extremely Low Income (30% AMI); this affects waitlist order, not eligibility. ⚠️ *data gap — affects a narrow exception, not the general 50%-AMI rule*

   - **Screener fields:** `household_size`, `county`, `calc_gross_income("yearly", ["all"])`
   - **Source:** TDHCA HCV Administrative Plan (Sept. 2022 update), Ch. 3 Part II; 24 CFR 982.201(b); 42 U.S.C. § 1437n(b)(1)
   - **Implementation:** Compare household income against the 50% AMI limit for the household's county and size, looked up from HUD's published FY2026 Section 8 Income Limits dataset (see Research Sources) — re-fetch annually when HUD updates it. TDHCA extends eligibility to 80% AMI ("Low Income") only for five narrow categories — continuously-assisted families, HOPE 1/2 homeownership residents, mortgage-prepayment-displaced families, Disaster preference, and Project Access (see Priority Criteria) — none of which apply to an ordinary applicant, so the 50% ceiling governs by default. Scenario 17 is the regression test confirming a household between the two ceilings is correctly rejected. **The same income-exclusion rules used for Benefit Value (see "Income exclusions modeled") apply here too** — a naive `calc_gross_income("yearly", ["all"])` call with no filtering could wrongly count a minor's wages or a foster child's income toward this ceiling and push an otherwise-eligible household over it, which is an eligibility miss, not just a value error.
   - **Known limitation:** the calculator can't detect Disaster preference or Project Access status from screener data, so a household in one of those two categories, between the 50% and 80% ceilings, would be incorrectly shown as ineligible. Handled conservatively, not by inclusivity default — same reasoning as Criterion 3's emancipated-minor exception. Documented, not a bug to fix in this ticket. **Surfaced in the description** ("if your community was recently declared a disaster area, or you're moving out of an institution due to a disability, you may still qualify...") since, unlike Criterion 3, this affects a more recognizable, actionable population.

2. **Applicant must not currently be receiving HCV/Section 8 assistance.**

   - **Screener fields:** `has_section_8`
   - **Source:** 24 CFR 982.551(n)
   - **Implementation:** `has_section_8 == true` → ineligible, as a hard override. A household already receiving Section 8/HCV assistance cannot receive a second voucher.

3. **Head of household, spouse, or co-head must have the legal capacity to enter a lease under Texas law** — in practice, age 18, unless the applicant is an emancipated minor. ⚠️ *data gap — handled conservatively, not by inclusivity default*

   - **Screener fields:** `birth_year` + `birth_month` for the member where `relationship == "headOfHousehold"`
   - **Source:** TDHCA HCV Administrative Plan (Sept. 2022 update), Ch. 3 Part I, citing 24 CFR § 5.504(b): *"The head of household must have the legal capacity to enter into a lease under state and local law. A minor who is emancipated under state law may be designated as head of household."* (24 CFR 982.4 and 24 CFR 5.403 both define "family" but set no age requirement themselves — the 18-year floor comes from Texas's age-of-majority rule via TDHCA's legal-capacity-to-lease standard, not a direct federal age minimum.)
   - **Known limitation:** the screener can't detect emancipated-minor status, so the age-18 proxy is a hard gate for every under-18 applicant (Scenario 7) rather than the usual inclusivity default — the base rule applies to the vast majority, and the exception is rare enough that assuming it applies by default would undermine the rule. No screener improvement recommended given the low expected incidence. **Not surfaced in the description** — unlike Criterion 1's Disaster/Project Access exception, this affects a much smaller, harder-to-self-identify population, and an unaccompanied minor in this situation is more likely reached through the description's existing homelessness/EHV-referral language than a dedicated sentence about emancipation status.

4. **At least one household member must be a U.S. citizen, national, or non-citizen with eligible immigration status.** **Not a data gap** — handled at the platform level via `legal_status_required`, not by the calculator or screener.

   - **Source:** TDHCA HCV Administrative Plan (Sept. 2022 update), Ch. 3 Part II p.28 ("Citizenship or Eligible Immigration Status"); 42 U.S.C. § 1436a; 24 CFR 5.506; 24 CFR 5.520
   - **Implementation:** `legal_status_required` lists all 6 statuses (no restriction) — HUD's rule only requires *one* member to qualify, so a mixed-status household is still shown the program. MFB's results-page filter can't model "at least one member qualifies" at a finer grain than the household's overall selection, so listing all 6 is correct.
   - **Benefit-value nuance (not an eligibility question — see Benefit Value):** a genuine mixed-status family legally receives **prorated** assistance — the pre-proration HAP (payment standard minus TTP) × eligible members ÷ total members, 24 CFR 5.520 — not the raw payment standard times that fraction. Not modeled — the calculator shows the full, unprorated value for every household, since the screener doesn't collect per-member immigration status.
   - **Watch item:** HUD's proposed rule (published 2026-02-20; comment period closed 2026-04-21; no final rule yet) would bar mixed-status families from HUD rental assistance entirely, not just end proration. If finalized, this becomes an eligibility question and this criterion needs a full re-review.
   - **Known limitation — noncitizen-student bar not modeled.** 24 CFR 5.522 / 42 U.S.C. § 1436a(c)(2)(A) categorically bar a noncitizen admitted temporarily and solely to pursue a full course of study (F-1/J-1/M-1-type visa), plus their noncitizen spouse and minor children, regardless of the general eligible-immigration-status rule above. Not evaluable — the screener captures immigration-status category, not visa subclass — but a narrow edge case in practice: HCV's applicant profile (low-income, seeking long-term local housing) is largely incompatible with the visa's own conditions (temporary admission, no intent to abandon foreign residence). **Not surfaced in the description** — too narrow and technical to state in plain language without the visa-subclass detail that gives it meaning, and citizenship/immigration handling generally isn't itemized in this program's description (it's enforced via `legal_status_required`, not description text, for every criterion in this spec).
   - **Impact:** Low — affects value precision for a subset of mixed-status households only; doesn't affect whether the program is shown or eligibility is correctly determined.

5. **Applicant must pass criminal background screening.** ⚠️ *data gap*

   - Mandatory, permanent bar: lifetime sex-offender registration; a conviction for manufacturing/producing methamphetamine on federally-assisted premises.
   - Mandatory, non-waivable: current illegal drug use (any use within the past 6 months — expires on its own, isn't "cured" by proving rehab); a drug-trafficking conviction (flat 10-year bar).
   - Mandatory but rehab-waivable: a documented pattern of drug/alcohol abuse TDHCA has reasonable cause to believe threatens health, safety, or peaceful enjoyment of the premises.
   - Discretionary (not mandatory): other criminal activity — drug-related (excluding personal use above), violent, or otherwise threatening to residents/staff/property — evidenced by a conviction, eviction, or parole/release record in the past 5 years.

   - **Screener fields:** none — criminal history is excluded from screener collection per MFB guidelines
   - **Source:** 42 U.S.C. § 13663 (sex-offender ban); TDHCA HCV Administrative Plan (Sept. 2022 update), Ch. 3 Part III p.35–36 (drug-related bars, including the 10-year trafficking bar — TDHCA-specific, not tied to any federal drug-trafficking-benefits statute found in the plan); 24 CFR 982.553
   - **Data gap handling:** assume the household passes — inclusivity assumption. **Results-based outcome not surfaced in the description** — background-check language reads more clinical/threatening than MFB's tone calls for relative to its informational value, the same reasoning that already excludes criminal-history data from screener collection. No screener improvement possible.
   - **Consent to verification — a separate, disclosure-worthy fact, surfaced in the description.** Criminal-record access itself requires a signed consent form (24 CFR 5.903), and failing to sign any required consent form is itself a mandatory denial ground (24 CFR 5.232; 24 CFR 982.552(b)(3); TDHCA Ch. 7 Part I: "If any family member who is required to sign a consent form fails to do so, TDHCA will deny admission"). Unlike the background-check result — an uncontrollable fact about a household's history — consenting to be checked is a controllable procedural step, the same category as providing documents, so it clears the bar for disclosure even though the result itself doesn't. Surfaced in the description as: "Everyone in your household must agree to a background and income check. This happens when you apply. If you don't agree, you can't get a voucher."
   - **Related, but separate:** SSN documentation (24 CFR 5.216/5.218) is also a mandatory-denial ground under TDHCA's plan, but it's a document requirement, not a background characteristic — handled via the config's `tx_ssn` document, not this criterion.
   - **Impact:** High

6. **TDHCA has discretion to deny based on a household's prior housing/financial/conduct history — or misrepresentation on the application itself.** ⚠️ *data gap*
   - Deliberately misrepresented the information on which eligibility or tenant rent is established, or otherwise did not provide complete and true information to TDHCA — a distinct ground from the fraud bullet below, not a subset of it (TDHCA's plan lists both separately)
   - Evicted from federally-assisted housing in the last 3 years (TDHCA's own lookback; federal default is 5) — waivable with proof of rehab or if circumstances no longer exist
   - Committed fraud, bribery, or a corrupt act connected to a federal/state housing program in the prior 5 years
   - Owes rent or other amounts to any PHA (HCV, Certificate, Moderate Rehab, or public housing) — waivable by repaying before waitlist selection
   - Hasn't reimbursed a PHA for HAP-related amounts (rent, damages, other lease amounts) — same repayment waiver
   - Breached a repayment agreement — same repayment waiver
   - Violated any family obligation on the voucher within the prior year (TDHCA's own 1-year lookback)
   - Subject to the Texas Sex Offender Statute or another state's registration requirement (overlaps with Criterion 5)
   - Abusive or threatening behavior toward TDHCA personnel (verbal, physical, or written, including racial epithets)
   - *Not* a ground for denial: a family's prior failure to meet Family Self-Sufficiency or Welfare-to-Work obligations.
   - *Not* a ground for denial (VAWA floor, 34 U.S.C. § 12491(b)(1)): being or having been a victim of domestic violence, dating violence, sexual assault, or stalking — even where a related incident would otherwise appear in a housing or criminal history record. Doesn't change calculator behavior (the inclusivity-assumption default below already extends equivalent treatment to every applicant regardless of cause), but worth stating so this criterion isn't misread as applying to DV-survivor history.

   - **Screener fields:** none — requires PHA records lookup
   - **Source:** TDHCA HCV Administrative Plan (Sept. 2022 update), Ch. 3 Part III p.34 (misrepresentation/incomplete information), p.37 (fraud, debts, repayment, family obligations); 24 CFR 982.552(c)(1); 34 U.S.C. § 12491(b)(1) (VAWA floor)
   - **Data gap handling:** assume none of these apply — inclusivity assumption. **Not surfaced in the description** — narrow, negative-history conditions affecting only households who've previously held a voucher or been in subsidized housing; broadcasting them to every user risks reading as presumptuous rather than helpful. TDHCA's own notice-and-hearing process (Ch. 3 Part III) is the appropriate individualized channel for anyone actually affected. No screener improvement recommended — matches how the identical PHA-debt/termination fact is handled in KS HCV's spec: MFB adds screener fields, or surfaces gaps in the description, only for neutral/circumstantial facts, not facts that could result in denial.
   - **Impact:** Medium

7. **Applicant must not have been evicted from federally-assisted housing for drug-related criminal activity within the past 3 years** — a mandatory federal bar, distinct from Criterion 6's discretionary general-eviction ground; waivable with proof of completed rehab or if the person who committed the act is no longer in the household. ⚠️ *data gap*

   - **Screener fields:** none
   - **Source:** 24 CFR 982.553(a)(1)(i); 42 U.S.C. § 13661; TDHCA HCV Administrative Plan (Sept. 2022 update), Ch. 3 Part III
   - **Data gap handling:** assume no such eviction — inclusivity assumption. **Not surfaced in the description**, for the same reason as Criterion 6. No screener improvement recommended — a negative-history fact, not a neutral/circumstantial one.
   - **Impact:** Medium

8. **Student restrictions** — 24 CFR 5.612 has no full-time qualifier; it applies to any individual **enrolled** at an institution of higher education (full- or part-time) who is also under 24, not a veteran, unmarried, has no dependent child, isn't a person with disabilities grandfathered in as of Nov. 30, 2005, and isn't independently income-eligible (or whose parents aren't). All seven conditions must hold for the restriction to apply — meeting any one exemption clears the household. ⚠️ *data gap*

   - **Screener fields:** `student`, `student_full_time`, `student_job_training_program` (partial)
   - **Source:** 24 CFR 5.612 (verbatim seven-condition test; no full-time distinction in the regulation itself); Section 327 of Public Law 109-115 (uncodified, the underlying statutory authority)
   - **Implementation:** check `student == true` (not just `student_full_time`) — a part-time enrolled student meeting the other six conditions is equally restricted. Several exemptions are evaluable directly — married status, dependent children, Job Corps/job training. The veteran exemption would be evaluable with the proposed `veteran` screener tile (see Priority Criterion 1).
   - **Data gap handling:** assume an applicable exemption applies unless screener data proves otherwise — inclusivity assumption. ⚠️ *Screener gap* — suggested improvement: add a "I was previously in foster care" tile to the Special Circumstances step (field `previously_in_foster_care` on `HouseholdMember`), the one remaining exemption condition that can't be inferred from existing fields. **Not surfaced in the description** beyond the generic "additional requirements may apply for students" sentence — too narrow/technical to name, and the inclusivity assumption already covers it regardless of whether the tile ships.
   - **Impact:** Low

9. **Household net assets must not exceed $100,000** (adjusted annually for inflation), absent an exemption for real property unsuitable for the family to live in — a mandatory federal denial/termination ground under HOTMA. ⚠️ *data gap — two distinct parts, handled differently: unreported assets default to inclusive; assets reported over $100,000 are a hard gate, handled conservatively like Criterion 3, not by inclusivity default*

   - **Screener fields:** `household_assets` (optional, decimal dollar field on `Screen` — if not reported, assume under threshold; inclusivity assumption)
   - **Source:** 24 CFR 5.618(a)
   - **Implementation:** if `household_assets` is reported and exceeds $100,000, the household is ineligible — a hard gate, not an inclusivity default, same reasoning as Criterion 3's emancipated-minor exception. The real-property exemption (excess assets held solely as real property unsuitable for the family to live in) isn't evaluable from screener data, so a genuinely exempt household would be incorrectly shown as ineligible — a narrow, accepted limitation. No screener improvement recommended — the combination (assets over $100k *and* the excess specifically tied up in unsuitable real property) is narrow enough that a dedicated question isn't worth the added screener burden.
   - **Surfaced in the description** ("Households with a lot of savings or other assets may not qualify") — unlike Criteria 5–7, this is a neutral financial fact rather than stigmatizing history, and a household can recognize it about themselves and verify with the PHA before applying. Same treatment as Criterion 1's Disaster/Project Access exception and Criterion 8's student restriction. No dollar figure stated, consistent with the rest of the description.
   - **Benefit-value nuance (not an eligibility question below $100,000):** for reported net assets between $50,000 and $100,000, 24 CFR 5.609(a) requires imputing income at HUD's current passbook savings rate and using the greater of imputed vs. actual asset income in the TTP calculation. **Not modeled** — no scenario in this spec has assets in this range, and implementing it requires tracking HUD's periodically-updated passbook rate. A documented, deliberate simplification, consistent with the medical/childcare/utility-allowance deferrals in Benefit Value.
   - **Impact:** Low — most low-income HCV applicants have net assets well under $50,000; this affects a narrow subset of otherwise-eligible households with higher savings or assets.

## Priority Criteria

These do not determine eligibility but affect waitlist position or access to special voucher categories — **with one exception: Disaster preference and Project Access (Priority Criterion 2) can also expand the eligibility ceiling itself to 80% AMI for a narrow group (see Criterion 1).** Where a priority factor isn't evaluable from screener data, assume it doesn't apply. For the waitlist-only factors this is inclusivity-neutral — it only affects waitlist position, never base eligibility or benefit value. For Disaster preference and Project Access, the same default instead means holding the household to the standard 50% AMI ceiling.

1. **Local preference categories — federal menu; TDHCA's own adopted mechanism is narrower.** 24 CFR 982.207 lets a PHA adopt local waitlist preferences from a broad federal menu (elderly, disability, dependent children, veterans, homeless/substandard housing, rent-burden, and others) — this is *permitted*, not mandatory, and each PHA picks its own combination. **TDHCA's own Administrative Plan does not adopt this six-category system.** TDHCA's actual mechanism (Ch. 3 Part II, p.51) is: (a) specialty-voucher sequencing — Non-Elderly Disabled, Project Access, and Mainstream voucher holders (referred via Texas HHSC) are served ahead of the general waitlist until each specialty allocation is filled — and (b) geographic waiting lists by service area. The only preference-adjacent mention of homelessness anywhere in the plan is a passing note (Ch. 3 Part III, EHV section, p.268) that waitlist applicants "with a homeless preference will be referred to the CoC" — not a defined, general local preference.

   Retained below as informational context (some Texas PHAs outside TDHCA's direct administration may adopt the fuller federal-menu combination) rather than a TDHCA-specific, screener-scoreable priority. None of these factors affect eligibility (see Criterion 1 for the two that do).

   | Factor | Screener data | Confirmed for TDHCA specifically? | Surfaced in description? |
   |---|---|---|---|
   | Elderly (62+), disability, dependent children | Evaluable — `birth_year`/`birth_month`, `disabled`, `household_members` relationship count (`child`/`fosterChild`/`grandChild`) | No — not found in TDHCA's plan; may apply at other TX PHAs | Yes — "seniors... people with disabilities, and families with children" |
   | Veteran status | ⚠️ Not collected (`veteran` field exists, unused). Suggested: add a Special Circumstances tile — would also help other TX programs | No — TDHCA's veteran-specific pathway is HUD-VASH referral (Priority Criterion 2), not a waitlist preference | Yes — "veterans" |
   | Homeless / substandard housing | ⚠️ Not collected — same `housing_situation` gap as EHV (Priority Criterion 2, below) | Partial — TDHCA references a "homeless preference" only for CoC/EHV referral, not as a general local preference | Yes — "families experiencing homelessness" |
   | Pays >50% of income toward rent | ⚠️ `rent` expense exists but isn't reliably captured (same limitation KS HCV notes). No screener fix recommended — would need a dedicated mandatory field | No — not found in TDHCA's plan | Yes — "paying a large share of their income toward rent" |

   - **Source:** 24 CFR 982.207 (federal menu); TDHCA HCV Administrative Plan (Sept. 2022 update), Ch. 3 Part II p.51 (TDHCA's actual adopted mechanism), Ch. 3 Part III p.268 (homeless→CoC referral mention)

2. **Special voucher categories** (EHV, VASH, Project Access, Disaster) — none are fully evaluable at the screener stage; direct applicants to contact TDHCA or their local PHA.

   | Category | What it is | Screener data | Surfaced in description? |
   |---|---|---|---|
   | Emergency Housing Vouchers (EHV) | For people who are homeless, at risk, or fleeing domestic violence, referred via Continuums of Care. TDHCA's allocation is fully committed — not accepting new referrals. | ⚠️ No `housing_situation` field | Indirectly, via the homelessness mention (EHV itself isn't named — not a live referral path right now) |
   | HUD-VASH | HCV + VA case management for homeless veterans | ⚠️ Needs the same `veteran` field as Criterion 1 | Indirectly, via the veteran mention |
   | Project Access | Disabled persons transitioning out of institutions. Opens the 80%-AMI ceiling (see Criterion 1) — an eligibility, not just priority, effect. | ⚠️ Partial — `disabled`/`long_term_disability` catches some cases, not the institutional-transition part | **Directly** — one of the "eligibility criteria we couldn't fully check" |
   | Disaster preference | Vouchers for TDHCA-flagged disaster-impacted communities, within 90 days of the disaster. Also opens the 80%-AMI ceiling. | ⚠️ No disaster-impact field | **Directly** — same reason as Project Access |

   Where not evaluable, assume not applicable — inclusivity-neutral for EHV/VASH; for Project Access/Disaster, this means holding the household to the standard 50% ceiling (see Criterion 1).

   - **Screener improvement suggested:** add a "What best describes your current housing situation?" question after the household-size step (options including homelessness and fleeing domestic violence) — routes toward EHV referral and resolves Priority Criterion 1's homelessness gap in the same stroke.
   - **Source:** 24 CFR 982.207; American Rescue Plan Act of 2021, § 3202 (EHV provisions); TDHCA HCV Administrative Plan (Sept. 2022 update), Ch. 3 Part II p.28 (Project Access, Disaster); TDHCA Section 8 Resources

## Benefit Value

**Benefit type:** In-kind rental subsidy — the PHA pays the Housing Assistance Payment (HAP) directly to the landlord each month. Value shown is an estimated annual monetary equivalent.

**Formula** (24 CFR 982.505(b); TDHCA HCV Administrative Plan (Sept. 2022 update), Ch. 6 Part III):

> Monthly HAP = min(Payment Standard, Gross Rent) − Total Tenant Payment (TTP), floored at $0
> Annual value = Monthly HAP × 12

MFB does collect a household's rent, via the `rent`/`mortgage` expense fields (`screen.calc_expenses("monthly", ["rent", "mortgage"])`) — but it's optional and not reliably captured (the same limitation noted for the rent-burden priority factor). Where reported, use `min(Payment Standard, reported rent)` per the formula above; where not reported, fall back to Payment Standard alone as a reasonable upper-bound estimate. Scenario 19 tests the reported-rent branch; Scenarios 1–18 test the no-rent-reported fallback. The $0 floor is a real, tested outcome (see Scenario 4), not an error condition — a household can be eligible for the voucher program with zero net subsidy if TTP exceeds the payment standard (or reported rent).

**Documented simplification — no utility allowance.** TDHCA defines Gross Rent as rent-to-owner *plus* a PHA-published utility allowance for tenant-paid utilities (24 CFR 982.517; TDHCA Admin Plan, Ch. 6 Part III, p.93–94), not bare contract rent. This calculator uses the household's reported rent alone as Gross Rent (Scenario 19), with no utility allowance added — MFB's screener doesn't collect utility costs, and TDHCA's allowance schedule (which varies by unit size and is revised at least annually) isn't captured anywhere in MFB's data. This understates Gross Rent, and therefore HAP, for the subset of households responsible for paying their own utilities. A known, deliberate simplification, matching the medical/childcare deduction deferrals above, not an oversight.

**Total Tenant Payment (TTP)** is the highest of (24 CFR 5.628):
1. 30% of monthly adjusted income
2. 10% of monthly gross income
3. Welfare rent — N/A for this program (TDHCA's plan: "Welfare rent does not apply")
4. Minimum rent, **$25/month** — 24 CFR 5.630(a)(2) actually gives TDHCA *discretion* to set HCV's minimum rent anywhere from $0 to $50 (HCV is grouped with public housing and moderate rehab in the discretionary range, not the flat-$25 "other section 8" bucket in (a)(3)); TDHCA elected $25 within that range (Admin Plan, p.90: *"The minimum rent for all Department localities is $25.00 per month"*). Waivable for documented financial hardship (temporary hardship: 90-day suspension; permanent hardship: ongoing exemption) — not evaluable from screener data

**Calculator implementation:** Adjusted annual income = gross annual income (`calc_gross_income("yearly", ["all"])`) minus the two deductions below; adjusted monthly income = adjusted annual income ÷ 12. Implement all three TTP components (30%-of-adjusted, 10%-of-gross, $25 floor) and take the highest — don't skip item 2 as an optimization, even though no scenario in this spec exercises it as the binding term. That's a real property of the math, not an oversight: for a very-low-income household with dependents, 30%-of-adjusted can drop below 10%-of-gross, but at that point both are already close to the $25 floor, so the floor — not the 10% term — ends up deciding TTP. The zero-income case (Scenario 14) is where the $25 floor binds. Round TTP to the nearest dollar (24 CFR 5.628).

**Income exclusions modeled** (24 CFR 5.609(b)) — apply before computing gross income, for both this eligibility test and the benefit value calculation below: (1) earned income (wages/self-employment) of a household member under 18 is excluded entirely — their *unearned* income (Social Security, child support, etc.) still counts; (2) all income of a `fosterChild`-relationship member is excluded entirely, earned or unearned. MFB's `calc_gross_income("yearly", ["all"])` sums every member's income with no such filtering — implement this by filtering `income_streams` by member age/type and by `relationship == "fosterChild"` before summing, not by using that call as-is. Scenario 23 tests the under-18-earned-income exclusion; Scenario 24 tests the foster-child exclusion (which is broader than the under-18 exclusion — it also covers a foster child's *unearned* income, which would otherwise still count for an ordinary minor).

**Other income exclusions — data gap, not modeled.** 24 CFR 5.609(b) also excludes foster-care/kinship-guardianship care payments, student financial assistance (scholarships/grants), insurance settlements, medical-expense reimbursements, disability-related civil-action settlements, PASS-plan set-asides, resident service stipends (≤$200/month), employment-training program earnings, and 529/Coverdell/baby-bond income, among others. None of these have a distinct `income_streams` type in MFB's screener (confirmed against the model) — a household receiving any of them has no way to report it as anything other than generic `other` income, so the calculator can't detect and exclude them specifically. Not evaluable, and no scenario is possible for these: there's no way to construct a household input that isolates them from ordinary `other` income. A genuine screener-driven data gap, not a modeling gap — flagged here rather than left silent.

**Adjusted-income deductions modeled** (24 CFR 5.611(a)):
- **$480/year per dependent** — a household member other than head, spouse, or co-head who is under 18, or 18+ and disabled or a full-time student. Foster children, foster adults, and live-in aides never count. MFB's `relationship` field has a distinct `fosterChild` value — exclude it. It has no distinct value for foster adults or live-in aides, so those can't be excluded from the count; if either is present in a household, they'll be incorrectly counted as a dependent when they meet the age/disability/student test. A known, narrow limitation, not an oversight. MFB's own tax-dependent logic (`is_dependent()`) uses a different definition (different age cutoffs, adds an income test HUD's rule doesn't have) and can't be reused as-is.
- **$525/year flat, once per family** for any elderly (62+) or disabled family — triggered by the head, spouse, or co-head being 62+ or disabled, not by any household member's status. Sourced to the current federal regulation (24 CFR 5.611(a)(2), CPI-adjusted annually) — **not** TDHCA's own Sept. 2022 Admin Plan, which still states the older, pre-HOTMA $400 figure (p.84). HUD's Part 5 Subpart F deduction amounts are federally mandated and CPI-indexed, not PHA-discretionary, so the current federal figure governs even though TDHCA's own plan text hasn't caught up — worth re-confirming once TDHCA republishes its plan.

**Deferred** (matching WA HCV's precedent for the same program type): unreimbursed medical/disability-assistance expenses exceeding 10% of annual income, and childcare expenses capped at the enabled member's earned income. Both require expense-amount data (`medical`, `childcare`) the screener collects but that add real complexity (the childcare cap in particular). Omitting them is a documented, deliberate simplification — it understates the benefit for households with qualifying expenses.

**Payment Standard = 100% of HUD's published FMR** for the household's county/area and bedroom size — a reasonable midpoint, since PHAs may set their actual payment standard anywhere from 90% to 110% of FMR without HUD approval (24 CFR 982.503(c)) and that split isn't knowable from screener data. Two lookup paths:

- **Dallas, Fort Worth-Arlington, San Antonio, Beaumont-Port Arthur** (the only TX mandatory-SAFMR metros, per HUD Notice PIH 2023-32 Appendix A) → ZIP-level Small Area FMR.
- **Everywhere else** (including Houston/Harris County, which publishes SAFMR data but isn't *mandatory*) → county-level / HUD Metro FMR Area FMR, below.

| County / Metro Area | Efficiency | 1BR | 2BR | 3BR | 4BR |
|---|---|---|---|---|---|
| Harris (Houston-The Woodlands-Sugar Land) | $1,280 | $1,323 | $1,573 | $2,116 | $2,639 |
| El Paso | $821 | $1,013 | $1,191 | $1,633 | $1,998 |
| Lubbock | $818 | $990 | $1,175 | $1,634 | $1,940 |
| Midland | $1,424 | $1,449 | $1,780 | $2,286 | $2,667 |
| Hidalgo (McAllen-Edinburg-Mission) | $842 | $847 | $1,060 | $1,376 | $1,522 |
| Cameron (Brownsville-Harlingen) | $773 | $866 | $1,047 | $1,414 | $1,479 |
| McLennan (Waco) | $850 | $996 | $1,240 | $1,599 | $1,644 |

*FY2026 figures, from HUD's official FMR table — verified against every county used in this spec's scenarios. Re-fetch and refresh annually. Not shown: Dallas, Bexar, Tarrant, and Collin use ZIP-level SAFMR instead (a separate HUD dataset), so their per-ZIP figures aren't comparable to this metro-wide table.*

**Documented simplification:** TDHCA and Houston Housing Authority both publish their own, more granular payment standards that can differ from generic FMR (e.g., TDHCA's real McLennan 3BR rate is $2,050/month vs. this table's $1,599 estimate). Not modeled — matches how other MFB Custom HCV programs (e.g. WA) make the same tradeoff, favoring a maintainable, self-contained data source over PHA-level precision. A known limitation, not an oversight.

**Family Share affordability constraint** (context only, doesn't change the formula): if a family chooses a unit with rent above the payment standard, they pay the difference out of pocket, and TDHCA won't approve an initial tenancy where total housing cost would exceed 40% of the family's monthly adjusted income (24 CFR 982.305(a)(5)).

**Bedroom size** (24 CFR 982.402; TDHCA HCV Administrative Plan (Sept. 2022 update), Ch. 5 Part II):

| Household size | Voucher bedroom size |
|---|---|
| 1 | 0BR (TDHCA leaves this as a discretionary 0BR-or-1BR choice; MFB defaults to 0BR as the conservative assumption) |
| 2 | 1BR |
| 3–4 | 2BR |
| 5–6 | 3BR |
| 7–8 | 4BR |

Not modeled: an approved live-in aide must be counted toward family unit size (24 CFR 982.402) — MFB's screener has no live-in-aide relationship category, so this can't be detected. Doesn't affect any scenario in this spec, but is a known limitation for future household compositions.

**Mixed-status household proration not modeled** (see Criterion 4 — this is a value question, not an eligibility one; whether the program is shown at all is already correctly handled by `legal_status_required`). A household with some but not all members having eligible immigration status legally receives **prorated** assistance — the pre-proration HAP (payment standard minus TTP) × eligible members ÷ total members, 24 CFR 5.520 — not the full payment standard times that fraction. The screener doesn't collect per-member immigration status, so this calculator shows the full, unprorated value for every household — an overestimate for the (likely small) subset of genuinely mixed-status households. Not fixed in this ticket; flagged for awareness.

**Sources:** TDHCA HCV Administrative Plan (Sept. 2022 update), Ch. 5 Part II, Ch. 6 Parts I–III; 24 CFR §§ 5.520, 5.609, 5.611, 5.618, 5.628, 5.630, 982.305(a)(5), 982.402, 982.503(c), 982.505, 982.517; HUD FMR Dataset Portal (https://www.huduser.gov/portal/datasets/fmr.html); HUD Small Area Fair Market Rents (https://www.huduser.gov/portal/datasets/fmr/smallarea/index.html); HUD Notice PIH 2023-32, Appendix A (https://www.hud.gov/sites/dfiles/PIH/documents/PIH2023-32.pdf).

## Implementation Coverage

- ✅ Real, hard eligibility gates implemented entirely in MFB's own logic: **3** — income (Criterion 1), duplicate-benefit exclusion (Criterion 2), head-of-household legal capacity to lease (Criterion 3, with one narrow, deliberately-unmodeled exception — see Criterion 3's emancipated-minor note)
- ℹ️ Non-gating, informational: geography (routes to payment-standard lookup only, see the note above Criterion 1); citizenship/immigration status (Criterion 4 — handled via `legal_status_required`, not a data gap; see Criterion 4 and the Benefit Value section for the separate mixed-status-proration value nuance)
- ⚠️ Data gaps: **5** (Criteria 5–9), each handled differently:
  - **Criteria 5–7** (criminal background, PHA discretionary history, drug-related eviction): inclusivity assumption, results kept off the page. Narrow-or-invasive facts the reviewer decided not to broadcast — most applicants have no disqualifying history, and this class of language risks a chilling effect, the same caution that already excludes this data from screener collection; TDHCA's formal notice process is the individualized channel for anyone actually affected. Criterion 5 has one partial exception: the background-check *result* stays off the page, but the separate, controllable fact that refusing to *consent* to verification is itself a mandatory denial ground is surfaced (see Criterion 5's consent note).
  - **Criterion 8** (student restrictions): partial screener field coverage plus a recommended screener addition (foster-care tile) — not description text.
  - **Criterion 9** (net assets): different in kind — directly evaluable via the existing `household_assets` field when reported (inclusivity default only when the field is left blank), a hard conservative gate when assets are reported over $100k, and surfaced in the description.

SSN is a document requirement (the config's `tx_ssn` document), not an eligibility criterion, despite also appearing as a TDHCA mandatory-denial ground.

## Research Sources

**Program overview and eligibility**
- [HUD Housing Choice Voucher (Section 8) Program Guide for Tenants](https://www.hud.gov/helping-americans/housing-choice-vouchers-tenants)
- [Texas Law Help: Housing Choice Vouchers (Section 8)](https://texaslawhelp.org/article/housing-choice-vouchers-section-8)
- [TDHCA Housing Choice Voucher Section 8 Program](https://www.tdhca.texas.gov/programs/housing-choice-voucher-section8-housing)
- [TDHCA Section 8 Resources (Payment Standards, PHA Plans, Administrative Plan)](https://www.tdhca.texas.gov/section-8-resources)
- [USA.gov: Housing Choice Voucher (Section 8)](https://www.usa.gov/housing-voucher-section-8)

**TDHCA Administrative Plan (primary source for TDHCA-specific eligibility, denial, and preference rules)**
- [TDHCA Housing Choice Voucher Program Administrative Plan (Sept. 2022 update)](https://www.tdhca.texas.gov/sites/default/files/section-8/docs/22-HCVP-AdminPlan.pdf) — confirmed still the current version as of 2026-07-08 (no newer revision published). Cited throughout Eligibility Criteria and Priority Criteria for TDHCA-specific rules: income-ceiling exceptions and legal-capacity-to-lease standard (Ch. 3 Part I–II), denial grounds (Ch. 3 Part III), local-preference mechanism (Ch. 3 Part II p.51, Part III p.268), bedroom-size standards (Ch. 5 Part II), and HAP calculation (Ch. 6 Parts I–III). Note: this plan's Ch. 6 deduction figures (elderly/disabled deduction, medical-expense threshold) are pre-HOTMA and stale — this spec follows the current federal regulation instead where the two conflict (see Benefit Value).

**Federal eligibility regulations**
- [24 CFR 982.353 — Move with continued tenant-based assistance](https://www.law.cornell.edu/cfr/text/24/982.353) — confirms no residency requirement for initial application; 12-month jurisdiction restriction for nonresident families
- [24 CFR 5.504(b) — Family information and verification](https://www.law.cornell.edu/cfr/text/24/5.504) — head-of-household legal-capacity-to-lease requirement
- [24 CFR 5.618 / 5.609 — Net family assets](https://www.law.cornell.edu/cfr/text/24/5.618) — HOTMA $100,000 asset limit and $50,000 income-imputation threshold
- [24 CFR 982.517 — Utility allowance schedule](https://www.law.cornell.edu/cfr/text/24/982.517) — Gross Rent = rent-to-owner + utility allowance; not modeled (see Benefit Value)
- [24 CFR 5.522 / 42 U.S.C. § 1436a(c)(2)(A) — Noncitizen student bar](https://www.law.cornell.edu/cfr/text/24/5.522) — categorical bar for temporary-visa students and their noncitizen spouse/children; not modeled (see Criterion 4)
- [HUD Housing Choice Voucher Guidebook (7420.10G), "Eligibility Determination and Denial of Assistance"](https://www.hud.gov/sites/dfiles/PIH/documents/HCV_Guidebook_Eligibility_Determination_and_Denial_of_Assistance.pdf) — HUD's own national baseline; used to cross-check that TDHCA's plan doesn't omit or misstate any federally-required eligibility/denial factor

**Income limits**
- [HUD FY2026 Section 8 Income Limits](https://www.huduser.gov/portal/datasets/il/il26/Section8-IncomeLimits-FY26.pdf) — primary source; values verified against HUD's official FY2026 dataset for every county used in this spec's scenarios. Re-fetch and update annually when HUD publishes new limits.

**Payment standards**
- [HUD Fair Market Rents Dataset Portal](https://www.huduser.gov/portal/datasets/fmr.html) — primary source for county-level FMR (used as Payment Standard everywhere outside the mandatory-SAFMR metros)
- [HUD Small Area Fair Market Rents (SAFMRs)](https://www.huduser.gov/portal/datasets/fmr/smallarea/index.html) — primary source for ZIP-level FMR in the mandatory-SAFMR metros
- [24 CFR 982.505 — Payment standard amount and schedule](https://www.ecfr.gov/current/title-24/subtitle-B/chapter-IX/part-982/subpart-K/section-982.505)
- [HUD Notice PIH 2023-32, Appendix A](https://www.hud.gov/sites/dfiles/PIH/documents/PIH2023-32.pdf) — confirms Dallas, Fort Worth-Arlington, San Antonio-New Braunfels, and Beaumont-Port Arthur as the only TX mandatory-SAFMR metros; Houston is not listed

**Waitlist status**
- [TDHCA PHA Portal](https://phaportal.tdhca.texas.gov/) — live source for current waitlist status; confirmed closed as of research date (June 2026) and re-confirmed closed as of 2026-07-08 via TDHCA's own announcements page and a third-party tracker showing the list closed again as of 2026-02-24 — implying an open/close cycle between the original May 2022 opening and today that this spec doesn't track in detail. Re-verify immediately before import regardless.
- [TDHCA announcement: last known opening before the current closure (May 2022)](https://www.tdhca.texas.gov/news/tdhca-announces-housing-choice-voucher-program-pre-applications-wait-list-open-may-2) — historical reference only; the list has opened and closed at least once since, most recently closing 2026-02-24

## Acceptance Criteria

[ ] Scenario 1 (Clearly Eligible Single Mother with Two Children in Harris County): User should be **eligible** with $12,684/year
[ ] Scenario 2 (Minimally Eligible Single Adult Just Under 50% AMI in El Paso County): User should be **eligible** with $2,832/year
[ ] Scenario 3 (Family of Four, Multi-Earner Income Aggregation, in Dallas County): User should be **eligible** with $18,348/year
[ ] Scenario 4 (Elderly Couple in Bexar County — TTP Exceeds Payment Standard): User should be **eligible** for the voucher with **$0/year** benefit value
[ ] Scenario 5 (Single Adult with Income Above the Real 50% AMI Limit in Travis County): User should be **ineligible**
[ ] Scenario 6 (Head of Household Exactly Age 18 in Tarrant County): User should be **eligible** with $16,920/year
[ ] Scenario 7 (17-Year-Old Head of Household in El Paso County - Below Minimum Age): User should be **ineligible**
[ ] Scenario 8 (45-Year-Old Head of Household Well Above Minimum Age in Lubbock County): User should be **eligible** with $5,496/year
[ ] Scenario 9 (Eligible Single Adult in Midland County - West Texas Service Area): User should be **eligible** with $12,768/year
[ ] Scenario 10 (Single Adult Already Receiving Section 8/HCV Assistance in Harris County): User should be **ineligible**
[ ] Scenario 11 (Currently Receiving HCV/Section 8 Assistance - Duplicate Benefit Exclusion in Dallas County): User should be **ineligible**
[ ] Scenario 12 (Mixed Household - Adult Head with Elderly Parent and Minor Child in Hidalgo County): User should be **eligible** with $5,124/year
[ ] Scenario 13 (Multiple Eligible Adults in Same Household - Two Working Adults with Two Children in Collin County): User should be **eligible** with $21,888/year
[ ] Scenario 14 (Household of One with Exactly Zero Income in Cameron County): User should be **eligible** with $8,976/year
[ ] Scenario 15 (Full-Time Student with Low Income in Lubbock County): User should be **eligible** with $6,936/year
[ ] Scenario 16 (Household of Five in McLennan County — Waco): User should be **eligible** with $12,420/year
[ ] Scenario 17 (Single Adult Between 50% and 80% AMI in Travis County — Ineligible Despite Clearing the Generic Federal Ceiling): User should be **ineligible**
[ ] Scenario 18 (Large Family of Seven in McLennan County — Waco, Tests 4BR Payment Standard Tier): User should be **eligible** with $12,168/year
[ ] Scenario 19 (Reported Rent Below Payment Standard in El Paso County): User should be **eligible** with $1,800/year
[ ] Scenario 20 (Household Exceeding the HOTMA Net-Asset Limit in Harris County): User should be **ineligible**
[ ] Scenario 21 (Elderly Head of Household with an 18+ Disabled Dependent in Bexar County): User should be **eligible** with $5,700/year
[ ] Scenario 22 (Foster Child Correctly Excluded from the Dependent Deduction in Harris County): User should be **eligible** with $11,556/year
[ ] Scenario 23 (Working Teenager's Wages Correctly Excluded from Countable Income in El Paso County): User should be **eligible** with $8,700/year
[ ] Scenario 24 (Foster Child's Unearned Income Correctly Excluded in Harris County): User should be **eligible** with $11,556/year

## Test Scenarios

### Scenario 1: Clearly Eligible Single Mother with Two Children in Harris County

**What we're checking**: Typical applicant who meets all eligibility criteria: income well below 50% AMI, head of household is 18+, not currently receiving Section 8, appropriate household size.

**Expected**: Eligible, $12,684/year

**Steps**:
- **Location**: Enter ZIP code `77002`, Select county `Harris`
- **Household**: Number of people: `3`
- **Person 1**: Birth month/year: `March 1991` (age 35), Relationship: Head of Household, Has income: Yes, Employment income: `$1,800` per month
- **Person 2**: Birth month/year: `September 2016` (age 9), Relationship: Child, Has income: No
- **Person 3**: Birth month/year: `January 2020` (age 6), Relationship: Child, Has income: No
- **Current Benefits**: Section 8 / Housing Choice Voucher: No

**Why this matters**: Baseline happy-path test, and the first scenario with dependents to exercise the $480/dependent deduction. Annual income $21,600 is well below the Harris County 3-person VLI of **$46,800 (FY2026)**. Houston isn't a mandatory-SAFMR metro, so payment standard uses the county-level FMR: 2BR (household size 3) = $1,573/month. Two dependents (both children) = $960/year deduction. Adjusted annual income = $21,600 − $960 = $20,640; adjusted monthly = $1,720. TTP = max(30% × $1,720, 10% × $1,800, $25) = $516/month. HAP = $1,573 − $516 = $1,057/month → **$12,684/year**.

---

### Scenario 2: Minimally Eligible Single Adult Just Under 50% AMI in El Paso County

**What we're checking**: Single-person household with income comfortably below the 50% AMI threshold, head of household just turned 18.

**Expected**: Eligible, $2,832/year

**Steps**:
- **Location**: Enter ZIP code `79901`, Select county `El Paso`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `May 2008` (age 18), Relationship: Head of Household, Has income: Yes, Employment income: `$1,950` per month, No current Section 8 / HCV assistance

**Why this matters**: Tests the youngest possible head of household and smallest household size. Annual income $23,400 is below the El Paso 1-person VLI (**~$29,300, FY2026**). El Paso isn't TDHCA-served or a mandatory-SAFMR metro, so payment standard uses the county FMR: 0BR = $821/month. TTP = $1,950 × 0.30 = $585/month. HAP = $821 − $585 = $236/month → **$2,832/year**.

---

### Scenario 3: Family of Four Just Under the Real 50% AMI Limit in Dallas County

**What we're checking**: Multi-earner income aggregation for a 4-person household, near (but under) the real eligibility ceiling.

**Expected**: Eligible, $18,348/year

**Steps**:
- **Location**: Enter ZIP code `75201`, Select county `Dallas`
- **Household**: Number of people: `4`
- **Person 1**: Birth month/year: `March 1986` (age 40), Relationship: Head of Household, Has income: Yes, Employment income: `$3,500` per month
- **Person 2**: Birth month/year: `September 1988` (age 37), Relationship: Spouse, Has income: Yes, Employment income: `$1,150` per month
- **Person 3**: Birth month/year: `January 2018` (age 8), Relationship: Child, Has income: No
- **Person 4**: Birth month/year: `July 2020` (age 5), Relationship: Child, Has income: No
- **Current Benefits**: NOT currently receiving Section 8/HCV assistance

**Why this matters**: Combined income $4,650/month ($55,800/year) is safely under Dallas's 4-person VLI (**$60,550, FY2026**). Dallas is a mandatory-SAFMR metro: ZIP 75201 (downtown), 2BR = $2,900/month. Two dependents (both children) = $960/year deduction. Adjusted annual income = $55,800 − $960 = $54,840; adjusted monthly = $4,570. TTP = max(30% × $4,570, 10% × $4,650, $25) = $1,371/month. HAP = $2,900 − $1,371 = $1,529/month → **$18,348/year**.

---

### Scenario 4: Elderly Couple in Bexar County (San Antonio) — TTP Exceeds Payment Standard, $0 Benefit Value

**What we're checking**: The Benefit Value formula's $0-floor edge case — TTP can exceed the payment standard, in which case the household remains eligible for the voucher but receives no net subsidy (pays full rent).

**Expected**: Eligible for the voucher program, but **$0 benefit value**

**Steps**:
- **Location**: Enter ZIP code `78207`, Select county `Bexar`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `March 1958` (age 68), Relationship: Head of Household, Has income: Yes, Income type: Social Security Retirement (`sSRetirement` in test case schema), Amount: `$2,000` per month
- **Person 2**: Birth month/year: `September 1960` (age 65), Relationship: Spouse, Has income: Yes, Income type: Social Security Retirement (`sSRetirement` in test case schema), Amount: `$1,000` per month
- **Current Benefits**: Section 8 / Housing Choice Voucher: No

**Why this matters**: Tests Social Security retirement income handling, the elderly-family deduction, and the TTP-exceeds-payment-standard branch together. Combined income $3,000/month ($36,000/year) is under Bexar's 2-person VLI (**$40,250, FY2026**), so the household is eligible. Bexar/San Antonio is a mandatory-SAFMR metro, but ZIP 78207 is a lower-rent neighborhood: 1BR SAFMR = $870/month. This household qualifies as an "elderly family" (head is 62+), so the $525/year deduction applies: adjusted annual income = $36,000 − $525 = $35,475; adjusted monthly = $2,956.25. TTP = max(30% × $2,956.25, 10% × $3,000, $25) = $887/month (rounded), which still exceeds the $870 payment standard — HAP floors at **$0/year**. Even with the deduction correctly applied, this household nets $0: the $43.75/month-equivalent reduction from the annual deduction isn't enough to close the $30/month gap between TTP and payment standard.

---

### Scenario 5: Single Adult with Income Above the Real 50% AMI Limit in Travis County (Austin)

**What we're checking**: The screener correctly rejects applicants above the real eligibility ceiling.

**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78745`, Select county `Travis`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1991` (age 35), Relationship: Head of Household, Has income: Yes, Employment income: `$6,250` per month, No current benefits

**Why this matters**: Travis County's 1-person VLI is **$47,050/year (FY2026)**; at $75,000/year, income exceeds it by a wide margin — an unambiguous ineligible case (also above the generic federal 80% AMI ceiling of **$74,800 (FY2026)**, so it stays ineligible under either standard). Contrast with Scenario 17, which sits between the two ceilings and depends on using the correct one.

---

### Scenario 6: Head of Household Exactly Age 18 in Tarrant County

**What we're checking**: The exact age-18 boundary is correctly included.

**Expected**: Eligible, $16,920/year

**Steps**:
- **Location**: Enter ZIP code `76102`, Select county `Tarrant`
- **Household**: Number of people: `1`
- **Person 1**: Relationship: Head of Household, Birth month/year: `May 2008` (age exactly 18 — turned 18 last month), Has income: Yes, Employment income: `$900` per month, No current Section 8/HCV assistance

**Why this matters**: Fort Worth-Arlington is a mandatory-SAFMR metro: ZIP 76102, 0BR = $1,680/month. TTP = $900 × 0.30 = $270/month. HAP = $1,680 − $270 = $1,410/month → **$16,920/year**.

---

### Scenario 7: 17-Year-Old Head of Household in El Paso County - Below Minimum Age

**What we're checking**: A head of household one year below the minimum age is correctly rejected.

**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `79901`, Select county `El Paso`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `September 2008` (age 17), Relationship: Head of Household, Has income: Yes, Employment income: `$1,200` per month, No current Section 8/HCV assistance

**Why this matters**: Age 17 is below the Criterion 3 minimum regardless of income — confirms the age gate is enforced independently of the income test. This represents an ordinary (non-emancipated) 17-year-old; the rare emancipated-minor/other-qualifications exception (see Criterion 3) is a documented, deliberately-conservative gap, not modeled here.

---

### Scenario 8: 45-Year-Old Head of Household Well Above Minimum Age in Lubbock County

**What we're checking**: A typical mid-range adult age processes correctly, complementing the boundary tests (Scenarios 6, 7).

**Expected**: Eligible, $5,496/year

**Steps**:
- **Location**: Enter ZIP code `79401`, Select county `Lubbock`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1981` (age 45), Relationship: Head of Household, Has income: Yes, Employment income: `$1,200` per month, Not currently receiving Section 8/HCV assistance

**Why this matters**: Lubbock isn't TDHCA-served or a mandatory-SAFMR metro, so payment standard uses the county FMR: 0BR = **$818/month (FY2026)**. TTP = $1,200 × 0.30 = $360/month. HAP = $818 − $360 = $458/month → **$5,496/year**.

---

### Scenario 9: Eligible Single Adult in Midland County - West Texas Service Area

**What we're checking**: The screener maps a West Texas ZIP to its own area median (oil-market-driven, higher than comparable-size TX metros) rather than a statewide average.

**Expected**: Eligible, $12,768/year

**Steps**:
- **Location**: Enter ZIP code `79701`, Select county `Midland`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1991` (age 35), Relationship: Head of Household, Has income: Yes, Employment income: `$1,200` per month, No current Section 8/HCV assistance

**Why this matters**: Midland isn't TDHCA-served or SAFMR: 0BR county FMR = **$1,424/month (FY2026)**. TTP = $1,200 × 0.30 = $360/month. HAP = $1,424 − $360 = $1,064/month → **$12,768/year**.

---

### Scenario 10: Single Adult Already Receiving Section 8/HCV Assistance in Harris County

**What we're checking**: The duplicate-benefit exclusion (Criterion 2) for a household already receiving Section 8.

**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `77001`, Select county `Harris`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1986` (age 40), Relationship: Head of Household, Has income: No
- **Current Benefits**: Indicate household is **already receiving Section 8 / Housing Choice Voucher assistance** (`has_section_8: true`)

**Why this matters**: 24 CFR 982.551(n) prohibits duplicate HCV assistance. The JSON test case must include `has_section_8: true` at the household level to trigger this exclusion (see Criterion 2).

---

### Scenario 11: Currently Receiving HCV/Section 8 Assistance - Duplicate Benefit Exclusion in Dallas County

**What we're checking**: The same duplicate-benefit exclusion for a multi-person household.

**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `75201`, Select county `Dallas`
- **Household**: Number of people: `3`
- **Person 1**: Birth month/year: `March 1988` (age 38), Relationship: Head of Household, Has income: Yes, Employment income: `$1,800` per month
- **Person 2**: Birth month/year: `September 2014` (age 11), Relationship: Child, Has income: No
- **Person 3**: Birth month/year: `January 2018` (age 8), Relationship: Child, Has income: No
- **Current Benefits**: Indicate household is currently receiving Section 8 / Housing Choice Voucher assistance (`has_section_8: true`)

**Why this matters**: Confirms the exclusion holds for larger households too, not just single-person ones.

---

### Scenario 12: Mixed Household - Adult Head with Elderly Parent and Minor Child in Hidalgo County

**What we're checking**: Income aggregation across a mixed-generation household with multiple income sources.

**Expected**: Eligible, $5,124/year

**Steps**:
- **Location**: Enter ZIP code `78501`, Select county `Hidalgo`
- **Household**: Number of people: `3`
- **Person 1**: Birth month/year: `March 1991` (age 35), Relationship: Head of Household, Has income: Yes, Employment income: `$1,400` per month, Not currently receiving Section 8/HCV assistance
- **Person 2**: Birth month/year: `January 1958` (age 68), Relationship: Parent, Has income: Yes, Social Security Retirement: `$750` per month, Insurance: Medicare
- **Person 3**: Birth month/year: `September 2018` (age 7), Relationship: Child, Has income: No, Insurance: Medicaid
- **Current Benefits**: NOT currently receiving HCV/Section 8 assistance

**Why this matters**: Annual combined income $25,800 is well below Hidalgo/McAllen's 3-person VLI (**~$37,700, FY2026**). Hidalgo isn't TDHCA-served or SAFMR: 2BR county FMR = **$1,060/month (FY2026)**. Only the child counts as a dependent — the elderly parent doesn't: HUD's dependent definition requires being under 18, disabled, or a full-time student, and the parent is none of those; nor does the household qualify as an "elderly family," since that designation depends on the head/spouse/co-head's age, not any other member's. One dependent = $480/year deduction. Adjusted annual income = $25,800 − $480 = $25,320; adjusted monthly = $2,110. TTP = max(30% × $2,110, 10% × $2,150, $25) = $633/month. HAP = $1,060 − $633 = $427/month → **$5,124/year**.

---

### Scenario 13: Multiple Eligible Adults in Same Household - Two Working Adults with Two Children in Collin County

**What we're checking**: Multiple income-earning adults are aggregated into one household total.

**Expected**: Eligible, $21,888/year

**Steps**:
- **Location**: Enter ZIP code `75024`, Select county `Collin`
- **Household**: Number of people: `4`
- **Person 1**: Relationship: Head of Household, Birth month/year: `March 1991` (age 35), Has income: Yes, Employment income: `$1,400` per month
- **Person 2**: Relationship: Spouse, Birth month/year: `September 1993` (age 32), Has income: Yes, Employment income: `$1,200` per month
- **Person 3**: Relationship: Child, Birth month/year: `January 2018` (age 8), Has income: No
- **Person 4**: Relationship: Child, Birth month/year: `July 2021` (age 4), Has income: No
- **Current Benefits**: NOT receiving Section 8 / HCV

**Why this matters**: Combined income $31,200/year is well below the Dallas-metro 4-person VLI (**~$60,550, FY2026**). Collin County falls within the Dallas mandatory-SAFMR metro: ZIP 75024 (Plano), 2BR = $2,580/month. Two dependents (both children) = $960/year deduction. Adjusted annual income = $31,200 − $960 = $30,240; adjusted monthly = $2,520. TTP = max(30% × $2,520, 10% × $2,600, $25) = $756/month. HAP = $2,580 − $756 = $1,824/month → **$21,888/year**.

---

### Scenario 14: Household of One with Exactly Zero Income in Cameron County

**What we're checking**: Zero income is handled gracefully, and — the key thing this scenario tests — TDHCA's $25/month minimum-rent floor is applied to TTP rather than letting it collapse to literal $0.

**Expected**: Eligible, $8,976/year

**Steps**:
- **Location**: Enter ZIP code `78520`, Select county `Cameron`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `February 1996` (age 30), Relationship: Head of Household, Has income: No (no income sources selected), Currently receiving Section 8/HCV: No, Insurance: None

**Why this matters**: Zero-income applicants are common in real HCV populations. Cameron isn't TDHCA-served or SAFMR: 0BR county FMR = **$773/month (FY2026)**. At $0 income, TTP's 30%-of-income and 10%-of-gross terms are both $0, so the $25/month minimum-rent floor governs: TTP = $25/month. HAP = $773 − $25 = $748/month → **$8,976/year**. (A naive implementation that lets TTP go to literal $0 would incorrectly compute $9,276/year.)

---

### Scenario 15: Full-Time Student with Low Income in Lubbock County

**What we're checking**: The student-restrictions inclusivity assumption (Criterion 8) — a full-time student with no disqualifying flags still shows as eligible.

**Expected**: Eligible, $6,936/year

**Steps**:
- **Location**: Enter ZIP code `79401`, Select county `Lubbock`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `April 2004` (age 22), Relationship: Head of Household, Full-time student: Yes (`student: true`, `student_full_time: true`), Has income: Yes, Employment income: `$800` per month, No current Section 8/HCV assistance

**Why this matters**: The calculator can't determine student-restriction status from screener data alone (no dependents, not married, no veteran status, no job training program on record), so it defaults to eligible. Same Lubbock 0BR payment standard as Scenario 8 (**$818/month, FY2026**). TTP = $800 × 0.30 = $240/month. HAP = $818 − $240 = $578/month → **$6,936/year**.

---

### Scenario 16: Household of Five in McLennan County (Waco) — Tests 3BR Payment Standard Tier

**What we're checking**: A 5-person household correctly maps to the 3BR voucher bedroom size, and the county-level FMR payment standard is applied correctly.

**Expected**: Eligible, $12,420/year

**Steps**:
- **Location**: Enter ZIP code `76701`, Select county `McLennan`
- **Household**: Number of people: `5`
- **Person 1**: Birth month/year: `January 1985` (age 41), Relationship: Head of Household, Has income: Yes, Employment income: `$2,000` per month
- **Person 2**: Birth month/year: `March 1988` (age 38), Relationship: Spouse, Has income: No
- **Person 3**: Birth month/year: `March 2016` (age 10), Relationship: Child, Has income: No
- **Person 4**: Birth month/year: `January 2018` (age 8), Relationship: Child, Has income: No
- **Person 5**: Birth month/year: `June 2021` (age 4), Relationship: Child, Has income: No
- **Current Benefits**: NOT currently receiving Section 8/HCV assistance

**Why this matters**: All other scenarios test household sizes 1–4 (0BR–2BR tiers); this is the one 3BR test. McLennan/Waco isn't a mandatory-SAFMR metro, so payment standard uses the county-level FMR: 3BR = $1,599/month. Three dependents (all children) = $1,440/year deduction. Annual income $24,000 is well below the Waco 5-person VLI (**~$48,800, FY2026**). Adjusted annual income = $24,000 − $1,440 = $22,560; adjusted monthly = $1,880. TTP = max(30% × $1,880, 10% × $2,000, $25) = $564/month. HAP = $1,599 − $564 = $1,035/month → **$12,420/year**.

---

### Scenario 17: Single Adult Between 50% and 80% AMI in Travis County (Austin) — Ineligible Despite Clearing the Generic Federal Ceiling

**What we're checking**: The key regression test for Criterion 1 — confirms the calculator uses TDHCA's real, tighter 50% AMI ceiling for ordinary applicants, not the generic 80% AMI figure sometimes cited for Section 8 nationally.

**Expected**: **Not eligible**

**Steps**:
- **Location**: Enter ZIP code `78745`, Select county `Travis`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1991` (age 35), Relationship: Head of Household, Has income: Yes, Employment income: `$4,583.33` per month, No current benefits

**Why this matters**: This household's income ($55,000/year) sits *above* Travis County's real 50% AMI limit (**$47,050, FY2026**) but *below* the generic federal 80% AMI ceiling (**$74,800, FY2026**). TDHCA's actual policy says ineligible — TDHCA only extends the 80% ceiling to five narrow categories (continuously-assisted, HOPE 1/2, mortgage-displaced, Disaster preference, Project Access; see Criterion 1), none of which apply to this ordinary applicant. If this scenario ever returns eligible in testing, the implementation is incorrectly using the generic 80% ceiling instead of TDHCA's real 50% rule. **Caveat:** this ineligible result assumes the household isn't disaster-impacted or transitioning out of an institution (Disaster preference / Project Access) — the calculator can't verify either from screener data, so a genuinely qualifying household in this exact income band would be incorrectly shown as ineligible. See Criterion 1 and Priority Criteria.

---

### Scenario 18: Large Family of Seven in McLennan County (Waco) — Tests 4BR Payment Standard Tier

**What we're checking**: A 7-person household correctly maps to the largest voucher bedroom size (4BR) — the one bedroom-size tier no other scenario exercises (Scenarios 1, 3, 4, and 16 cover 2BR, 2BR, 1BR, and 3BR respectively; nothing previously tested 4BR).

**Expected**: Eligible, $12,168/year

**Steps**:
- **Location**: Enter ZIP code `76701`, Select county `McLennan`
- **Household**: Number of people: `7`
- **Person 1**: Birth month/year: `January 1985` (age 41), Relationship: Head of Household, Has income: Yes, Employment income: `$2,300` per month
- **Person 2**: Birth month/year: `March 1988` (age 38), Relationship: Spouse, Has income: No
- **Person 3**: Birth month/year: `March 2012` (age 14), Relationship: Child, Has income: No
- **Person 4**: Birth month/year: `January 2014` (age 12), Relationship: Child, Has income: No
- **Person 5**: Birth month/year: `June 2016` (age 10), Relationship: Child, Has income: No
- **Person 6**: Birth month/year: `September 2018` (age 8), Relationship: Child, Has income: No
- **Person 7**: Birth month/year: `June 2021` (age 4), Relationship: Child, Has income: No
- **Current Benefits**: NOT currently receiving Section 8/HCV assistance

**Why this matters**: McLennan/Waco isn't a mandatory-SAFMR metro, so payment standard uses the county-level FMR: 4BR = $1,644/month. Five dependents (all children) = $2,400/year deduction — the largest dependent count in this spec, a good stress test for the deduction logic. Annual income $27,600 is well below any plausible 7-person VLI for Waco (the 5-person figure is already ~$48,800, FY2026; HUD income limits increase with household size, so the 7-person figure is higher still). Adjusted annual income = $27,600 − $2,400 = $25,200; adjusted monthly = $2,100. TTP = max(30% × $2,100, 10% × $2,300, $25) = $630/month. HAP = $1,644 − $630 = $1,014/month → **$12,168/year**.

---

### Scenario 19: Reported Rent Below Payment Standard in El Paso County

**What we're checking**: When a household reports actual rent lower than the Payment Standard, HAP uses `min(Payment Standard, reported rent)` — not Payment Standard alone. Confirms the calculator reads the `rent` expense field rather than defaulting to the Payment-Standard-only estimate every time it's available.

**Expected**: Eligible, $1,800/year

**Steps**:
- **Location**: Enter ZIP code `79901`, Select county `El Paso`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1991` (age 35), Relationship: Head of Household, Has income: Yes, Employment income: `$1,500` per month, No current Section 8/HCV assistance
- **Expenses**: Rent: `$600` per month

**Why this matters**: Annual income $18,000 is well below the El Paso 1-person VLI (~$29,300, FY2026). El Paso's Payment Standard (0BR) is $821/month, but this household's reported rent ($600/month) is lower — the real formula uses the lower of the two. TTP = $1,500 × 0.30 = $450/month. HAP = min($821, $600) − $450 = $600 − $450 = $150/month → **$1,800/year**. A naive implementation that always uses Payment Standard regardless of reported rent would incorrectly compute HAP = $821 − $450 = $371/month → $4,452/year — overstating this household's real benefit by more than 2×.

---

### Scenario 20: Household Exceeding the HOTMA Net-Asset Limit in Harris County

**What we're checking**: The net-assets eligibility gate (Criterion 9) — a household otherwise well within the income limit is correctly rejected once reported assets exceed the $100,000 HOTMA cap.

**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `77002`, Select county `Harris`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1991` (age 35), Relationship: Head of Household, Has income: Yes, Employment income: `$1,200` per month, No current Section 8/HCV assistance
- **Household assets**: `$150,000`

**Why this matters**: Income alone ($14,400/year) is well under Harris County's 1-person VLI, so a naive implementation would show this household eligible on income alone. 24 CFR 5.618(a) makes net assets over $100,000 — absent a real-property exemption the screener can't detect — a mandatory federal denial ground. Confirms the calculator checks `household_assets` independently of the income test rather than skipping it.

---

### Scenario 21: Elderly Head of Household with an 18+ Disabled Dependent in Bexar County

**What we're checking**: Two previously-untested branches of the dependent deduction at once — (1) a dependent who qualifies via the "18+ and disabled or a full-time student" path rather than being under 18, and (2) the $480/dependent and $525/elderly-family deductions both applying to the same household simultaneously (every other scenario with dependents has a non-elderly head, and Scenario 4's elderly-family case has no dependents).

**Expected**: Eligible, $5,700/year

**Steps**:
- **Location**: Enter ZIP code `78207`, Select county `Bexar`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `April 1963` (age 63), Relationship: Head of Household, Has income: Yes, Employment income: `$1,400` per month, No current Section 8/HCV assistance
- **Person 2**: Birth month/year: `May 2007` (age 19), Relationship: Child, Disabled: Yes, Has income: No

**Why this matters**: Annual income $16,800 is well below Bexar County's 2-person VLI of **$40,250 (FY2026, independently verified)**. Bexar/San Antonio is a mandatory-SAFMR metro; ZIP 78207's 1BR SAFMR is $870/month (same rate as Scenario 4). Person 2 qualifies as a dependent through the age-19-and-disabled path, not the under-18 path — $480/year. The head is 63 (62+), triggering the elderly-family deduction — $525/year. Combined deductions = $1,005/year. Adjusted annual income = $16,800 − $1,005 = $15,795; adjusted monthly = $1,316.25. TTP = max(30% × $1,316.25 = $394.875, 10% × $1,400 = $140, $25) = $395 (rounded). HAP = $870 − $395 = $475/month → **$5,700/year**. A naive implementation that only recognizes under-18 dependents, or that only allows one deduction category per household, would compute a lower HAP than this.

---

### Scenario 22: Foster Child Correctly Excluded from the Dependent Deduction in Harris County

**What we're checking**: The dependent deduction must exclude foster children — MFB's `relationship` field has a distinct `fosterChild` value specifically so the calculator can tell them apart from a household's own children, but no prior scenario actually included one to confirm the exclusion works.

**Expected**: Eligible, $11,556/year

**Steps**:
- **Location**: Enter ZIP code `77002`, Select county `Harris`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `March 1991` (age 35), Relationship: Head of Household, Has income: Yes, Employment income: `$1,200` per month, No current Section 8/HCV assistance
- **Person 2**: Birth month/year: `June 2016` (age 10), Relationship: Foster Child, Has income: No

**Why this matters**: Annual income $14,400 is well below Harris County's 2-person VLI of **$41,600 (FY2026, independently verified)**. Houston isn't a mandatory-SAFMR metro, so payment standard uses the county-level FMR: 1BR = $1,323/month (independently verified — this cell of the table had never been exercised by a scenario before). The foster child does **not** count as a dependent, so the deduction is $0 — adjusted annual income equals gross, $14,400; adjusted monthly = $1,200. TTP = max(30% × $1,200 = $360, 10% × $1,200 = $120, $25) = $360. HAP = $1,323 − $360 = $963/month → **$11,556/year**. A naive implementation that counts every child-type relationship as a dependent — including `fosterChild` — would incorrectly compute a $480/year larger deduction and a higher HAP than this.

---

### Scenario 23: Working Teenager's Wages Correctly Excluded from Countable Income in El Paso County

**What we're checking**: 24 CFR 5.609(b)(3) excludes the *earned* income of a household member under 18 entirely — their unearned income (SS, child support) would still count, but wages don't. This is a different, previously-untested branch of the income calculation from the dependent deduction: it's about what counts as *gross income* in the first place, not about the per-dependent deduction. No prior scenario has a child with any income at all.

**Expected**: Eligible, $8,700/year

**Steps**:
- **Location**: Enter ZIP code `79901`, Select county `El Paso`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `March 1988` (age 38), Relationship: Head of Household, Has income: Yes, Employment income: `$1,000` per month, No current Section 8/HCV assistance
- **Person 2**: Birth month/year: `June 2010` (age 16), Relationship: Child, Has income: Yes, Employment income: `$400` per month

**Why this matters**: Only Person 1's income counts toward gross income — Person 2's $400/month wages are excluded entirely because they're a minor's *earned* income (24 CFR 5.609(b)(3)). Correct gross annual income = $1,000 × 12 = $12,000, well below El Paso County's 2-person VLI of **$33,500 (FY2026, independently verified)**. Person 2 still counts as a dependent for the $480/year deduction — that's a separate rule from whether their income counts. Adjusted annual income = $12,000 − $480 = $11,520; adjusted monthly = $960. TTP = max(30% × $960 = $288, 10% × $1,000 = $100, $25) = $288. El Paso's 1BR FMR is $1,013/month (independently verified). HAP = $1,013 − $288 = $725/month → **$8,700/year**. A naive implementation that includes the teenager's wages in gross income would compute $16,800/year gross instead of $12,000, and a materially lower HAP as a result — a concrete, detectable failure mode this scenario is designed to catch.

---

### Scenario 24: Foster Child's Unearned Income Correctly Excluded in Harris County

**What we're checking**: 24 CFR 5.609(b)(8) excludes *all* income of a foster child — earned or unearned — which is broader than the under-18 exclusion tested in Scenario 23 (that one only excludes a regular minor's *earned* income; their unearned income, like Social Security, would still count). Giving the foster child unearned income specifically isolates this broader rule from the narrower one.

**Expected**: Eligible, $11,556/year

**Steps**:
- **Location**: Enter ZIP code `77002`, Select county `Harris`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `March 1991` (age 35), Relationship: Head of Household, Has income: Yes, Employment income: `$1,200` per month, No current Section 8/HCV assistance
- **Person 2**: Birth month/year: `June 2016` (age 10), Relationship: Foster Child, Has income: Yes, Income type: Social Security, Amount: `$200` per month

**Why this matters**: This scenario is identical to Scenario 22 except the foster child now has $200/month in Social Security income — and the expected result is deliberately **unchanged** from Scenario 22 ($11,556/year), because that income must be excluded entirely. If the foster child's income were wrongly included, gross annual income would be $16,800 instead of $14,400, adjusted monthly would rise to $1,400, TTP would rise to $420 (30% of $1,400), and HAP would drop to $903/month = $10,836/year — a $720/year detectable shortfall versus the correct value. The unchanged expected value, next to Scenario 22, is the point: it proves adding income to a foster child doesn't affect the result, the way it would for any other household member.
