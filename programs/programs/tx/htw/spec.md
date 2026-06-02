# Healthy Texas Women (TX) Program Implementation

## Program Details

- **Program**: Healthy Texas Women
- **State**: TX
- **White Label**: tx
- **Research Date**: 2026-05-22
- **Review Date**: 2026-05-28

## Eligibility Criteria

1. **Must be female (assigned female at birth or identify as female for reproductive health services)** ⚠️ *data gap*
   - Note: The screener does not collect sex or gender information for household members. This is a fundamental eligibility requirement for the program. Without a sex/gender field, we cannot filter out male applicants. Assume all screener users are eligible for this criterion (inclusive assumption).
   - Source: HTW Who Can Apply page: 'Women ages 15 through 44'; Program name 'Healthy Texas Women'

2. **Must be age 15 through 44 for standard HTW (or age 18-44 for HTW Plus)**
   - Screener fields:
     - `household_member.birth_year`
     - `household_member.birth_month`
   - Source: HTW Who Can Apply page: 'Women ages 15 through 44'; TMHP HTW Handbook Chapter 2: HTW Plus for ages 18-44

3. **Household income must be at or below the state's income limit (204.2% of the Federal Poverty Level, effective March 1, 2026)**
   - Screener fields:
     - `household_size`
     - `calc_gross_income("monthly", ["all"])`
   - Source: HTW Who Can Apply page: 'Have a household income at or below 200% of the federal poverty level'; TMHP HTW Handbook Chapter 2; Texas HHS HTW income limit table (effective March 1, 2026)
   - Note: Texas HHS applies the threshold at 204.2% FPL in practice. Monthly limits: 1 person $2,716 / 2 people $3,682 / 3 people $4,649 / 4 people $5,616 / 5 people $6,582.

4. **Must be a Texas resident**
   - Screener fields:
     - `zipcode`
     - `county`
   - Source: HTW Who Can Apply page: 'Be a resident of the state of Texas'

5. **Must not be enrolled in Medicaid or CHIP at the time of application**
   - Screener fields:
     - `insurance["medicaid"]`
     - `insurance["chp"]`
   - Source: HTW Who Can Apply page: 'Not be enrolled in Medicaid at the time you apply'; HTW FAQ: 'You cannot be enrolled in Medicaid or CHIP when you apply for HTW'

6. **Must not be pregnant at the time of application (for standard HTW; pregnant women are referred to Medicaid for Pregnant Women instead)**
   - Screener fields:
     - `household_member.pregnant`
   - Source: HTW FAQ: 'If you are pregnant, you may qualify for Medicaid for Pregnant Women'; HTW Who Can Apply implies non-pregnant status for HTW enrollment

7. **Must not have other comprehensive health insurance coverage (Medicare, employer-sponsored, private insurance, VA, etc.)**
   - Screener fields:
     - `insurance["employer"]`
     - `insurance["private"]`
     - `insurance["medicare"]`
     - `insurance["va"]`
   - Source: HTW Who Can Apply page: 'Not have health coverage, including...Medicare'; HTW FAQ confirms no other insurance

8. **Must be a U.S. citizen, U.S. national, or qualified non-citizen (legal immigration status required)** ⚠️ *data gap*
   - Note: The screener does not collect citizenship or immigration status. HTW requires U.S. citizenship, U.S. national status, or qualified non-citizen status (e.g., lawful permanent resident, refugee, asylee). Undocumented immigrants are not eligible for standard HTW. This is addressed at the config level via `legal_status_required` — undocumented (`non_citizen`) is excluded from the program.
   - Source: HTW Who Can Apply page: 'Be a U.S. citizen or qualified non-citizen'; TMHP HTW Handbook Chapter 2 references citizenship/immigration documentation requirements

## Benefit Value

This is a free health services program — there is no fixed cash benefit value. Services are provided at no cost to the enrollee. The `estimated_value` field is set to "Varies based on services used" and no calculator value is displayed. This is appropriate for a services-based program.

## Implementation Coverage

- ✅ Evaluable criteria: 6 (criteria 2, 3, 4, 5, 6, 7)
- ⚠️ Data gaps: 2 (criteria 1, 8)

The core financial eligibility (income at or below 204.2% FPL) and age requirements (15-44) can be well-evaluated. Insurance status exclusions (Medicaid, CHIP, Medicare, employer, private) are well-covered by existing health insurance fields. The program is Texas-specific and residency can be validated via zipcode/county. The most critical gaps are: (1) no sex/gender field to confirm the applicant is female, and (2) no citizenship/immigration status field (partially addressed via `legal_status_required` config).

## Research Sources

- [Healthy Texas Women (HTW) Program Overview – Official Program Website](https://www.healthytexaswomen.org/healthcare-programs/healthy-texas-women)
- [Texas HHS – Healthy Texas Women Program Provider Information and Resources](https://www.hhs.texas.gov/providers/health-services-providers/healthy-texas-women-program-providers)
- [Texas Children's Health Plan – Provider Alert: Healthy Texas Women Program Benefits Summary](https://www.texaschildrenshealthplan.org/news/provider-alert/healthy-texas-women-program-benefits)
- [TMHP Notice: Healthy Texas Women (HTW) Plus Services Available September 1, 2020 (PDF)](http://www.tmhp.com/News_Items/2020/08-August/082820%20Healthy%20Texas%20Women%20HTW%20Plus%20Services%20Available%20September%201,%202020.pdf)
- [Healthy Texas Women – Who Can Apply: Eligibility Requirements](https://www.healthytexaswomen.org/healthcare-programs/healthy-texas-women/htw-who-can-apply)
- [Healthy Texas Women – Frequently Asked Questions (FAQ)](https://www.healthytexaswomen.org/healthcare-programs/healthy-texas-women/htw-questions-answers)
- [Healthy Texas Women – How to Apply for HTW Coverage](https://www.healthytexaswomen.org/healthcare-programs/healthy-texas-women/htw-how-apply)

## Acceptance Criteria

[ ] Scenario 1 (Clearly Eligible Single Woman Age 28 - Typical HTW Applicant): User should be **eligible**
[ ] Scenario 2 (Age 44, Income at Exactly the Income Limit, Household of 1): User should be **eligible**
[ ] Scenario 3 (Income Just Below Limit for Household of 3): User should be **eligible**
[ ] Scenario 4 (Income Exactly at Limit for Household of 4): User should be **eligible**
[ ] Scenario 5 (Income Just Above Limit for Household of 2): User should be **ineligible**
[ ] Scenario 6 (Age Exactly 15 - Minimum Age Boundary): User should be **eligible**
[ ] Scenario 7 (Age 14 - Just Below Minimum Age): User should be **ineligible**
[ ] Scenario 8 (Age 40 - Comfortably Within Range): User should be **eligible**
[ ] Scenario 9 (Excluded Due to Current Medicaid Enrollment): User should be **ineligible**
[ ] Scenario 10 (Mixed Household - Eligible Woman with Ineligible Husband and Child): User should be **eligible**
[ ] Scenario 11 (Multiple Eligible Women in Same Household - Two Sisters Ages 22 and 30): User should be **eligible**
[ ] Scenario 12 (Age Exactly 44 with Birthday This Month - Upper Age Boundary): User should be **eligible**
[ ] Scenario 13 (Ineligible Due to Pregnancy): User should be **ineligible**
[ ] Scenario 14 (Ineligible Due to Existing Employer Health Insurance): User should be **ineligible**
