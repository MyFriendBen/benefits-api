# NJ FamilyCare Cover All Kids (NJ) — Program Spec

## 1. Header

- **Program Tier**: `standalone`
- **Program Key**: `nj_cover_all_kids`
- **White Label**: NJ
- **Engine**: `MFB`
- **Calculator**: `white_labels/nj/cover_all_kids`, class `NjCoverAllKids`
- **Calculator added**: 2026-10-14
- **Spec last verified**: 2026-10-15
- **Rules last changed**: N/A - standalone

## 2. Inheritance & Variance

- **Tier verified**: 2026-10-07
- **Inherits from**: N/A - standalone
- **Variance table**: N/A - standalone

## 3. Eligibility Structure

**Routes**: N/A - single path

**Structure**: `nj_resident` AND `age_under_19` AND `income_limit` [degraded by: `tax_household_rules`, `magi_income_definition`, `dependent_marital_status`, `self_employment_net_earnings`] AND `immigration_status_any`

## 4. Covered Eligibility Criteria

1. `nj_resident` — **NJ FamilyCare includes New Jersey residents**
   - Label: Lives in New Jersey
   - Routes: N/A - single path
   - Evaluation scope: `household`
   - Inheritance status: `N/A`
   - Enforced by: `white-label`
   - Fields: —
   - Logic: —
   - Approximations:
     - N/A
   - Source: NJ FamilyCare, Who is Eligible? — "NJ FamilyCare includes New Jersey residents; all are eligible to apply." — [snapshot `2026-10-06--njfc-who-is-eligible`](sources/2026-10-06--njfc-who-is-eligible/content.md), accessed 2026-10-06
   - Source: NJ Department of Human Services, Cover All Kids FAQ, "What information does my child need for eligibility?" — "There are two main pieces of information in the application: where you live (NJ residence) and how much money you make (income)." — [snapshot `2026-10-07--nj-dhs-cover-all-kids-faqs`](sources/2026-10-07--nj-dhs-cover-all-kids-faqs/content.md), accessed 2026-10-07
   - Conflicting source: N/A

2. `age_under_19` — **NJ FamilyCare includes all NJ children regardless of immigration status from birth until they turn 19**
   - Label: Is under age 19
   - Routes: N/A - single path
   - Evaluation scope: `member`
   - Inheritance status: `N/A`
   - Enforced by: `calculator`
   - Fields: `birth_year_month` (HouseholdMember), `age` (HouseholdMember)
   - Logic: `HouseholdMember.calc_age()` < `19` passes
   - Approximations:
     - N/A
   - Source: NJ Department of Human Services, Cover All Kids FAQ, "What age counts as a kid?" — "NJ FamilyCare includes all NJ children regardless of immigration status from birth until they turn 19." — [snapshot `2026-10-07--nj-dhs-cover-all-kids-faqs`](sources/2026-10-07--nj-dhs-cover-all-kids-faqs/content.md), accessed 2026-10-07
   - Source: NJ FamilyCare, Who is Eligible? — "Children under 19 are eligible with higher incomes up to 355% of the Federal Poverty Level (FPL) ($9,763/month for a family of four)." — [snapshot `2026-10-06--njfc-who-is-eligible`](sources/2026-10-06--njfc-who-is-eligible/content.md), accessed 2026-10-06
   - Conflicting source: N/A

