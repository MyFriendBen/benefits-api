# Earned Income Tax Credit (NJ) — Program Spec

## 1. Header

- **Program Tier**: `standalone`
- **Program Key**: `nj_eitc`
- **White Label**: NJ
- **Engine**: `MFB`
- **Calculator**: N/A - not yet implemented
- **Calculator added**: N/A - not yet implemented
- **Spec last verified**: 2026-10-28
- **Rules last changed**: N/A - standalone

## 2. Inheritance & Variance

- **Tier verified**: 2026-10-26
- **Inherits from**: N/A - standalone
- **Variance table**: N/A - standalone

## 3. Eligibility Structure

Legend: `✓` the calculator evaluates this rule · `≈` evaluates it in part · `✗` does not evaluate it

**Routes**: `federal_credit` OR `age_expansion`

- `federal_credit` — a New Jersey resident who qualifies for the federal Earned Income Tax Credit
  - ALL OF:
    - `✓` You lived in New Jersey for at least part of 2025 (`nj_residency`)
    - `≈` Your immigration status lets you hold a work-valid Social Security number (`valid_social_security_number`) — evaluated without:
        - `✗` Everyone on your return has a work-valid Social Security number (`social_security_numbers`)
    - `≈` You qualify for the 2025 federal Earned Income Tax Credit (`federal_eitc_allowed`) — evaluated without:
        - `✗` In a civil union, you claim jointly, or separately with a child (`civil_union_joint_return`)

  `nj_residency` AND `valid_social_security_number` [degraded by: `social_security_numbers`] AND `federal_eitc_allowed` [degraded by: `civil_union_joint_return`]

- `age_expansion` — a New Jersey resident aged 18 or older with no qualifying child who misses the federal credit only because of its age limits
  - ALL OF:
    - `✓` You lived in New Jersey for at least part of 2025 (`nj_residency`)
    - `≈` Your immigration status lets you hold a work-valid Social Security number (`valid_social_security_number`) — evaluated without:
        - `✗` Everyone on your return has a work-valid Social Security number (`social_security_numbers`)
    - `✓` You were at least 18 on December 31, 2025 (`age_18_or_older`)
    - `✓` You can't claim a child for the Earned Income Tax Credit (`no_qualifying_child`)
    - `≈` You meet every federal Earned Income Tax Credit rule except age (`federal_requirements_except_age`) — evaluated without:
        - `✗` No one can claim you or your spouse as a dependent (`not_claimed_as_dependent`)
        - `✗` In a civil union, you claim jointly, or separately with a child (`civil_union_joint_return`)
    - NOT:
      - `≈` You qualify for the 2025 federal Earned Income Tax Credit (`federal_eitc_allowed`) — evaluated without:
          - `✗` In a civil union, you claim jointly, or separately with a child (`civil_union_joint_return`)

  `nj_residency` AND `valid_social_security_number` [degraded by: `social_security_numbers`] AND `age_18_or_older` AND `no_qualifying_child` AND `federal_requirements_except_age` [degraded by: `not_claimed_as_dependent`, `civil_union_joint_return`] AND NOT `federal_eitc_allowed` [degraded by: `civil_union_joint_return`]

## 4. Covered Eligibility Criteria

1. `nj_residency` — **The filer must be a New Jersey resident for at least part of the tax year.**
   - Label: You lived in New Jersey for at least part of 2025
   - Routes: `federal_credit`, `age_expansion`
   - Evaluation scope: `household`
   - Inheritance status: `N/A`
   - Enforced by: `white-label`
   - Fields: —
   - Logic: —
   - Approximations: N/A
   - Source: Notice to Employees, eligibility list — "Be a resident of this state for at least some of the tax year" — [snapshot `2026-10-26--nj-eitc-notice-to-employees-2025`](sources/2026-10-26--nj-eitc-notice-to-employees-2025/content.md), accessed 2026-10-26
   - Source: N.J.S.A. 54A:4-7(a)(1), as amended by P.L. 2021, c.130 — "A resident individual who is eligible for a credit under section 32 of the federal Internal Revenue Code of 1986" — [snapshot `2026-10-26--nj-pl-2021-c130`](sources/2026-10-26--nj-pl-2021-c130/content.md), accessed 2026-10-26
   - Conflicting source: N/A

2. `federal_eitc_allowed` — **The filer must be eligible for the federal earned income tax credit under 26 U.S.C. § 32 for the same tax year.**
   - Label: You qualify for the 2025 federal Earned Income Tax Credit
   - Routes: `federal_credit`, `age_expansion`
   - Evaluation scope: `household`
   - Inheritance status: `N/A`
   - Enforced by: `calculator`
   - Fields: `type` (IncomeStream), `amount` (IncomeStream), `frequency` (IncomeStream), `relationship` (HouseholdMember), `birth_year_month` (HouseholdMember), `student_full_time` (HouseholdMember), `disabled` (HouseholdMember), `long_term_disability` (HouseholdMember), `visually_impaired` (HouseholdMember)
   - Logic: `federal_eitc_amount` > 0, where `federal_eitc_amount` is the amount the rules in `programs/white_labels/federal/eitc/federal_eitc_spec.md` (§3 to §5 and §7) return for the household
   - Approximations:
     - sources work out a civil union couple's credit on a mock joint federal return, and limit a partner filing separately; the Logic above counts a `domesticPartner` as unmarried, because the screener does not collect whether partners are in a civil union. → `civil_union_joint_return`
   - Source: N.J.S.A. 54A:4-7(a)(1), as amended by P.L. 2021, c.130 — "shall be allowed a credit for the taxable year equal to a percentage, as provided in paragraph (2) of this subsection, of the federal earned income tax credit that would be allowed to the individual" — [snapshot `2026-10-26--nj-pl-2021-c130`](sources/2026-10-26--nj-pl-2021-c130/content.md), accessed 2026-10-26
   - Source: Notice to Employees, under the headline, second paragraph — "Everyone who applies and qualifies for the federal credit is eligible for the New Jersey Earned Income Tax Credit (NJEITC)." — [snapshot `2026-10-26--nj-eitc-notice-to-employees-2025`](sources/2026-10-26--nj-eitc-notice-to-employees-2025/content.md), accessed 2026-10-26
   - Conflicting source: N/A

