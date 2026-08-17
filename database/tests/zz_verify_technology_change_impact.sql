\set ON_ERROR_STOP on

-- Buyer acceptance for the first Technology Change Impact & Target-State Planner
-- projection. The initial branch commit proved this test RED before migration
-- 0015 introduced the deterministic impact projector boundary.

DO $$
BEGIN
  IF to_regprocedure(
      'architecture_core.project_technology_change_impact(uuid,timestamptz,timestamptz,integer)'
     ) IS NULL THEN
    RAISE EXCEPTION 'technology change impact projector is missing';
  END IF;
END;
$$;

INSERT INTO architecture_core.architecture_object (
    tenant_record_id,
    architecture_object_id,
    object_type_id
) VALUES
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196f100-1111-7111-8111-111111111111',
        '0195d145-64e8-7f4f-8a23-a0cc784cb807'
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196f120-2222-7222-8222-222222222222',
        '0195d145-64e8-7f4f-8a23-a0cc784cb802'
    );

INSERT INTO architecture_core.technology_version (
    tenant_record_id,
    architecture_object_id,
    version_label,
    release_date,
    support_end_date
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196f100-1111-7111-8111-111111111111',
    '12.4',
    '2024-01-15',
    '2026-12-31'
);

INSERT INTO architecture_core.application_record (
    tenant_record_id,
    architecture_object_id,
    application_code,
    application_category_code
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196f120-2222-7222-8222-222222222222',
    'inventory_planning',
    'saas_application'
);

INSERT INTO architecture_core.architecture_relation (
    tenant_record_id,
    architecture_relation_id,
    relation_type_id,
    source_object_id,
    target_object_id,
    valid_from,
    recorded_at,
    truth_status_code,
    evidence_record_id
) VALUES
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196f101-1111-7111-8111-111111111111',
        '0195d145-64e8-7f4f-8a23-a0cc784cb816',
        '0195d145-64e8-7f4f-8a23-a0cc784cb903',
        '0196f100-1111-7111-8111-111111111111',
        '2026-01-01T00:00:00Z',
        '2026-08-01T00:00:00Z',
        'authoritative',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196f102-1111-7111-8111-111111111111',
        '0195d145-64e8-7f4f-8a23-a0cc784cb812',
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        '0195d145-64e8-7f4f-8a23-a0cc784cb903',
        '2026-01-01T00:00:00Z',
        '2026-08-01T00:00:00Z',
        'authoritative',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196f103-1111-7111-8111-111111111111',
        '0195d145-64e8-7f4f-8a23-a0cc784cb811',
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        '0195d145-64e8-7f4f-8a23-a0cc784cb901',
        '2026-07-01T00:00:00Z',
        '2026-09-01T00:00:00Z',
        'authoritative',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196f121-2222-7222-8222-222222222222',
        '0195d145-64e8-7f4f-8a23-a0cc784cb812',
        '0196f120-2222-7222-8222-222222222222',
        '0195d145-64e8-7f4f-8a23-a0cc784cb903',
        '2026-01-01T00:00:00Z',
        '2026-08-01T00:00:00Z',
        'proposed',
        NULL
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196f122-2222-7222-8222-222222222222',
        '0195d145-64e8-7f4f-8a23-a0cc784cb811',
        '0196f120-2222-7222-8222-222222222222',
        '0195d145-64e8-7f4f-8a23-a0cc784cb901',
        '2026-01-01T00:00:00Z',
        '2026-08-01T00:00:00Z',
        'proposed',
        NULL
    );

INSERT INTO architecture_core.lifecycle_interval (
    tenant_record_id,
    lifecycle_interval_id,
    architecture_object_id,
    lifecycle_phase_id,
    valid_from,
    valid_to,
    recorded_at,
    evidence_record_id
) VALUES
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196f110-1111-7111-8111-111111111111',
        '0196f100-1111-7111-8111-111111111111',
        '0195d145-64e8-7f4f-8a23-a0cc784cb821',
        '2026-01-01T00:00:00Z',
        '2026-10-01T00:00:00Z',
        '2026-08-01T00:00:00Z',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196f111-1111-7111-8111-111111111111',
        '0196f100-1111-7111-8111-111111111111',
        '0195d145-64e8-7f4f-8a23-a0cc784cb822',
        '2026-10-01T00:00:00Z',
        '2027-01-01T00:00:00Z',
        '2026-08-01T00:00:00Z',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196f112-1111-7111-8111-111111111111',
        '0196f100-1111-7111-8111-111111111111',
        '0195d145-64e8-7f4f-8a23-a0cc784cb824',
        '2027-01-01T00:00:00Z',
        NULL,
        '2026-08-01T00:00:00Z',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
    );

-- The projector is tenant-bound even when the migration acceptance connection
-- is the schema-owner test user. Every acceptance file runs in a fresh psql
-- session, so set the application tenant explicitly before invoking it.
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

DO $$
DECLARE
  impacted_row record;
