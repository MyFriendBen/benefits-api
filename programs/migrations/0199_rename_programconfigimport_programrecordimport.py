from django.db import migrations


class Migration(migrations.Migration):
    """
    Program-ops program records are the only program import, so the tracking model is named for
    them. Its own migration rather than part of 0198, so a database that already applied 0198
    still gets the rename.
    """

    dependencies = [
        ("programs", "0198_program_estimated_decision_time_and_applied_record"),
    ]

    operations = [
        migrations.RenameModel(old_name="ProgramConfigImport", new_name="ProgramRecordImport"),
    ]
