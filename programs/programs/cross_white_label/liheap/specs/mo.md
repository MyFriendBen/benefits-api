# Low Income Home Energy Assistance Program (LIHEAP) (MO) — Program Spec

- **Program key**: `mo_liheap` (`programs/programs/cross_white_label/liheap/mo.py`, class `MoLiheap`)
- **Base federal program**: LIHEAP (`base_program: "liheap"`)
- **White label**: MO
- **Engine**: MFB custom
- **Added to MFB**: implemented
- **Spec last updated**: 2026-08-21
- **Sources verified as of**: 2026-08-21

## Covered Eligibility Criteria

1. **Household countable monthly income is at or below 60% of Missouri's State Median Income for the household size**
   - Evaluation scope: household
   - Captured via: `Screen.household_size` (Screen, IntegerField); `Screen.calc_gross_income` (accessor) over countable income types, monthly.
   - Limit table (monthly income, 60% SMI), carried as a program constant:

     | Size | Limit | | Size | Limit |
     |---|---|---|---|---|
     | 1 | $2,840 | | 6 | $7,209 |
     | 2 | $3,714 | | 7 | $7,373 |
     | 3 | $4,588 | | 8 | $7,537 |
     | 4 | $5,461 | | 9 | $7,701 |
     | 5 | $6,335 | | 10 | $7,864 |

     Above size 10: +$164 per additional member.
   - Countable income = gross income less the exclusions and deductions below. The criterion is not evaluated when `household_size` is null.
   - **MFB limitation — household-size cap.** The live MFB household-size field caps entries at 8 (`.lte(8)`), so sizes 9 and above cannot be entered through the current screener. Table rows 9 and 10, and the +$164 increment above 10, are consequently unreachable and unexercised by any scenario — a regression in either would go undetected until the intake cap changes. Sizes 1 through 8 remain fully reachable and are pinned below.
   - **MFB limitation — income timing (Divergence D5, committed exception to the inclusive-gap rule).** Missouri budgets the calendar month **preceding** the application month — `Determine all gross earned and unearned income less the allowable income` exclusions for that month — while MFB evaluates currently-reported income. The screener records no income period at all, so the two cannot be reconciled: a household whose income rose this month is counted higher than Missouri would count it, and one whose income fell is counted lower.
     - **Committed handling**: currently-reported income is used as the household's income, without adjustment. No inclusive handling exists short of abandoning the income test, because the screener holds no second income figure to fall back to and no date to compare against.
     - This is a **platform-level MFB limitation** — it applies wherever MFB models a prior-month-budgeted benefit — and not a Missouri-specific policy assumption.
   - Source: LIHEAP Policy and Procedure Manual, Income Determination — `Determine all gross earned and unearned income less the allowable income` exclusions for the month prior to the application month — [snapshot `2026-08-20--modss-liheap-policy-procedure-manual`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-policy-procedure-manual/content.md), accessed 2026-08-20
   - Source: MyDSS Benefit Program Income Limits, `As of 04/01/2026`, Low Income Home Energy Assistance Program row ($2,840 through $7,537 for household sizes 1–8 at State Median Income 60%) — [snapshot `2026-08-20--modss-benefit-program-income-limits`](../../../sources/mo/mo_liheap/2026-08-20--modss-benefit-program-income-limits/content.md), accessed 2026-08-20
   - Source: FFY2026 application, revision MO 886-4576 (9-2025), Program Description — `0%-60% STATE MEDIAN INCOME (SMI)`, `1                             2,840`, `9                             7,701`, `10                            7,864`, and `more than 10 members, add $164` — [snapshot `2026-08-20--modss-liheap-application-form`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-application-form/content.md), accessed 2026-08-20
   - Source: FFY2026 Model State Plan §2.1 — `All Household Sizes                                    State Median Income                                                 60.00%` — [snapshot `2026-08-20--mo-liheap-model-state-plan-ffy2026`](../../../sources/mo/mo_liheap/2026-08-20--mo-liheap-model-state-plan-ffy2026/content.md), accessed 2026-08-20
   - **Source conflict — income limit figures.** The 2026 FPL Chart for all Programs PDF, linked from the MyDSS page, gives lower figures — `"Low Income Home Energy Assistance Program"           "$2,535"` — [snapshot `2026-08-20--modss-2026-fpl-chart-all-programs`](../../../sources/mo/mo_liheap/2026-08-20--modss-2026-fpl-chart-all-programs/content.md), accessed 2026-08-20. **Committed interpretation**: the MyDSS page's figures govern, because the FFY2026 application independently corroborates them.
     - The MyDSS page's own note reads `add $163 to the maximum monthly income for each household member` for sizes over 6, but its table increments by $164 ($7,209 → $7,373) and the application states $164 — **$164 governs**.
     - A second, deeper conflict sits in the regulation itself: 13 CSR 40-19.020(6)(D) requires each household to meet the `fied income guidelines based on their house-` hold size established in section (14) of that rule, and (14) sets Federal Poverty Level bands topping out at 126–135% — a materially lower standard than 60% SMI. **Committed interpretation**: the 2017 rule predates Missouri's current election; the FFY2026 Model State Plan, the FFY2026 application and the MyDSS page all carry 60% SMI, and 42 U.S.C. §8624(b)(2) authorises it, so the current 60% SMI standard governs — [snapshot `2026-08-20--13-csr-40-19-020`](../../../sources/mo/mo_liheap/2026-08-20--13-csr-40-19-020/content.md), accessed 2026-08-20.

   **Income exclusions** (applied before the deductions below).
   - Earned income of any household member under 18 is excluded; their SSA income still counts. Captured via `HouseholdMember.calc_age` (accessor) with `Screen.calc_gross_income` restricted to members 18 and over for `["wages", "selfEmployment", "boarder"]` — the same set Deduction 1 uses, since Missouri's earned-income definition includes roomer-boarder income.
   - Interest and dividend income is excluded. Captured via `Screen.calc_gross_income` excluding the `investment` and `deferredComp` income types.
   - Missouri's other exclusions are narrow sub-cases of income types it otherwise counts — `gifts`, `cashAssistance` and `veteran` income are all countable here (the manual documents `Monetary assistance from family-friends or stipend`, `BP, SAB, and TANF:` and `Veterans Administration Disability Benefits` as countable income), so none of those types is excluded wholesale. The excluded sub-cases are recorded in data gap 7.
   - The under-18 rule covers earned income only: Missouri's own sentence continues that unearned income from disability `should not be included but SSA income` should be, and MFB has no income type representing non-SSA disability income for a minor — `sSDisability` and `sSI` are both SSA income and stay countable. That residue is also in data gap 7.
   - Source: LIHEAP Policy and Procedure Manual, Income Exclusions — `Earned income received from a household member under the age` of 18 should not be included as household income, and `Interest-Dividend Income` covering annuities, CDs, IRAs, Keoghs and deferred compensation plans, savings and checking accounts, bonds, and dividends from stocks or mutual funds — [snapshot `2026-08-20--modss-liheap-policy-procedure-manual`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-policy-procedure-manual/content.md), accessed 2026-08-20

   **Deduction 1 — 20% of earned income.**
   - Evaluation scope: household
   - Captured via: `Screen.calc_gross_income` (accessor) over `["wages", "selfEmployment", "boarder"]`, monthly, × 0.20
   - Source: LIHEAP Policy and Procedure Manual, Income Deductions, `Earned Income Deduction of 20%` — `This deduction applies to employment income including wages,` vacation pay, regular bonuses, overtime, tips, sick leave, maternity leave, roomer-boarder, and self-employment income — [snapshot `2026-08-20--modss-liheap-policy-procedure-manual`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-policy-procedure-manual/content.md), accessed 2026-08-20

   **Deduction 2 — $100 medical deduction where the applicant or spouse is age 65 or older, or has a disability. Once per household.**
   - Evaluation scope: household (tested against the head and spouse only)
   - Captured via: `HouseholdMember.calc_age` (accessor), `HouseholdMember.has_disability` (accessor), `HouseholdMember.is_head` / `.is_spouse` (accessors)
   - Age granularity: MFB collects birth year and month, not day, and treats a member as having reached 65 throughout their birth month. Missouri is stricter — `The member must turn 65 prior to the date the case` shows as registered — so MFB may grant the deduction slightly earlier. **Inclusive.**
   - Disability definition: 13 CSR 40-19.020(2)(C) defines a disabled individual as one `vidual who is totally and permanently disabled` or blind **and** receiving one of a named list of benefits (Social Security Disability, SSI, Railroad Retirement Disability, State Aid to the Blind, VA Disability and others) — the manual restates this narrow definition operationally and limits documentation to a closed list of benefit evidence, so it is the rule in practice as well as on paper. `HouseholdMember.has_disability` is self-reported and carries no benefit-receipt condition, so MFB grants this deduction to households Missouri might not. **Inclusive.**
   - Source: 13 CSR 40-19.020(2)(C) — `vidual who is totally and permanently disabled` or blind and receiving one or more of the listed benefits — [snapshot `2026-08-20--13-csr-40-19-020`](../../../sources/mo/mo_liheap/2026-08-20--13-csr-40-19-020/content.md), accessed 2026-08-20
   - Source: LIHEAP Policy and Procedure Manual, Medical Deduction for Elderly-Disabled — `applicant or spouse is elderly (age 65 or older) or disabled.` and `The system allows only one $100 deduction, even if both applicant` and spouse meet criteria — [snapshot `2026-08-20--modss-liheap-policy-procedure-manual`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-policy-procedure-manual/content.md), accessed 2026-08-20

   **Deduction 3 — child support paid to someone outside the household.**
   - Evaluation scope: household
   - Captured via: `Screen.calc_expenses` (accessor) over `["childSupport"]`, monthly
   - Source: LIHEAP Policy and Procedure Manual, Child Support Payments — `All child support payments (except for lump sum payments) paid by` any household member to someone not included in the LIHEAP household — [snapshot `2026-08-20--modss-liheap-policy-procedure-manual`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-policy-procedure-manual/content.md), accessed 2026-08-20

   **Deduction 4 — $202.90 per month for each household member who has Medicare.**
   - Evaluation scope: member
   - Captured via: `HouseholdMember.has_insurance` (accessor) with `"medicare"`, backed by `Insurance.medicare` (Insurance, BooleanField)
   - Missouri deducts the member's actual SMI premium, and only where the member pays it rather than being in Medicare buy-in. The screener captures neither the premium amount nor buy-in status, so this spec commits to the CMS standard 2026 Part B premium as a conservative approximation. It over-deducts for buy-in households, which admits households rather than excluding them; it is not a claim that any individual pays this amount.
   - Missouri also conditions the deduction on case category — `Allowable for all household members of a B or C case who are` paying this premium, and only on a Category A case where income exceeds the maximum allowed. MFB applies it unconditionally, which is the same inclusive direction.
   - Source: LIHEAP Policy and Procedure Manual, SMI Premium — `SMI is an additional health cost that is available to persons receiving` SS and RRB — [snapshot `2026-08-20--modss-liheap-policy-procedure-manual`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-policy-procedure-manual/content.md), accessed 2026-08-20
   - Source: CMS, Medicare Deductible, Coinsurance & Premium Rates CY 2026 Update (MM14279) — `Part B standard premium: $202.90 a month` — [snapshot `2026-08-20--cms-medicare-premium-rates-cy2026`](../../../sources/mo/mo_liheap/2026-08-20--cms-medicare-premium-rates-cy2026/content.md), accessed 2026-08-20

