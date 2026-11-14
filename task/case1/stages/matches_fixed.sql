matches_fixed:
WITH ranked AS (
    SELECT
        match_id,
        duration,
        game_mode,
        lobby_type,
        radiant_win,
        DENSE_RANK() OVER (
            PARTITION BY match_id
            ORDER BY loaded_at DESC NULLS LAST
        ) AS version_rank
    FROM lakehouse.raw.pg__matches
    WHERE match_id IS NOT NULL
),
latest_distinct AS (
    SELECT DISTINCT
        match_id,
        duration,
        game_mode,
        lobby_type,
        radiant_win
    FROM ranked
    WHERE version_rank = 1
),
valid_keys AS (
    SELECT match_id
    FROM latest_distinct
    GROUP BY match_id
    HAVING COUNT(*) = 1
)
SELECT
    m.match_id,
    m.duration,
    m.game_mode,
    m.lobby_type,
    m.radiant_win
FROM latest_distinct m
JOIN valid_keys k
    ON m.match_id = k.match_id
WHERE (
    m.game_mode IS NULL
    OR m.game_mode NOT IN (15, 18, 19, 20, 21, 23)
)
AND (
    m.lobby_type IS NULL
    OR m.lobby_type NOT IN (1, 4, 8)
)