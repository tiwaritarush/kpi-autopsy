CREATE TEMP TABLE case_snapshot AS
WITH event_summary AS (
    SELECT
        application_id,
        MIN(CASE WHEN activity = 'A_Create Application' THEN occurred_at END) AS created_at,
        MIN(CASE WHEN activity = 'O_Create Offer' THEN occurred_at END) AS first_offer_at,
        MIN(CASE WHEN activity = 'O_Accepted' THEN occurred_at END) AS accepted_offer_at,
        MIN(CASE WHEN activity = 'A_Accepted' THEN occurred_at END) AS application_stage_at,
        MAX(occurred_at) AS last_event_at
    FROM events
    WHERE occurred_at <= :as_of
    GROUP BY application_id
), application_states AS (
    SELECT
        application_id,
        activity,
        ROW_NUMBER() OVER (
            PARTITION BY application_id
            ORDER BY occurred_at DESC, event_row DESC
        ) AS position
    FROM events
    WHERE occurred_at <= :as_of AND event_origin = 'Application'
), offer_counts AS (
    SELECT application_id, COUNT(*) AS offer_count
    FROM offer_snapshot
    GROUP BY application_id
)
SELECT
    a.application_id,
    a.application_type,
    a.loan_goal,
    a.requested_amount,
    e.created_at,
    SUBSTR(e.created_at, 1, 7) AS created_month,
    e.first_offer_at,
    e.accepted_offer_at,
    e.application_stage_at,
    e.last_event_at,
    s.activity AS last_application_activity,
    COALESCE(o.offer_count, 0) AS offer_count,
    CASE WHEN e.accepted_offer_at IS NOT NULL THEN 1 ELSE 0 END AS accepted_offer,
    CASE WHEN e.first_offer_at IS NOT NULL
        THEN (JULIANDAY(e.first_offer_at) - JULIANDAY(e.created_at)) * 24
    END AS first_offer_hours,
    CASE WHEN e.accepted_offer_at IS NULL
        AND s.activity NOT IN ('A_Pending', 'A_Denied', 'A_Cancelled')
        THEN 1 ELSE 0
    END AS is_open,
    JULIANDAY(:as_of) - JULIANDAY(e.created_at) AS age_days
FROM applications a
JOIN event_summary e ON e.application_id = a.application_id
LEFT JOIN application_states s ON s.application_id = a.application_id AND s.position = 1
LEFT JOIN offer_counts o ON o.application_id = a.application_id
WHERE e.created_at IS NOT NULL;
