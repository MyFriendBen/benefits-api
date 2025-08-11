{{
  config(
    materialized='table',
    description='Intermediate model for white label program breakdowns'
  )
}}

SELECT
    wl.name as white_label_name,
    wl.code as white_label_code,
    wl.state_code,
    pe.name_abbreviated,
    pe.name,
    pe.value_type,
    COUNT(*) as total_checks,
    SUM(CASE WHEN pe.eligible = true THEN 1 ELSE 0 END) as qualified_count,
    AVG(CASE WHEN pe.eligible = true THEN pe.estimated_value ELSE NULL END) as avg_benefit_value,
    SUM(CASE WHEN pe.eligible = true THEN pe.estimated_value ELSE 0 END) as total_benefit_value,
    CASE 
        WHEN COUNT(*) > 0 
        THEN ROUND((SUM(CASE WHEN pe.eligible = true THEN 1 ELSE 0 END)::decimal / COUNT(*)) * 100, 2)
        ELSE 0
    END as white_label_qualification_rate_percent
FROM {{ ref('stg_program_eligibility') }} pe
LEFT JOIN {{ source('django_apps', 'screener_screen') }} s ON pe.screen_id = s.id
LEFT JOIN {{ source('django_apps', 'screener_whitelabel') }} wl ON s.white_label_id = wl.id
WHERE wl.name IS NOT NULL
GROUP BY wl.name, wl.code, wl.state_code, pe.name_abbreviated, pe.name, pe.value_type
ORDER BY wl.name, pe.name_abbreviated 