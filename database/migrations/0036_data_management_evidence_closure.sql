BEGIN;

CREATE TABLE architecture_core.assessment_evidence_acceptance (
    tenant_record_id uuid NOT NULL,
    assessment_evidence_acceptance_id uuid NOT NULL DEFAULT uuidv7(),
    assessment_improvement_plan_id uuid NOT NULL,
    projection_receipt_id uuid NOT NULL,
    evidence_uri text NOT NULL,
    evidence_truth_status_code text NOT NULL,
    evidence_sha256 text NOT NULL,
    decision_request_id uuid NOT NULL,
    accepted_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT assessment_evidence_acceptance_primary_key
        PRIMARY KEY (tenant_record_id, assessment_evidence_acceptance_id),
    CONSTRAINT assessment_evidence_acceptance_plan_foreign
        FOREIGN KEY (tenant_record_id, assessment_improvement_plan_id)
        REFERENCES architecture_core.assessment_improvement_plan
            (tenant_record_id, assessment_improvement_plan_id),
    CONSTRAINT assessment_evidence_acceptance_receipt_foreign
        FOREIGN KEY (tenant_record_id, projection_receipt_id)
        REFERENCES architecture_core.projection_receipt
            (tenant_record_id, projection_receipt_id),
    CONSTRAINT assessment_evidence_acceptance_uuid_version
        CHECK (uuid_extract_version(assessment_evidence_acceptance_id) = 7),
    CONSTRAINT assessment_evidence_acceptance_decision_uuid_version
        CHECK (uuid_extract_version(decision_request_id) = 7),
    CONSTRAINT assessment_evidence_acceptance_uri_format
        CHECK (
            evidence_uri ~
            '^urn:cwl:(?=[^:]{2,63}:)[a-z][a-z0-9]+(?:_[a-z0-9]+)*:data_context:assessment_evidence:[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT assessment_evidence_acceptance_truth_allowed
        CHECK (evidence_truth_status_code IN ('authoritative', 'observed')),
    CONSTRAINT assessment_evidence_acceptance_digest_format
        CHECK (evidence_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT assessment_evidence_acceptance_plan_unique
        UNIQUE (tenant_record_id, assessment_improvement_plan_id),
    CONSTRAINT assessment_evidence_acceptance_decision_unique
        UNIQUE (tenant_record_id, decision_request_id)
);

CREATE TABLE architecture_core.milestone_completion_record (
    tenant_record_id uuid NOT NULL,
    milestone_completion_record_id uuid NOT NULL DEFAULT uuidv7(),
    initiative_milestone_id uuid NOT NULL,
    assessment_evidence_acceptance_id uuid NOT NULL,
    completed_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT milestone_completion_record_primary_key
        PRIMARY KEY (tenant_record_id, milestone_completion_record_id),
    CONSTRAINT milestone_completion_record_milestone_foreign
        FOREIGN KEY (tenant_record_id, initiative_milestone_id)
        REFERENCES architecture_core.initiative_milestone
            (tenant_record_id, initiative_milestone_id),
    CONSTRAINT milestone_completion_record_acceptance_foreign
        FOREIGN KEY (tenant_record_id, assessment_evidence_acceptance_id)
        REFERENCES architecture_core.assessment_evidence_acceptance
            (tenant_record_id, assessment_evidence_acceptance_id),
    CONSTRAINT milestone_completion_record_uuid_version
        CHECK (uuid_extract_version(milestone_completion_record_id) = 7),
    CONSTRAINT milestone_completion_record_milestone_unique
        UNIQUE (tenant_record_id, initiative_milestone_id),
    CONSTRAINT milestone_completion_record_acceptance_unique
        UNIQUE (tenant_record_id, assessment_evidence_acceptance_id)
);

ALTER TABLE architecture_core.assessment_evidence_acceptance
    ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.assessment_evidence_acceptance
    FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy
ON architecture_core.assessment_evidence_acceptance
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

ALTER TABLE architecture_core.milestone_completion_record
    ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.milestone_completion_record
    FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy
ON architecture_core.milestone_completion_record
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

CREATE FUNCTION architecture_core.reject_data_management_closure_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION USING
    ERRCODE = '23514',
    MESSAGE = 'accepted data-management evidence and milestone completion history is immutable';
END;
$$;

CREATE TRIGGER assessment_evidence_acceptance_history_guard
BEFORE UPDATE OR DELETE
ON architecture_core.assessment_evidence_acceptance
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_data_management_closure_mutation();

CREATE TRIGGER milestone_completion_record_history_guard
BEFORE UPDATE OR DELETE
ON architecture_core.milestone_completion_record
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_data_management_closure_mutation();

CREATE FUNCTION architecture_core.accept_data_management_improvement_evidence(
    requested_assessment_improvement_plan_id uuid,
    requested_projection_receipt_id uuid,
    requested_evidence_uri text,
    requested_evidence_truth_status_code text,
    requested_evidence_sha256 text,
    requested_decision_request_id uuid,
    requested_accepted_at timestamptz
)
RETURNS TABLE (
    assessment_evidence_acceptance_id uuid,
    milestone_completion_record_id uuid,
    evidence_outbox_event_id uuid,
    milestone_outbox_event_id uuid,
    next_action text
)
LANGUAGE plpgsql
VOLATILE
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
  active_tenant_id uuid;
  active_tenant_code text;
  evidence_identifier_text text;
  receipt_source_uri text;
  receipt_event_identifier text;
  receipt_status_code text;
  receipt_processed_at timestamptz;
  source_plan architecture_core.assessment_improvement_plan%ROWTYPE;
  existing_acceptance architecture_core.assessment_evidence_acceptance%ROWTYPE;
  existing_completion architecture_core.milestone_completion_record%ROWTYPE;
  existing_evidence_event architecture_core.outbox_event%ROWTYPE;
  existing_milestone_event architecture_core.outbox_event%ROWTYPE;
  existing_derived_event_count integer;
  inserted_acceptance_id uuid;
  inserted_completion_id uuid;
  inserted_evidence_event_id uuid;
  inserted_milestone_event_id uuid;
  resolved_next_action text;
BEGIN
  active_tenant_id := architecture_core.current_tenant_id();
  IF active_tenant_id IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'verified tenant context is required for data-management evidence acceptance';
  END IF;

  IF requested_assessment_improvement_plan_id IS NULL
     OR requested_projection_receipt_id IS NULL
     OR requested_evidence_uri IS NULL
     OR requested_evidence_truth_status_code IS NULL
     OR requested_evidence_sha256 IS NULL
     OR requested_decision_request_id IS NULL
     OR requested_accepted_at IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'evidence acceptance requires plan, receipt, evidence identity, truth, digest, decision, and acceptance time';
  END IF;

  IF uuid_extract_version(requested_assessment_improvement_plan_id) <> 7
     OR uuid_extract_version(requested_projection_receipt_id) <> 7
     OR uuid_extract_version(requested_decision_request_id) <> 7
     OR requested_evidence_truth_status_code NOT IN ('authoritative', 'observed')
     OR requested_evidence_sha256 !~ '^[0-9a-f]{64}$' THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'evidence acceptance identifiers, truth status, or digest are invalid';
  END IF;

  SELECT tenant_record.tenant_code
    INTO active_tenant_code
    FROM architecture_core.tenant_record AS tenant_record
   WHERE tenant_record.tenant_record_id = active_tenant_id;

  evidence_identifier_text := split_part(requested_evidence_uri, ':', 6);
  IF active_tenant_code IS NULL
     OR array_length(string_to_array(requested_evidence_uri, ':'), 1) <> 6
     OR split_part(requested_evidence_uri, ':', 1) IS DISTINCT FROM 'urn'
     OR split_part(requested_evidence_uri, ':', 2) IS DISTINCT FROM 'cwl'
     OR split_part(requested_evidence_uri, ':', 3) IS DISTINCT FROM active_tenant_code
     OR split_part(requested_evidence_uri, ':', 4) IS DISTINCT FROM 'data_context'
     OR split_part(requested_evidence_uri, ':', 5) IS DISTINCT FROM 'assessment_evidence'
     OR evidence_identifier_text !~
        '^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
     OR uuid_extract_version(evidence_identifier_text::uuid) <> 7 THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'evidence URI must be a tenant-local canonical UUIDv7 Data Context assessment-evidence reference';
  END IF;

  -- Resolve exact committed replay before current-state checks. The decision ID
  -- is transport idempotency evidence; changing any semantic field fails closed.
  SELECT acceptance_record.*
    INTO existing_acceptance
    FROM architecture_core.assessment_evidence_acceptance AS acceptance_record
   WHERE acceptance_record.tenant_record_id = active_tenant_id
     AND acceptance_record.decision_request_id = requested_decision_request_id;

  IF existing_acceptance.assessment_evidence_acceptance_id IS NOT NULL THEN
    IF existing_acceptance.assessment_improvement_plan_id IS DISTINCT FROM
           requested_assessment_improvement_plan_id
       OR existing_acceptance.projection_receipt_id IS DISTINCT FROM
           requested_projection_receipt_id
       OR existing_acceptance.evidence_uri IS DISTINCT FROM requested_evidence_uri
       OR existing_acceptance.evidence_truth_status_code IS DISTINCT FROM
           requested_evidence_truth_status_code
       OR existing_acceptance.evidence_sha256 IS DISTINCT FROM requested_evidence_sha256
       OR existing_acceptance.accepted_at IS DISTINCT FROM requested_accepted_at THEN
      RAISE EXCEPTION USING
        ERRCODE = '23505',
        MESSAGE = 'decision request id already represents different evidence-acceptance meaning';
    END IF;

    SELECT completion_record.*
      INTO existing_completion
      FROM architecture_core.milestone_completion_record AS completion_record
     WHERE completion_record.tenant_record_id = active_tenant_id
       AND completion_record.assessment_evidence_acceptance_id =
           existing_acceptance.assessment_evidence_acceptance_id;

    SELECT event_record.*
      INTO existing_evidence_event
      FROM architecture_core.outbox_event AS event_record
     WHERE event_record.tenant_record_id = active_tenant_id
       AND event_record.decision_request_id = requested_decision_request_id
       AND event_record.event_type_code =
           'org.contextualwisdomlab.ea.data_management.evidence_accepted.v1';

    SELECT event_record.*
      INTO existing_milestone_event
      FROM architecture_core.outbox_event AS event_record
     WHERE event_record.tenant_record_id = active_tenant_id
       AND event_record.causation_event_id = existing_evidence_event.outbox_event_id
       AND event_record.event_type_code =
           'org.contextualwisdomlab.ea.data_management.milestone_completed.v1';

    SELECT count(*)
      INTO existing_derived_event_count
      FROM architecture_core.outbox_event AS event_record
     WHERE event_record.tenant_record_id = active_tenant_id
       AND event_record.causation_event_id = existing_evidence_event.outbox_event_id
       AND event_record.event_type_code =
           'org.contextualwisdomlab.ea.data_management.milestone_completed.v1';

    resolved_next_action := existing_evidence_event.event_payload_json ->> 'next_action';
    IF existing_completion.milestone_completion_record_id IS NULL
       OR existing_evidence_event.outbox_event_id IS NULL
       OR existing_milestone_event.outbox_event_id IS NULL
       OR existing_derived_event_count <> 1
       OR resolved_next_action IS NULL THEN
      RAISE EXCEPTION USING
        ERRCODE = '23514',
        MESSAGE = 'evidence acceptance exists without complete transactional closure evidence';
    END IF;

    RETURN QUERY
    SELECT
      existing_acceptance.assessment_evidence_acceptance_id,
      existing_completion.milestone_completion_record_id,
      existing_evidence_event.outbox_event_id,
      existing_milestone_event.outbox_event_id,
      resolved_next_action;
    RETURN;
  END IF;

  SELECT plan_record.*
    INTO source_plan
    FROM architecture_core.assessment_improvement_plan AS plan_record
   WHERE plan_record.tenant_record_id = active_tenant_id
     AND plan_record.assessment_improvement_plan_id =
         requested_assessment_improvement_plan_id
   FOR UPDATE;

  IF source_plan.assessment_improvement_plan_id IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'assessment improvement plan is unavailable for the verified tenant';
  END IF;

  IF EXISTS (
      SELECT 1
        FROM architecture_core.assessment_evidence_acceptance AS acceptance_record
       WHERE acceptance_record.tenant_record_id = active_tenant_id
         AND acceptance_record.assessment_improvement_plan_id =
             requested_assessment_improvement_plan_id
  ) THEN
    RAISE EXCEPTION USING
      ERRCODE = '23505',
      MESSAGE = 'assessment improvement plan already has accepted evidence under another decision';
  END IF;

  SELECT
      receipt_record.event_source_uri,
      receipt_record.event_identifier,
      receipt_record.processing_status_code,
      receipt_record.processed_at
    INTO
      receipt_source_uri,
      receipt_event_identifier,
      receipt_status_code,
      receipt_processed_at
    FROM architecture_core.projection_receipt AS receipt_record
   WHERE receipt_record.tenant_record_id = active_tenant_id
     AND receipt_record.projection_receipt_id = requested_projection_receipt_id;

  IF receipt_source_uri IS NULL
     OR receipt_source_uri IS DISTINCT FROM
        'urn:cwl:' || active_tenant_code || ':semantic_data_portal'
     OR receipt_event_identifier IS DISTINCT FROM evidence_identifier_text
     OR receipt_status_code IS DISTINCT FROM 'processed'
     OR receipt_processed_at IS NULL
     OR receipt_processed_at > requested_accepted_at THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'accepted evidence requires a processed tenant-local Semantic Data Portal receipt matching the evidence UUIDv7 identity';
  END IF;

  INSERT INTO architecture_core.assessment_evidence_acceptance (
      tenant_record_id,
      assessment_improvement_plan_id,
      projection_receipt_id,
      evidence_uri,
      evidence_truth_status_code,
      evidence_sha256,
      decision_request_id,
      accepted_at
  ) VALUES (
      active_tenant_id,
      requested_assessment_improvement_plan_id,
      requested_projection_receipt_id,
      requested_evidence_uri,
      requested_evidence_truth_status_code,
      requested_evidence_sha256,
      requested_decision_request_id,
      requested_accepted_at
  )
  RETURNING assessment_evidence_acceptance.assessment_evidence_acceptance_id
    INTO inserted_acceptance_id;

  INSERT INTO architecture_core.milestone_completion_record (
      tenant_record_id,
      initiative_milestone_id,
      assessment_evidence_acceptance_id,
      completed_at
  ) VALUES (
      active_tenant_id,
      source_plan.initiative_milestone_id,
      inserted_acceptance_id,
      requested_accepted_at
  )
  RETURNING milestone_completion_record.milestone_completion_record_id
    INTO inserted_completion_id;

  IF EXISTS (
      SELECT 1
        FROM architecture_core.assessment_missing_evidence_projection AS missing_record
       WHERE missing_record.tenant_record_id = active_tenant_id
         AND missing_record.data_management_assessment_projection_id =
             source_plan.data_management_assessment_projection_id
         AND NOT EXISTS (
             SELECT 1
               FROM architecture_core.assessment_improvement_plan AS plan_record
               JOIN architecture_core.assessment_evidence_acceptance AS acceptance_record
                 ON acceptance_record.tenant_record_id = plan_record.tenant_record_id
                AND acceptance_record.assessment_improvement_plan_id =
                    plan_record.assessment_improvement_plan_id
              WHERE plan_record.tenant_record_id = missing_record.tenant_record_id
                AND plan_record.data_management_assessment_projection_id =
                    missing_record.data_management_assessment_projection_id
                AND plan_record.missing_evidence_code = missing_record.missing_evidence_code
         )
  ) THEN
    resolved_next_action := 'close_remaining_assessment_gap';
  ELSE
    resolved_next_action := 'request_assessment_recheck';
  END IF;

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
      source_plan.target_capability_object_id,
      NULL,
      'org.contextualwisdomlab.ea.data_management.evidence_accepted.v1',
      pg_catalog.jsonb_build_object(
          'assessment_improvement_plan_id', requested_assessment_improvement_plan_id,
          'data_management_assessment_projection_id',
          source_plan.data_management_assessment_projection_id,
          'missing_evidence_code', source_plan.missing_evidence_code,
          'assessment_evidence_acceptance_id', inserted_acceptance_id,
          'evidence_uri', requested_evidence_uri,
          'evidence_truth_status_code', requested_evidence_truth_status_code,
          'evidence_sha256', requested_evidence_sha256,
          'accepted_at', requested_accepted_at,
          'next_action', resolved_next_action
      ),
      '1.0.0',
      requested_decision_request_id
  )
  RETURNING outbox_event.outbox_event_id
    INTO inserted_evidence_event_id;

  INSERT INTO architecture_core.outbox_event (
      tenant_record_id,
      aggregate_object_id,
      architecture_transformation_id,
      event_type_code,
      event_payload_json,
      event_schema_version,
      causation_event_id,
      decision_request_id
  ) VALUES (
      active_tenant_id,
      source_plan.target_capability_object_id,
      NULL,
      'org.contextualwisdomlab.ea.data_management.milestone_completed.v1',
      pg_catalog.jsonb_build_object(
          'assessment_improvement_plan_id', requested_assessment_improvement_plan_id,
          'initiative_milestone_id', source_plan.initiative_milestone_id,
          'milestone_completion_record_id', inserted_completion_id,
          'assessment_evidence_acceptance_id', inserted_acceptance_id,
          'completed_at', requested_accepted_at,
          'next_action', resolved_next_action
      ),
      '1.0.0',
      inserted_evidence_event_id,
      NULL
  )
  RETURNING outbox_event.outbox_event_id
    INTO inserted_milestone_event_id;

  RETURN QUERY
  SELECT
    inserted_acceptance_id,
    inserted_completion_id,
    inserted_evidence_event_id,
    inserted_milestone_event_id,
    resolved_next_action;
END;
$$;

COMMENT ON TABLE architecture_core.assessment_evidence_acceptance IS
'Append-only EA receipt that binds one accountable data-management improvement gap to accepted Data/AI Context evidence without copying source-system authority.';

COMMENT ON TABLE architecture_core.milestone_completion_record IS
'Append-only completion evidence for an immutable initiative milestone; completion never rewrites the milestone definition.';

COMMENT ON FUNCTION architecture_core.accept_data_management_improvement_evidence(
    uuid,
    uuid,
    text,
    text,
    text,
    uuid,
    timestamptz
) IS
'Accepts only authoritative or observed tenant-local Semantic Data Portal assessment evidence, records immutable milestone completion and transactional outbox evidence atomically, returns an assessment-recheck next action when all projected gaps are closed, and makes exact UUIDv7 decision replay deterministic.';

COMMIT;
