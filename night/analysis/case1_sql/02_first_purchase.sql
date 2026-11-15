-- Publish as lakehouse.mart.night_case1_first_purchase.
-- The complete pair is ineligible when ANY source event fails validation.
WITH pairs AS (
    SELECT match_id, steam_account_id,
        COUNT(*) AS purchase_events_count,
        SUM(CASE WHEN event_valid THEN 0 ELSE 1 END) AS invalid_events_count,
        MIN(purchase_time_sec) AS first_purchase_time_sec,
        MIN(player_slot) AS player_slot,
        MIN(hero_id) AS hero_id,
        MIN(rank) AS rank,
        MIN(CASE WHEN win THEN 1 ELSE 0 END) AS win_int,
        MIN(duration_sec) AS duration_sec,
        MIN(game_mode) AS game_mode,
        MIN(lobby_type) AS lobby_type,
        MIN(match_start_epoch_sec) AS match_start_epoch_sec,
        MIN(period_start_epoch_sec) AS period_start_epoch_sec,
        MIN(period_end_epoch_sec) AS period_end_epoch_sec,
        MIN(stage_loaded_at) AS source_stage_loaded_at_min,
        MAX(stage_loaded_at) AS source_stage_loaded_at_max
    FROM lakehouse.stage.night_case1_purchase_events
    GROUP BY match_id, steam_account_id
), eligible AS (
    SELECT * FROM pairs WHERE invalid_events_count = 0
      AND purchase_events_count BETWEEN 1 AND 2
      AND source_stage_loaded_at_min = source_stage_loaded_at_max
      AND (SELECT COUNT(DISTINCT stage_loaded_at)
           FROM lakehouse.stage.night_case1_purchase_events) = 1
      AND (SELECT COUNT(DISTINCT rules_version)
           FROM lakehouse.stage.night_case1_purchase_events) = 1
), ordered AS (
    SELECT first_purchase_time_sec,
        ROW_NUMBER() OVER (ORDER BY first_purchase_time_sec, match_id, steam_account_id) AS rn,
        COUNT(*) OVER () AS n
    FROM eligible
), threshold AS (
    SELECT AVG(CAST(first_purchase_time_sec AS DOUBLE)) AS median_purchase_time_sec
    FROM ordered WHERE rn IN (FLOOR((n+1)/2.0), FLOOR((n+2)/2.0))
)
SELECT eligible.*, win_int = 1 AS win,
    rank IS NULL AS rank_is_unknown,
    steam_account_id = 4294967295 AS is_anonymous,
    median_purchase_time_sec,
    CASE WHEN first_purchase_time_sec <= median_purchase_time_sec
         THEN 'early' ELSE 'late' END AS timing_group,
    CAST(NULL AS BOOLEAN) AS history_complete,
    TRUE AS is_provisional,
    CURRENT_TIMESTAMP AS mart_loaded_at,
    'night-case1-conservative-v1' AS rules_version
FROM eligible CROSS JOIN threshold