2. **Household is responsible for its home energy costs**
   - Evaluation scope: household
   - Captured via: `Screen.has_expense` (accessor) over `["rent", "mortgage", "heating", "cooling", "otherUtilities"]`
   - This is a proxy. Missouri requires an account in a household member's name, or a qualifying renter/landlord arrangement, plus actual heating or cooling costs. A housing or utility expense is broader — a household whose landlord bears the energy cost with no pass-through has rent but no responsibility, and will be shown as eligible. **Inclusive.**
   - Source: 13 CSR 40-19.020(6)(C) — each household must have an account in their name or meet the definition of a renter/landlord household and be `incurring heat-` ing/cooling costs — [snapshot `2026-08-20--13-csr-40-19-020`](../../../sources/mo/mo_liheap/2026-08-20--13-csr-40-19-020/content.md), accessed 2026-08-20
   - Source: MyDSS LIHEAP page, Who is eligible — `Are responsible for paying the utilities for your home (including if you rent)` — [snapshot `2026-08-20--modss-liheap-overview`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-overview/content.md), accessed 2026-08-20

3. **The applicant is a U.S. citizen or a qualified non-citizen**
   - Evaluation scope: config
   - Captured via: `legal_status_required` = `["citizen", "gc_5plus", "gc_5less", "refugee", "otherWithWorkPermission"]`
   - Missouri checks qualifying status for household members, but only the applicant's non-qualifying status makes the case ineligible. Other non-qualifying members are excluded from the household count while their available income still counts — see data gap 6, since the screener collects no per-member immigration status.
   - `gc_5less` is included because lawful permanent residents qualify regardless of how long they have held that status. `refugee` and `otherWithWorkPermission` carry the refugee, asylee and parolee classes Missouri documents via an annotated I-94, and COFA citizens, whom the manual names as qualified non-citizens.
   - Source: LIHEAP Policy and Procedure Manual, Citizenship — `If the individual claiming they are not a citizen is the applicant, the case will be` determined ineligible, and `Exclude individuals not meeting these criteria from the household count.` — [snapshot `2026-08-20--modss-liheap-policy-procedure-manual`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-policy-procedure-manual/content.md), accessed 2026-08-20
   - Source: ACF LIHEAP IM 1998-25 — `all qualified aliens, regardless of when they entered the U.S., continue` to be eligible to receive assistance and services under LIHEAP if they meet other program requirements — [snapshot `2026-08-20--acf-liheap-im-1998-25-federal-public-benefits`](../../../sources/mo/mo_liheap/2026-08-20--acf-liheap-im-1998-25-federal-public-benefits/content.md), accessed 2026-08-20
   - **Source conflict — qualifying non-citizen classes.** 13 CSR 40-19.020(6)(A) names only two qualifying classes — `All household members must be a cit`izen of the United States or a legal permanent resident — [snapshot `2026-08-20--13-csr-40-19-020`](../../../sources/mo/mo_liheap/2026-08-20--13-csr-40-19-020/content.md), accessed 2026-08-20. **Committed interpretation**: the manual's I-94 annotation list and COFA paragraph, backed by ACF IM 1998-25, supply the classes the regulation's two-class sentence omits.

4. **Household resides in Missouri**
   - Evaluation scope: household
   - Captured via: `Screen.zipcode` (Screen, CharField) against `MoConfigurationData.counties_by_zipcode` (`configuration/white_labels/mo.py`, 1,126 Missouri ZIPs)
   - An out-of-state mailing address does not disqualify a household whose physical residence is in Missouri; `Screen.zipcode` asks where the household lives, so it matches the rule. A null `zipcode` is treated as met rather than failing closed, consistent with the inclusive handling of every other unobservable condition here.
   - **MFB limitation — platform-enforced, untestable.** The Missouri screener's own ZIP-entry step is gated on `MoConfigurationData.counties_by_zipcode` before submission, so a non-Missouri ZIP is rejected at intake and never reaches this criterion. Residency is therefore platform-enforced as well as modelled here; no calculator-negative scenario is possible, and a regression in this criterion's own check would not be caught by any scenario.
   - Source: MyDSS LIHEAP page, Who is eligible — `Are a Missouri resident` — [snapshot `2026-08-20--modss-liheap-overview`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-overview/content.md), accessed 2026-08-20