3. `age_18_or_older` — **The filer must be at least 18 years old.**
   - Label: You were at least 18 on December 31, 2025
   - Routes: `age_expansion`
   - Evaluation scope: `member`
   - Inheritance status: `N/A`
   - Enforced by: `calculator`
   - Fields: `birth_year_month` (HouseholdMember), `relationship` (HouseholdMember)
   - Logic: `HouseholdMember.age_at_end_of_year(2025)` ≥ 18 for the head
   - Approximations: N/A
   - Source: Notice to Employees, under the headline, second paragraph — "New Jerseyans who are at least 18 and who cannot claim a qualifying child are eligible for the NJEITC even if they are not eligible for the federal credit due to age limits." — [snapshot `2026-10-26--nj-eitc-notice-to-employees-2025`](sources/2026-10-26--nj-eitc-notice-to-employees-2025/content.md), accessed 2026-10-26
   - Source: 2025 NJ-1040 instructions, Line 58, requirements list — "You were at least 18 years old on the last day of the tax" — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
   - Source: 2025 NJ-1040 instructions, Line 58, requirements list — "year; and" — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
   - Source: N.J.S.A. 54A:4-7(a)(4), as amended by P.L. 2021, c.130 — "A resident individual who is at least [21] 18 years" — [snapshot `2026-10-26--nj-pl-2021-c130`](sources/2026-10-26--nj-pl-2021-c130/content.md), accessed 2026-10-26
   - Conflicting source: N/A

4. `no_qualifying_child` — **The filer cannot claim a qualifying child for the federal credit.**
   - Label: You can't claim a child for the Earned Income Tax Credit
   - Routes: `age_expansion`
   - Evaluation scope: `household`
   - Inheritance status: `N/A`
   - Enforced by: `calculator`
   - Fields: `relationship` (HouseholdMember), `birth_year_month` (HouseholdMember), `student_full_time` (HouseholdMember), `disabled` (HouseholdMember), `long_term_disability` (HouseholdMember), `visually_impaired` (HouseholdMember)
   - Logic: n = 0, where n is the number of household members, other than the head and the member whose `relationship` is `spouse`, who pass `child_relationship` and `child_age` as `programs/white_labels/federal/eitc/federal_eitc_spec.md` §4 states them
   - Approximations: N/A
   - Source: N.J.S.A. 54A:4-7(a)(4), as amended by P.L. 2021, c.130 — "of age or older, but cannot claim a qualifying child as defined under section 152 of the federal Internal Revenue Code of 1986 (26 U.S.C. s.152) for the federal earned income tax credit" — [snapshot `2026-10-26--nj-pl-2021-c130`](sources/2026-10-26--nj-pl-2021-c130/content.md), accessed 2026-10-26
   - Source: Notice to Employees, under the headline, second paragraph — "New Jerseyans who are at least 18 and who cannot claim a qualifying child are eligible for the NJEITC even if they are not eligible for the federal credit due to age limits." — [snapshot `2026-10-26--nj-eitc-notice-to-employees-2025`](sources/2026-10-26--nj-eitc-notice-to-employees-2025/content.md), accessed 2026-10-26
   - Conflicting source: N/A

5. `federal_requirements_except_age` — **The filer must meet every federal earned income tax credit requirement other than the minimum and maximum age.**
   - Label: You meet every federal Earned Income Tax Credit rule except age
   - Routes: `age_expansion`
   - Evaluation scope: `household`
   - Inheritance status: `N/A`
   - Enforced by: `calculator`
   - Fields: `type` (IncomeStream), `amount` (IncomeStream), `frequency` (IncomeStream), `relationship` (HouseholdMember)
   - Logic: `federal_eitc_amount` > 0, computed for a household with no qualifying child and without the `filer_age_25_to_64` test, by the rules in `programs/white_labels/federal/eitc/federal_eitc_spec.md` (§3 to §5 and §7)
   - Approximations:
     - sources also require that no other taxpayer can claim the filer, or the spouse on a joint return, as a dependent; the Logic above does not test it, because the screener does not collect who can claim a household member as a dependent. → `not_claimed_as_dependent`
     - sources bar a civil union couple from this route, since it is eligible only if it claims and is allowed a federal credit; the Logic above counts a `domesticPartner` as unmarried, because the screener does not collect whether partners are in a civil union. → `civil_union_joint_return`
   - Source: N.J.S.A. 54A:4-7(a)(4), as amended by P.L. 2021, c.130 — "The resident individual shall meet all qualifications, except for the minimum or maximum age, for the federal earned income tax credit in order to be eligible for the New Jersey earned income tax credit." — [snapshot `2026-10-26--nj-pl-2021-c130`](sources/2026-10-26--nj-pl-2021-c130/content.md), accessed 2026-10-26
   - Source: Notice to Employees, eligibility list — "or be at least 18 years old and meet all the federal criteria for a credit except age limits;" — [snapshot `2026-10-26--nj-eitc-notice-to-employees-2025`](sources/2026-10-26--nj-eitc-notice-to-employees-2025/content.md), accessed 2026-10-26
   - Conflicting source: N/A

6. `valid_social_security_number` — **The filer, the spouse and any qualifying child listed on the return must each have a valid Social Security number.**
   - Label: Your immigration status lets you hold a work-valid Social Security number
   - Routes: `federal_credit`, `age_expansion`
   - Evaluation scope: `household`
   - Inheritance status: `N/A`
   - Enforced by: `program-record`
   - Fields: `legal_status_required` (Program)
   - Logic: `Program.legal_status_required` = {`citizen`, `gc_5plus`, `gc_5less`, `refugee`, `otherWithWorkPermission`}
   - Approximations:
     - sources require a valid Social Security number for the filer, the spouse and each qualifying child; the Logic above admits every status that can carry one, because the screener collects neither Social Security numbers nor immigration status; the program record's legal statuses decide who is shown the program. → `social_security_numbers`
   - Source: Notice to Employees, eligibility list — "Have a valid Social Security number. Your spouse and any qualifying child you list on your tax return also must have a valid Social Security number." — [snapshot `2026-10-26--nj-eitc-notice-to-employees-2025`](sources/2026-10-26--nj-eitc-notice-to-employees-2025/content.md), accessed 2026-10-26
   - Conflicting source: N/A

## 5. Missing Eligibility Criteria (Data Gaps)

