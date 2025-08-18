{{
  config(
    materialized='view'
  )
}}

-- Remove duplicates: Some records can share the same `uuid` due to pulling validations.
-- We keep a single row per `uuid`, choosing the most recent `submission_date`
-- (tie-broken by highest `id`). This guarantees unique uuids for downstream
-- models and satisfies the uniqueness tests.
WITH filtered AS (
    SELECT
        id,
        uuid,
        completed,
        submission_date,
        start_date,
        white_label_id,
        household_size,
        household_assets,
        housing_situation,
        zipcode,
        county,
        is_test,
        is_test_data
    FROM {{ source('django_apps', 'screener_screen') }}
    WHERE 
        -- Only include completed screeners
        completed = true
        -- Filter out test data (check both is_test and is_test_data)
        AND (is_test = false OR is_test IS NULL)
        AND (is_test_data = false OR is_test_data IS NULL)
        -- Only include records with submission dates
        AND submission_date IS NOT NULL
), deduped AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY uuid
            ORDER BY submission_date DESC, id DESC
        ) AS row_num
    FROM filtered
)

SELECT
    id,
    uuid,
    completed,
    submission_date,
    start_date,
    white_label_id,
    household_size,
    household_assets,
    housing_situation,
    zipcode,
    county,
    is_test,
    is_test_data,
    -- Add date parts for easier aggregation
    DATE(submission_date) as submission_date_only,
    EXTRACT(YEAR FROM submission_date) as submission_year,
    EXTRACT(MONTH FROM submission_date) as submission_month,
    EXTRACT(DAY FROM submission_date) as submission_day,
    EXTRACT(DOW FROM submission_date) as submission_day_of_week
FROM deduped
WHERE row_num = 1