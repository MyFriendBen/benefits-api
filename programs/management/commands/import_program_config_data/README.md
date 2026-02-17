# Import New Program Tool

This directory contains utilities for importing new program configurations into the benefits-api system using JSON configuration files.

## Directory Structure

```
programs/management/commands/
├── import_program_config.py         # Django management command
└── import_program_config_data/      # Documentation and data
    ├── README.md                    # This file
    └── data/                        # JSON configuration files
        ├── il_csfp_initial_config.json
        └── ... (other program configs)
```

## Overview

The `import_program_config` Django management command allows you to create new programs with all associated entities (categories, warning messages, documents, and navigators) from a single JSON configuration file. This tool:

- Creates programs with automatic translation to all supported languages
- Supports both creating new entities and referencing existing ones
- Validates required fields and provides helpful error messages
- Runs all operations in a database transaction (rollback on error)
- Includes a dry-run mode to preview changes before applying them

## Usage

### Basic Command

```bash
python manage.py import_program_config programs/management/commands/import_program_config_data/data/<config_file>.json
```

### Dry Run Mode

Preview what will be created without making any changes:

```bash
python manage.py import_program_config programs/management/commands/import_program_config_data/data/<config_file>.json --dry-run
```

### Example

```bash
# Preview the IL CSFP program import
python manage.py import_program_config programs/management/commands/import_program_config_data/data/il_csfp_initial_config.json --dry-run

# Actually import the program
python manage.py import_program_config programs/management/commands/import_program_config_data/data/il_csfp_initial_config.json
```

## JSON Configuration Format

### Required Top-Level Fields

```json
{
  "white_label": {
    "code": "REQUIRED - white label code (e.g., 'il', 'co')"
  },
  "program_category": {
    "external_name": "REQUIRED - category identifier"
  },
  "program": {
    "name_abbreviated": "REQUIRED - program abbreviated name"
  }
}
```

### Complete Configuration Structure

```json
{
  "white_label": {
    "code": "il"
  },

  "program_category": {
    "external_name": "il_food_nutrition",
    "name": "Food & Nutrition",  // Required for new categories
    "icon": "food",              // Required for new categories
    "description": "...",        // Optional
    "tax_category": false        // Optional, defaults to false
  },

  "program": {
    "name_abbreviated": "il_csfp",
    "year": "2025",
    "legal_status_required": ["citizen", "refugee", "gc_5plus"],
    "name": "Program Name",
    "description": "Program description...",
    "learn_more_link": "https://example.gov/program-info",  // Informational page about the program
    "apply_button_link": "https://example.gov/apply",       // Direct application form
    "apply_button_description": "Learn More",
    "estimated_application_time": "10 minutes",
    "website_description": "Short description",
    "external_name": "il_csfp",
    "active": true,
    "low_confidence": false,
    "show_on_current_benefits": true,
    "value_format": "percent"
  },

  "warning_message": {
    "external_name": "il_csfp_warning",
    "calculator": "_show",       // Defaults to "_show"
    "message": "Warning text..."
  },

  "documents": [
    {
      "external_name": "id_proof",
      "text": "Document description",
      "link_url": "https://...",   // Optional
      "link_text": "Learn more"   // Optional
    }
  ],

  "navigators": [
    {
      "external_name": "greater_chicago_food_depository",
      "name": "Greater Chicago Food Depository",
      "email": "contact@example.org",
      "description": "Navigator description...",
      "assistance_link": "https://...",
      "phone_number": "773-247-3663",    // Optional
      "counties": ["Cook", "DuPage"],    // Optional
      "languages": ["en", "es"]          // Optional
    }
  ]
}
```

## Field Details

### Program Category

**For existing categories**: Only `external_name` is required.

**For new categories**: Must include:
- `external_name` - Unique identifier
- `name` - Display name (translatable)
- `icon` - Icon identifier

Optional:
- `description` - Category description (translatable)
- `tax_category` - Boolean, defaults to false

### Program