1. `social_security_numbers` — **The filer, the spouse and any qualifying child listed on the return must each hold a valid Social Security number, not only an individual taxpayer identification number.**
   - Label: Everyone on your return has a work-valid Social Security number
   - Routes: `federal_credit`, `age_expansion`
   - Evaluation scope: `household`
   - Inheritance status: `N/A`
   - Degrades: `valid_social_security_number`
   - Why: The screener does not collect Social Security numbers, or whether a spouse or child holds one; it collects no immigration status either, and the program record's legal statuses decide who is shown the program.
   - Effect: `widens`
   - Handling: `not surfaced`
   - Handling rationale: A household without a number valid for work cannot get one by reading the rule, and the program is shown only to the five immigration statuses that can hold one.
   - Source: Notice to Employees, eligibility list — "Have a valid Social Security number. Your spouse and any qualifying child you list on your tax return also must have a valid Social Security number." — [snapshot `2026-10-26--nj-eitc-notice-to-employees-2025`](sources/2026-10-26--nj-eitc-notice-to-employees-2025/content.md), accessed 2026-10-26

2. `not_claimed_as_dependent` — **The filer, and the spouse on a joint return, must not be a dependent another taxpayer can claim, unless that taxpayer is not required to file and files no return or files only for a refund of withheld or estimated tax.**
   - Label: No one can claim you or your spouse as a dependent
   - Routes: `age_expansion`
   - Evaluation scope: `household`
   - Inheritance status: `N/A`
   - Degrades: `federal_requirements_except_age`
   - Why: The screener does not collect who can claim a household member as a dependent; `relationship` shows a parent living in the household, but not whether that parent can claim the filer, and nothing about a claimant living elsewhere.
   - Effect: `widens`
   - Handling: `surfaces in description`
   - Handling rationale: A young worker whose parent or guardian can claim them cannot claim the credit, and checking with that person before filing is what changes whether they claim it.
   - Source: N.J.S.A. 54A:4-7(a)(4), as amended by P.L. 2021, c.130 — "The resident individual shall meet all qualifications, except for the minimum or maximum age, for the federal earned income tax credit in order to be eligible for the New Jersey earned income tax credit." — [snapshot `2026-10-26--nj-pl-2021-c130`](sources/2026-10-26--nj-pl-2021-c130/content.md), accessed 2026-10-26
   - Source: 26 U.S.C. § 32(c)(1)(A)(ii)(III) — "such individual is not a dependent for whom a deduction is allowable under section 151 to another taxpayer for any taxable year beginning in the same calendar year as such taxable year." — [snapshot `2026-10-13--usc-26-32`](../../federal/eitc/sources/2026-10-13--usc-26-32/content.md), accessed 2026-10-13
   - Source: Publication 596 (2025), Rule 12—You Cannot Be the Dependent of Another Person — "If you are filing a joint return, you meet this rule if you did not check either box that says “Someone can claim you as a dependent” or “Someone can claim your spouse as a dependent.”" — [snapshot `2026-10-13--irs-pub-596-2025`](../../federal/eitc/sources/2026-10-13--irs-pub-596-2025/content.md), accessed 2026-10-13
   - Source: Publication 596 (2025), Rule 12—You Cannot Be the Dependent of Another Person — "If someone else can claim you as a dependent on their return, but doesn’t, you still can’t claim the credit unless the person who can claim you on their tax return isn’t required to file an income tax return and doesn’t file a tax return or files a return only to claim a refund of withheld income tax or estimated tax paid." — [snapshot `2026-10-13--irs-pub-596-2025`](../../federal/eitc/sources/2026-10-13--irs-pub-596-2025/content.md), accessed 2026-10-13
   - Source: 2025 NJ-1040 instructions, Line 58 — "You are not listed as a dependent on another tax return" — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26

3. `civil_union_joint_return` — **Partners in a civil union file their New Jersey return with the same filing statuses as spouses and are eligible only if they claim and are allowed a federal credit: a couple filing a joint New Jersey return works out the credit from a mock joint federal return, and a partner filing separately can claim it only with a qualifying child who lived with them for more than half the year and after living apart for the last six months of the year.**
   - Label: In a civil union, you claim jointly, or separately with a child
   - Routes: `federal_credit`, `age_expansion`
   - Evaluation scope: `household`
   - Inheritance status: `N/A`
   - Degrades: `federal_eitc_allowed`, `federal_requirements_except_age`
   - Why: The screener does not collect whether two partners are in a civil union; `relationship` records `domesticPartner` for civil union partners and other partners alike, and the federal calculation this spec references counts only a `spouse` as married, so a civil union couple's credit is worked out without the partner. That can show a credit to a couple whose combined income is over the limit, or the flat amount through `age_expansion` to a couple the sources bar from it, and miss one for a couple whose partner's earnings or child would bring them into it.
   - Effect: `varies`
   - Handling: `surfaces in description`
   - Handling rationale: A couple in a civil union is told its credit is worked out the way a married couple's is, so the amount shown may differ, and knowing that lets it check the figure when it files.
   - Source: 2025 NJ-1040 instructions, Filing Status, Civil Unions — "Civil Unions. Partners in a civil union must file their New" — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
   - Source: 2025 NJ-1040 instructions, Filing Status, Civil Unions — "Jersey Income Tax returns using the same filing statuses as" — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
   - Source: 2025 NJ-1040 instructions, Filing Status, Civil Unions — "spouses under New Jersey Gross Income Tax Law." — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
   - Source: 2025 NJ-1040 instructions, Line 58 — "If you did not file a joint or separate federal return, prepare" — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
   - Source: 2025 NJ-1040 instructions, Line 58 — "a mock federal return using the same filing status as on your" — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
   - Source: 2025 NJ-1040 instructions, Line 58 — "NJ-1040, then calculate the amount of the federal EIC that you" — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
   - Source: 2025 NJ-1040 instructions, Line 58 — "would have been eligible to receive." — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
   - Source: 2025 NJ-1040 instructions, Line 58, Civil Union Couples — "You are eligible for an NJEITC only if you claim and are al-" — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
   - Source: 2025 NJ-1040 instructions, Line 58, Civil Union Couples — "lowed a federal EIC. If you are not filing a joint New Jersey" — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
   - Source: 2025 NJ-1040 instructions, Line 58, Civil Union Couples — "return, you must have had a qualifying child who lived with" — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
   - Source: 2025 NJ-1040 instructions, Line 58, Civil Union Couples — "you for more than half of 2025, and lived apart from your civil" — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
   - Source: 2025 NJ-1040 instructions, Line 58, Civil Union Couples — "union partner for the last six months of 2025." — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26

## 6. Access

