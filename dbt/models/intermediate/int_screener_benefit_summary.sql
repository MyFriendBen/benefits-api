{{
  config(
    materialized='table',
    description='Intermediate model summarizing benefit qualification for each completed screener'
  )
}}

WITH screener_eligibility AS (
    SELECT
        screen_id,
        COUNT(*) as total_programs_checked,
        SUM(CASE WHEN eligible = true THEN 1 ELSE 0 END) as programs_qualified_for,
        SUM(CASE WHEN eligible = true THEN estimated_value ELSE 0 END) as total_estimated_value,
        MAX(eligibility_date) as last_eligibility_check,
        -- Get unique program types qualified for
        COUNT(DISTINCT CASE WHEN eligible = true THEN name_abbreviated END) as unique_program_types_qualified
    FROM {{ ref('stg_program_eligibility') }}
    GROUP BY screen_id
),

screener_base AS (
    SELECT
        s.id as screen_id,
        s.uuid,
        s.completed,
        s.submission_date,
        s.start_date,
        s.white_label_id,
        s.household_size,
        s.household_assets,
        s.housing_situation,
        s.zipcode,
        s.county,
        s.is_test,
        s.is_test_data,
        -- Add date parts
        s.submission_date_only,
        s.submission_year,
        s.submission_month
    FROM {{ ref('stg_screener_screen') }} s
)

SELECT
    sb.screen_id,
    sb.uuid,
    sb.submission_date,
    sb.submission_date_only,
    sb.submission_year,
    sb.submission_month,
    sb.white_label_id,
    sb.household_size,
    sb.household_assets,
    sb.housing_situation,
    sb.zipcode,
    sb.county,
    -- Eligibility summary
    COALESCE(se.total_programs_checked, 0) as total_programs_checked,
    COALESCE(se.programs_qualified_for, 0) as programs_qualified_for,
    COALESCE(se.total_estimated_value, 0) as total_estimated_value,
    COALESCE(se.unique_program_types_qualified, 0) as unique_program_types_qualified,
    se.last_eligibility_check,
    -- Key business metrics
    CASE 
        WHEN se.programs_qualified_for > 0 THEN true 
        ELSE false 
    END as qualified_for_any_benefits,
    CASE 
        WHEN se.programs_qualified_for > 0 THEN 'Yes'
        ELSE 'No'
    END as qualified_for_any_benefits_label,
    -- Qualification rate for this screener
    CASE 
        WHEN se.total_programs_checked > 0 
        THEN ROUND((se.programs_qualified_for::decimal / se.total_programs_checked) * 100, 2)
        ELSE 0
    END as qualification_rate_percent
FROM screener_base sb
LEFT JOIN screener_eligibility se ON sb.screen_id = se.screen_id
ORDER BY sb.submission_date DESC 