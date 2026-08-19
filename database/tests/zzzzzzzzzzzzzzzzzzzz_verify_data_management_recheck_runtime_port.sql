\set ON_ERROR_STOP on

-- The authenticated runtime must reach reassessment only through a tenant-bound
-- command port; it may not depend on a pre-existing session tenant GUC.
RESET ROLE;
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb712',
    false
);

DO $$
DECLARE
  projection_id uuid;
  acceptance_id uuid;
  recheck_id uuid;
  outbox_id uuid;
  next_action text;
BEGIN
  SELECT projection_record.data_management_assessment_projection_id
    INTO projection_id
    FROM architecture_core.data_management_assessment_projection AS projection_record
   WHERE projection_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND projection_record.assessment_result_uri =
         'urn:cwl:tenant_001:data_context:data_management_assessment:0196f200-1111-7111-8111-111111111142'
     AND projection_record.superseded_at IS NULL;

  SELECT acceptance_record.assessment_evidence_acceptance_id
    INTO acceptance_id
    FROM architecture_core.assessment_evidence_acceptance AS acceptance_record
    JOIN architecture_core.assessment_improvement_plan AS plan_record
      ON plan_record.tenant_record_id = acceptance_record.tenant_record_id
     AND plan_record.assessment_improvement_plan_id =
         acceptance_record.assessment_improvement_plan_id
   WHERE acceptance_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND plan_record.data_management_assessment_projection_id = projection_id;

  SELECT
      result.assessment_recheck_request_id,
      result.outbox_event_id,
      result.next_action
    INTO recheck_id, outbox_id, next_action
    FROM architecture_core.request_data_management_assessment_recheck_for_tenant(
      '0195d145-64e8-7f4f-8a23-a0cc784cb711',
      projection_id,
      acceptance_id,
      '0196f300-1111-7111-8111-111111111169',
      '2026-08-19T00:30:00Z'
    ) AS result;

  IF recheck_id IS NULL
     OR outbox_id IS NULL
     OR next_action IS DISTINCT FROM 'await_assessment_recheck' THEN
    RAISE EXCEPTION
      'runtime reassessment port did not preserve the idempotent buyer receipt';
  END IF;
END;
$$;

DO $$
BEGIN
  IF EXISTS (
      SELECT 1
        FROM pg_catalog.pg_roles
       WHERE rolname = 'ea_runtime'
  ) AND NOT pg_catalog.has_function_privilege(
      'ea_runtime',
      'architecture_core.request_data_management_assessment_recheck_for_tenant(uuid,uuid,uuid,uuid,timestamptz)',
      'EXECUTE'
  ) THEN
    RAISE EXCEPTION 'ea_runtime cannot execute the reassessment command port';
  END IF;
END;
$$;
