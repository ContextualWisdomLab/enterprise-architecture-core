\set ON_ERROR_STOP on

-- Regression acceptance for closing an assessment gap only after Semantic Data
-- Portal evidence with an acceptable truth status is received through migration 0036.

RESET ROLE;
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

INSERT INTO architecture_core.projection_receipt (
    tenant_record_id,
    projection_receipt_id,
    source_system_code,
    event_identifier,
    event_type_code,
    source_reference_uri,
    source_truth_status_code,
    payload_sha256,
    received_at,
    recorded_at,
    processing_status_code
)
VALUES (
    current_setting('app.tenant_record_id')::uuid,
    '0196f200-1111-7111-8111-111111111131',
    'semantic_data_portal',
    '0196f200-1111-7111-8111-111111111132',
    'org.contextualwisdomlab.data_context.assessment_evidence.v1',
    'urn:cwl:tenant_001:data_context:assessment_evidence:0196f200-1111-7111-8111-111111111133',
    'observed',
    repeat('3', 64),
    '2026-08-19T00:00:00Z',
    '2026-08-19T00:00:00Z',
    'processed'
),
(
    current_setting('app.tenant_record_id')::uuid,
    '0196f200-1111-7111-8111-111111111134',
    'pg_erd_cloud',
    '0196f200-1111-7111-8111-111111111135',
    'org.contextualwisdomlab.data_context.assessment_evidence.v1',
    'urn:cwl:tenant_001:data_context:assessment_evidence:0196f200-1111-7111-8111-111111111136',
    'observed',
    repeat('4', 64),
    '2026-08-19T00:00:01Z',
    '2026-08-19T00:00:01Z',
    'processed'
),
(
    current_setting('app.tenant_record_id')::uuid,
    '0196f200-1111-7111-8111-111111111137',
    'semantic_data_portal',
    '0196f200-1111-7111-8111-111111111138',
    'org.contextualwisdomlab.data_context.assessment_evidence.v1',
    'urn:cwl:tenant_001:data_context:assessment_evidence:0196f200-1111-7111-8111-111111111139',
    'inferred',
    repeat('5', 64),
    '2026-08-19T00:00:02Z',
    '2026-08-19T00:00:02Z',
    'processed'
);

DO $$
DECLARE
  plan_id uuid;
  acceptance_record record;
  replay_record record;
  evidence_outbox_event_id uuid;
  milestone_outbox_event_id uuid;
  accepted_count bigint;
  completed_count bigint;
  history_count bigint;
  milestone_completion_count bigint;
  outbox_count bigint;