5. **The household includes a member old enough to be the applicant**
   - Evaluation scope: household
   - Captured via: `HouseholdMember.calc_age` (accessor) — at least one member aged 15 or older
   - Missouri expects an applicant aged 18 or over, and allows a member aged 15 to 17 to apply where no adult is in the household. Only the under-15 case is an outright denial, so that is the line this criterion draws.
   - Source: LIHEAP Policy and Procedure Manual, Application — `Applicants should be an individual that is age eighteen (18) or over` and residing in the household, with applicants between 15 and 18 accepted where there is no other member over 18, and `If the applicant is under the age of fifteen (15), the application will be denied.` — [snapshot `2026-08-20--modss-liheap-policy-procedure-manual`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-policy-procedure-manual/content.md), accessed 2026-08-20

## Missing Eligibility Criteria (Data Gaps)

1. **Household resources may not exceed $3,000**
   - **Why**: `Screen.household_assets` is not Missouri's countable-resource figure in either direction. It omits resources Missouri counts (certificates of deposit, IRAs, Keoghs and deferred compensation, money markets) and includes funds Missouri exempts (Medicare Set-Aside accounts, FEMA disaster relief) as well as resources documented as restricted or inaccessible.
   - **Handling**: assumed met, and not evaluated. **Inclusive** — applying the field directly would exclude households Missouri would find eligible. The limit is surfaced in the program description.
   - Source: MyDSS LIHEAP page, Who is eligible — `Have $3,000 or less in your bank accounts, retirement accounts, or investments` — [snapshot `2026-08-20--modss-liheap-overview`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-overview/content.md), accessed 2026-08-20
   - Source: 13 CSR 40-19.020(6)(B) — resources may not `exceed three thousand dollars ($3,000);` — [snapshot `2026-08-20--13-csr-40-19-020`](../../../sources/mo/mo_liheap/2026-08-20--13-csr-40-19-020/content.md), accessed 2026-08-20

2. **Missouri's household definition — private living quarters, one meter and one bill, one residence per year**
   - **Why**: the screener has no field for shared metering, private-entrance living quarters, or a second residence.
   - **Handling**: assumed met. `Screen.household_size` is used as given. **Inclusive** — admits households that share a meter with another household. Missouri also limits a multiply-named fuel account to one recipient, which the screener cannot see either.
   - Source: LIHEAP Policy and Procedure Manual, Household — `Household is defined as an individual(s) living in private living quarters` for which residential heat-cooling is purchased in common — [snapshot `2026-08-20--modss-liheap-policy-procedure-manual`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-policy-procedure-manual/content.md), accessed 2026-08-20
   - Source: LIHEAP Policy and Procedure Manual, Ineligible Individuals-Households — `Only one individual on a multiple named fuel bill account will be eligible` to receive LIHEAP benefits — [snapshot `2026-08-20--modss-liheap-policy-procedure-manual`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-policy-procedure-manual/content.md), accessed 2026-08-20
   - Source: FFY2026 application, revision MO 886-4576 (9-2025) — `1 bill + 1 meter = 1 Household` — [snapshot `2026-08-20--modss-liheap-application-form`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-application-form/content.md), accessed 2026-08-20

3. **Living situations that make a household ineligible**
   - **Why**: Missouri excludes households in a nursing or boarding home, a hotel, motel, dormitory or temporary shelter, or government-subsidized housing, unless the household pays an energy supplier or landlord directly for heating or cooling; households in transitional living whose energy is paid by the Department of Mental Health; and households in a recreational vehicle, travel trailer, tent or shed at the same address as, and sharing a meter or power source with, a household that has already received EA this fiscal year. `Screen.housing_situation` (Screen, CharField) distinguishes renting, owning and homelessness but carries no subsidy, institutional, or direct-payment dimension.
   - **Handling**: assumed met. **Inclusive** — households in these situations are shown as eligible.
   - Source: LIHEAP Policy and Procedure Manual, Ineligible Individuals-Households — `Consider households meeting the following conditions ineligible:` including `Resides in a professional, practical, or domiciliary nursing or boarding home`, `Resides in a hotel, motel, dormitory or temporary shelter and does not pay` a home energy supplier directly, `In a transitional living situation.`, and `Residing in a recreational vehicle, travel trailer, tent or shed residing at the` same address and sharing power — [snapshot `2026-08-20--modss-liheap-policy-procedure-manual`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-policy-procedure-manual/content.md), accessed 2026-08-20
   - Source: 13 CSR 40-19.020(7)(H) — an RV, travel trailer, tent or shed at the same address `as, and sharing the same meter or source of` power with a household that has already received EA in the current LIHEAP fiscal year — [snapshot `2026-08-20--13-csr-40-19-020`](../../../sources/mo/mo_liheap/2026-08-20--13-csr-40-19-020/content.md), accessed 2026-08-20
   - Source: FFY2026 Model State Plan §2.3 — `Only eligible if the client is paying an energy supplier out-of-pocket.` — [snapshot `2026-08-20--mo-liheap-model-state-plan-ffy2026`](../../../sources/mo/mo_liheap/2026-08-20--mo-liheap-model-state-plan-ffy2026/content.md), accessed 2026-08-20

4. **A fuel-supplier credit balance over $500 makes a household ineligible, unless it pre-pays for fuel**
   - **Why**: the screener collects no utility account balance, and no pre-payment arrangement.
   - **Handling**: assumed met. **Inclusive.**
   - Source: LIHEAP Policy and Procedure Manual, Ineligible Individuals-Households — `Has a credit balance with their fuel supplier in excess of $500.` and `This will not apply to households that pre-pay for their fuel.` — [snapshot `2026-08-20--modss-liheap-policy-procedure-manual`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-policy-procedure-manual/content.md), accessed 2026-08-20

5. **A household that cuts its own wood, where wood is its primary heating source, is ineligible**
   - **Why**: the screener collects no primary heating fuel, so it cannot identify wood-heating households, let alone self-supplied ones.
   - **Handling**: assumed met. **Inclusive.**
   - Source: LIHEAP Policy and Procedure Manual, Ineligible Individuals-Households — `Cut their own wood.` — [snapshot `2026-08-20--modss-liheap-policy-procedure-manual`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-policy-procedure-manual/content.md), accessed 2026-08-20
   - Source: 13 CSR 40-19.020(7)(G) — a household that cuts its own wood, `when wood is the household` 's primary source of heating — [snapshot `2026-08-20--13-csr-40-19-020`](../../../sources/mo/mo_liheap/2026-08-20--13-csr-40-19-020/content.md), accessed 2026-08-20

6. **Individuals excluded from the household while their income still counts**
   - **Why**: Missouri drops non-qualified non-citizens, incarcerated people, roomers, boarders and live-in attendants, the deceased, and people not living in the home at application from the household count, while still counting income they make available to the household. The screener collects no per-member immigration status, incarceration status, or roomer/boarder role, so neither the count adjustment nor the income treatment can be reproduced.
   - **Handling**: `Screen.household_size` is used as given and all reported income is counted. Missouri drops excluded individuals from the count while MFB keeps them, so MFB's household size — and therefore its income limit — is the larger of the two. **Inclusive.**
   - Source: LIHEAP Policy and Procedure Manual, Citizenship — `Exclude individuals not meeting these criteria from the household count.` — [snapshot `2026-08-20--modss-liheap-policy-procedure-manual`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-policy-procedure-manual/content.md), accessed 2026-08-20

