# Update Validations Command

Updates existing Validation records in the database from a JSON file. Useful for batch corrections to eligibility, values, or notes.

## Usage

```bash
# Preview changes without modifying the database
python manage.py update_validations path/to/updates.json --dry-run

# Apply updates
python manage.py update_validations path/to/updates.json
```

## JSON Format

```json
{
  "description": "Human-readable description of these updates",
  "updates": [
    {
      "screen_uuid": "12345678-1234-1234-1234-123456789abc",
      "program_name": "snap",
      "eligible": false,
      "value": 0,
      "notes": "Optional notes about this validation",
      "reason": "Optional explanation for why this update is needed"
    }
  ]
}
```

### Required Fields

- `description` - Description of the update batch
- `updates` - Array of validation updates, each requiring:
  - `screen_uuid` - UUID of the screen
  - `program_name` - Program's `name_abbreviated` (e.g., "snap", "tx_aca")
  - At least one of: `eligible`, `value`, or `notes`

### Optional Fields (per update)

- `eligible` - Boolean eligibility status
- `value` - Numeric benefit value
- `notes` - Human-readable notes
- `reason` - Documentation field explaining why the update is being made (not stored in database, for audit/reference purposes only)

See [update_validation_example.json](update_validation_example.json) for a complete example.

## Behavior

- Validates JSON against [update_validation_schema.json](update_validation_schema.json) before processing
- Verifies all referenced screens and validations exist
- Runs all updates in a single database transaction (all succeed or all fail)
- Reports changes made for each validation
