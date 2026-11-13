WITH counts AS (
    SELECT
        COUNT(*) AS buyers_count,
        COUNT(DISTINCT match_id) AS matches_count,
        MIN(median_purchase_time_sec) AS median_purchase_time_sec,
        COUNT(CASE WHEN timing_group = 'early' THEN 1 END) AS early_buyers_count,
        COUNT(CASE WHEN timing_group = 'late' THEN 1 END) AS late_buyers_count,
        COUNT(DISTINCT CASE WHEN timing_group = 'early' THEN match_id END)
            AS early_matches_count,
        COUNT(DISTINCT CASE WHEN timing_group = 'late' THEN match_id END)
            AS late_matches_count,
        COUNT(CASE WHEN timing_group = 'early' AND win THEN 1 END) AS early_wins,
        COUNT(CASE WHEN timing_group = 'late' AND win THEN 1 END) AS late_wins,
        AVG(CASE WHEN timing_group = 'early' THEN first_purchase_minutes END)
            AS early_avg_purchase_minutes,
        AVG(CASE WHEN timing_group = 'late' THEN first_purchase_minutes END)
            AS late_avg_purchase_minutes,
        COUNT(CASE WHEN rank_is_unknown THEN 1 END) AS unknown_rank_buyers_count,
        COUNT(CASE WHEN is_anonymous THEN 1 END) AS anonymous_buyers_count,
        COUNT(CASE WHEN is_provisional THEN 1 END) AS provisional_buyers_count,
        MIN(mart_loaded_at) AS source_mart_loaded_at_min,
        MAX(mart_loaded_at) AS source_mart_loaded_at_max
    FROM lakehouse.mart.case1_dominator_first_purchase
), rates AS (
    SELECT
        counts.*,
        CAST(early_wins AS DOUBLE) / NULLIF(early_buyers_count, 0) AS early_win_rate,
        CAST(late_wins AS DOUBLE) / NULLIF(late_buyers_count, 0) AS late_win_rate
    FROM counts
), comparison AS (
    SELECT
        rates.*,
        (early_win_rate - late_win_rate) * 100.0 AS win_rate_diff_pp
    FROM rates
)
SELECT
    buyers_count,
    matches_count,
    median_purchase_time_sec,
    median_purchase_time_sec / 60.0 AS median_purchase_minutes,
    early_buyers_count,
    late_buyers_count,
    early_matches_count,
    late_matches_count,
    early_wins,
    late_wins,
    early_buyers_count - early_wins AS early_losses,
    late_buyers_count - late_wins AS late_losses,
    early_win_rate,
    late_win_rate,
    early_win_rate * 100.0 AS early_win_rate_pct,
    late_win_rate * 100.0 AS late_win_rate_pct,
    win_rate_diff_pp,
    3.0 AS target_diff_pp,
    win_rate_diff_pp >= 3.0 AS target_reached,
    early_avg_purchase_minutes,
    late_avg_purchase_minutes,
    unknown_rank_buyers_count,
    anonymous_buyers_count,
    provisional_buyers_count,
    source_mart_loaded_at_min,
    source_mart_loaded_at_max,
    CAST(CURRENT_TIMESTAMP AS TIMESTAMP) AS mart_loaded_at,
    'case1-mart-v2-median' AS rules_version
FROM comparison
