{{
  config(
    materialized='view',
    description='Staging model for program translation data, focusing on value_type labels'
  )
}}

WITH translations_t AS (
    SELECT
        tt.id,
        tt.label
    FROM {{ source('django_apps', 'translations_translation') }} tt
    WHERE label ILIKE 'program.%-name' 
       OR label ILIKE 'program.%-apply_button_link' 
       OR label ILIKE 'program.%-value_type'
    ORDER BY tt.id
),

translations_tt AS (
    SELECT 
        ttt.id, 
        master_id, 
        language_code, 
        text
    FROM {{ source('django_apps', 'translations_translation_translation') }} ttt
    LEFT JOIN translations_t tt ON ttt.master_id = tt.id
    WHERE master_id IN (tt.id) 
      AND language_code = 'en-us'
)

SELECT 
    ttt.id, 
    ttt.master_id, 
    tt.label, 
    ttt.language_code, 
    ttt.text
FROM translations_t tt
LEFT JOIN translations_tt ttt ON tt.id = ttt.master_id
WHERE tt.label ILIKE 'program.%-value_type' 