3. `income_limit` — **Children under 19 are eligible with household MAGI income up to 355% of the Federal Poverty Level; MAGI leaves out SSI, child support, gifts, workers' compensation and cash assistance such as TANF, and counts a dependent's income only if the dependent must file a federal tax return**
   - Label: Household MAGI income at or below 355% FPL
   - Routes: N/A - single path
   - Evaluation scope: `household`
   - Inheritance status: `N/A`
   - Enforced by: `calculator`
   - Fields: `type` (IncomeStream), `amount` (IncomeStream), `frequency` (IncomeStream), `relationship` (HouseholdMember), `birth_year_month` (HouseholdMember), `age` (HouseholdMember), `visually_impaired` (HouseholdMember), `year` (Program)
   - Logic: sum of `HouseholdMember.calc_gross_income("monthly", ["all"], exclude=["sSI", "childSupport", "gifts", "workersComp", "cashAssistance", "cashAssistanceOther"])` over members where `HouseholdMember.is_in_tax_unit()` is `true` <= `3.55` × the `Program.year` FPL for that member count ÷ `12` passes. A member who is neither `is_head()` nor `is_spouse()` adds their income to the sum only if they must file, which is true when any of these holds on yearly amounts, with A = `$2,050` for each of `calc_age()` >= `65` and `visually_impaired`:
     - unearned income > `$1,350` + A
     - earned income > `$16,100` + A
     - earned plus unearned income > the smaller of (the larger of `$1,350` and earned income + `$450`) and `$16,100`, plus A
     - `selfEmployment` income >= `$400`

     Earned income is `wages` and `selfEmployment`. Unearned income is every other counted type, except that `sSDisability`, `sSRetirement`, `sSSurvivor` and `sSDependent` enter these four tests only when one-half of them plus the member's other income is more than `$25,000`.
   - Approximations:
     - sources set the household by who files and who claims whom, with exceptions for children claimed by a non-custodial parent or by someone other than a parent; the Logic above counts the members the screener places in the child's tax unit, because the screener does not collect who expects to claim each child. → `tax_household_rules`
     - sources leave veterans' disability payments and alimony from divorces finalized on or after January 1, 2019 out of MAGI; the Logic above counts `veteran` and `alimony` in full, because the screener does not collect which kind of veteran payment or when the divorce was finalized. → `magi_income_definition`
     - sources give a married dependent a lower filing threshold; the Logic above applies the unmarried thresholds to every dependent, because the screener does not collect whether a dependent is married to someone outside the household. → `dependent_marital_status`
     - sources set the `$400` self-employment test on net earnings; the Logic above applies it to the `selfEmployment` amount entered, because the screener does not collect whether that amount is before or after business expenses. → `self_employment_net_earnings`
   - Source: NJ FamilyCare, Who is Eligible? — "Children under 19 are eligible with higher incomes up to 355% of the Federal Poverty Level (FPL) ($9,763/month for a family of four)." — [snapshot `2026-10-06--njfc-who-is-eligible`](sources/2026-10-06--njfc-who-is-eligible/content.md), accessed 2026-10-06
   - Source: NJ FamilyCare, Who is Eligible?, New Income and Household Size Calculations — "Financial eligibility for individuals seeking eligibility for NJ FamilyCare will be based on their Modified Adjusted Gross Income or MAGI." — [snapshot `2026-10-06--njfc-who-is-eligible`](sources/2026-10-06--njfc-who-is-eligible/content.md), accessed 2026-10-06
   - Source: 42 CFR 435.603(h)(1), Budget period, Applicants and new enrollees — "Financial eligibility for Medicaid for applicants, and other individuals not receiving Medicaid benefits at the point at which eligibility for Medicaid is being determined, must be based on current monthly household income and family size." — [snapshot `2026-10-07--42-cfr-435-603`](sources/2026-10-07--42-cfr-435-603/content.md), accessed 2026-10-07
   - Source: 42 CFR 435.603(d)(2)(i), Income of children and tax dependents — "The MAGI-based income of an individual who is included in the household of his or her natural, adopted or step parent and is not expected to be required to file a tax return under section 6012(a)(1) of the Code for the taxable year in which eligibility for Medicaid is being determined, is not included in household income whether or not the individual files a tax return." — [snapshot `2026-10-07--42-cfr-435-603`](sources/2026-10-07--42-cfr-435-603/content.md), accessed 2026-10-07
   - Source: 42 CFR 435.603(d)(2)(ii) — "The MAGI-based income of a tax dependent described in paragraph (f)(2)(i) of this section who is not expected to be required to file a tax return under section 6012(a)(1) of the Code for the taxable year in which eligibility for Medicaid is being determined is not included in the household income of the taxpayer whether or not such tax dependent files a tax return." — [snapshot `2026-10-07--42-cfr-435-603`](sources/2026-10-07--42-cfr-435-603/content.md), accessed 2026-10-07
   - Source: 42 CFR 435.603(e), MAGI-based income — "For the purposes of this section, MAGI-based income means income calculated using the same financial methodologies used to determine modified adjusted gross income as defined in section 36B(d)(2)(B) of the Code" — [snapshot `2026-10-07--42-cfr-435-603`](sources/2026-10-07--42-cfr-435-603/content.md), accessed 2026-10-07
   - Source: HealthCare.gov, What to include as income, "Don't count these income types" — "Child support", "Gifts", "Supplemental Security Income (SSI)", "Worker's compensation" — [snapshot `2026-10-14--healthcare-gov-what-to-include-as-income`](sources/2026-10-14--healthcare-gov-what-to-include-as-income/content.md), accessed 2026-10-14
   - Source: HealthCare.gov, What to include as income, "Count these income types" — "Federal taxable wages (from your job)", "Self-employment income", "Social Security", "Social Security Disability Income (SSDI)", "Unemployment compensation", "Retirement or pension income", "Investment income", "Rental and royalty income" — [snapshot `2026-10-14--healthcare-gov-what-to-include-as-income`](sources/2026-10-14--healthcare-gov-what-to-include-as-income/content.md), accessed 2026-10-14
   - Source: HealthCare.gov, What to include as income, "Do I include my dependents' income from things like summer jobs, work-study, and limited part-time work?" — "Count their income only if they need to file a federal tax return." — [snapshot `2026-10-14--healthcare-gov-what-to-include-as-income`](sources/2026-10-14--healthcare-gov-what-to-include-as-income/content.md), accessed 2026-10-14
   - Source: IRS Publication 501 (2025), Support Test (To Be a Qualifying Relative), Tax-exempt income — "Tax-exempt income includes certain social security benefits, welfare benefits, nontaxable life insurance proceeds, Armed Forces family allotments, nontaxable pensions, and tax-exempt interest." — [snapshot `2026-10-14--irs-pub-501-2025`](sources/2026-10-14--irs-pub-501-2025/content.md), accessed 2026-10-14
   - Source: IRS Publication 501 (2025), Table 2, Single dependents not 65 or older or blind — "You must file a return if any of the following apply. Your unearned income was more than $1,350. Your earned income was more than $15,750. Your gross income was more than the larger of: $1,350, or Your earned income (up to $15,300) plus $450." — [snapshot `2026-10-14--irs-pub-501-2025`](sources/2026-10-14--irs-pub-501-2025/content.md), accessed 2026-10-14
   - Source: IRS Publication 501 (2025), Table 2 — "Earned income includes salaries, wages, tips, professional fees, and taxable scholarship and fellowship grants. Gross income is the total of your unearned and earned income." — [snapshot `2026-10-14--irs-pub-501-2025`](sources/2026-10-14--irs-pub-501-2025/content.md), accessed 2026-10-14
   - Source: IRS Publication 501 (2025), Table 8, line 7b — "If born before January 2, 1961, or blind, multiply $2,000 ($1,600 if married) by the number in the box above." — [snapshot `2026-10-14--irs-pub-501-2025`](sources/2026-10-14--irs-pub-501-2025/content.md), accessed 2026-10-14
   - Source: IRS Publication 501 (2025), Table 3 — "You had net earnings from self-employment of at least $400." — [snapshot `2026-10-14--irs-pub-501-2025`](sources/2026-10-14--irs-pub-501-2025/content.md), accessed 2026-10-14
   - Source: IRS Publication 501 (2025), Table 1, note ** — "Don’t include any social security benefits unless (a) you’re married filing a separate return and you lived with your spouse at any time during 2025, or (b) one-half of your social security benefits plus your other gross income and any tax-exempt interest is more than $25,000 ($32,000 if married filing jointly)." — [snapshot `2026-10-14--irs-pub-501-2025`](sources/2026-10-14--irs-pub-501-2025/content.md), accessed 2026-10-14
   - Source: IRS Rev. Proc. 2025-32, §4.14(1), Standard Deduction, table row — "Unmarried Individuals (other than Surviving Spouses and Heads of $16,100 Households) (§ 1(j)(2)(C))" — [snapshot `2026-10-14--irs-rev-proc-2025-32`](sources/2026-10-14--irs-rev-proc-2025-32/content.md), accessed 2026-10-14
   - Source: IRS Rev. Proc. 2025-32, §4.14(2), Dependent — "For taxable years beginning in 2026, the standard deduction amount under § 63(c)(5) for an individual who may be claimed as a dependent by another taxpayer cannot exceed the greater of (1) $1,350, or (2) the sum of $450 and the individual's earned income." — [snapshot `2026-10-14--irs-rev-proc-2025-32`](sources/2026-10-14--irs-rev-proc-2025-32/content.md), accessed 2026-10-14
   - Source: IRS Rev. Proc. 2025-32, §4.14(3), Aged or blind — "The additional standard deduction amount is increased to $2,050 if the individual is also unmarried and not a surviving spouse." — [snapshot `2026-10-14--irs-rev-proc-2025-32`](sources/2026-10-14--irs-rev-proc-2025-32/content.md), accessed 2026-10-14
   - Conflicting source: Publication 501's Table 2 gives the 2025 thresholds; Rev. Proc. 2025-32 controls the amounts, because 42 CFR 435.603(d)(2) tests filing "for the taxable year in which eligibility for Medicaid is being determined", which is 2026; Publication 501 supplies the test's form, decided 2026-10-14.

