# Legacy program configs — no longer imported

Program records live in [program-ops](https://github.com/MyFriendBen/program-ops), as
`programs/**/*_program_record.json`. `import_program_records` reads only those: it creates a
program the first time and keeps it matching its record after that. Run it through program-ops'
`scripts/import_programs.py`, which does a dry run first and works for local, staging and prod.

The JSON files in `data/` are what benefits-api used to seed programs from. **Nothing imports them
any more**, and they are not updated. They stay for now because:

- they hold researched text — documents and navigator descriptions — that never reached the
  database, since only the first config to create a shared row was ever applied. The shared-row
  clean-up reads it from here;
- `programs/management/commands/tests/test_five_year_bar_legal_statuses.py` and
  `programs/vintage_tests.py` still read them, until those checks move onto program-ops records.

Don't add or edit files here. A new program, or a change to one, is a program-ops record.
