# KS Homestead Property Tax Refund (K-40H) — Eligibility Spec

## Program Details

- **Program**: Homestead Refund (K-40H)
- **State**: KS
- **White Label**: ks
- **Claim Year**: 2025 (filed January 1 – April 15, 2026)
- **Research Date**: 2026-06-11 (reviewed/corrected 2026-06-12; eligibility-completeness pass 2026-07-06; K.A.R. regulatory-layer pass 2026-07-07)

> **Maintenance note**: The household income limit is CPI-indexed annually under K.S.A. 79-4508. The $43,389 figure below is for the 2025 claim year and must be updated each year when KDOR publishes the new booklet. Do not hardcode as a permanent constant.
>
> The config `apply_button_link` points to the year-stamped K-40H form PDF (`.../pdf/k-40h25.pdf`). Update the year suffix annually alongside the income limit (e.g., `k-40h26.pdf` for the 2026 claim year) when KDOR posts the new form. Also update the AARP Tax-Aide navigator `assistance_link` (`kstaxaide.com/homestead-2025`) to the matching year suffix at the same time. Re-confirmed 2026-07-07: `k-40h26.pdf`/`k-40hbook26.pdf` do not exist yet — the 2025 documents remain current. A 2026-session bill to restore renter eligibility (SB 455 / HB 2074) died in committee — renters remain ineligible (criterion 4) as of this writing; worth a watch item since two bills attempted this in one session.

## Eligibility Criteria

