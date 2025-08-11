{{
  config(
    materialized='table',
    description='Mart model answering: What percentage of completed screeners qualified for benefits?'
  )
}}

WITH overall_summary AS (
    SELECT
        COUNT(*) as total_completed_screeners,
        SUM(CASE WHEN qualified_for_any_benefits = true THEN 1 ELSE 0 END) as qualified_screeners,
        SUM(CASE WHEN qualified_for_any_benefits = false THEN 1 ELSE 0 END) as not_qualified_screeners,
        AVG(qualification_rate_percent) as avg_qualification_rate_percent,
        SUM(total_estimated_value) as total_benefit_value,
        AVG(total_estimated_value) as avg_benefit_value_per_qualified_screener
    FROM {{ ref('int_screener_benefit_summary') }}
),

white_label_summary AS (
    SELECT
        white_label_id,
        COUNT(*) as total_screeners,
        SUM(CASE WHEN qualified_for_any_benefits = true THEN 1 ELSE 0 END) as qualified_screeners,
        SUM(CASE WHEN qualified_for_any_benefits = false THEN 1 ELSE 0 END) as not_qualified_screeners,
        SUM(total_estimated_value) as total_benefit_value,
        AVG(total_estimated_value) as avg_benefit_value_per_qualified_screener,
        AVG(qualification_rate_percent) as avg_qualification_rate_percent
    FROM {{ ref('int_screener_benefit_summary') }}
    WHERE white_label_id IS NOT NULL
    GROUP BY white_label_id
),

time_period_summary AS (
    SELECT
        submission_year,
        submission_month,
        DATE_TRUNC('month', submission_date_only) as month_start,
        COUNT(*) as total_screeners,
        SUM(CASE WHEN qualified_for_any_benefits = true THEN 1 ELSE 0 END) as qualified_screeners,
        SUM(CASE WHEN qualified_for_any_benefits = false THEN 1 ELSE 0 END) as not_qualified_screeners,
        SUM(total_estimated_value) as total_benefit_value,
        AVG(total_estimated_value) as avg_benefit_value_per_qualified_screener
    FROM {{ ref('int_screener_benefit_summary') }}
    GROUP BY submission_year, submission_month, DATE_TRUNC('month', submission_date_only)
),

demographic_summary AS (
    SELECT
        CASE 
            WHEN household_size <= 2 THEN '1-2 people'
            WHEN household_size <= 4 THEN '3-4 people'
            WHEN household_size <= 6 THEN '5-6 people'
            ELSE '7+ people'
        END as household_size_group,
        CASE 
            WHEN household_assets IS NULL THEN 'Unknown'
            WHEN household_assets <= 1000 THEN 'Low ($0-$1K)'
            WHEN household_assets <= 5000 THEN 'Medium ($1K-$5K)'
            WHEN household_assets <= 10000 THEN 'High ($5K-$10K)'
            ELSE 'Very High ($10K+)'
        END as asset_group,
        housing_situation,
        COUNT(*) as total_screeners,
        SUM(CASE WHEN qualified_for_any_benefits = true THEN 1 ELSE 0 END) as qualified_screeners,
        SUM(CASE WHEN qualified_for_any_benefits = false THEN 1 ELSE 0 END) as not_qualified_screeners,
        SUM(total_estimated_value) as total_benefit_value,
        AVG(total_estimated_value) as avg_benefit_value_per_qualified_screener
    FROM {{ ref('int_screener_benefit_summary') }}
    GROUP BY 
        CASE 
            WHEN household_size <= 2 THEN '1-2 people'
            WHEN household_size <= 4 THEN '3-4 people'
            WHEN household_size <= 6 THEN '5-6 people'
            ELSE '7+ people'
        END,
        CASE 
            WHEN household_assets IS NULL THEN 'Unknown'
            WHEN household_assets <= 1000 THEN 'Low ($0-$1K)'
            WHEN household_assets <= 5000 THEN 'Medium ($1K-$5K)'
            WHEN household_assets <= 10000 THEN 'High ($5K-$10K)'
            ELSE 'Very High ($10K+)'
        END,
        housing_situation
),

combined_results AS (
    -- Overall metrics (answer to the main question)
    SELECT
        'Overall' as breakdown_type,
        'All Screeners' as breakdown_value,
        os.total_completed_screeners,
        os.qualified_screeners,
        os.not_qualified_screeners,
        CASE 
            WHEN os.total_completed_screeners > 0 
            THEN ROUND((os.qualified_screeners::decimal / os.total_completed_screeners) * 100, 2)
            ELSE 0
        END as qualification_rate_percent,
        os.total_benefit_value,
        os.avg_benefit_value_per_qualified_screener,
        os.avg_qualification_rate_percent,
        CURRENT_TIMESTAMP as calculated_at
    FROM overall_summary os

    UNION ALL

    -- White label breakdown
    SELECT
        'White Label' as breakdown_type,
        COALESCE(wl.name, 'Unknown') as breakdown_value,
        wls.total_screeners,
        wls.qualified_screeners,
        wls.not_qualified_screeners,
        CASE 
            WHEN wls.total_screeners > 0 
            THEN ROUND((wls.qualified_screeners::decimal / wls.total_screeners) * 100, 2)
            ELSE 0
        END as qualification_rate_percent,
        wls.total_benefit_value,
        wls.avg_benefit_value_per_qualified_screener,
        wls.avg_qualification_rate_percent,
        CURRENT_TIMESTAMP as calculated_at
    FROM white_label_summary wls
    LEFT JOIN {{ source('django_apps', 'screener_whitelabel') }} wl ON wls.white_label_id = wl.id

    UNION ALL

    -- Time period breakdown
    SELECT
        'Time Period' as breakdown_type,
        TO_CHAR(tps.month_start, 'YYYY-MM') as breakdown_value,
        tps.total_screeners,
        tps.qualified_screeners,
        tps.not_qualified_screeners,
        CASE 
            WHEN tps.total_screeners > 0 
            THEN ROUND((tps.qualified_screeners::decimal / tps.total_screeners) * 100, 2)
            ELSE 0
        END as qualification_rate_percent,
        tps.total_benefit_value,
        tps.avg_benefit_value_per_qualified_screener,
        NULL as avg_qualification_rate_percent,
        CURRENT_TIMESTAMP as calculated_at
    FROM time_period_summary tps

    UNION ALL

    -- Demographic breakdown
    SELECT
        'Demographics' as breakdown_type,
        CONCAT(ds.household_size_group, ' | ', ds.asset_group) as breakdown_value,
        ds.total_screeners,
        ds.qualified_screeners,
        ds.not_qualified_screeners,
        CASE 
            WHEN ds.total_screeners > 0 
            THEN ROUND((ds.qualified_screeners::decimal / ds.total_screeners) * 100, 2)
            ELSE 0
        END as qualification_rate_percent,
        ds.total_benefit_value,
        ds.avg_benefit_value_per_qualified_screener,
        NULL as avg_qualification_rate_percent,
        CURRENT_TIMESTAMP as calculated_at
    FROM demographic_summary ds
)

SELECT * FROM combined_results
ORDER BY 
    CASE breakdown_type
        WHEN 'Overall' THEN 1
        WHEN 'White Label' THEN 2
        WHEN 'Time Period' THEN 3
        WHEN 'Demographics' THEN 4
    END,
    qualification_rate_percent DESC 