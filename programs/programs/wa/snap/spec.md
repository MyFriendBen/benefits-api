# Washington State SNAP (Basic Food) Program

## Program Details

- **Program**: SNAP (Basic Food)
- **State**: WA
- **White Label**: wa
- **PolicyEngine Variable**: `snap`
- **Research Date**: 2026-04-09

## Core Eligibility Framework

Washington's Basic Food (SNAP) program uses **Broad-Based Categorical Eligibility (BBCE)**, which significantly simplifies screening compared to federal SNAP:

- **Gross income limit**: 200% of Federal Poverty Level (vs. standard 130%)
- **Net income limit**: 100% FPL (standard federal requirement)
- **Asset test**: Eliminated for most households under BBCE

## Evaluable vs. Non-Evaluable Criteria

**10 of 21 criteria can be screened** with available fields:
- Gross/net income tests
- Household size determination
- State residency (WA ZIP code validation)
- Current SNAP receipt status
- Student eligibility exemptions
- TANF/SSI categorical eligibility
- Basic non-financial requirements

**10 criteria have data gaps** (citizenship status, SSN, criminal history, ABAWD work hours, institutional residence, voluntary job quit, prior fraud disqualification)

**1 complex edge case** warrants a disclaimer rather than screening logic: households with members 60+ or disabled may qualify through an alternative net-income-only path if they fail the gross income test.

> Disclaimer: *"If you received an ineligible result and your household includes someone over 60 or with a disability, you may still qualify—consider applying."*

## Key Corrections from Original Research

1. **Pregnant women count as one household member** for SNAP purposes (not two). Pregnancy is relevant only for work requirement exemptions, not FPL threshold calculations.

2. **Updated 2026 FPL thresholds** applied to test scenarios (e.g., 200% FPL for household of 1 = $2,660/month).

3. **Net income deduction methodology** cannot be precisely replicated in a screener due to variable standard deductions, utility allowances, shelter caps, and medical expense rules.

## Benefit Structure

Maximum monthly benefits (FFY 2025):
- Household of 1: $298/month
- Household of 4: $994/month

Actual benefit = maximum minus 30% of household net income. Average benefit is approximately $188/person/month.

## Implementation Coverage

- ✅ Evaluable criteria: 10
- ⚠️ Data gaps: 10

The screener can reliably identify eligible households for straightforward cases but should surface disclaimers regarding potential alternative eligibility paths for elderly/disabled households and missing citizenship data.

## Research Sources

- [WA DSHS Basic Food Program](https://www.dshs.wa.gov/esa/community-services-offices/basic-food)
- [Washington Connection (Application)](https://www.washingtonconnection.org/home/)
- [WAC 388-408-0015 - Household membership](https://app.leg.wa.gov/wac/default.aspx?cite=388-408-0015)
- [HHS Poverty Guidelines](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines)

## Files

- Program config: `programs/management/commands/import_program_config_data/data/wa_snap_initial_config.json`
- Test cases: `validations/management/commands/import_validations/data/wa_snap.json`
