\set ON_ERROR_STOP on

-- Buyer acceptance for converting semantic-data-portal assessment gaps into
-- provenance-preserving EA improvement work. This file intentionally lands
-- before migration 0031 so the first hosted candidate fails at the missing
-- executable boundary rather than at a source-text assertion.

RESET ROLE;
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

DO $$
DECLARE
  missing_table_count integer;
BEGIN
  SELECT count(*)
    INTO missing_table_count
    FROM (VALUES
      ('data_management_assessment_projection'),
      ('assessment_missing_evidence_projection'),
      ('assessment_improvement_plan')
    ) AS required_table(table_name)
   WHERE to_regclass('architecture_core.' || required_table.table_name) IS NULL;

  IF missing_table_count <> 0 THEN
    RAISE EXCEPTION
      'data-management improvement tables missing: %',
      missing_table_count;
  END IF;
END;
$$;

INSERT INTO architecture_core.architecture_object (
    tenant_record_id,
    architecture_object_id,
    object_type_id
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196f100-1111-7111-8111-111111111110',
    '0195d145-64e8-7f4f-8a23-a0cc784cb804'
)
ON CONFLICT DO NOTHING;

INSERT INTO architecture_core.organization_unit (
    tenant_record_id,
    architecture_object_id,
    organization_code,
    organization_kind_code
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196f100-1111-7111-8111-111111111110',
    'data_governance_office',
    'functional_owner'
)
ON CONFLICT DO NOTHING;

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
    '0196f100-1111-7111-8111-111111111111',
    'urn:cwl:tenant_001:semantic_data_portal',
    '0196f100-1111-7111-8111-111111111121',
    repeat('c', 64),
    '1.0.0',
    '2026-08-18T00:00:02Z',
    '2026-08-18T00:00:03Z',
    'processed'
);

DO $$
DECLARE
  inserted_projection_id uuid;
  inserted_plan_id uuid;
  inserted_initiative_id uuid;
  inserted_milestone_id uuid;
  inserted_event_id uuid;
  replay_plan_id uuid;
  source_truth text;
  initiative_truth text;
  missing_code_count integer;
  event_count integer;