4. `immigration_status_any` — **Children under 19, regardless of their immigration status, may continue to qualify for NJ FamilyCare**
   - Label: Any immigration status qualifies
   - Routes: N/A - single path
   - Evaluation scope: `member`
   - Inheritance status: `N/A`
   - Enforced by: `program-record`
   - Fields: `legal_status_required` (Program)
   - Logic: `Program.legal_status_required` includes `citizen`, `non_citizen`, `refugee`, `gc_5plus`, `gc_5less`, `otherWithWorkPermission`
   - Approximations:
     - N/A
   - Source: NJ FamilyCare, Who is Eligible? — "Children can qualify regardless of their immigration status." — [snapshot `2026-10-06--njfc-who-is-eligible`](sources/2026-10-06--njfc-who-is-eligible/content.md), accessed 2026-10-06
   - Source: NJ Division of Medical Assistance and Health Services, Federal Changes to NJ FamilyCare/Medicaid, Non-citizens who may continue to qualify — "Children under 19, regardless of their immigration status" — [snapshot `2026-10-06--nj-dmahs-federal-changes-2026`](sources/2026-10-06--nj-dmahs-federal-changes-2026/content.md), accessed 2026-10-06
   - Conflicting source: N/A

## 5. Missing Eligibility Criteria (Data Gaps)

