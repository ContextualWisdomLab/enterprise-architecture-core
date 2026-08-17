\set ON_ERROR_STOP on

-- Buyer acceptance for the cross-domain continuation of Technology Change
-- Impact. This test intentionally precedes migration 0016 so the first branch
-- commit is RED at the missing normalized projection boundary.

DO $$
BEGIN
  IF to_regclass('architecture_core.external_context_reference') IS NULL THEN
    RAISE EXCEPTION 'external context reference table is missing';
  END IF;
  IF to_regclass('architecture_core.application_context_projection') IS NULL THEN
    RAISE EXCEPTION 'application context projection table is missing';
  END IF;
  IF to_regprocedure(
      'architecture_core.project_application_context_impact(uuid,timestamptz,timestamptz)'
     ) IS NULL THEN
    RAISE EXCEPTION 'application context impact projector is missing';
  END IF;
END;
$$;

SET ROLE ea_runtime;
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
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
) VALUES
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196f200-1000-7100-8100-000000000001',
        'urn:cwl:tenant_001:pg_erd_cloud',
        '0196f200-1000-7100-8100-000000000101',
        repeat('1', 64),
        'context-assertion/v1',
        '2026-08-10T00:00:00Z',
        '2026-08-10T00:01:00Z',
        'processed'
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196f200-1000-7100-8100-000000000002',
        'urn:cwl:tenant_001:semantic_data_portal',
        '0196f200-1000-7100-8100-000000000102',
        repeat('2', 64),
        'context-assertion/v1',
        '2026-08-20T00:00:00Z',
        '2026-08-20T00:01:00Z',
        'processed'
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196f200-1000-7100-8100-000000000003',
        'urn:cwl:tenant_001:lineage_weave',
        '0196f200-1000-7100-8100-000000000103',
        repeat('3', 64),
        'context-assertion/v1',
        '2026-08-21T00:00:00Z',
        '2026-08-21T00:01:00Z',
        'processed'
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196f200-1000-7100-8100-000000000004',
        'urn:cwl:tenant_001:semantic_data_portal',
        '0196f200-1000-7100-8100-000000000104',
        repeat('4', 64),
        'context-assertion/v1',
        '2026-08-22T00:00:00Z',
        NULL,
        'received'
    );

INSERT INTO architecture_core.external_context_reference (
    tenant_record_id,
    external_context_reference_id,
    reference_authority_code,
    canonical_object_uri,
    external_object_kind_code,
    recorded_at
) VALUES
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196f200-2000-7200-8200-000000000001',
        'pg_erd_cloud',
        'urn:cwl:tenant_001:pg_erd_cloud:database_schema:0196f200-3000-7300-8300-000000000001',
        'database_schema',
        '2026-08-10T00:01:30Z'
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196f200-2000-7200-8200-000000000002',
        'semantic_data_portal',
        'urn:cwl:tenant_001:semantic_data_portal:data_product:0196f200-3000-7300-8300-000000000002',
        'data_product',
        '2026-08-20T00:01:30Z'
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196f200-2000-7200-8200-000000000003',
        'semantic_data_portal',
        'urn:cwl:tenant_001:semantic_data_portal:model:0196f200-3000-7300-8300-000000000003',
        'model',
        '2026-08-21T00:01:30Z'
    );

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.external_context_reference (
        tenant_record_id,
        external_context_reference_id,
        reference_authority_code,
        canonical_object_uri,
        external_object_kind_code
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196f200-2000-7200-8200-000000000004',
        'semantic_data_portal',
        'urn:cwl:tenant_002:semantic_data_portal:data_product:0196f200-3000-7300-8300-000000000004',
        'data_product'
    );
    RAISE EXCEPTION 'foreign-tenant external canonical URI was accepted';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

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
) VALUES
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196f200-4000-7400-8400-000000000001',
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        '0196f200-2000-7200-8200-000000000001',
        '0196f200-1000-7100-8100-000000000001',
        'depends_on',
        'observed',
        '2026-08-10T00:00:00Z',
        '2026-08-10T00:02:00Z'
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196f200-4000-7400-8400-000000000002',
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        '0196f200-2000-7200-8200-000000000002',
        '0196f200-1000-7100-8100-000000000002',
        'depends_on',
        'authoritative',
        '2026-08-20T00:00:00Z',
        '2026-08-20T00:02:00Z'
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196f200-4000-7400-8400-000000000003',
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        '0196f200-2000-7200-8200-000000000003',
        '0196f200-1000-7100-8100-000000000003',
        'impacts',
        'inferred',
        '2026-08-21T00:00:00Z',
        '2026-08-21T00:02:00Z'
    );

