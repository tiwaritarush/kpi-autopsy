CREATE TEMP TABLE offer_snapshot AS
SELECT
    offer_id,
    application_id,
    MIN(CASE WHEN activity = 'O_Create Offer' THEN occurred_at END) AS created_at,
    MIN(CASE WHEN activity = 'O_Accepted' THEN occurred_at END) AS accepted_at,
    MAX(CASE WHEN activity = 'O_Create Offer' THEN offered_amount END) AS offered_amount
FROM events
WHERE occurred_at <= :as_of AND offer_id IS NOT NULL
GROUP BY offer_id, application_id;
