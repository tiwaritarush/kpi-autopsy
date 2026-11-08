SELECT application_id, accepted_offer AS numerator, 1 AS denominator
FROM case_snapshot
WHERE first_offer_at >= :start AND first_offer_at < :end;
