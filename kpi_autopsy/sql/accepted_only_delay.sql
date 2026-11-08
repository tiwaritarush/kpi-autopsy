SELECT application_id, first_offer_hours AS numerator, 1 AS denominator
FROM case_snapshot
WHERE created_at >= :start AND created_at < :end
  AND first_offer_at IS NOT NULL AND accepted_offer = 1;
