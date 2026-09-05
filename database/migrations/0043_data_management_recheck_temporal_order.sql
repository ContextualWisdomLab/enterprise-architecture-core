BEGIN;

CREATE FUNCTION architecture_core.enforce_assessment_recheck_temporal_order()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
  trigger_accepted_at timestamptz;
BEGIN
  SELECT acceptance_record.accepted_at
    INTO trigger_accepted_at
    FROM architecture_core.assessment_evidence_acceptance AS acceptance_record
   WHERE acceptance_record.tenant_record_id = NEW.tenant_record_id
     AND acceptance_record.assessment_evidence_acceptance_id =
         NEW.trigger_evidence_acceptance_id;

  IF trigger_accepted_at IS NOT NULL
     AND NEW.requested_at < trigger_accepted_at THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'assessment reassessment request cannot predate triggering evidence acceptance';
  END IF;

  RETURN NEW;
END;
$$;

REVOKE ALL
ON FUNCTION architecture_core.enforce_assessment_recheck_temporal_order()
FROM PUBLIC;

CREATE TRIGGER assessment_recheck_request_temporal_guard
BEFORE INSERT
ON architecture_core.assessment_recheck_request
FOR EACH ROW
EXECUTE FUNCTION architecture_core.enforce_assessment_recheck_temporal_order();

DO $$
BEGIN
  IF EXISTS (
      SELECT 1
        FROM architecture_core.assessment_recheck_request AS recheck_record
        JOIN architecture_core.assessment_evidence_acceptance AS acceptance_record
          ON acceptance_record.tenant_record_id = recheck_record.tenant_record_id
         AND acceptance_record.assessment_evidence_acceptance_id =
             recheck_record.trigger_evidence_acceptance_id
       WHERE recheck_record.requested_at < acceptance_record.accepted_at
  ) THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'existing assessment reassessment request predates triggering evidence acceptance';
  END IF;
END;
$$;

COMMENT ON FUNCTION architecture_core.enforce_assessment_recheck_temporal_order() IS
'Fail-closed temporal integrity guard for immutable reassessment-request evidence. A reassessment request may be recorded at the same instant as, or after, the evidence acceptance that causally closed the final projected gap, but never before it.';

COMMIT;
