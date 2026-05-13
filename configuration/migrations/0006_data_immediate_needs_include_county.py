# Rebuild data_immediate_needs so each row carries screener_screen.county (nullable).
# When Metabase (or other BI) joins this mart to a county dimension, INNER JOIN
# previously dropped all screens with NULL county. Grouping/counting at the
# (white_label, partner, county) grain keeps NULL county as its own bucket.

from django.db import migrations


CREATE_DATA_IMMEDIATE_NEEDS_WITH_COUNTY = """
CREATE MATERIALIZED VIEW data_immediate_needs AS
 WITH base AS (
         SELECT data.white_label_id,
            data.partner,
            data.county,
            sum(
                CASE
                    WHEN (data.needs_baby_supplies = true) THEN 1
                    ELSE 0
                END) AS needs_baby_supplies,
            sum(
                CASE
                    WHEN (data.needs_child_dev_help = true) THEN 1
                    ELSE 0
                END) AS needs_child_dev_help,
            sum(
                CASE
                    WHEN (data.needs_food = true) THEN 1
                    ELSE 0
                END) AS needs_food,
            sum(
                CASE
                    WHEN (data.needs_funeral_help = true) THEN 1
                    ELSE 0
                END) AS needs_funeral_help,
            sum(
                CASE
                    WHEN (data.needs_housing_help = true) THEN 1
                    ELSE 0
                END) AS needs_housing_help,
            sum(
                CASE
                    WHEN (data.needs_mental_health_help = true) THEN 1
                    ELSE 0
                END) AS needs_mental_health_help,
            sum(
                CASE
                    WHEN (data.needs_family_planning_help = true) THEN 1
                    ELSE 0
                END) AS needs_family_planning_help,
            sum(
                CASE
                    WHEN (data.needs_dental_care = true) THEN 1
                    ELSE 0
                END) AS needs_dental_care,
            sum(
                CASE
                    WHEN (data.needs_job_resources = true) THEN 1
                    ELSE 0
                END) AS needs_job_resources,
            sum(
                CASE
                    WHEN (data.needs_legal_services = true) THEN 1
                    ELSE 0
                END) AS needs_legal_services,
            sum(
                CASE
                    WHEN (data.needs_college_savings = true) THEN 1
                    ELSE 0
                END) AS needs_college_savings,
            sum(
                CASE
                    WHEN (data.needs_veteran_services = true) THEN 1
                    ELSE 0
                END) AS needs_veteran_services
           FROM data
          GROUP BY data.white_label_id, data.partner, data.county
        )
 SELECT base.white_label_id,
    base.partner,
    base.county,
    unnest(ARRAY['Baby Supplies'::text, 'Child Development'::text, 'Food'::text, 'Funeral'::text, 'Housing'::text, 'Mental Health'::text, 'Family Planning'::text, 'Dental Care'::text, 'Job Resources'::text, 'Legal Services'::text, 'College Savings'::text, 'Veteran Services'::text]) AS benefit,
    unnest(ARRAY[base.needs_baby_supplies, base.needs_child_dev_help, base.needs_food, base.needs_funeral_help, base.needs_housing_help, base.needs_mental_health_help, base.needs_family_planning_help, base.needs_dental_care, base.needs_job_resources, base.needs_legal_services, base.needs_college_savings, base.needs_veteran_services]) AS count
   FROM base;
"""