**Required**:
- `name_abbreviated` - Short unique identifier for the program

**IMPORTANT - Calculator Naming Convention**:
The `name_abbreviated` field **must match** the calculator key defined in `programs/programs/{white_label_code}/__init__.py`.

For example, if your white label is `il` and you're creating a CSFP program:
- The calculator dictionary in `programs/programs/il/__init__.py` has: `"il_csfp": IlCommoditySupplementalFoodProgram`
- Your program's `name_abbreviated` must be: `"il_csfp"`

This linkage is critical for the eligibility calculator to work. The system looks up calculators using the pattern:
```python
calculators[program.name_abbreviated]  # Must find the calculator class
```

Naming pattern: `{white_label_code}_{program_short_name}`
- Illinois CSFP: `il_csfp`
- Texas SNAP: `tx_snap`
- Colorado Medicaid: `co_medicaid`

**Translatable fields** (auto-translated to all languages):
- `name` - Full program name
- `description` - Detailed description
- `apply_button_description` - Text for apply button
- `website_description` - Short description for website
- All other text fields

**URL fields** (translatable but NOT auto-translated):
- `learn_more_link` - Informational page URL
- `apply_button_link` - Application page URL

**Configuration fields**:
- `year` - FPL year (e.g., "2025")
- `legal_status_required` - Array of legal status codes
- `external_name` - External identifier (can be same as name_abbreviated)
- `active` - Boolean
- `low_confidence` - Boolean
- `show_on_current_benefits` - Boolean
- `value_format` - Format for benefit values

### Warning Message (Optional)

- `external_name` - REQUIRED
- `calculator` - Defaults to "_show"
- `message` - Warning text (translatable)

### Documents (Optional Array)

**For existing documents**: Only `external_name` is required.

**For new documents**: Must include:
- `external_name` - Unique identifier
- `text` - Document description (translatable)

Optional:
- `link_url` - URL for more information
- `link_text` - Link text (translatable)

### Navigators (Optional Array)

**For existing navigators**: Only `external_name` is required.

**For new navigators**: Must include:
- `external_name` - Unique identifier
- `name` - Navigator name (translatable)
- `email` - Contact email (translatable)
- `description` - Description text (translatable)
- `assistance_link` - URL for assistance (not auto-translated)

Optional:
- `phone_number` - Contact phone number
- `counties` - Array of county names
- `languages` - Array of language codes

## Behavior Notes

### Translations

- All translatable fields are automatically translated to all supported languages
- English text is provided in the JSON config
- Machine translation is applied except for fields marked as `no_auto` (like URLs)
- Manual translations can be updated later through the admin interface

### Existing Entities

- If a program with the same `name_abbreviated` and white label exists, the import is skipped
- Documents, navigators, and categories can be referenced by `external_name` without recreating them
- Warning messages are shared across programs with the same calculator

### Validation

- All required fields are validated before any database changes
- Helpful error messages indicate missing or invalid fields
- The entire import runs in a transaction (all or nothing)

### Dry Run

- Use `--dry-run` flag to see what will be created
- No database changes are made
- Shows all entities that would be created or referenced
- Useful for validating JSON config before actual import

## Workflow: Creating a New Program

### Step 1: Create the Calculator (if needed)

Before importing a program, you need to create the eligibility calculator:

1. **Create calculator directory**: `programs/programs/{white_label}/program_name/`
2. **Create calculator.py**: Implement your eligibility logic
3. **Register in __init__.py**: Add to `{white_label}_calculators` dict

Example for IL CSFP:
```python
# programs/programs/il/__init__.py
il_calculators: dict[str, type[ProgramCalculator]] = {
    "il_csfp": IlCommoditySupplementalFoodProgram,  # Key must match name_abbreviated
    # ... other calculators
}
```

### Step 2: Create the JSON Config File

1. Copy an existing config file from `data/` as a template
2. Update all required fields:
   - **Critical**: `name_abbreviated` must match your calculator key
   - Update all translatable text (name, description, etc.)
   - Set year, legal statuses, and other config
   - Add documents and navigators as needed

