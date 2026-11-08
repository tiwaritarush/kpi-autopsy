SELECT c.application_id, c.accepted_offer AS numerator, 1 AS denominator
FROM case_snapshot c
JOIN offer_snapshot o ON o.application_id = c.application_id
WHERE c.created_at >= :start AND c.created_at < :end;
