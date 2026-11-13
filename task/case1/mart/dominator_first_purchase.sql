WITH purchase_pairs AS (
    SELECT
        match_id,
        steam_account_id,
        COUNT(*) AS purchase_events_count,
        COUNT(time) AS known_purchase_times_count,
        MIN(time) AS first_purchase_time_sec,
        MAX(time) AS last_purchase_time_sec
    FROM lakehouse.stage.purchase_events
    WHERE itemId = 164
    GROUP BY match_id, steam_account_id
), player_links AS (
    SELECT match_id, account_id, COUNT(*) AS player_rows
    FROM lakehouse.stage.match_players
    GROUP BY match_id, account_id
), eligible AS (
    SELECT
        b.match_id,
        b.steam_account_id,
        p.player_slot,
        p.hero_id,
        p.rank,
        p.is_radiant,
        p.win,
        m.radiant_win,
        m.duration AS duration_sec,
        m.game_mode,
        m.lobby_type,
        b.purchase_events_count,
        b.first_purchase_time_sec
    FROM purchase_pairs b
    JOIN lakehouse.stage.matches m ON b.match_id = m.match_id
    JOIN player_links links
      ON b.match_id = links.match_id
     AND b.steam_account_id = links.account_id
     AND links.player_rows = 1
    JOIN lakehouse.stage.match_players p
      ON b.match_id = p.match_id
     AND b.steam_account_id = p.account_id
    WHERE b.steam_account_id > 0
      AND b.purchase_events_count <= 2
      AND b.known_purchase_times_count = b.purchase_events_count
      AND b.first_purchase_time_sec >= 0
      AND b.last_purchase_time_sec <= m.duration
      AND m.duration > 0
      AND m.game_mode NOT IN (15, 18, 19, 20, 21, 23)
      AND m.lobby_type NOT IN (1, 4, 8)
      AND p.player_slot IS NOT NULL
      AND p.hero_id IS NOT NULL
      AND p.is_radiant IS NOT NULL
      AND p.win IS NOT NULL
      AND m.radiant_win IS NOT NULL
      AND p.win = CASE WHEN p.is_radiant THEN m.radiant_win
                       ELSE NOT m.radiant_win END
), ordered_purchases AS (
    SELECT
        first_purchase_time_sec,
        ROW_NUMBER() OVER (
            ORDER BY first_purchase_time_sec, match_id, steam_account_id
        ) AS purchase_order,
        COUNT(*) OVER () AS buyers_count
    FROM eligible
), median_threshold AS (
    SELECT AVG(CAST(first_purchase_time_sec AS DOUBLE)) AS median_purchase_time_sec
    FROM ordered_purchases
    WHERE purchase_order IN (
        FLOOR((buyers_count + 1) / 2.0),
        FLOOR((buyers_count + 2) / 2.0)
    )
)
SELECT
    match_id,
    steam_account_id,
    player_slot,
    164 AS item_id,
    hero_id,
    rank,
    rank IS NULL AS rank_is_unknown,
    steam_account_id = 4294967295 AS is_anonymous,
    is_radiant,
    win,
    radiant_win,
    duration_sec,
    game_mode,
    lobby_type,
    purchase_events_count,
    first_purchase_time_sec,
    CAST(first_purchase_time_sec AS DOUBLE) / 60.0 AS first_purchase_minutes,
    median_purchase_time_sec,
    median_purchase_time_sec / 60.0 AS median_purchase_minutes,
    CASE WHEN first_purchase_time_sec <= median_purchase_time_sec THEN 'early' ELSE 'late'
    END AS timing_group,
    CAST(NULL AS BOOLEAN) AS history_complete,
    TRUE AS is_provisional,
    CAST(CURRENT_TIMESTAMP AS TIMESTAMP) AS mart_loaded_at,
    'case1-mart-v2-median' AS rules_version
FROM eligible
CROSS JOIN median_threshold
