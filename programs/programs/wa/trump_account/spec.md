# Washington: 530A ("Trump") Accounts

- **Program**: 530A ("Trump") Accounts
- **Scope**: Washington white label (`wa`)
- **Backend**: Same federal calculator as other states — `programs/programs/federal/trump_account/calculator.py` (`TrumpAccount`), keyed by `name_abbreviated` **`trump_account`**.
- **Program row**: `Program.external_name` **`wa_trump_account`** (unique in DB); import config `wa_trump_account_initial_config.json`.
- **Research / criteria**: See `programs/programs/federal/trump_account/spec.md` for the full eligibility matrix, sources, and the nine baseline test scenarios.

## WA-specific notes

| Topic | Detail |
|-------|--------|
| Import path | `programs/management/commands/import_program_config_data/data/wa_trump_account_initial_config.json` |
| Validations | `validations/management/commands/import_validations/data/wa_trump_account.json` (households use `white_label: "wa"`; geography examples use King / Spokane counties) |
| White label UI keys | `configuration/white_labels/wa.py` — `cash.benefits.trump_account` (same canonical key as TX; shared translation labels) |
| Has-benefits step | `show_in_has_benefits_step`: **false** in seed — omit from “already have this benefit” list per product; `has_benefit("trump_account")` still works if the FE sends the canonical field |

## Test scenarios (9)

Aligned with federal `spec.md` § Test Scenarios: newborn in pilot window, outside pilot window, age 18+, adult-only household, high income (no limit), two pilot-eligible children, mixed pilot/non-pilot children, pregnant-only path, pregnant + existing child.