1. `njeitc_filing` — **The credit is claimed by filing a New Jersey resident income tax return, Form NJ-1040, even where income is below the filing threshold; a calendar-year filer's 2025 return is due by April 15, 2026, and a refund can generally be requested for three years from the return's due date, including extensions**
   - Question: `application_window`
   - Kind: `timing`
   - Inheritance status: N/A
   - Handling: `surfaces in description`
   - Handling rationale: A household earning too little to be required to file still has to file to get the credit, and knowing that is what changes whether they do; a household that missed the April due date can still request the refund for three years, and knowing that is what keeps them from giving up on the credit.
   - Source: Notice to Employees, under the headline, third paragraph — "To get the NJEITC, you must file a New Jersey Resident Income Tax return, even if your income is below New Jersey’s minimum filing threshold amount." — [snapshot `2026-10-26--nj-eitc-notice-to-employees-2025`](sources/2026-10-26--nj-eitc-notice-to-employees-2025/content.md), accessed 2026-10-26
   - Source: 2025 NJ-1040 instructions, When to File — "If you are a calendar year filer, your 2025 New Jersey Income Tax return is due by" — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
   - Source: 2025 NJ-1040 instructions, When to File — "April 15, 2026. Fiscal year filers, see page 5." — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
   - Source: 2025 NJ-1040 instructions, Time Period for Refunds — "Time Period for Refunds. Generally, you have three years" — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
   - Source: 2025 NJ-1040 instructions, Time Period for Refunds — "from the date the return was due (including extensions) to re-" — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
   - Source: 2025 NJ-1040 instructions, Time Period for Refunds — "quest a refund." — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26

2. `njeitc_processing_time` — **A New Jersey refund is generally issued 4 weeks or more after an electronic filing and at least 12 weeks after a mailed return, and 15 weeks or more where extra processing is needed; a refund containing the NJEITC may take longer because these claims need additional review**
   - Question: `decision_time`
   - Kind: `timing`
   - Inheritance status: N/A
   - Handling: `sets estimated_decision_time`
   - Handling rationale: The record field carries the published times, "4 weeks or more if you e-file, 12 or more if you mail it, longer if the claim is reviewed", so a household filing now can see when to expect an answer; the field renders nowhere yet, and the description is left alone to avoid a duplicate when it does.
   - Source: Check Your Refund Status, general refund processing times — "4 weeks or more after you file electronically;" — [snapshot `2026-10-26--nj-check-refund-status`](sources/2026-10-26--nj-check-refund-status/content.md), accessed 2026-10-26
   - Source: Check Your Refund Status, general refund processing times — "At least 12 weeks after you mail your return;" — [snapshot `2026-10-26--nj-check-refund-status`](sources/2026-10-26--nj-check-refund-status/content.md), accessed 2026-10-26
   - Source: Check Your Refund Status, general refund processing times — "15 weeks or more for additional processing requirements or paper returns sent by certified mail." — [snapshot `2026-10-26--nj-check-refund-status`](sources/2026-10-26--nj-check-refund-status/content.md), accessed 2026-10-26
   - Source: Check Your Refund Status, general refund processing times — "If your refund contains a New Jersey Earned Income Tax Credit (NJEITC), it may be delayed beyond the time frames listed above because these claims require additional review." — [snapshot `2026-10-26--nj-check-refund-status`](sources/2026-10-26--nj-check-refund-status/content.md), accessed 2026-10-26

3. `njeitc_file_online` — **A household can file the NJ-1040 online for free through New Jersey Online Filing at fastfile.nj.gov, open to any resident or part-year resident; NJ E-File through purchased tax software, an online tax preparation website or a preparer also files it**
   - Question: `apply_online`
   - Kind: `process`
   - Inheritance status: N/A
   - Handling: `sets apply_button_link`
   - Handling rationale: The apply button goes to https://www.nj.gov/treasury/taxation/payments-notices.shtml, the Division's Individual Income Tax Filing Options, which lists online filing and paper forms for New Jersey residents side by side, so a household that has not filed before finds both ways to file.
   - Source: 2025 NJ-1040 instructions, New Jersey Online Filing — "Any resident (or part-year resident) can use it to file their 2025 NJ-1040 for free." — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
   - Source: 2025 NJ-1040 instructions, back cover, New Jersey Online Filing — "fastfile.nj.gov" — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
   - Source: 2025 NJ-1040 instructions, NJ E-File — "You can file your Form NJ-1040 for 2025 using NJ" — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
   - Source: 2025 NJ-1040 instructions, NJ E-File — "E-File, whether you are a full-year resident or a part-" — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
   - Source: 2025 NJ-1040 instructions, NJ E-File — "year resident. Use tax software you purchase, go to an" — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
   - Source: 2025 NJ-1040 instructions, NJ E-File — "online tax preparation website, or have a tax preparer" — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
   - Source: 2025 NJ-1040 instructions, NJ E-File — "file your return." — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
   - Source: File, Pay, and Manage, Individual Income Tax Filing Options, New Jersey Residents row — "File Your Return for NJ residents" — [snapshot `2026-10-28--nj-file-pay-manage`](sources/2026-10-28--nj-file-pay-manage/content.md), accessed 2026-10-28
   - Source: File, Pay, and Manage, Individual Income Tax Filing Options, New Jersey Residents row — "Find Forms for NJ residents" — [snapshot `2026-10-28--nj-file-pay-manage`](sources/2026-10-28--nj-file-pay-manage/content.md), accessed 2026-10-28

4. `njeitc_file_by_mail` — **A household can file a paper NJ-1040 by mail, using the envelope in the booklet**
   - Question: `apply_other_channels`
   - Kind: `process`
   - Inheritance status: N/A
   - Handling: `surfaces in description`
   - Handling rationale: A household without internet access, or that prefers paper, can still claim the credit, and the description is the only place the record can say so.
   - Source: 2025 NJ-1040 instructions, Where to Mail Your Return — "Use the envelope in your booklet to mail your NJ-1040" — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26

