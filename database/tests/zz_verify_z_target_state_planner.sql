\set ON_ERROR_STOP on

-- Buyer acceptance for the joined Technology Change Impact & Target-State
-- Planner. This test intentionally lands before migration 0020 so the first
-- branch commit is RED at the missing deterministic decision projection.

DO $$
BEGIN
  IF to_regprocedure(
      'architecture_core.project_technology_target_state_plan(uuid,timestamptz,timestamptz,integer)'
     ) IS NULL THEN
    RAISE EXCEPTION 'technology target-state planner is missing';
  END IF;
END;
$$;

SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

-- Bind the technology-impacted application into the already governed target
-- scenario without copying external product state into EA authority.
INSERT INTO architecture_core.scenario_object_delta (
    tenant_record_id,
    scenario_object_delta_id,
    architecture_scenario_id,
    sequence_number,
    architecture_object_id,
    desired_presence_code,
    effective_from,
    recorded_at,
    truth_status_code,
    evidence_record_id
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196f300-1000-7100-8100-000000000001',
    '0196e002-1111-7111-8111-111111111111',
    1,
    '0196f130-3333-7333-8333-333333333333',
    'present',
    '2026-08-25T00:00:00Z',
    '2026-08-25T00:01:00Z',
    'authoritative',
    '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
);

-- Add receipt-bound physical-schema evidence for that impacted application.
INSERT INTO architecture_core.projection_receipt (
    tenant_record_id,
    projection_receipt_id,
    event_source_uri,
    event_identifier,
    payload_sha256,
    schema_version,
    received_at,
    processed_at,
    processing_status_code
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196f300-2000-7200-8200-000000000001',
    'urn:cwl:tenant_001:pg_erd_cloud',
    '0196f300-2000-7200-8200-000000000101',
    repeat('a', 64),
    'context-assertion/v1',
    '2026-08-25T00:00:00Z',
    '2026-08-25T00:01:00Z',
    'processed'
);

INSERT INTO architecture_core.external_context_reference (
    tenant_record_id,
    external_context_reference_id,
    reference_authority_code,
    canonical_object_uri,
    external_object_kind_code,
    recorded_at
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196f300-3000-7300-8300-000000000001',
    'pg_erd_cloud',
    'urn:cwl:tenant_001:pg_erd_cloud:database_schema:0196f300-3000-7300-8300-000000000101',
    'database_schema',
    '2026-08-25T00:01:30Z'
);

INSERT INTO architecture_core.application_context_projection (
    tenant_record_id,
    application_context_projection_id,
    application_object_id,
    external_context_reference_id,
    projection_receipt_id,
    projection_relation_code,
    truth_status_code,
    valid_from,
    recorded_at
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196f300-4000-7400-8400-000000000001',
    '0196f130-3333-7333-8333-333333333333',
    '0196f300-3000-7300-8300-000000000001',
    '0196f300-2000-7200-8200-000000000001',
    'depends_on',
    'observed',
    '2026-08-25T00:00:00Z',
    '2026-08-25T00:02:00Z'
);

DO $$
DECLARE
  planned_row record;
BEGIN
  SELECT *
    INTO planned_row
    FROM architecture_core.project_technology_target_state_plan(
        '0196f100-1111-7111-8111-111111111111',
        '2026-09-15T00:00:00Z',
        '2026-09-15T00:00:00Z',
        180
    )
   WHERE application_object_id = '0196f130-3333-7333-8333-333333333333'
     AND external_object_kind_code = 'database_schema';

  IF planned_row.impact_status_code <> 'lifecycle_change_soon'
     OR planned_row.impact_evidence_state_code <> 'complete'
     OR planned_row.external_truth_status_code <> 'observed'
     OR planned_row.remediation_initiative_code <> 'retire_legacy_database'
     OR planned_row.scenario_code <> 'approved_database_target'
     OR planned_row.transformation_state_code <> 'proposed'
     OR planned_row.decision_readiness_code <> 'target_state_pending_approval'
     OR planned_row.recommended_action_code <> 'approve_target_state' THEN
    RAISE EXCEPTION 'proposed target-state plan was projected incorrectly';
  END IF;
END;
$$;

DO $$
DECLARE
  planned_row record;
BEGIN
  SELECT *
    INTO planned_row
    FROM architecture_core.project_technology_target_state_plan(
        '0196f100-1111-7111-8111-111111111111',
        '2027-02-01T00:00:00Z',
        '2027-02-01T00:00:00Z',
        180
    )
   WHERE application_object_id = '0196f130-3333-7333-8333-333333333333'
     AND external_object_kind_code = 'database_schema';

  IF planned_row.impact_status_code <> 'end_of_life'
     OR planned_row.transformation_state_code <> 'started'
     OR planned_row.decision_readiness_code <> 'execution_in_progress'
     OR planned_row.recommended_action_code <> 'monitor_transformation' THEN
    RAISE EXCEPTION 'started transformation did not become an execution action';
  END IF;
END;
$$;

DO $$
DECLARE
  planned_row record;
BEGIN
  SELECT *
    INTO planned_row
    FROM architecture_core.project_technology_target_state_plan(
        '0196f100-1111-7111-8111-111111111111',
        '2027-07-01T00:00:00Z',
        '2027-07-01T00:00:00Z',
        180
    )
   WHERE application_object_id = '0196f130-3333-7333-8333-333333333333'
     AND external_object_kind_code = 'database_schema';

  IF planned_row.transformation_state_code <> 'completed'
     OR planned_row.decision_readiness_code <> 'completed'
     OR planned_row.recommended_action_code <> 'verify_target_state' THEN
    RAISE EXCEPTION 'completed transformation lacks the buyer verification action';
  END IF;
END;
$$;

DO $$
BEGIN
  BEGIN
    PERFORM *
      FROM architecture_core.project_technology_target_state_plan(
          '0196f100-1111-7111-8111-111111111111',
          NULL,
          '2027-02-01T00:00:00Z',
          180
      );
    RAISE EXCEPTION 'NULL planner valid-time cutoff was accepted';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

-- A historical planner read must still use a scenario that was active at the
-- requested recording cutoff after that scenario was superseded later.
BEGIN;
UPDATE architecture_core.architecture_scenario
   SET superseded_at = '2027-08-01T00:00:00Z'
 WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
   AND architecture_scenario_id = '0196e002-1111-7111-8111-111111111111';

DO $$
DECLARE
  historical_row record;
BEGIN
  SELECT *
    INTO historical_row
    FROM architecture_core.project_technology_target_state_plan(
        '0196f100-1111-7111-8111-111111111111',
        '2027-07-01T00:00:00Z',
        '2027-07-15T00:00:00Z',
        180
    )
   WHERE application_object_id = '0196f130-3333-7333-8333-333333333333'
     AND external_object_kind_code = 'database_schema';

  IF historical_row.scenario_code <> 'approved_database_target'
     OR historical_row.transformation_state_code <> 'completed'
     OR historical_row.recommended_action_code <> 'verify_target_state' THEN
    RAISE EXCEPTION 'historical target-state plan was not reproducible';
  END IF;
END;
$$;

ROLLBACK;

SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb712',
    false
);

DO $$
BEGIN
  BEGIN
    PERFORM *
      FROM architecture_core.project_technology_target_state_plan(
          '0196f100-1111-7111-8111-111111111111',
          '2027-02-01T00:00:00Z',
          '2027-02-01T00:00:00Z',
          180
      );
    RAISE EXCEPTION 'cross-tenant technology plan was visible';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;