BEGIN
  SELECT result.data_management_assessment_projection_id
    INTO inserted_projection_id
    FROM architecture_core.record_data_management_assessment_result(
      '0196f100-1111-7111-8111-111111111111',
      'urn:cwl:tenant_001:data_context:data_management_assessment:0196f101-1111-7111-8111-111111111111',
      'urn:cwl:tenant_001:ea_core:business_capability:0195d145-64e8-7f4f-8a23-a0cc784cb901',
      'dama_dmbok2r',
      '2024',
      'baseline_data_management',
      '1.0.0',
      '2026-08-18T00:00:00Z',
      '2026-08-18T00:00:01Z',
      7600,
      'evidence_gap',
      'observed',
      'urn:cwl:tenant_001:data_context:assessment_evidence:0196f102-1111-7111-8111-111111111111',
      repeat('d', 64),
      'https://example.com/evidence/assessment-001',
      NULL,
      ARRAY['control_evidence', 'stewardship_evidence']::text[]
    ) AS result;

  IF inserted_projection_id IS NULL THEN
    RAISE EXCEPTION 'assessment projection did not return an identity';
  END IF;

  SELECT count(*), max(projection.truth_status_code)
    INTO missing_code_count, source_truth
    FROM architecture_core.assessment_missing_evidence_projection AS missing
    JOIN architecture_core.data_management_assessment_projection AS projection
      ON projection.tenant_record_id = missing.tenant_record_id
     AND projection.data_management_assessment_projection_id =
         missing.data_management_assessment_projection_id
   WHERE missing.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND missing.data_management_assessment_projection_id = inserted_projection_id;

  IF missing_code_count <> 2 OR source_truth IS DISTINCT FROM 'observed' THEN
    RAISE EXCEPTION
      'assessment projection lost normalized gaps or source truth: %, %',
      missing_code_count,
      source_truth;
  END IF;

  SELECT
      result.assessment_improvement_plan_id,
      result.remediation_initiative_id,
      result.initiative_milestone_id,
      result.outbox_event_id
    INTO
      inserted_plan_id,
      inserted_initiative_id,
      inserted_milestone_id,
      inserted_event_id
    FROM architecture_core.create_data_management_improvement_plan(
      inserted_projection_id,
      'control_evidence',
      '0196f103-1111-7111-8111-111111111111',
      '0195d145-64e8-7f4f-8a23-a0cc784cb901',
      '0196f100-1111-7111-8111-111111111110',
      'close_control_evidence_gap',
      'Close control evidence gap',
      'control_evidence_accepted',
      'Control evidence accepted',
      '2026-11-30T00:00:00Z',
      'portfolio://fy2026/data-governance'
    ) AS result;

  IF inserted_plan_id IS NULL
     OR inserted_initiative_id IS NULL
     OR inserted_milestone_id IS NULL
     OR inserted_event_id IS NULL THEN
    RAISE EXCEPTION 'improvement plan did not return complete receipt identities';
  END IF;

  SELECT truth_status_code
    INTO initiative_truth
    FROM architecture_core.remediation_initiative
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND remediation_initiative_id = inserted_initiative_id;

  IF initiative_truth IS DISTINCT FROM 'proposed' THEN
    RAISE EXCEPTION
      'assessment evidence was silently promoted to authoritative initiative: %',
      initiative_truth;
  END IF;

  SELECT count(*)
    INTO event_count
    FROM architecture_core.outbox_event
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND outbox_event_id = inserted_event_id
     AND aggregate_object_id = '0195d145-64e8-7f4f-8a23-a0cc784cb901'
     AND event_type_code =
         'org.contextualwisdomlab.ea.data_management.improvement_initiative_created.v1'
     AND event_payload_json ->> 'assessment_result_uri' =
         'urn:cwl:tenant_001:data_context:data_management_assessment:0196f101-1111-7111-8111-111111111111'
     AND event_payload_json ->> 'missing_evidence_code' = 'control_evidence'
     AND NOT (event_payload_json ? 'provenance_source_locator')
     AND NOT (event_payload_json ? 'funding_reference');

  IF event_count <> 1 THEN
    RAISE EXCEPTION 'privacy-minimized improvement outbox evidence missing';
  END IF;

  SELECT result.assessment_improvement_plan_id
    INTO replay_plan_id
    FROM architecture_core.create_data_management_improvement_plan(
      inserted_projection_id,
      'control_evidence',
      '0196f103-1111-7111-8111-111111111111',
      '0195d145-64e8-7f4f-8a23-a0cc784cb901',
      '0196f100-1111-7111-8111-111111111110',
      'close_control_evidence_gap',
      'Close control evidence gap',
      'control_evidence_accepted',
      'Control evidence accepted',
      '2026-11-30T00:00:00Z',
      'portfolio://fy2026/data-governance'
    ) AS result;

  IF replay_plan_id IS DISTINCT FROM inserted_plan_id THEN
    RAISE EXCEPTION 'exact decision replay created a different improvement plan';
  END IF;

  SELECT count(*)
    INTO event_count
    FROM architecture_core.outbox_event
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND event_type_code =
         'org.contextualwisdomlab.ea.data_management.improvement_initiative_created.v1'
     AND event_payload_json ->> 'decision_request_id' =
         '0196f103-1111-7111-8111-111111111111';

  IF event_count <> 1 THEN
    RAISE EXCEPTION 'exact replay emitted % improvement events', event_count;
  END IF;
END;
$$;

DO $$
DECLARE
  projection_id uuid;
BEGIN
  SELECT data_management_assessment_projection_id
    INTO projection_id
    FROM architecture_core.data_management_assessment_projection
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND assessment_result_uri =
         'urn:cwl:tenant_001:data_context:data_management_assessment:0196f101-1111-7111-8111-111111111111';

  BEGIN
    PERFORM *
      FROM architecture_core.create_data_management_improvement_plan(
        projection_id,
        'stewardship_evidence',
        '0196f103-1111-7111-8111-111111111111',
        '0195d145-64e8-7f4f-8a23-a0cc784cb901',
        '0196f100-1111-7111-8111-111111111110',
        'close_other_gap',
        'Close another gap',
        'other_evidence_accepted',
        'Other evidence accepted',
        '2026-12-15T00:00:00Z',
        NULL
      );
    RAISE EXCEPTION 'conflicting decision replay was accepted';
  EXCEPTION WHEN unique_violation OR check_violation THEN
    NULL;
  END;