5. `njeitc_documents` — **If the Division sends a letter asking for proof, the household sends copies of Social Security cards for the filer, spouse and dependents claimed, an IRS Record of Account or Tax Account Transcript, income forms, and proof of each qualifying child's relationship such as a birth certificate**
   - Question: `documents_required`
   - Kind: `process`
   - Inheritance status: N/A
   - Handling: `listed in documents`
   - Handling rationale: A household that keeps these ready can answer a letter quickly, and the record's documents list is where a household looks for what to bring.
   - Source: I Received a Letter, Required Documents, Federal Documents — "Social Security cards for yourself, your spouse, and any dependents claimed on the tax return" — [snapshot `2026-10-26--nj-eitc-received-a-letter`](sources/2026-10-26--nj-eitc-received-a-letter/content.md), accessed 2026-10-26
   - Source: I Received a Letter, Required Documents, Federal Documents — "IRS Record of Account or Tax Account Transcript - Request this document at no cost from the IRS" — [snapshot `2026-10-26--nj-eitc-received-a-letter`](sources/2026-10-26--nj-eitc-received-a-letter/content.md), accessed 2026-10-26
   - Source: I Received a Letter, Required Documents, Qualifying Children — "You must prove the relationship with your qualifying child is legal." — [snapshot `2026-10-26--nj-eitc-received-a-letter`](sources/2026-10-26--nj-eitc-received-a-letter/content.md), accessed 2026-10-26
   - Source: I Received a Letter, Required Documents, Proof of Income — "All W-2 forms;" — [snapshot `2026-10-26--nj-eitc-received-a-letter`](sources/2026-10-26--nj-eitc-received-a-letter/content.md), accessed 2026-10-26
   - Source: I Received a Letter, Required Documents, Proof of Income — "All 1099 forms; and/or" — [snapshot `2026-10-26--nj-eitc-received-a-letter`](sources/2026-10-26--nj-eitc-received-a-letter/content.md), accessed 2026-10-26
   - Source: I Received a Letter, Required Documents, Proof of Income — "Business/Self-employment Records" — [snapshot `2026-10-26--nj-eitc-received-a-letter`](sources/2026-10-26--nj-eitc-received-a-letter/content.md), accessed 2026-10-26
   - Source: I Received a Letter, Required Documents, Qualifying Children — "A copy of the qualifying child's birth certificate, which lists your name as the mother or father;" — [snapshot `2026-10-26--nj-eitc-received-a-letter`](sources/2026-10-26--nj-eitc-received-a-letter/content.md), accessed 2026-10-26
   - Source: I Received a Letter, Required Documents, Qualifying Children — "Court documents, marriage certificate, or a paternity test result, which proves your relationship" — [snapshot `2026-10-26--nj-eitc-received-a-letter`](sources/2026-10-26--nj-eitc-received-a-letter/content.md), accessed 2026-10-26

6. `njeitc_notice_review` — **The Division may send a letter requesting documents and approves no credit until it verifies them**
   - Question: `application_steps`
   - Kind: `process`
   - Inheritance status: N/A
   - Handling: `surfaces in description`
   - Handling rationale: The agency starts this step and a household cannot do it in advance, but one that knows a letter may come, and that an unanswered letter stops the credit, can answer it at once.
   - Source: I Received a Letter, opening paragraph — "No credits will be approved until we can verify your information." — [snapshot `2026-10-26--nj-eitc-received-a-letter`](sources/2026-10-26--nj-eitc-received-a-letter/content.md), accessed 2026-10-26
   - Source: NJEITC overview, fourth paragraph — "You must respond to the notice and provide the requested information or we will not be able to apply the credit." — [snapshot `2026-10-26--nj-eitc-overview`](sources/2026-10-26--nj-eitc-overview/content.md), accessed 2026-10-26

7. `njeitc_help` — **Trained VITA and TCE volunteers help prepare federal and New Jersey returns at locations around the state, and the Division answers NJEITC questions by phone at (609) 943-5000 and online at eitc.nj.gov**
   - Question: `help_available`
   - Kind: `process`
   - Inheritance status: N/A
   - Handling: `listed in navigators`
   - Handling rationale: A household unsure how to file can be pointed to free volunteer preparers and the Division's own NJEITC contacts, which is what the navigators list is for.
   - Source: 2025 NJ-1040 instructions, Who Can Help — "Trained volunteers in the VITA (Volunteer Income Tax Assistance) and" — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
   - Source: 2025 NJ-1040 instructions, Who Can Help — "TCE (Tax Counseling for the Elderly) programs are available to help" — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
   - Source: 2025 NJ-1040 instructions, Who Can Help — "prepare both federal and State returns at locations throughout New" — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
   - Source: 2025 NJ-1040 instructions, Who Can Help — "Jersey. For the location nearest you, contact the Division’s Customer" — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
   - Source: 2025 NJ-1040 instructions, Who Can Help — "Service Center at (609) 292-6400 or the Internal Revenue Service." — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
   - Source: Notice to Employees, closing list — "NJ online: eitc.nj.gov" — [snapshot `2026-10-26--nj-eitc-notice-to-employees-2025`](sources/2026-10-26--nj-eitc-notice-to-employees-2025/content.md), accessed 2026-10-26
   - Source: Notice to Employees, closing list — "NJ by phone: (609) 943-5000" — [snapshot `2026-10-26--nj-eitc-notice-to-employees-2025`](sources/2026-10-26--nj-eitc-notice-to-employees-2025/content.md), accessed 2026-10-26

8. `njeitc_application_time` — **Applying takes 1 hour, compared to the 3 hours we publish for `federal_eitc`: it means completing the NJ-1040, shorter than the federal return because line 58 is one line that enters 40% of the federal credit or $260**
   - Question: `application_time`
   - Kind: `process`
   - Inheritance status: N/A
   - Handling: `sets estimated_application_time`
   - Handling rationale: The results card and program page show this figure, and a household deciding whether to claim should see it is shorter than the federal return. The duration is MFB's own estimate, compared to `federal_eitc`; no agency states one.
   - Source: 2025 NJ-1040 instructions, Line 58 — "The NJEITC is 40% of the federal EIC." — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
   - Source: 2025 NJ-1040 instructions, Line 58 — "If so, enter $260 on line 58." — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26

**Questions with no rule**, as of 2026-10-26:

| Questions | Answer | Why / Source |
|---|---|---|
| `waitlist`, `waitlist_reopens`, `lottery`, `funding_limit` — `capacity` | `implied no` | The sources are silent. The statute allows the credit to every eligible resident individual, and the Notice to Employees, the instructions and the Division's pages name no queue, drawing or fund that can run out |
| `priority_groups`, `set_asides` — `priority` | `implied no` | The sources are silent; every return claiming the credit is processed the same way, and the Division's pages name no group served first or slots held back |
| `apply_before_event` — `timing` | `implied no` | The sources state no event a household must apply before; the only deadline is the return's due date, entry 1 |
| `delivery_time` — `timing` | `unknown` | The refund status page gives how long processing takes, carried in entry 2, and says refunds are paid by paper check or direct deposit; no source gives how long a refund takes to arrive once approved |
| `advance_registration`, `renewal` — `process` | `implied no` | The NJEITC overview, the Notice to Employees and the NJ-1040 instructions name no registration, assessment or appearance before filing, and say nothing about renewal |

## 7. Benefit Value