# Previous production definition (pg_matviews, pre-0006): aggregate with no county column.
CREATE_DATA_IMMEDIATE_NEEDS_LEGACY = """
CREATE MATERIALIZED VIEW data_immediate_needs AS
 WITH base AS (
         SELECT data.white_label_id,
            data.partner,
            sum(
                CASE
                    WHEN (data.needs_baby_supplies = true) THEN 1
                    ELSE 0
                END) AS needs_baby_supplies,
            sum(
                CASE
                    WHEN (data.needs_child_dev_help = true) THEN 1
                    ELSE 0
                END) AS needs_child_dev_help,
            sum(
                CASE
                    WHEN (data.needs_food = true) THEN 1
                    ELSE 0
                END) AS needs_food,
            sum(
                CASE
                    WHEN (data.needs_funeral_help = true) THEN 1
                    ELSE 0
                END) AS needs_funeral_help,
            sum(
                CASE
                    WHEN (data.needs_housing_help = true) THEN 1
                    ELSE 0
                END) AS needs_housing_help,
            sum(
                CASE
                    WHEN (data.needs_mental_health_help = true) THEN 1
                    ELSE 0
                END) AS needs_mental_health_help,
            sum(
                CASE
                    WHEN (data.needs_family_planning_help = true) THEN 1
                    ELSE 0
                END) AS needs_family_planning_help,
            sum(
                CASE
                    WHEN (data.needs_dental_care = true) THEN 1
                    ELSE 0
                END) AS needs_dental_care,
            sum(
                CASE
                    WHEN (data.needs_job_resources = true) THEN 1
                    ELSE 0
                END) AS needs_job_resources,
            sum(
                CASE
                    WHEN (data.needs_legal_services = true) THEN 1
                    ELSE 0
                END) AS needs_legal_services,
            sum(
                CASE
                    WHEN (data.needs_college_savings = true) THEN 1
                    ELSE 0
                END) AS needs_college_savings,
            sum(
                CASE
                    WHEN (data.needs_veteran_services = true) THEN 1
                    ELSE 0
                END) AS needs_veteran_services
           FROM data
          GROUP BY data.white_label_id, data.partner
        )
 SELECT base.white_label_id,
    base.partner,
    unnest(ARRAY['Baby Supplies'::text, 'Child Development'::text, 'Food'::text, 'Funeral'::text, 'Housing'::text, 'Mental Health'::text, 'Family Planning'::text, 'Dental Care'::text, 'Job Resources'::text, 'Legal Services'::text, 'College Savings'::text, 'Veteran Services'::text]) AS benefit,
    unnest(ARRAY[base.needs_baby_supplies, base.needs_child_dev_help, base.needs_food, base.needs_funeral_help, base.needs_housing_help, base.needs_mental_health_help, base.needs_family_planning_help, base.needs_dental_care, base.needs_job_resources, base.needs_legal_services, base.needs_college_savings, base.needs_veteran_services]) AS count
   FROM base;
"""


def _has_data_matview(schema_editor) -> bool:
    if schema_editor.connection.vendor != "postgresql":
        return False
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM pg_matviews WHERE matviewname = %s",
            ["data"],
        )
        return cursor.fetchone() is not None


def forwards_rebuild_immediate_needs(apps, schema_editor):
    if not _has_data_matview(schema_editor):
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("DROP MATERIALIZED VIEW IF EXISTS data_immediate_needs")
        cursor.execute(CREATE_DATA_IMMEDIATE_NEEDS_WITH_COUNTY)


def backwards_restore_legacy_immediate_needs(apps, schema_editor):
    if not _has_data_matview(schema_editor):
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("DROP MATERIALIZED VIEW IF EXISTS data_immediate_needs")
        cursor.execute(CREATE_DATA_IMMEDIATE_NEEDS_LEGACY)


class Migration(migrations.Migration):
    """
    Rebuilds analytics matview data_immediate_needs so county is part of its grain.

    If the database has no `data` matview (some empty dev/staging DBs), forwards
    becomes a no-op but Django still records this migration. Before relying on
    analytics on that database, create the standard matviews first, then reverse
    configuration.0006 and re-apply it (or run the CREATE SQL from forwards manually).
    """

    dependencies = [
        ("configuration", "0005_alter_configuration_white_label"),
    ]

    operations = [
        migrations.RunPython(forwards_rebuild_immediate_needs, backwards_restore_legacy_immediate_needs),
    ]
