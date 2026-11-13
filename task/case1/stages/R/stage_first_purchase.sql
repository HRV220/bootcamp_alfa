WITH pair_quality AS (
    SELECT
        match_id,
        steam_account_id,
        COUNT(*) AS pair_events_count,
        MAX(CASE WHEN event_valid THEN 0 ELSE 1 END) AS has_problem
    FROM lakehouse.stage.case1_dominator_purchase_events
    GROUP BY match_id, steam_account_id
), eligible AS (
    SELECT e.*
    FROM lakehouse.stage.case1_dominator_purchase_events e
    JOIN pair_quality q
      ON e.match_id = q.match_id
     AND e.steam_account_id = q.steam_account_id
    WHERE q.has_problem = 0
      AND q.pair_events_count <= 2
)
SELECT
    match_id,
    steam_account_id,
    player_slot,
    hero_id,
    rank,
    is_radiant,
    win,
    duration,
    game_mode,
    lobby_type,
    radiant_win,
    match_start_epoch_sec,
    is_anonymous,
    rank_is_unknown,
    MIN(purchase_time_sec) AS first_purchase_time,
    CAST(MIN(purchase_time_sec) AS DOUBLE) / 60.0 AS first_purchase_minutes,
    MIN(purchase_epoch_sec) AS first_purchase_epoch_sec,
    COUNT(*) AS purchase_events_count,
    CASE WHEN MIN(purchase_time_sec) <= 480 THEN 'early' ELSE 'late'
    END AS timing_group,
    CAST(NULL AS BOOLEAN) AS history_complete,
    TRUE AS is_provisional,
    MIN(stage_loaded_at) AS source_stage_loaded_at,
    CAST(CURRENT_TIMESTAMP AS TIMESTAMP) AS stage_loaded_at,
    'case1-stage-sql-v2' AS rules_version
FROM eligible
GROUP BY
    match_id, steam_account_id, player_slot, hero_id, rank,
    is_radiant, win, duration, game_mode, lobby_type, radiant_win,
    match_start_epoch_sec, is_anonymous, rank_is_unknown