7. **Narrow income exclusions that sit inside otherwise-countable income types**
   - **Why**: each of these is a sub-case of an MFB income type whose ordinary content Missouri counts, so the screener cannot separate them:
     - Birthday and Christmas gifts, and student cash gifts or awards — inside `gifts`
     - Veteran's educational benefits — inside `veteran`
     - Payments or allowances under Federal, State or Local law for Energy Assistance, including HUD rent-utility subsidies — inside `cashAssistance`
     - Work study (the screener flags `HouseholdMember.student_has_work_study` but records no separate amount), Foster Grandparents/VISTA/AmeriCorps compensation, and income under Title V of the Older Americans Act — inside `wages`
     - Unearned non-SSA disability income of a member under 18, for which MFB has no income type at all (`sSDisability` and `sSI` are SSA income, which Missouri counts)
     - Lump-sum payments, relocation payments and Nazi-persecution victim payments — no MFB income type for any of these
     - (Missouri's Interest-Dividend list also names IRAs and Keoghs, but those are already excluded — MFB's `deferredComp` type is labelled "Withdrawals from Deferred Compensation (IRA, Keogh, etc.)" and criterion 1 excludes it.)
   - **Handling — committed, approved exception to the inclusive-gap rule (Divergence D6)**: all of these are counted, because excluding the whole enclosing type would remove income Missouri plainly counts — TANF, VA disability benefits, ordinary contributions and wages. **Exclusive** — a household living on Title V or AmeriCorps stipends, or a minor's non-SSA disability income, will show a higher countable income than Missouri would find. The inclusive alternative (excluding the whole enclosing income type) was considered and rejected, because it would drop income Missouri plainly counts and produce a larger, less predictable error in the other direction.
   - Source: LIHEAP Policy and Procedure Manual, Miscellaneous Exclusions — `Compensation provided to volunteers in the Foster Grandparents` Program, VISTA, or the AmeriCorps Program, and `Income received under Title V of the Older Americans Act` — [snapshot `2026-08-20--modss-liheap-policy-procedure-manual`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-policy-procedure-manual/content.md), accessed 2026-08-20

8. **Energy Assistance is paid once per household per program year**
   - **Why**: the screener records no prior LIHEAP receipt, and Missouri also excludes members already approved for EA elsewhere, or moving into a household that has already received EA this year at the same address.
   - **Handling**: assumed no prior receipt. **Inclusive** — a household already paid this program year is still shown as eligible.
   - Source: 13 CSR 40-19.020(4) — not more than one EA benefit per eligible household `during any LIHEAP fiscal year` — [snapshot `2026-08-20--13-csr-40-19-020`](../../../sources/mo/mo_liheap/2026-08-20--13-csr-40-19-020/content.md), accessed 2026-08-20
   - Source: LIHEAP Policy and Procedure Manual, Ineligible Individuals-Households — `Members that have already been approved and received EA` or individuals moving into a household that has already received EA in the current program year at the same address — [snapshot `2026-08-20--modss-liheap-policy-procedure-manual`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-policy-procedure-manual/content.md), accessed 2026-08-20

