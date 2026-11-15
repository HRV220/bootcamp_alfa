-- One row per available buyer-match pair, including excluded pairs.
-- NULL/anonymous keys are diagnostic groups, not necessarily real people.
SELECT match_id, steam_account_id,
    COUNT(*) AS available_purchase_events,
    SUM(CASE WHEN event_valid THEN 0 ELSE 1 END) AS invalid_events,
    COUNT(*) > 2 AS exceeds_purchase_limit,
    MIN(stage_loaded_at) <> MAX(stage_loaded_at) AS mixed_generation,
    MIN(purchase_time_sec) AS observed_min_time_sec,
    SUM(CASE WHEN event_valid THEN 0 ELSE 1 END) = 0
      AND COUNT(*) BETWEEN 1 AND 2
      AND MIN(stage_loaded_at) = MAX(stage_loaded_at) AS pair_locally_eligible
FROM lakehouse.stage.night_case1_purchase_events
GROUP BY match_id, steam_account_id