1. `tax_household_rules` — **The household is set by tax filing: a child claimed as a tax dependent is in the household of the taxpayer claiming them, except someone claimed who is not the taxpayer's spouse or child, a child living with both parents who do not file jointly, and a child claimed by a non-custodial parent**
   - Label: Claimed children join filer's household, with three exceptions
   - Routes: N/A - single path
   - Evaluation scope: `household`
   - Inheritance status: `N/A`
   - Degrades: `income_limit`
   - Why: The screener does not collect who expects to claim each child as a tax dependent.
   - Effect: `varies`
   - Handling: `not surfaced`
   - Handling rationale: The agency builds the household from the tax return; a family can't change who claims whom to qualify, so there is nothing for them to act on.
   - Source: 42 CFR 435.603(f)(2), Basic rule for individuals claimed as a tax dependent — "In the case of an individual who expects to be claimed as a tax dependent by another taxpayer for the taxable year in which an initial determination or renewal of eligibility is being made, the household is the household of the taxpayer claiming such individual as a tax dependent" — [snapshot `2026-10-07--42-cfr-435-603`](sources/2026-10-07--42-cfr-435-603/content.md), accessed 2026-10-07
   - Source: 42 CFR 435.603(f)(2)(i) — "Individuals other than a spouse or child who expect to be claimed as a tax dependent by another taxpayer" — [snapshot `2026-10-07--42-cfr-435-603`](sources/2026-10-07--42-cfr-435-603/content.md), accessed 2026-10-07
   - Source: 42 CFR 435.603(f)(2)(ii) — "Individuals under the age specified by the State under paragraph (f)(3)(iv) of this section who expect to be claimed by one parent as a tax dependent and are living with both parents but whose parents do not expect to file a joint tax return" — [snapshot `2026-10-07--42-cfr-435-603`](sources/2026-10-07--42-cfr-435-603/content.md), accessed 2026-10-07
   - Source: 42 CFR 435.603(f)(2)(iii) — "Individuals under the age specified by the State under paragraph (f)(3)(iv) of this section who expect to be claimed as a tax dependent by a non-custodial parent." — [snapshot `2026-10-07--42-cfr-435-603`](sources/2026-10-07--42-cfr-435-603/content.md), accessed 2026-10-07

2. `magi_income_definition` — **MAGI leaves out veterans' disability payments, and alimony from divorces and separations finalized on or after January 1, 2019**
   - Label: Veterans' disability pay and post-2018 alimony don't count
   - Routes: N/A - single path
   - Evaluation scope: `household`
   - Inheritance status: `N/A`
   - Degrades: `income_limit`
   - Why: The screener does not collect whether a veteran's payment is disability pay or a pension, or when a divorce or separation paying alimony was finalized.
   - Effect: `narrows`
   - Handling: `not surfaced`
   - Handling rationale: It turns away households whose veterans' disability pay or recent alimony tips them over the limit, and those households never see Cover All Kids to read the description.
   - Source: HealthCare.gov, What to include as income, "Don't count these income types" — "Alimony for divorces and separations finalized on or after January 1, 2019", "Veterans' disability payments" — [snapshot `2026-10-14--healthcare-gov-what-to-include-as-income`](sources/2026-10-14--healthcare-gov-what-to-include-as-income/content.md), accessed 2026-10-14
   - Source: HealthCare.gov, What to include as income, "Count these income types" — "Alimony from divorces and separations finalized before January 1, 2019" — [snapshot `2026-10-14--healthcare-gov-what-to-include-as-income`](sources/2026-10-14--healthcare-gov-what-to-include-as-income/content.md), accessed 2026-10-14

3. `dependent_marital_status` — **A married dependent must file at a lower threshold: with any income if their spouse files separately and itemizes, and with $1,650 rather than $2,050 added for being 65 or older or blind**
   - Label: Married dependents face lower tax filing thresholds
   - Routes: N/A - single path
   - Evaluation scope: `member`
   - Inheritance status: `N/A`
   - Degrades: `income_limit`
   - Why: The screener does not collect whether a household member other than the head and spouse is married to someone outside the household.
   - Effect: `widens`
   - Handling: `not surfaced`
   - Handling rationale: A married dependent in a household applying for children's coverage is rare, and nothing in the description would change what the family reports.
   - Source: IRS Publication 501 (2025), Table 2, Married dependents — "Your gross income was at least $5 and your spouse files a separate return and itemizes deductions." — [snapshot `2026-10-14--irs-pub-501-2025`](sources/2026-10-14--irs-pub-501-2025/content.md), accessed 2026-10-14
   - Source: IRS Rev. Proc. 2025-32, §4.14(3), Aged or blind — "For taxable years beginning in 2026, the additional standard deduction amount under § 63(f) for the aged or the blind is $1,650." — [snapshot `2026-10-14--irs-rev-proc-2025-32`](sources/2026-10-14--irs-rev-proc-2025-32/content.md), accessed 2026-10-14

4. `self_employment_net_earnings` — **A dependent with $400 or more of net self-employment earnings, after business expenses, must file a tax return**
   - Label: Dependent with $400+ net self-employment earnings must file
   - Routes: N/A - single path
   - Evaluation scope: `member`
   - Inheritance status: `N/A`
   - Degrades: `income_limit`
   - Why: The screener does not collect whether the self-employment amount entered is before or after business expenses.
   - Effect: `narrows`
   - Handling: `not surfaced`
   - Handling rationale: It turns away households whose teenager's small business clears $400 only before expenses, and those households never see Cover All Kids to read the description.
   - Source: IRS Publication 501 (2025), Table 3 — "You had net earnings from self-employment of at least $400." — [snapshot `2026-10-14--irs-pub-501-2025`](sources/2026-10-14--irs-pub-501-2025/content.md), accessed 2026-10-14

