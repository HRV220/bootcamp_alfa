WITH events AS (
    SELECT
        match_id,
        CONCAT('kill:', CAST(id AS VARCHAR(64))) AS event_id,
        'hero_kill' AS event_type,
        CAST(time AS INTEGER) AS event_time,
        CAST(steam_account_id AS BIGINT) AS steam_account_id,
        CAST(attacker AS INTEGER) AS attacker,
        CAST(target AS INTEGER) AS target,
        CAST(gold AS INTEGER) AS gold,
        CAST(xp AS INTEGER) AS xp,
        CAST(NULL AS INTEGER) AS cost,
        CAST(NULL AS INTEGER) AS radiant_mask,
        CAST(NULL AS INTEGER) AS dire_mask,
        CAST(NULL AS VARCHAR(256)) AS item_name,
        CAST(NULL AS INTEGER) AS item_cost,
        CAST(NULL AS INTEGER) AS streak_hero_id,
        CAST(NULL AS INTEGER) AS streak_value
    FROM lakehouse.raw.mongo__kill_events
    WHERE id IS NOT NULL

    UNION ALL

    SELECT
        match_id,
        CONCAT('tower_destroyed:', CAST(id AS VARCHAR(64))),
        'tower_destroyed',
        CAST(time AS INTEGER),
        CAST(NULL AS BIGINT),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER),
        CAST(radiant AS INTEGER),
        CAST(dire AS INTEGER),
        CAST(NULL AS VARCHAR(256)),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER)
    FROM lakehouse.raw.mongo__tower_death_events
    WHERE id IS NOT NULL

    UNION ALL

    SELECT
        match_id,
        CONCAT('roshan_reward:', CAST(id AS VARCHAR(64))),
        'roshan_reward',
        CAST(time AS INTEGER),
        CAST(steam_account_id AS BIGINT),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER),
        CAST(amount AS INTEGER),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER),
        CAST(NULL AS VARCHAR(256)),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER)
    FROM lakehouse.raw.mongo__gold_events
    WHERE id IS NOT NULL
      AND LOWER(reason) = 'roshan'

    UNION ALL

    SELECT
        match_id,
        CONCAT('buyback:', CAST(id AS VARCHAR(64))),
        'buyback',
        CAST(time AS INTEGER),
        CAST(steam_account_id AS BIGINT),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER),
        CAST(cost AS INTEGER),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER),
        CAST(NULL AS VARCHAR(256)),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER)
    FROM lakehouse.raw.mongo__buyback_events
    WHERE id IS NOT NULL

    UNION ALL

    SELECT
        p.match_id,
        CONCAT('purchase:', CAST(p.id AS VARCHAR(64))),
        'item_purchase',
        CAST(p.time AS INTEGER),
        CAST(p.steam_account_id AS BIGINT),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER),
        CAST(COALESCE(i.localized_name, i.name) AS VARCHAR(256)),
        CAST(i.cost AS INTEGER),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER)
    FROM lakehouse.raw.mongo__purchase_events p
    INNER JOIN lakehouse.raw.pg__items i
        ON p.itemid = i.item_id
    WHERE p.id IS NOT NULL
      AND i.cost > 2000

    UNION ALL

    SELECT
        match_id,
        CONCAT('streak:', CAST(id AS VARCHAR(64))),
        LOWER(TRIM(type)),
        CAST(time AS INTEGER),
        CAST(steam_account_id AS BIGINT),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER),
        CAST(NULL AS INTEGER),
        CAST(NULL AS VARCHAR(256)),
        CAST(NULL AS INTEGER),
        CAST(heroid AS INTEGER),
        CAST(value AS INTEGER)
    FROM lakehouse.raw.mongo__streak_events
    WHERE id IS NOT NULL
      AND UPPER(TRIM(type)) IN ('KILL_STREAK', 'MULTI_KILL')
)
SELECT *
FROM events;