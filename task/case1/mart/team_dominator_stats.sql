WITH valid_players AS (
    SELECT
        match_id,
        player_slot,
        account_id,
        is_radiant,
        win,
        CASE WHEN account_id IS NULL OR account_id = 4294967295 THEN 1 ELSE 0 END AS is_hidden
    FROM lakehouse.stage.match_players
),
teams AS (
    SELECT
        match_id,
        is_radiant,
        MAX(CASE WHEN win THEN 1 ELSE 0 END) AS win,
        COUNT(DISTINCT player_slot) AS players_in_slots,
        SUM(is_hidden) AS hidden_players
    FROM valid_players
    GROUP BY match_id, is_radiant
),
valid_matches AS (
    SELECT match_id
    FROM teams
    GROUP BY match_id
    HAVING COUNT(DISTINCT is_radiant) = 2
       AND MIN(players_in_slots) = 5
       AND MAX(players_in_slots) = 5
       AND SUM(win) = 1
),
bad_matches AS (
    SELECT DISTINCT match_id
    FROM valid_players
    WHERE is_hidden = 1
),
dom_purchases AS (
    SELECT
        match_id,
        steam_account_id,
        CAST(time AS INTEGER) AS buy_time
    FROM lakehouse.stage.purchase_events_new
    WHERE itemid = 164
),
team_dom AS (
    SELECT
        vp.match_id,
        vp.is_radiant,
        COUNT(dp.buy_time) AS dom_cnt,
        MIN(dp.buy_time) AS first_dom_time
    FROM valid_players vp
    LEFT JOIN dom_purchases dp
        ON dp.match_id = vp.match_id
       AND dp.steam_account_id = vp.account_id
    GROUP BY vp.match_id, vp.is_radiant
)
SELECT
    t.match_id,
    t.is_radiant,
    t.win,
    m.duration,
    m.game_mode,
    m.lobby_type,
    CASE
        WHEN m.duration < 1800 THEN '1: <30 min'
        WHEN m.duration < 2400 THEN '2: 30-40'
        WHEN m.duration < 3000 THEN '3: 40-50'
        ELSE '4: 50+'
    END AS dur_bucket,
    t.players_in_slots,
    t.hidden_players,
    COALESCE(td.dom_cnt, 0) AS dom_cnt,
    CASE WHEN COALESCE(td.dom_cnt, 0) > 0 THEN true ELSE false END AS team_has_dom,
    CAST(td.first_dom_time AS INTEGER) AS first_dom_time,
    CAST(false AS BOOLEAN) AS match_has_hidden_buyer
FROM teams t
JOIN valid_matches v
    ON v.match_id = t.match_id
JOIN lakehouse.stage.matches_fixed m
    ON m.match_id = t.match_id
LEFT JOIN team_dom td
    ON td.match_id = t.match_id
   AND td.is_radiant = t.is_radiant
LEFT JOIN bad_matches bm
    ON bm.match_id = t.match_id
WHERE bm.match_id IS NULL