BEGIN
  SELECT assessment_improvement_plan_id
    INTO STRICT plan_id
    FROM architecture_core.assessment_improvement_plan
   WHERE tenant_record_id = current_setting('app.tenant_record_id')::uuid
     AND missing_evidence_code = 'ownership_evidence';

  BEGIN
    PERFORM *
      FROM architecture_core.accept_data_management_improvement_evidence(
        plan_id,
        '0196f200-1111-7111-8111-111111111140',
        'urn:cwl:tenant_001:data_context:assessment_evidence:0196f200-1111-7111-8111-111111111141',
        'inferred',
        repeat('5', 64),
        '0196f200-1111-7111-8111-111111111142',
        '2026-08-19T00:10:00Z'
      );
    RAISE EXCEPTION 'inferred assessment evidence was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;

  BEGIN
    PERFORM *
      FROM architecture_core.accept_data_management_improvement_evidence(
        plan_id,
        '0196f200-1111-7111-8111-111111111143',
        'urn:cwl:tenant_001:data_context:assessment_evidence:0196f200-1111-7111-8111-111111111144',
        'observed',
        repeat('9', 64),
        '0196f200-1111-7111-8111-111111111145',
        '2026-08-19T00:10:01Z'
      );
    RAISE EXCEPTION 'assessment evidence with a mismatched receipt digest was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;

  BEGIN
    PERFORM *
      FROM architecture_core.accept_data_management_improvement_evidence(
        plan_id,
        '0196f200-1111-7111-8111-111111111147',
        'urn:cwl:tenant_001:data_context:assessment_evidence:0196f200-1111-7111-8111-111111111148',
        'observed',
        repeat('4', 64),
        '0196f200-1111-7111-8111-111111111150',
        '2026-08-19T00:10:02Z'
      );
    RAISE EXCEPTION 'foreign-authority assessment evidence was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;

  SELECT *
    INTO STRICT acceptance_record
    FROM architecture_core.accept_data_management_improvement_evidence(
      plan_id,
      '0196f200-1111-7111-8111-111111111131',
      'urn:cwl:tenant_001:data_context:assessment_evidence:0196f200-1111-7111-8111-111111111133',
      'observed',
      repeat('3', 64),
      '0196f200-1111-7111-8111-111111111151',
      '2026-08-19T00:10:03Z'
    );

  IF acceptance_record.next_action IS DISTINCT FROM 'request_assessment_recheck' THEN
    RAISE EXCEPTION 'unexpected evidence-closure next action: %', acceptance_record.next_action;
  END IF;

  IF acceptance_record.assessment_evidence_acceptance_id IS NULL
     OR acceptance_record.milestone_completion_record_id IS NULL THEN
    RAISE EXCEPTION 'evidence closure did not return immutable receipt identities';
  END IF;

  SELECT *
    INTO STRICT replay_record
    FROM architecture_core.accept_data_management_improvement_evidence(
      plan_id,
      '0196f200-1111-7111-8111-111111111131',
      'urn:cwl:tenant_001:data_context:assessment_evidence:0196f200-1111-7111-8111-111111111133',
      'observed',
      repeat('3', 64),
      '0196f200-1111-7111-8111-111111111151',
      '2026-08-19T00:10:03Z'
    );

  IF replay_record.assessment_evidence_acceptance_id IS DISTINCT FROM
       acceptance_record.assessment_evidence_acceptance_id
     OR replay_record.milestone_completion_record_id IS DISTINCT FROM
       acceptance_record.milestone_completion_record_id
     OR replay_record.next_action IS DISTINCT FROM acceptance_record.next_action THEN
    RAISE EXCEPTION 'exact evidence-closure replay was not deterministic';
  END IF;

  BEGIN
    PERFORM *
      FROM architecture_core.accept_data_management_improvement_evidence(
        plan_id,
        '0196f200-1111-7111-8111-111111111131',
        'urn:cwl:tenant_001:data_context:assessment_evidence:0196f200-1111-7111-8111-111111111133',
        'observed',
        repeat('3', 64),
        '0196f200-1111-7111-8111-111111111152',
        '2026-08-19T00:10:03Z'
      );
    RAISE EXCEPTION 'conflicting evidence-closure replay was accepted';
  EXCEPTION WHEN unique_violation THEN
    NULL;
  END;

  SELECT count(*)
    INTO accepted_count
    FROM architecture_core.assessment_evidence_acceptance
   WHERE tenant_record_id = current_setting('app.tenant_record_id')::uuid
     AND assessment_improvement_plan_id = plan_id;
  IF accepted_count <> 1 THEN
    RAISE EXCEPTION 'unexpected evidence acceptance count: %', accepted_count;
  END IF;

  SELECT count(*)
    INTO milestone_completion_count
    FROM architecture_core.milestone_completion_record
   WHERE tenant_record_id = current_setting('app.tenant_record_id')::uuid
     AND initiative_milestone_id = acceptance_record.initiative_milestone_id;
  IF milestone_completion_count <> 1 THEN
    RAISE EXCEPTION 'unexpected milestone completion count: %', milestone_completion_count;
  END IF;

  SELECT count(*)
    INTO history_count
    FROM architecture_core.transformation_history_record
   WHERE tenant_record_id = current_setting('app.tenant_record_id')::uuid;
  IF history_count < 1 THEN
    RAISE EXCEPTION 'existing architecture history was unexpectedly removed';
  END IF;

  SELECT count(*)
    INTO completed_count
    FROM architecture_core.initiative_milestone
   WHERE tenant_record_id = current_setting('app.tenant_record_id')::uuid
     AND initiative_milestone_id = acceptance_record.initiative_milestone_id
     AND recorded_at IS NOT NULL;
  IF completed_count <> 1 THEN
    RAISE EXCEPTION 'milestone source row was mutated or removed';
  END IF;

  SELECT event_identifier
    INTO STRICT evidence_outbox_event_id
    FROM architecture_core.outbox_event
   WHERE tenant_record_id = current_setting('app.tenant_record_id')::uuid
     AND causation_event_id = '0196f200-1111-7111-8111-111111111151'
     AND event_type = 'org.contextualwisdomlab.ea.data_management.evidence_accepted.v1';

  SELECT count(*)
    INTO outbox_count
    FROM architecture_core.outbox_event
   WHERE tenant_record_id = current_setting('app.tenant_record_id')::uuid
     AND causation_event_id = '0196f200-1111-7111-8111-111111111151'
     AND event_type = 'org.contextualwisdomlab.ea.data_management.evidence_accepted.v1';
  IF outbox_count <> 1 THEN
    RAISE EXCEPTION 'unexpected evidence-accepted outbox count: %', outbox_count;
  END IF;

  SELECT event_identifier
    INTO STRICT milestone_outbox_event_id
    FROM architecture_core.outbox_event
   WHERE tenant_record_id = current_setting('app.tenant_record_id')::uuid
     AND causation_event_id = evidence_outbox_event_id
     AND event_type = 'org.contextualwisdomlab.ea.data_management.milestone_completed.v1';

  SELECT count(*)
    INTO outbox_count
    FROM architecture_core.outbox_event
   WHERE tenant_record_id = current_setting('app.tenant_record_id')::uuid
     AND causation_event_id = evidence_outbox_event_id
     AND event_type = 'org.contextualwisdomlab.ea.data_management.milestone_completed.v1';
  IF outbox_count <> 1 THEN
    RAISE EXCEPTION 'unexpected milestone-completed outbox count: %', outbox_count;
  END IF;

  IF milestone_outbox_event_id IS NULL THEN
    RAISE EXCEPTION 'milestone completion event identity was not returned';
  END IF;
END;
$$;
