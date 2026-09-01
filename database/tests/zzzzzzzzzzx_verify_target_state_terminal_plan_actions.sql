\set ON_ERROR_STOP on

BEGIN;

-- Regression: the canonical buyer planner must understand the terminal states
-- introduced after migration 0020. A verified target must route through the
-- evidence-freshness monitoring boundary before the buyer may continue; a later
-- gap_detected observation must route directly to governed replanning.

SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

-- This suite intentionally keeps an older transformation for the same scenario
-- and remediation initiative so historical planner acceptance can exercise the
-- started/completed lifecycle. Isolate this terminal-state fixture by
-- superseding that competing transformation only inside this transaction; the
-- final ROLLBACK restores it for the later historical planner test.
UPDATE architecture_core.architecture_transformation
   SET superseded_at = clock_timestamp()
 WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
   AND architecture_transformation_id = '0196e010-1111-7111-8111-111111111111'
   AND superseded_at IS NULL;

-- Keep this acceptance file self-contained. The neighboring planner fixture is
-- intentionally rolled back, so relying on its rows would make NULL planner
-- results pass the comparisons below without exercising terminal routing.
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
        '2027-02-02T00:00:00Z',
        clock_timestamp(),
        180
    )
   WHERE application_object_id = '0196f130-3333-7333-8333-333333333333'
     AND external_object_kind_code = 'database_schema';

  IF planned_row.transformation_state_code <> 'verified'
     OR planned_row.decision_readiness_code <> 'target_state_verified'
     OR planned_row.recommended_action_code <> 'monitor_target_state' THEN
    RAISE EXCEPTION 'verified target state bypasses freshness monitoring in the canonical planner';
  END IF;
END;
$$;

INSERT INTO architecture_core.evidence_record (
    tenant_record_id,
    evidence_record_id,
    evidence_uri,
    sha256_digest,
    source_locator
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196e200-1111-7111-8111-111111111190',
    'urn:cwl:tenant_001:ea_core:target_state_evidence:0196e200-1111-7111-8111-111111111190',
    'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
    'verification://target-state/planner-gap-regression'
);

SELECT *
  FROM architecture_core.record_target_state_verification(
      '0195d145-64e8-7f4f-8a23-a0cc784cb711',
      '0196e010-1111-7111-8111-111111111191',
      '0196e210-1111-7111-8111-111111111190',
      '2027-05-05T00:00:00Z',
      'keyverse:https://id.example/realms/cwl#target-state-verifier-123',
      'Regression evidence detects a target-state gap.',
      '0196e200-1111-7111-8111-111111111190',
      'gap_detected'
  );

DO $$
DECLARE
  planned_row record;
BEGIN
  SELECT *
    INTO planned_row
    FROM architecture_core.project_technology_target_state_plan(
        '0196f100-1111-7111-8111-111111111111',
        '2027-05-05T00:00:00Z',
        clock_timestamp(),
        180
    )
   WHERE application_object_id = '0196f130-3333-7333-8333-333333333333'
     AND external_object_kind_code = 'database_schema';

  IF planned_row.transformation_state_code <> 'gap_detected'
     OR planned_row.decision_readiness_code <> 'plan_blocked'
     OR planned_row.recommended_action_code <> 'replan_target_state' THEN
    RAISE EXCEPTION 'gap-detected target state does not route the buyer to replanning';
  END IF;
END;
$$;

ROLLBACK;