## 6. Access

1. `apply_online` — **Online – njfamilycare.org. Applications are available in English and Spanish.**
   - Question: `apply_online`
   - Kind: `process`
   - Inheritance status: `N/A`
   - Handling: `sets apply_button_link`
   - Handling rationale: The apply button is where a family shown Cover All Kids starts, so it goes to NJ FamilyCare's online application at https://dmahs-nj.my.site.com/familycare/quickstart — the page the "Apply Here" button on snapshots `2026-10-06--njfc-home` and `2026-10-06--njfc-who-is-eligible` links to.
   - Source: NJ Department of Human Services, Cover All Kids FAQ, "Where can I apply?" — "Online – njfamilycare.org. Applications are available in English and Spanish." — [snapshot `2026-10-07--nj-dhs-cover-all-kids-faqs`](sources/2026-10-07--nj-dhs-cover-all-kids-faqs/content.md), accessed 2026-10-07

2. `apply_by_phone_or_in_person` — **Families can also apply over the phone or in person at the County Board of Social Services**
   - Question: `apply_other_channels`
   - Kind: `process`
   - Inheritance status: `N/A`
   - Handling: `surfaces in description`
   - Handling rationale: Families who can't apply online, or need another language, learn they can call or go to their county office instead.
   - Source: NJ Department of Human Services, Cover All Kids FAQ, "Where can I apply?" — "Over the phone – 1-800-701-0710 (TTY: 711)" — [snapshot `2026-10-07--nj-dhs-cover-all-kids-faqs`](sources/2026-10-07--nj-dhs-cover-all-kids-faqs/content.md), accessed 2026-10-07
   - Source: NJ Department of Human Services, Cover All Kids FAQ, "Where can I apply?" — "In person at the County Board of Social Services" — [snapshot `2026-10-07--nj-dhs-cover-all-kids-faqs`](sources/2026-10-07--nj-dhs-cover-all-kids-faqs/content.md), accessed 2026-10-07

3. `application_information` — **The application asks where you live and how much money you make; children without "qualified immigrant" status provide no additional documents and no Social Security number**
   - Question: `documents_required`
   - Kind: `process`
   - Inheritance status: `N/A`
   - Handling: `listed in documents`, `surfaces in description`
   - Handling rationale: Families listed in documents learn what to have ready; saying in the description that no immigration papers or Social Security number are needed reaches the families most likely to hold back from applying.
   - Source: NJ Department of Human Services, Cover All Kids FAQ, "What information does my child need for eligibility?" — "There are two main pieces of information in the application: where you live (NJ residence) and how much money you make (income)." — [snapshot `2026-10-07--nj-dhs-cover-all-kids-faqs`](sources/2026-10-07--nj-dhs-cover-all-kids-faqs/content.md), accessed 2026-10-07
   - Source: NJ Department of Human Services, Cover All Kids FAQ, "What information does my child need for eligibility?" — "Children applying for NJ FamilyCare without “qualified immigrant” status will not have to provide additional documents." — [snapshot `2026-10-07--nj-dhs-cover-all-kids-faqs`](sources/2026-10-07--nj-dhs-cover-all-kids-faqs/content.md), accessed 2026-10-07
   - Source: NJ Department of Human Services, Cover All Kids FAQ, "Does my child need a Social Security Number (SSN) to apply for NJ FamilyCare if they do not have a “qualified immigrant” status?" — "Children who do not have “qualified immigrant” status do not need to provide a social security number." — [snapshot `2026-10-07--nj-dhs-cover-all-kids-faqs`](sources/2026-10-07--nj-dhs-cover-all-kids-faqs/content.md), accessed 2026-10-07

4. `enrollment_help` — **NJ FamilyCare health benefits coordinators take applications by phone, with live translators available**
   - Question: `help_available`
   - Kind: `process`
   - Inheritance status: `N/A`
   - Handling: `listed in navigators`
   - Handling rationale: A family who needs help or another language gets a number to call on the program page.
   - Source: NJ Department of Human Services, Cover All Kids FAQ, "Who can apply for a child?" — "They can also apply over the phone by speaking to an NJ FamilyCare health benefits coordinator at 1-800-701-0710 (TTY: 711)." — [snapshot `2026-10-07--nj-dhs-cover-all-kids-faqs`](sources/2026-10-07--nj-dhs-cover-all-kids-faqs/content.md), accessed 2026-10-07
   - Source: NJ Department of Human Services, Cover All Kids FAQ, "Where can I apply?" — "Note: if you do not speak English, there are live translators available. Call 1-800-701-0710 (TTY: 711) and ask for live translation into your language." — [snapshot `2026-10-07--nj-dhs-cover-all-kids-faqs`](sources/2026-10-07--nj-dhs-cover-all-kids-faqs/content.md), accessed 2026-10-07

