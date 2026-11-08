SELECT application_id,
       CASE WHEN application_stage_at IS NOT NULL THEN 1 ELSE 0 END AS numerator,
       1 AS denominator
FROM case_snapshot
WHERE created_at >= :start AND created_at < :end;
