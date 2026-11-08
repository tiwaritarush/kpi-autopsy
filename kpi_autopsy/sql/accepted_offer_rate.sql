SELECT application_id, accepted_offer AS numerator, 1 AS denominator
FROM case_snapshot
WHERE created_at >= :start AND created_at < :end;
