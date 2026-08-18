# Import Urgent Need Tool

Utilities for importing **urgent need** configurations (Additional Needs step) into benefits-api via a single JSON file. Mirrors the program import tooling but targets the `UrgentNeed` model.

## Directory Structure

```
programs/management/commands/
├── import_urgent_need_config.py          # Django management command
└── import_urgent_need_config_data/       # Documentation and sample data
    ├── README.md                         # This file
    └── data/
        └── tx_diaper_bank.json           # Example urgent need config
```

## Overview

The `import_urgent_need_config` command creates or updates urgent needs with translations and related entities. It:

- Creates/updates an `UrgentNeed` with auto-translated fields
- Creates/associates `UrgentNeedType` (category_type) with icon + translation
- Creates/associates `UrgentNeedCategory` (type_short)
- Optionally associates functions, counties, required expense types, and FPL year
- Validates required fields with clear errors
- Runs inside a database transaction (rolls back on error)
- Supports dry-run to preview changes

## Usage

```bash
python manage.py import_urgent_need_config programs/management/commands/import_urgent_need_config_data/data/<config>.json
python manage.py import_urgent_need_config programs/management/commands/import_urgent_need_config_data/data/<config>.json --dry-run
python manage.py import_urgent_need_config programs/management/commands/import_urgent_need_config_data/data/<config>.json --override
```

- `--dry-run`: Show what would be created/updated without DB writes.
- `--override`: Delete any existing `UrgentNeed` with the same `external_name` and recreate it from the provided config; relations are cleared and replaced.

## JSON Configuration Format

### Required Top-Level Fields

```json
{
  "white_label": { "code": "REQUIRED - white label code (e.g., 'tx', 'il')" },
  "need": {
    "external_name": "REQUIRED - unique urgent need key"
  }
}
```

### Complete Example (tx_diaper_bank)

```json
{
  "white_label": { "code": "tx" },
  "need": {
    "external_name": "tx_diaper_bank",
    "category_type": {
      "external_name": "diapers_and_baby_supplies",
      "name": "Diapers and baby supplies"
    },
    "type_short": ["baby supplies"],
    "translations": {
      "name": "National Diaper Bank Network",
      "description": "Use to find access to baby diapers, wipes, and other new baby needs.",
      "link": "https://nationaldiaperbanknetwork.org/member-directory/",
      "warning": "",
      "website_description": "Map to find local diaper banks in your area.",
      "notification_message": ""
    },
    "functions": [],
    "counties": [
      "Travis",
      "Dallas",
      "El Paso",
      "Tarrant",
      "Galveston",
      "Brazoria",
      "Collin",
      "Bexar",
      "McLennan"
    ],
    "required_expense_types": ["childSupport"],
    "active": true,
    "low_confidence": false,
    "show_on_current_benefits": true
  }
}
```

## Field Details

### White Label
- **white_label.code** (required): Must already exist.

### Urgent Need
- **need.external_name** (required): Unique identifier.
- **category_type.external_name** (required): Created if missing. Optional `name` (translated) and `icon`.
- **type_short** (required): One or more categories (`UrgentNeedCategory.name`).
- **translations** (required): English strings for all translatable fields; auto-translated to other languages.
  - Required keys: `name`, `description`, `link`, `warning`, `website_description`.
  - Optional key: `notification_message`.
- **functions** (optional): Calculator names; each must be registered in `programs.urgent_needs.urgent_need_functions`. If you don’t need custom logic, omit this array.
- **phone_number** (optional): E.164 preferred.
- **counties** (optional): Names; created under the same white label if missing.
- **required_expense_types** (optional): Names aligning with `ExpenseType` (created if missing).
- **fpl** (optional): `{ "year": "2024", "period": "2024" }` to create/update `FederalPoveryLimit`.
- **active / low_confidence / show_on_current_benefits**: Booleans, default to `true / false / true`.

## Workflow: Adding a New Urgent Need

1) **Create the JSON config**
   - Copy an existing file from `data/` (e.g., `tx_diaper_bank.json`).
   - Set `white_label.code` and a unique `need.external_name`.
   - Fill required translations and type_short.
   - Add optional counties/expense types/FPL/phone as needed.
   - Only add `functions` if a registered calculator exists.

2) **Validate with dry run**
```bash
python manage.py import_urgent_need_config programs/management/commands/import_urgent_need_config_data/data/your_file.json --dry-run
```

3) **Import for real**
```bash
python manage.py import_urgent_need_config programs/management/commands/import_urgent_need_config_data/data/your_file.json
```

## Behavior Notes

- Runs in a transaction; failures roll back.
- Provides clear validation errors for missing/invalid fields.
- Auto-translates translatable fields to all supported languages (English input required).
- If `--override` is used, existing relations (type_short, functions, counties, expense types) are cleared and replaced.

## Examples

- `data/tx_diaper_bank.json` – Texas diaper bank urgent need.

More examples can be added to the `data/` folder following the same schema.

## Bulk Import

`import_all_urgent_need_configs` imports every config in `data/` whose `external_name` does not
already exist as an `UrgentNeed`. There is no tracking table — existence in the database is the
signal.

```bash
python manage.py import_all_urgent_need_configs --list          # existing vs pending
python manage.py import_all_urgent_need_configs --dry-run
python manage.py import_all_urgent_need_configs
python manage.py import_all_urgent_need_configs --white-label ks
```

`--override` deletes and recreates urgent needs that already exist, discarding any edits made
through the Django admin. It must be scoped with `--white-label` or `--file`:

```bash
python manage.py import_all_urgent_need_configs --override --file ks_harvesters.json
```

## Gotchas

### `type_short` must have a matching immediate-need tile

An urgent need is only ever returned when its `type_short` matches a box the user checked on the
immediate-needs step. Valid values are the keys of `possible_needs` in `screener/views.py`
`urgent_need_results`, and each one is gated on a `Screen.needs_*` field that the frontend only
sends when the corresponding key exists in that white label's `acute_condition_options`. A
`type_short` with no tile in the target white label produces a permanently invisible record.

### County names must match `counties_by_zipcode` exactly

`UrgentNeedFunction.county_eligible` does a plain string membership test against `screen.county`,
and the naming convention differs per white label:

| White label | Format |
| --- | --- |
| `co`, `ks`, `mo`, `nc`, `wa` | `"Sedgwick County"` (MO also has the bare `"St. Louis City"`) |
| `il`, `tx` | `"DuPage"`, `"St. Clair"` |
| `ma` | municipalities, not counties |

An empty `counties` array means all counties. A near-miss like `"Sedgwick"` for `ks` silently
never matches.

### Omit `category_type.name` / `icon` when reusing an existing type

The importer overwrites both whenever the config supplies them, so pointing a new urgent need at
an `UrgentNeedType` that other urgent needs already share will relabel their section header.
Supply `external_name` only in that case.

### `required_expense_types` is an eligibility gate

`UrgentNeedFunction.expense_eligible` hides the resource unless the user reported one of the
listed expenses. Leave it empty for resources that should be shown unconditionally. Valid values
are the camelCase `ExpenseType` names (`rent`, `mortgage`, `heating`, `cooling`, `telephone`,
`internet`, `otherUtilities`, `medical`, `childCare`, `childSupport`, `dependentCare`,
`propertyTax`, `hoa`, `homeownersInsurance`) — there is no single "Utilities" value.