5. `annual_renewal` — **Members will have to renew their coverage once a year**
   - Question: `renewal`
   - Kind: `process`
   - Inheritance status: `N/A`
   - Handling: `surfaces in description`
   - Handling rationale: A family that enrolls a child needs to watch for NJ FamilyCare's mail and reply each year, or the child loses coverage they still qualify for.
   - Source: NJ Department of Human Services, Cover All Kids FAQ, "How often does my child have to renew their coverage?" — "Members will have to renew their coverage once a year. This is the same as standard NJ FamilyCare members." — [snapshot `2026-10-07--nj-dhs-cover-all-kids-faqs`](sources/2026-10-07--nj-dhs-cover-all-kids-faqs/content.md), accessed 2026-10-07
   - Source: NJ FamilyCare, Who is Eligible? — "Parents still need to renew the coverage each year." — [snapshot `2026-10-06--njfc-who-is-eligible`](sources/2026-10-06--njfc-who-is-eligible/content.md), accessed 2026-10-06

6. `application_time` — **Applying takes 15 - 30 minutes**
   - Question: `application_time`
   - Kind: `process`
   - Inheritance status: `N/A`
   - Handling: `sets estimated_application_time`
   - Handling rationale: The results card and the program page both render that field, so the description would say it a third time.
   - How the number was reached: compared — `wa_apple_health_for_kids` and `ks_chip`, both children's coverage applications, publish "15 - 30 minutes".
   - Source: N/A - compared; the Cover All Kids FAQ, who_eligbl.aspx and both home pages say nothing about how long the application takes.

**Questions with no rule**, as of 2026-10-07:

| Questions | Answer | Why / Source |
|---|---|---|
| `waitlist`, `waitlist_reopens`, `lottery`, `funding_limit` — `capacity` | `implied no` | No source in the set mentions a waitlist, lottery, enrollment cap or funding limit. |
| `priority_groups`, `set_asides` — `priority` | `implied no` | No source in the set mentions any order of service or set-aside among children who qualify. |
| `application_window`, `deadline`, `apply_before_event` — `timing` | `implied no` | No source in the set mentions an application window, a deadline, or an event to apply before. |
| `decision_time`, `delivery_time` — `timing` | `unknown` | The Cover All Kids FAQ, who_eligbl.aspx and both home pages were checked; none says how long a decision takes or when coverage starts. |
| `advance_registration` — `process` | `implied no` | The Cover All Kids FAQ's "Where can I apply?" lists online, phone and in-person applications as alternatives and names no interview, assessment or in-person step. |
## 7. Benefit Value

- Inheritance status: `N/A`
- Derivation: `estimate-mfb`
- value_format: `estimated_annual`
- Value: $3,915 per member
- Variation axes: `flat`
- Calculation: $545 NJ 2026 monthly benchmark premium for a 40-year-old ÷ 1.278 age-40 factor × 0.765 ages 0–14 factor × 12 months = $3,915
- Assumptions:
  - assumes the benchmark silver plan is comparable coverage to the standard NJ FamilyCare benefit package, substituted because Cover All Kids has no price of its own
  - assumes a family would pay the full unsubsidized premium for comparable coverage
  - assumes a child aged 15–18 costs the same as a child aged 0–14, though NJ's factors for each age from 15 to 18 are higher, so the value understates their premium
  - assumes each child is priced separately, though NJ caps a family's premium at three children under age 20
  - assumes KFF's statewide average, weighted by county plan selections, describes a family anywhere in New Jersey
- Approximations:
  - N/A
- Source: KFF, Marketplace Average Monthly Benchmark Premiums, 2026, New Jersey row — "| New Jersey | 545 |" — [snapshot `2026-10-14--kff-marketplace-benchmark-premiums-2026-rendered`](sources/2026-10-14--kff-marketplace-benchmark-premiums-2026-rendered/content.md), accessed 2026-10-14
- Source: KFF, Marketplace Average Monthly Benchmark Premiums, Notes — "Premiums were analyzed using the second-lowest cost silver (benchmark) premium for a 40-year-old in each county and weighted by county plan selections" — [snapshot `2026-10-14--kff-marketplace-benchmark-premiums-2026-rendered`](sources/2026-10-14--kff-marketplace-benchmark-premiums-2026-rendered/content.md), accessed 2026-10-14
- Source: NJ Department of Banking and Insurance, 2026 New Jersey Individual Health Benefits Plans and Rates, Age Rating Factors — "0-14 0.765 40 1.278" — [snapshot `2026-10-14--nj-dobi-ihc-rates-2026`](sources/2026-10-14--nj-dobi-ihc-rates-2026/content.md), accessed 2026-10-14
- Source: NJ Department of Banking and Insurance, 2026 New Jersey Individual Health Benefits Plans and Rates — "Monthly Base Rate is multipled by the Age Rating Factor to determine the monthly premium for each person to be covered." — [snapshot `2026-10-14--nj-dobi-ihc-rates-2026`](sources/2026-10-14--nj-dobi-ihc-rates-2026/content.md), accessed 2026-10-14
- Source: NJ Department of Banking and Insurance, 2026 New Jersey Individual Health Benefits Plans and Rates — "Note: For dependent children under age 20, the monthly premium is capped at the sum of the premiums for three children." — [snapshot `2026-10-14--nj-dobi-ihc-rates-2026`](sources/2026-10-14--nj-dobi-ihc-rates-2026/content.md), accessed 2026-10-14
- Source: CMS, Market Rating Reforms, State Specific Rating Variations — "If a cell is blank or a state is not listed, the federal default applies." — [snapshot `2026-10-14--cms-state-specific-rating-variations`](sources/2026-10-14--cms-state-specific-rating-variations/content.md), accessed 2026-10-14
- Source: CMS, Market Rating Reforms, State Specific Rating Variations, New Jersey row, whose individual-market age rating ratio and state-established age curve cells are blank — "| New Jersey | | | 1:1 | | 1.824:1* | Yes | 1:1 | | | | |" — [snapshot `2026-10-14--cms-state-specific-rating-variations`](sources/2026-10-14--cms-state-specific-rating-variations/content.md), accessed 2026-10-14
- Source: NJ Department of Human Services, Cover All Kids FAQ, "What benefits will children enrolled in NJ FamilyCare receive?" — "Members will receive the standard NJ FamilyCare benefit package" — [snapshot `2026-10-07--nj-dhs-cover-all-kids-faqs`](sources/2026-10-07--nj-dhs-cover-all-kids-faqs/content.md), accessed 2026-10-07