9. **The excess-income crisis exception**
   - **Why**: Missouri re-computes income, excluding a terminated income stream, for a household that is over the limit but in a documented crisis where a member's income has stopped entirely. The screener collects neither the service-termination status nor the income-termination date that Missouri's exception also requires, so the exception cannot be reproduced in full.
   - **Handling**: treated inclusively. MFB records no income period (see criterion 1's income-timing note), and its questions ask what a household receives now, so a fully terminated stream is typically not reported and therefore not counted — which lands where Missouri's exception lands. The outcome is not guaranteed, because nothing prevents a household from reporting an ended stream. The additional crisis and service-termination conditions are not verified, which only widens the result in the applicant's favour.
   - Source: LIHEAP Policy and Procedure Manual, `Excess Income-Crisis Situation` — all conditions must be met: prior-month income causes ineligibility, the household is documented in crisis with service threatened or terminated, and the member no longer has any income — [snapshot `2026-08-20--modss-liheap-policy-procedure-manual`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-policy-procedure-manual/content.md), accessed 2026-08-20

10. **Zero-income households must explain how they manage**
    - **Why**: where every member aged 18 or over reported no income for the prior month, Missouri contacts the applicant and denies the application if the household cannot explain how it manages. The screener collects no such explanation.
    - **Handling**: assumed satisfied. **Inclusive** — a zero-income household is shown as eligible.
    - Source: LIHEAP Policy and Procedure Manual, Zero Income — if the applicant cannot `adequately explain management of this household, deny the` application — [snapshot `2026-08-20--modss-liheap-policy-procedure-manual`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-policy-procedure-manual/content.md), accessed 2026-08-20

## Priority Criteria

- Households including a member aged 60 or older, or a member with a disability, may apply from October 1; all other households apply from November 1. This changes when a household may apply, never whether it qualifies.
  - Captured: description text — the program description states the early October application period for households with someone 60 or older or with a disability.
  - Missouri's regulatory definition of disability is narrower than the screener's self-reported one (see Deduction 2); the same inclusive direction applies here.
  - Source: FFY2026 Model State Plan §2.3, which files this under its priority questions — `Older Adults (60 years or older)?` — [snapshot `2026-08-20--mo-liheap-model-state-plan-ffy2026`](../../../sources/mo/mo_liheap/2026-08-20--mo-liheap-model-state-plan-ffy2026/content.md), accessed 2026-08-20
  - Source: LIHEAP Policy and Procedure Manual, Early Application Period — `For households with a person who is disabled or age 60 or older` — [snapshot `2026-08-20--modss-liheap-policy-procedure-manual`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-policy-procedure-manual/content.md), accessed 2026-08-20
  - Source: FFY2026 application, revision MO 886-4576 (9-2025) — `Send your application on or after October 1, 2025` — [snapshot `2026-08-20--modss-liheap-application-form`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-application-form/content.md), accessed 2026-08-20
  - Source: LIHEAP Policy and Procedure Manual, Early Application Period — `all other households from November 1` – May 31 — [snapshot `2026-08-20--modss-liheap-policy-procedure-manual`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-policy-procedure-manual/content.md), accessed 2026-08-20

## Related Programs

- **Energy Crisis Intervention Program (ECIP)** — a separate crisis benefit with its own trigger, at the same 60% SMI threshold. Not modelled by this spec.
  - Winter maximum $800, summer maximum $300.
  - The manual opens the winter component on November 1 for elderly and disabled households and December 1 for all others; the application states the applicant-facing window as November 1 – May 31.
  - Renter households whose heating is included in rent may receive EA but not ECIP.
  - Source: MyDSS LIHEAP page — `Helps pay your energy bill when you have a` termination or disconnect notice indicating a specific disconnect date — [snapshot `2026-08-20--modss-liheap-overview`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-overview/content.md), accessed 2026-08-20
  - Source: FFY2026 application, revision MO 886-4576 (9-2025) — `Up to $800 November 1 through May` 31 and `Up to $300 June 1 through September` 30 — [snapshot `2026-08-20--modss-liheap-application-form`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-application-form/content.md), accessed 2026-08-20
  - Source: FFY2026 Model State Plan §2.3 — utilities-included renters receive a one-time payment and `The clients are also not eligible for ECIP benefits.` — [snapshot `2026-08-20--mo-liheap-model-state-plan-ffy2026`](../../../sources/mo/mo_liheap/2026-08-20--mo-liheap-model-state-plan-ffy2026/content.md), accessed 2026-08-20
  - Source: FFY2026 Model State Plan §4.1, crisis component — `All Household Sizes                                   State Median Income                                                        60.00%` — [snapshot `2026-08-20--mo-liheap-model-state-plan-ffy2026`](../../../sources/mo/mo_liheap/2026-08-20--mo-liheap-model-state-plan-ffy2026/content.md), accessed 2026-08-20
- **Weatherization assistance** — home energy conservation services on a different income threshold entirely (200% FPL). Not modelled by this spec.
  - Source: FFY2026 Model State Plan §5.1 — `All Household Sizes                               HHS Poverty Guidelines                                                200.00%` — [snapshot `2026-08-20--mo-liheap-model-state-plan-ffy2026`](../../../sources/mo/mo_liheap/2026-08-20--mo-liheap-model-state-plan-ffy2026/content.md), accessed 2026-08-20
  - Source: LIHEAP Clearinghouse, Missouri profile — `Weatherization: 200% Federal Poverty Guidelines` — [snapshot `2026-08-20--liheap-clearinghouse-missouri-profile`](../../../sources/mo/mo_liheap/2026-08-20--liheap-clearinghouse-missouri-profile/content.md), accessed 2026-08-20

## Benefit Value

- **Value: $153 one-time estimated value.** MFB's conservative flat estimate, set at Missouri's published minimum Energy Assistance benefit — the estimate for the households this spec models.
  - Not offered as a floor for the unmodelled renter pathway below: those awards are computed from rent and capped, and no captured source establishes whether the $153 component minimum applies to them.
  - Not a guaranteed floor for modelled households generally either: Missouri's CARS recoupment (below) can reduce a household's actual current-year payment, including to $0, independent of this estimate.
- **`value_format`: `lump_sum`.** 13 CSR 40-19.020(3)(A) itself describes the Energy Assistance award as a `direct one (1) time lump sum payment`, matching the config. Missouri may add a supplemental payment in a year when it receives additional funding; that is contingent and not modelled.
- **Variation axes: none modelled.** Missouri varies the award by household size, income range and fuel type, and pays utilities-included renters on a share-of-rent formula instead; MFB models none of these and returns $153 for every eligible household.
- **Outstanding EA claim (CARS recoupment) — data gap.** Missouri checks an approved household's Social Security numbers against its Claims and Restitution System (CARS) for an outstanding prior EA claim and reduces the calculated EA benefit by the amount of that claim; if the claim equals or exceeds the benefit, the household's EA payment displays as $0.00. The screener collects no CARS claim balance.
  - **Committed handling**: assume no outstanding claim and return the standard $153 estimate. No scenario models this, because the claim balance is not observable in the current screener.
  - Source: LIHEAP Policy and Procedure Manual, Claims and Restitution — `If a CARS claim is outstanding and the application is determined eligible for EA, the calculated EA benefit will be reduced by the amount of the claim` and `If the CARS amount is equal to or greater than the EA benefit, the "EA Benefits" field will display $0.00` — [snapshot `2026-08-20--modss-liheap-policy-procedure-manual`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-policy-procedure-manual/content.md), accessed 2026-08-20
- Source: FFY2026 Model State Plan §2.6 — `Minimum Benefit                              $153                            Maximum Benefit                                $495` — [snapshot `2026-08-20--mo-liheap-model-state-plan-ffy2026`](../../../sources/mo/mo_liheap/2026-08-20--mo-liheap-model-state-plan-ffy2026/content.md), accessed 2026-08-20
- Source: FFY2026 application, revision MO 886-4576 (9-2025), Program Description — `Below is the maximum payment amount your household can` receive, listing `Natural Gas                     $326`, `Tank Propane                     $495`, `Electric                      $318`, `Fuel Oil                      $326`, `Wood                         $219`, `Kerosene                       $153`, `Cylinder Propane                  $177` — [snapshot `2026-08-20--modss-liheap-application-form`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-application-form/content.md), accessed 2026-08-20
- Source: FFY2026 Model State Plan §2.3, renter payment (not modelled) — `Clients receive a one-time direct payment equal to 16% of their annual rent, not to exceed` the maximum allowed EA benefit — [snapshot `2026-08-20--mo-liheap-model-state-plan-ffy2026`](../../../sources/mo/mo_liheap/2026-08-20--mo-liheap-model-state-plan-ffy2026/content.md), accessed 2026-08-20
- Source: LIHEAP Policy and Procedure Manual, Renter Household Payment (not modelled) — a `direct cash payment equal to 16% of their annual rent not to exceed the maximum` EA benefit payment — [snapshot `2026-08-20--modss-liheap-policy-procedure-manual`](../../../sources/mo/mo_liheap/2026-08-20--modss-liheap-policy-procedure-manual/content.md), accessed 2026-08-20
- Source: 13 CSR 40-19.020(13), the same payment stated as a ceiling (not modelled) — no `more than eight percent (8%) of their annual` rental charge — [snapshot `2026-08-20--13-csr-40-19-020`](../../../sources/mo/mo_liheap/2026-08-20--13-csr-40-19-020/content.md), accessed 2026-08-20
- **Justification for $153**:
  - Missouri's actual Energy Assistance award ranges from $153 to $495 and varies by income, household size and fuel type. The seven per-fuel figures Missouri publishes are maximum amounts, not the amounts every household receives, and the current payment matrix that sets the award within those maxima is not published. The MFB screener also collects no primary heating fuel, so the household's fuel row cannot be identified.
  - This spec therefore commits to $153 — Missouri's published minimum benefit — as a deliberate conservative estimate, rather than an average that would overstate the award for households receiving less than the maximum. $153 is not a claim that Missouri pays every eligible household $153, and (per the CARS note above) it is not a guaranteed payment either.
  - 13 CSR 40-19.020(14) does publish a fuel-type × income-band matrix with values as low as $45, but its figures predate and contradict the current $153–$495 range, so it is not used to reconstruct an award.
  - **Renter payment (not modelled).** A separate award applies where heating is included in the rent — a share of annual rent rather than a fuel-based amount. Whether the $153 component minimum also applies to it is not established by anything captured here: the screener records no utilities-included tenancy, and inferring one from a rent expense with no itemised utility expense would misclassify ordinary renters.
    - **Source conflict — size of the renter payment, unresolved, no scenario commits to either reading.** The model plan and manual both state a one-time payment equal to 16% of annual rent, not to exceed the maximum EA benefit; 13 CSR 40-19.020(13) states the same payment as a ceiling of no more than 8% of annual rental charge.

## Test Scenarios

**Coverage map**

| Rule / variation axis | Scenarios |
|---|---|
| Income at or below 60% SMI | pass: 1; boundary: 2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23 |
| Limit table, size 1 | boundary: 2, 3, 4, 8, 10, 13, 17, 22 |
| Limit table, size 2 | boundary: 6, 7, 11, 12, 16, 18, 20, 21, 23 |
| Limit table, size 4 | boundary: 15 |
| Limit table, size 7 | boundary: 9 |
| Limit table, size 8 | boundary: 14, 19 |
| Deduction 1 — 20% earned income | boundary: 4 (rate not smaller), 22 (rate not larger); not applied to unearned: 3 |
| Deduction 2 — $100, age 65 threshold | boundary: 6 (granted at exactly 65), 18 (denied at 64) |
| Deduction 2 — disability branch | boundary: 10 |
| Deduction 2 — once per household | boundary: 11 |
| Deduction 2 — spouse qualifies | boundary: 21 |
| Deduction 2 — non-spouse member does not qualify | boundary: 12 |
| Deduction 3 — child support paid | boundary: 8 |
| Deduction 4 — $202.90 per Medicare member | boundary: 7 |
| Exclusion — earned income under 18 | boundary: 16 (17, excluded), 20 (18, counted) |
| Minor's SSA income still counts | boundary: 23 |
| Exclusion — interest and dividend income | boundary: 17 |
| Income frequency conversion | boundary: 13 |
| Energy-cost responsibility — rent + heating (golden path) | pass: 1 |
| Energy-cost responsibility — heating | pass: 2, 6, 7, 13, 21 |
| Energy-cost responsibility — none | fail: 5 |
| Missouri residency | platform-enforced at ZIP/county intake; no core scenario |
| Applicant age (member 15 or older) | fail: 24 |
| Benefit value | every eligible scenario: $153 (CARS recoupment not modelled — data gap) |

**Known scenario gaps**

- Criterion 3 (citizenship) is config-scope and can't be varied by any scenario — the screener collects no per-member immigration status.
- Data gap 1 (the $3,000 resource limit) has no dedicated scenario, because MFB cannot calculate Missouri's countable resources.
- Data gaps 2–8 and 10 are unscreenable and unverified by scenario: Missouri's household definition, the ineligible living situations, the $500 credit balance, self-supplied wood, individuals excluded from the household count, the narrow income exclusions inside countable types, prior-year EA receipt, and zero-income explanation.
- Data gap 9's substance is covered by ordinary income collection, not a dedicated scenario — a household whose income has stopped simply reports nothing to count.
- The utilities-included renter payment and the 8%-versus-16% conflict have no scenario, because that pathway isn't modelled and the sources are unresolved.
- The award doesn't vary by fuel type or income band in any scenario, because the value is flat by design.
- CARS recoupment (Benefit Value) has no scenario, because the outstanding-claim balance isn't observable in the current screener.
- Two null-handling paths are untested: criterion 1 skips evaluation when `household_size` is null, and criterion 4 treats a null `zipcode` as met.
- Limit-table rows 3, 5 and 6 have no scenario and rest on the published table as constants.
- Sizes 9 and 10, and the +$164 increment above 10, are untestable — the current screener caps household size at 8.
- Criterion 4's own Missouri-ZIP check has no negative scenario, because the live MO screener's ZIP/county intake rejects a non-Missouri ZIP before the calculator runs.
- Each deduction/exclusion set is exercised through one income type only: `wages` for the earned-income deduction set (`wages`, `selfEmployment`, `boarder`), and `investment` for the interest-and-dividend exclusion set.
- `mortgage`, `cooling`, and `otherUtilities` are valid inputs to criterion 2 but have no dedicated scenarios; homeowners are covered only through the `heating` scenarios and criterion 2's implementation note.
- Scenarios 2 and 13 are a deliberate near-pair: both are plain-monthly, at-the-limit controls that isolate a frequency-conversion failure from a boundary failure.

### Scenario 1: Single adult, low income, renter — Eligible, $153
**What we're checking**: the ordinary eligible path, with a direct heating expense establishing energy-cost responsibility.
**Expected**: Eligible — $153 (earned $1,000 × 0.80 = $800 ≤ $2,840)
**Steps**:
* Location: ZIP `63101`, county `St. Louis City`
* Person 1: born March 1986 (age 40), head of household, earned income $1,000/month
* Expenses: rent $600/month, heating $150/month
**Why this matters**: confirms the base eligible path and the flat $153 value. The heating expense makes criterion 2 directly observable, not just inferred from the rent proxy.

---

### Scenario 2: Household of 1 exactly at the income limit — Eligible, $153
**What we're checking**: the income boundary is inclusive at the limit.
**Expected**: Eligible — $153 (unearned $2,840 = limit $2,840; no deductions apply)
**Steps**:
* Location: ZIP `65201`, county `Boone County`
* Person 1: born March 1986 (age 40), head of household, unearned (pension) income $2,840/month
* Expenses: heating $150/month
**Why this matters**: confirms the income limit is inclusive — exactly at the limit is eligible.

---

### Scenario 3: Household of 1 one dollar over the limit — Ineligible
**What we're checking**: the income boundary excludes above the limit, and the 20% deduction is not applied to unearned income.
**Expected**: Ineligible (unearned $2,841 exceeds the size-1 limit of $2,840)
**Steps**:
* Location: ZIP `65201`, county `Boone County`
* Person 1: born March 1986 (age 40), head of household, unearned (pension) income $2,841/month
* Expenses: heating $150/month
**Why this matters**: confirms the income limit excludes anything above it, pins the size-1 limit at exactly $2,840, and confirms the 20% deduction does not apply to unearned income — applying it here would wrongly give $2,272.80 and flip this to eligible.

---

### Scenario 4: Earned income at the limit after the 20% deduction — Eligible, $153
**What we're checking**: the earned-income deduction rate.
**Expected**: Eligible — $153 ($3,550 × 0.80 = $2,840.00 = size-1 limit $2,840)
**Steps**:
* Location: ZIP `64108`, county `Jackson County`
* Person 1: born March 1986 (age 40), head of household, earned income $3,550/month
* Expenses: rent $700/month, heating $50/month
**Why this matters**: confirms the earned-income deduction rate is exactly 20% — a smaller rate (19% → $2,875.50) or no deduction ($3,550) would wrongly exceed the limit. A larger rate wouldn't be caught here, since the household is already at the limit; **scenario 22** covers that direction. Scenario 3 confirms the deduction doesn't apply to unearned income.

---

### Scenario 5: Eligible income but no housing or utility expense — Ineligible
**What we're checking**: the energy-cost responsibility criterion.
**Expected**: Ineligible (no rent, mortgage, heating, cooling or other-utilities expense)
**Steps**:
* Location: ZIP `63101`, county `St. Louis City`
* Person 1: born March 1986 (age 40), head of household, earned income $500/month
* Expenses: none
**Why this matters**: confirms the energy-cost responsibility check is enforced — income alone isn't enough.

---

### Scenario 6: Household of 2, head exactly 65, eligible only after the $100 deduction — Eligible, $153
**What we're checking**: the $100 medical deduction is granted at exactly 65.
**Expected**: Eligible — $153 ($3,814 − $100 = $3,714 = size-2 limit $3,714)
**Steps**:
* Location: ZIP `65201`, county `Boone County`
* Person 1: born August 1961 (age 65 as of 2026-08-20), head of household, unearned (`sSRetirement`) income $3,814/month
* Person 2: born March 1963 (age 63), spouse, no income
* Expenses: heating $200/month
**Why this matters**: confirms the $100 deduction is granted starting in the birth month a member turns 65, not only after a full month has passed. The head reaches 65 in the reference month here (`age_from_date` treats `today.month >= birth.month` as reached); requiring a later date instead would deny the deduction and flip this to ineligible ($3,814 > $3,714). Scenario 18 covers the other side of the threshold.

---

### Scenario 7: Two Medicare members, eligible only after both deductions — Eligible, $153
**What we're checking**: the Medicare deduction is applied per member, not once per household (the $202.90 constant is an MFB approximation, not verified policy — see Deduction 4).
**Expected**: Eligible — $153 ($4,219.80 − $100 elderly − $405.80 Medicare (2 × $202.90) = $3,714.00 = size-2 limit $3,714)
**Steps**:
* Location: ZIP `64108`, county `Jackson County`
* Person 1: born March 1959 (age 67), head of household, unearned (`sSRetirement`) income $4,219.80/month, insurance: Medicare
* Person 2: born March 1958 (age 68), spouse, no income, insurance: Medicare
* Expenses: heating $180/month
**Why this matters**: confirms the Medicare deduction applies per member, not once per household — applying it only once would give $3,916.90 > $3,714 and wrongly flip this to ineligible.

---

### Scenario 8: Child support paid, eligible only after the deduction — Eligible, $153
**What we're checking**: the child-support-paid deduction.
**Expected**: Eligible — $153 ($3,005 − $165 = $2,840 = size-1 limit $2,840)
**Steps**:
* Location: ZIP `63101`, county `St. Louis City`
* Person 1: born March 1986 (age 40), head of household, unearned (pension) income $3,005/month
* Expenses: rent $650/month, heating $50/month, child support $165/month
**Why this matters**: confirms child support paid is treated as a deduction, not as income, and that omitting it would wrongly flip this to ineligible.

---

### Scenario 9: Household of 7 at the size-7 limit — Eligible, $153
**What we're checking**: the limit table above household size 6.
**Expected**: Eligible — $153 (unearned $7,373 = size-7 limit $7,373)
**Steps**:
* Location: ZIP `65201`, county `Boone County`
* Person 1: born March 1986 (age 40), head of household, unearned (pension) income $7,373/month
* Persons 2–7: children born 2012–2022, no income
* Expenses: rent $1,200/month, heating $50/month
**Why this matters**: confirms the limit table extends past size 6 with its own published row ($7,373), rather than clamping at the size-6 row ($7,209, which would wrongly deny this household). This alone can't distinguish a correct size-7 row from a table that just falls through to the +$164 increment rule, since $7,209 + $164 happens to equal $7,373 — and that distinction, along with the increment rule's own $163-vs-$164 discrepancy at size 9→10, can no longer be tested at all, because the live MFB household-size field caps entries at 8.

---

### Scenario 10: Head under 65 with a disability — Eligible, $153
**What we're checking**: the disability branch of the $100 medical deduction (tests MFB simplification, not verified policy — Missouri's regulatory definition also requires receipt of a qualifying benefit).
**Expected**: Eligible — $153 ($2,940 − $100 = $2,840 = size-1 limit $2,840)
**Steps**:
* Location: ZIP `63101`, county `St. Louis City`
* Person 1: born March 1976 (age 50), head of household, has a long-term disability, unearned (pension) income $2,940/month
* Expenses: rent $700/month, heating $50/month
**Why this matters**: confirms the disability branch of the $100 deduction — removing it would wrongly flip this to ineligible.

