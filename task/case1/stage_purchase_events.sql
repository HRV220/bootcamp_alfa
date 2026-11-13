WITH purchases AS (
    SELECT
        id AS purchase_event_id,
        match_id,
        steam_account_id,
        itemid,
        time AS purchase_time_sec,
        job_id AS source_job_id,
        sys_insert_stamp AS source_loaded_at,
        src_modified_stamp AS source_modified_at
    FROM lakehouse.raw.mongo__purchase_events
    WHERE itemid = 164
), target_ids AS (
    SELECT DISTINCT purchase_event_id
    FROM purchases
    WHERE purchase_event_id IS NOT NULL
), event_id_counts AS (
    SELECT r.id, COUNT(*) AS n
    FROM lakehouse.raw.mongo__purchase_events r
    JOIN target_ids t ON r.id = t.purchase_event_id
    GROUP BY r.id
), item_status AS (
    SELECT COUNT(*) AS n, MAX(name) AS item_name
    FROM lakehouse.raw.pg__items
    WHERE item_id = 164
), match_counts AS (
    SELECT match_id, COUNT(*) AS n
    FROM lakehouse.raw.pg__matches
    GROUP BY match_id
), player_counts AS (
    SELECT match_id, account_id, COUNT(*) AS n
    FROM lakehouse.raw.pg__match_players
    GROUP BY match_id, account_id
), player_slot_counts AS (
    SELECT match_id, player_slot, COUNT(*) AS n
    FROM lakehouse.raw.pg__match_players
    GROUP BY match_id, player_slot
), context AS (
    SELECT
        e.*,
        COALESCE(ic.n, 0) AS event_id_rows,
        i.n AS item_rows,
        i.item_name,
        COALESCE(mc.n, 0) AS match_rows,
        COALESCE(pc.n, 0) AS player_rows,
        COALESCE(sc.n, 0) AS player_slot_rows,
        CAST(m.start_time AS BIGINT) AS match_start_epoch_sec,
        m.duration,
        m.game_mode,
        m.lobby_type,
        m.radiant_win,
        p.player_slot,
        p.hero_id,
        p.rank,
        p.is_radiant,
        p.win
    FROM purchases e
    CROSS JOIN item_status i
    LEFT JOIN event_id_counts ic ON e.purchase_event_id = ic.id
    LEFT JOIN match_counts mc ON e.match_id = mc.match_id
    LEFT JOIN player_counts pc
      ON e.match_id = pc.match_id
     AND e.steam_account_id = pc.account_id
    -- Подробные строки добавляем только при ровно одном соответствии.
    LEFT JOIN lakehouse.raw.pg__matches m
      ON e.match_id = m.match_id AND mc.n = 1
    LEFT JOIN lakehouse.raw.pg__match_players p
      ON e.match_id = p.match_id
     AND e.steam_account_id = p.account_id AND pc.n = 1
    LEFT JOIN player_slot_counts sc
      ON p.match_id = sc.match_id AND p.player_slot = sc.player_slot
), prepared AS (
    SELECT
        context.*,
        COUNT(*) OVER (PARTITION BY match_id, steam_account_id)
            AS buyer_purchase_events_count,
        match_start_epoch_sec + CAST(purchase_time_sec AS BIGINT)
            AS purchase_epoch_sec,
        CASE
            WHEN is_radiant IS NULL OR radiant_win IS NULL THEN NULL
            WHEN is_radiant THEN radiant_win
            ELSE NOT radiant_win
        END AS expected_win,
        steam_account_id = 4294967295 AS is_anonymous,
        rank IS NULL AS rank_is_unknown
    FROM context
), diagnosed AS (
    SELECT
        prepared.*,
        CONCAT_WS('|',
            CASE WHEN purchase_event_id IS NULL OR TRIM(purchase_event_id) = ''
                 THEN 'invalid_event_id' END,
            CASE WHEN event_id_rows > 1 THEN 'duplicate_event_id' END,
            CASE WHEN item_rows <> 1 OR item_name IS NULL
                           OR item_name <> 'helm_of_the_dominator'
                 THEN 'invalid_item_reference' END,
            CASE WHEN match_id IS NULL THEN 'null_match_id' END,
            CASE WHEN steam_account_id IS NULL THEN 'null_account_id' END,
            CASE WHEN steam_account_id = 0 THEN 'bot' END,
            CASE WHEN steam_account_id < 0 THEN 'invalid_account_id' END,
            CASE WHEN buyer_purchase_events_count > 2
                 THEN 'excessive_purchase_events' END,
            CASE WHEN match_rows = 0 THEN 'match_not_found' END,
            CASE WHEN match_rows > 1 THEN 'ambiguous_match' END,
            CASE WHEN player_rows = 0 THEN 'player_not_found' END,
            CASE WHEN player_rows > 1 THEN 'ambiguous_player' END,
            CASE WHEN player_rows = 1 AND player_slot_rows <> 1
                 THEN 'invalid_player_slot_key' END,
            CASE WHEN match_rows = 1 AND lobby_type IN (1, 4, 8)
                 THEN 'excluded_lobby' END,
            CASE WHEN match_rows = 1 AND game_mode IN (15, 18, 19, 20, 21, 23)
                 THEN 'excluded_game_mode' END,
            CASE WHEN match_rows = 1 AND (lobby_type IS NULL OR game_mode IS NULL)
                 THEN 'unknown_match_context' END,
            CASE WHEN match_rows = 1
                       AND (match_start_epoch_sec IS NULL OR match_start_epoch_sec <= 0)
                 THEN 'invalid_match_start' END,
            CASE WHEN match_rows = 1 AND (duration IS NULL OR duration <= 0)
                 THEN 'invalid_duration' END,
            CASE WHEN purchase_time_sec IS NULL THEN 'null_purchase_time' END,
            CASE WHEN purchase_time_sec < 0 THEN 'negative_purchase_time' END,
            CASE WHEN match_rows = 1 AND purchase_time_sec > duration
                 THEN 'purchase_after_match' END,
            CASE WHEN player_rows = 1 AND (
                      player_slot IS NULL OR hero_id IS NULL
                      OR is_radiant IS NULL OR win IS NULL)
                 THEN 'unknown_player_context' END,
            CASE WHEN match_rows = 1 AND radiant_win IS NULL
                 THEN 'unknown_match_outcome' END,
            CASE WHEN win <> expected_win THEN 'outcome_conflict' END
        ) AS dq_reasons
    FROM prepared
)
SELECT
    purchase_event_id,
    match_id,
    steam_account_id,
    itemid,
    purchase_time_sec,
    buyer_purchase_events_count,
    buyer_purchase_events_count > 2 AS exceeds_purchase_limit,
    source_job_id,
    source_loaded_at,
    source_modified_at,
    event_id_rows,
    item_rows,
    match_rows,
    player_rows,
    player_slot_rows,
    match_start_epoch_sec,
    purchase_epoch_sec,
    duration,
    game_mode,
    lobby_type,
    radiant_win,
    player_slot,
    hero_id,
    rank,
    is_radiant,
    win,
    expected_win,
    is_anonymous,
    rank_is_unknown,
    dq_reasons,
    dq_reasons = '' AS event_valid,
    CAST(CURRENT_TIMESTAMP AS TIMESTAMP) AS stage_loaded_at,
    'case1-stage-sql-v2' AS rules_version
FROM diagnosed

-- Справочно: прежние снимки профилирования. Запрос выше читает текущий RAW.
-- items: 8964302861571785310
-- purchases: 1692340780650444458
-- matches: 5479601878325658821
-- players: 6702098789656983058