## 8. Test Scenarios

**Coverage map**

| Slug | Scenarios |
|---|---|
| `age_under_19` | 1, 4, 5 |
| `income_limit` | 1, 2, 3, 6, 7, 8, 9 |
| `immigration_status_any` | — enforced by the program record; verified by `verify-program-record` |

**Known scenario gaps**: `tax_household_rules` (degrades `income_limit`), `magi_income_definition` (degrades `income_limit`), `dependent_marital_status` (degrades `income_limit`), `self_employment_net_earnings` (degrades `income_limit`)

**Routes with no scenario**: N/A - single path

### Scenario 1: Two parents and two young children with moderate wages

**Checking**: `age_under_19`, `income_limit` — golden path; a newborn and a ten-year-old both clear age and income

**Expected**: Eligible — $7,830/year estimated ($3,915 × 2 eligible members)

**Steps**:

* Location: ZIP `07102`, county `Essex County`
* Person 1: age 35, head of household, wages $5,000/month
* Person 2: age 34, spouse, no income
* Person 3: age 0, child, no income
* Person 4: age 10, child, no income

**Kills**: a value computed per household instead of per eligible child, or an age floor that drops newborns.

### Scenario 2: Family of four just under the published limit

**Checking**: `income_limit` — at the limit: $1 under the $9,763/month family-of-four figure

**Expected**: Eligible — $7,830/year estimated ($3,915 × 2 eligible members)

**Steps**:

* Location: ZIP `07102`, county `Essex County`
* Person 1: age 35, head of household, wages $9,762/month
* Person 2: age 34, spouse, no income
* Person 3: age 8, child, no income
* Person 4: age 12, child, no income

**Kills**: a limit set below 355% FPL, or a strict `<` where the rule is "up to".

### Scenario 3: Family of four $1 over the published limit

**Checking**: `income_limit` — one step past the $9,763/month family-of-four figure

**Expected**: Ineligible — `income_limit` fails

**Steps**:

* Location: ZIP `07102`, county `Essex County`
* Person 1: age 35, head of household, wages $9,764/month
* Person 2: age 34, spouse, no income
* Person 3: age 8, child, no income
* Person 4: age 12, child, no income

**Kills**: a limit set above 355% FPL, or one computed for the wrong household size.

### Scenario 4: An 18-year-old in a low-income family

**Checking**: `age_under_19` — at the limit: the oldest age that qualifies

**Expected**: Eligible — $3,915/year estimated ($3,915 × 1 eligible member)

**Steps**:

* Location: ZIP `07102`, county `Essex County`
* Person 1: age 45, head of household, wages $3,000/month
* Person 2: age 44, spouse, no income
* Person 3: age 18, child, no income
* Person 4: age 25, child, no income

**Kills**: an off-by-one that drops 18-year-olds by testing `< 18` or `<= 17`.

### Scenario 5: A 19-year-old is the only young person in the family

**Checking**: `age_under_19` — one step past: the first age that doesn't qualify

**Expected**: Ineligible — `age_under_19` fails

**Steps**:

* Location: ZIP `07102`, county `Essex County`
* Person 1: age 45, head of household, wages $3,000/month
* Person 2: age 44, spouse, no income
* Person 3: age 19, child, no income
* Person 4: age 22, child, no income

**Kills**: an off-by-one that admits 19-year-olds by testing `<= 19`.

### Scenario 6: A teenager's summer-job wages don't count

**Checking**: `income_limit` — a dependent's $9,600 a year in wages is under every 2026 filing threshold, so it stays out of household income

**Expected**: Eligible — $7,830/year estimated ($3,915 × 2 eligible members)

**Steps**:

