{{
  config(
    materialized='table',
    description='Mart model providing detailed breakdown of benefit qualification by program type'
  )
}}

WITH program_rankings AS (
    SELECT
        name_abbreviated,
        name,
        value_type,
        total_checks,
        qualified_count,
        not_qualified_count,
        avg_benefit_value,
        total_benefit_value,
        qualification_rate_percent,
        rejection_rate_percent,
        -- Rank programs by qualification rate
        ROW_NUMBER() OVER (ORDER BY qualification_rate_percent DESC) as rank_by_qualification_rate,
        -- Rank programs by total volume
        ROW_NUMBER() OVER (ORDER BY total_checks DESC) as rank_by_volume,
        -- Rank programs by total benefit value
        ROW_NUMBER() OVER (ORDER BY total_benefit_value DESC) as rank_by_value,
        -- Categorize programs by qualification rate
        CASE 
            WHEN qualification_rate_percent >= 80 THEN 'High Qualification Rate (80%+)'
            WHEN qualification_rate_percent >= 60 THEN 'Medium Qualification Rate (60-79%)'
            WHEN qualification_rate_percent >= 40 THEN 'Moderate Qualification Rate (40-59%)'
            WHEN qualification_rate_percent >= 20 THEN 'Low Qualification Rate (20-39%)'
            ELSE 'Very Low Qualification Rate (<20%)'
        END as qualification_rate_category,
        -- Categorize programs by benefit value
        CASE 
            WHEN avg_benefit_value >= 10000 THEN 'High Value ($10K+)'
            WHEN avg_benefit_value >= 5000 THEN 'Medium Value ($5K-$10K)'
            WHEN avg_benefit_value >= 1000 THEN 'Moderate Value ($1K-$5K)'
            WHEN avg_benefit_value >= 100 THEN 'Low Value ($100-$1K)'
            ELSE 'Very Low Value (<$100)'
        END as benefit_value_category,
        -- Get timing information from the base data
        min_delivery_time,
        max_delivery_time,
        min_application_time,
        max_application_time
    FROM {{ ref('int_benefit_program_summary') }}
),

white_label_insights AS (
    SELECT
        name_abbreviated,
        COUNT(DISTINCT white_label_name) as total_white_labels,
        STRING_AGG(DISTINCT white_label_name, ', ') as white_label_names,
        STRING_AGG(DISTINCT white_label_code, ', ') as white_label_codes,
        STRING_AGG(DISTINCT state_code, ', ') as state_codes,
        AVG(white_label_qualification_rate_percent) as avg_qualification_rate,
        SUM(total_benefit_value) as total_benefit_value_distributed,
        COUNT(DISTINCT CASE WHEN white_label_qualification_rate_percent > 50 THEN white_label_name END) as high_performing_white_labels,
        COUNT(DISTINCT CASE WHEN white_label_qualification_rate_percent < 20 THEN white_label_name END) as low_performing_white_labels
    FROM {{ ref('int_white_label_program_summary') }}
    GROUP BY name_abbreviated
),

program_trends AS (
    SELECT
        pe.name_abbreviated,
        DATE_TRUNC('month', pe.eligibility_date) as month,
        COUNT(*) as monthly_checks,
        SUM(CASE WHEN pe.eligible = true THEN 1 ELSE 0 END) as monthly_qualified,
        AVG(CASE WHEN pe.eligible = true THEN pe.estimated_value ELSE NULL END) as monthly_avg_value,
        SUM(CASE WHEN pe.eligible = true THEN pe.estimated_value ELSE 0 END) as monthly_total_value
    FROM {{ ref('stg_program_eligibility') }} pe
    GROUP BY pe.name_abbreviated, DATE_TRUNC('month', pe.eligibility_date)
)

SELECT
    -- Program identification
    pr.name_abbreviated,
    pr.name,
    pr.value_type,
    
    -- Core metrics
    pr.total_checks,
    pr.qualified_count,
    pr.not_qualified_count,
    pr.qualification_rate_percent,
    pr.rejection_rate_percent,
    
    -- Rankings
    pr.rank_by_qualification_rate,
    pr.rank_by_volume,
    pr.rank_by_value,
    
    -- Categorizations
    pr.qualification_rate_category,
    pr.benefit_value_category,
    
    -- Financial metrics
    pr.avg_benefit_value,
    pr.total_benefit_value,
    
    -- Timing information
    pr.min_delivery_time,
    pr.max_delivery_time,
    pr.min_application_time,
    pr.max_application_time,
    
    -- White label insights (aggregated)
    wli.total_white_labels,
    wli.white_label_names,
    wli.white_label_codes,
    wli.state_codes,
    wli.avg_qualification_rate,
    wli.total_benefit_value_distributed,
    wli.high_performing_white_labels,
    wli.low_performing_white_labels,
    
    -- Performance indicators
    CASE 
        WHEN pr.qualification_rate_percent > 70 AND pr.total_checks > 100 THEN 'High Performer'
        WHEN pr.qualification_rate_percent > 50 AND pr.total_checks > 50 THEN 'Good Performer'
        WHEN pr.qualification_rate_percent > 30 AND pr.total_checks > 25 THEN 'Average Performer'
        WHEN pr.qualification_rate_percent > 10 AND pr.total_checks > 10 THEN 'Low Performer'
        ELSE 'Needs Investigation'
    END as performance_indicator,
    
    -- Trend analysis (last 3 months vs previous 3 months)
    COALESCE(recent.monthly_avg_qualified, 0) as recent_monthly_avg_qualified,
    COALESCE(previous.monthly_avg_qualified, 0) as previous_monthly_avg_qualified,
    CASE 
        WHEN previous.monthly_avg_qualified > 0 
        THEN ROUND(((recent.monthly_avg_qualified - previous.monthly_avg_qualified) / previous.monthly_avg_qualified) * 100, 2)
        ELSE NULL
    END as qualification_trend_percent,
    
    CURRENT_TIMESTAMP as calculated_at

FROM program_rankings pr
LEFT JOIN white_label_insights wli ON pr.name_abbreviated = wli.name_abbreviated
LEFT JOIN (
    SELECT 
        name_abbreviated,
        AVG(monthly_qualified) as monthly_avg_qualified
    FROM program_trends 
    WHERE month >= CURRENT_DATE - INTERVAL '3 months'
    GROUP BY name_abbreviated
) recent ON pr.name_abbreviated = recent.name_abbreviated
LEFT JOIN (
    SELECT 
        name_abbreviated,
        AVG(monthly_qualified) as monthly_avg_qualified
    FROM program_trends 
    WHERE month >= CURRENT_DATE - INTERVAL '6 months' AND month < CURRENT_DATE - INTERVAL '3 months'
    GROUP BY name_abbreviated
) previous ON pr.name_abbreviated = previous.name_abbreviated

ORDER BY 
    pr.rank_by_qualification_rate,
    pr.total_checks DESC 