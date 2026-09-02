BEGIN;

CREATE OR REPLACE FUNCTION architecture_core.create_data_management_improvement_plan(
    requested_assessment_projection_id uuid,
    requested_missing_evidence_code text,
    requested_decision_request_id uuid,
    requested_target_capability_object_id uuid,
    requested_accountable_organization_object_id uuid,
    requested_initiative_code text,
    requested_initiative_title text,
    requested_milestone_code text,
    requested_milestone_title text,
    requested_due_at timestamptz,
    requested_funding_reference text
)
RETURNS TABLE (
    assessment_improvement_plan_id uuid,
    remediation_initiative_id uuid,
    initiative_milestone_id uuid,
    outbox_event_id uuid
)
LANGUAGE plpgsql
VOLATILE
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
  active_tenant_id uuid;
  source_result_uri text;
  source_recorded_at timestamptz;
  source_truth_status_code text;
  source_superseded_at timestamptz;
  source_readiness_code text;
  existing_plan architecture_core.assessment_improvement_plan%ROWTYPE;
  existing_initiative architecture_core.remediation_initiative%ROWTYPE;
  existing_milestone architecture_core.initiative_milestone%ROWTYPE;
  existing_event_id uuid;
  inserted_plan_id uuid;
  inserted_initiative_id uuid;
  inserted_milestone_id uuid;
  inserted_event_id uuid;