* Location: ZIP `07102`, county `Essex County`
* Person 1: age 40, head of household, wages $9,000/month
* Person 2: age 39, spouse, no income
* Person 3: age 16, child, wages $800/month
* Person 4: age 10, child, no income

**Kills**: a calculator that adds a dependent's income without checking whether the dependent must file, which puts this family at $9,800/month and over the limit.

### Scenario 7: A teenager who earns enough to file pushes the family over the limit

**Checking**: `income_limit` — a dependent's $18,000 a year in wages is over the $16,100 earned-income threshold, so it counts

**Expected**: Ineligible — `income_limit` fails

**Steps**:

* Location: ZIP `07102`, county `Essex County`
* Person 1: age 40, head of household, wages $9,000/month
* Person 2: age 39, spouse, no income
* Person 3: age 17, child, wages $1,500/month
* Person 4: age 10, child, no income

**Kills**: a calculator that leaves out every dependent's income, or one still using 2025's thresholds in a way that misses a teenager who must file.

### Scenario 8: Child support received doesn't count

**Checking**: `income_limit` — $2,000/month in child support would put this family over the limit if it counted

**Expected**: Eligible — $7,830/year estimated ($3,915 × 2 eligible members)

**Steps**:

* Location: ZIP `07102`, county `Essex County`
* Person 1: age 38, head of household, wages $8,000/month, child support received $2,000/month
* Person 2: age 37, spouse, no income
* Person 3: age 8, child, no income
* Person 4: age 12, child, no income

**Kills**: a calculator that counts every income type the screener collects, including income MAGI leaves out.

### Scenario 9: TANF cash assistance doesn't count

**Checking**: `income_limit` — $2,000/month in TANF would put this family over the limit if it counted

**Expected**: Eligible — $7,830/year estimated ($3,915 × 2 eligible members)

**Steps**:

* Location: ZIP `07102`, county `Essex County`
* Person 1: age 38, head of household, wages $8,000/month, TANF cash assistance $2,000/month
* Person 2: age 37, spouse, no income
* Person 3: age 8, child, no income
* Person 4: age 12, child, no income

**Kills**: a calculator that counts public assistance, which is tax-exempt and so outside MAGI.

## 9. Research Sources

| Snapshot | Tier | Title | URL | Retrieved |
|---|---|---|---|---|
| `2026-10-06--nj-dhs-cover-all-kids-home` | 2 | Cover All Kids — NJ Department of Human Services | https://nj.gov/coverallkids/ | 2026-10-06 |
| `2026-10-07--nj-dhs-cover-all-kids-faqs` | 2 | Cover All Kids — Frequently Asked Questions | https://nj.gov/coverallkids/faqs/ | 2026-10-07 |
| `2026-10-06--nj-dmahs-federal-changes-2026` | 2 | Federal Changes to NJ FamilyCare/Medicaid | https://www.nj.gov/humanservices/dmahs/obbba/medicaid-federal-changes.shtml | 2026-10-06 |
| `2026-10-06--njfc-home` | 2 | NJ FamilyCare home page | https://njfamilycare.dhs.state.nj.us/ | 2026-10-06 |
| `2026-10-06--njfc-who-is-eligible` | 2 | NJ FamilyCare — Who is Eligible? | https://njfamilycare.dhs.state.nj.us/who_eligbl.aspx | 2026-10-06 |
| `2026-10-07--42-cfr-435-603` | 1 | 42 CFR 435.603 — Application of modified adjusted gross income (MAGI) | https://www.ecfr.gov/api/versioner/v1/full/2026-10-05/title-42.xml?section=435.603 | 2026-10-07 |
| `2026-10-14--healthcare-gov-what-to-include-as-income` | 2 | HealthCare.gov — What to include as income | https://www.healthcare.gov/income-and-household-information/income/ | 2026-10-14 |
| `2026-10-14--irs-pub-501-2025` | 2 | IRS Publication 501 (2025) — Dependents, Standard Deduction, and Filing Information | https://www.irs.gov/publications/p501 | 2026-10-14 |
| `2026-10-14--irs-rev-proc-2025-32` | 2 | IRS Rev. Proc. 2025-32 — 2026 inflation-adjusted items | https://www.irs.gov/pub/irs-drop/rp-25-32.pdf | 2026-10-14 |
| `2026-10-14--nj-dobi-ihc-rates-2026` | 2 | NJ DOBI — 2026 New Jersey Individual Health Benefits Plans and Rates | https://www.nj.gov/dobi/division_insurance/ihcseh/ihcrates2026.pdf | 2026-10-14 |
| `2026-10-14--cms-state-specific-rating-variations` | 2 | CMS — Market Rating Reforms: State Specific Rating Variations | https://www.cms.gov/CCIIO/Programs-and-Initiatives/Health-Insurance-Market-Reforms/state-rating | 2026-10-14 |
| `2026-10-14--kff-marketplace-benchmark-premiums-2026-rendered` | 3 | KFF — Marketplace Average Monthly Benchmark Premiums | https://www.kff.org/affordable-care-act/state-indicator/marketplace-average-benchmark-premiums/ | 2026-10-14 |
