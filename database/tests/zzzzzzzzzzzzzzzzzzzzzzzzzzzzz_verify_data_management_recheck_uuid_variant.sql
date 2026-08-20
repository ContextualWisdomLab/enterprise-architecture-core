\set ON_ERROR_STOP on

-- Canonical Context Fabric references are RFC 9562 UUIDv7 values. PostgreSQL
-- returns NULL from uuid_extract_version() for UUIDs outside the RFC variant,
-- so comparisons that only use `<> 7` can accidentally treat them as valid.
RESET ROLE;
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

DO $$
DECLARE
  projection_id uuid;
  acceptance_id uuid;
  request_time timestamptz;
  non_rfc_variant_decision_id constant uuid :=
      '0196f300-1111-7111-0111-111111111177';
BEGIN
  IF uuid_extract_version(non_rfc_variant_decision_id) IS NOT NULL THEN
    RAISE EXCEPTION
      'non-RFC UUID fixture unexpectedly reports a version: %',
      uuid_extract_version(non_rfc_variant_decision_id);
  END IF;

  SELECT
      recheck_record.data_management_assessment_projection_id,
      recheck_record.trigger_evidence_acceptance_id,
      recheck_record.requested_at
    INTO projection_id, acceptance_id, request_time
    FROM architecture_core.assessment_recheck_request AS recheck_record
    JOIN architecture_core.data_management_assessment_projection AS projection_record
      ON projection_record.tenant_record_id = recheck_record.tenant_record_id
     AND projection_record.data_management_assessment_projection_id =
         recheck_record.data_management_assessment_projection_id
   WHERE recheck_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND projection_record.superseded_at IS NULL
   ORDER BY recheck_record.recorded_at DESC
   LIMIT 1;

  IF projection_id IS NULL OR acceptance_id IS NULL OR request_time IS NULL THEN
    RAISE EXCEPTION 'active reassessment fixture is unavailable';
  END IF;

  BEGIN
    PERFORM *
      FROM architecture_core.request_data_management_assessment_recheck(
        projection_id,
        acceptance_id,
        non_rfc_variant_decision_id,
        request_time
      );
    RAISE EXCEPTION
      'non-RFC UUID variant reassessment decision was accepted';
  EXCEPTION WHEN check_violation THEN
    IF SQLERRM NOT LIKE '%assessment_recheck_request_decision_uuid_version%' THEN
      RAISE;
    END IF;
  END;
END;
$$;