BEGIN
  active_tenant_id := architecture_core.current_tenant_id();
  IF active_tenant_id IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'verified tenant context is required for assessment improvement planning';
  END IF;

  IF requested_assessment_projection_id IS NULL
     OR requested_missing_evidence_code IS NULL
     OR requested_decision_request_id IS NULL
     OR requested_target_capability_object_id IS NULL
     OR requested_accountable_organization_object_id IS NULL
     OR requested_initiative_code IS NULL
     OR requested_initiative_title IS NULL
     OR requested_milestone_code IS NULL
     OR requested_milestone_title IS NULL
     OR requested_due_at IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'assessment improvement planning requires source gap, decision, accountability, initiative, milestone, and due time';
  END IF;

  IF uuid_extract_version(requested_assessment_projection_id) <> 7
     OR uuid_extract_version(requested_decision_request_id) <> 7
     OR uuid_extract_version(requested_target_capability_object_id) <> 7
     OR uuid_extract_version(requested_accountable_organization_object_id) <> 7
     OR requested_missing_evidence_code !~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'
     OR length(requested_missing_evidence_code) NOT BETWEEN 2 AND 128
     OR requested_initiative_code !~ '^[a-z][a-z0-9]+(?:_[a-z0-9]+)*$'
     OR length(requested_initiative_code) > 128
     OR length(btrim(requested_initiative_title)) NOT BETWEEN 1 AND 512
     OR requested_milestone_code !~ '^[a-z][a-z0-9]+(?:_[a-z0-9]+)*$'
     OR length(requested_milestone_code) > 128
     OR length(btrim(requested_milestone_title)) NOT BETWEEN 1 AND 512
     OR (
        requested_funding_reference IS NOT NULL
        AND length(requested_funding_reference) NOT BETWEEN 1 AND 2048
     ) THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'assessment improvement decision fields are invalid or exceed bounds';
  END IF;

  -- Replay is resolved before current-state preconditions. Once the decision and
  -- its outbox evidence committed, a later source supersession must not turn an
  -- exact transport retry into a new business decision or an availability error.
  SELECT plan_record.*
    INTO existing_plan
    FROM architecture_core.assessment_improvement_plan AS plan_record
   WHERE plan_record.tenant_record_id = active_tenant_id
     AND plan_record.decision_request_id = requested_decision_request_id;

  IF existing_plan.assessment_improvement_plan_id IS NOT NULL THEN
    SELECT initiative_record.*
      INTO existing_initiative
      FROM architecture_core.remediation_initiative AS initiative_record
     WHERE initiative_record.tenant_record_id = active_tenant_id
       AND initiative_record.remediation_initiative_id =
           existing_plan.remediation_initiative_id;

    SELECT milestone_record.*
      INTO existing_milestone
      FROM architecture_core.initiative_milestone AS milestone_record
     WHERE milestone_record.tenant_record_id = active_tenant_id
       AND milestone_record.initiative_milestone_id =
           existing_plan.initiative_milestone_id;

    IF existing_plan.data_management_assessment_projection_id IS DISTINCT FROM
           requested_assessment_projection_id
       OR existing_plan.missing_evidence_code IS DISTINCT FROM
           requested_missing_evidence_code
       OR existing_plan.target_capability_object_id IS DISTINCT FROM
           requested_target_capability_object_id
       OR existing_plan.accountable_organization_object_id IS DISTINCT FROM
           requested_accountable_organization_object_id
       OR existing_plan.funding_reference IS DISTINCT FROM requested_funding_reference
       OR existing_initiative.initiative_code IS DISTINCT FROM requested_initiative_code
       OR existing_initiative.initiative_title IS DISTINCT FROM requested_initiative_title
       OR existing_milestone.milestone_code IS DISTINCT FROM requested_milestone_code
       OR existing_milestone.milestone_title IS DISTINCT FROM requested_milestone_title
       OR existing_milestone.target_at IS DISTINCT FROM requested_due_at THEN
      RAISE EXCEPTION USING
        ERRCODE = '23505',
        MESSAGE = 'decision request id already represents different improvement-plan meaning';
    END IF;

    SELECT event_record.outbox_event_id
      INTO existing_event_id
      FROM architecture_core.outbox_event AS event_record
     WHERE event_record.tenant_record_id = active_tenant_id
       AND event_record.decision_request_id = requested_decision_request_id
       AND event_record.event_type_code =
           'org.contextualwisdomlab.ea.data_management.improvement_initiative_created.v1';

    IF existing_event_id IS NULL THEN
      RAISE EXCEPTION USING
        ERRCODE = '23514',
        MESSAGE = 'improvement-plan evidence exists without transactional outbox evidence';
    END IF;

    RETURN QUERY
    SELECT
      existing_plan.assessment_improvement_plan_id,
      existing_plan.remediation_initiative_id,
      existing_plan.initiative_milestone_id,
      existing_event_id;
    RETURN;
  END IF;

  SELECT
      projection_record.assessment_result_uri,
      projection_record.source_recorded_at,
      projection_record.truth_status_code,
      projection_record.superseded_at,
      projection_record.readiness_code
    INTO
      source_result_uri,
      source_recorded_at,
      source_truth_status_code,
      source_superseded_at,
      source_readiness_code
    FROM architecture_core.data_management_assessment_projection AS projection_record
    JOIN architecture_core.assessment_missing_evidence_projection AS missing_record
      ON missing_record.tenant_record_id = projection_record.tenant_record_id
     AND missing_record.data_management_assessment_projection_id =
         projection_record.data_management_assessment_projection_id
     AND missing_record.missing_evidence_code = requested_missing_evidence_code
   WHERE projection_record.tenant_record_id = active_tenant_id
     AND projection_record.data_management_assessment_projection_id =
         requested_assessment_projection_id
   FOR UPDATE OF projection_record;

  IF source_result_uri IS NULL
     OR source_readiness_code IS DISTINCT FROM 'evidence_gap'
     OR source_superseded_at IS NOT NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'improvement planning requires an active projected missing-evidence gap';
  END IF;

  IF requested_due_at <= source_recorded_at THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'improvement milestone must follow the source assessment recording time';
  END IF;

  PERFORM 1
    FROM architecture_core.business_capability AS capability_record
   WHERE capability_record.tenant_record_id = active_tenant_id
     AND capability_record.architecture_object_id =
         requested_target_capability_object_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'target capability is unavailable for the verified tenant';
  END IF;

  PERFORM 1
    FROM architecture_core.organization_unit AS organization_record
   WHERE organization_record.tenant_record_id = active_tenant_id
     AND organization_record.architecture_object_id =
         requested_accountable_organization_object_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'accountable organization is unavailable for the verified tenant';
  END IF;

  INSERT INTO architecture_core.remediation_initiative (
      tenant_record_id,
      initiative_code,
      initiative_title,
      initiative_description,
      valid_from,
      truth_status_code
  ) VALUES (
      active_tenant_id,
      requested_initiative_code,
      requested_initiative_title,
      'Proposed from projected data-management assessment gap: ' ||
          requested_missing_evidence_code,
      source_recorded_at,
      'proposed'
  )
  RETURNING remediation_initiative.remediation_initiative_id
    INTO inserted_initiative_id;

  INSERT INTO architecture_core.initiative_milestone (
      tenant_record_id,
      remediation_initiative_id,
      milestone_code,
      milestone_title,
      milestone_description,
      sequence_number,
      target_at,
      valid_from,
      truth_status_code
  ) VALUES (
      active_tenant_id,
      inserted_initiative_id,
      requested_milestone_code,
      requested_milestone_title,
      'Proposed evidence-closure milestone; requires human authorization before execution.',
      1,
      requested_due_at,
      source_recorded_at,
      'proposed'
  )
  RETURNING initiative_milestone.initiative_milestone_id
    INTO inserted_milestone_id;

  INSERT INTO architecture_core.assessment_improvement_plan (
      tenant_record_id,
      data_management_assessment_projection_id,
      missing_evidence_code,
      decision_request_id,
      target_capability_object_id,
      accountable_organization_object_id,
      remediation_initiative_id,
      initiative_milestone_id,
      funding_reference
  ) VALUES (
      active_tenant_id,
      requested_assessment_projection_id,
      requested_missing_evidence_code,
      requested_decision_request_id,
      requested_target_capability_object_id,
      requested_accountable_organization_object_id,
      inserted_initiative_id,
      inserted_milestone_id,
      requested_funding_reference
  )
  RETURNING assessment_improvement_plan.assessment_improvement_plan_id
    INTO inserted_plan_id;

  INSERT INTO architecture_core.outbox_event (
      tenant_record_id,
      aggregate_object_id,
      architecture_transformation_id,
      event_type_code,
      event_payload_json,
      event_schema_version,
      decision_request_id
  ) VALUES (
      active_tenant_id,
      requested_target_capability_object_id,
      NULL,
      'org.contextualwisdomlab.ea.data_management.improvement_initiative_created.v1',
      pg_catalog.jsonb_build_object(
          'assessment_result_uri', source_result_uri,
          'missing_evidence_code', requested_missing_evidence_code,
          'target_capability_object_id', requested_target_capability_object_id,
          'accountable_organization_object_id',
          requested_accountable_organization_object_id,
          'remediation_initiative_id', inserted_initiative_id,
          'initiative_milestone_id', inserted_milestone_id,
          'decision_request_id', requested_decision_request_id,
          'due_at', requested_due_at,
          'source_truth_status_code', source_truth_status_code,
          'initiative_truth_status_code', 'proposed',
          'next_action', 'review_and_authorize_improvement_initiative'
      ),
      '1.0.0',
      requested_decision_request_id
  )
  RETURNING outbox_event.outbox_event_id
    INTO inserted_event_id;

  RETURN QUERY
  SELECT
    inserted_plan_id,
    inserted_initiative_id,
    inserted_milestone_id,
    inserted_event_id;
END;
$$;

COMMENT ON FUNCTION architecture_core.create_data_management_improvement_plan(
    uuid,
    text,
    uuid,
    uuid,
    uuid,
    text,
    text,
    text,
    text,
    timestamptz,
    text
) IS
'Creates one proposed EA improvement initiative for an active projected data-management evidence gap. Exact UUIDv7 decision replay returns the original plan and transactional outbox receipt even after source supersession; a new decision still requires an active source gap. Source projection truth is preserved and never promoted to authoritative EA truth.';

COMMIT;
