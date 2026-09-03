# Ticket to Work Health Assurance (MO) — Program Spec

- **Program key**: `mo_twha` (`programs/programs/cross_white_label/medicaid/disability/mo.py`)
- **Base federal program**: Medicaid (state buy-in authorized by the federal Ticket to Work and Work Incentives Improvement Act of 1999, Public Law 106-170)
- **White label**: MO
- **Engine**: MFB custom
- **Statutory basis**: RSMo 208.146, **effective 2026-08-28** (A.L. 2026 H.B. 2372). This spec describes the law in force from that date.
- **Added to MFB**: not yet added — Discovery package for MFB-1287 / MFB-1223
- **Spec last updated**: 2026-09-02
- **Sources verified as of**: 2026-09-02

## Covered Eligibility Criteria

1. **Age 16 through 64, inclusive of the calendar month in which the person turns 16 or 65**
   - Evaluation scope: member
   - Captured via: `HouseholdMember.birth_year` / `HouseholdMember.birth_month` (derived from the stored `birth_year_month`, DateField). Compare stored birth year/month directly against the year and month of `screen.get_reference_date()`; a bare `age` integer or `calc_age()` cannot distinguish someone in their 65th-birthday month from someone one month past it.
   - Null handling: a member with no stored birth date fails this condition closed. Defensive only — the screener requires both fields, but `birth_year_month` is nullable on the model and screens can arrive through the API.
   - Source: 0855.000.00 TWHA — "The purpose of the TWHA program is to provide medical care for persons with disabilities, age 16 through 64, who are employed." — [snapshot `2026-08-24--dss-manual-0855-000-00-twha`](../../../sources/mo/mo_twha/2026-08-24--dss-manual-0855-000-00-twha/content.md), accessed 2026-08-24
   - Source (month-inclusive boundary): 0855.005.05 Age Requirement — "Participants must be age 16 through age 64. This includes the month the person turns age 16 or 65." — [snapshot `2026-08-24--dss-manual-0855-005-05`](../../../sources/mo/mo_twha/2026-08-24--dss-manual-0855-005-05/content.md), accessed 2026-08-24
   - Source (corroborating): IM-4 TWHA brochure — "You may be eligible if you are age 16-64 and:" — [snapshot `2026-08-24--im4-twha-brochure`](../../../sources/mo/mo_twha/2026-08-24--im4-twha-brochure/content.md), accessed 2026-08-24

2. **Meets the SSI definition of disabled (Basic Coverage Group), or is an "employed individual with a medically improved disability" under TWWIIA (Medically Improved Group)**
   - Evaluation scope: member
   - **Policy rule**: the applicant meets TWHA's Permanent and Total Disability standard (Basic Coverage Group) or the Medically Improved Disability standard. Missouri establishes this by SSI/Social Security disability receipt or a Medical Review Team (MRT) determination.
   - **⚠️ Data Gap — formal disability determination**: MFB cannot reproduce an SSA or MRT disability finding from screener input. See Data Gap 1.
   - **Committed handling**: treat `long_term_disability OR visually_impaired` (HouseholdMember, boolean) as an inclusive proxy for the statutory standard. Use these fields, NOT the generic `disabled` flag, mirroring KS/CO precedent for this program family — the generic flag is broader and admits short-term conditions.
   - Null handling: a null/unanswered value on either field is treated as "no," not "unknown" — a member with neither field reported does not satisfy the proxy.
   - Source: RSMo 208.146.1(1) — "Except for earnings, meets the definition of disabled under the Supplemental Security Income Program or meets the definition of an employed individual with a medically improved disability under TWWIIA;" — [snapshot `2026-09-01--rsmo-208-146`](../../../sources/mo/mo_twha/2026-09-01--rsmo-208-146/content.md), accessed 2026-09-01
   - Source (corroborating): IM-4 TWHA brochure — "Permanently and totally disabled" — [snapshot `2026-08-24--im4-twha-brochure`](../../../sources/mo/mo_twha/2026-08-24--im4-twha-brochure/content.md), accessed 2026-08-24
   - Source (Basic Coverage Group determination method): 0855.005.25 Disability Requirement — "Disability for the Basic Coverage Group will be determined either by receipt of SSI or Social Security based on disability, or the Medical Review Team (MRT)." — [snapshot `2026-08-24--dss-manual-0855-005-25`](../../../sources/mo/mo_twha/2026-08-24--dss-manual-0855-005-25/content.md), accessed 2026-08-24

3. **Employed with qualifying earned income under TWHA's Medicare/Social Security tax rule**
   - Evaluation scope: member
   - **Policy rule**: the applicant has earned income, with no dollar floor beyond having some. Missouri ordinarily requires Medicare and Social Security taxes to be withheld from it, or paid on it if self-employed. Effective 2017-02-01 there is an exception: medically related caregiver or homemaker/chore wages paid through a government agency such as DMH or DHSS qualify **even though those wages are specifically exempt and no such taxes are due**. The criterion is TWHA's tax rule, not "income subject to FICA/SECA".
   - **⚠️ Data Gap — which tax treatment applies**: MFB cannot observe whether a reported stream was taxed, nor whether an untaxed stream falls in the exempt caregiver category. See Data Gap 2.
   - **Committed handling**: treat any reported `wages` or `selfEmployment` above $0 as qualifying earned income. Do not add a tax-status gate — the exception means untaxed wages can qualify, so gating would false-deny exactly the caregiver population Missouri wrote it for.
   - Captured via: `calc_gross_income("monthly", ["earned"])` (HouseholdMember method), which classifies `wages` and `selfEmployment` by `IncomeStream.type`, not `IncomeStream.category`. Pass the `earned` selector, not the `wages` type alone, which would exclude every self-employed applicant.
   - Implementation note: Basic Coverage and Medically Improved Group employment thresholds differ (no floor vs. 40 hours/month at minimum wage); the screener can't distinguish the groups, so the more permissive Basic Coverage rule applies to all members (Data Gap 3).
   - Source: RSMo 208.146.1(2) — "Has earned income, as defined in subsection 2 of this section;" — [snapshot `2026-09-01--rsmo-208-146`](../../../sources/mo/mo_twha/2026-09-01--rsmo-208-146/content.md), accessed 2026-09-01
   - Source (group-specific employment thresholds and FICA exception): 0855.005.30 Employment Requirement — for the Basic Coverage Group: "There is no minimum level of hours of employment or amount of earnings required." For the Medically Improved Group: "An individual must have earnings from employment equal to at least 40 hours per month at the federal minimum wage." And: "Effective February 1, 2017, participants will be considered in compliance with the statutory requirement to pay Medicare and Social Security taxes if they work in a medically related caregiver or homemaker/chore services position and the payment received is through a government agency such as DMH or DHSS where no such taxes are paid because the wages are specifically exempt and no such taxes are due." — [snapshot `2026-08-24--dss-manual-0855-005-30`](../../../sources/mo/mo_twha/2026-08-24--dss-manual-0855-005-30/content.md), accessed 2026-08-24

4. **Countable resources at or below the TWHA asset limit — $6,220.50 (1 person) / $12,441.00 (couple), effective 2026-07-01, computed the same as MO HealthNet's permanent-and-total-disability standard except that retirement accounts are excluded entirely and medical savings/independent living accounts are excluded up to $5,000/year each in deposits and earnings**
   - Evaluation scope: household
   - Captured via: `household_assets` (Screen, DecimalField). The screener accepts whole dollars only, so the cent-level limits are not directly enterable — $6,220 and $12,441 are the operative single and couple boundary values a screen can express.
   - Implementation note: the asset limit is set for the TWHA assistance unit (single individual or married couple, per criterion 5), not MFB's generic household size — dependants do not raise it.
   - Implementation note: retirement accounts (401(k), 403(b), Keogh, pension, etc.) are excluded from the asset test entirely — only distributions count as income (criterion 5). `household_assets` already covers only cash/checking/savings/stocks/bonds/mutual funds, so there is no divergence to flag.
   - Implementation note: `household_assets` neither separates the excluded account types (medical savings, independent living) nor captures the other resources Missouri's PTD framework counts — see Data Gap 4 for the committed two-way handling.
   - **Committed handling**: pass a household whose reported `household_assets` is at or below the limit. Do **not** deny on assets alone when it exceeds the limit — MFB cannot tell how much of the total is an excluded medical savings or independent living balance. Reported assets alone never produce a hard ineligible determination.
   - Null handling: a null/unanswered `household_assets` is treated as $0 (fails open on the asset test)
   - Source (limit definition): RSMo 208.146.3(1) — "For purposes of determining eligibility under this section, the available asset limit and the definition of available assets shall be the same as those used to determine MO HealthNet eligibility for permanent and totally disabled individuals under subdivision (24) of subsection 1 of section 208.151 except for:" — [snapshot `2026-09-01--rsmo-208-146`](../../../sources/mo/mo_twha/2026-09-01--rsmo-208-146/content.md), accessed 2026-09-01
   - Source (dollar amounts): MHABD Appendix J — "Ticket to Work Health Assurance (TWHA)" table — "1 person                            $         3,990              04-01-26 $                6,220.50           07-01-26" and "2 people                                       5,410             04-01-26                12,441.00            07-01-26" — [snapshot `2026-08-24--mhabd-appendix-j-2026`](../../../sources/mo/mo_twha/2026-08-24--mhabd-appendix-j-2026/content.md), accessed 2026-08-24
   - Source (retirement accounts excluded entirely): 0855.005.35 Resource Requirement — "Resource considerations, with the exception of retirement accounts, are the same as for MHABD individuals. All retirement accounts are excluded from the calculation of assets for the Ticket to Work Health Assurance (TWHA) program." — [snapshot `2026-08-24--dss-manual-0855-005-35`](../../../sources/mo/mo_twha/2026-08-24--dss-manual-0855-005-35/content.md), accessed 2026-08-24
   - Source (medical savings / independent living account exclusions, statutory text): RSMo 208.146.3(1)(a)-(b) — "Medical savings accounts limited to deposits of earned income and earnings on such income while a participant in the program created under this section with a value not to exceed five thousand dollars per year;" and "Independent living accounts limited to deposits of earned income and earnings on such income while a participant in the program created under this section with a value not to exceed five thousand dollars per year." — [snapshot `2026-09-01--rsmo-208-146`](../../../sources/mo/mo_twha/2026-09-01--rsmo-208-146/content.md), accessed 2026-09-01

