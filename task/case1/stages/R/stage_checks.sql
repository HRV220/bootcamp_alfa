WITH events AS (
    SELECT * FROM lakehouse.stage.case1_dominator_purchase_events
), firsts AS (
    SELECT * FROM lakehouse.stage.case1_dominator_first_purchase
), repeated_events AS (
    SELECT purchase_event_id FROM events
    GROUP BY purchase_event_id HAVING COUNT(*) > 1
), repeated_firsts AS (
    SELECT match_id, steam_account_id FROM firsts
    GROUP BY match_id, steam_account_id HAVING COUNT(*) > 1
), blocked_pairs AS (
    SELECT match_id, steam_account_id FROM events
    GROUP BY match_id, steam_account_id
    HAVING MAX(CASE WHEN event_valid THEN 0 ELSE 1 END) = 1 OR COUNT(*) > 2
), excessive_purchase_pairs AS (
    SELECT match_id, steam_account_id FROM events
    GROUP BY match_id, steam_account_id HAVING COUNT(*) > 2
)
SELECT 'stage_events' AS metric, COUNT(*) AS value FROM events
UNION ALL
SELECT 'null_event_id', COUNT(*) FROM events WHERE purchase_event_id IS NULL
UNION ALL
SELECT 'repeated_event_id_groups', COUNT(*) FROM repeated_events
UNION ALL
SELECT 'blocked_buyer_pairs', COUNT(*) FROM blocked_pairs
UNION ALL
SELECT 'more_than_two_purchase_pairs', COUNT(*) FROM excessive_purchase_pairs
UNION ALL
SELECT 'excessive_pairs_in_firsts', COUNT(*) FROM firsts
WHERE purchase_events_count > 2
UNION ALL
SELECT 'events_with_old_rules', COUNT(*) FROM events
WHERE rules_version IS NULL OR rules_version <> 'case1-stage-sql-v2'
UNION ALL
SELECT 'first_purchase_pairs', COUNT(*) FROM firsts
UNION ALL
SELECT 'repeated_first_purchase_keys', COUNT(*) FROM repeated_firsts
UNION ALL
SELECT 'first_purchase_with_null_key', COUNT(*) FROM firsts
WHERE match_id IS NULL OR steam_account_id IS NULL
UNION ALL
SELECT 'blocked_pairs_in_firsts', COUNT(*) FROM firsts f JOIN blocked_pairs b
  ON f.match_id = b.match_id AND f.steam_account_id = b.steam_account_id
UNION ALL
SELECT 'early_pairs', COUNT(*) FROM firsts WHERE timing_group = 'early'
UNION ALL
SELECT 'late_pairs', COUNT(*) FROM firsts WHERE timing_group = 'late'
UNION ALL
SELECT 'unknown_rank_pairs', COUNT(*) FROM firsts WHERE rank_is_unknown
UNION ALL
SELECT 'anonymous_pairs', COUNT(*) FROM firsts WHERE is_anonymous
UNION ALL
SELECT 'forbidden_filters_in_firsts', COUNT(*) FROM firsts
WHERE steam_account_id = 0 OR lobby_type IN (1, 4, 8)
   OR game_mode IN (15, 18, 19, 20, 21, 23)
UNION ALL
SELECT 'source_stage_batches_differ', COUNT(*) FROM firsts
WHERE source_stage_loaded_at IS NULL
   OR source_stage_loaded_at <> (SELECT MAX(stage_loaded_at) FROM events)
UNION ALL
SELECT CONCAT_WS(':', 'event_status',
                 CASE WHEN dq_reasons = '' THEN 'ok' ELSE dq_reasons END), COUNT(*)
FROM events GROUP BY dq_reasons
