WITH ranked AS (
    SELECT
        match_id,
        player_slot,
        account_id,
        hero_id,
        rank,
        is_radiant,
        win,
        ROW_NUMBER() OVER (
            PARTITION BY match_id, player_slot
            ORDER BY
                src_modified_stamp DESC NULLS LAST,
                account_id DESC NULLS LAST,
                hero_id DESC NULLS LAST,
                rank DESC NULLS LAST,
                is_radiant DESC NULLS LAST,
                win DESC NULLS LAST
        ) AS rn
    FROM lakehouse.raw.pg__match_players
    WHERE match_id IS NOT NULL
      AND player_slot IS NOT NULL
)
SELECT
    p.match_id,
    p.player_slot,
    p.account_id,
    p.hero_id,
    p.rank,
    p.is_radiant,
    p.win
FROM ranked p
JOIN lakehouse.stage.matches m
    ON m.match_id = p.match_id
WHERE p.rn = 1
