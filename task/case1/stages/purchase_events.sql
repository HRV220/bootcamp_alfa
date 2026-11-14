WITH projected AS (
    SELECT DISTINCT
        CAST(id AS STRING) AS id,
        CAST(match_id AS BIGINT) AS match_id,
        CAST(itemid AS INT) AS itemId,
        CAST(steam_account_id AS BIGINT) AS steam_account_id,
        CAST(time AS INT) AS time
    FROM lakehouse.raw.mongo__purchase_events
    WHERE id IS NOT NULL
      AND match_id IS NOT NULL
),
valid_ids AS (
    SELECT id
    FROM projected
    GROUP BY id
    HAVING COUNT(*) = 1
)
SELECT
    e.id,
    e.match_id,
    e.itemId,
    e.steam_account_id,
    e.time
FROM projected e
JOIN valid_ids v
    ON e.id = v.id
JOIN lakehouse.stage.matches m
    ON e.match_id = m.match_id