1. **Claimant must meet at least one categorical requirement:**

   - (a) Age 55 or older for the ENTIRE claim year — i.e., born before January 1, 1970 (for claim year 2025)
   - (b) Blind or totally and permanently disabled all of 2025, regardless of age
   - (c) Has a dependent child who lived with the claimant the entire year, born before January 1, 2025, under age 18 all of 2025, and who is or may be claimed as the claimant's tax dependent
   - (d) Disabled veteran (service-connected evaluation of 50% or greater) ⚠️ *partial data gap — proxied via VA-benefits income stream and disability flags; see criterion 8*
   - (e) Surviving spouse (not remarried) of a disabled veteran, or of a member of the armed forces who died in the line of duty during active service ⚠️ *partial data gap — caught only when survivor reports VA-benefits income; otherwise under-inclusive; see criterion 8*

   - Screener fields:
     - `household_members.birth_year` / `birth_month` (path a — implement as birth_year ≤ 1969, NOT age >= 55, to satisfy the "entire calendar year" requirement precisely)
     - `visually_impaired`, `disabled`, `long_term_disability` (path b — proxies; see criterion 9)
     - `household_members.birth_year` / `birth_month` + `household_members.relationship` (path c — use the child's birth date, NOT `age`. The rule is "under 18 the ENTIRE calendar year," and `age` is only a current snapshot. For claim year 2025: child `birth_year ≥ 2008` (i.e., born on/after Jan 1, 2008, so they do not turn 18 during 2025) AND born before Jan 1, 2025. Generalize as `claim_year − 17 ≤ birth_year` and born before the claim year. Mirrors path (a)'s birth-year approach.)
   - Source: [KDOR Homestead Refund Programs](https://www.ksrevenue.gov/perstaxtypeshs.html); [2025 K-40H Booklet](https://www.ksrevenue.gov/pdf/k-40hbook25.pdf), "Qualifications" and Lines 1–3 instructions; K.S.A. 79-4502
   - Notes: Paths (a)–(c) are evaluable from screener data. Path (c): apply the birth-year age test above to each child, and treat children currently in the household as a proxy for "entire year" residence (inclusivity assumption — see criterion 12).

2. **Household income must not exceed $43,389 (2025 claim year)**

   - Screener fields:
     - `income_streams` (all household members, via `calc_gross_income`, with the adjustments below)
   - Source: [2025 K-40H Booklet](https://www.ksrevenue.gov/pdf/k-40hbook25.pdf), Line 10 instructions and Refund Percentage Table; [KDOR Homestead Programs](https://www.ksrevenue.gov/perstaxtypeshs.html); K.S.A. 79-4508 (CPI indexing)
   - Notes — **K-40H household income differs from gross income; the calculator must apply these adjustments**:
     - Count only **50%** of Social Security retirement/survivor and non-disability SSI benefits (`sSRetirement`, `sSSurvivor`, `sSI` — see screener note below)
     - **Exclude entirely**: Social Security disability (`sSDisability`), SSI disability (per KDOR FAQ: "SSI Disability payments" are fully excluded, same as SSDI), VA disability (see dev note in criterion 8 — the `veteran` income type cannot distinguish VA disability from non-disability VA payments; treat entire stream as includable income per the chosen default), and Railroad Retirement disability payments. Also excluded: SS payments of a person whose benefits converted from disability at full retirement age. **Implementation note (checked 2026-07-07)**: no distinct "Railroad Retirement" income-stream type exists in the screener model — this exclusion is currently unreachable/moot rather than an untested branch. No scenario needed unless/until such a field is added; flag in code comments so a developer doesn't search for a phantom field.
     - Note (screener limitation): the screener has a single `sSI` type and cannot distinguish non-disability SSI (aged/blind — 50%) from SSI Disability (excluded). Default: treat `sSI` → 50%. This is **conservative** for disability-SSI recipients — their income is over-counted relative to the correct rule ($0), so their estimated refund will be lower than their actual entitlement. The truly inclusive default would be to exclude all `sSI`, but that would overstate refunds for aged/blind SSI recipients. 50% follows the booklet's general rule and is the correct pragmatic default; flag in calculator code comments.
     - Include all members' income: wages, self-employment, interest/dividends, all other pensions/annuities, veterans non-disability benefits, unemployment, workers comp, TAF/welfare, alimony, gambling winnings, etc.
     - **Exclude entirely**: child support (`childSupport`) and nongovernmental gifts (`gifts`) — the 2025 K-40H form's "Excluded Income" section (items b–c) and K.S.A. 79-4502 both explicitly exclude these from household income. The screener has both as income-stream types; the calculator must exclude them, not include them.
     - **Exclude entirely**: income of a dependent minor or incapacitated household member who is not seized of legal title to the homestead and not a party to its rental agreement. Operative text (K.A.R. 92-22-11, fetched 2026-07-07): *"Household income shall not include the income of a dependent minor or an incapacitated person who occupies the homestead if the person is not seized of legal title or a party to the rental agreement of the homestead."* Without this exclusion the calculator would over-count, e.g., a working teenager's wages or a dependent adult's SSI/earnings toward the $43,389 limit. MFB's `household_members` tags dependents via `relationship`/age; exclude `income_streams` for members flagged as a `child` or otherwise dependent who don't hold title. Non-dependent adult co-residents (boarders, caregivers, unrelated adults) remain fully included per the 2025 booklet's Line 9 instructions — this exclusion applies only to dependents/incapacitated members without an ownership or rental-agreement stake.
     - Net operating losses / net capital losses may NOT reduce household income.
     - **Exclude entirely** (2025 K-40H form, "Excluded Income" section, verified verbatim 2026-07-08 by reading the actual form image, page 2 of the claim): **(a) Food Stamps** — moot for the calculator: SNAP is modeled in the screener as a separate boolean (`has_snap`), never as an `income_streams` entry, so it could never be wrongly counted as income in the first place; **(d) Settlements (lump sum)** and **(e) Personal and Student Loans** — genuine risk, unlike Food Stamps: neither has a dedicated `income_streams` type, so a user or a careless implementation could report a one-time legal settlement or student-loan disbursement under the generic `other` income type and have it wrongly counted toward the $43,389 limit. Flag in calculator code comments: `other`-type income needs a case-by-case judgment call, not a blanket include.
   - Residual gap (minor): statutory household income also includes federal EITC received, gain from business/investment property sales and long-term capital gains (2025 K-40H Booklet, page 2, "Household income includes"), and income of part-year household members — not captured by the screener as distinct types (a capital gain could plausibly be reported under the `investment` or `other` type if the user thinks to, but nothing forces it). Inclusivity assumption: ignore; may slightly over-include households near the limit.

3. **Claimant must be a Kansas resident**

   - Screener fields:
     - `zipcode`
     - `county`
   - Source: [2025 K-40H Booklet](https://www.ksrevenue.gov/pdf/k-40hbook25.pdf), "Qualifications"; K.S.A. 79-4502
   - Notes: Statute requires residency for the ENTIRE claim year; the screener verifies current residency only (see criterion 7).

4. **Claimant must OWN and occupy the homestead. Renters are NOT eligible.**

   - Screener fields:
     - `expenses` (Housing rows: `rent`, `mortgage`, `propertyTax`) — proxy, see logic below
   - Source: [2025 K-40H Booklet](https://www.ksrevenue.gov/pdf/k-40hbook25.pdf): "Homestead refunds are not available to renters. You must own your home to qualify."; [KDOR Homestead Programs](https://www.ksrevenue.gov/perstaxtypeshs.html); K.S.A. 79-4502 (definition of "owned"); K.S.A. 79-4501 (amendment history)
   - Notes:
     - **Renter eligibility was repealed by L. 2012, ch. 135, § 30, eff. 1/1/2013.** K.S.A. 79-4501's amendment history (re-confirmed via ksrevisor.gov 2026-07-07) lists this exact citation and date; the current, live statute text contains no renter provision. Before that date the program allowed renters to deem 15% of rent as property tax; that provision no longer exists — any renter logic in the calculator is incorrect. **Precision note**: the amendment-history line itself is just a citation/date stub — it doesn't literally say "repeals the renter provision" — so the *characterization* of what the 2012 amendment did (vs. just its citation and date) rests on the corroborating web-search history check from the 2026-07-06 pass, not a direct statutory quote. The current-law conclusion (renters are not eligible today) is independently and directly confirmed from the live 2025 booklet regardless of this historical framing, so nothing about the calculator's behavior depends on the 2012/15% detail being airtight.
     - **Ownership** (K.S.A. 79-4502 definition of "owned"; K.A.R. 92-22-12, fetched 2026-07-07) includes: the claimant's name on the deed; a contract-for-deed vendee; a joint tenant or tenant in common; **a life estate holder**; **a beneficiary of a trust (e.g., a revocable living trust) that holds title** — common in this program's 55+ target demographic, where the home is often titled to a trust rather than the individual; and **a statutory inchoate spousal interest ([K.S.A. 59-505](https://www.ksrevisor.gov/statutes/chapters/ch59/059_005_0005.html), "Surviving spouse entitled to 1/2 of real estate")** — if the homestead is titled solely to an ineligible spouse, the claimant spouse is still treated as a co-owner. "Rent to own" (no equitable/legal title yet) does NOT qualify. **Benefit-calc nuance (not currently modeled)**: K.A.R. 92-22-12 also specifies that tenancy-in-common co-owners are deemed to own "the whole" homestead only if all co-tenants are household members who pay the taxes; otherwise each co-owner's allowed property tax is prorated to their legal ownership percentage. The calculator currently assumes 100% ownership share — flag as a known simplification for the rare non-household co-ownership case.
     - **Manufactured/mobile homes qualify as a "homestead"** (K.S.A. 79-4502; 2025 K-40H Booklet, "Mobile and Manufactured Homeowners"). A manufactured/mobile homeowner who *rents the land/lot* the home sits on still qualifies as a homeowner for the home itself (they claim only the home's property tax, not the land's). **Proxy-logic caveat**: the calculator's `rent` expense > 0 → ineligible rule (below) would misclassify a lot-renting manufactured homeowner as a renter if they report lot rent under the `rent` expense type. Flag this known false-negative edge case in calculator code comments; no current screener field distinguishes "renting your home" from "renting the lot under a home you own."
     - **Proxy logic for the calculator** (the standard screener has no homeowner field; `is_home_owner`/`is_renter` exist only in the Energy Calculator):
       1. `rent` expense > 0 → NOT eligible (renter) — see manufactured-home caveat above for a known false-negative
       2. Else if `mortgage` expense > 0 OR `propertyTax` expense > 0 → treat as homeowner
       3. Else (no housing expenses entered) → treat as homeowner (inclusivity assumption; owners with paid-off homes — common in the 55+ K-40H demographic — show no mortgage. Over-includes renters who skipped the rent field.)
       These assumptions must appear as comments in the calculator code.
     - **Proposed screener improvement**: ask "Do you own or rent the place where you live?" (Own / Rent / Neither toggle) at the top of Step 6 Housing expenses, stored in the existing-but-unasked `housing_situation` field on the Screen model. Replaces the proxy with a direct answer and benefits all future housing-tenure programs. Mockup shared with the team 2026-06-12.

5. **Homestead appraised value must not exceed $350,000** ⚠️ *data gap*

   - Screener fields: none
   - Source: K.S.A. 79-4522 (controlling statute: "appraised valuation... exceeds $350,000" disqualifies); [KDOR Homestead Programs](https://www.ksrevenue.gov/perstaxtypeshs.html) ("Your house cannot be valued at more than $350,000"); [2025 K-40H Booklet](https://www.ksrevenue.gov/pdf/k-40hbook25.pdf), Line 12 instructions; [KDOR Homestead FAQ](https://www.ksrevenue.gov/faqs-taxhomestead.html)
   - Notes: This is a hard statutory bar — a home over the cap is ineligible regardless of income or category. **Boundary note (refined 2026-07-07)**: the controlling statute, K.S.A. 79-4522, disqualifies only when value "exceeds $350,000" (so exactly $350,000 qualifies), and the claim form itself (k-40h25.pdf, Line 12 field label) agrees — "Tax on property valued at **more than** $350,000 does not qualify." Only the 2025 booklet's Line 12 line-by-line *instructions* use stricter language — "$350,000 **or more** does not qualify" (implying exactly $350,000 disqualifies). So it's statute-and-form vs. booklet-instructions, not a bare summary-page inconsistency — the statute (and the form that implements it) governs, and both agree exactly $350,000 still qualifies. Immaterial for the calculator either way since home value is not captured. The screener does not capture home value, and a screener question was considered and rejected as too privacy-sensitive (reviewed 2026-06-12). Inclusivity assumption: assume the home is under the cap (most homes of income-eligible households will be; worst case is a denied application). **Surface in program description AND in the More Info document list**: "Your home must be appraised at $350,000 or less."

6. **Claimant must not be claimed as a dependent on another person's tax return** ⚠️ *data gap*

   - Screener fields: none
   - Source: [2025 K-40H Booklet](https://www.ksrevenue.gov/pdf/k-40hbook25.pdf); K.S.A. 79-4502
   - Notes: Not captured by the screener. Inclusivity assumption: assume the head of household is not someone else's dependent (reasonable for heads of household). **Description-surfacing disposition**: no description text needed — unlike criterion 5's home-value cap, this isn't a realistic population risk: to be a K-40H claimant at all, you must independently own a home and file your own refund claim (criterion 4), which is close to mutually exclusive with being claimed as someone else's tax dependent. Surfacing it would add clutter without protecting anyone in practice.
   - Screener improvement: considered, not proposed — the question is non-sensitive but fails the value test: near-empty error population (a tax dependent rarely owns the homestead they occupy), over-inclusion only, single program gated. Tracker watch item: revisit if future tax-credit programs need dependency status (reviewed 2026-06-12).

7. **Kansas residency for the ENTIRE claim year** ⚠️ *data gap*

   - Screener fields: none (current `zipcode`/`county` used as proxy via criterion 3)
   - Source: [2025 K-40H Booklet](https://www.ksrevenue.gov/pdf/k-40hbook25.pdf), "Qualifications"; K.S.A. 79-4502
   - Notes: Cannot verify full-year duration. Inclusivity assumption: current KS residency suffices for screening; people who moved to Kansas mid-year will be over-included. **Surface in program description**: "You must have lived in Kansas for all of the year you are claiming."
   - Screener improvement: considered, not proposed — the full-year requirement is already surfaced in the description; a "Did you live in Kansas for all of [year]?" question would add friction for every KS user to filter a small minority of mid-year arrivals.

8. **Disabled veteran and surviving spouse categorical paths** ⚠️ *data gap*

   - Screener fields: `income_streams` (type: Veteran's Pension or Benefits) — partial proxy; `visually_impaired`/`disabled`/`long_term_disability` — overlapping proxy
   - Source: [KDOR Homestead FAQ](https://www.ksrevenue.gov/faqs-taxhomestead.html) (50%+ service-connected rating, per [38 U.S.C. § 1101](https://www.law.cornell.edu/uscode/text/38/1101) et seq. / [10 U.S.C. § 1201](https://www.law.cornell.edu/uscode/text/10/1201) et seq.; surviving spouse eligible until remarriage); [2025 K-40H Booklet](https://www.ksrevenue.gov/pdf/k-40hbook25.pdf), Line 2 instructions
   - Notes: The disabled-veteran threshold is **50% or greater** service-connected rating (NOT 100%). **Proxy logic**: treat a Veteran's Pension or Benefits income stream on any member as satisfying the categorical requirement (the stream also catches survivors receiving VA benefits, partially covering path e). Cannot verify the 50%+ rating (over-inclusive), and misses veterans with no VA cash benefits (under-inclusive) — though those usually qualify via paths (a) or (b) anyway. Assumptions go in calculator code comments. **Proposed screener improvement** (2026-06-12): a "Connected to the U.S. military" Special Circumstances tile with an opt-in follow-up distinguishing veteran from un-remarried surviving spouse — maps to the existing `veteran` and `surviving_spouse` model fields (no model change; UI only). Pattern case: K-40SVR (planned per MFB-1068 mutex notes) uses both as primary categorical paths. Not required for K-40H launch — the income-stream proxy stands in the interim. The 50%+ rating deliberately stays unasked (medical-detail territory); it remains an over-inclusive assumption verified at application. **Surface in program description**: disabled veterans (50%+ rating) and un-remarried surviving spouses of disabled veterans or service members who died in the line of duty also qualify.
   - **Dev note — VA income-stream double-use (resolve in code comments):** the same "Veteran's Pension or Benefits" stream is used here as the *eligibility* proxy AND, under criterion 2, is treated as *includable* (non-disability) household income. But a 50%+ disabled veteran's VA payment is *disability* compensation, which criterion 2 says to **exclude**. The stream type cannot distinguish disability from non-disability VA income, so the two criteria pull in opposite directions for the same dollar. Chosen default (matches Scenario 12): count the VA stream as income (over-includes income → conservative on benefit amount) while letting it satisfy the categorical path. Document explicitly; revisit if a dedicated `veteran`/`surviving_spouse` screener input ships (then VA disability income can be excluded and the proxy retired).
   - Statutory definition (verified 2026-06-15, [KDOR FAQ](https://www.ksrevenue.gov/faqs-taxhomestead.html) / K.S.A. 79-4502): a "disabled veteran" is a Kansas resident, honorably discharged, **VA-certified at 50%+ permanent disability sustained through military action/accident or disease contracted in active service** — slightly narrower than generic "service-connected"; immaterial to the proxy but note for accuracy.

9. **Disability must be total and permanent (certified), or blindness** ⚠️ *data gap*

    - Screener fields: `visually_impaired`, `disabled`, `long_term_disability` (proxies)
    - Source: [2025 K-40H Booklet](https://www.ksrevenue.gov/pdf/k-40hbook25.pdf), Line 2 instructions (Social Security disability statement or physician-completed Schedule DIS); [KDOR Homestead FAQ](https://www.ksrevenue.gov/faqs-taxhomestead.html)
    - Notes: Statute requires total and permanent disability preventing substantial gainful activity, documented via SSA letter or Schedule DIS. **Concrete SGA threshold (verified 2026-07-08, reading the actual Schedule DIS form)**: when certification is via physician (not an existing SSA determination), annual income from substantial gainful activity must not exceed the SSA's 2025 limits — **$19,440** if the impairment is other than blindness, **$32,400** if the individual is blind. The screener booleans (`disabled`, `visually_impaired`, `long_term_disability`) cannot verify severity, certification, or this SGA income ceiling — a person who self-reports as disabled but earns well above these limits from work would be over-included by the proxy even though they may not meet K-40H's actual disability standard. This sharpens, rather than replaces, the existing inclusivity assumption: accept the booleans for screening; the SGA threshold and formal certification are both verified at application, not by the screener. **Description-surfacing disposition**: no additional text needed — the general "blind or disabled" categorical path is already covered via criterion 1(b); the SGA threshold and certification mechanism are application-time verification details, not facts a user needs to see before applying.
    - Screener improvement: not viable — certification is a documentation requirement (SSA letter or Schedule DIS) confirmed at application, not something a screener question can meaningfully capture. The existing disability booleans already carry the relevant signal.

10. **Claimant must occupy the homestead as their primary residence** ⚠️ *data gap*

    - Screener fields: none
    - Source: [2025 K-40H Booklet](https://www.ksrevenue.gov/pdf/k-40hbook25.pdf); K.S.A. 79-4502 definition of "homestead"; K.A.R. 92-22-4 (fetched 2026-07-07)
    - Notes: Cannot verify occupancy. Inclusivity assumption: assume the screened address is the occupied primary residence. **This assumption has affirmative legal support**: K.A.R. 92-22-4(d) provides that "temporary absence from the domicile shall not disqualify a claimant for a refund" — a seasonal absence or absence of reasonable duration (e.g., illness, hospitalization, a nursing-home stay) counts as temporary, and domicile is defined (92-22-4(a)) as the place the claimant intends to return to. So a claimant temporarily away from the screened address for illness or a similar reason would still legally qualify — the inclusivity assumption is not just a screener limitation, it matches the actual rule. **Description-surfacing disposition**: no additional text needed — the existing "your home" framing in the description already implies primary residence; the temporary-absence nuance is a reassurance point better suited to a navigator/FAQ than the main description, since surfacing it upfront would raise a question most users never have.
    - Screener improvement: considered, not proposed — "Is this your primary home?" would catch vacation homes and investment properties, but the error population is small and the description's "your home" framing already implies primary residence.

11. **General property taxes must be assessed and paid/payable on the homestead** ⚠️ *data gap*

    - Screener fields: `expenses` (`propertyTax` row — optional, often skipped)
    - Source: [2025 K-40H Booklet](https://www.ksrevenue.gov/pdf/k-40hbook25.pdf), Line 12 instructions; K.S.A. 79-4502 "property taxes accrued"
    - Notes: **Not an independent disqualifying gate** — unlike criterion 5's $350,000 cap, this isn't enforced by a separate rule. If a household genuinely has no property tax assessed (a fully tax-exempt home), the Benefit Value formula naturally produces allowed tax = $0 → refund = $0 → below the $5 floor → not issued, using the exact same mechanism already tested by Scenario 15. No separate "disqualify if no property tax" logic is needed; the existing $5 floor already covers this case automatically. Inclusivity assumption for eligibility: assume homeowners have property tax assessed (tax-exempt homes are a rare edge case) — practically moot given the above, but stated for clarity. For the benefit estimate, use the `propertyTax` expense when entered; otherwise fall back to the $700 cap — see Benefit Value methodology. Delinquent property taxes don't affect eligibility — the refund is redirected to the County Treasurer (K.S.A. 79-4523). **Description-surfacing disposition**: no description text needed — reinforced, not just held over, by the reclassification above: since this isn't an independent disqualifying rule but a natural consequence of having nothing to refund, there's no hidden gate to warn users about (self-evident for a property-tax refund program), and the calculator's own default-to-$700 behavior when the field is left blank already absorbs most of the practical risk before the $5 floor even applies.
    - Screener improvement: not viable — individual residential tax exemptions are rare enough that the inclusivity assumption holds for nearly all users; adding a question would add friction for everyone to catch a small edge case.

12. **Dependent child must have resided with the claimant the entire year** ⚠️ *data gap*

    - Screener fields: none (current `household_members` composition used as proxy)
    - Source: [2025 K-40H Booklet](https://www.ksrevenue.gov/pdf/k-40hbook25.pdf), Line 3 instructions
    - Notes: Inclusivity assumption: treat children currently in the household as having resided all year. The booklet also requires the child to reside "solely" with the claimant and be claimable as the claimant's dependent — shared-custody households may be over-included. **Description-surfacing disposition**: no additional text needed beyond the general dependent-child categorical mention (criterion 1(c)) — the "resided solely" and full-year nuances are edge cases better caught at application than surfaced to every user in the description.
    - Screener improvement: considered, not proposed for launch — "Has this child lived with you all year?" would address shared-custody over-inclusion, but the "solely" and dependency requirements are verified at application anyway. Revisit when household-composition questions are scoped for other programs that also need full-year residency of members.

13. **Claimant must not be a recipient of public funds specifically designated for the payment of taxes during the claim period** ⚠️ *data gap*

    - Screener fields: none
    - Source: K.S.A. 79-4515 (fetched ksrevisor.gov 2026-07-06)
    - Notes: Statute-only anti-double-dip provision. Operative text (K.S.A. 79-4515): *"No claim for relief under the provisions of this act shall be allowed to any claimant who is a recipient of public funds specifically designated for the payment of taxes during the period for which the claim is filed."* Distinct from general public assistance/cash benefits, which do NOT trigger this bar — only funds earmarked specifically for tax payment do. Not addressed anywhere in the KDOR program page, FAQ, or booklet, and not screener-evaluable. Inclusivity assumption: assume the claimant has not received tax-specific public funds — a narrow, low-incidence population verified by KDOR at application/audit. No description text needed; low practical impact.
    - Screener improvement: not viable — no screener question could reasonably capture "did you receive public funds specifically earmarked to pay your property taxes" without confusing typical users; this is an administrative/fraud-prevention check adjudicated by KDOR.

14. **Claim is disallowed if title to the homestead was acquired primarily to receive this benefit** ⚠️ *data gap*

    - Screener fields: none
    - Source: K.S.A. 79-4516 (fetched ksrevisor.gov 2026-07-06)
    - Notes: Statute-only anti-abuse provision. Operative text (K.S.A. 79-4516): *"A claim shall be disallowed if the division finds that the claimant received title to his or her homestead primarily for the purpose of receiving benefits under this act."* Not addressed anywhere in the KDOR program page, FAQ, or booklet, and not screener-evaluable (intent behind a property acquisition cannot be captured by a screener question). Inclusivity assumption: assume good-faith ownership — a rare edge case adjudicated by KDOR at application/audit, not the screener. **Description-surfacing disposition**: no description text needed — this is a fraud-prevention provision aimed at bad-faith actors; surfacing it to legitimate users ("don't buy a house just to get this refund") would be confusing and serves no screening purpose for the population MFB actually reaches.
    - Screener improvement: not viable — purpose/intent is not a screenable fact.

### Removed from eligibility criteria (vs. original research)

- ~~Renters qualify / 15% of rent as property tax~~ — repealed by L. 2012, ch. 135, § 30, eff. 1/1/2013; renters are ineligible (see criterion 4)
- ~~Income limit $42,600~~ — 2024 figure; corrected to $43,389 for 2025 with indexing note
- ~~VA disability must be 100%~~ — corrected to 50%+ (criterion 8)
- ~~Filing deadline (April 15)~~ — administrative requirement, moved to program description
- ~~Only one claimant per household may file~~ — administrative/structural; the screener evaluates households, not competing claimants. Kept as a note in the "Dev Notes — Sibling-Program Mutex" section below (formerly numbered as an eligibility criterion; relocated 2026-07-06 because it's calculator/results-page display logic, not a K-40H eligibility gate — a household's K-40H eligibility does not depend on it).

## Priority Criteria

None. K-40H is an entitlement refund — every qualifying claim is paid; there is no priority ordering, waitlist, or preference system. Confirmed by reading K.S.A. 79-4501 through 79-4523 in full (2026-07-06): no capped-funding, waitlist, or preference-ordering language anywhere in the Act.

## Dev Notes — Sibling-Program Mutex (K-40PT / K-40SVR)

*Relocated from the numbered Eligibility Criteria during the 2026-07-06 completeness sign-off: by its own logic this is calculator/results-page display logic, not a K-40H eligibility gate — a household's K-40H eligibility does not depend on this rule at all. It only matters once K-40PT and/or K-40SVR are implemented as separate MFB programs, at which point the results page must decide which of possibly multiple eligible programs to surface.*

**Only one refund claim (K-40H, K-40PT, or K-40SVR) may be filed per household per year** (K.S.A. 79-4507; [2025 K-40H Booklet](https://www.ksrevenue.gov/pdf/k-40hbook25.pdf), "Qualifications"; [KDOR Homestead FAQ](https://www.ksrevenue.gov/faqs-taxhomestead.html)). The three Kansas property tax refund programs are mutually exclusive for a given year. If/when K-40PT (SAFESR) or K-40SVR are added to the KS white label, the results page should note that only one may be claimed and KDOR WebFile automatically selects the largest. Surface in program description.

**Sibling-program parameters (verified 2026-06-15 against the [KDOR Homestead Programs page](https://www.ksrevenue.gov/perstaxtypeshs.html), for the future "best of three" implementation):**

- **K-40PT / SAFESR**: refund = **75%** of property taxes timely paid; household income ≤ **$25,380**; age **65+** the entire year (born before 1/1/1960); KS resident all year; own/occupy; home ≤ $350,000. No sliding scale — flat 75%, no $700 cap.
- **K-40SVR**: refund = current-year property tax minus base-year property tax; household income ≤ **$58,041**; categorical paths = age 65+ entire base year OR disabled veteran entire base year OR surviving spouse of a prior K-40SVR claimant; KS resident all year; own/occupy; home ≤ $350,000 (base year). Note the base-year mechanics (base year is the first full year the claimant met the 65/veteran test, not earlier than 2021). **Income-definition change (verified 2026-07-07):** HB 2231 § 11 (2025 session) redefines K-40SVR's household income as total Kansas Adjusted Gross Income (KAGI), effective TY2025 — a different computation from K-40H's category-by-category sum (requires pro forma KS returns for all household members). KDOR Notice 25-05 (July 3, 2025) confirms this change does NOT affect K-40H or K-40PT's income definitions. When K-40SVR is scoped for implementation, its income methodology needs its own spec section — it cannot reuse K-40H's Criterion 2 logic.
- Because the three programs use different income limits, percentages, and bases, the "best of three" logic must compute each independently and surface the largest — it cannot assume K-40H always wins.

**Minor note**: the booklet clarifies that a married couple who own and occupy *separate* households may each file a separate claim — the one-claim-per-household mutex only binds couples sharing one homestead. Low practical impact given the screener's single-household model.

**Screener improvement**: none possible — this is calculator/results logic, not user data. No question would resolve it (claims are annual; a prior year's choice doesn't bind this year). Handle by showing the best of the three programs once siblings ship, mirroring WebFile (reviewed 2026-06-12).

## Benefit Value

**Type**: Variable, computed. Refund = (allowed property tax) × (refund percentage), where:

- **Allowed property tax** = lesser of 2025 general property tax on the homestead or **$700** (K-40H line 13). Excludes special assessments, service charges, interest/late fees, and taxes on agricultural or commercial land (verified verbatim 2026-07-08, [2025 K-40H Booklet](https://www.ksrevenue.gov/pdf/k-40hbook25.pdf), Line 12 instructions: *"Do not include special assessments, such as those levied for streets, sewers, or utilities; charges for services, such as sewer services; interest or late charges; or taxes on agricultural or commercial land."*).
- **Refund percentage** comes from the income-based table below (2025 booklet, page 3). Refunds under $5 are not issued.
- Maximum possible refund: **$700** (requires household income ≤ $6,000 and property tax ≥ $700).
- `value_format`: `estimated_annual` (the refund is an annual amount, claimed each year — matches the property-tax-relief peers `tx_hse` and `wa_senior_disabled_pte`; NOT `lump_sum`, which is reserved for genuinely one-time benefits).

**2025 Refund Percentage Table** (household income → percentage):

| Household income (K-40H line 10) | Refund % |
| --- | --- |
| $0 – $6,000 | 100% |
| $6,001 – $7,000 | 96% |
| $7,001 – $8,000 | 92% |
| $8,001 – $9,000 | 88% |
| $9,001 – $10,000 | 84% |
| $10,001 – $11,000 | 80% |
| $11,001 – $12,000 | 76% |
| $12,001 – $13,000 | 72% |
| $13,001 – $14,000 | 68% |
| $14,001 – $15,000 | 64% |
| $15,001 – $16,000 | 60% |
| $16,001 – $17,000 | 55% |
| $17,001 – $18,000 | 50% |
| $18,001 – $19,000 | 45% |
| $19,001 – $20,000 | 40% |
| $20,001 – $21,000 | 35% |
| $21,001 – $22,000 | 30% |
| $22,001 – $23,000 | 25% |
| $23,001 – $24,000 | 20% |
| $24,001 – $25,000 | 15% |
| $25,001 – $26,000 | 10% |
| $26,001 – $43,389 | 5% |
| $43,390 and over | 0% (ineligible) |

**Property tax estimation methodology**: The standard screener collects Property Taxes as a Housing expense (`propertyTax`, often skipped by users). Calculator logic:

1. If `propertyTax` expense > 0: allowed property tax = min(annualized `propertyTax` expense, $700)
2. Else: assume allowed property tax = **$700** (the cap). Median Kansas residential property tax bills are well above $700, so this is accurate for nearly all homeowners; it slightly overestimates only for owners whose annual bill is under $700 (uncommon).

Estimated refund = allowed property tax × refund percentage from household income. These assumptions must appear as comments in the calculator code.

**Known simplifications** (conscious, low-impact — note in code comments): the estimate ignores the booklet's proration rules for partial rental/business use of the home (K.A.R. 92-22-5) and for mid-year moves (both reduce the claimable tax for small populations); ignores the Farm Owners rule (2025 K-40H Booklet, page 5: a homestead that's part of a farm covered by a single tax statement may only claim the general property tax paid on the "HOMESITE," not the whole farm parcel — the screener has no way to distinguish a farm-homesite bill from a standard residential bill, so a farm-owning household's entered `propertyTax` expense may overstate the allowed amount); ignores delinquent-tax redirection and the broader debtor set-off rule (any delinquent state debt — child support, student loan, medical bills, income tax, not just property tax — is deducted from the refund before payment; 2025 K-40H Booklet, page 6, "Debtor Set-Off") — both change where/how much of the refund is actually disbursed, not the computed refund amount itself; and assumes 100% ownership share, ignoring the tenancy-in-common proration rule for non-household co-owners (K.A.R. 92-22-12 — see criterion 4) that would reduce the allowed property tax to the claimant's legal ownership percentage in that rare case. **Finding confirmed 2026-07-08** (initially inferred from the K-40H/K-40PT forms, since resolved by web search corroborated by a KDOR/county-treasurer training document): both forms carry the note *"If you filed Form ELG with your county, your refund will be reduced by the ELG amount applied to the first half of your 2025 property tax."* "Form ELG" is the eligibility letter KDOR sends to a claimant's County Treasurer on behalf of a prior-year Homestead refund recipient who opted into the Refund Advancement Program — it credits the advancement amount against the first half of the *current* year's real estate tax, and that same amount is then subtracted from the *next* homestead refund to avoid double-paying the claimant. The estimator ignores this offset — a claimant who used advancement in a prior year would see a smaller actual refund than the calculator estimates. Narrow population (opt-in program, not the default path), but a real, now-confirmed simplification; flag in code comments.

- Source: [2025 K-40H Booklet](https://www.ksrevenue.gov/pdf/k-40hbook25.pdf), Refund Percentage Table and Lines 12–15 instructions; K.A.R. 92-22-5, 92-22-12 (proration rules, fetched 2026-07-07)

## Test Scenarios

*All scenarios use 2025 claim-year rules (income limit $43,389; refund table from the 2025 booklet). Expense-object key names mirror `income_streams` and need dev confirmation at import. County naming: the KS white label (`configuration/white_labels/ks.py`) stores counties **with** the "County" suffix (e.g., `Sedgwick County`). The k40h calculator does not use county at all, so the county value in these scenarios is location metadata only and does not affect the computed refund — the bare names below are harmless. (For reference, county matching in PE-based KS programs is suffix-insensitive: `CountyDependency` normalizes `Sedgwick` and `Sedgwick County` to the same token.)*

Benefit assumptions: allowed property tax = min(annualized Property Taxes expense, $700), defaulting to $700 when no expense is entered. Household income per the K-40H definition: 50% of SS/SSI retirement-survivor benefits; SS/SSI/VA/Railroad disability payments fully excluded; child support and gifts fully excluded; all other member income counted. Refund = allowed tax × table percentage; refunds under $5 are not paid. Values are annual refunds (`estimated_annual`).

---

### Scenario 1: Senior homeowner, Social Security income (Golden Path) ✓ in validation JSON

**What we're checking**: A 68-year-old homeowner qualifies via the age path (born before Jan 1, 1970) with the 50% Social Security rule applied to household income and the $700 cap fallback when no property-tax expense is entered.
**Expected**: Eligible — $616 (income = 50% × $16,800 = $8,400 → 88% bracket; $700 × 0.88 = $616).
**Steps**:

* Location: ZIP `67202`, county `Sedgwick`
* Household size: `1`, assets: $0
* Person 1: Birth month/year `March 1958` (age 68), `headOfHousehold`, Social Security retirement: $1,400/month, insurance: none
* Expenses: none

**Why this matters**: Primary regression test. Confirms the birth-year age check, the 50% SS inclusion rule, the no-housing-expenses → homeowner assumption, and the $700 cap fallback all work together.

---

### Scenario 2: Renter, otherwise fully qualified ✓ in validation JSON

**What we're checking**: A 70-year-old with qualifying age and income who pays rent is excluded — renters are not eligible under current law (repealed by L. 2012, ch. 135, § 30, eff. 1/1/2013).
**Expected**: Not eligible (no value). (Would be $644 if a homeowner.)
**Steps**:

* Location: ZIP `66604`, county `Shawnee`
* Household size: `1`, assets: $0
* Person 1: Birth month/year `May 1956` (age 70), `headOfHousehold`, Social Security retirement: $1,200/month, insurance: none
* Expenses: rent $800/month

**Why this matters**: Tests the owner-only gate via the rent-expense proxy — the headline correction of this review. Proves categorical eligibility and income do not override tenure.

---

### Scenario 3: Under-55 parent, dependent-child path, income near limit ✓ in validation JSON

**What we're checking**: A household where no adult meets age/disability paths qualifies via a dependent child under 18; multi-member wage aggregation lands just under the $43,389 limit in the 5% bracket; mortgage expense marks the household as owner.
**Expected**: Eligible — $35 (income = $42,000 → 5% bracket; $700 × 0.05 = $35; ≥ $5 floor so payable).
**Steps**:

* Location: ZIP `66502`, county `Riley`
* Household size: `3`, assets: $0
* Person 1: Birth month/year `September 1983` (age 42), `headOfHousehold`, wages: $2,300/month, insurance: none
* Person 2: Birth month/year `February 1986` (age 40), `spouse`, wages: $1,200/month, insurance: none
* Person 3: Birth month/year `April 2012` (age 14), `child`, no income, insurance: none
* Expenses: mortgage $900/month

**Why this matters**: Validates the dependent-child categorical path with non-qualifying adults, household income aggregation across members, the near-limit bracket, the owner-via-mortgage proxy, and the minimum-payout rule.

---

### Scenario 4: Income just below the $43,389 limit

**What we're checking**: A senior homeowner with pension income just under the ceiling remains eligible; pensions count at 100% (unlike Social Security).
**Expected**: Eligible — $35 (income = $43,200 → 5% bracket; $700 × 0.05 = $35).
**Steps**:

* Location: ZIP `66044`, county `Douglas`
* Household size: `1`, assets: $0
* Person 1: Birth month/year `January 1957` (age 69), `headOfHousehold`, pension: $3,600/month, insurance: none
* Expenses: none

**Why this matters**: Income boundary test (just-eligible side) with a 100%-counted income type.

---

### Scenario 5: Income exactly at $43,389

**What we're checking**: The limit is inclusive — the refund table's last eligible bracket runs "to $43,389", so exactly $43,389 qualifies.
**Expected**: Eligible — $35 (top of the 5% bracket).
**Steps**:

* Location: ZIP `66604`, county `Shawnee`
* Household size: `1`, assets: $0
* Person 1: Birth month/year `July 1955` (age 70), `headOfHousehold`, pension: $43,389/year (annual frequency), insurance: none
* Expenses: none

**Why this matters**: Exact-boundary test; ensures the comparison is ≤ $43,389, not < $43,389.

---

### Scenario 6: Income just above the limit

**What we're checking**: Income of $43,500 falls in the table's "$43,390 and over → 0%" row and is correctly rejected.
**Expected**: Not eligible (no value).
**Steps**:

* Location: ZIP `66044`, county `Douglas`
* Household size: `1`, assets: $0
* Person 1: Birth month/year `January 1957` (age 69), `headOfHousehold`, pension: $43,500/year (annual frequency), insurance: none
* Expenses: none

**Why this matters**: Exclusion side of the income boundary; confirms no rounding tolerance above the statutory cap.

---

### Scenario 7: Age boundary — born December 1969

**What we're checking**: The youngest birth date that qualifies via the age path: born December 1969 means 55 for all of 2025.
**Expected**: Eligible — $644 (income = 50% × $14,400 = $7,200 → 92% bracket; $700 × 0.92 = $644).
**Steps**:

* Location: ZIP `67202`, county `Sedgwick`
* Household size: `1`, assets: $0
* Person 1: Birth month/year `December 1969` (age 56), `headOfHousehold`, Social Security retirement: $1,200/month, insurance: none
* Expenses: none

**Why this matters**: Inclusive edge of the birth-year check (`birth_year ≤ 1969`).

---

### Scenario 8: Age boundary — born March 1970 (age 56 at screening, still ineligible)

**What we're checking**: A person who turned 55 *during* 2025 was not 55 the entire claim year and has no other categorical path. They are 56 years old at screening time yet ineligible for the 2025 claim.
**Expected**: Not eligible (no value).
**Steps**:

* Location: ZIP `67202`, county `Sedgwick`
* Household size: `1`, assets: $0
* Person 1: Birth month/year `March 1970` (age 56), `headOfHousehold`, wages: $1,500/month, not disabled, insurance: none
* Expenses: mortgage $750/month

**Why this matters**: The critical off-by-one. This is why the age check must use `birth_year ≤ 1969`, never `age >= 55` — the researcher's original "age exactly 55, born 1971" scenarios got this backwards.

---

### Scenario 9: Disability path with SSDI exclusion

**What we're checking**: A 39-year-old qualifies via the disability path independent of age, and their SSDI is fully excluded from household income — yielding the maximum refund.
**Expected**: Eligible — $700 (SSDI excluded → income $0 → 100% bracket; $700 × 1.00 = $700).
**Steps**:

* Location: ZIP `66044`, county `Douglas`
* Household size: `1`, assets: $0
* Person 1: Birth month/year `September 1986` (age 39), `headOfHousehold`, disabled: yes, Social Security Disability: $1,400/month, insurance: none
* Expenses: none

**Why this matters**: Tests the disability categorical path AND the SSDI income exclusion. A naive gross-income calculation would yield $16,800 → 60% → $420 — a $280 error.

---

### Scenario 10: Senior couple — 50% SS rule across two members

**What we're checking**: Two Social Security incomes are aggregated and the 50% rule applies to the household total.
**Expected**: Eligible — $385 (income = 50% × $33,600 = $16,800 → 55% bracket; $700 × 0.55 = $385).
**Steps**:

* Location: ZIP `66502`, county `Riley`
* Household size: `2`, assets: $0
* Person 1: Birth month/year `March 1955` (age 71), `headOfHousehold`, Social Security retirement: $1,500/month, insurance: none
* Person 2: Birth month/year `June 1958` (age 68), `spouse`, Social Security retirement: $1,300/month, insurance: none
* Expenses: none

**Why this matters**: Validates multi-member SS aggregation, the 50% rule at household level, and a mid-table bracket.

---

### Scenario 11: Property-tax expense below the $700 cap

**What we're checking**: When the Property Taxes expense is entered and annualizes below $700, the allowed tax is the entered amount, not the cap.
**Expected**: Eligible — $528 (income $8,400 → 88%; allowed tax = min($600, $700) = $600; $600 × 0.88 = $528).
**Steps**:

* Location: ZIP `66604`, county `Shawnee`
* Household size: `1`, assets: $0
* Person 1: Birth month/year `March 1958` (age 68), `headOfHousehold`, Social Security retirement: $1,400/month, insurance: none
* Expenses: property taxes $50/month

**Why this matters**: Exercises the expense-driven allowed-tax branch instead of the $700 fallback (compare Scenario 1: same household, $616 vs $528).

---

### Scenario 12: Veteran path via VA-benefits income stream

**What we're checking**: A 45-year-old with no disability flags and no children qualifies categorically through a Veteran's Pension or Benefits income stream (proxy for the disabled-veteran path).
**Expected**: Eligible — $532 (income = $12,000 → 76% bracket; $700 × 0.76 = $532).
**Steps**:

* Location: ZIP `66044`, county `Douglas`
* Household size: `1`, assets: $0
* Person 1: Birth month/year `May 1981` (age 45), `headOfHousehold`, Veteran's Pension or Benefits: $1,000/month, insurance: none
* Expenses: none

**Why this matters**: Tests the VA-stream categorical proxy. Dev note: if the user's VA payment is actually *disability* compensation it should be excluded from income (→ $0 → $700); the stream type cannot distinguish — document the chosen treatment in code comments.

---

### Scenario 13: Child turned 18 during the claim year

**What we're checking**: The dependent-child path requires the child to be under 18 for ALL of 2025. A child born June 2007 turned 18 in June 2025 and does not qualify the household.
**Expected**: Not eligible (no value).
**Steps**:

* Location: ZIP `66502`, county `Riley`
* Household size: `2`, assets: $0
* Person 1: Birth month/year `August 1981` (age 44), `headOfHousehold`, wages: $2,000/month, insurance: none
* Person 2: Birth month/year `June 2007` (age 19), `child`, no income, insurance: none
* Expenses: mortgage $850/month

**Why this matters**: The current-household-composition proxy must still apply the claim-year age test to the child's birth date, not the child's current age alone.

---

### Scenario 14: No categorical path

**What we're checking**: A 50-year-old homeowner with low income, no disability, and no children fails all categorical paths and is rejected despite passing residency, ownership, and income.
**Expected**: Not eligible (no value).
**Steps**:

* Location: ZIP `67202`, county `Sedgwick`
* Household size: `1`, assets: $0
* Person 1: Birth month/year `April 1976` (age 50), `headOfHousehold`, wages: $1,800/month, not disabled, insurance: none
* Expenses: mortgage $800/month

**Why this matters**: Confirms the OR logic requires at least one categorical path — income, residency, and ownership alone are insufficient.

---

### Scenario 15: Sub-$5 refund non-payment (payout floor, non-issuance case)

**What we're checking**: A qualifying senior whose calculated refund falls below $5 receives nothing — KDOR does not issue refunds under $5. Income in the 5% bracket combined with a low entered property-tax expense produces a sub-$5 result.
**Expected**: Not eligible — no value (refund = $96 × 5% = $4.80 → below $5 floor → not issued; ineligible scenarios carry no `value` key).
**Steps**:

* Location: ZIP `66604`, county `Shawnee`
* Household size: `1`, assets: $0
* Person 1: Birth month/year `February 1957` (age 69), `headOfHousehold`, pension: $43,200/year (annual frequency), insurance: none
* Expenses: property taxes $8/month

**Why this matters**: Tests the minimum-payout floor's non-issuance branch. Without this scenario, a calculator that skips the `< $5 → $0` check produces a $4.80 result that would incorrectly show as a payable benefit. The entered `propertyTax` expense ($96/year) also exercises the low-bill path of the allowed-tax calculation.

---

### Scenario 16: Surviving-spouse proxy; `sSSurvivor` and `sSI` income (50% rule — both types)

**What we're checking**: A 51-year-old surviving spouse qualifies categorically via a VA-income stream proxy; both survivor Social Security (`sSSurvivor`) and SSI (`sSI`) income streams are each counted at 50% per the K-40H income rules.
**Expected**: Eligible — $476 (K-40H income: $6,000 veteran [100%] + $4,800 [50% × $9,600 sSSurvivor] + $2,400 [50% × $4,800 sSI] = $13,200 → 68% bracket; $700 × 0.68 = $476).
**Steps**:

* Location: ZIP `66210`, county `Johnson`
* Household size: `1`, assets: $0
* Person 1: Birth month/year `March 1975` (age 51), `headOfHousehold`, income streams:
  - Veteran's Pension or Benefits: $500/month
  - Social Security Survivor: $800/month
  - SSI: $400/month (treated as non-disability SSI → 50% per screener default)
  - insurance: none
* Expenses: none

**Why this matters**: The only scenario that exercises `sSSurvivor` and `sSI` — both explicitly named in criterion 2 as 50%-discounted but absent from all other scenarios. The VA-income stream simultaneously tests the surviving-spouse categorical proxy. A developer applying the 50% rule to a hardcoded type list could silently omit either type without this test catching it.

---

### Scenario 17: Child support and gift income excluded from household income

**What we're checking**: A 65-year-old homeowner receives child support and gift income alongside wages. Both child support and gifts must be fully excluded from K-40H household income (criterion 2) — only the wages count.
**Expected**: Eligible — $700 (K-40H income: $4,800 wages only [child support and gifts excluded] → $0–$6,000 bracket, 100%; $700 × 1.00 = $700). A calculator that wrongly includes the excluded streams would compute income = $4,800 + $21,600 + $3,600 = $30,000 → 5% bracket → $700 × 0.05 = $35 — a $665 error.
**Steps**:

* Location: ZIP `67202`, county `Sedgwick`
* Household size: `1`, assets: $0
* Person 1: Birth month/year `June 1960` (age 65), `headOfHousehold`, income streams:
  - Wages: $400/month
  - Child Support: $1,800/month
  - Gifts: $300/month
  - insurance: none
* Expenses: none

**Why this matters**: Closes the gap flagged during the 2026-07-06/07 completeness sign-off. This is the same failure class as Scenario 9's SSDI exclusion — a rule stated in the spec (child support and gifts excluded) with no scenario forcing a developer to actually implement it. Without this test, a calculator that includes every `income_streams` entry by default would pass every other scenario in this spec while still overcounting income by $25,200 for any household with these income types.

---

### Scenario 18: Blind/visually-impaired categorical path (not `disabled`)

**What we're checking**: A 40-year-old with no qualifying age and no dependent child qualifies via the blind/disability categorical path using the `visually_impaired` screener flag specifically — not the `disabled` boolean already exercised in Scenario 9.
**Expected**: Eligible — $504 (income = $12,600 → 72% bracket; $700 × 0.72 = $504).
**Steps**:

* Location: ZIP `66044`, county `Douglas`
* Household size: `1`, assets: $0
* Person 1: Birth month/year `March 1986` (age 40), `headOfHousehold`, `visually_impaired`: yes, `disabled`: no, `long_term_disability`: no, wages: $1,050/month, insurance: none
* Expenses: none

**Why this matters**: Criterion 1(b)/9 names `visually_impaired`, `disabled`, and `long_term_disability` as equally valid categorical-path proxies, but only `disabled` was exercised (Scenario 9) before this. A developer who hardcodes just one field into the OR-check would pass every other scenario in this spec while silently excluding claimants who are blind or flagged only via `long_term_disability`. K.A.R. 92-22-8 (legal blindness: 20/200 corrected acuity or ≤20° visual field) corroborates this is a genuine, independent categorical path, not a duplicate of the general disability path. `long_term_disability` remains untested — a lower-priority residual gap, noted below rather than closed, since `visually_impaired` and `disabled` together already prove the OR-logic isn't hardcoded to a single field.

---

### Scenario 19: Dependent child's income excluded from household income (K.A.R. 92-22-11)

**What we're checking**: A dependent child living in the household has part-time wage income that must be excluded from K-40H household income under K.A.R. 92-22-11, since the child holds no title to the homestead and isn't party to any rental agreement.
**Expected**: Eligible — $700 (K-40H income: $6,000 head-of-household wages only [child's wages excluded] → $0–$6,000 bracket, 100%; $700 × 1.00 = $700). A calculator that wrongly includes the child's income would compute $6,000 + $3,600 = $9,600 → 84% bracket → $700 × 0.84 = $588 — a $112 error.
**Steps**:

* Location: ZIP `66502`, county `Riley`
* Household size: `2`, assets: $0
* Person 1: Birth month/year `August 1965` (age 60), `headOfHousehold`, wages: $500/month, insurance: none
* Person 2: Birth month/year `June 2009` (age 16), `child`, wages: $300/month (part-time job), insurance: none
* Expenses: none

**Why this matters**: Closes a gap surfaced during the 2026-07-07 citation-verification pass — K.A.R. 92-22-11 was added to Criterion 2 in the prior round but never exercised by a scenario, the same failure class as Scenario 17: a documented income-exclusion rule with zero test coverage is indistinguishable from an unimplemented one until a scenario forces the point.

---

### Scenario 20: Long-term-disability categorical path (not `disabled` or `visually_impaired`)

**What we're checking**: A 35-year-old with no qualifying age and no dependent child qualifies via the disability categorical path using the `long_term_disability` screener flag specifically — the third and last of the three proxy fields named in Criterion 1(b)/9, closing out the residual gap left open after Scenario 18.
**Expected**: Eligible — $448 (income = $14,400 → 64% bracket; $700 × 0.64 = $448).
**Steps**:

* Location: ZIP `66044`, county `Douglas`
* Household size: `1`, assets: $0
* Person 1: Birth month/year `July 1990` (age 35), `headOfHousehold`, `long_term_disability`: yes, `disabled`: no, `visually_impaired`: no, wages: $1,200/month, insurance: none
* Expenses: none

**Why this matters**: Completes what Scenario 18 started. With `disabled` (Scenario 9), `visually_impaired` (Scenario 18), and now `long_term_disability` each independently exercised, a developer can no longer hardcode any subset of the three proxy fields into the categorical-path OR-check without a scenario catching it — the risk flagged in Scenario 18 as "lower-priority residual" is now fully closed rather than left open.

---

**Coverage map**: age path (1, 7, 8), disability path (9, 18, 20 — all three proxy fields independently tested), child path (3, 13), veteran proxy (12), surviving-spouse proxy + `sSSurvivor` + `sSI` 50% rule (16 — surviving-spouse without VA income is a documented under-inclusive gap, not a testable code path), no path (14), income boundary (4, 5, 6), 50% SS rule — `sSRetirement` (1, 10), SSDI exclusion (9), child-support/gifts exclusion (17), dependent-minor income exclusion (19), owner/renter gate (2, 3, 11), allowed-tax branches (1, 11), payout floor — above floor (3), payout floor — non-issuance (15).

**Known scenario gaps (updated 2026-07-07 — all four closed, zero residual):** ~~no scenario exercises the child-support/gifts income exclusion~~ — closed by Scenario 17. ~~only the `disabled` proxy field is exercised~~ — closed: Scenario 18 added `visually_impaired`, Scenario 20 added `long_term_disability`; all three disability-categorical proxy fields now have independent coverage. ~~K.A.R. 92-22-11's dependent-minor income exclusion (added to criterion 2 in the third verification round) had no scenario~~ — closed by Scenario 19. Data-gap criteria with no screener field (5, 6, 7, 10, 13, 14) have no dedicated scenario by design; that's expected, not a coverage failure, since nothing in the screener can drive a test for a statute-only, non-screener-evaluable bar. The Railroad Retirement disability exclusion (criterion 2) has no scenario because no matching screener income type exists — not a coverage gap, a moot rule (see criterion 2 note). The tenancy-in-common proration nuance (criterion 4 / Benefit Value) has no scenario by design, consistent with the pre-existing rental/business-use and mid-year-move simplifications it sits alongside — all three are documented "known simplifications," not tested branches.

## Implementation Coverage

- ✅ Evaluable criteria: 4 (categorical paths a–c; income limit with adjustments; current KS residency; homeownership via documented expense-based proxy, now broadened to cover trusts/life estates and manufactured homes)
- ⚠️ Data gaps: 10 (criteria 5–14), all with explicit inclusivity assumptions above. Two added 2026-07-06 (criteria 13, 14 — statute-only anti-abuse/anti-double-dip bars found by reading K.S.A. 79-4501–4523 in full; absent from the KDOR page, FAQ, and booklet).
- 💡 Proposed screener improvements: (1) `housing_situation` own/rent question (criterion 4); (2) military-connection tile with veteran / surviving-spouse follow-up (criterion 8 — pattern case: K-40SVR). Considered and rejected: home value question (privacy-sensitive — criterion 5 handled via description)

The three highest-impact criteria — categorical eligibility, the income limit, and homeownership — are evaluable or reasonably proxied. The most consequential data gap is the $350,000 home value cap, which is surfaced in the program description.

## Research Sources

- [Kansas Department of Revenue — Kansas Homestead Refund Programs](https://www.ksrevenue.gov/perstaxtypeshs.html)
- [2025 Homestead or Property Tax Refund for Homeowners Booklet (K-40H instructions)](https://www.ksrevenue.gov/pdf/k-40hbook25.pdf)
- [Kansas Department of Revenue — Homestead Frequently Asked Questions](https://www.ksrevenue.gov/faqs-taxhomestead.html)
- [2025 Kansas Homestead Claim Form K-40H](https://www.ksrevenue.gov/pdf/k-40h25.pdf)
- [K.S.A. 79-4501](https://www.ksrevisor.gov/statutes/chapters/ch79/079_045_0001.html) — Homestead Property Tax Refund Act: title, purpose, amendment history (renter-repeal citation: L. 2012, ch. 135, § 30)
- [K.S.A. 79-4502](https://ksrevisor.gov/statutes/chapters/ch79/079_045_0002.html) — Homestead Property Tax Refund Act: Definitions (homestead, household, household income, "owned" incl. trusts/life estates, disabled veteran, claimant)
- [K.S.A. 79-4507](https://www.ksrevisor.gov/statutes/chapters/ch79/079_045_0007.html) — one claim per household per year (sibling-program mutex)
- [K.S.A. 79-4508](https://www.ksrevisor.gov/statutes/chapters/ch79/079_045_0008.html) — CPI indexing of the income limit
- [K.S.A. 79-4508a](https://www.ksrevisor.gov/statutes/chapters/ch79/079_045_0008a.html) — base-year refund mechanism for seniors/disabled veterans (sibling program; note: the statute itself doesn't use the label "K-40SVR" — that's KDOR's administrative form name for this mechanism, confirmed 2026-07-07; the substance — base-year definition, $50,000 income limit, $350,000 home-value limit — matches K-40SVR exactly)
- [K.S.A. 79-4509](https://www.ksrevisor.gov/statutes/chapters/ch79/079_045_0009.html) — $700 refund cap
- [K.S.A. 79-4515](https://www.ksrevisor.gov/statutes/chapters/ch79/079_045_0015.html) — public-tax-fund-recipient bar (criterion 13)
- [K.S.A. 79-4516](https://www.ksrevisor.gov/statutes/chapters/ch79/079_045_0016.html) — anti-abuse title-acquisition bar (criterion 14)
- [K.S.A. 79-4517](https://www.ksrevisor.gov/statutes/chapters/ch79/079_045_0017.html) — 4-year good-cause late-filing exception
- [K.S.A. 79-4522](https://www.ksrevisor.gov/statutes/chapters/ch79/079_045_0022.html) — $350,000 home value cap (controlling statute; criterion 5)
- [K.S.A. 79-4523](https://www.ksrevisor.gov/statutes/chapters/ch79/079_045_0023.html) — delinquent-tax redirection
- [K.A.R. 92-22-4](https://www.law.cornell.edu/regulations/kansas/K-A-R-92-22-4) — domicile / temporary absence (criterion 10)
- [K.A.R. 92-22-5](https://www.law.cornell.edu/regulations/kansas/K-A-R-92-22-5) — homestead used for rental/business purposes (corroborates Benefit Value proration note)
- [K.A.R. 92-22-8](https://www.law.cornell.edu/regulations/kansas/K-A-R-92-22-8) — proof of disability, legal-blindness threshold (corroborates criterion 9)
- [K.A.R. 92-22-11](https://www.law.cornell.edu/regulations/kansas/K-A-R-92-22-11) — household income exclusion for a dependent minor/incapacitated member without title or rental-agreement interest (criterion 2)
- [K.A.R. 92-22-12](https://www.law.cornell.edu/regulations/kansas/K-A-R-92-22-12) — ownership definitions incl. statutory inchoate spousal interest and tenancy-in-common proration (criterion 4)
- [K.S.A. 59-505](https://www.ksrevisor.gov/statutes/chapters/ch59/059_005_0005.html) — "Surviving spouse entitled to 1/2 of real estate," the inchoate spousal interest referenced by K.A.R. 92-22-12 (criterion 4)
- [K.A.R. 92-22-33](https://www.law.cornell.edu/regulations/kansas/K-A-R-92-22-33) — dependent-child requirements (corroborates criteria 1(c)/12)
- [K.A.R. 92-22, full article](https://www.law.cornell.edu/regulations/kansas/agency-92/article-22) — table of contents; individual section links above verified 2026-07-07 (URL pattern: `law.cornell.edu/regulations/kansas/K-A-R-92-22-{N}`)
- [38 U.S.C. § 1101](https://www.law.cornell.edu/uscode/text/38/1101) — VA disability-compensation definitions (criterion 8)
- [10 U.S.C. § 1201](https://www.law.cornell.edu/uscode/text/10/1201) — armed-forces disability-retirement standard (criterion 8)
- [HB 2074](https://kslegislature.gov/li/b2025_26/measures/hb2074/) / [SB 455](https://www.kslegislature.gov/li/b2025_26/measures/sb455/) — 2026-session bills to restore Homestead renter eligibility; both independently confirmed died in House/Senate committee (verified 2026-07-07)
- HB 2231 § 11 (2025 session) / KDOR Notice 25-05 (July 3, 2025) — confirms K-40SVR-only household-income redefinition (KAGI); K-40H unaffected
- [Saline County KDOR Tax Training Series (Homestead)](https://www.salinecountyks.gov/media/Treasurer/2019-homestead-power-point.pdf) — confirms "Form ELG" is the eligibility letter KDOR sends to a claimant's County Treasurer for prior-year Refund Advancement Program participants (Benefit Value known simplification)

*Full statutory read (K.S.A. 79-4501 through 79-4523, confirming 79-4512/4514/4518/4520 repealed and 79-4524–4529 reserved) completed 2026-07-06 as part of the eligibility-completeness sign-off — see criteria 13–14 and the ownership/manufactured-home notes in criterion 4. Regulatory-layer pass (K.A.R. 92-22, the two previously-unread KDOR legislative documents, and a 2026-session legislative-activity check) completed 2026-07-07 — see criteria 2, 4, and 10, and the Dev Notes K-40SVR income-methodology note. Direct page-image read of the full 16-page 2025 booklet and all four claim/certification forms (K-40H, K-40PT, K-40SVR, Schedule DIS) completed 2026-07-08 — caught the agricultural/commercial-land and Farm Owners property-tax exclusions (Benefit Value), three additional excluded-income categories (Food Stamps, Settlements, Personal/Student Loans — criterion 2), the undocumented "Form ELG" refund-reduction note (Benefit Value), and the concrete SGA income thresholds for physician-certified disability (criterion 9) — all missed by prior text-extraction-based reads of the same document.*
