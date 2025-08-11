{{
  config(
    materialized='view',
    description='Staging model for program eligibility data, cleaned and standardized'
  )
}}

SELECT
    pes.id,
    pes.eligibility_snapshot_id,
    es.screen_id,
    es.submission_date,
    es.is_batch,
    es.had_error,
    pes.new,
    pes.name,
    pes.name_abbreviated,
    pes.value_type,
    pes.estimated_value,
    pes.estimated_delivery_time,
    pes.estimated_application_time,
    pes.eligible,
    pes.failed_tests,
    pes.passed_tests,
    -- Add date parts for easier aggregation
    DATE(es.submission_date) as eligibility_date,
    EXTRACT(YEAR FROM es.submission_date) as eligibility_year,
    EXTRACT(MONTH FROM es.submission_date) as eligibility_month,
    EXTRACT(DAY FROM es.submission_date) as eligibility_day
FROM {{ source('django_apps', 'screener_programeligibilitysnapshot') }} pes
LEFT JOIN {{ source('django_apps', 'screener_eligibilitysnapshot') }} es 
    ON pes.eligibility_snapshot_id = es.id
WHERE
    -- Only include successful eligibility calculations
    es.had_error = false
    -- Only include completed screens
    AND es.screen_id IS NOT NULL
    -- Only include actual eligibility results
    AND pes.eligible IS NOT NULL 