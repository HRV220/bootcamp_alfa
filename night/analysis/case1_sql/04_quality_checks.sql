-- Standalone SELECT for a recorded, immutable stage snapshot.
-- Counts of reasons can overlap; do not sum them into a loss waterfall.
SELECT COUNT(*) AS source_dominator_events,
    SUM(CASE WHEN event_valid THEN 1 ELSE 0 END) AS valid_events,
    SUM(CASE WHEN dq_event_id THEN 1 ELSE 0 END) AS dq_event_id_events,
    SUM(CASE WHEN dq_match_key THEN 1 ELSE 0 END) AS dq_match_key_events,
    SUM(CASE WHEN dq_buyer_key THEN 1 ELSE 0 END) AS dq_buyer_key_events,
    SUM(CASE WHEN dq_player_link THEN 1 ELSE 0 END) AS dq_player_link_events,
    SUM(CASE WHEN dq_period THEN 1 ELSE 0 END) AS dq_period_events,
    SUM(CASE WHEN dq_duration THEN 1 ELSE 0 END) AS dq_duration_events,
    SUM(CASE WHEN dq_purchase_time THEN 1 ELSE 0 END) AS dq_purchase_time_events,
    SUM(CASE WHEN dq_game_mode THEN 1 ELSE 0 END) AS dq_game_mode_events,
    SUM(CASE WHEN dq_lobby_type THEN 1 ELSE 0 END) AS dq_lobby_type_events,
    SUM(CASE WHEN dq_hero THEN 1 ELSE 0 END) AS dq_hero_events,
    SUM(CASE WHEN dq_outcome THEN 1 ELSE 0 END) AS dq_outcome_events,
    MIN(stage_loaded_at) AS min_loaded_at, MAX(stage_loaded_at) AS max_loaded_at
FROM lakehouse.stage.night_case1_purchase_events
