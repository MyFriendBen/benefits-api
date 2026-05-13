# Implement Women, Infants, and Children (WIC) Nutrition Program (WA)

## Program Details

* **Program**: Women, Infants, and Children (WIC) Nutrition Program
* **State**: WA
* **White Label**: wa
* **Research Date**: 2026-05-06

## Eligibility Criteria

1. **Categorical requirement: Must be a pregnant woman, postpartum woman (up to 6 months after end of pregnancy), breastfeeding woman (up to 12 months), infant (under 1 year), or child (ages 1-4, up but not including 5th birthday)**
   * Screener fields:
     * `birth_year`
     * `birth_month`
     * `pregnant`
     * `relationship`
   * Source: 7 CFR 246.7(c)(1); [https://doh.wa.gov/you-and-your-family/wic/wic-eligibility](https://doh.wa.gov/you-and-your-family/wic/wic-eligibility)
2. **Income eligibility: Household gross income at or below 185% of the Federal Poverty Level (FPL)**
   * Note: **Income is NOT used as a disqualifying criterion when any household member is enrolled in SNAP, Medicaid, or TANF** (see Criterion 3). The income check must be bypassed entirely when adjunctive eligibility applies -- do not fail eligibility based on income in those cases.
   * Note: Per WA DOH: "If you are pregnant, include each unborn child in household size." This means a pregnant single woman expecting one child uses HH of 2 thresholds; a pregnant woman expecting twins uses HH of 3 thresholds; etc.
   * Screener fields:
     * `household_size`
     * `income_streams`
     * `pregnant`
   * Source: 7 CFR 246.7(d)(1); [https://doh.wa.gov/you-and-your-family/wic/wic-eligibility](https://doh.wa.gov/you-and-your-family/wic/wic-eligibility)
3. **Adjunctive income eligibility: Participants in SNAP, Medicaid, or TANF are automatically income-eligible for WIC**
   * Note: When any of these programs is active for the household, income is not evaluated as a disqualifying criterion.
   * Screener fields:
     * `has_snap`
     * `has_medicaid`
     * `has_tanf`
   * Source: 7 CFR 246.7(d)(2)(iv); [https://doh.wa.gov/you-and-your-family/wic/wic-eligibility](https://doh.wa.gov/you-and-your-family/wic/wic-eligibility)
4. **Residency: Must reside in the state of Washington**
   * Screener fields:
     * `zipcode`
     * `county`
   * Source: 7 CFR 246.7(c)(1)(i); [https://doh.wa.gov/you-and-your-family/wic/wic-eligibility](https://doh.wa.gov/you-and-your-family/wic/wic-eligibility)
5. **Nutritional risk determination: Must be found at nutritional risk by a WIC health professional** :warning: *data gap*
   * Note: In-person clinical assessment at WIC clinic; cannot be pre-screened. Rarely a barrier for otherwise eligible individuals.
   * Impact: Low
   * Source: 7 CFR 246.7(c)(4); [https://doh.wa.gov/you-and-your-family/wic/wic-eligibility](https://doh.wa.gov/you-and-your-family/wic/wic-eligibility)
6. **Postpartum/breastfeeding window** :warning: *data gap*
   * Note: Non-breastfeeding postpartum women are eligible up to 6 months after end of pregnancy; breastfeeding women up to 12 months. No postpartum or breastfeeding status field exists in the screener. Can be approximated from infant age if an infant under 1 year is present in the household.
   * Impact: Medium
   * Source: 7 CFR 246.7(c)(1)(ii)-(iii); [https://doh.wa.gov/you-and-your-family/wic/wic-eligibility](https://doh.wa.gov/you-and-your-family/wic/wic-eligibility)

## Priority Criteria

None identified. WIC operates on a first-come, first-served basis within categorical and income eligibility, though federal regulations (7 CFR 246.7(e)) define a priority system for when local agencies reach capacity. This priority system is an administrative mechanism, not a pre-screening criterion.

## Benefit Value

* **Estimated value**: $80 per eligible household member per month (range: $50-$165)

**Methodology**: WIC provides food benefits that vary by participant category (pregnant/breastfeeding women, infants, and children each receive different monthly food packages). The national average WIC benefit was **$81.51 per participant per month in FY2024**. King County WA specifically reports approximately **$150/month for a family of two**.

For calculator purposes: multiply the number of WIC-eligible household members by $80/month, then express as an **annual** value ($80 x eligible members x 12).

**Counting methodology**: WIC-eligible household members include (a) the pregnant woman, (b) each unborn child she is expecting, (c) each infant under 1 year, and (d) each child ages 1-4. Per WA DOH, unborn children count toward both household size (for income test) and as separate WIC participants for benefit value calculation. Example: a pregnant woman expecting one child + one toddler under 5 = 3 eligible participants ($80 x 3 x 12 = $2,880/year).

**Value Estimate Sources**:

* [CBPP -- WIC average $81.51/participant/month in FY2024](https://www.cbpp.org/research/food-assistance/special-supplemental-nutrition-program-for-women-infants-and-children)
* [King County WA WIC (~$150/month for a family of two)](https://kingcounty.gov/en/dept/dph/health-safety/health-centers-programs-services/maternity-support-wic/wic-supplemental-nutrition-program)

## Implementation Coverage

* Evaluable criteria: 4
* Data gaps: 2

4 of 6 criteria can be evaluated with current screener fields. The core requirements -- categorical status (pregnant/postpartum/infant/child under 5), income at or below 185% FPL, adjunctive eligibility via SNAP/Medicaid/TANF, Washington residency -- are all well-covered. The 2 data gaps are low/medium impact: nutritional risk assessment is procedural; postpartum window can be approximated from infant age.

**Critical implementation note**: The income check must be bypassed entirely when adjunctive eligibility (SNAP, Medicaid, or TANF) is present. Applying the income test to adjunctive-eligible households would incorrectly exclude them.

## Research Sources

* [WA DOH WIC Eligibility and Income Limits](https://doh.wa.gov/you-and-your-family/wic/wic-eligibility)
* [USDA WIC Regulations -- 7 CFR Part 246](https://www.ecfr.gov/current/title-7/subtitle-B/chapter-II/subchapter-A/part-246)
* [Cornell LII -- 7 CFR 246.2 (Definitions: "child," "infant," "postpartum woman")](https://www.law.cornell.edu/cfr/text/7/246.2)
* [Cornell LII -- 7 CFR 246.7 (Certification of participants)](https://www.law.cornell.edu/cfr/text/7/246.7)
* [CBPP WIC Research (FY2024 average benefit)](https://www.cbpp.org/research/food-assistance/special-supplemental-nutrition-program-for-women-infants-and-children)
* [King County WA WIC Supplemental Nutrition Program](https://kingcounty.gov/en/dept/dph/health-safety/health-centers-programs-services/maternity-support-wic/wic-supplemental-nutrition-program)
