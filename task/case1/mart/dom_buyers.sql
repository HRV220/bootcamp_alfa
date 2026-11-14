WITH buys AS (
    SELECT match_id, steam_account_id, MIN(`time`) AS buy_time
    FROM lakehouse.stage.purchase_events_new
    WHERE itemid = 164
      AND `time` >= 0
    GROUP BY match_id, steam_account_id
),
players AS (
    SELECT match_id, account_id, player_slot, hero_id, `rank` AS rank_raw, is_radiant, win
    FROM (
        SELECT mp.*,
               row_number() OVER (
                   PARTITION BY mp.match_id, mp.account_id
                   ORDER BY mp.player_slot
               ) AS rn
        FROM lakehouse.stage.match_players mp
        WHERE mp.account_id IS NOT NULL
          AND mp.account_id <> 4294967295
    )
    WHERE rn = 1
),
j AS (
    SELECT b.match_id,
           b.steam_account_id,
           b.buy_time,
           p.player_slot,
           p.hero_id,
           p.rank_raw,
           p.is_radiant,
           p.win,
           (p.match_id IS NOT NULL) AS is_direct,
           m.duration,
           m.game_mode,
           m.lobby_type
    FROM buys b
    JOIN lakehouse.stage.matches_fixed m ON m.match_id = b.match_id
    LEFT JOIN players p
      ON p.match_id = b.match_id AND p.account_id = b.steam_account_id
),
med AS (
    SELECT approx_percentile(buy_time, 0.5) AS median_sec
    FROM j
    WHERE is_direct
)
SELECT j.match_id,
       j.steam_account_id,
       j.buy_time,
       CASE WHEN j.is_direct THEN 'direct' ELSE 'hidden' END AS resolution,
       j.player_slot,
       j.hero_id,
       j.rank_raw,
       CASE WHEN j.rank_raw IS NULL OR j.rank_raw = 0 THEN 0
            ELSE CAST(floor((j.rank_raw - 1) / 10.0) + 1 AS integer) END AS league,
       j.is_radiant,
       CASE WHEN NOT j.is_direct THEN NULL
            WHEN j.win THEN 1 ELSE 0 END                             AS win,
       j.duration,
       j.game_mode,
       j.lobby_type,
       CASE WHEN j.duration < 1800 THEN '1: <30 min'
            WHEN j.duration < 2400 THEN '2: 30-40'
            WHEN j.duration < 3000 THEN '3: 40-50'
            ELSE '4: 50+' END                                        AS dur_bucket,
       CASE WHEN j.buy_time < 360  THEN '1: <6'
            WHEN j.buy_time < 480  THEN '2: 6-8'
            WHEN j.buy_time < 600  THEN '3: 8-10'
            WHEN j.buy_time < 720  THEN '4: 10-12'
            WHEN j.buy_time < 900  THEN '5: 12-15'
            WHEN j.buy_time < 1200 THEN '6: 15-20'
            ELSE '7: 20+' END                                        AS buy_bucket,
       med.median_sec                                                AS median_buy_sec,
       CASE WHEN j.is_direct THEN j.buy_time <= med.median_sec END   AS is_early
FROM j
CROSS JOIN med