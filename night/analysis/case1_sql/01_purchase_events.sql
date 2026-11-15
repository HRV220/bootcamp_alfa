-- Proposed portable SELECT for Spark/Trino. Not executed in the cluster.
-- Publish as lakehouse.stage.night_case1_purchase_events.
-- All item-164 input rows remain, including invalid and out-of-period events.
WITH parameters AS (
    SELECT 1791936000 AS period_start_epoch_sec,
           1792108800 AS period_end_epoch_sec
), id_counts AS (
    SELECT id, COUNT(*) AS id_rows
    FROM lakehouse.raw.mongo__purchase_events GROUP BY id
), match_counts AS (
    SELECT match_id, COUNT(*) AS match_rows
    FROM lakehouse.raw.pg__matches GROUP BY match_id
), unique_matches AS (
    SELECT m.* FROM lakehouse.raw.pg__matches m
    JOIN match_counts c ON m.match_id = c.match_id AND c.match_rows = 1
), account_counts AS (
    SELECT match_id, account_id, COUNT(*) AS account_rows
    FROM lakehouse.raw.pg__match_players GROUP BY match_id, account_id
), slot_counts AS (
    SELECT match_id, player_slot, COUNT(*) AS slot_rows
    FROM lakehouse.raw.pg__match_players GROUP BY match_id, player_slot
), unique_players AS (
    SELECT p.* FROM lakehouse.raw.pg__match_players p
    JOIN account_counts a ON p.match_id = a.match_id
      AND p.account_id = a.account_id AND a.account_rows = 1
    JOIN slot_counts s ON p.match_id = s.match_id
      AND p.player_slot = s.player_slot AND s.slot_rows = 1
), context AS (
    SELECT e.id AS event_id, e.match_id, e.steam_account_id, e.itemid,
           e.time AS purchase_time_sec,
           COALESCE(i.id_rows, 0) AS event_id_rows,
           COALESCE(mc.match_rows, 0) AS match_rows,
           COALESCE(ac.account_rows, 0) AS player_account_rows,
           p.player_slot, p.hero_id, p.rank, p.is_radiant, p.win,
           m.start_time AS match_start_epoch_sec, m.duration AS duration_sec,
           m.game_mode, m.lobby_type, m.radiant_win,
           parameters.period_start_epoch_sec, parameters.period_end_epoch_sec
    FROM lakehouse.raw.mongo__purchase_events e
    CROSS JOIN parameters
    LEFT JOIN id_counts i ON e.id = i.id
    LEFT JOIN match_counts mc ON e.match_id = mc.match_id
    LEFT JOIN unique_matches m ON e.match_id = m.match_id
    LEFT JOIN account_counts ac ON e.match_id = ac.match_id
      AND e.steam_account_id = ac.account_id
    LEFT JOIN unique_players p ON e.match_id = p.match_id
      AND e.steam_account_id = p.account_id
    WHERE e.itemid = 164
), flags AS (
    SELECT context.*,
        event_id IS NULL OR event_id_rows <> 1 AS dq_event_id,
        match_id IS NULL OR match_rows <> 1 AS dq_match_key,
        steam_account_id IS NULL OR steam_account_id <= 0 AS dq_buyer_key,
        player_account_rows <> 1 OR player_slot IS NULL AS dq_player_link,
        match_start_epoch_sec IS NULL
          OR match_start_epoch_sec < period_start_epoch_sec
          OR match_start_epoch_sec >= period_end_epoch_sec AS dq_period,
        duration_sec IS NULL OR duration_sec <= 0 AS dq_duration,
        purchase_time_sec IS NULL OR purchase_time_sec < 0
          OR COALESCE(purchase_time_sec > duration_sec, FALSE) AS dq_purchase_time,
        game_mode IS NULL OR game_mode IN (15,18,19,20,21,23) AS dq_game_mode,
        lobby_type IS NULL OR lobby_type IN (1,4,8) AS dq_lobby_type,
        hero_id IS NULL AS dq_hero,
        is_radiant IS NULL OR win IS NULL OR radiant_win IS NULL
          OR COALESCE(win <> CASE WHEN is_radiant THEN radiant_win
                                 ELSE NOT radiant_win END, FALSE) AS dq_outcome
    FROM context
)
SELECT flags.*,
    NOT (dq_event_id OR dq_match_key OR dq_buyer_key OR dq_player_link
         OR dq_period OR dq_duration OR dq_purchase_time OR dq_game_mode
         OR dq_lobby_type OR dq_hero OR dq_outcome) AS event_valid,
    CURRENT_TIMESTAMP AS stage_loaded_at,
    'night-case1-conservative-v1' AS rules_version
FROM flags