---

### Scenario 11: Two members aged 65 or older, one deduction only — Ineligible
**What we're checking**: the $100 deduction is granted once per household, not per qualifying member.
**Expected**: Ineligible ($3,914 − $100 = $3,814 exceeds the size-2 limit of $3,714)
**Steps**:
* Location: ZIP `65201`, county `Boone County`
* Person 1: born March 1961 (age 65), head of household, unearned (pension) income $3,914/month
* Person 2: born March 1959 (age 67), spouse, no income
* Expenses: heating $200/month
**Why this matters**: confirms the $100 deduction is applied once per household, not once per qualifying member — applying it twice would give $3,714 = the limit and wrongly flip this to eligible.

---

### Scenario 12: Qualifying age in a non-spouse member — Ineligible
**What we're checking**: the $100 deduction applies only to the applicant or spouse.
**Expected**: Ineligible (no deduction; unearned $3,800 exceeds the size-2 limit of $3,714)
**Steps**:
* Location: ZIP `64108`, county `Jackson County`
* Person 1: born March 1986 (age 40), head of household, unearned (pension) income $3,800/month
* Person 2: born March 1956 (age 70), parent of the head, no income
* Expenses: rent $800/month, heating $50/month
**Why this matters**: confirms the $100 deduction is restricted to the applicant or spouse — extending it to any qualifying member would give $3,700 ≤ $3,714 and wrongly flip this to eligible.

