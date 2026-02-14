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
- **functions** (optional): Calculator names; each must be registered in `programs.programs.urgent_needs.urgent_need_functions`. If you don’t need custom logic, omit this array.
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
