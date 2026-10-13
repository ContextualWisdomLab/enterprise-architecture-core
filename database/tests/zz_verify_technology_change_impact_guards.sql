\set ON_ERROR_STOP on

-- Fail-closed boundary regressions for the buyer-facing impact projector.
-- These cases intentionally exercise ambiguous NULL cutoffs and incomplete
-- lifecycle provenance that must never produce a decision-ready action.
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

DO $$
BEGIN
  BEGIN
    PERFORM *
      FROM architecture_core.project_technology_change_impact(
          '0196f100-1111-7111-8111-111111111111',
          NULL,
          '2026-09-15T00:00:00Z',
          180
      );
    RAISE EXCEPTION 'NULL valid-time cutoff was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;

  BEGIN
    PERFORM *
      FROM architecture_core.project_technology_change_impact(
          '0196f100-1111-7111-8111-111111111111',
          '2026-08-17T00:00:00Z',
          NULL,
          180
      );
    RAISE EXCEPTION 'NULL system-time cutoff was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;

  BEGIN
    PERFORM *
      FROM architecture_core.project_technology_change_impact(
          '0196f100-1111-7111-8111-111111111111',
          '2026-08-17T00:00:00Z',
          '2026-09-15T00:00:00Z',
          NULL
      );
    RAISE EXCEPTION 'NULL planning horizon was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;

BEGIN;

UPDATE architecture_core.lifecycle_interval
   SET evidence_record_id = NULL
 WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
   AND lifecycle_interval_id = '0196f111-1111-7111-8111-111111111111';

DO $$
DECLARE
  impacted_row record;
BEGIN
  SELECT *
    INTO impacted_row
    FROM architecture_core.project_technology_change_impact(
        '0196f100-1111-7111-8111-111111111111',
        '2026-08-17T00:00:00Z',
        '2026-09-15T00:00:00Z',
        180
    )
   WHERE application_object_id = '0196f130-3333-7333-8333-333333333333';

  IF impacted_row.impact_status_code <> 'lifecycle_change_soon'
     OR impacted_row.lifecycle_evidence_record_id IS NOT NULL
     OR impacted_row.evidence_state_code <> 'missing_lifecycle_evidence'
     OR impacted_row.recommended_action_code <> 'complete_lifecycle_evidence' THEN
    RAISE EXCEPTION
      'risk-driving lifecycle transition without provenance became actionable';
  END IF;
END;
$$;

ROLLBACK;
