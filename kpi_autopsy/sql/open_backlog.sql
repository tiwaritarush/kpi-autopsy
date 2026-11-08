SELECT application_id, is_open AS numerator, 1 AS denominator
FROM case_snapshot
WHERE created_at >= :start AND created_at < :end;