DO $$
BEGIN
  BEGIN
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
        '0196f200-4000-7400-8400-000000000004',
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        '0196f200-2000-7200-8200-000000000003',
        '0196f200-1000-7100-8100-000000000003',
        'impacts',
        'authoritative',
        '2026-08-21T00:00:00Z',
        '2026-08-21T00:03:00Z'
    );
    RAISE EXCEPTION 'LineageWeave proposal was promoted to authoritative';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
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
        '0196f200-4000-7400-8400-000000000005',
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        '0196f200-2000-7200-8200-000000000002',
        '0196f200-1000-7100-8100-000000000004',
        'depends_on',
        'authoritative',
        '2026-08-22T00:00:00Z',
        '2026-08-22T00:02:00Z'
    );
    RAISE EXCEPTION 'unprocessed event receipt became impact evidence';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

DO $$
DECLARE
  projected_count integer;
  projected_row record;
BEGIN
  SELECT count(*)
    INTO projected_count
    FROM architecture_core.project_application_context_impact(
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        '2026-08-17T00:00:00Z',
        '2026-08-17T00:00:00Z'
    );
  IF projected_count <> 1 THEN
    RAISE EXCEPTION
      'late-recorded cross-domain evidence leaked into historical projection: %',
      projected_count;
  END IF;

  SELECT *
    INTO projected_row
    FROM architecture_core.project_application_context_impact(
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        '2026-08-17T00:00:00Z',
        '2026-08-17T00:00:00Z'
    );
  IF projected_row.external_object_kind_code <> 'database_schema'
     OR projected_row.projection_source_code <> 'pg_erd_cloud'
     OR projected_row.truth_status_code <> 'observed'
     OR projected_row.recommended_action_code <> 'review_schema_dependency' THEN
    RAISE EXCEPTION 'physical-schema evidence was projected incorrectly';
  END IF;
END;
$$;

DO $$
DECLARE
  projected_count integer;
  data_product_action text;
  model_action text;
  model_truth text;
BEGIN
  SELECT count(*)
    INTO projected_count
    FROM architecture_core.project_application_context_impact(
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        '2026-08-22T12:00:00Z',
        '2026-08-22T12:00:00Z'
    );
  IF projected_count <> 3 THEN
    RAISE EXCEPTION 'cross-domain impact evidence is incomplete: %', projected_count;
  END IF;

  SELECT recommended_action_code
    INTO data_product_action
    FROM architecture_core.project_application_context_impact(
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        '2026-08-22T12:00:00Z',
        '2026-08-22T12:00:00Z'
    )
   WHERE external_object_kind_code = 'data_product';
  IF data_product_action <> 'review_data_product_impact' THEN
    RAISE EXCEPTION 'data-product evidence lacks a buyer next action';
  END IF;

  SELECT recommended_action_code, truth_status_code
    INTO model_action, model_truth
    FROM architecture_core.project_application_context_impact(
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        '2026-08-22T12:00:00Z',
        '2026-08-22T12:00:00Z'
    )
   WHERE external_object_kind_code = 'model';
  IF model_action <> 'review_truth_origin' OR model_truth <> 'inferred' THEN
    RAISE EXCEPTION 'inferred lineage silently became decision-ready';
  END IF;
END;
$$;

DO $$
BEGIN
  BEGIN
    PERFORM *
      FROM architecture_core.project_application_context_impact(
          '0195d145-64e8-7f4f-8a23-a0cc784cb902',
          NULL,
          '2026-08-22T12:00:00Z'
      );
    RAISE EXCEPTION 'NULL valid-time cutoff was accepted';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
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
      FROM architecture_core.project_application_context_impact(
          '0195d145-64e8-7f4f-8a23-a0cc784cb902',
          '2026-08-22T12:00:00Z',
          '2026-08-22T12:00:00Z'
      );
    RAISE EXCEPTION 'cross-tenant application impact was visible';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

RESET ROLE;