END;
$$;

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
    '0196f100-1111-7111-8111-111111111112',
    'urn:cwl:tenant_001:semantic_data_portal',
    '0196f100-1111-7111-8111-111111111122',
    repeat('e', 64),
    '1.0.0',
    '2026-09-18T00:00:02Z',
    '2026-09-18T00:00:03Z',
    'processed'
);

DO $$
DECLARE
  replacement_projection_id uuid;
  prior_plan_count integer;
  prior_superseded_at timestamptz;
BEGIN
  SELECT result.data_management_assessment_projection_id
    INTO replacement_projection_id
    FROM architecture_core.record_data_management_assessment_result(
      '0196f100-1111-7111-8111-111111111112',
      'urn:cwl:tenant_001:data_context:data_management_assessment:0196f101-1111-7111-8111-111111111112',
      'urn:cwl:tenant_001:ea_core:business_capability:0195d145-64e8-7f4f-8a23-a0cc784cb901',
      'dama_dmbok2r',
      '2024',
      'baseline_data_management',
      '1.0.0',
      '2026-09-18T00:00:00Z',
      '2026-09-18T00:00:01Z',
      8100,
      'evidence_gap',
      'observed',
      'urn:cwl:tenant_001:data_context:assessment_evidence:0196f102-1111-7111-8111-111111111112',
      repeat('f', 64),
      'https://example.com/evidence/assessment-002',
      'urn:cwl:tenant_001:data_context:data_management_assessment:0196f101-1111-7111-8111-111111111111',
      ARRAY['stewardship_evidence']::text[]
    ) AS result;

  IF replacement_projection_id IS NULL THEN
    RAISE EXCEPTION 'superseding assessment projection was not recorded';
  END IF;

  SELECT superseded_at
    INTO prior_superseded_at
    FROM architecture_core.data_management_assessment_projection
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND assessment_result_uri =
         'urn:cwl:tenant_001:data_context:data_management_assessment:0196f101-1111-7111-8111-111111111111';

  SELECT count(*)
    INTO prior_plan_count
    FROM architecture_core.assessment_improvement_plan AS plan_record
    JOIN architecture_core.data_management_assessment_projection AS projection
      ON projection.tenant_record_id = plan_record.tenant_record_id
     AND projection.data_management_assessment_projection_id =
         plan_record.data_management_assessment_projection_id
   WHERE plan_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND projection.assessment_result_uri =
         'urn:cwl:tenant_001:data_context:data_management_assessment:0196f101-1111-7111-8111-111111111111';

  IF prior_superseded_at IS NULL OR prior_plan_count <> 1 THEN
    RAISE EXCEPTION
      'superseding assessment rewrote historical improvement work: %, %',
      prior_superseded_at,
      prior_plan_count;
  END IF;
END;
$$;

SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb712',
    false
);

DO $$
BEGIN
  BEGIN
    PERFORM *
      FROM architecture_core.record_data_management_assessment_result(
        '0196f100-1111-7111-8111-111111111111',
        'urn:cwl:tenant_001:data_context:data_management_assessment:0196f101-1111-7111-8111-111111111113',
        'urn:cwl:tenant_001:ea_core:business_capability:0195d145-64e8-7f4f-8a23-a0cc784cb901',
        'dama_dmbok2r',
        '2024',
        'baseline_data_management',
        '1.0.0',
        '2026-10-18T00:00:00Z',
        '2026-10-18T00:00:01Z',
        5000,
        'evidence_gap',
        'observed',
        'urn:cwl:tenant_001:data_context:assessment_evidence:0196f102-1111-7111-8111-111111111113',
        repeat('a', 64),
        NULL,
        NULL,
        ARRAY['control_evidence']::text[]
      );
    RAISE EXCEPTION 'cross-tenant assessment projection unexpectedly succeeded';
  EXCEPTION WHEN check_violation OR foreign_key_violation THEN
    NULL;
  END;
END;
$$;

SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);
