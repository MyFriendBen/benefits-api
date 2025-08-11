{{
  config(
    materialized='view'
  )
}}

SELECT
    id,
    uuid,
    completed,
    submission_date,
    start_date,
    is_test,
    is_test_data,
    -- Add date parts for easier aggregation
    DATE(submission_date) as submission_date_only,
    EXTRACT(YEAR FROM submission_date) as submission_year,
    EXTRACT(MONTH FROM submission_date) as submission_month,
    EXTRACT(DAY FROM submission_date) as submission_day,
    EXTRACT(DOW FROM submission_date) as submission_day_of_week
FROM {{ source('django_apps', 'screener_screen') }}
WHERE 
    -- Only include completed screeners
    completed = true
    -- Filter out test data (check both is_test and is_test_data)
    AND (is_test = false OR is_test IS NULL)
    AND (is_test_data = false OR is_test_data IS NULL)
    -- Only include records with submission dates
    AND submission_date IS NOT NULL 