### Step 3: Validate and Import

1. Run with `--dry-run` to validate:
   ```bash
   python manage.py import_program_config programs/management/commands/import_new_program/data/your_config.json --dry-run
   ```
2. Review the output carefully - check all fields
3. Run without `--dry-run` to actually import:
   ```bash
   python manage.py import_program_config programs/management/commands/import_new_program/data/your_config.json
   ```

### Important Notes

- **Calculator First**: Always create the calculator code before importing the program
- **Name Matching**: The `name_abbreviated` in your JSON must exactly match the calculator key
- **One-Time Import**: This tool only creates new programs. Updates require manual database changes or new migrations
- **Category Benefits**: If your program should appear in the "Additional Resources" step, you must also configure it in `configuration/white_labels/{state_code}.py` - see details below

## Critical Integration: Category Benefits

When creating a new program, you may need to update the white label configuration to enable the "I already have this" checkbox functionality in the "Additional Resources" step.

### The Naming Convention Chain

The benefit key in `category_benefits` creates a critical chain that must be consistent:

1. **Config Key**: In `configuration/white_labels/{code}.py`
   ```python
   category_benefits = {
       "food": {
           "benefits": {
               "snap": {  # ← This key is critical!
                   "name": {"_label": "", "_default_message": "SNAP"},
                   "description": {"_label": "", "_default_message": "..."}
               }
           }
       }
   }
   ```

2. **Database Field**: In `screener/models.py`, Screen model must have:
   ```python
   has_snap = models.BooleanField(default=False)
   ```

3. **Frontend Field**: In `benefits-calculator/src/Assets/updateScreen.ts`:
   ```typescript
   has_snap: formData.benefits.snap
   ```

4. **Backend Mapping**: In `screener/models.py`, `has_benefit()` method:
   ```python
   name_map = {
       "snap": self.has_snap,
       "co_snap": self.has_snap,      # Multiple programs, same benefit!
       "tx_snap": self.has_snap,       # All map to same has_* field
       "federal_snap": self.has_snap,
   }
   ```

### Multiple Programs, Same Benefit

Multiple programs can check the same benefit field. For example:
- Regular screener: `name_abbreviated = "snap"`
- State variant: `name_abbreviated = "co_snap"`
- Calculator variant: `name_abbreviated = "co_energy_calculator_snap"`

**All must map to the SAME `has_*` field** in the `has_benefit()` name_map!

### Adding a New Program with Benefit Checkbox

If your program needs an "I already have this" checkbox:

1. **Add to white label config** (`configuration/white_labels/{code}.py`):
   ```python
   category_benefits = {
       "food": {
           "benefits": {
               "my_program": {  # ← Use a consistent key
                   "name": {"_label": "", "_default_message": "My Program Name"},
                   "description": {"_label": "", "_default_message": "Description"}
               }
           }
       }
   }
   ```

2. **Add database field** to Screen model (requires migration)
3. **Add frontend mapping** in `updateScreen.ts`
4. **Add backend mapping** for ALL variant names of your program

For complete details, see: `configuration/white_labels/_template.py` (lines 243-303)

## Troubleshooting

### "Program already exists"
The program has already been imported. This command only creates new programs.

### "Missing required field"
Check the error message for the specific field and add it to your JSON config.

### "WhiteLabel not found"
Ensure the white label code exists in the database.

### "Year not found"
The FPL year must exist in the FederalPoveryLimit table.

### "Legal status not found"
Verify all legal status codes in the LegalStatus table.

## Examples

See the `data/` directory for complete working examples:
- `il_csfp_initial_config.json` - Illinois CSFP program with navigators

## Development

To add support for new entity types:
1. Add the entity to the JSON schema documentation
2. Create an `_import_<entity>` method following the existing pattern
3. Add translation support if needed using `_bulk_update_entity_translations`
4. Update the dry-run report in `_print_dry_run_report`
5. Add the import call in the `handle` method
