-- Publish as lakehouse.mart.night_case1_winrate.
-- Observational point estimates only, no significance or causal assertion.
WITH counts AS (
    SELECT COUNT(*) AS buyers_count,
        COUNT(DISTINCT match_id) AS matches_count,
        MIN(median_purchase_time_sec) AS median_purchase_time_sec,
        COUNT(CASE WHEN timing_group = 'early' THEN 1 END) AS early_n,
        COUNT(CASE WHEN timing_group = 'late' THEN 1 END) AS late_n,
        COUNT(CASE WHEN timing_group = 'early' AND win THEN 1 END) AS early_wins,
        COUNT(CASE WHEN timing_group = 'late' AND win THEN 1 END) AS late_wins,
        MIN(mart_loaded_at) AS source_mart_loaded_at_min,
        MAX(mart_loaded_at) AS source_mart_loaded_at_max
    FROM lakehouse.mart.night_case1_first_purchase
), rates AS (
    SELECT counts.*,
        100.0 * early_wins / NULLIF(early_n, 0) AS early_win_rate_pct,
        100.0 * late_wins / NULLIF(late_n, 0) AS late_win_rate_pct
    FROM counts
)
SELECT rates.*,
    early_win_rate_pct - late_win_rate_pct AS win_rate_diff_pp,
    3.0 AS target_diff_pp,
    early_win_rate_pct - late_win_rate_pct >= 3.0 AS target_reached,
    CURRENT_TIMESTAMP AS summary_loaded_at
FROM rates