5. **Countable income at or below 250% of the Federal Poverty Level, except that the disabled worker's own earned income between 250% and 300% FPL is excluded from the count — evaluated as a single individual or married couple, not by generic household size**
   - Evaluation scope: household (income test, computed for the single individual or the married couple, per below) / member (whose earned income gets the 250–300% exclusion — the exclusion applies only to "the worker with a disability," not to a spouse's income or to the worker's own unearned income)
   - **Committed implementation**: countable income is derived by applying the statutory disregards to gross income, in this order, before comparing against the FPL thresholds below — **not** by comparing gross income directly to Appendix J's $3,990/$5,410 figures, which are DSS's own pre-computed ceiling for the all-earned-income case, not a general gross-wage cutoff:
     1. Exclude Temporary Assistance cash grants entirely — MFB's `cashAssistance` income type maps directly to this exclusion and contributes $0 to countable income
     2. Exclude the first $50,000/year ($4,166.67/month) of the spouse's **earned** income only (not the spouse's unearned income). This applies to any spouse, **including a spouse who is also a disabled worker** — neither the statute nor the operative manual section conditions the disregard on the spouse's disability status (see Source conflict below)
     3. Subtract a $20 standard deduction (once per case)
     4. Subtract health insurance premiums — MFB's screener reports these via the generic `medical` expense field; see Data Gap 6 for the committed treatment
     5. Subtract $75/month for the disabled worker's dental and optical insurance premiums, or the actual premium amount if it exceeds $75/month — MFB always applies the $75 floor; see Data Gap 6
     6. Exclude all SSI payments in full, and exclude the first $50/month of the disabled worker's SSDI payments
     7. Subtract a standard deduction equal to one-half of the disabled worker's own earned income. This deduction applies even when that earned income is itself excluded as sheltered-workshop income — the two treatments are independent (see Data Gap 7).
   - Countable income may not go below $0; the disregard order floors there.
   - **Operational thresholds** (Appendix J's own cent boundaries, which the calculator should use directly):

     | Assistance unit | Below 250% FPL | 250% up to and including 300% FPL |
     |---|---|---|
     | Single | $3,324.99 and below | $3,325.00 – $3,990.00 |
     | Couple | $4,508.99 and below | $4,509.00 – $5,410.00 |

   - A case at or below the 250% boundary is eligible. A case in the 250–300% band is eligible **only** if the entire excess above the 250% boundary is the disabled worker's own earned income (after the item-7 deduction); a premium applies in that band (see Benefit Value). Excess from any other source — a spouse's unearned income, a spouse's earned income above the item-2 disregard, or the worker's own unearned income beyond the SSI/$50-SSDI disregard — is **not** excluded and disqualifies at 250% FPL. Countable income above $3,990.00 (single) / $5,410.00 (couple) is ineligible regardless of source. **This criterion states the ordinary pass.** Where it would deny, Data Gap 7's inclusive pass then runs and may remove an unisolable earned-income, `veteran`, or `investment` stream, so a denial here alone is not the calculator's answer.
   - Assistance-unit rule: a TWHA case is evaluated as a single individual or a married couple, not by MFB's generic household size — both spouses' income and resources (criterion 4) count, dependent children do not enlarge the unit or raise the threshold, and both spouses can independently qualify if each separately meets all eligibility factors.
   - Source (rule): RSMo 208.146.1(4) — "Has income, as determined in subsection 3 of this section, that does not exceed two hundred fifty percent of the federal poverty level, excluding any earned income of the worker with a disability between two hundred fifty and three hundred percent of the federal poverty level." — [snapshot `2026-09-01--rsmo-208-146`](../../../sources/mo/mo_twha/2026-09-01--rsmo-208-146/content.md), accessed 2026-09-01
   - Source (disregards): RSMo 208.146.3(2), items (a)–(f) — "The first fifty thousand dollars of earned income of the person's spouse;", "A twenty dollar standard deduction;", "Health insurance premiums;", "A seventy-five dollar a month standard deduction for the disabled worker's dental and optical insurance when the total dental and optical insurance premiums are less than seventy-five dollars;", "All Supplemental Security Income payments, and the first fifty dollars of SSDI payments; and", "A standard deduction for impairment-related employment expenses equal to one-half of the disabled worker's earned income." — [snapshot `2026-09-01--rsmo-208-146`](../../../sources/mo/mo_twha/2026-09-01--rsmo-208-146/content.md), accessed 2026-09-01
   - Source (corroborating disregard list, the dental/optical actual-premium rule, and the half-earned deduction's independence from the sheltered-workshop exclusion): 0855.005.40 Income Requirement, under "Disregards for income determinations:" — "First $50,000 of the disabled worker’s spouse’s annual earned income", "Twenty dollar standard exemption", "Health insurance premiums", "Seventy-five dollar a month standard deduction for the disabled worker’s dental and optical insurance when the total dental and optical insurance premiums are less than seventy-five dollars. If the total dental and optical insurance premiums exceed $75, allow the actual premium." and "The disabled worker is entitled to this deduction even if the earned income is excluded from the gross income test as sheltered workshop income." — [snapshot `2026-08-24--dss-manual-0855-005-40`](../../../sources/mo/mo_twha/2026-08-24--dss-manual-0855-005-40/content.md), accessed 2026-08-24
   - **Source conflict (resolved — spouse's disability status)**: Appendix K qualifies this disregard as applying to a *non-disabled* spouse; the statute and operative manual do not. Resolved in favour of the statute and manual, which control over a summary appendix — and the unqualified reading is the inclusive one for a dual-TWHA couple the manual plainly contemplates. Appendix K is dated 07/2026, so this is a live conflict in a current document: an implementer who reads it should not "correct" the rule back. Sources in precedence order:
     - Controlling (statute): RSMo 208.146.3(2)(a) — "The first fifty thousand dollars of earned income of the person's spouse" — [snapshot `2026-09-01--rsmo-208-146`](../../../sources/mo/mo_twha/2026-09-01--rsmo-208-146/content.md), accessed 2026-09-01
     - Operative manual, agreeing: 0855.005.40 Income Requirement — "First $50,000 of the disabled worker’s spouse’s annual earned income" — [snapshot `2026-08-24--dss-manual-0855-005-40`](../../../sources/mo/mo_twha/2026-08-24--dss-manual-0855-005-40/content.md), accessed 2026-08-24
     - Corroborating the dual-TWHA couple: 0855.020.00 TWHA Couple Cases — "Both spouses can receive TWHA coverage if both meet all eligibility factors for TWHA." — [snapshot `2026-08-24--dss-manual-0855-020-00`](../../../sources/mo/mo_twha/2026-08-24--dss-manual-0855-020-00/content.md), accessed 2026-08-24
     - Outvoted (summary appendix, 07/2026): Appendix K — "First $50,000 of non-disabled" — the entry continues, line-wrapped, "spouse's annual income", which also drops "earned" — [snapshot `2026-08-24--appendix-k`](../../../sources/mo/mo_twha/2026-08-24--appendix-k/content.md), accessed 2026-08-24
   - Source (Temporary Assistance cash grant exclusion, incorporated into TWHA): 0855.005.40 Income Requirement — "Income Exclusions are allowed for the MO HealthNet Program as outlined in 0805.015.10 Income Exclusions." — [snapshot `2026-08-24--dss-manual-0855-005-40`](../../../sources/mo/mo_twha/2026-08-24--dss-manual-0855-005-40/content.md), accessed 2026-08-24; and the incorporated list: 0805.015.10 Income Exclusions — "Temporary Assistance cash grant" — [snapshot `2026-08-24--mhabd-0805-015-10`](../../../sources/mo/mo_twha/2026-08-24--mhabd-0805-015-10/content.md), accessed 2026-08-24
   - Source (single-individual-or-couple assistance unit): 0855.005.40 Income Requirement — "A TWHA participant’s need is determined as a single individual or a married couple. Review 0855.020.00 TWHA Couple Cases to determine eligibility for couples." — [snapshot `2026-08-24--dss-manual-0855-005-40`](../../../sources/mo/mo_twha/2026-08-24--dss-manual-0855-005-40/content.md), accessed 2026-08-24
   - Source (both spouses can independently qualify): 0855.020.00 TWHA Couple Cases — "Both spouses can receive TWHA coverage if both meet all eligibility factors for TWHA." — [snapshot `2026-08-24--dss-manual-0855-020-00`](../../../sources/mo/mo_twha/2026-08-24--dss-manual-0855-020-00/content.md), accessed 2026-08-24
   - Source (2026 dollar boundaries): MHABD Appendix J — "TWHA – Income and premiums effective 04-01-2026" table — "200% up to but not including 250%   Single                       2,660.00 – 3,324.99                                133" and "Couple                       3,607.00 – 4,508.99                                180" and "250% up to and including 300%       Single                       3,325.00 – 3,990.00                                200" and "Couple                       4,509.00 – 5,410.00                                271" — [snapshot `2026-08-24--mhabd-appendix-j-2026`](../../../sources/mo/mo_twha/2026-08-24--mhabd-appendix-j-2026/content.md), accessed 2026-08-24
   - Source (2026 FPL): Federal Register 91 FR (2026-00755), 48 CONTIGUOUS STATES AND THE DISTRICT OF COLUMBIA table — "1 ..................................................     $15,960" and "2 ..................................................      21,640" — [snapshot `2026-08-24--fr-2026-poverty-guidelines`](../../../sources/mo/mo_twha/2026-08-24--fr-2026-poverty-guidelines/content.md), accessed 2026-08-24

6. **Missouri resident (and intends to stay)**
   - Evaluation scope: config (enforced by which white label serves the screen, not a calculator condition)
   - Implementation note: "intends to stay" isn't observable from any screener field — see Data Gap 5. Residency is assumed met for any user routed to the MO white label (consistent with every other MO program).
   - Source (TWHA's own residence rule): 0855.005.20 Residence — "Residence requirements are the same as for Medical Assistance programs for the aged, blind and disabled. These requirements are found in Sections 1015.000.00 Residence (OAA, PTD, and AB) through 1015.020.25 Correspondence With Out-of-State Agency." — [snapshot `2026-09-02--dss-manual-0855-005-20-residence`](../../../sources/mo/mo_twha/2026-09-02--dss-manual-0855-005-20-residence/content.md), accessed 2026-09-02
   - Source (corroborating, plain-language): IM-4 TWHA brochure — "Living in Missouri (and intend to stay)" — [snapshot `2026-08-24--im4-twha-brochure`](../../../sources/mo/mo_twha/2026-08-24--im4-twha-brochure/content.md), accessed 2026-08-24

7. **U.S. citizen or qualified non-citizen**
   - Evaluation scope: config
   - Captured via: config `legal_status_required`: `citizen`, `gc_5plus`, `refugee`, `otherWithWorkPermission`
   - **Policy rule**: TWHA adopts Family MO HealthNet (MAGI) citizenship and immigrant-status rules wholesale. A qualified immigrant is one of the enumerated categories cited below. Those present before 8/22/96 face no waiting period. Those entering on or after 8/22/96 are sorted into two published lists — a **no-waiting-period group** (American Indians born in Canada, Amerasians, asylees, Cuban and Haitian entrants, withholding-of-removal cases, Iraqi and Afghan Special Immigrants, refugees, trafficking victims) and a **five-year-bar group** (lawful permanent residents, immigrants paroled ≥ 1 year, pre-4/1/1980 conditional entrants, battered immigrants), whose bar runs five years **from date of entry** and is expressly waived for active-duty U.S. Armed Forces members, veterans, their spouses and dependent children, and unmarried surviving spouses of veterans. Non-qualified immigrants are ineligible apart from emergency care. COFA migrants (Federated States of Micronesia, Palau, Marshall Islands) have been eligible since 2020-12-27.
   - **Committed MFB mapping.** Missouri's rule is more granular than MFB's status buckets. MFB collects no legal-status field on `Screen` or `HouseholdMember`; `legal_status_required` is applied as a results-page filter, so no calculator branch exists in either direction and the criterion is settled entirely in config.

     | `legal_status_required` value | Included | Basis |
     |---|---|---|
     | `citizen` | ✅ | Exact. |
     | `refugee` | ✅ | MFB's Refugee/Asylee bucket — the §207 refugee and §208 asylee no-waiting-period populations. |
     | `gc_5plus` | ✅ | The ordinary lawful permanent resident past the five-year bar. |
     | `otherWithWorkPermission` | ✅ | MFB's broader "Other Lawful" bucket — the remaining qualifying lawful and no-waiting-period categories with no MFB selection of their own, **including COFA migrants**. |
     | `gc_5less` | ❌ | Lawful Permanent Resident is the first category 1805.020.10.10.10 lists as barred. |
     | `non_citizen` | ❌ | 1805.020.10.15 makes non-qualified immigrants ineligible apart from emergency care. |

   - **Both directions of approximation**, none expressible by MFB:

     | Direction | Mismatch |
     |---|---|
     | Under-inclusive | Missouri's clock runs from **date of entry**; `gc_5less` measures time holding the green card. Someone who entered in 2010 and adjusted to LPR in 2025 selects `gc_5less` but is past Missouri's bar. |
     | Under-inclusive | The military/veteran/veteran-family waiver cannot be represented — `HouseholdMember.veteran` is collected, but `legal_status_required` is a flat filter that cannot be conditioned on another field. |
     | Under-inclusive | A current green-card status can obscure a prior exempt status (a refugee who later adjusted), which MFB does not record. |
     | Over-inclusive | `otherWithWorkPermission` is coarse and can admit lawful categories Missouri would bar, because MFB captures neither status subtype nor time in status. |

     Excluding `gc_5less` is deliberate: admitting it wholesale would admit the ordinary barred LPR in order to capture a set of narrow, enumerated exceptions. This is a systemic MFB platform constraint, not a TWHA-specific open question.
   - Source (TWHA incorporates the MAGI standard by reference): 0855.005.10 Residence and Citizenship — "Citizenship/Alien status requirements are the same as for the Family MO HealthNet (MAGI) program. Refer to MAGI Manual Section 1805.020.00 Citizenship and Immigrant Status." — [snapshot `2026-08-24--dss-manual-0855-005-10`](../../../sources/mo/mo_twha/2026-08-24--dss-manual-0855-005-10/content.md), accessed 2026-08-24
   - Source (who is a qualified immigrant): 1805.020.10 Immigrant Status — "A qualified immigrant is one who is:" followed by "A lawful permanent resident under the Immigration and Nationality Act (INA)", "A refugee (207 of INA)", "An asylee (208 of INA)", "An immigrant who has had deportation or removal withheld under 243(h) of (INA) or 241(b)(3)", "An immigrant granted parole for at least one year by the INS under 212(d)(5) of INA", "An immigrant granted conditional entry under 203(a)(7) of immigration law in effect before April 1, 1980", "An immigrant granted status as a Cuban or Haitian entrant (as defined in section 501(e) of the Refugee Education Assistance Act of 1980)", "A battered immigrant, as defined by P.L. 104-208", "An American Indian born in Canada, if s/he is at least one-half American Indian blood", "An Amerasian Immigrant; or" and "Trafficking Victim, as defined by the Trafficking Victims Act of 2000" — [snapshot `2026-09-01--mo-magi-1805-020-10`](../../../sources/mo/mo_twha/2026-09-01--mo-magi-1805-020-10/content.md), accessed 2026-09-01
   - Source (no waiting period for pre-8/22/96 arrivals): 1805.020.10.05 — "All qualified immigrants who were in the U.S. PRIOR to August 22, 1996, and who otherwise meet MO HealthNet eligibility criteria, are eligible." — [snapshot `2026-09-01--mo-magi-1805-020-10-05`](../../../sources/mo/mo_twha/2026-09-01--mo-magi-1805-020-10-05/content.md), accessed 2026-09-01
   - Source (the five-year bar for later arrivals): 1805.020.10.10 Qualified Alien Five-Year Bar — "Qualified immigrants entering the U.S. ON OR AFTER August 22, 1996, may be eligible for MO HealthNet immediately, or may be subject to a five-year period of ineligibility." — [snapshot `2026-08-24--mo-magi-1805-020-10-10`](../../../sources/mo/mo_twha/2026-08-24--mo-magi-1805-020-10-10/content.md), accessed 2026-08-24. The parent section states the two outcomes; its two child sections, cited next, resolve which arrivals fall into each.
   - Source (which post-8/22/96 arrivals have no waiting period): 1805.020.10.10.05 Qualified Immigrants With No Waiting Period — "Qualified immigrants entering the U.S. on or after August 22, 1996 who are members of one of the groups listed below have no waiting period" followed by "American Indians born in Canada", "Amerasian Immigrant", "Asylees under 208 of INA", "Cubans and Haitian entrants defined in Section 501(e) of the Refugee Education Assistance Act of 1980", "Immigrants for whom deportation or removal has been withheld under either 243(h) or 214(b)(3) of the INA", "Iraqi and Afghan Special Immigrants", "Refugees under 207 of INA" and "Trafficking Victim, as defined by the Trafficking Victims Act of 2000" — [snapshot `2026-09-01--mo-magi-1805-020-10-10-05`](../../../sources/mo/mo_twha/2026-09-01--mo-magi-1805-020-10-10-05/content.md), accessed 2026-09-01
   - Source (which post-8/22/96 arrivals are barred, and the exceptions): 1805.020.10.10.10 Qualified Immigrants With a Five-Year Period of Ineligibility — "Qualified immigrants entering the U.S. on or after August 22, 1996 who are not eligible for MO HealthNet for five years following their date of entry are listed below" followed by "Lawful Permanent Resident", "An immigrant granted parole for at least one year by the INS under 212(d)(5) of INA", "An immigrant granted conditional entry under 203(a)(7) of INA in effect before April 1, 1980" and "A battered immigrant, as defined by P.L. 104-208 is an immigrant:"; and the exception — "EXCEPTION: The five-year ineligibility period DOES NOT APPLY to the immigrants listed above if they are:" followed by "on active duty in the U.S. Armed Forces", "a veteran of the U.S. Armed Forces", "the spouse or dependent child of a veteran or active duty U. S. Armed Forces personnel" and "the unmarried surviving spouse of a veteran" — [snapshot `2026-09-01--mo-magi-1805-020-10-10-10`](../../../sources/mo/mo_twha/2026-09-01--mo-magi-1805-020-10-10-10/content.md), accessed 2026-09-01
   - Source (non-qualified immigrants): 1805.020.10.15 — "Non-qualified immigrants are ineligible for MO HealthNet benefits." — [snapshot `2026-09-01--mo-magi-1805-020-10-15`](../../../sources/mo/mo_twha/2026-09-01--mo-magi-1805-020-10-15/content.md), accessed 2026-09-01
   - Source (COFA migrants): 1805.020.10.20 — "Citizens of the Federated States of Micronesia, Republic of Palau and Republic of the Marshall Islands" who "are eligible to receive" MO HealthNet "As of December 27, 2020, in accordance with section 208 of the Federal Consolidated Appropriations Act, 2021" — [snapshot `2026-09-01--mo-magi-1805-020-10-20`](../../../sources/mo/mo_twha/2026-09-01--mo-magi-1805-020-10-20/content.md), accessed 2026-09-01
   - Source (MO-specific plain-language statement, corroborating): DB101 Missouri — "Immigrants who have been lawfully present for five years or longer and some other noncitizens who meet specific noncitizen requirements qualify for all of the same programs that U.S. citizens can get." — [snapshot `2026-08-24--db101-twha`](../../../sources/mo/mo_twha/2026-08-24--db101-twha/content.md), accessed 2026-08-24

## Missing Eligibility Criteria (Data Gaps)

1. **⚠️ Formal disability determination (PTD / Medically Improved)**
   - Why: Missouri establishes TWHA disability by SSI/Social Security disability receipt or an MRT determination, and MFB records neither. `long_term_disability` ("any medical or developmental condition that has lasted or is expected to last more than 12 months") is materially broader than an FSD/MRT Permanent and Total Disability finding; `visually_impaired` records self-reported vision loss, not a statutory blindness determination.
   - Handling: treat `long_term_disability OR visually_impaired` as an inclusive proxy (criterion 2). MFB may surface members who do not meet the statutory standard — the inclusive direction is committed rather than gating on a fact the screener cannot see.
   - Source: 0855.005.25 Disability Requirement — "Disability for the Basic Coverage Group will be determined either by receipt of SSI or Social Security based on disability, or the Medical Review Team (MRT)." — [snapshot `2026-08-24--dss-manual-0855-005-25`](../../../sources/mo/mo_twha/2026-08-24--dss-manual-0855-005-25/content.md), accessed 2026-08-24

2. **⚠️ Whether a reported earned-income stream satisfies TWHA's Medicare/Social Security tax rule, including the government-paid caregiver/homemaker exception**
   - Why: the screener records income amount, type, and frequency, but neither whether Medicare/Social Security taxes were withheld from (or paid on) a stream, nor whether an untaxed stream is the exempt government-paid caregiver or homemaker/chore work that qualifies anyway. Both halves are invisible to it.
   - Handling: assumed met — treat any reported `wages` or `selfEmployment` as qualifying earned income. The exception runs the same direction as the inclusive default, so this cannot false-deny on either half.
   - Source (the ordinary rule): RSMo 208.146.2 — "For income to be considered earned income for purposes of this section, the department of social services shall document that Medicare and Social Security taxes are withheld from such income." and "Self-employed persons shall provide proof of payment of Medicare and Social Security taxes for income to be considered earned." — [snapshot `2026-09-01--rsmo-208-146`](../../../sources/mo/mo_twha/2026-09-01--rsmo-208-146/content.md), accessed 2026-09-01
   - Source (the exception): 0855.005.30 Employment Requirement — "Effective February 1, 2017, participants will be considered in compliance with the statutory requirement to pay Medicare and Social Security taxes if they work in a medically related caregiver or homemaker/chore services position and the payment received is through a government agency such as DMH or DHSS where no such taxes are paid because the wages are specifically exempt and no such taxes are due." — [snapshot `2026-08-24--dss-manual-0855-005-30`](../../../sources/mo/mo_twha/2026-08-24--dss-manual-0855-005-30/content.md), accessed 2026-08-24

3. **⚠️ Medically Improved Group's 40-hours/month-at-minimum-wage employment threshold**
   - Why: no screener field distinguishes the Basic Coverage Group (no hours/earnings floor beyond earned income > $0) from the Medically Improved Group (≥ 40 hours/month at the federal minimum wage). Both groups receive identical Medicaid benefits, so there is no benefit-value consequence.
   - Handling: apply the Basic Coverage Group's rule (any earned income > $0) to every member. The 40-hour requirement is not a screener gate — gating on it would risk denying an otherwise-eligible Basic Coverage member who works fewer hours.
   - Source: 0855.005.30 Employment Requirement (see criterion 3 citation above)

4. **⚠️ Resource composition — MFB's assets question is narrower than Missouri's countable-resource definition, in both directions**
   - Why: `household_assets` (Screen, DecimalField) is a single aggregate figure covering cash, checking/savings, stocks, bonds, and mutual funds. Missouri's underlying Permanent and Total Disability resource framework is broader in one direction and narrower in the other, and MFB can reconcile neither:
     - **Reported total may overstate countable resources.** TWHA excludes retirement accounts entirely (criterion 4) and excludes medical savings and independent living accounts up to $5,000/year each in deposits and earnings. The screener can't separate account types out of the aggregate.
     - **Reported total may understate countable resources.** Under 13 CSR 40-2.030, FSD counts property of any kind the claimant owns or has an interest in, less encumbrances — which reaches real property not furnishing shelter, salable personal property, and the cash surrender or loan value of life insurance, subject to the PTD exemptions. None of these has a screener field, so a household can hold countable resources MFB never sees.
   - **Committed handling** (inclusive in both directions, per criterion 4): pass a household at or below the limit, and do not deny on assets alone when the reported figure exceeds it. An over-limit figure may be partly excluded account balances, so denying risks a false denial; an under-limit figure may omit countable resources, so passing may over-include. Reported assets alone never produce a hard ineligible determination. Neither direction is a screener field, so there is no branch to test.
   - Source (TWHA's exclusions): RSMo 208.146.3(1), items (a)–(b) — "Medical savings accounts limited to deposits of earned income and earnings on such income while a participant in the program created under this section with a value not to exceed five thousand dollars per year;" and "Independent living accounts limited to deposits of earned income and earnings on such income while a participant in the program created under this section with a value not to exceed five thousand dollars per year." — [snapshot `2026-09-01--rsmo-208-146`](../../../sources/mo/mo_twha/2026-09-01--rsmo-208-146/content.md), accessed 2026-09-01
   - Source (TWHA inherits MHABD's resource rules apart from retirement accounts): 0855.005.35 Resource Requirement — "Resource considerations, with the exception of retirement accounts, are the same as for MHABD individuals." — [snapshot `2026-08-24--dss-manual-0855-005-35`](../../../sources/mo/mo_twha/2026-08-24--dss-manual-0855-005-35/content.md), accessed 2026-08-24
   - Source (the breadth of the underlying PTD resource definition): 13 CSR 40-2.030(1) — "In determining eligibility for public assistance, the Family Support Division (FSD) shall consider property of any kind or character which the claimant owns or possesses or has an interest in, of which s/he is the record or beneficial owner, less encumbrances of record." And 13 CSR 40-2.030(5) — "Personal property is defined as household goods, jewelry, farm surpluses, livestock, farm or business machinery or equipment, automobiles and trucks, and similar items." And 13 CSR 40-2.030(4) — "The value of a life insurance policy at any time shall be the cash surrender value of the policy, minus the amount of any lien, loan, accrued interest payments or assigned portion of the policy." And, for real property held by a PTD applicant, 13 CSR 40-2.030(8) — "owns real property which is not furnishing shelter for him/her, its current market value shall be considered an available asset" — [snapshot `2026-09-01--13-csr-40-2-030`](../../../sources/mo/mo_twha/2026-09-01--13-csr-40-2-030/content.md), accessed 2026-09-01
   - Source (corroborating): Appendix K — Resource Levels — [snapshot `2026-08-24--appendix-k`](../../../sources/mo/mo_twha/2026-08-24--appendix-k/content.md), accessed 2026-08-24

5. **⚠️ "Intent to remain" in Missouri**
   - Why: no screener field records a stated intent to remain in the state
   - Handling: assumed-met for any user routed to the MO white label
   - Source: IM-4 TWHA brochure (see criterion 6 citation above)

6. **⚠️ Health insurance premium vs. dental/optical premium vs. medical bill, for the income disregards in criterion 5**
   - Why: MFB's screener collects a single generic `medical` expense category ("Medical Insurance Premium &/or Bills"); it can't isolate a health insurance premium from a medical bill, or a dental/optical premium from either
   - **Committed handling**: treat the full reported `medical` expense as the health-insurance-premium disregard (criterion 5, item 4), and always apply the $75/month dental-and-optical standard deduction (item 5) regardless of whether a `medical` expense was reported, since MFB cannot determine whether distinct dental/optical insurance exists. Both only reduce countable income, so this may slightly over-include borderline households rather than false-deny them.
   - Consequence for test construction: because the $75 deduction rests on an unobservable fact, no scenario's expected outcome may depend on it. See Test Scenarios § Scenario construction rule.

7. **⚠️ Sheltered workshop certified extended employment; the broader MHABD income exclusion list TWHA incorporates by reference**
   - Why: TWHA incorporates MHABD's general income exclusion list (0805.015.10) by reference. That list excludes income earned by individuals certified for extended employment at a sheltered workshop (at that workshop or elsewhere) from the income test entirely, while preserving the half-earned-income deduction; it also excludes LIHEAP, specific veteran-benefit sub-components (Aid and Attendance, dependent allowances, Unusual Medical Expenses, VA Housebound Allowance), vocational rehabilitation payments, ABLE account contributions/earnings/qualified distributions, and disaster-relief payments. No screener field records sheltered-workshop certification, and MFB's income categories are too coarse to isolate most sub-components. (The Temporary Assistance cash grant exclusion from the same list *is* observable — `cashAssistance` maps to it directly — so it is a normal rule in criterion 5, not a gap.)
   - **Scope**: both sources exclude income earned by *individuals* eligible for certified extended employment, without limiting that to the disabled applicant. Since the assistance unit is the individual or married couple (criteria 4 and 5), the exclusion reaches **any earned-income stream of any member whose income enters the unit** — applicant or spouse. Certification is a screener field for neither.
   - **Committed handling, by MFB income category:**
     - Wages/self-employment of any assistance-unit member (applicant or spouse): may be fully excluded if that member is eligible for certified extended employment (unobservable) — counted as reported per criterion 5's disregard order. For the **applicant's own** earned income the half-earned deduction applies under either treatment (criterion 5, item 7), so the treatments differ only in whether the gross amount enters the count. A **spouse's** earned income gets no half-earned deduction under either treatment — only the spouse earned-income disregard (criterion 5, item 2) — so for a spouse the treatments differ by the full post-disregard residue.
     - `veteran` ("Veteran's Pension or Benefits"): Missouri excludes only specific FSD-verified sub-components (Aid and Attendance, dependent allowance, Unusual Medical Expenses, Housebound Allowance), not veteran income categorically. MFB cannot isolate them, so the category is counted as reported.
     - `investment`: may contain excluded ABLE-account interest/dividends/earnings, but ordinary investment income is not excluded. MFB cannot distinguish them, so the category is counted as reported.
     - LIHEAP, disaster-relief payments, vocational rehabilitation payments, and the veteran/ABLE sub-components above have no corresponding MFB income category at all, so a household cannot report them — correctly never counted, no denial risk.
   - **Committed inclusive fallback (deterministic, two-pass).** Counting these amounts as reported is a computation default, not a denial ground. The calculator resolves the ambiguity by computing twice:
     1. **Ordinary pass** — compute countable income from reported income with every observable exclusion and disregard applied in criterion 5's order.
     2. **Inclusive pass** — if and only if the ordinary pass would return ineligible, recompute with **every** unisolable potentially-excluded component removed **in full**: the entire reported earned-income stream (`wages`, `selfEmployment`) of every assistance-unit member, the entire reported `veteran` stream, and the entire reported `investment` stream. Whole streams, not estimated portions — MFB cannot size a portion, so a portion-based rule would not be deterministic. The half-earned deduction still applies (criterion 5, item 7), and countable income floors at $0. No attribution judgment is needed about which amount "caused" the denial; the pass either changes the outcome or it does not.
     3. **Return ineligible only if countable income still exceeds the 250% boundary after the inclusive pass** ($3,324.99 single / $4,508.99 couple). Eligible otherwise. The 250–300% band ceiling is not a second limit at this step: pass 2 removes `wages` and `selfEmployment` in full — which is exactly MFB's `earned` selector — so no earned income survives into this comparison and the band allowance, which covers only worker-earned excess, can never apply here. The band ceiling governs the **ordinary** pass (criterion 5), where earned income is still present.
     4. The 300% FPL maximum stays binding, and applies to income remaining **after** applicable exclusions — never a reason to make sheltered-workshop income count. The two rules are structurally different: the 250–300% allowance is a *disregard* applied within the income test and switched off above 300% (the manual's "**this** income disregard is not applied" scopes the switch-off to that allowance), whereas sheltered-workshop earnings are *excluded from the gross income test* and so never enter the computation the ceiling measures. An exclusion that removes income before the test cannot be defeated by a ceiling operating on the test's result; the half-earned deduction confirms the ordering, surviving even when the income it is computed from is excluded. **Step 4 is MFB's committed reading of an ambiguity the sources leave open**: the manual never defines "gross income test", so it does not state outright that Appendix J's maximum measures post-exclusion income. The alternative reading would let the ceiling defeat an exclusion the manual grants, so this spec resolves it inclusively.
   - Source (the 250–300% allowance is a disregard, and it is that disregard the 300% rule switches off): 0855.005.40 Income Requirement — "Note: Earned income of the disabled worker from 250% to 300% of the FPL is disregarded. If the participant is above 300% of the FPL, this income disregard is not applied as the participant is not eligible." — [snapshot `2026-08-24--dss-manual-0855-005-40`](../../../sources/mo/mo_twha/2026-08-24--dss-manual-0855-005-40/content.md), accessed 2026-08-24
   - Source (the income maximum itself is binding, step 4): 0855.005.40 Income Requirement — "Individuals cannot spend down to obtain this coverage. Individuals with income above the monthly income maximum are not eligible for TWHA." — [snapshot `2026-08-24--dss-manual-0855-005-40`](../../../sources/mo/mo_twha/2026-08-24--dss-manual-0855-005-40/content.md), accessed 2026-08-24
   - Source (sheltered-workshop earnings are excluded from the gross income test itself, not disregarded within it): 0855.005.40 Income Requirement — "The disabled worker is entitled to this deduction even if the earned income is excluded from the gross income test as sheltered workshop income." — [snapshot `2026-08-24--dss-manual-0855-005-40`](../../../sources/mo/mo_twha/2026-08-24--dss-manual-0855-005-40/content.md), accessed 2026-08-24
   - **What the fallback reaches.** It is deliberately over-inclusive and **does** remove income Missouri would count: for a worker holding no certification Missouri counts the wages pass 2 removes, and Missouri never excludes an entire veteran's pension for anyone (only FSD-verified portions), so removing the whole `veteran` stream over-excludes by construction. That is the accepted cost of a deterministic rule MFB can run without the isolating facts. It never touches unearned income outside the enumerated exclusion list — a pension, for instance — which still denies (Scenarios 10 and 18).
   - **Product-visible consequence.** Because a whole earned-income stream can be removed, **a household whose excess is entirely earned income is always returned eligible, at any income level** — a single filer reporting $10,000/month of `wages` passes. Intended, but MFB's practical earned-income ceiling is therefore unbounded, and the program description must not present an income ceiling as a screening outcome. Verified by unit tests on the countable-income helper (Implementation), not a household scenario.
   - Consequence for test construction: no scenario's ineligible outcome may rest on any assistance-unit member's earned income, or on a `veteran` or `investment` amount, being the deciding income — pass 2 removes those streams, so such a fixture returns eligible by design. See Test Scenarios § Scenario construction rule.
   - 0805.015.10's "Department of Mental Health Funds" is **not** a fourth unisolable component: criterion 3 relies on DMH-paid caregiver wages being *qualifying earned income*, and the surrounding list items are assistance payments to clients rather than wages. Read the other way, pass 2 already removes the earned stream in full, so no outcome changes.
   - Source (TWHA-specific sheltered-workshop exclusion): 0855.005.40 Income Requirement — "Note: Exclude any income earned by individuals eligible for certified extended employment at a sheltered workshop. This exclusion applies to income earned at both a sheltered workshop and a different employer when the individual is certified for extended employment at a sheltered workshop." — [snapshot `2026-08-24--dss-manual-0855-005-40`](../../../sources/mo/mo_twha/2026-08-24--dss-manual-0855-005-40/content.md), accessed 2026-08-24
   - Source (the incorporated MHABD exclusion list): 0805.015.10 Income Exclusions — "Any income earned by individuals eligible for certified extended employment at a sheltered workshop. This includes income earned from employment at a sheltered workshop and from other employers." / "Achieving a Better Life Experience (ABLE) account. Third-party contributions to and interest, dividends, or other distributed earnings in an ABLE account." / "Vocational Rehabilitation Payments – Payments made for maintenance, transportation, tuition, fees, etc., in connection with a claimant participating in training or school attendance subsidized by the Division of Vocational Rehabilitation." — [snapshot `2026-08-24--mhabd-0805-015-10`](../../../sources/mo/mo_twha/2026-08-24--mhabd-0805-015-10/content.md), accessed 2026-08-24
   - Source (veteran-benefit sub-component exclusions, confirming these are FSD-verified portions, not categorical): 0805.015.10 Income Exclusions — "Any portion of a veteran’s pension designated for Aid and Attendance." / "Any benefits designated for a veteran’s dependent." / "Any portion of a veteran’s pension paid for Unusual Medical Expenses, also known as unreimbursed medical expenses." / "VA Housebound Allowances, also known as Home Bound, may increase a monthly pension when the veteran is confined to their home due to a permanent disability." — each requires "verification from the Veterans Administration to determine what portion of the payment is designated" as the excluded component — [snapshot `2026-08-24--mhabd-0805-015-10`](../../../sources/mo/mo_twha/2026-08-24--mhabd-0805-015-10/content.md), accessed 2026-08-24

## Priority Criteria

None.

## Benefit Value

- Value: **$12,200/year per eligible TWHA member** — an MFB estimated value of Medicaid coverage, not a cash payment, not a guaranteed amount of medical care, and not an estimate of what a specific member will personally receive or save.
- `value_format`: `null` (MFB's default monthly display)
- `low_confidence`: `false` (MFB default — the badge is not routinely used)
- Variation axes: flat per eligible member (multiply by the count of eligible household members). One eligible member → $12,200/year; two → $24,400/year.
- **Display contract**: the calculator returns the **annual** per-member value; the frontend derives the monthly figure. With `value_format: null` the results card renders `programValue ÷ 12` at whole-dollar precision — **$1,017/month** for one member ($12,200 ÷ 12 = $1,016.67), **$2,033/month** for two ($24,400 ÷ 12 = $2,033.33). The program detail page does not divide: it shows **"Estimated Annual Value — $12,200"**, which is the accurate label for an expenditure-based estimate (`estimated_annual` would instead label it "Average Annual Savings", overclaiming for a value that is not savings received). Compute two-member households as $12,200 × 2 = $24,400 *before* the frontend divides. Scenario assertions are annual: they assert calculator output, not display.
  - **Why `null` and not `estimated_annual`**: the field only selects the card's cadence — the calculator stores the annual value either way. This follows the KS Working Healthy precedent: its seed config carries `estimated_annual`, but the **prod config was changed to Monthly after import**, so the card shows ≈$1,588/month from the stored $19,051 rather than "$19,051/year" (`member_amount` unchanged). Setting `null` in TWHA's seed config means it ships correct rather than needing the same post-import prod edit. WA Apple Health is the in-repo precedent for the pattern — annual per-member value stored, `value_format: null`.
- **Methodology**: Missouri's average Medicaid benefit spending per full-year-equivalent (FYE) enrollee, all enrollees, FY2024 — $15,891,669,916 ÷ 1,302,603 FYE enrollees = **$12,200**. MACPAC publishes this per-FYE figure directly; MFB does not recompute it, so there is no rounding step. FYE is MACPAC's own denominator; MACPAC notes that FYE may also be referred to as average monthly enrollment, which avoids the partial-year ambiguity that affects raw participant counts.
- **Why a statewide proxy, not the TWHA-specific mean.** Missouri publishes TWHA-specific spending, giving a well-sourced program mean of **$46,819/year**: Missouri reports $101,176,849 in SFY2025 TWHA spending ($65,451,021 premium + $35,725,828 non-premium) across 2,161 participants (1,489 premium + 672 non-premium). MFB deliberately does not display it: TWHA spending is concentrated in ID/DD waiver services — in December 2025, **$7,180,100.79 of $10,089,876.89 combined (71%)**, reaching 299 + 271 = 570 recipients against 1,588 + 918 = 2,506 enrollees. (Recipients and enrollees are different columns and not a strict subset, so no share *of enrollees* is asserted.) The mean is a valid accounting figure but a poor proxy for a typical member. Candidates considered:

  | Candidate | Annual | Disposition |
  |---|---|---|
  | TWHA program mean | $46,819 | Rejected — accurate accounting, but heavily influenced by ID/DD waiver spending and therefore not representative of typical member utilization |
  | MO disabled-Medicaid average | $30,231–$32,702 | Rejected — same LTSS concentration; the class of figure MFB already rejected on KS Working Healthy |
  | KS Working Healthy | $19,051 | Sound sibling benchmark, but Kansas-specific |
  | TWHA non-waiver sensitivity | ~$13,933 | Constructed, not published — one month, point-in-time enrollment, waiver stripped while those members stay in the denominator |
  | **MO all-Medicaid per FYE** | **$12,200** | **Chosen** — a published Missouri-wide Medicaid benchmark that avoids relying on TWHA's unusually concentrated waiver spending |

- The premium (criterion 5, and the schedule below) is **not** netted from this value — it is a separate, income-tiered monthly cost surfaced in the program description.
- Source (the displayed value): MACPAC Exhibit 23, Medicaid Benefit Spending per Full-Year Equivalent Enrollee, FY2024 (February 2026) — Missouri row: "Missouri                          1,302,603        15,891,669,916          12,200            333,562         2,724,330,914             8,167" — and the exhibit's own definition of the denominator: "FY is fiscal year. FYE is full-year equivalent." The same note adds that FYE may also be referred to as average monthly enrollment. — [snapshot `2026-08-24--macpac-exhibit-23-fy2024`](../../../sources/mo/mo_twha/2026-08-24--macpac-exhibit-23-fy2024/content.md), accessed 2026-08-24
- Source (the TWHA-specific mean this decision declines to display): HB 2372 Fiscal Note, L.R. No. 5868S.08A (Committee on Legislative Research, Oversight Division, May 13, 2026) — "The Ticket to Work program cost the DSS $65,451,021 in SFY 2025 for the premium program and $35,725,828 in SFY 2025 for the non-premium program." and "During SFY 2025, approximately 1,489 individuals participated in the premium program and 672 in the non-" (the source PDF hyphenates across a line break here; the sentence completes "premium program.") — [snapshot `2026-09-01--hb2372-fiscal-note-5868s08a`](../../../sources/mo/mo_twha/2026-09-01--hb2372-fiscal-note-5868s08a/content.md), accessed 2026-09-01
- Source (the waiver concentration behind that decision — **offline retained document**; the originating DSS URL `https://dss.mo.gov/re/pdf/fsd_mhdmr/1225-family-support-mohealthnet-report.pdf` is preserved as provenance only and returns **404 as of 2026-09-02**, as does the whole `/re/pdf/fsd_mhdmr/` tree): DSS FSD/MHD Monthly Management Report, December 2025, Table 21 — "MO HEALTHNET RECIPIENTS AND PAYMENTS BY ELIGIBILITY CATEGORY" — "ELIGIBILITY CATEGORY: TICKET TO WORK - PREMIUM" / "NUMBER OF ELIGIBLES ENROLLED ON 12/31/25: 1,588" / "     ID/DD WAIVER                                   $3,943,201.17          299" / "TOTAL                                               $5,959,986.10"; and "ELIGIBILITY CATEGORY: TICKET TO WORK - NON-PREMIUM" / "NUMBER OF ELIGIBLES ENROLLED ON 12/31/25: 918" / "     ID/DD WAIVER                                   $3,236,899.62          271" / "TOTAL                                               $4,129,890.79" — [snapshot `2026-08-24--fsd-mhd-report-dec2025`](../../../sources/mo/mo_twha/2026-08-24--fsd-mhd-report-dec2025/content.md), accessed 2026-08-24. Rows re-read from the retained snapshot and confirmed on 2026-09-02; `sha256_raw` and `sha256_content` both match the manifest.

### 2026 premium schedule (not netted from Benefit Value — see criterion 5)

| Countable income (% FPL) | Single | Couple |
|---|---|---|
| Less than 100% | $0 | $0 |
| 100% up to but not including 150% | $53 | $72 |
| 150% up to but not including 200% | $80 | $108 |
| 200% up to but not including 250% | $133 | $180 |
| 250% up to and including 300% | $200 | $271 |

- Source: MHABD Appendix J — "TWHA – Income and premiums effective 04-01-2026" table — "Less than 100%                      Single                   $       1,330.00 or less        $                          0" / "100% up to but not including 150%   Single                       1,330.01 – 1,994.99                                   53" and "Couple                       1,804.01 – 2,704.99                                   72" / "150% up to but not including 200%   Single                       1,995.00 – 2,659.99                                   80" and "Couple                       2,705.00 – 3,606.99                                 108" (the 200–250% and 250–300% rows are cited in criterion 5) — [snapshot `2026-08-24--mhabd-appendix-j-2026`](../../../sources/mo/mo_twha/2026-08-24--mhabd-appendix-j-2026/content.md), accessed 2026-08-24
- The premium is surfaced to the user, not computed as a calculator output. Its band moves with the sheltered-workshop treatment of any assistance-unit member's earned income (Data Gap 7), so no test scenario asserts a premium amount.

## Implementation

- Age (criterion 1) must be computed from `birth_year_month` against `screen.get_reference_date()`, month-precision — not from a precomputed `age` integer — since the 65-and-under boundary is inclusive of the birth month itself. `Screen.get_reference_date()` returns the earliest validation's date for a frozen screen and today's date otherwise. Do not use `Screen.submission_date` as the age reference date: the field does exist, but `get_reference_date()` never reads it — a submitted screen with no validations still resolves to today — so the two are not interchangeable.
- Countable income (criterion 5) must be derived from the itemized statutory disregards in the committed order, then compared against the operational thresholds in criterion 5's table — not by comparing gross income directly to Appendix J's $3,990/$5,410 figures, which would silently misclassify any household with a spouse, SSI, SSDI, or a mix of earned/unearned income.
- Earned income (criterion 3) must be read through the `earned` selector, which includes the `wages` and `selfEmployment` income types.
- `cashAssistance` is excluded from countable income unconditionally (criterion 5, item 1).
- TWHA's assistance unit (criteria 4 and 5) is the single individual or married couple, not MFB's generic household size — both spouses' income and resources count, dependent children neither enlarge the unit nor raise the income or asset thresholds, and each spouse is independently evaluated (a couple pays only one premium).
- The half-earned-income deduction (criterion 5, item 7) applies whether or not the earned income it is computed from is itself excluded as sheltered-workshop income.
- **Other coverage (employer-sponsored insurance and HIPP) is post-eligibility coordination of benefits, not an eligibility criterion.** A member holding employer-sponsored insurance — `Insurance.employer`, via `has_insurance_types(("employer",))` — **must not** be made ineligible, and `employer` must not appear in any eligibility gate. Both sources govern people who are *already* eligible: the statute conditions on "an eligible person's employer", the manual on "an eligible participant's employer". Where DSS finds employer coverage more cost-effective the participant must enrol, DSS pays their share of premiums, co-payments and other participation costs (scoped to costs "for MO HealthNet covered services"), and TWHA becomes the statutory secondary/supplemental coverage for personal care assistance services, related costs, and non-emergency medical transportation. None of that is a screening determination: MFB cannot make the cost-effectiveness finding, HIPP staff do (referral via form HIPP-1 whenever the employer offers coverage), and the member is eligible either way. Scenario 19 pins the behavioural half; that `employer` is absent from every gate is a code-review check, since a gate combining it with another condition could still pass that scenario.
  - Source (statute, conditioned on an already-eligible person): RSMo 208.146.6 — "If an eligible person's employer offers employer-sponsored health insurance and the department of social services determines that it is more cost effective, such person shall participate in the employer-sponsored insurance." / "The department shall pay such person's portion of the premiums, co-payments, and any other costs associated with participation in the employer-sponsored health insurance." / "the medical assistance provided under this section shall be provided to an eligible person as a secondary or supplemental policy for only personal care assistance services, as defined in section 208.900, and related costs and nonemergency medical transportation to any employer-sponsored benefits that may be available to such person" — [snapshot `2026-09-01--rsmo-208-146`](../../../sources/mo/mo_twha/2026-09-01--rsmo-208-146/content.md), accessed 2026-09-01
  - Source (TWHA's own HIPP section, likewise conditioned on an eligible participant): 0855.025.00 HIPP — "If an eligible participant’s employer offers employer-sponsored health insurance and the MO HealthNet Division (MHD) determines that it is cost effective, the individual must participate in the employer-sponsored insurance. The Department of Social Services will pay the participant’s portion of the premiums, co-payments, and any other costs associated with participation in the employer-sponsored health insurance." — [snapshot `2026-09-01--dss-manual-0855-025-00-hipp`](../../../sources/mo/mo_twha/2026-09-01--dss-manual-0855-025-00-hipp/content.md), accessed 2026-09-01
- **The countable-income calculation must be factored into a separately testable helper** returning, alongside the total, each income stream's contribution to the count and each disregard's applied amount. This is an internal test seam, not a user- or API-facing output. Six scenarios (9, 11, 12, 13, 14, 16) assert against that output — a stream's contribution, a disregard's amount, or the total — rather than the binary outcome, because their rules have no outcome to flip. Data Gap 7's fallback and criterion 4's asset handling are verified by unit tests on this helper plus code review, not household scenarios, since their deciding facts are unobservable.
- The data gaps above are inclusive limitations, not silently resolved — no screening rule should treat an unresolved data gap as grounds for denial.
- **Implement Data Gap 7's inclusive fallback exactly as its four numbered steps specify** — a two-pass computation, whole streams never estimated portions, no judgment about which amount caused the denial, and the post-pass-2 comparison against the **250% boundary** ($3,324.99 single / $4,508.99 couple), not the 300% band ceiling. Unearned income outside the exclusion list is untouched by pass 2 and still denies (Scenarios 10 and 18). Pass 2's presence is verified by a unit test on the countable-income helper: an earned-income-only household above the 300% maximum must return eligible after the recompute.

## Acceptance Criteria

- [ ] All 19 test scenarios below pass.
- [ ] A member holding employer-sponsored insurance is eligible — verified behaviourally by Scenario 19, contrasted with Scenario 1. That `Insurance.employer` appears in no eligibility gate is the stronger structural claim and is a code-review check, not something a passing scenario establishes.
- [ ] Age is evaluated month-inclusively at both ends of the 16–64 range (Scenarios 2–6).
- [ ] No calculator behavior denies a household on assets alone when reported assets exceed the limit (criterion 4's committed handling). This is a code-review check, not a scenario assertion — no fixture reports assets above a standard, because criterion 4 gives that case no distinct outcome to assert (Known scenario gaps).
- [ ] Criterion 5 is evaluated via the itemized disregard order, not a direct Appendix-J comparison — verified by the spouse-, SSI-, SSDI-, and cash-assistance-disregard scenarios (11, 12, 13, 16), each of which would fail under a naive gross-income comparison.
- [ ] The spouse earned-income disregard applies regardless of the spouse's own disability status (Scenario 14).
- [ ] The 250–300% allowance attributes the excess above the 250% boundary to its source, not to whatever income places the case in the band — verified by Scenario 9's intermediate assertion of a $2,000 `wages` contribution with a $1,000 half-earned deduction (its Eligible verdict alone cannot show this, since pass 2 would also admit it while reporting $0), contrasted with Scenario 10, where the excess is a spouse's unearned income that neither the allowance nor pass 2 reaches.
- [ ] Criteria 4 and 5 are evaluated against the single-individual-or-married-couple assistance unit, not generic household size — verified by Scenario 18 (dependent children do not raise the income threshold) and Scenario 14's two-member value. Selection of the couple *resource* standard is a code-review check: criterion 4 forbids denying on reported assets, so the standard chosen has no outcome to flip.
- [ ] Both `wages` and `selfEmployment` satisfy the earned-income criterion (Scenarios 1 and 17).
- [ ] No gap in the Data Gaps section is a denial ground. Data Gap 7's two-pass fallback is implemented as specified: an ineligible result is returned only after recomputing with every unisolable potentially-excluded stream removed in full and the household still exceeding the 250% boundary. Enforced by a unit test on the countable-income helper — an earned-income-only household above the 300% maximum must return eligible after the recompute — plus code review, since the deciding fact is unobservable and cannot carry a household scenario.
- [ ] The 300% FPL maximum is applied to income remaining *after* applicable exclusions, and is not used to bring sheltered-workshop income into the count — the manual switches off the 250–300% *disregard* above 300%, while sheltered-workshop earnings are excluded from the gross income test itself. Exercised by the same helper unit test.
- [ ] Unearned income outside the exclusion list still produces ineligible results — the fallback does not swallow the income test (Scenarios 10 and 18).
- [ ] No test asserts, in either direction, whether a member is certified for extended employment or whether a household carries dental/optical insurance — neither is a screener field (Scenario construction rule).
- [ ] The calculator returns the **annual** value: $12,200/year per eligible member, multiplied by the count of eligible members (Scenarios 1 and 14; two members is $24,400). MACPAC publishes the per-FYE figure directly, so there is no rounding step. Monthly presentation is a frontend concern driven by `value_format: null` ($1,017 and $2,033 respectively) and is not asserted by any calculator test.
- [ ] Age is evaluated against `screen.get_reference_date()`, which tests pin to 2026-09-01.

## Test Scenarios

**Scenario construction rule**: two facts this spec relies on are unobservable — whether a household carries distinct dental/optical insurance (Data Gap 6), and whether any assistance-unit member is eligible for certified extended employment (Data Gap 7, which reaches a spouse's earned income as well as the applicant's). MFB's committed handling resolves both deterministically, so output for a given fixture is predictable: the $75 deduction is always applied, and Data Gap 7's fallback always runs the same way.

**Coverage map**

| Rule / variation axis | Scenarios |
|---|---|
| Age 16–64, inclusive of 16th/65th birthday month (member) | 1 (pass, golden path), 3 (boundary pass, 16), 4 (boundary pass, 64), 5 (boundary pass, 65th-birthday month); 2 (boundary fail, 15), 6 (boundary fail, one month past 65) |
| Qualifying disability proxy (member) | 1 (pass, `long_term_disability`); 15 (pass, `visually_impaired` alone — proves the OR); 7 (fail — neither field) |
| Employed with earned income (member) | 1 (pass, `wages`); 17 (pass, `selfEmployment`); 8 (fail — no earned income) |
| Countable income ≤ 250% FPL, with the disabled worker's earned income allowed 250–300% FPL, and the excess attributed to a source | 1 (pass, low income); 9 (intermediate assertion: the helper reports a $2,000 `wages` contribution, which the inclusive path would report as $0 — the Eligible result alone cannot discriminate); 10 (fail — same band, but the excess is a spouse's unearned income, which neither the allowance nor the inclusive pass reaches) |
| Statutory income disregards | 11 (spouse's first-$50,000/year earned income, ordinary spouse); 14 (the same disregard where the spouse is **also** a disabled worker); 12 (SSI in full); 13 (first $50 of SSDI); 16 (Temporary Assistance cash grant) |
| Assistance unit is an individual or married couple, not household size | 18 (dependent children do not raise the income threshold — eligibility branch); 14 (both spouses independently evaluated, two-member value) |
| Benefit value scales per eligible member | 1 (1 member, $12,200); 14 (2 eligible members, $24,400) |
| Employer-sponsored insurance does not disqualify (post-eligibility HIPP coordination) | 19 (pass, `Insurance.employer` set — contrasts with 1, the same fixture without it) |
| U.S. citizen or qualified non-citizen (config) | enforced by config `legal_status_required`, not a calculator-evaluated screener field — not a scenario |
| Missouri residency (config) | enforced by white-label routing — not a scenario |
| Premium amount (cost-sharing) | documented in criterion 5 and Benefit Value; not scenario-tested — the premium is surfaced, not a calculator output, and its band moves with an unobservable fact |

**Known scenario gaps** — the following are not scenario-tested because the deciding fact is unavailable to the screener:

- The Basic Coverage / Medically Improved Group split (Data Gap 3): the screener carries one generic disability signal and cannot observe which group a member is in. The more permissive Basic Coverage rule applies to all members.
- The formal PTD/MRT disability determination (Data Gap 1): Scenario 15 exercises MFB's `long_term_disability OR visually_impaired` proxy mapping, not a statutory blindness pathway.
- The resource limit and resource composition (Data Gap 4): reported assets alone never produce an ineligible determination (criterion 4), so no reported figure — under, at, or over the limit — changes the outcome. Selection of the applicable standard is verified by code review instead. Neither the TWHA-excluded account types nor the additional resources Missouri's PTD framework counts are screener fields, so there is no branch to test.
- The health-insurance-premium and $75 dental/optical deductions (Data Gap 6): both are applied unconditionally rather than branching on a distinguishing fact, so there is no branch to test.
- Sheltered-workshop certification (Data Gap 7): no scenario states whether a member holds certification, and none asserts an outcome turning on a `veteran` or `investment` amount. An income-decided *ineligible* outcome can never turn on any member's earned income, since pass 2 removes the stream — so such a scenario is impossible to write, not merely omitted. The fallback is verified outside the scenario set by a unit test on the countable-income helper; Scenarios 10 and 18 bound it from the other side, and Scenario 9's intermediate shows it did not fire where the ordinary pass sufficed.
- TWHA Medicare/Social Security tax-rule treatment (Data Gap 2) and Missouri residency intent (Data Gap 5): assumed met, no branch.
- Criteria 6 and 7 (residency, citizenship) are enforced by config, not by any screener field a calculator could branch on.
- The HIPP cost-effectiveness determination (Implementation, Other coverage): MFB cannot make it and it does not affect eligibility, so only the inclusive half is testable — Scenario 19 proves employer coverage does not disqualify. Whether a member is actually routed to HIPP, and the resulting secondary/supplemental service scope, are outside what the screener models.

All scenarios assume a calculator reference date of **2026-09-01** — on or after the program's 2026-08-28 effective date. Tests must pin or patch `Screen.get_reference_date()` to 2026-09-01; ages are expressed via `birth_year`/`birth_month` and are meaningless without that pin. MO LIHEAP and MA BSP already establish this pattern (`patch.object(Screen, "get_reference_date", ...)`).

### Scenario 1: Golden path — Eligible, $12,200
**What we're checking**: a working-age disabled worker with low earned income qualifies.
**Expected**: Eligible — $12,200 (1 eligible member × $12,200/year)

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Birth month/year: `January 1986` (age 40), Relationship: `Head of Household`, Long-term disability: `Yes`, Has income: `Yes`, Income type: `wages`, Income amount: `$1,000` per month
- **Assets**: Household resources: `$0`
- **Current Benefits**: Select no current benefits

**Why this matters**: the golden path — disabled, employed, low income — resolves to eligible at the full per-member value with no other rule tripping.

---

### Scenario 2: Age boundary — Ineligible, below the age-16 floor
**What we're checking**: the age-16 floor.
**Expected**: Ineligible (member is younger than the 16-year age floor)

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Birth month/year: `August 2011` (age 15), Relationship: `Head of Household`, Long-term disability: `Yes`, Has income: `Yes`, Income type: `wages`, Income amount: `$1,000` per month
- **Assets**: Household resources: `$0`
- **Current Benefits**: Select no current benefits

**Why this matters**: turns 16 in August 2027, after the reference date. Protects the program-specific age floor against a generic minor-employment assumption.

---

### Scenario 3: Age boundary — Eligible, the calendar month of the 16th birthday, $12,200
**What we're checking**: age 16 is included, and the floor is month-inclusive at its first month.
**Expected**: Eligible — $12,200

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Birth month/year: `September 2010` (age 16), Relationship: `Head of Household`, Long-term disability: `Yes`, Has income: `Yes`, Income type: `wages`, Income amount: `$1,000` per month
- **Assets**: Household resources: `$0`
- **Current Benefits**: Select no current benefits

**Why this matters**: turns 16 in the 2026-09 reference month. Protects `age >= 16` against an off-by-one `age > 16`, per 0855.005.05's "includes the month the person turns age 16".

---

### Scenario 4: Age boundary — Eligible, age 64, $12,200
**What we're checking**: age 64 is included, not excluded.
**Expected**: Eligible — $12,200

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Birth month/year: `August 1962` (age 64), Relationship: `Head of Household`, Long-term disability: `Yes`, Has income: `Yes`, Income type: `wages`, Income amount: `$1,000` per month
- **Assets**: Household resources: `$0`
- **Current Benefits**: Select no current benefits

**Why this matters**: protects `age <= 64` against an off-by-one `age < 64`.

---

### Scenario 5: Age boundary — Eligible, the calendar month of the 65th birthday, $12,200
**What we're checking**: eligibility runs through the entire calendar month in which the person turns 65 — the ceiling is month-inclusive, not "under 65 as of the screen date."
**Expected**: Eligible — $12,200

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Birth month/year: `September 1961` (age 65), Relationship: `Head of Household`, Long-term disability: `Yes`, Has income: `Yes`, Income type: `wages`, Income amount: `$1,000` per month
- **Assets**: Household resources: `$0`
- **Current Benefits**: Select no current benefits

**Why this matters**: turns 65 in the 2026-09 reference month. Protects the month-inclusive ceiling against a strict "age as of today < 65" test, per 0855.005.05's "includes the month the person turns age ... 65".

---

### Scenario 6: Age boundary — Ineligible, one month past the 65th birthday
**What we're checking**: the age-64 ceiling is enforced once the birthday month has fully passed.
**Expected**: Ineligible (member has aged out of the 16–64 range)

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Birth month/year: `August 1961` (age 65), Relationship: `Head of Household`, Long-term disability: `Yes`, Has income: `Yes`, Income type: `wages`, Income amount: `$1,000` per month
- **Assets**: Household resources: `$0`
- **Current Benefits**: Select no current benefits

**Why this matters**: turned 65 one month before the 2026-09 reference month. Paired with Scenario 5 — the ceiling exists and is month-inclusive, so this member is excluded because the birthday month ended, not because the ceiling is miscomputed.

---

### Scenario 7: No qualifying disability — Ineligible
**What we're checking**: the disability requirement is enforced, not waived for an otherwise-qualifying working adult.
**Expected**: Ineligible (neither disability field is set)

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Birth month/year: `January 1986` (age 40), Relationship: `Head of Household`, Long-term disability: `No`, Visually impaired: `No`, Has income: `Yes`, Income type: `wages`, Income amount: `$1,000` per month
- **Assets**: Household resources: `$0`
- **Current Benefits**: Select no current benefits

**Why this matters**: protects against dropping the disability condition and admitting any working adult in the age range.

---

### Scenario 8: No earned income — Ineligible
**What we're checking**: the employment/earned-income requirement.
**Expected**: Ineligible (not employed / no earned income)

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Birth month/year: `January 1986` (age 40), Relationship: `Head of Household`, Long-term disability: `Yes`, Has income: `No`
- **Assets**: Household resources: `$0`
- **Current Benefits**: Select no current benefits

**Why this matters**: protects against admitting a disabled, non-working adult — this is the *working*-disabled buy-in, not a general disability Medicaid pathway.

---

### Scenario 9: Worker's own earned income carries the case into the 250–300% FPL band — Eligible, $12,200
**What we're checking**: the 250–300% FPL allowance admits a case whose countable income exceeds the 250% boundary *because of the worker's own earned income*, in a household that also has unearned income — the calculator must attribute the excess to a source, not merely compare a total.
**Expected**: Eligible — $12,200. Intermediate assertion: the helper reports Person 1's `wages` stream contributing **$2,000** to the count, with a **$1,000** half-earned deduction applied.

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Birth month/year: `January 1986` (age 40), Relationship: `Head of Household`, Long-term disability: `Yes`, Has income: `Yes`, Income: `wages` `$2,000` per month and `pension` `$2,500` per month
- **Assets**: Household resources: `$0`
- **Current Benefits**: Select no current benefits

**Why this matters**: countable income is $2,500 + ($2,000 × 50%) − $20 − $75 = $3,405, inside the single-person $3,325.00–$3,990.00 band. Unearned income alone ($2,500 net of case-level deductions) is below the 250% boundary, so the excess is worker-earned and the allowance applies. **The verdict alone cannot carry this test**: pass 2 would remove the $2,000 and drop the total to $1,405, so a calculator without the allowance still returns Eligible. The intermediate discriminates — the two paths report $2,000 vs $0 — and being stream-scoped it holds with or without the $75 (total $3,480, still in band). Scenario 10 is the contrasting half. No premium amount is asserted.

---

### Scenario 10: Spouse's unearned income above 250% FPL — Ineligible (exclusion scope test)
**What we're checking**: the 250–300% FPL allowance applies **only** to the disabled worker's own earned income — not to a spouse's unearned income — and pass 2 cannot remove it.
**Expected**: Ineligible (countable income exceeds 250% FPL; the excess is the spouse's unearned income)

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Birth month/year: `January 1986` (age 40), Relationship: `Head of Household`, Long-term disability: `Yes`, Has income: `Yes`, Income type: `wages`, Income amount: `$40` per month
- **Person 2 (Spouse)**: Birth month/year: `January 1986` (age 40), Relationship: `Spouse`, Has income: `Yes`, Income type: `pension`, Income amount: `$4,650` per month
- **Assets**: Household resources: `$0`
- **Current Benefits**: Select no current benefits

**Why this matters**: pass 1 gives $4,650 + ($40 × 50%) − $20 − $75 = $4,575, above the couple's $4,508.99 boundary, so pass 2 runs: removing the worker's $40 while the half-earned deduction still applies gives $4,650 − $20 − $20 − $75 = $4,535 — still above the boundary by $26.01. The denial survives the fallback because the deciding income is the spouse's `pension`, which pass 2 does not touch. Protects against capping *all* household income at 300% FPL ($5,410) instead of scoping the allowance to the worker's own earned income (RSMo 208.146.1(4)).

---

### Scenario 11: Spouse's first-$50,000/year earned-income disregard — Eligible, $12,200
**What we're checking**: the first $50,000/year ($4,166.67/month) of the spouse's *earned* income is excluded from countable income.
**Expected**: Eligible — $12,200. Intermediate assertion: $4,166.67/month of the spouse's `wages` is removed by the spouse earned-income disregard, leaving $2,833.33 of spouse earned income in the countable-income computation.

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Birth month/year: `January 1986` (age 40), Relationship: `Head of Household`, Long-term disability: `Yes`, Has income: `Yes`, Income type: `wages`, Income amount: `$200` per month
- **Person 2 (Spouse)**: Birth month/year: `January 1986` (age 40), Relationship: `Spouse`, Has income: `Yes`, Income type: `wages`, Income amount: `$7,000` per month
- **Assets**: Household resources: `$0`
- **Current Benefits**: Select no current benefits

**Why this matters**: the disregard leaves $7,000 − $4,166.67 = $2,833.33 counted. Pass 1 gives $2,833.33 + $100 − $20 − $75 = $2,838.33, far under the couple's $4,508.99 boundary, so pass 2 never runs. **The verdict alone cannot prove the disregard was applied** — had pass 1 denied, pass 2 would have removed both spouses' earned income and admitted the household anyway. Hence the intermediate: omitting the disregard carries the full $7,000 into the count instead of $2,833.33.

---

### Scenario 12: SSI full disregard — Eligible, $12,200 (countable income $0)
**What we're checking**: all SSI payments are excluded from countable income in full.
**Expected**: Eligible — $12,200. Intermediate assertion: TWHA countable income = **$0**.

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Birth month/year: `January 1986` (age 40), Relationship: `Head of Household`, Long-term disability: `Yes`, Has income: `Yes`, Income: `wages` `$40` per month and `sSI` `$994` per month
- **Assets**: Household resources: `$0`
- **Current Benefits**: Select no current benefits

**Why this matters**: the $40 wage is nominal enough that countable income floors at $0 under every treatment — ordinary ($20 − $20 − $75, floored) and sheltered ($0 − $20 − $20 − $75, floored), with or without the $75 — so the exact $0 is invariant and safe to assert. The verdict cannot discriminate ($994 alone cannot cross $3,324.99), so the intermediate carries the test: failing to fully disregard SSI yields a total above $0.

---

### Scenario 13: First-$50 SSDI disregard — Eligible, $12,200
**What we're checking**: the first $50/month of the disabled worker's SSDI is excluded from countable income.
**Expected**: Eligible — $12,200. Intermediate assertion: the `sSDisability` stream contributes **$3,325** ($3,375 − $50) to countable income, before the case-level deductions.

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Birth month/year: `January 1986` (age 40), Relationship: `Head of Household`, Long-term disability: `Yes`, Has income: `Yes`, Income: `wages` `$40` per month and `sSDisability` `$3,375` per month
- **Assets**: Household resources: `$0`
- **Current Benefits**: Select no current benefits

**Why this matters**: stream-scoped because a final total would rest on the always-applied $75 deduction, which Data Gap 6 forbids any expected outcome from depending on. Dropping the $50 disregard yields a $3,375 contribution and fails. Across the $75 variations the total sits between $3,210 and $3,325 and the case is eligible throughout; pass 1 admits it, so pass 2 never runs.

---

### Scenario 14: Two eligible members, each receiving the spouse disregard — Eligible, $24,400
**What we're checking**: two things — the per-member value scales with the number of independently-eligible members, and the $50,000/year spouse earned-income disregard applies to a spouse **who is also a disabled worker**.
**Expected**: Eligible — $24,400 (2 eligible members × $12,200/year). Intermediate assertion: when Person 1 is evaluated, $4,166.67/month of Person 2's `wages` is removed by the spouse earned-income disregard — applied even though Person 2 is themselves a disabled worker.

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Birth month/year: `January 1986` (age 40), Relationship: `Head of Household`, Long-term disability: `Yes`, Has income: `Yes`, Income type: `wages`, Income amount: `$200` per month
- **Person 2 (Spouse)**: Birth month/year: `January 1986` (age 40), Relationship: `Spouse`, Long-term disability: `Yes`, Has income: `Yes`, Income type: `wages`, Income amount: `$8,500` per month
- **Assets**: Household resources: `$0`
- **Current Benefits**: Select no current benefits

**Why this matters**: each spouse is evaluated in turn as the disabled worker, the other as "the spouse." Evaluating Person 1: $8,500 − $4,166.67 = $4,333.33, plus Person 1's own $100 after the half-earned deduction, less $20 and $75 = $4,338.33 — under the couple's $4,508.99 boundary. Evaluating Person 2: Person 1's $200 is fully covered by the spouse disregard, and Person 2's own $8,500 halves to $4,250, less $20 and $75 = $4,155 — also under. Both qualify: $12,200 × 2 = $24,400. The intermediate proves the disregard: conditioning it on a non-disabled spouse would count Person 2's full $8,500 when evaluating Person 1, yet the verdict cannot show that — either spouse's wages might be excluded unobservably and the value would still be $24,400. Hence a dual-disabled couple here rather than the ordinary spouse of Scenario 11.

---

### Scenario 15: Qualifying disability via the `visually_impaired` field alone — Eligible, $12,200
**What we're checking**: `visually_impaired` alone (without `long_term_disability`) satisfies MFB's disability proxy — the two signals are an OR. Tests the screener-field mapping, not a distinct statutory blindness pathway.
**Expected**: Eligible — $12,200

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Birth month/year: `January 1986` (age 40), Relationship: `Head of Household`, Long-term disability: `No`, Visually impaired: `Yes`, Has income: `Yes`, Income type: `wages`, Income amount: `$1,000` per month
- **Assets**: Household resources: `$0`
- **Current Benefits**: Select no current benefits

**Why this matters**: protects against dropping the `visually_impaired` half of the OR and requiring `long_term_disability` specifically.

---

### Scenario 16: Temporary Assistance cash grant excluded — Eligible, $12,200
**What we're checking**: `cashAssistance` maps to the incorporated "Temporary Assistance cash grant" exclusion and contributes nothing to countable income.
**Expected**: Eligible — $12,200. Intermediate assertion: the `cashAssistance` stream contributes **$0** to countable income.

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Birth month/year: `January 1986` (age 40), Relationship: `Head of Household`, Long-term disability: `Yes`, Has income: `Yes`, Income: `wages` `$40` per month and `cashAssistance` `$292` per month
- **Person 2 (Child)**: Birth month/year: `March 2016` (age 10), Relationship: `Child`, Has income: `No`
- **Person 3 (Child)**: Birth month/year: `June 2019` (age 7), Relationship: `Child`, Has income: `No`
- **Assets**: Household resources: `$0`
- **Current Benefits**: Select no current benefits

**Why this matters**: the verdict does not discriminate — counting the $292 would still leave the household eligible — so the assertion is scoped to the stream's own contribution, fixed by the exclusion. Pass 1 admits the case so pass 2 never runs; the total is deterministic but not asserted, because it depends on the always-applied $75 deduction that Data Gap 6 rules out of any expected outcome.

---

### Scenario 17: Self-employment as the earned-income pathway — Eligible, $12,200
**What we're checking**: self-employment income satisfies the employment criterion, not just `wages`.
**Expected**: Eligible — $12,200

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Birth month/year: `January 1986` (age 40), Relationship: `Head of Household`, Long-term disability: `Yes`, Has income: `Yes`, Income type: `selfEmployment`, Income amount: `$1,000` per month
- **Assets**: Household resources: `$0`
- **Current Benefits**: Select no current benefits

**Why this matters**: both types are earned income and 0855.005.30 accepts employment or self-employment with no floor. Protects against reading the `wages` type directly instead of the `earned` selector, which would deny every self-employed applicant.

---

### Scenario 18: Dependent children do not resize the assistance unit — Ineligible
**What we're checking**: TWHA measures the disabled worker against the **single-person** income threshold even when the household contains dependants — the assistance unit is an individual or married couple, never generic household size.
**Expected**: Ineligible (countable income exceeds the single-person 250% FPL boundary)

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Birth month/year: `January 1986` (age 40), Relationship: `Head of Household`, Long-term disability: `Yes`, Has income: `Yes`, Income: `wages` `$40` per month and `pension` `$3,600` per month
- **Person 2 (Child)**: Birth month/year: `March 2016` (age 10), Relationship: `Child`, Has income: `No`
- **Person 3 (Child)**: Birth month/year: `June 2019` (age 7), Relationship: `Child`, Has income: `No`
- **Assets**: Household resources: `$0`
- **Current Benefits**: Select no current benefits

**Why this matters**: pass 1 gives $3,600 + ($40 × 50%) − $20 − $75 = $3,525, above the single-person $3,324.99 boundary, so pass 2 runs and removes the worker's $40: $3,600 − $20 − $20 − $75 = $3,485 — still above the boundary, with or without the $75. The excess is unearned pension income and the worker's earned contribution is at most $20, far too small for the 250–300% allowance. Protects against sizing the threshold to a three-person household.

---

### Scenario 19: Employer-sponsored insurance does not disqualify — Eligible, $12,200
**What we're checking**: a member holding employer-sponsored health insurance is still eligible. Employer coverage triggers post-eligibility HIPP coordination, not a screening exclusion (Implementation).
**Expected**: Eligible — $12,200

**Steps**:
- **Location**: Enter ZIP code `63101`, Select county `St. Louis City`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Birth month/year: `January 1986` (age 40), Relationship: `Head of Household`, Long-term disability: `Yes`, Has income: `Yes`, Income type: `wages`, Income amount: `$1,000` per month, Insurance: `Employer`
- **Assets**: Household resources: `$0`
- **Current Benefits**: Select no current benefits

**Why this matters**: Scenario 1's fixture with employer insurance added — the only difference is the insurance field, and the expected result is identical, so the pair localises any fault to that field. Treating `employer` as disqualifying is the natural mistake, since employer coverage does change what TWHA pays for. Coverage mode does not branch the benefit value (Benefit Value).

---

## Research Sources

| Snapshot | Tier | Title | URL | Retrieved |
|---|---|---|---|---|
| `2026-09-01--rsmo-208-146` | 1 | RSMo 208.146 - Ticket to Work Health Assurance Program (A.L. 2026 H.B. 2372, effective 8/28/2026) | https://revisor.mo.gov/main/OneSection.aspx?section=208.146 | 2026-09-01 |
| `2026-08-24--rsmo-208-146-current` | 1 | RSMo 208.146 as effective 8/28/2023 (expired 8/28/2025) — **superseded** by `2026-09-01--rsmo-208-146`; cited only for what the law was during SFY2025, the benefit value's numerator period | https://revisor.mo.gov/main/OneSection.aspx?section=208.146&bid=54170 | 2026-08-24 |
| `2026-09-01--hb2372-fiscal-note-5868s08a` | 1 | HB 2372 Fiscal Note, L.R. No. 5868S.08A (Oversight Division, May 13, 2026) — TWHA SFY2025 cost and participation | https://documents.house.mo.gov/billtracking/bills261/fiscal/fispdf/5868S.08A.ORG.pdf | 2026-09-01 |
| `2026-09-01--13-csr-40-2-030` | 1 | 13 CSR 40-2.030 Definitions Relating to Real and Personal Property (Department of Social Services, Family Support Division) | https://www.sos.mo.gov/cmsimages/adrules/csr/current/13csr/13c40-2.pdf | 2026-09-01 |
| `2026-08-24--fr-2026-poverty-guidelines` | 1 | Annual Update of the HHS Poverty Guidelines, 91 FR (2026-00755) | https://www.govinfo.gov/content/pkg/FR-2026-01-15/pdf/2026-00755.pdf | 2026-08-24 |
| `2026-08-24--dss-manual-0855-000-00-twha` | 2 | 0855.000.00 Ticket to Work Health Assurance (TWHA) Program - DSS Manuals | https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0855-000-00/ | 2026-08-24 |
| `2026-08-24--dss-manual-0855-005-05` | 2 | 0855.005.05 Age Requirement - TWHA - DSS Manuals | https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0855-000-00/0855-005-00/0855-005-05/ | 2026-08-24 |
| `2026-08-24--dss-manual-0855-005-10` | 2 | 0855.005.10 Residence and Citizenship - TWHA - DSS Manuals | https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0855-000-00/0855-005-00/0855-005-10/ | 2026-08-24 |
| `2026-09-02--dss-manual-0855-005-20-residence` | 2 | 0855.005.20 Residence - TWHA - DSS Manuals | https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0855-000-00/0855-005-00/0855-005-20/ | 2026-09-02 |
| `2026-08-24--dss-manual-0855-005-25` | 2 | 0855.005.25 Disability Requirement - TWHA - DSS Manuals | https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0855-000-00/0855-005-00/0855-005-25/ | 2026-08-24 |
| `2026-08-24--dss-manual-0855-005-30` | 2 | 0855.005.30 Employment Requirement - TWHA - DSS Manuals | https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0855-000-00/0855-005-00/0855-005-30/ | 2026-08-24 |
| `2026-08-24--dss-manual-0855-005-35` | 2 | 0855.005.35 Resource Requirement - TWHA - DSS Manuals | https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0855-000-00/0855-005-00/0855-005-35/ | 2026-08-24 |
| `2026-08-24--dss-manual-0855-005-40` | 2 | 0855.005.40 Income Requirement - TWHA - DSS Manuals | https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0855-000-00/0855-005-00/0855-005-40/ | 2026-08-24 |
| `2026-08-24--dss-manual-0855-020-00` | 2 | 0855.020.00 TWHA Couple Cases - DSS Manuals | https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0855-000-00/0855-020-00/ | 2026-08-24 |
| `2026-09-01--dss-manual-0855-025-00-hipp` | 2 | 0855.025.00 HIPP - TWHA - DSS Manuals | https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0855-000-00/0855-025-00/ | 2026-09-01 |
| `2026-08-24--mhabd-0805-015-10` | 2 | 0805.015.10 Income Exclusions - MHABD - DSS Manuals | https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0805-000-00/0805-015-00/0805-015-10/ | 2026-08-24 |
| `2026-08-24--mo-magi-1805-020-10-10` | 2 | 1805.020.10.10 Qualified Alien Five-Year Bar - Family MO HealthNet MAGI | https://dssmanuals.mo.gov/family-mo-healthnet-magi/1805-000-00/1805-020-00/1805-020-10/1805-020-10-10/ | 2026-08-24 |
| `2026-09-01--mo-magi-1805-020-10` | 2 | 1805.020.10 Immigrant Status - Family MO HealthNet (MAGI) | https://dssmanuals.mo.gov/family-mo-healthnet-magi/1805-000-00/1805-020-00/1805-020-10/ | 2026-09-01 |
| `2026-09-01--mo-magi-1805-020-10-05` | 2 | 1805.020.10.05 Qualified Immigrants Entering Prior to 8/22/96 - Family MO HealthNet (MAGI) | https://dssmanuals.mo.gov/family-mo-healthnet-magi/1805-000-00/1805-020-00/1805-020-10/1805-020-10-05/ | 2026-09-01 |
| `2026-09-01--mo-magi-1805-020-10-10-05` | 2 | 1805.020.10.10.05 Qualified Immigrants With No Waiting Period - Family MO HealthNet (MAGI) | https://dssmanuals.mo.gov/family-mo-healthnet-magi/1805-000-00/1805-020-00/1805-020-10/1805-020-10-10/1805-020-10-10-05/ | 2026-09-01 |
| `2026-09-01--mo-magi-1805-020-10-10-10` | 2 | 1805.020.10.10.10 Qualified Immigrants With a Five-Year Period of Ineligibility - Family MO HealthNet (MAGI) | https://dssmanuals.mo.gov/family-mo-healthnet-magi/1805-000-00/1805-020-00/1805-020-10/1805-020-10-10/1805-020-10-10-10/ | 2026-09-01 |
| `2026-09-01--mo-magi-1805-020-10-15` | 2 | 1805.020.10.15 Non-qualified Immigrants - Family MO HealthNet (MAGI) | https://dssmanuals.mo.gov/family-mo-healthnet-magi/1805-000-00/1805-020-00/1805-020-10/1805-020-10-15/ | 2026-09-01 |
| `2026-09-01--mo-magi-1805-020-10-20` | 2 | 1805.020.10.20 Citizens of the Federated States of Micronesia, Republic of Palau and Republic of the Marshall Islands (COFA) - Family MO HealthNet (MAGI) | https://dssmanuals.mo.gov/family-mo-healthnet-magi/1805-000-00/1805-020-00/1805-020-10/1805-020-10-20/ | 2026-09-01 |
| `2026-08-24--im4-twha-brochure` | 2 | IM-4 TWHA - Ticket to Work Health Assurance Program Brochure | https://dssmanuals.mo.gov/wp-content/uploads/2021/10/brochure_twha.pdf | 2026-08-24 |
| `2026-08-24--mhabd-appendix-j-2026` | 2 | MHABD Appendix J - Eligibility Standards for Non-MAGI Programs (07/2026, TWHA effective 04-01-2026) | https://dssmanuals.mo.gov/wp-content/uploads/2022/07/mhabd-appendix-j.pdf | 2026-08-24 |
| `2026-08-24--appendix-k` | 2 | Appendix K - Resource Levels | https://dssmanuals.mo.gov/wp-content/uploads/2018/10/appendix_k.pdf | 2026-08-24 |
| `2026-08-24--fsd-mhd-report-dec2025` | 2 | DSS FSD/MHD Monthly Management Report, December 2025 — TWHA premium/non-premium enrollment and spending composition (**offline retained document**: snapshot is the evidentiary source; originating URL preserved as provenance, 404 as of 2026-09-02) | https://dss.mo.gov/re/pdf/fsd_mhdmr/1225-family-support-mohealthnet-report.pdf | 2026-08-24 |
| `2026-08-24--macpac-exhibit-23-fy2024` | 2 | MACPAC Exhibit 23 — Medicaid Benefit Spending per Full-Year Equivalent Enrollee, Newly Eligible Adult and All Enrollees by State, FY2024 (February 2026) | https://www.macpac.gov/wp-content/uploads/2026/01/EXHIBIT-23.-Medicaid-Benefit-Spending-per-Full-Year-Equivalent-Enrollee-for-Newly-Eligible-Adult-and-All-Enrollees-by-State-FY-2024.pdf | 2026-08-24 |
| `2026-08-24--db101-twha` | 3 | DB101 Missouri - MO HealthNet's Ticket to Work Health Assurance | https://mo.db101.org/mo/programs/health_coverage/how_health/program2b.htm | 2026-08-24 |