BEGIN
  SELECT *
    INTO impacted_row
    FROM architecture_core.project_technology_change_impact(
        '0196f100-1111-7111-8111-111111111111',
        '2026-08-17T00:00:00Z',
        '2026-08-15T00:00:00Z',
        180
    )
   WHERE application_object_id = '0195d145-64e8-7f4f-8a23-a0cc784cb902';

  IF impacted_row.technology_component_id IS DISTINCT FROM
      '0195d145-64e8-7f4f-8a23-a0cc784cb903'::uuid
     OR impacted_row.application_object_id IS DISTINCT FROM
      '0195d145-64e8-7f4f-8a23-a0cc784cb902'::uuid THEN
    RAISE EXCEPTION 'technology-to-application impact path is incomplete';
  END IF;
  IF impacted_row.capability_object_id IS NOT NULL
     OR impacted_row.evidence_state_code <> 'missing_capability_mapping'
     OR impacted_row.recommended_action_code <> 'complete_capability_mapping' THEN
    RAISE EXCEPTION
      'late-recorded capability evidence leaked across the system-time cutoff';
  END IF;
  IF impacted_row.impact_status_code <> 'lifecycle_change_soon'
     OR impacted_row.lifecycle_phase_code <> 'active'
     OR impacted_row.lifecycle_change_at IS DISTINCT FROM
        '2026-10-01T00:00:00Z'::timestamptz THEN
    RAISE EXCEPTION 'bitemporal lifecycle horizon classification is incorrect';
  END IF;
END;
$$;

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
   WHERE application_object_id = '0195d145-64e8-7f4f-8a23-a0cc784cb902';

  IF impacted_row.capability_object_id IS DISTINCT FROM
      '0195d145-64e8-7f4f-8a23-a0cc784cb901'::uuid
     OR impacted_row.capability_code <> 'order_fulfillment'
     OR impacted_row.evidence_state_code <> 'complete' THEN
    RAISE EXCEPTION 'recorded capability impact evidence was not projected';
  END IF;
  IF impacted_row.recommended_action_code <> 'plan_target_state'
     OR impacted_row.version_relation_truth_status_code <> 'authoritative'
     OR impacted_row.usage_relation_truth_status_code <> 'authoritative'
     OR impacted_row.capability_relation_truth_status_code <> 'authoritative' THEN
    RAISE EXCEPTION 'impact action or truth provenance is incorrect';
  END IF;
END;
$$;

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
   WHERE application_object_id = '0196f120-2222-7222-8222-222222222222';

  IF impacted_row.evidence_state_code <> 'requires_truth_review'
     OR impacted_row.recommended_action_code <> 'review_truth_origin'
     OR impacted_row.usage_relation_truth_status_code <> 'proposed'
     OR impacted_row.capability_relation_truth_status_code <> 'proposed' THEN
    RAISE EXCEPTION
      'proposed dependency path silently became an actionable architecture fact';
  END IF;
END;
$$;

-- `technology_version.support_end_date` predates the bitemporal lifecycle model
-- and has no system-recording interval. Mutating that current metadata must not
-- rewrite a historical impact projection; lifecycle_interval is the auditable
-- source for time-travel risk classification.
UPDATE architecture_core.technology_version
   SET support_end_date = '2026-08-18'
 WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
   AND architecture_object_id = '0196f100-1111-7111-8111-111111111111';

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
   WHERE application_object_id = '0195d145-64e8-7f4f-8a23-a0cc784cb902';

  IF impacted_row.impact_status_code <> 'lifecycle_change_soon'
     OR impacted_row.lifecycle_change_at IS DISTINCT FROM
        '2026-10-01T00:00:00Z'::timestamptz THEN
    RAISE EXCEPTION
      'mutable non-temporal version metadata rewrote bitemporal impact history';
  END IF;
END;
$$;

DO $$
DECLARE
  impacted_row record;
BEGIN
  SELECT *
    INTO impacted_row
    FROM architecture_core.project_technology_change_impact(
        '0196f100-1111-7111-8111-111111111111',
        '2027-01-15T00:00:00Z',
        '2027-01-15T00:00:00Z',
        180
    )
   WHERE application_object_id = '0195d145-64e8-7f4f-8a23-a0cc784cb902';

  IF impacted_row.lifecycle_phase_code <> 'end_of_life'
     OR impacted_row.impact_status_code <> 'end_of_life'
     OR impacted_row.recommended_action_code <> 'start_remediation' THEN
    RAISE EXCEPTION 'end-of-life impact did not escalate to remediation';
  END IF;
END;
$$;

DO $$
BEGIN
  BEGIN
    PERFORM *
      FROM architecture_core.project_technology_change_impact(
          '0196f100-1111-7111-8111-111111111111',
          '2026-08-17T00:00:00Z',
          '2026-09-15T00:00:00Z',
          0
      );
    RAISE EXCEPTION 'unbounded planning horizon was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;

  BEGIN
    PERFORM *
      FROM architecture_core.project_technology_change_impact(
          '0196f199-1111-7111-8111-111111111111',
          '2026-08-17T00:00:00Z',
          '2026-09-15T00:00:00Z',
          180
      );
    RAISE EXCEPTION 'unknown technology version was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;