- Inheritance status: `N/A`
- Derivation: `formula`
- value_format: `estimated_annual`
- Payment unit: `household`
- Value: N/A - formula
- Variation axes: route, federal credit amount (earned income, adjusted gross income, number of qualifying children, filing status), months of New Jersey residency
- Calculation: on `federal_credit`, `credit = nj_rate × federal_eitc_amount`; on `age_expansion`, `credit = age_expansion_amount`; on both, `credit = credit × (residency_months ÷ 12)`
- Terms:
  - nj_rate = 40% for taxable years beginning on or after January 1, 2020, so 40% for 2025 — N.J.S.A. 54A:4-7(a)(2)(l), as amended by P.L. 2021, c.130 — "40% for taxable years beginning on or after January 1, 2020." — [snapshot `2026-10-26--nj-pl-2021-c130`](sources/2026-10-26--nj-pl-2021-c130/content.md), accessed 2026-10-26
  - federal_eitc_amount = the federal credit the rules in `programs/white_labels/federal/eitc/federal_eitc_spec.md` §7 compute for the household — N.J.S.A. 54A:4-7(a)(1), as amended by P.L. 2021, c.130 — "shall be allowed a credit for the taxable year equal to a percentage, as provided in paragraph (2) of this subsection, of the federal earned income tax credit that would be allowed to the individual" — [snapshot `2026-10-26--nj-pl-2021-c130`](sources/2026-10-26--nj-pl-2021-c130/content.md), accessed 2026-10-26
  - age_expansion_amount = $260 for 2025 — 2025 NJ-1040 instructions, Line 58 — "If so, enter $260 on line 58." — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26; the amount is predicated on the federal maximum for no qualifying child — N.J.S.A. 54A:4-7(a)(4), as amended by P.L. 2021, c.130 — "Calculation of the New Jersey earned income tax credit available to individuals pursuant to this paragraph shall be predicated on the federal maximum amount for taxpayers with no qualifying child" — [snapshot `2026-10-26--nj-pl-2021-c130`](sources/2026-10-26--nj-pl-2021-c130/content.md), accessed 2026-10-26; the federal maximum credit with no qualifying child for 2025 is $649, of which 40% is $259.60 — Rev. Proc. 2024-40, § 2.06(1), table — "Number of Qualifying Children Item One Two Three or More None Earned Income Amount $12,730 $17,880 $17,880 $8,490 Maximum Amount of Credit $4,328 $7,152 $8,046 $649" — [snapshot `2026-10-13--irs-rev-proc-2024-40`](../../federal/eitc/sources/2026-10-13--irs-rev-proc-2024-40/content.md), accessed 2026-10-13
  - residency_months = the months of the tax year the household lived in New Jersey, counting any month with 15 days or more, so 12 for a full-year resident — N.J.S.A. 54A:4-7(b), as amended by P.L. 2021, c.130 — "In the case of a part-year resident claimant, the amount of the credit allowed pursuant to this section shall be pro-rated, based upon that proportion which the total number of months of the claimant's residency in the taxable year bears to 12 in that period. For this purpose, 15 days or more shall constitute a month." — [snapshot `2026-10-26--nj-pl-2021-c130`](sources/2026-10-26--nj-pl-2021-c130/content.md), accessed 2026-10-26
- Assumptions:
  - N/A
- Approximations:
  - sources prorate the credit by the months of New Jersey residency, counting any month with 15 days or more; the method above applies the full-year credit, because the screener does not collect how many months of the tax year the household lived in New Jersey.
  - sources take 40% of the federal credit allowed for the tax year; the method above takes 40% of the federal estimate in `federal_eitc_spec.md` §7, so it carries that estimate's approximations, such as income measured now rather than for 2025, because the screener does not collect what that spec lists.
  - sources apply a refund to debts owed to New Jersey, the Internal Revenue Service or another claimant state; the method above reports the credit with no offset, because the screener does not collect whether a household owes an offsettable debt or how much.
- Source: the refund offset in `Approximations` — Check Your Refund Status, Why is your refund different than you expected? — "Your refund can be used to pay debts you owe to: The State of New Jersey, including any of its agencies. The Internal Revenue Service. Another claimant state/city that has a personal income tax set-off agreement with New Jersey." — [snapshot `2026-10-26--nj-check-refund-status`](sources/2026-10-26--nj-check-refund-status/content.md), accessed 2026-10-26
- Source: the credit can be refunded — 2025 NJ-1040 instructions, Line 58 — "earned income. It reduces the amount of tax you owe and can" — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
- Source: the credit can be refunded — 2025 NJ-1040 instructions, Line 58 — "give you a refund." — [snapshot `2026-10-26--nj-1040-instructions-2025`](sources/2026-10-26--nj-1040-instructions-2025/content.md), accessed 2026-10-26
- Source: the credit is refunded where it exceeds the tax owed — N.J.S.A. 54A:4-7(c), as amended by P.L. 2021, c.130 — "If the credit exceeds the amount of tax otherwise due, that amount of excess shall be an overpayment for the purposes of N.J.S.54A:9-7" — [snapshot `2026-10-26--nj-pl-2021-c130`](sources/2026-10-26--nj-pl-2021-c130/content.md), accessed 2026-10-26

## 8. Test Scenarios

**Coverage map**

| Slug | Scenarios |
|---|---|
| `federal_eitc_allowed` | 1, 3, 5, 6, 7, 8, 9, 11, 13, 14, 15, 16, 17, 20 |
| `age_18_or_older` | 3, 4 |
| `no_qualifying_child` | 3, 9 |
| `valid_social_security_number` | — enforced by the program record; verified by `verify-program-record` |
| `federal_requirements_except_age` | 3, 5, 8, 10, 12, 14, 18, 19 |
| route (value axis) | 3, 5, 6, 8, 14, 15 |
| federal credit amount (value axis) | 1, 2, 6, 13, 15, 16, 20 |
| months of New Jersey residency (value axis) | — none; the screener holds no months of residency, so every scenario is a full year (see §7 Approximations) |

**Known scenario gaps**: `social_security_numbers` (degrades `valid_social_security_number`), `not_claimed_as_dependent` (degrades `federal_requirements_except_age`), `civil_union_joint_return` (degrades `federal_eitc_allowed`, `federal_requirements_except_age`)

**Routes with no scenario**: N/A - none

### Scenario 1: Single parent with one young child

**Checking**: `federal_eitc_allowed`, federal credit amount (value axis) — the golden path on the `federal_credit` route, 40% of a federal credit on the plateau

**Expected**: Eligible — $1,731.20/year estimated (40% × $4,328, the federal credit for one qualifying child, single, $20,000, from `federal_eitc_spec.md` scenario 1)

