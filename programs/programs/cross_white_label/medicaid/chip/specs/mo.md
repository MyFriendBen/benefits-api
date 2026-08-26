# Implement CHIP (MO) Program

## Program Details

- **Program**: MO HealthNet for Kids (CHIP) — premium CHIP 73/74/75
- **State**: Missouri
- **Program key**: mo_chip
- **Policy year**: 2026
- **Calculator type**: PE calculator (elig + value varies)
- **White Label**: mo
- **Scope**: covers premium CHIP groups 73/74/75 only (income above the applicable premium-CHIP lower routing boundary, at or below 305% FPL). Children below that floor are out of scope for this calculator and route through Missouri's non-premium child-coverage pathways (MHK, CHIP 4M as applicable) — see Eligibility Criteria, Criterion 2.

## Eligibility Criteria

1. **Child must be under age 19**
   - Screener fields:
     - `birth_year (HouseholdMember)`
     - `birth_month (HouseholdMember)`
   - Source: Mo. Rev. Stat. § 208.631.2: '"children" are persons up to nineteen years of age'; DSS Manual § 1840.010.10 ("Uninsured"): 'Under 19'

2. **Child's MAGI household income must fall between the age-based premium-CHIP lower routing boundary and the CHIP ceiling** (see note for both figures)
   - Screener fields:
     - `household_size`
     - `income (all IncomeStream fields)`
   - **Note — this is a PE-backed calculator: PE's live `is_chip_eligible_child` output is the actual runtime determinant of both the lower routing boundary and the ceiling.** Missouri's published Appendix A monthly-dollar table (below) is the policy reference this spec's expected scenario outcomes are validated against — it states the *policy-correct* boundary, which is what PE's own parameter is intended to implement, not a separate MFB-side recomputation. The 148%/196%/300% nominal figures plus the 5% disregard describe the *policy concept* (effective 153%/201%/305%); Appendix A's monthly maximums already have the disregard built in, so those dollar figures — not a recomputed FPL% — are the policy-correct standard. Appendix A's cycle runs 2026-04-01–2027-03-31 (a separate schedule from Appendix E's premium table below, which turns over 2026-07-01). **PE blocker resolved**: PE previously diverged from Appendix A at three exact-dollar boundaries (Scenarios 3, 4, 15a); PolicyEngine's fix (PR #9297) is confirmed live and MFB's production PE version pin has been updated accordingly — see Acceptance Criteria.

     | Household size | Premium-CHIP lower routing boundary, ages 1–18 (148% label, "CHIP 4M" row) | Premium-CHIP lower routing boundary, under age 1 (196% label, "MPW & MHK under 1" row) | CHIP ceiling (300% label, "SMHB & CHIP 75" row) |
     |---|---|---|---|
     | 1 | $2,035/month | $2,674/month | $4,057/month |
     | 2 | $2,760/month | $3,625/month | $5,501/month |
     | 3 | **$3,484/month** | **$4,577/month** | **$6,944/month** |
     | 4 | $4,208/month | $5,528/month | **$8,388/month** |
     | 5 | $4,932/month | $6,479/month | $9,832/month |
     | 6 | $5,656/month | $7,431/month | $11,275/month |
     | 7 | $6,381/month | $8,382/month | $12,719/month |
     | 8 | $7,105/month | $9,334/month | $14,163/month |

     These are the exact dollar boundaries this spec's scenarios are built against for household sizes 1–8 (the sizes this calculator supports — see Benefit Value's scope note); the bolded HH3/HH4 values are exercised by Scenarios 3–6 and 15a/15b. This is the complete policy-correct reference for household sizes 1–8, including the ceiling column — the standard PE's live `is_chip_eligible_child` output is expected to match at runtime (see Criterion 2's note above — the three exact boundaries where it previously didn't are now confirmed fixed). For household sizes 9+ (out of scope for this calculator's UI, but still relevant if the UI cap ever changes), implementation must pull the corresponding row directly from the current Appendix A table rather than deriving a dollar figure from the nominal FPL percentage — Appendix A's own dollar figures do not reduce to a clean multiplication of the current-year FPL base: the published values above do not match a raw 148%/196%/300% × current FPL calculation. **Note**: a child at or below the applicable boundary is outside premium CHIP 73/74/75's scope and routes to Missouri's non-premium child-coverage pathways (MHK, CHIP 4M) — this routing decision is a scope boundary, not itself a finding that the child is Medicaid-eligible (CHIP 4M covers some children in this band who are not Medicaid-eligible).
   - Source: Mo. Rev. Stat. § 208.631.1 (150-300% FPL eligibility range); DSS Manual § 1805-030-20-20-05 (5% disregard); DSS Manual MAGI Appendix A (current monthly-dollar maximums, effective 2026-04-01–2027-03-31, disregard already incorporated — the binding source for this criterion's implementation)
   - **Classification: partial, not full — committed data-gap approximation.** Treats the screener's `household_size` and summed income as the MAGI-household test directly, but Missouri actually constructs a separate MAGI household per applicant based on tax-filing/dependency and non-filer rules (DSS § 1805.030.10) — siblings on one application can have different household sizes for their own determinations. This is a committed, accepted approximation for this calculator.
   - **Scope**: this calculator covers premium CHIP groups 73/74/75 only. Children who do not clear the applicable premium-CHIP lower boundary are outside this calculator's scope and are routed through Missouri's non-premium child-coverage pathways, including MHK and CHIP 4M as applicable.

3. **Child must not be Medicaid-eligible via another MO HealthNet pathway** — potential (undetermined) non-MAGI Medicaid eligibility triggers referral/coordination, not automatic CHIP denial
   - **Classification: partial.** Directly evaluates current Medicaid enrollment through the screener's `medicaid` flag; potential eligibility through other Medicaid pathways is a documented data gap and is not evaluated.
   - Screener fields: `medicaid` (enrollment flag), `birth_year`/`birth_month`, `household_size`, `income (all IncomeStream fields)`, `insurance`
   - **Legal basis** (42 CFR § 457.350; Mo. Rev. Stat. § 208.631.2): a child eligible for MO HealthNet isn't "uninsured" for CHIP purposes — this is an eligibility test, not an enrollment checkbox. **Found eligible** (subsection d) is dispositive. **Potentially eligible** on a non-MAGI basis (subsection e) only triggers referral, and (e)(4) requires later CHIP disenrollment if Medicaid confirms eligibility.
   - **What's computed**: the `medicaid` enrollment flag maps into PE's `receives_medicaid` input, and PE's own `is_chip_eligible_child` computation excludes the child — an MFB→PE input mapping, not a separate MFB-side exclusion. **Confirmed by live PE evidence** (Scenario 11): PE correctly returns `is_chip_eligible_child=False` when `receives_medicaid=True`. Income at or below criterion 2's routing boundary (≤201% under age 1, ≤153% ages 1-18) is already routed outside this premium-CHIP calculator under criterion 2 — that routing decision is not treated here as an independent finding that the child is Medicaid-eligible. `private`/`employer` insurance selections do **not** gate (see below). (Distinct from criterion 5's *unenrolled* ESI-access gap.)
   - **Everything else — not evaluable, inclusive default (screener can't screen for it), no denial per § 457.350(e):**

     | | Item | Why not screenable | Committed handling |
     |---|---|---|---|
     | ⚠️ | Other Medicaid pathways (disability, foster-care, adoption-assistance, HCBS/waiver) | No pathway-specific status collected; `disabled` flag ≠ Medicaid-pathway eligibility | Don't gate; disclose possible later referral/disenrollment (§ 457.350(e)(4)) in description |
     | ⚠️ | Geographic-access exception (42 CFR § 457.310(b)(2)(ii)) | `insurance` can't represent access adequacy | Not gated |
     | ⚠️ | Comprehensive vs. limited-benefit coverage: 3 "still uninsured" exceptions (DSS § 1840.010.10 — Caring Foundation coverage, HIPP-paid coverage, exhausted plan maximums) and limited-benefit coverage (accident-only, fixed-indemnity, short-term, workers'-comp, auto med-pay, healthcare-sharing-ministry) | `insurance`'s `private`/`employer` values can't distinguish any of these from genuine comprehensive coverage | Not gated — see "Net committed behavior" below |
     | | MHDC spend-down (not yet met for the month ⇒ not equivalently "enrolled," DSS § 1840.010.10) | No spend-down/non-spend-down distinction today | Not gated |

   - **Net committed behavior**: `private`/`employer` selections do **not** automatically exclude the child. The screener's `insurance` field cannot distinguish genuinely comprehensive, disqualifying coverage from Missouri's recognized exceptions above — that is an unscreenable eligibility distinction, not merely an inconvenient ambiguity, so it follows MFB's standard inclusive-default convention rather than an exception to it. **Committed handling**: a `private`/`employer` selection does not, by itself, mark the child ineligible; CHIP stays visible, and the program description explains that comprehensive coverage may make a child ineligible while limited coverage may not — Missouri verifies the actual coverage type at application. No new screener field is required. **No core scenario tests this distinction**: it's an unmodelable data gap with one committed inclusive handling rule (above) — per the scenario-coverage rules, a true data gap with committed inclusive handling doesn't require dedicated scenario coverage, so no `private`/`employer` scenario is kept in the core spec scenario set.
   - Source: Mo. Rev. Stat. § 208.631.2; DSS Manual § 1840.010.10; MAGI MO HealthNet Program Descriptions (4/2026); 42 CFR § 457.350
   - MAGI household-composition nuances (non-filer rules, tax-dependency edge cases) are covered under criterion 2, not repeated here.

4. **Missouri state residency required**
   - Screener fields:
     - `zipcode`
     - `county`
   - Source: Mo. Rev. Stat. § 208.631.2: uninsured children must '[be] residents of the state of Missouri'; DSS Manual § 1840.010.10 applies to Missouri residents
   - Missouri accepts self-attestation of residency, and a student attending college in Missouri satisfies this rule if they intend to remain in Missouri while in school (DSS § 1805.005.00). Niche case, low prevalence for a CHIP-age population (under 19); not worth a separate scenario or screener change.

5. **Premium-group child (income above 150% FPL) must not have access to affordable employer, group-membership, or private health insurance (unenrolled)** ⚠️ *data gap*
   - Note: DSS § 1840.010.15 — *"Access to affordable insurance available through employment, a group membership, or from a private company causes ineligibility"* (group membership incl. union/professional/trade associations) for premium groups CHIP 73-75. Missouri's own affordability test, not an ACA "minimum value" standard.
   - **Two distinct affordability tests:**

     | | 5a. Employer/group (§ 1840.010.15.05, § .10) | 5b. Private/FFM marketplace (§ 1840.010.15.08, § .15) |
     |---|---|---|
     | Affordability standard | **Fixed $ standard**, not the family's actual income/size — *"the affordability standard is based upon a monthly premium amount of 3% of 150% of the FPL for a household of three"* (CHIP73; 4% of 185% for CHIP74, 5% of 225% for CHIP75, § 1840.010.15.05) | *"Compare the CHIP Premium to the FFM Highest Gold Premium. If it is more than the CHIP premium, no affordable insurance is available"* (§ 1840.010.15.08) |
     | Disqualifies only if all hold | (1) affordable, (2) meets MO's health-insurance definition, (3) *"the insurance covers all of a child's pre-existing conditions"* (§ 1840.010.15.10) — **no** NEMT/comprehensive-services condition | (1) affordable, (2) *"the insurance covers all MO HealthNet services (except non-emergency medical transportation)"* (§ 1840.010.15.15), (3) covers pre-existing conditions |
     | Exception | **State employees**: affordable "regardless of actual cost" (same rule as criterion 7) | — |

   - **Also not "available"** if: (a) child doesn't yet meet workplace eligibility terms (hours/tenure); (b) plan excludes the pre-existing condition (RSMo § 208.640/SB 577 2007); (c) benefits exhausted.
   - **Not screenable** — `insurance` captures none of these facts (unlike criterion 3, this is unenrolled *access*, not current coverage). Per 'default to inclusive': not gated on; surfaced as a program-description note.
   - **Special-needs exception (§ 1840.010.15.08)**: undefined, currently moot — no effect since criterion 5 already defaults inclusive.
   - **IHS access is not disqualifying**: 42 CFR § 457.320(b)(5) bars excluding an AI/AN child from CHIP solely for IHS access. Not screenable, and moot regardless since criterion 5's inclusive default never gates on unenrolled-access facts.
   - Source: DSS Manual §§ 1840.010.15, .15.05, .15.08, .15.10, .15.15; Mo. Rev. Stat. §§ 208.631.2, 208.640/SB 577 (2007); 42 CFR § 457.320(b)(5)
   - **Test scenarios**: none — the screener doesn't collect the facts needed to resolve this gap (same as criterion 3's `private`/`employer` handling).

6. **Institutional-status exclusions — two branches** ⚠️ *data gap*
   - 42 CFR § 457.310(c)(2): excludes (i) inmates of a public institution, and (ii) IMD patients "at the time of initial application or any redetermination" — that time qualifier grammatically attaches to (ii) only; (i) has no time limiter.
   - **6a. New applicant, public-institution inmate** (§ 457.310(c)(2)(i)): excluded at new application.
   - **6b. IMD patient** (§ 457.310(c)(2)(ii)): excluded at initial application *or* any redetermination.
   - **Committed handling**: neither is screenable (no institutional-status field) — inclusive data gap both ways. Not surfaced in the program description (low-prevalence edge case for an under-19 population; contrast criteria 5/7, which are surfaced).
   - Source: 42 CFR § 457.310(c)(2)

- **Out of scope**: pregnant minors under 19 route to MHK/Medicaid/pregnancy coverage before Show-Me Healthy Babies — program-precedence between sibling MFB programs (SMHB itself out of scope here and in MFB-1261), not a CHIP criterion.

7. **No access to a state health-benefits plan via a family member's qualifying public-agency employment (MO or another state)** ⚠️ *data gap*
   - Note: DSS § 1840.010.15.12 — *"Health insurance available to a state employee through a state agency is considered affordable regardless of cost"* (Social Security Act § 2110(b)(2)(B)). Doesn't apply to temp/part-time/intern/contract employees (no plan access); extends to other states' public agencies too. Not screenable; per 'default to inclusive,' not gated on — noted in program description.
   - Source: DSS § 1840.010.15.12; 42 CFR § 457.310(c)

8. **U.S. citizenship or qualified immigration status required — changes federally on 2026-10-01, confirmed by Missouri DSS** ⚠️ *configurable — not a data gap*
   - Note: Federal CHIP law requires citizenship or qualified-alien status. Missouri is not among the states electing the CHIPRA § 214 (ICHIA) option (CMS list, updated 2026-04-02), so the standard 5-year bar applies with no under-5 expansion.
   - **Status by period:**

     | Period | Categories |
     |---|---|
     | Current, no-wait (through 2026-09-30) | AI born in Canada, Amerasians, asylees, Cuban/Haitian entrants, withholding-of-removal grantees, Iraqi/Afghan SIVs, refugees, trafficking victims (§ 1805.020.10.10.05); COFA migrants since 2024-03-09 (§ 1805.020.10.20) |
     | Current, 5-year bar | LPRs, parolees ≥1yr, conditional entrants (pre-4/1/1980), battered immigrants (P.L. 104-208) — military/veteran/spouse/dependent exceptions apply (§ 1805.020.10.10.10) |
     | From 2026-10-01 (CMS SHO #26-001, P.L. 119-21 § 71109; confirmed by MO DSS's H.R. 1 page) | Only 4 groups keep federal funding: citizens/nationals, LPRs (bar unchanged), Cuban/Haitian entrants, COFA migrants. Refugees, asylees, and other humanitarian groups lose the federal funding basis; MO DSS has already notified affected households |

   - **Committed MFB handling**: `legal_status_required` keeps its current 5 values (`citizen`, `refugee`, `gc_5plus`, `gc_5less`, `otherWithWorkPermission`) through 2026-09-30. **Effective 2026-10-01, remove `refugee`** — the only one of MFB's 6 status values that maps to a group federal CHIP funding excludes starting that date. Single config-file change, dated to Missouri's own effective date. `otherWithWorkPermission` remains a coarse inclusive bucket by design, since MFB's schema can't separately distinguish the statuses within it.
   - **Current handling (through 2026-09-30)**: only `non_citizen` excluded. `gc_5less` stays inclusive because the 5-year bar has undetectable exceptions (military/veteran/spouse/dependent) — excluding it risks hiding eligible households. Inclusion ≠ confirmed CHIP-qualified status; the real determination happens at application.
   - Source: 42 CFR § 457.320(b)(6), (c), (d); 8 U.S.C. § 1613 (5-year bar); DSS Manual §§ 1805.020.00, .10.10.05, .10.10.10, .10.20; [CMS's CHIPRA § 214 election list](https://www.medicaid.gov/medicaid/enrollment-strategies/medicaid-and-chip-coverage-of-lawfully-residing-children-pregnant-women) (updated 2026-04-02, Missouri not listed); CMS SHO #26-001 implementing P.L. 119-21 § 71109; [MO DSS H.R. 1 Participant Resources](https://mydss.mo.gov/hr1/participant-resources)

## Priority Criteria

None.

## Benefit Value

**Formula**: `annual value = max(1, sum(PE chip_gross for each CHIP-eligible child) − (PE mo_chip_premium × 12))`. Both `chip_gross` and `mo_chip_premium` are read live from PE's own output — MFB does not copy PE's gross figure into an MFB-side constant, and does not run its own Appendix E premium lookup alongside PE. Premium is charged once per household, not per child.

**Gross per-child value: PE's live `chip_gross` output, ≈$2,911.85/year per eligible child** — a FY2024 spending proxy (per child ever enrolled in MO's separate CHIP program), not a precise per-child benefit figure. Read directly from PE's own `per_capita_chip_gross` calculation, not an MFB-side constant. Derivation, for provenance only:

| | Amount | Source |
|---|---|---|
| Separate-CHIP spending (net of cost-sharing) | $303,540,996 | PE `chip/spending/separate_chip/total.yaml` (exact input). MACPAC corroboration: [Exhibit 33](https://www.macpac.gov/wp-content/uploads/2026/01/EXHIBIT-33.-CHIP-Spending-by-State-FY-2024.pdf) reports Missouri's relevant separate-CHIP/pregnancy spending as **$303.5M**, rounded — the exhibit does not itself publish the exact-dollar figure |
| + Cost-sharing offsets | $12,674,381 | PE `chip/cost_sharing_offsets/separate_chip.yaml` (cites CMS MBES/CBES; no public browsable table for this exact line) |
| ÷ Enrollment (children ever enrolled, even 1 month) | 108,596 | PE `chip/enrollment/separate_chip.yaml` (exact input). MACPAC corroboration: [Exhibit 32](https://www.macpac.gov/wp-content/uploads/2026/01/EXHIBIT-32.-Child-Enrollment-in-CHIP-and-Medicaid-by-State-FY-2024.pdf) reports Missouri's enrollment in thousands/rounded form, not this exact count |
| = Gross per-child | **$2,911.85** | Matches PE's `chip_gross` output ($2,911.851 unrounded) |

**Exact inputs** ($303,540,996 / $12,674,381 / 108,596) come from PE's own parameter data; MACPAC's exhibits corroborate the same spending/enrollment only at rounded precision ($303.5M; enrollment in thousands).

**Why it's a proxy**: MACPAC's $303.5M line is "Separate CHIP programs **and coverage of pregnant women**" (Missouri is 1 of 7 states using CHIP funds this way, per Exhibit 33 n.1) — not child-only spending. The 108,596 denominator counts enrollment events, not member-years/months. A numerator that includes pregnancy spending over an enrollment-event denominator isn't a precise per-child annual cost — treat it as an estimate. **Committed framing**: describe it as "PolicyEngine's FY2024 spending proxy per child ever enrolled," never as an exact per-child benefit value. PE's variable logic: `per_capita_chip_gross.py`, `chip_gross.py`, `per_capita_chip.py`, `chip.py` ([source](https://github.com/PolicyEngine/policyengine-us/tree/master/policyengine_us/variables/gov/hhs/chip/)).

Note: $303,540,996 ÷ 108,596 = $2,795.14 is PE's **net** per-capita figure (`chip`/`per_capita_chip`) — not what this spec uses. This spec reads PE's **gross** output (`chip_gross`, ≈$2,911.85) since the premium is subtracted separately below; reading the net figure and also subtracting the premium would double-count cost-sharing.

**Premium (once per household)**: income above 150% FPL owes a monthly premium in one of three tiers, per DSS Appendix E, IM-4(PRM) (07-26), **effective 2026-07-01** (the public `mydss.mo.gov` HTML chart is stale, still showing 2025-07-01 rates — the Appendix E PDF is the source of truth). At or below 150% FPL: no premium. This calculator reads the premium live from PE's `mo_chip_premium` output, not an MFB-side lookup — the table below is what PE's parameter is intended to implement and what this spec's scenario values are validated against.

| Family size | >150–185% FPL | >185–225% FPL | >225–300% FPL |
|---|---|---|---|
| 1 | $19/mo | $62/mo | $150/mo |
| 2 | $25/mo | $83/mo | $203/mo |
| 3 | $32/mo | $105/mo | $256/mo |
| 4 | $39/mo | $127/mo | $309/mo |
| 5 | $45/mo | $148/mo | $363/mo |
| 6 | $52/mo | $170/mo | $416/mo |
| 7 | $58/mo | $191/mo | $469/mo |
| 8 | $65/mo | $214/mo | $522/mo |
| 9 | $72/mo | $236/mo | $576/mo |
| 10 | $78/mo | $257/mo | $629/mo |
| 11 | $85/mo | $279/mo | $682/mo |
| 12 | $92/mo | $301/mo | $735/mo |

**Scope: sizes 1-8 only.** Sizes 9-12 are published but undefined for this calculator: eligibility criteria still apply at any size, but `benefits-calculator`'s `HouseholdSize.tsx` enforces a hard `.lte(8)`, so no household above 8 can be submitted through the real screener. Size 13+ has no published rate at all. Scenario 17 (size 8) is the largest case the test suite can exercise.

**Worked examples** (one eligible child): family of 1, tier 1: $2,911.85 − ($19×12=$228) = **$2,683.85**; tier 2: − ($62×12=$744) = **$2,167.85**; tier 3: − ($150×12=$1,800) = **$1,111.85**. The ≤150%-FPL no-premium band is empty in practice, since the premium-CHIP lower routing boundary (153%/201%) sits above the 150% non-premium line for both age groups. For multiple children: multiply gross by eligible-child count, subtract the single household premium once.

**Floor at $1, not $0** (Scenario 10): family size 3+ in the top tier makes premium×12 exceed $2,911.85, going negative — floor the net value at **$1**. Product/display convention only, not a Missouri rule (their chart has no concept of negative benefit). The floor is $1 rather than $0 because a $0 program is reported ineligible (`eligible = value > 0`) and then dropped again by the frontend's own `programValue(program) > 0` filter, so a $0 floor would hide CHIP from exactly the families this case describes — a child who is eligible and would get coverage, just with no net monetary value at this income and family size. $1 is a visibility sentinel, not an estimate of the benefit.

**MFB value methodology**: `max(1, sum(chip_gross for each eligible child) − mo_chip_premium × 12)`, where every term on the right is read live from PE's own output — `eligible_children` is the set of children **PE's own live `is_chip_eligible_child` output** marks eligible, `chip_gross` is PE's own per-eligible-child gross value, and `mo_chip_premium` is PE's own monthly household premium. PE is the actual runtime determination for eligibility, gross value, and premium alike — not an offline cross-check, and not a set of PE outputs copied into MFB-side constants or recomputed in parallel. Reading `chip_gross` (not `chip`/`per_capita_chip`, PE's net figure) avoids double-counting cost-sharing, since `mo_chip_premium` is subtracted separately. **Committed handling**: MFB sends PE the household facts it actually knows (age, income, household size, reported current Medicaid enrollment via `receives_medicaid`) and uses PE's live `is_chip_eligible_child`, `chip_gross`, and `mo_chip_premium` outputs as the determination, full stop — no MFB-side Appendix A/Appendix E recomputation runs in place of or alongside it, and no MFB override neutralizes a PE result MFB doesn't like. The three exact-dollar-boundary divergences (Scenarios 3, 4, 15a) are confirmed fixed and MFB's production PE version pin has been updated — see Acceptance Criteria.

**Data gap — AI/AN premium exemption** (value precision, not eligibility): 42 CFR § 457.535 prohibits states from imposing CHIP premiums/cost-sharing on AI/AN children (DSS § 1840.025.00). Not screenable — no tribal-membership field, and PE's `race` variable has no AI/AN category. **Handling**: compute the premium normally for everyone, and note the exemption in the program description so AI/AN families know to inquire.

**Annualization methodology — current-rate annualized, not a calendar-year historical blend.** Expected annual values are *the currently-effective monthly premium × 12* ("if this rate holds for a full year going forward"), not the household's actual blended total across a year that straddles Missouri's July 1 rate change. A prospective applicant has no single "calendar year" premium history — their 12-month window starts whenever they apply, under whatever rate is current then. This matches how MFB's other programs present "estimated annual value."

**Query-period methodology — `chip_gross` and `is_chip_eligible_child` are queried at the annual period; `mo_chip_premium` alone is queried at a current-month period and multiplied by 12.** `chip_gross` and eligibility reflect parameters that don't change mid-2026, so the annual period returns the correct figure directly. `mo_chip_premium` is the one output that changes mid-year (2026-07-01) — querying it at the annual period would blend the two halves' rates into a meaningless average, so it must be queried within the applicant's current half of 2026 and multiplied by 12. **Never query `chip_gross` at a monthly period**: a year-scoped variable queried monthly returns PE's pro-rated 1/12 share (confirmed: $242.65/month × 12 = $2,911.80, matching the annual figure) — summing it as if monthly-scoped, the way `mo_chip_premium` is handled, would understate every scenario's value ~12×.

## Acceptance Criteria

**Eligibility and PE integration**

[ ] Income-boundary (lower routing + ceiling) eligibility, gross value, and premium are all determined live by PE's `is_chip_eligible_child`/`chip_gross`/`mo_chip_premium` output — no MFB-side Appendix A/Appendix E recomputation runs instead of or alongside PE, and no MFB override neutralizes a PE result to force a match.
[ ] The `medicaid` enrollment field maps to PE's `receives_medicaid` input; PE's own eligibility output honors it and excludes the child (Scenario 11).
[ ] Coarse `private`/`employer` insurance selections do not gate eligibility — inclusive handling per criterion 3 (no dedicated core scenario; unmodelable data gap).
[ ] Immigration/legal-status visibility is driven entirely by `legal_status_required` config, with `refugee` removed effective 2026-10-01 per criterion 8.
[ ] Household sizes 1–8 are supported end-to-end through the current screener UI; sizes 9+ follow the same eligibility criteria but are out of scope for value-calculation testing until the UI cap changes (Scenario 17).

**Benefit value calculation**

[ ] Premium is read live from PE's `mo_chip_premium` output for household sizes 1–8 — no separate MFB-side lookup against Appendix E runs instead of or alongside it (Scenarios 18–21).
[ ] The top premium tier extends through criterion 2's Appendix A CHIP-ceiling dollar figure for each household size, not Appendix E's narrower printed top-row bound — this falls out automatically from reading PE's live `mo_chip_premium` output (Scenario 2).
[ ] `chip_gross`/`is_chip_eligible_child` are queried at the annual period; `mo_chip_premium` alone is queried at a current-month period and multiplied by 12 — never the same period for both (querying `chip_gross` monthly would understate every scenario's value ~12×; see Benefit Value's "Query-period methodology").
[ ] The household premium is subtracted exactly once per household, regardless of the number of CHIP-eligible children (Scenarios 12, 13, 17).
[ ] Per-child gross value is summed unrounded across all eligible children before the single final rounding to cents (Scenario 17).
[ ] Net value floors at $1 — never $0 and never negative — so a premium-exceeds-value household keeps a visible program rather than being filtered out by `eligible = value > 0` (Scenario 10).
[ ] Value is presented on an annual cadence (`annual value` / `estimated_annual`), not monthly.

**Test coverage**

[ ] All 20 scenarios in the Test Scenarios section return their committed eligibility/value results.
[ ] The live `mo_chip` calculator runs against a PE model version whose `mo_chip_premium` output matches Appendix E's current (2026-07-01) rate table across all 12 family sizes and 3 tiers.

**PE blocker resolved.** A live rerun against PolicyEngine's private API (2026-08-19, post-release) against PE's `frontier` channel (model `1.815.1`, includes [PR #9258](https://github.com/PolicyEngine/policyengine-us/pull/9258) and [PR #9297](https://github.com/PolicyEngine/policyengine-us/pull/9297)) confirmed **all 20 scenarios match their committed expected eligibility and value** — including Scenarios 3, 4, and 15a's exact-dollar boundaries and every premium-bearing scenario, verified against full-precision `chip_gross`/`mo_chip_premium` output (e.g. Scenario 17: `242.65425/mo × 12 × 6 children − $214×12` rounds to $14,903.11, matching exactly). MFB's global `PolicyEngineConfig.policyengine_version` pin (`benefits-api/configuration/models.py`) has since been updated to this exact version, so production requests now resolve to the verified model. No PE-side blocker remains for this spec.

Not independently re-confirmed by this review: the live production DB value of `PolicyEngineConfig.policyengine_version` (this session has no production DB access) — the pin was reported by engineering, not read directly. A rerun against the live production endpoint (not `frontier`) after deploy is the standard sanity check, but is not treated here as a condition of this spec's readiness.
- If a rerun against the actual production version still diverges on any scenario, treat it as a new, distinct issue — don't reopen the other 19 or add an MFB-side override to compensate.

## Test Scenarios

**Fixed evaluation date: July 20, 2026.** Every scenario's age (computed from `birth_month`/`birth_year`) and eligibility result below assumes a screening date of July 20, 2026. Ages, and any result that depends on age, must be recomputed if evaluated at a different date — do not assume these results are stable indefinitely.

Two notes on the age-sensitive scenarios, since CHIP's under-19 gate is an age *ceiling* and any upward shift in a child's computed age can push them out of eligibility:

- **Scenario 14 is date-stable as written.** Its child's birth month was chosen so the scenario reads 18 for every screening month of 2026 and under either age semantics described below. It previously used `August 2007` ("turns 19 next month"), which read 18 only through July 2026 and returned Not eligible from August onward.
- **Scenario 2 is not date-stable.** Its child's `December 2007` birth month reads 18 on a screening-date age, but 19 on a period-year age (`period year − birth_year`). If the shared `AgeDependency` moves to period-year age (MFB-1726), that child ages out and Scenario 2 stops exercising the 5% disregard at all — it would return Not eligible for a reason that has nothing to do with the disregard. Restating the child's birth month as any 2008 month keeps both the income calibration and the disregard test intact under either semantics. Note that the spec-scenario tests pass a literal `age`, not a birth date, so they stay green either way and will not catch this.

### Scenario 1: Clearly Eligible Child – Low-Income Family of 3, ~183% FPL
**What we're checking**: Basic happy-path eligibility: child under 19, household income in the first premium tier (150–185% FPL), Missouri resident, uninsured, no existing Medicaid, proper relationship
**Expected**: Eligible, **$2,527.85/year**

**Steps**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `3`
- **Person 1**: Birth month/year: `March 1985` (age 41), Relationship: `headOfHousehold`, Has income: Yes, Employment income: `$4,167` per month (~$50,000/year), Insurance: `none`, Citizenship: US Citizen
- **Person 2**: Birth month/year: `June 1987` (age 39), Relationship: `spouse`, Has income: No, Insurance: `none`, Citizenship: US Citizen
- **Person 3**: Birth month/year: `September 2018` (age 7), Relationship: `child`, Has income: No, Insurance: `none`, Citizenship: US Citizen

**Why this matters**: ~$50,000/year for a household of 3 (≈183% FPL) is above the ages-1-18 lower routing boundary (153%) and the non-premium band (≤150%), landing cleanly in the first premium tier ($32/mo). Net value = $2,911.85 gross − ($32 × 12 = $384) = **$2,527.85/year**. Confirms basic CHIP eligibility with a real committed value.
- **Source**: DSS Manual MAGI Appendix A (HH3 ages-1-18 lower boundary, $3,484/mo) and Appendix E, IM-4(PRM) (07-26) (HH3, >150–185% band, $32/mo).

---

### Scenario 2: Income Between 300–305% FPL – Eligible via the 5% FPL Disregard, Family of 2
**What we're checking**: Household income above the statutory 300% FPL figure but within the 5% FPL disregard band (up to 305%) is still eligible — validates that the disregard is actually applied, not just the bare 300% cutoff
**Expected**: Eligible, **$475.85/year**

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `2`
- **Person 1**: Relationship: `headOfHousehold`, Birth month/year: `January 1986` (age 40), Has income: Yes, Employment income: `$5,458.33` per month (~$65,500/year), No current health insurance, Citizenship: US Citizen
- **Person 2**: Relationship: `child`, Birth month/year: `December 2007` (age 18), Has income: No, No current health insurance, No current Medicaid coverage, Citizenship: US Citizen

**Why this matters**: At $65,500/year, this household clears the bare nominal 300% FPL figure but is still within the 5%-disregard-inclusive band (305%) — a naive "income ≤ 300% FPL" implementation would wrongly reject it. Falls in the top premium tier for family size 2 ($203/mo). Net value = $2,911.85 − ($203 × 12 = $2,436) = **$475.85/year**. PE's live output correctly applies the disregard and admits this household — like Scenarios 3, 4, and 15a (Criterion 2's now-resolved PE blocker), this scenario now matches on the current production PE version.
- **Source**: DSS Manual § 1805-030-20-20-05 (5% FPL disregard applied to the 300% CHIP ceiling) and DSS Manual MAGI Appendix A (HH2 ceiling, $5,501/mo).

---

### Scenario 3: Newborn, Income Exactly at the Published Infant Medicaid Ceiling – Should Be Ineligible for CHIP
**What we're checking**: Income exactly equal to Missouri's published Appendix A infant (under-age-1) ceiling for household size 3 must resolve to Medicaid-eligible, not CHIP-eligible (the boundary is inclusive toward Medicaid — `≤`, not `<`). Mirror case to Scenario 15a's exact-boundary test, but for the infant-specific ceiling.
**Expected**: Not eligible (still Medicaid-eligible as an infant, not CHIP)

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `3`
- **Person 1**: Birth month/year: `March 1991` (age 35), Relationship: `headOfHousehold`, Has income: `Yes`, Employment income entered at **monthly frequency**, `$4,577.00`/month exactly, Insurance: None, Citizenship: US Citizen
- **Person 2**: Birth month/year: `September 1993` (age 32), Relationship: `spouse`, Has income: No, Insurance: None, Citizenship: US Citizen
- **Person 3**: Birth month/year: `April 2026` (age 0, newborn), Has income: No, Insurance: None, Not currently enrolled in Medicaid (`medicaid` field = No), Citizenship: US Citizen

**Why this matters**: Missouri's published Appendix A table lists $4,577.00/month as the infant (under-age-1) effective maximum for a household of 3 — the policy-correct boundary per Criterion 2. At exactly $4,577.00/month, the newborn sits at this boundary and should resolve to Medicaid-eligible (and thus CHIP-ineligible). This was one of the three exact-dollar-boundary scenarios affected by the now-resolved PE blocker (see Acceptance Criteria) — confirmed fixed on a live rerun, and MFB's production PE version pin has been updated accordingly.
- **Source**: DSS Manual MAGI Appendix A (HH3 under-age-1 row, $4,577.00/mo) and 42 CFR § 457.350(d) (Medicaid-eligible child is dispositive, CHIP-ineligible).

---

### Scenario 4: Income Exactly at the CHIP Ceiling – Family of 4, Two Children
**What we're checking**: Income exactly at the true (disregard-inclusive) ceiling is still eligible, confirming the inclusive boundary at Missouri's published Appendix A ceiling for household size 4, not the bare 300% statutory figure. This is also the calculator's canonical PE-validation case (see below).
**Expected**: Eligible, **$2,115.70/year** — the policy-correct expected result per Missouri's published Appendix A ceiling. See "Why this matters" below — this boundary was a named PE blocker, now confirmed resolved.

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `4`
- **Person 1**: Birth month/year: `March 1988` (age 38), Relationship: `headOfHousehold`, Citizenship: `US Citizen`, Has income: `Yes`, Employment income entered at **monthly frequency**, `$8,388.00`/month exactly, Has health insurance: `None`
- **Person 2**: Birth month/year: `September 1990` (age 35), Relationship: `spouse`, Citizenship: `US Citizen`, Has income: `No`, Has health insurance: `None`
- **Person 3**: Birth month/year: `January 2015` (age 11), Relationship: `child`, Citizenship: `US Citizen`, Has income: `No`, Has health insurance: `No`, Currently on Medicaid: `No`
- **Person 4**: Birth month/year: `June 2019` (age 7), Relationship: `child`, Citizenship: `US Citizen`, Has income: `No`, Has health insurance: `No`, Currently on Medicaid: `No`

**Why this matters**: Missouri's current Appendix A table lists $8,388.00/month as the CHIP upper effective maximum for a household of 4 — the policy-correct boundary per criterion 2, not a raw 305%-of-FPL calculation. Income exactly at $8,388.00/month should still qualify, confirming the inclusive boundary sits at the published Appendix A ceiling, not the bare statutory 300% figure. Falls in the top premium tier for family size 4 ($309/mo). Two eligible children: net value = (2 × $2,911.85) − ($309 × 12 = $3,708) = **$2,115.70/year** — the policy-correct expected result. One of the three exact-dollar-boundary scenarios (with Scenario 3 and Scenario 15a) affected by the now-resolved PE blocker in Acceptance Criteria — confirmed matching on a live rerun after PolicyEngine's fix (PR #9297) and MFB's production version pin update.
- **Source**: DSS Manual MAGI Appendix A (HH4 ceiling, $8,388.00/mo) and Appendix E, IM-4(PRM) (07-26) (HH4, >225–300% band, $309/mo).

---

### Scenario 5: Income One Dollar Above the CHIP Ceiling – Family of 3, Child Should Be Ineligible
**What we're checking**: Verifies that a child in a household with income exceeding Missouri's published Appendix A CHIP ceiling for household size 3 is correctly denied CHIP eligibility. **Amended for implementation:** the screener sends PolicyEngine `int(annual income)`, so a one-cent-per-month step — twelve cents a year — is truncated away and this household arrives identical to its boundary twin. The input below steps one dollar per month instead, the smallest step that survives the truncation; the side of the boundary, the premium tier and the expected value are unchanged.
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `3`
- **Person 1**: Birth month/year: `March 1990` (age 36), Relationship: `headOfHousehold`, Citizenship: `US Citizen`, Has income: `Yes`, Employment income entered at **monthly frequency**, `$6,945.00`/month exactly, Health insurance: `None`
- **Person 2**: Birth month/year: `September 1992` (age 33), Relationship: `spouse`, Citizenship: `US Citizen`, Has income: `No`, Health insurance: `None`
- **Person 3**: Birth month/year: `January 2018` (age 8), Relationship: `child`, Citizenship: `US Citizen`, Has income: `No`, Health insurance: `None`, Not currently receiving Medicaid
- **Current Benefits**: Select no current benefits

**Why this matters**: $6,944.00/month is Missouri's published Appendix A ceiling for a household of 3; one dollar above it must be denied, confirming PE enforces the exact published boundary rather than a recomputed FPL percentage. PE's live output correctly denies this household — no divergence here (Scenarios 3, 4, and 15a's divergence, per Criterion 2's PE blocker, is now resolved too).
- **Source**: DSS Manual MAGI Appendix A (HH3 ceiling, $6,944.00/mo).

---

### Scenario 6: Newborn, Income One Dollar Above the Published Infant Medicaid Ceiling – Genuine CHIP Case
**What we're checking**: Income immediately above that same infant boundary must flip to CHIP-eligible — the mirror case to Scenario 3, one dollar higher. **Amended for implementation:** the screener sends PolicyEngine `int(annual income)`, so a one-cent-per-month step — twelve cents a year — is truncated away and this household arrives identical to its boundary twin. The input below steps one dollar per month instead, the smallest step that survives the truncation; the side of the boundary, the premium tier and the expected value are unchanged. A newborn satisfies the 'under age 19' criterion, and clearing the infant-specific ceiling (higher than the ages-1-18 ceiling) makes this a genuine CHIP case rather than Medicaid.
**Expected**: Eligible, **$1,651.85/year**

**Steps**: Identical to Scenario 3 except Person 1's employment income is entered at **monthly frequency**, `$4,578.00`/month — one dollar above the $4,577.00 boundary.

**Why this matters**: At $4,578.00/month — one dollar above Missouri's published Appendix A infant ceiling for a household of 3 — this newborn sits just above the line, close enough that a boundary implementation error would misclassify them, but genuinely above the correct threshold, so the correct result is CHIP-eligible, not Medicaid. Falls in the 185–225% FPL premium tier for family size 3 ($105/mo). Net value = $2,911.85 − ($105 × 12 = $1,260) = **$1,651.85/year**.
- **Source**: DSS Manual MAGI Appendix A (HH3 under-age-1 row, $4,577.00/mo) and Appendix E, IM-4(PRM) (07-26) (HH3, >185–225% band, $105/mo).

---

### Scenario 7: Age 19 – Should NOT Be Eligible
**What we're checking**: Validates that a 19-year-old is correctly excluded from CHIP, since Missouri CHIP requires the child to be under age 19 (Mo. Rev. Stat. § 208.631.2)
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `March 1980` (age 46), Relationship: `headOfHousehold`, Has income: Yes, Employment income: `$3,000` per month (~$36,000/year), Insurance: `none`, Citizenship: US Citizen
- **Person 2**: Birth month/year: `January 2007` (age 19), Relationship: `child`, Has income: No, Insurance: `none`, Citizenship: US Citizen

**Why this matters**: Income ($36,000/year, ≈166% FPL) is otherwise fully within this calculator's scope, isolating age as the sole exclusion reason. The person has unambiguously already turned 19 (birth month well clear of the current month), so the correct result is no eligible children at all. Complements Scenario 6 (age 0, minimum eligible) by testing the upper boundary.
- **Source**: Mo. Rev. Stat. § 208.631.2 ("'children' are persons up to nineteen years of age").

---

### Scenario 9: Income Below the Premium-CHIP Lower Boundary — Outside This Premium CHIP Calculator
**What we're checking**: A child whose household income falls below this calculator's effective 153% FPL lower boundary is outside this premium CHIP 73-75 calculator's scope — verifies the calculator's lower scope boundary at 153% effective, not the wrong nominal 148% figure.
**Expected**: Not eligible — outside this premium CHIP calculator's scope.

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `3`
- **Person 1**: Birth month/year: `March 1990` (age 36), Relationship: `headOfHousehold`, Has income: Yes, Employment income: `$3,417` per month (~$41,000/year), Insurance: `none`, Citizenship: US Citizen
- **Person 2**: Birth month/year: `September 1992` (age 33), Relationship: `spouse`, Has income: No, Insurance: `none`, Citizenship: US Citizen
- **Person 3**: Birth month/year: `January 2016` (age 10), Relationship: `child`, Has income: No, Insurance: `none`, Not currently enrolled in Medicaid (`medicaid` field = No), Citizenship: US Citizen
- **Current Benefits**: Select no current benefits

**Why this matters**: $41,000/year sits above the nominal 148%-of-FPL figure (~$40,434) but below the correct Appendix A boundary ($41,808) — a calculator using the wrong nominal threshold would incorrectly admit this household, while the correct Appendix A boundary excludes them into Missouri's CHIP 4M non-premium group.
- **Source**: DSS Manual MAGI Appendix A (HH3 ages-1-18 lower boundary, $3,484.00/mo).

---

### Scenario 10: Single Child, Top Premium Tier – Net Value Floors at $1
**What we're checking**: When a single eligible child's household is in the top premium tier for a family size where premium × 12 exceeds the gross per-child value, the net value must floor at $1 rather than display negative or fall to $0 (which would filter the program out of the results entirely)
**Expected**: Eligible, **$1/year** (floored sentinel)

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `3`
- **Person 1**: Birth month/year: `March 1990` (age 36), Relationship: `headOfHousehold`, Has income: Yes, Employment income: `$5,833.33` per month (~$70,000/year), Insurance: `none`, Citizenship: US Citizen
- **Person 2**: Birth month/year: `September 1992` (age 33), Relationship: `spouse`, Has income: No, Insurance: `none`, Citizenship: US Citizen
- **Person 3**: Birth month/year: `January 2018` (age 8), Relationship: `child`, Has income: No, Insurance: `none`, Not currently receiving Medicaid or CHIP, Citizenship: US Citizen

**Why this matters**: 2026 FPL for a household of 3 is $27,320; $70,000/year is ≈256% FPL, landing in the top premium tier ($256/mo). Raw computation: $2,911.85 − ($256 × 12 = $3,072) = **−$160.15**, which must never be displayed to a user. The correct behavior is to floor at **$1/year** while the child remains eligible (still gets coverage, just no net monetary value at this income/family-size combination). $1 rather than $0 because `eligible = value > 0` would report a $0 program ineligible and the frontend's `programValue(program) > 0` filter would drop it again — flooring at $0 hides CHIP from precisely this household. This is the committed test for the Benefit Value section's floor rule.
- **Source**: DSS Manual Appendix E, IM-4(PRM) (07-26) (HH3, >225–300% band, $256/mo); the $1 floor itself is an MFB product/display convention (Benefit Value section), not a Missouri-published rule.

---

### Scenario 11: Child Already Receiving Medicaid – Excluded from CHIP
**What we're checking**: Validates that a child who already has Medicaid coverage is excluded from CHIP via the screener's `medicaid` enrollment flag, since CHIP is only for children not otherwise eligible for or enrolled in Medicaid
**Expected**: Not eligible (no CHIP-eligible children in this household)

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `3`
- **Person 1**: Birth month/year: `March 1990` (age 36), Relationship: `headOfHousehold`, Has income: Yes, Employment income: `$2,500` per month, Insurance: `none`, Citizenship: US Citizen
- **Person 2**: Birth month/year: `September 1992` (age 33), Relationship: `spouse`, Has income: Yes, Employment income: `$1,800` per month, Insurance: `none`, Citizenship: US Citizen
- **Person 3**: Birth month/year: `January 2018` (age 8), Relationship: `child`, Has income: No, Insurance: `medicaid` (child already has Medicaid coverage), Citizenship: US Citizen
- **Current Benefits**: Indicate that the child (Person 3) currently receives Medicaid

**Why this matters**: Tests the enrollment-flag path via the screener's `medicaid` field. Household income (~$51,600/year) is above the Appendix A lower routing boundary ($41,808) and wouldn't itself trigger Medicaid income-eligibility, isolating the enrollment check from the income check tested in Scenario 9.
- **Source**: 42 CFR § 457.350(d) (a child found Medicaid-eligible is dispositive and CHIP-ineligible) and Mo. Rev. Stat. § 208.631.2.

---

### Scenario 12: Mixed Household – Two Children Eligible, One Over Age 18, Plus Adult
**What we're checking**: Validates that in a multi-member household, only children under age 19 are flagged as CHIP-eligible while an adult child (age 19) and the head of household are correctly excluded, and that household size is correctly counted for the income threshold
**Expected**: Eligible, **$4,299.70/year**

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `4`
- **Person 1**: Relationship: `headOfHousehold`, Birth month/year: `March 1984` (age 42), Has income: `Yes`, Employment income: `$5,500` per month ($66,000/year), Insurance: `None`, Citizenship: `US Citizen`
- **Person 2**: Relationship: `child`, Birth month/year: `January 2007` (age 19), Has income: `No`, Insurance: `None`, Citizenship: `US Citizen`
- **Person 3**: Relationship: `child`, Birth month/year: `September 2014` (age 11), Has income: `No`, Insurance: `None`, Citizenship: `US Citizen`
- **Person 4**: Relationship: `child`, Birth month/year: `December 2020` (age 5), Has income: `No`, Insurance: `None`, Citizenship: `US Citizen`

**Why this matters**: Tests the core multi-member logic: a household with children of varying ages where two meet the under-19 criterion and one (age 19) does not. 2026 FPL for a household of 4 is $33,000; $66,000/year is ≈200% FPL, landing in the 185–225% premium tier ($127/mo). Two eligible children (Persons 3 and 4; Person 2 excluded for age): net value = (2 × $2,911.85) − ($127 × 12 = $1,524) = **$4,299.70/year**.
- **Source**: Mo. Rev. Stat. § 208.631.2 (under-19 age gate) and DSS Manual Appendix E, IM-4(PRM) (07-26) (HH4, >185–225% band, $127/mo).

---

### Scenario 13: Multiple Eligible Children – Family of 5, Three Children Under 19
**What we're checking**: Validates that multiple children in the same household can each independently qualify for CHIP when all age, income, residency, and coverage criteria are met, and that the household premium is charged only once despite three eligible children
**Expected**: Eligible, **$4,379.55/year**

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `5`
- **Person 1**: Relationship: `headOfHousehold`, Birth month/year: `March 1988` (age 38), Has income: Yes, Employment income: `$5,500` per month ($66,000/year), Insurance: None, Not currently receiving Medicaid or CHIP
- **Person 2**: Relationship: `spouse`, Birth month/year: `June 1990` (age 36), Has income: Yes, Employment income: `$2,000` per month ($24,000/year), Insurance: None, Not currently receiving Medicaid or CHIP
- **Person 3**: Relationship: `child`, Birth month/year: `September 2010` (age 15), Has income: No, Insurance: None, Not currently receiving Medicaid or CHIP
- **Person 4**: Relationship: `child`, Birth month/year: `January 2015` (age 11), Has income: No, Insurance: None, Not currently receiving Medicaid or CHIP
- **Person 5**: Relationship: `child`, Birth month/year: `April 2021` (age 5), Has income: No, Insurance: None, Not currently receiving Medicaid or CHIP

**Why this matters**: 2026 FPL for a household of 5 is $38,680; combined income of $90,000/year is ≈233% FPL, landing in the top premium tier ($363/mo for family size 5). Three eligible children, one household premium: net value = (3 × $2,911.85 = $8,735.55) − ($363 × 12 = $4,356) = **$4,379.55/year**. Confirms the system identifies ALL eligible children (not just the first) while adults are correctly excluded, and that a large eligible-child count comfortably absorbs the top-tier premium without hitting the $1 floor.
- **Source**: DSS Manual Appendix E, IM-4(PRM) (07-26) (HH5, >225–300% band, $363/mo); premium-once-per-household per the Benefit Value section's committed methodology.

---

### Scenario 14: Child in the Last Still-Eligible Birth Year – Unambiguously Still 18
**What we're checking**: Tests the upper age boundary from the eligible side, using a birth month whose *eligibility outcome* is unambiguous even though the screener captures only birth month/year and cannot know whether the birthday has already occurred
**Expected**: Eligible, **$2,611.85/year**

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `2`
- **Person 1**: Relationship: `headOfHousehold`, Birth month/year: `March 1980` (age 46), Has income: Yes, Employment income: `$3,000` per month (~$36,000/year), Insurance: None, Citizenship: US Citizen
- **Person 2**: Relationship: `child`, Birth month/year: `January 2008` (age 18), Has income: No, Insurance: None, Not currently receiving Medicaid or CHIP, Citizenship: US Citizen

**Why this matters**: The screener captures birth month/year, not day, so for a birth month at or adjacent to the boundary it cannot tell whether the birthday has already occurred — and a single day would flip the result. `January 2008` removes that risk from both directions at once: the screener computes 18 for every screening month of 2026, and even if the child's actual birthday has not yet passed they would be 17 — both are under 19, so the eligibility outcome carries no day-level ambiguity. 2008 is also the last birth year still 18 in 2026 under a period-year age, so this input holds under either age semantics (see the evaluation-date note above). Scenario 7 covers the ineligible side of the same boundary at age 19. $36,000/year is ≈166% FPL for a household of 2, landing in the first premium tier ($25/mo). Net value = $2,911.85 − ($25 × 12 = $300) = **$2,611.85/year**.
- **Source**: Mo. Rev. Stat. § 208.631.2 (under-19 age gate, evaluated from `birth_month`/`birth_year`) and DSS Manual Appendix E, IM-4(PRM) (07-26) (HH2, >150–185% band, $25/mo).

---

### Scenario 15a: Income Exactly at the Published Lower Routing Boundary — Outside This Premium Calculator's Scope
**What we're checking**: Income exactly equal to Missouri's published Appendix A lower routing boundary for ages 1-18, household size 3, must resolve to ineligible for **this** premium CHIP 73-75 calculator (the boundary is inclusive — `≤`, not `<`). This is the mirror case to Scenario 4's "exactly at the ceiling" test, but for the *lower* age-based boundary.
**Expected**: Not eligible — outside this premium CHIP calculator's scope.

**Steps**: ZIP `63101`, county St. Louis City. Household of 3: Person 1 (`headOfHousehold`, age 36, March 1990, employment income entered at **monthly frequency**, `$3,484.00`/month exactly, insurance `none`, US Citizen); Person 2 (`spouse`, age 33, September 1992, no income, insurance `none`, US Citizen); Person 3 (`child`, age 10, January 2016, no income, insurance `none`, not currently enrolled in Medicaid, US Citizen).

**Why this matters**: Missouri's current Appendix A table lists $3,484.00/month as the ages-1-18 effective maximum for a household of 3 — the policy-correct lower routing boundary per criterion 2. At exactly $3,484.00/month, the child sits at this calculator's lower scope boundary and should be routed to Missouri's non-premium child-coverage pathways instead. This was one of the three exact-dollar-boundary scenarios affected by the now-resolved PE blocker (see Scenario 4's note and Acceptance Criteria) — confirmed fixed on a live rerun, and MFB's production PE version pin has been updated accordingly.
- **Source**: DSS Manual MAGI Appendix A (HH3 ages-1-18 lower boundary, $3,484.00/mo).

---

### Scenario 15b: Income One Dollar Above the Published Lower Routing Boundary — Genuine CHIP Case
**What we're checking**: Income immediately above that same boundary must flip to CHIP-eligible — the mirror case to 15a, one dollar higher. **Amended for implementation:** the screener sends PolicyEngine `int(annual income)`, so a one-cent-per-month step — twelve cents a year — is truncated away and this household arrives identical to its boundary twin. The input below steps one dollar per month instead, the smallest step that survives the truncation; the side of the boundary, the premium tier and the expected value are unchanged.
**Expected**: Eligible, **$2,527.85/year**

**Steps**: Identical to 15a except Person 1's employment income is entered at **monthly frequency**, `$3,485.00`/month — one dollar above the $3,484.00 boundary.

**Why this matters**: At $3,485.00/month — one dollar above Missouri's published Appendix A lower routing boundary for a household of 3 — this household sits just above the line, close enough that a boundary implementation error would misclassify it, but genuinely above the correct threshold, so the correct result is CHIP-eligible, not Medicaid. Falls in the first premium tier for family size 3 ($32/mo). Net value = $2,911.85 − ($32 × 12 = $384) = **$2,527.85/year** (matches Scenario 1's dollar figure because both share the same family size and premium tier — this scenario tests boundary proximity, not a unique dollar total).
- **Source**: DSS Manual MAGI Appendix A (HH3 ages-1-18 lower boundary, $3,484.00/mo) and Appendix E, IM-4(PRM) (07-26) (HH3, >150–185% band, $32/mo).

---

### Scenario 17: Family Size 8 – Concrete Eligible Boundary Case (Largest Household the Screener UI Accepts)
**What we're checking**: The family-size lookup correctly resolves a large household at the screener's actual maximum size (8) — `HouseholdSize.tsx` enforces a hard `.lte(8)`, so this is the largest household any test can exercise through the real UI (Missouri's own chart continues through size 12; see Benefit Value's scope note).
**Expected**: Eligible, **$14,903.11/year**

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `8`
- **Person 1**: Relationship: `headOfHousehold`, Birth month/year: `March 1985` (age 41), Has income: Yes, Employment income entered at **yearly frequency**, `$114,000`/year exactly (= $9,500.00/month), Insurance: None, Citizenship: US Citizen
- **Person 2**: Relationship: `spouse`, Birth month/year: `June 1987` (age 39), Has income: No, Insurance: None, Citizenship: US Citizen
- **Persons 3–8** (6 children), each given an explicit birth month/year, none an infant:
  - Person 3: May 2023 (age 3)
  - Person 4: February 2021 (age 5)
  - Person 5: July 2019 (age 7)
  - Person 6: April 2017 (age 9)
  - Person 7: January 2015 (age 11)
  - Person 8: October 2012 (age 13)
  - All 6: Relationship `child`, Has income: No, Insurance: None, Citizenship: US Citizen, not currently enrolled in Medicaid or CHIP

**Why this matters**: Missouri's Appendix E chart publishes family-size-8 monthly income bands directly (not derived from raw FPL-percentage math): the >185% band runs $8,591.01–$10,448.00/month at a $214/mo premium. This household's $9,500.00/month sits inside that published band. No child is an infant, and $9,500/month is well above the 153% premium-CHIP lower routing boundary for ages 1-18 at this family size, so all six children are CHIP-eligible, not Medicaid. Six eligible children, one household premium: net value = (6 × $2,911.851 = $17,471.106, rounding to cents only once at the end → $17,471.11) − ($214 × 12 = $2,568) = **$14,903.11/year**. (Multiplying the already-rounded $2,911.85 display figure by 6 first gives $17,471.10 — one cent low; per-child value must be summed unrounded before the single final rounding.)
- **Source**: DSS Manual Appendix E, IM-4(PRM) (07-26) (HH8, >185–225% band, $8,591.01–$10,448.00/mo, $214/mo); `benefits-calculator`'s `HouseholdSize.tsx` (`.lte(8)` UI cap — Benefit Value's scope note).

---

Family sizes 9-12 have no test scenario: Missouri publishes rates for them, but the screener's own UI cannot currently accept a household size above 8, so there is no way to submit one through the real screener to test (see the Benefit Value section). Family size 13+ likewise has no test scenario: Missouri publishes no premium rate for that range at all. Household size 9+ eligibility follows the same criteria 1-8 as any other household size; only the value calculation is affected, and only for sizes this screener can actually collect.

---

### Scenario 18: Premium Tier Boundary — Income Exactly at Missouri's Published Tier 1/Tier 2 Cutoff (Still Tier 1)
**What we're checking**: Income exactly at Missouri's own published monthly tier boundary resolves to the *lower* tier (inclusive upper bound on tier 1), not the higher one. **Boundary source**: Appendix E publishes a rounded **monthly** dollar table, not a raw FPL-percentage calculation — for family size 2, the table itself states the >150% band runs "$2,705.00 to $3,337.00" and the >185% band begins at "$3,337.01." $3,337.00 is the correct boundary value (185% of annual FPL ÷ 12 would give $3,336.17, which is not what Missouri publishes).
**Expected**: Eligible, **$2,611.85/year**

**Steps**: ZIP `63101`, county St. Louis City. Household of 2: Person 1 (`headOfHousehold`, birth month/year `March 1986`, age 40, employment income entered at **monthly frequency**, `$3,337.00`/month exactly, insurance `none`, US Citizen); Person 2 (`child`, birth month/year `January 2016`, age 10, no income, insurance `none`, US Citizen).

**Why this matters**: $3,337.00/month is the exact upper bound of Missouri's published >150% monthly band for family size 2 (tier 1, $25/mo premium). This household's income sits exactly on that published line and must resolve to the first premium tier, not the second. Net value = $2,911.85 − ($25 × 12 = $300) = **$2,611.85/year**.
- **Source**: DSS Manual Appendix E, IM-4(PRM) (07-26) (HH2 row: ">150 $2,705.00 to $3,337.00 $25").

---

### Scenario 19: Premium Tier Boundary — Income One Dollar Above Missouri's Published Tier 1/Tier 2 Cutoff (Enters Tier 2)
**What we're checking**: Income one dollar above Missouri's own published boundary correctly enters the second tier. **Amended for implementation:** the screener sends PolicyEngine `int(annual income)`, so a one-cent-per-month step — twelve cents a year — is truncated away and this household arrives identical to its boundary twin. The input below steps one dollar per month instead, the smallest step that survives the truncation; the side of the boundary, the premium tier and the expected value are unchanged.
**Expected**: Eligible, **$1,915.85/year**

**Steps**: Identical to Scenario 18 except Person 1's employment income is entered at **monthly frequency**, `$3,338.00`/month — one dollar past the $3,337.00 end of the >150% band, so inside the >185% band Missouri's Appendix E table starts at `$3,337.01` for family size 2.

**Why this matters**: $3,337.01/month is the exact published start of the >185% tier for family size 2 ($83/mo premium), and $3,338.00 is inside it. This household must land in the 185–225% tier, not tier 1. Net value = $2,911.85 − ($83 × 12 = $996) = **$1,915.85/year**.
- **Source**: DSS Manual Appendix E, IM-4(PRM) (07-26) (HH2 row: ">185 $3,337.01 to $4,058.00 $83").

---

### Scenario 20: Premium Tier Boundary — Income Exactly at Missouri's Published Tier 2/Tier 3 Cutoff (Still Tier 2)
**What we're checking**: Income exactly at Missouri's own published monthly tier boundary resolves to the *lower* tier.
**Expected**: Eligible, **$1,915.85/year**

**Steps**: Identical to Scenario 18 except Person 1's employment income is entered at **monthly frequency**, `$4,058.00`/month exactly — the published upper bound of the >185% band for family size 2.

**Why this matters**: $4,058.00/month is the exact published end of Missouri's >185% monthly band for family size 2 (tier 2, $83/mo premium). This income sits exactly on that published line and must resolve to the 185–225% tier, not the top tier. Net value = $2,911.85 − ($83 × 12 = $996) = **$1,915.85/year** (matches Scenario 19's dollar figure because both fall in the same tier for the same family size — the two scenarios test different boundaries, not different premium math).
- **Source**: DSS Manual Appendix E, IM-4(PRM) (07-26) (HH2 row: ">185 $3,337.01 to $4,058.00 $83").

---

### Scenario 21: Premium Tier Boundary — Income One Dollar Above Missouri's Published Tier 2/Tier 3 Cutoff (Enters Top Tier)
**What we're checking**: Income one dollar above Missouri's own published boundary correctly enters the top premium tier. **Amended for implementation:** the screener sends PolicyEngine `int(annual income)`, so a one-cent-per-month step — twelve cents a year — is truncated away and this household arrives identical to its boundary twin. The input below steps one dollar per month instead, the smallest step that survives the truncation; the side of the boundary, the premium tier and the expected value are unchanged.
**Expected**: Eligible, **$475.85/year**

**Steps**: Identical to Scenario 18 except Person 1's employment income is entered at **monthly frequency**, `$4,059.00`/month — one dollar past the $4,058.00 end of the >185% band, so inside the >225% band Missouri's Appendix E table starts at `$4,058.01` for family size 2.

**Why this matters**: $4,058.01/month is the exact published start of the >225% tier for family size 2 ($203/mo premium), and $4,059.00 is inside it. This household must land in the top 225–300% tier, not the middle tier. Net value = $2,911.85 − ($203 × 12 = $2,436) = **$475.85/year**. Appendix E's exact row for family size 2: `>225 | $4,058.01 to $5,410.00 | $203` — this scenario's income falls within that published range.
- **Source**: DSS Manual Appendix E, IM-4(PRM) (07-26) (HH2 row: ">225 $4,058.01 to $5,410.00 $203").

---

The AI/AN premium exemption has no test scenario: submitting Scenario 1's household with tribal membership added is not a distinguishable input (no tribal-membership field exists in either the screener or PE), so it cannot test anything beyond what Scenario 1 already confirms. The committed handling, description requirement, and citation live in the Benefit Value section's AI/AN data-gap note.

## Source Documentation

- [Mo. Rev. Stat. § 208.631](https://revisor.mo.gov/main/OneSection.aspx?section=208.631) – full current statute text (effective 2014): only 2 subsections exist
- [Missouri DSS Manual § 1840.010.10 – Uninsured](https://dssmanuals.mo.gov/family-mo-healthnet-magi/1840-000-00/1840-010-00/1840-010-10/)
- [Missouri DSS Manual § 1840.025.00 – Payment of Premium](https://dssmanuals.mo.gov/family-mo-healthnet-magi/1840-000-00/1840-025-00/) – confirms no anti-crowd-out waiting period exists today; documents the separate 30-day coverage-*start* delay for the >225% FPL premium group (CHIP75); also source of the AI/AN premium-exemption note
- [Missouri DSS Manual § 1805-030-20-20-05 – 5% FPL Income Disregard](https://dssmanuals.mo.gov/family-mo-healthnet-magi/1805-000-00/1805-030-00/1805-030-20/1805-030-20-20/1805-030-20-20-05/) – confirms disregard applies to CHIP's 300% FPL ceiling
- [42 CFR § 457.310(c)](https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-D/part-457/subpart-C/section-457.310) ([Cornell Law mirror](https://www.law.cornell.edu/cfr/text/42/457.310)) – institution/public-agency-plan exclusions
- [42 CFR § 457.350](https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-D/part-457/subpart-C/section-457.350) ([Cornell Law mirror](https://www.law.cornell.edu/cfr/text/42/457.350)) – Medicaid/CHIP coordination rule: subsection (d) confirms a child found eligible for MAGI Medicaid must be transferred to Medicaid and found CHIP-ineligible (dispositive); subsection (e) confirms a child only potentially eligible for non-MAGI Medicaid triggers referral/transfer while CHIP still completes its own determination (not an automatic denial), with (e)(4) requiring CHIP disenrollment if Medicaid later confirms eligibility
- [Missouri DSS Appendix E – "MO HealthNet for Kids – CHIP Premium Chart," IM-4(PRM) (07-26)](https://dssmanuals.mo.gov/wp-content/uploads/2019/05/appendix-e.pdf) – confirmed effective July 1, 2026, $19/$62/$150 (family of 1)
- [MAGI MO HealthNet Program Descriptions (4/2026)](https://dssmanuals.mo.gov/wp-content/uploads/2020/03/MAGI-Appendix-I.pdf) – source of the infant (196% FPL nominal) vs. ages-1-18 (148% FPL nominal) Medicaid ceiling distinction
- [DSS Manual MAGI Appendix A (PDF)](https://dssmanuals.mo.gov/wp-content/uploads/2019/03/MAGIappendix-a.pdf) – monthly-dollar income maximums by household size, disregard already incorporated; this is the binding source for criterion 2's implementation, not just a confirmation of the 153%/201%/305% policy concept. The 2026 income-limit values are effective 2026-04-01 through 2027-03-31. Appendix A presents them in two table periods — 4/1/2026–6/30/2026 and 7/1/2026–3/31/2027 — because CHIP premium amounts change July 1; the eligibility-income rows themselves are unchanged across the two periods. This is a separate cycle from Appendix E's 2026-07-01 premium-table cycle cited above — do not conflate the two effective dates. (The HTML `dssmanuals.mo.gov/family-mo-healthnet-magi/magi-appendix-a/` page is stale and currently surfaces an older 2022 table — use the direct PDF linked here, not that page.)
- [DSS Manual § 1840.010.15.12](https://dssmanuals.mo.gov/family-mo-healthnet-magi/1840-000-00/1840-010-00/1840-010-15/1840-010-15-12/) – Missouri-specific state-employee health plan exclusion (criterion 7)
- [42 CFR § 457.535](https://www.law.cornell.edu/cfr/text/42/457.535) – controlling federal rule prohibiting CHIP premiums/cost-sharing for AI/AN children (Benefit Value's AI/AN exemption note)
- [ASPE 2026 Poverty Guidelines](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines) – base FPL dollar figures by household size, cross-checked against the Appendix E chart's monthly income bands
- [MACPAC Exhibit 33 – CHIP Spending by State](https://www.macpac.gov/publication/chip-spending-by-state/) and [Exhibit 32 – Child Enrollment in CHIP and Medicaid by State](https://www.macpac.gov/publication/child-enrollment-in-chip-and-medicaid-by-state/) – MO FY2024 spending/enrollment figures (rounded; see Benefit Value for exact PE inputs vs. MACPAC's rounded corroboration)
- PolicyEngine source (`per_capita_chip.py`, `per_capita_chip_gross.py`, `chip.py`, `chip_gross.py`, `is_chip_eligible_child.py`, `has_chip_disqualifying_health_coverage.py`, `receives_medicaid.py`, `is_medicaid_eligible.py`, `medicaid_income_level.py`, and the MO `mo_chip_premium`/spending/enrollment/cost-sharing-offset parameter files); [PR #9258](https://github.com/PolicyEngine/policyengine-us/pull/9258) (converts `mo_chip_premium` to a `MONTH`-definition variable, merged 2026-08-09); [PR #9297](https://github.com/PolicyEngine/policyengine-us/pull/9297) (applies Missouri's rounded Appendix A dollar limits to `medicaid_income_level`, merged 2026-08-17)
- [CMS's current CHIPRA § 214 (ICHIA) election list](https://www.medicaid.gov/medicaid/enrollment-strategies/medicaid-and-chip-coverage-of-lawfully-residing-children-pregnant-women), updated 2026-04-02 – directly confirms Missouri is not among the states electing this option for CHIP children (criterion 8)
- [CMS SHO #26-001](https://www.medicaid.gov/federal-policy-guidance/downloads/sho26001.pdf), implementing P.L. 119-21 § 71109 – federal basis for the 2026-10-01 immigration-eligibility narrowing
- [MO DSS H.R. 1 Participant Resources](https://mydss.mo.gov/hr1/participant-resources) – Missouri's own confirmation of the 2026-10-01 implementation date, categories excluded (refugees, asylees, other humanitarian groups), and that notices were already mailed/emailed to affected households in June 2026