---

### Scenario 13: Income reported yearly, at the monthly limit — Eligible, $153
**What we're checking**: income frequency is normalised to monthly before comparison.
**Expected**: Eligible — $153 (unearned $34,080/year ÷ 12 = $2,840.00/month = size-1 limit $2,840)
**Steps**:
* Location: ZIP `65201`, county `Boone County`
* Person 1: born March 1986 (age 40), head of household, unearned (pension) income $34,080/year
* Expenses: heating $150/month
**Why this matters**: confirms yearly income is converted to monthly before the limit check. Every other scenario states income monthly, so this is the only one that catches a frequency-conversion error.

---

### Scenario 14: Household of 8 at the size-8 limit — Eligible, $153
**What we're checking**: the size-8 row of the limit table — the highest household size the live MFB household-size field can enter.
**Expected**: Eligible — $153 (unearned $7,537 = size-8 limit $7,537)
**Steps**:
* Location: ZIP `65201`, county `Boone County`
* Person 1: born March 1986 (age 40), head of household, unearned (pension) income $7,537/month
* Persons 2–8: children born 2008–2022, no income
* Expenses: rent $1,300/month, heating $50/month
**Why this matters**: confirms the size-8 row of the limit table — the largest household size the live screener allows. Sizes 9 and 10, and the +$164 increment beyond 10, can't be entered through the live screener and so aren't tested by any scenario.

---

### Scenario 15: Household of 4 at the size-4 limit — Eligible, $153
**What we're checking**: a mid-table row of the limit table.
**Expected**: Eligible — $153 (unearned $5,461 = size-4 limit $5,461)
**Steps**:
* Location: ZIP `63101`, county `St. Louis City`
* Person 1: born March 1986 (age 40), head of household, unearned (pension) income $5,461/month
* Person 2: born March 1988 (age 38), spouse, no income
* Persons 3–4: children born 2015 and 2018, no income
* Expenses: rent $1,100/month, heating $50/month
**Why this matters**: confirms a mid-table row (size 4) of the limit table.

---