**Steps**:

* Location: ZIP `07102`, county `Essex County`
* Person 1: age 30, head of household, wages $20,000/year
* Person 2: age 8, child, no income

**Kills**: a calculator that returns nothing, or the flat $260, for an ordinary working parent.

### Scenario 2: Single parent, one child, in the federal phase-out

**Checking**: federal credit amount (value axis) — a different federal lookup, so a different 40%

**Expected**: Eligible — $1,432.40/year estimated (40% × $3,581, the federal credit for one qualifying child, single, $28,000, from `federal_eitc_spec.md` scenario 5)

**Steps**:

* Location: ZIP `07102`, county `Essex County`
* Person 1: age 33, head of household, wages $28,000/year
* Person 2: age 4, child, no income

**Kills**: a calculator that pays 40% of the maximum federal credit instead of 40% of the credit this household gets.

### Scenario 3: Childless 18-year-old

**Checking**: `age_18_or_older`, `no_qualifying_child`, `federal_requirements_except_age`, `federal_eitc_allowed`, route (value axis) — the `age_expansion` route at its youngest eligible age, with the federal credit turned away on age; `federal_requirements_except_age` asserts the approximation `not_claimed_as_dependent`

**Expected**: Eligible — $260/year estimated (the flat amount for 2025 for a filer with no qualifying child who misses the federal credit only on age)

**Steps**:

* Location: ZIP `07102`, county `Essex County`
* Person 1: age 18 at the end of 2025, head of household, wages $9,000/year

**Kills**: an age floor above 18 that still admits 24-year-olds — tests MFB's not-claimed-as-dependent approximation, not verified policy.

### Scenario 4: Childless 17-year-old

**Checking**: `age_18_or_older` — one year under the floor

**Expected**: Ineligible — `age_18_or_older` fails

**Steps**:

* Location: ZIP `07102`, county `Essex County`
* Person 1: age 17 at the end of 2025, head of household, wages $9,000/year

**Kills**: an off-by-one that admits 17-year-olds.

### Scenario 5: Childless 24-year-old, federally ineligible

**Checking**: `federal_requirements_except_age`, `federal_eitc_allowed`, route (value axis) — a household the federal credit turns away on age and New Jersey admits; `federal_requirements_except_age` asserts the approximation `not_claimed_as_dependent`

**Expected**: Eligible — $260/year estimated (the flat amount; the federal credit is $0 at 24, and even setting age aside, 40% of its $312 would be only $124.80)

**Steps**:

* Location: ZIP `07102`, county `Essex County`
* Person 1: age 24 at the end of 2025, head of household, wages $15,000/year

**Kills**: a calculator that applies the federal 25 to 64 band to NJ, or pays this household 40% of a federal credit of $0 — tests MFB's not-claimed-as-dependent approximation, not verified policy.

### Scenario 6: Childless 25-year-old, the federal age band's lower end

**Checking**: `federal_eitc_allowed`, route (value axis), federal credit amount (value axis) — the `federal_credit` route, where the amount is 40% of the federal credit rather than the flat $260

**Expected**: Eligible — $124.80/year estimated (40% × $312, the federal credit with no qualifying child, single, $15,000, from `federal_eitc_spec.md` scenario 24)

**Steps**:

* Location: ZIP `07102`, county `Essex County`
* Person 1: age 25 at the end of 2025, head of household, wages $15,000/year

**Kills**: a calculator that pays the flat $260 to every childless filer 18 or older.

### Scenario 7: Childless 64-year-old, the federal age band's upper end

**Checking**: `federal_eitc_allowed` — the last age on the `federal_credit` route

**Expected**: Eligible — $124.80/year estimated (40% × $312, the federal credit with no qualifying child, single, $15,000)

**Steps**:

* Location: ZIP `07102`, county `Essex County`
* Person 1: age 64 at the end of 2025, head of household, wages $15,000/year

**Kills**: an off-by-one that moves a 64-year-old to the flat $260 or turns them away.

### Scenario 8: Childless 65-year-old

**Checking**: `federal_requirements_except_age`, `federal_eitc_allowed`, route (value axis) — the first age outside the federal band, with no maximum age; `federal_requirements_except_age` asserts the approximation `not_claimed_as_dependent`

**Expected**: Eligible — $260/year estimated (the flat amount; the federal credit is $0 at 65)

**Steps**:

* Location: ZIP `07102`, county `Essex County`
* Person 1: age 65 at the end of 2025, head of household, wages $15,000/year

**Kills**: an upper age limit carried over from the federal 64, which P.L. 2021, c.130 removed — tests MFB's not-claimed-as-dependent approximation, not verified policy.

### Scenario 9: Parent aged 22 with a young child

**Checking**: `no_qualifying_child`, `federal_eitc_allowed` — a filer under 25 with a qualifying child takes `federal_credit` and gets 40% of the federal credit, not the flat $260

**Expected**: Eligible — $1,731.20/year estimated (40% × $4,328, the federal credit for one qualifying child, single, $20,000, from `federal_eitc_spec.md` scenario 22)

**Steps**:

* Location: ZIP `07102`, county `Essex County`
* Person 1: age 22, head of household, wages $20,000/year
* Person 2: age 3, child, no income

**Kills**: a calculator that drops the child count for filers under 25, or lets `age_expansion` outrank `federal_credit`, and pays the flat $260.

### Scenario 10: Childless 24-year-old at the earned income limit

**Checking**: `federal_requirements_except_age` — the federal income limit still applies on the `age_expansion` route

**Expected**: Ineligible — `federal_requirements_except_age` fails ($19,104 is not below the no-child limit)

**Steps**:

* Location: ZIP `07102`, county `Essex County`
* Person 1: age 24 at the end of 2025, head of household, wages $19,104/year

**Kills**: an age-expansion route that skips the federal income limit and pays the $260 to any childless filer 18 or older.

### Scenario 11: Childless 30-year-old at the earned income limit

**Checking**: `federal_eitc_allowed` — the `federal_credit` route turns away a household at the limit

**Expected**: Ineligible — `federal_eitc_allowed` fails ($19,104 is not below the no-child limit)

**Steps**:

* Location: ZIP `07102`, county `Essex County`
* Person 1: age 30 at the end of 2025, head of household, wages $19,104/year

**Kills**: a calculator that admits a childless 25-to-64 filer at the federal income limit.

### Scenario 12: Childless 24-year-old in the last table row that pays a credit

**Checking**: `federal_requirements_except_age` — asserts the approximation `not_claimed_as_dependent`

