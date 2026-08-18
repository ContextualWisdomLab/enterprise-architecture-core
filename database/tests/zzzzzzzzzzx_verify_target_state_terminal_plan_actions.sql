\set ON_ERROR_STOP on

-- Regression: the canonical buyer planner must understand the terminal states
-- introduced after migration 0020. A verified target stays under monitoring;
-- a later gap_detected observation must route directly to governed replanning.

SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
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
     OR planned_row.recommended_action_code <> 'continue_monitoring' THEN
    RAISE EXCEPTION 'verified target state is not actionable in the canonical planner';
  END IF;
END;
$$;

BEGIN;

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