### Scenario 16: Household with a working 17-year-old — Eligible, $153
**What we're checking**: earned income of a household member under 18 is excluded, at the boundary.
**Expected**: Eligible — $153 (head unearned $3,714 = size-2 limit $3,714; the 17-year-old's $500 earned income is excluded)
**Steps**:
* Location: ZIP `64108`, county `Jackson County`
* Person 1: born March 1986 (age 40), head of household, unearned (pension) income $3,714/month
* Person 2: born March 2009 (age 17), child, earned income $500/month
* Expenses: rent $900/month, heating $50/month
**Why this matters**: confirms earned income of a 17-year-old is excluded — counting it (even after the 20% deduction, adding $400) would give $4,114 > $3,714 and wrongly flip this to ineligible.

---

### Scenario 17: Household with investment income — Eligible, $153
**What we're checking**: interest and dividend income is excluded.
**Expected**: Eligible — $153 (unearned pension $2,840 = size-1 limit $2,840; $300 investment income excluded)
**Steps**:
* Location: ZIP `63101`, county `St. Louis City`
* Person 1: born March 1986 (age 40), head of household, unearned (pension) income $2,840/month, investment income $300/month
* Expenses: rent $700/month, heating $50/month
**Why this matters**: confirms investment income is excluded — counting it would give $3,140 > $2,840 and wrongly flip this to ineligible.

---

### Scenario 18: Head aged 64, no medical deduction — Ineligible
**What we're checking**: the $100 deduction is denied below 65.
**Expected**: Ineligible (no deduction; unearned $3,814 exceeds the size-2 limit of $3,714)
**Steps**:
* Location: ZIP `65201`, county `Boone County`
* Person 1: born March 1962 (age 64), head of household, unearned (`sSRetirement`) income $3,814/month
* Person 2: born March 1964 (age 62), spouse, no income
* Expenses: heating $200/month
**Why this matters**: confirms the $100 deduction is denied below 65. The likeliest confusion is with age 60, which Missouri uses for the early-application period, not this deduction — using 60 here would give $3,714 = the limit and wrongly flip this to eligible.

---

### Scenario 19: Household of 8 one dollar over the size-8 limit — Ineligible
**What we're checking**: the size-8 boundary excludes above the limit, at the highest household size the live screener can enter.
**Expected**: Ineligible (unearned $7,538 exceeds the size-8 limit of $7,537)
**Steps**:
* Location: ZIP `65201`, county `Boone County`
* Person 1: born March 1986 (age 40), head of household, unearned (pension) income $7,538/month
* Persons 2–8: children born 2008–2022, no income
* Expenses: rent $1,300/month, heating $50/month
**Why this matters**: confirms the size-8 limit excludes anything above it. Paired with scenario 14, this pins the top-of-table boundary the current MFB screener can actually reach.

---

### Scenario 20: Household with a working 18-year-old — Ineligible
**What we're checking**: earned income of a member aged 18 is counted.
**Expected**: Ineligible (head unearned $3,714 + the 18-year-old's $500 × 0.80 = $400, giving $4,114 > size-2 limit $3,714)
**Steps**:
* Location: ZIP `64108`, county `Jackson County`
* Person 1: born March 1986 (age 40), head of household, unearned (pension) income $3,714/month
* Person 2: born March 2008 (age 18), child, earned income $500/month
* Expenses: rent $900/month, heating $50/month
**Why this matters**: confirms earned income of an 18-year-old is counted, not excluded — excluding it would give $3,714 = the limit and wrongly flip this to eligible. With scenario 16, this pins the under-18 exclusion at exactly 18.

---

### Scenario 21: Qualifying age in the spouse, not the head — Eligible, $153
**What we're checking**: the $100 deduction is granted when the *spouse* qualifies, not only the applicant.
**Expected**: Eligible — $153 ($3,814 − $100 = $3,714 = size-2 limit $3,714)
**Steps**:
* Location: ZIP `63101`, county `St. Louis City`
* Person 1: born March 1986 (age 40), head of household, unearned (pension) income $3,814/month
* Person 2: born March 1960 (age 66), spouse, no income
* Expenses: heating $200/month
**Why this matters**: confirms the $100 deduction is granted when the spouse qualifies, not only the head — restricting it to the head would give $3,814 > $3,714 and wrongly flip this to ineligible. Scenario 12 proves a non-spouse member does *not* qualify; this proves a spouse does.

---

### Scenario 22: Earned income one dollar past the deduction boundary — Ineligible
**What we're checking**: the earned-income deduction rate is not larger than 20%.
**Expected**: Ineligible ($3,551 × 0.80 = $2,840.80, which exceeds the size-1 limit of $2,840)
**Steps**:
* Location: ZIP `63101`, county `St. Louis City`
* Person 1: born March 1986 (age 40), head of household, earned income $3,551/month
* Expenses: rent $700/month, heating $50/month
**Why this matters**: confirms the earned-income deduction rate is not larger than 20%. A too-generous rate would pass every other scenario undetected — at 30% the countable figure is $2,485.70, comfortably under the limit — so this is the only scenario that catches it.

---

### Scenario 23: Minor with SSA income — Ineligible
**What we're checking**: the under-18 exclusion covers earned income only; a minor's SSA income still counts.
**Expected**: Ineligible (head unearned $3,714 + the 17-year-old's $100 SSI = $3,814, which exceeds the size-2 limit of $3,714)
**Steps**:
* Location: ZIP `64108`, county `Jackson County`
* Person 1: born March 1986 (age 40), head of household, unearned (`sSRetirement`) income $3,714/month
* Person 2: born March 2009 (age 17), child, unearned (`sSI`) income $100/month
* Expenses: rent $900/month, heating $50/month
**Why this matters**: confirms the under-18 income exclusion covers earned income only — excluding all income (including SSA) would give $3,714 = the limit and wrongly flip this to eligible. Scenario 16 pins the earned side of the same rule.

---

### Scenario 24: No household member aged 15 or older — Ineligible
**What we're checking**: the applicant-age criterion.
**Expected**: Ineligible (oldest member is 14; Missouri denies an application from an applicant under 15)
**Steps**:
* Location: ZIP `63101`, county `St. Louis City`
* Person 1: born March 2012 (age 14), head of household, earned income $400/month
* Person 2: born March 2016 (age 10), `sisterOrBrother`, no income
* Expenses: rent $500/month, heating $50/month
**Why this matters**: income and expenses both qualify, so this fails only on the applicant-age rule — dropping that criterion would wrongly flip it to eligible.

---

## Research Sources

| Snapshot | Tier | Fidelity | Title | URL | Retrieved |
|---|---|---|---|---|---|
| `2026-08-20--13-csr-40-19-020` | 1 | raw | 13 CSR 40-19 — Missouri FSD energy assistance rules (incl. 40-19.020 LIHEAP and Utilicare) | https://www.sos.mo.gov/cmsimages/adrules/csr/current/13csr/13c40-19.pdf | 2026-08-20 |
| `2026-08-20--42-usc-8624` | 1 | raw | 42 U.S.C. 8624 — LIHEAP applications and requirements | https://www.law.cornell.edu/uscode/text/42/8624 | 2026-08-20 |
| `2026-08-20--acf-liheap-im-1998-25-federal-public-benefits` | 1 | rendered | LIHEAP IM 1998-25 — Interpretation of 'Federal Public Benefits' Under the Welfare Reform Law (ACF/OCS) | https://acf.gov/ocs/policy-guidance/liheap-im-1998-25-interpretation-federal-public-benefits-under-welfare-reform | 2026-08-20 |
| `2026-08-20--mo-liheap-model-state-plan-ffy2026` | 2 | raw | Missouri LIHEAP Model State Plan, FFY2026 (active) | https://dss.mo.gov/fsd/energy-assistance/pdf/liheap-active-ffy2026.pdf | 2026-08-20 |
| `2026-08-20--mo-liheap-model-state-plan-ffy2027` | 2 | raw | Missouri LIHEAP Model State Plan, FFY2027 (draft) | https://dss.mo.gov/fsd/energy-assistance/pdf/liheap-active-ffy2027.pdf | 2026-08-20 |
| `2026-08-20--modss-liheap-policy-procedure-manual` | 2 | raw | The Low-Income Home Energy Assistance Program (LIHEAP) Policy and Procedure Manual — MO DSS FSD | https://dss.mo.gov/fsd/energy-assistance/pdf/liheap-policy-procedure-manual.pdf | 2026-08-20 |
| `2026-08-20--modss-liheap-application-form` | 2 | raw | LIHEAP application (Financial Assistance for Home Energy Costs) — MO DSS FSD | https://dssmanuals.mo.gov/wp-content/uploads/2022/02/liheap-application.pdf | 2026-08-20 |
| `2026-08-20--modss-liheap-overview` | 2 | raw | Low Income Home Energy Assistance Program (LIHEAP) — Missouri DSS | https://mydss.mo.gov/utility-assistance/liheap | 2026-08-20 |
| `2026-08-20--modss-benefit-program-income-limits` | 2 | raw | Benefit Program Income Limits — Missouri DSS (MyDSS) | https://mydss.mo.gov/benefit-program-income-limits | 2026-08-20 |
| `2026-08-20--modss-2026-fpl-chart-all-programs` | 2 | raw | 2026 FPL Chart for all Programs (rev. 3-31-26) — Missouri DSS | https://mydss.mo.gov/sites/mydss/files/media/pdf/2026/03/2026%20FPL%20Chart%20for%20all%20Programs_3-31-26_AOD.pdf | 2026-08-20 |
| `2026-08-20--modss-benefit-program-limit-chart` | 2 | raw | Benefit Program Limit Chart — Missouri DSS | https://mydss.mo.gov/media/pdf/benefit-program-limit-chart | 2026-08-20 |
| `2026-08-20--modss-liheap-state-plan-index` | 2 | raw | Missouri FFY LIHEAP Model State Plan index — MO DSS FSD | https://dss.mo.gov/fsd/energy-assistance/state-plan-liheap-lihwap-ffy.htm | 2026-08-20 |
| `2026-08-20--modss-liheap-information-sheet` | 2 | raw | LIHEAP information sheet — MO DSS FSD | https://dss.mo.gov/fsd/energy-assistance/pdf/liheap-information.pdf | 2026-08-20 |
| `2026-08-20--cms-medicare-premium-rates-cy2026` | 2 | raw | Medicare Deductible, Coinsurance & Premium Rates: CY 2026 Update (MM14279) — CMS | https://www.cms.gov/files/document/mm14279-medicare-deductible-coinsurance-premium-rates-cy-2026-update.pdf | 2026-08-20 |
| `2026-08-20--liheap-clearinghouse-missouri-profile` | 3 | rendered | Missouri — LIHEAP Clearinghouse state profile (ACF) | https://liheapch.acf.gov/profiles/Missouri.htm | 2026-08-20 |
| `2026-08-20--wcmcaa-energy-assistance` | 3 | raw | Low Income Home Energy Assistance Program (LIHEAP) — West Central Missouri Community Action Agency | https://wcmcaa.org/ea/ | 2026-08-20 |
