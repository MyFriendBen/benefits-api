{{
  config(
    materialized='table',
    description='Intermediate model summarizing benefit qualification by program type (overall metrics only)'
  )
}}

SELECT
    name_abbreviated,
    name,
    value_type,
    COUNT(*) as total_checks,
    SUM(CASE WHEN eligible = true THEN 1 ELSE 0 END) as qualified_count,
    SUM(CASE WHEN eligible = false THEN 1 ELSE 0 END) as not_qualified_count,
    AVG(CASE WHEN eligible = true THEN estimated_value ELSE NULL END) as avg_benefit_value,
    SUM(CASE WHEN eligible = true THEN estimated_value ELSE 0 END) as total_benefit_value,
    MIN(estimated_delivery_time) as min_delivery_time,
    MAX(estimated_delivery_time) as max_delivery_time,
    MIN(estimated_application_time) as min_application_time,
    MAX(estimated_application_time) as max_application_time,
    -- Key metrics
    CASE 
        WHEN COUNT(*) > 0 
        THEN ROUND((SUM(CASE WHEN eligible = true THEN 1 ELSE 0 END)::decimal / COUNT(*)) * 100, 2)
        ELSE 0
    END as qualification_rate_percent,
    CASE 
        WHEN SUM(CASE WHEN eligible = true THEN 1 ELSE 0 END) > 0 
        THEN ROUND((SUM(CASE WHEN eligible = false THEN 1 ELSE 0 END)::decimal / SUM(CASE WHEN eligible = true THEN 1 ELSE 0 END)) * 100, 2)
        ELSE 0
    END as rejection_rate_percent
FROM {{ ref('stg_program_eligibility') }}
GROUP BY name_abbreviated, name, value_type
ORDER BY 
    CASE 
        WHEN COUNT(*) > 0 
        THEN ROUND((SUM(CASE WHEN eligible = true THEN 1 ELSE 0 END)::decimal / COUNT(*)) * 100, 2)
        ELSE 0
    END DESC, 
    COUNT(*) DESC 