**Expected**: Eligible — $260/year estimated (ignoring age, the federal credit is $2, from the $19,050–$19,099 row)

**Steps**:

* Location: ZIP `07102`, county `Essex County`
* Person 1: age 24 at the end of 2025, head of household, wages $19,099/year

**Kills**: an age-expansion test that cuts off before the federal table does — tests MFB's not-claimed-as-dependent approximation, not verified policy.

### Scenario 13: Childless 30-year-old in the last table row that pays a credit

**Checking**: `federal_eitc_allowed`, federal credit amount (value axis)

**Expected**: Eligible — $0.80/year estimated (40% × $2)

**Steps**:

* Location: ZIP `07102`, county `Essex County`
* Person 1: age 30 at the end of 2025, head of household, wages $19,099/year

**Kills**: a calculator that drops a small federal credit or rounds 40% of it to $0.

### Scenario 14: Married couple, both under 25, no child

**Checking**: `federal_requirements_except_age`, `federal_eitc_allowed`, route (value axis) — asserts the approximation `not_claimed_as_dependent`

**Expected**: Eligible — $260/year estimated (federal $0 on age; ignoring age, the joint no-child credit at $20,000 is $473)

**Steps**:

* Location: ZIP `07102`, county `Essex County`
* Person 1: age 22 at the end of 2025, head of household, wages $20,000/year
* Person 2: age 23, spouse, no income

**Kills**: single-filer limits applied to a married couple on `age_expansion` — tests MFB's not-claimed-as-dependent approximation, not verified policy.

### Scenario 15: Married, only the spouse in the federal age band

**Checking**: `federal_eitc_allowed`, route (value axis), federal credit amount (value axis)

**Expected**: Eligible — $189.20/year estimated (40% × $473, joint, no child)

**Steps**:

* Location: ZIP `07102`, county `Essex County`
* Person 1: age 22 at the end of 2025, head of household, wages $20,000/year
* Person 2: age 30, spouse, no income

**Kills**: a calculator that reads only the head's age and pays the flat $260.

### Scenario 16: Married couple aged 30 in the last joint table row that pays a credit

**Checking**: `federal_eitc_allowed`, federal credit amount (value axis)

**Expected**: Eligible — $1.20/year estimated (40% × $3, joint, no child, the $26,150–$26,199 row)

**Steps**:

* Location: ZIP `07102`, county `Essex County`
* Person 1: age 30 at the end of 2025, head of household, wages $26,199/year
* Person 2: age 30, spouse, no income

**Kills**: a calculator that applies the single no-child limit to a married couple, or drops a small joint federal credit.

### Scenario 17: Married couple aged 30 at the joint earned income limit

**Checking**: `federal_eitc_allowed`

**Expected**: Ineligible — `federal_eitc_allowed` fails ($26,214 is not below the joint no-child limit)

**Steps**:

* Location: ZIP `07102`, county `Essex County`
* Person 1: age 30 at the end of 2025, head of household, wages $26,214/year
* Person 2: age 30, spouse, no income

**Kills**: a calculator that admits a married couple at the joint federal limit.

### Scenario 18: Married couple under 25 in the last joint table row that pays a credit

**Checking**: `federal_requirements_except_age` — asserts the approximation `not_claimed_as_dependent`

**Expected**: Eligible — $260/year estimated (federal $0 on age; ignoring age, the joint no-child credit at $26,199 is $3)

**Steps**:

* Location: ZIP `07102`, county `Essex County`
* Person 1: age 22 at the end of 2025, head of household, wages $26,199/year
* Person 2: age 23, spouse, no income

**Kills**: an age-expansion test that uses the single no-child limit for a married couple — tests MFB's not-claimed-as-dependent approximation, not verified policy.

### Scenario 19: Married couple under 25 at the joint earned income limit

**Checking**: `federal_requirements_except_age`

**Expected**: Ineligible — `federal_requirements_except_age` fails ($26,214 is not below the joint no-child limit)

**Steps**:

* Location: ZIP `07102`, county `Essex County`
* Person 1: age 22 at the end of 2025, head of household, wages $26,214/year
* Person 2: age 23, spouse, no income

**Kills**: an age-expansion route that pays the $260 to a married couple at or over the joint federal limit.

### Scenario 20: Head with a domestic partner, both working

**Checking**: `federal_eitc_allowed`, federal credit amount (value axis) — `federal_eitc_allowed` asserts the approximation `civil_union_joint_return`

**Expected**: Eligible — $124.80/year estimated (40% × $312, single, no child, $15,000; the partner's income is not added)

**Steps**:

* Location: ZIP `07102`, county `Essex County`
* Person 1: age 30 at the end of 2025, head of household, wages $15,000/year
* Person 2: age 30, domestic partner, wages $15,000/year

**Kills**: a calculator that treats a domestic partner as a spouse and works out a joint credit — tests MFB's civil-union approximation, not verified policy.

## 9. Research Sources

| Snapshot | Tier | Title | URL | Retrieved |
|---|---|---|---|---|
| `2026-10-26--nj-pl-2021-c130` | 1 | P.L. 2021, c.130 (A5345) — amends N.J.S.A. 54A:4-7 | https://pub.njleg.gov/bills/2020/AL21/130_.HTM | 2026-10-26 |
| `2026-10-26--nj-1040-instructions-2025` | 2 | 2025 NJ-1040 Resident Return instructions | https://www.nj.gov/treasury/taxation/pdf/current/1040i.pdf | 2026-10-26 |
| `2026-10-26--nj-eitc-notice-to-employees-2025` | 2 | Notice to Employees: 2025 Earned Income Tax Credit (eitcstatement.pdf) | https://www.nj.gov/treasury/taxation/pdf/eitcstatement.pdf | 2026-10-26 |
| `2026-10-26--nj-eitc-overview` | 2 | NJ Earned Income Tax Credit (NJEITC) overview | https://www.nj.gov/treasury/taxation/eitc/eitcinfo.shtml | 2026-10-26 |
| `2026-10-26--nj-check-refund-status` | 2 | Check Your Refund Status | https://www.nj.gov/treasury/taxation/checkrefundstatus.shtml | 2026-10-26 |
| `2026-10-26--nj-eitc-received-a-letter` | 2 | NJEITC: I Received a Letter | https://www.nj.gov/treasury/taxation/eitc/replyeitc.shtml | 2026-10-26 |
| `2026-10-28--nj-file-pay-manage` | 2 | File, Pay, and Manage (Individual Income Tax Filing Options) | https://www.nj.gov/treasury/taxation/payments-notices.shtml | 2026-10-28 |
