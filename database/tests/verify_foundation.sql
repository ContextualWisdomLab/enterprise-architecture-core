\set ON_ERROR_STOP on

CREATE ROLE ea_runtime NOLOGIN NOINHERIT;
GRANT USAGE ON SCHEMA architecture_core TO ea_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE
    ON ALL TABLES IN SCHEMA architecture_core TO ea_runtime;
GRANT EXECUTE
    ON ALL FUNCTIONS IN SCHEMA architecture_core TO ea_runtime;

DO $$
DECLARE
  object_type_count integer;
  relation_type_count integer;
  lifecycle_phase_count integer;
BEGIN
  SELECT count(*)
    INTO object_type_count
    FROM architecture_core.object_type
   WHERE object_type_code IN (
      'business_capability',
      'organization_unit',
      'application_record',
      'application_interface',
      'technology_provider',
      'technology_component',
      'technology_version'
   );
  SELECT count(*)
    INTO relation_type_count
    FROM architecture_core.relation_type
   WHERE relation_type_code IN (
      'supports_capability',
      'uses_technology',
      'exposes_interface',
      'consumes_interface',
      'provided_by',
      'has_version'
   );
  SELECT count(*)
    INTO lifecycle_phase_count
    FROM architecture_core.lifecycle_phase
   WHERE lifecycle_phase_code IN (
      'planned',
      'active',
      'phase_out',
      'end_of_life',
      'retired'
   );
  IF object_type_count <> 7 THEN
    RAISE EXCEPTION 'foundation object types missing: %', object_type_count;
  END IF;
  IF relation_type_count <> 6 THEN
    RAISE EXCEPTION 'foundation relation types missing: %', relation_type_count;
  END IF;
  IF lifecycle_phase_count <> 5 THEN
    RAISE EXCEPTION 'foundation lifecycle phases missing: %', lifecycle_phase_count;
  END IF;
END;
$$;

INSERT INTO architecture_core.tenant_record (
    tenant_record_id,
    tenant_code,
    tenant_title
) VALUES
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        'tenant_001',
        'Tenant One'
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb712',
        'tenant_002',
        'Tenant Two'
    );

INSERT INTO architecture_core.architecture_object (
    tenant_record_id,
    architecture_object_id,
    object_type_id,
    canonical_asset_uri
) VALUES
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0195d145-64e8-7f4f-8a23-a0cc784cb901',
        '0195d145-64e8-7f4f-8a23-a0cc784cb801',
        'urn:cwl:tenant_001:ea_core:business_capability:0195d145-64e8-7f4f-8a23-a0cc784cb901'
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        '0195d145-64e8-7f4f-8a23-a0cc784cb802',
        'urn:cwl:tenant_001:ea_core:application_record:0195d145-64e8-7f4f-8a23-a0cc784cb902'
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0195d145-64e8-7f4f-8a23-a0cc784cb903',
        '0195d145-64e8-7f4f-8a23-a0cc784cb803',
        'urn:cwl:tenant_001:ea_core:technology_component:0195d145-64e8-7f4f-8a23-a0cc784cb903'
    );

INSERT INTO architecture_core.business_capability (
    tenant_record_id,
    architecture_object_id,
    capability_code,
    capability_level
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0195d145-64e8-7f4f-8a23-a0cc784cb901',
    'order_fulfillment',
    1
);

INSERT INTO architecture_core.application_record (
    tenant_record_id,
    architecture_object_id,
    application_code,
    application_category_code
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0195d145-64e8-7f4f-8a23-a0cc784cb902',
    'legacy_order_platform',
    'business_application'
);

INSERT INTO architecture_core.technology_component (
    tenant_record_id,
    architecture_object_id,
    component_code,
    component_category_code
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0195d145-64e8-7f4f-8a23-a0cc784cb903',
    'acme_database_12',
    'database_platform'
);

SET ROLE ea_runtime;
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

DO $$
DECLARE
  visible_tenant_count integer;
BEGIN
  SELECT count(*)
    INTO visible_tenant_count
    FROM architecture_core.tenant_record;
  IF visible_tenant_count <> 1 THEN
    RAISE EXCEPTION
      'tenant row-level security exposed % tenants',
      visible_tenant_count;
  END IF;
END;
$$;

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.architecture_object (
        tenant_record_id,
        architecture_object_id,
        object_type_id,
        canonical_asset_uri
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb712',
        '0195d145-64e8-7f4f-8a23-a0cc784cb904',
        '0195d145-64e8-7f4f-8a23-a0cc784cb802',
        'urn:cwl:tenant_002:ea_core:application_record:0195d145-64e8-7f4f-8a23-a0cc784cb904'
    );
    RAISE EXCEPTION 'cross-tenant insert unexpectedly succeeded';
  EXCEPTION
    WHEN insufficient_privilege THEN NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.evidence_record (
        tenant_record_id,
        evidence_record_id,
        evidence_uri,
        sha256_digest
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '550e8400-e29b-41d4-a716-446655440000',
        'urn:cwl:evidence:invalid_uuid',
        repeat('a', 64)
    );
    RAISE EXCEPTION 'non-UUIDv7 identifier unexpectedly succeeded';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.architecture_object (
        tenant_record_id,
        architecture_object_id,
        object_type_id,
        canonical_asset_uri
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0195d145-64e8-7f4f-8a23-a0cc784cb905',
        '0195d145-64e8-7f4f-8a23-a0cc784cb802',
        'urn:cwl:tenant_002:ea_core:technology_component:0195d145-64e8-7f4f-8a23-a0cc784cb905'
    );
    RAISE EXCEPTION 'canonical URI mismatch unexpectedly succeeded';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.architecture_relation (
        tenant_record_id,
        architecture_relation_id,
        relation_type_id,
        source_object_id,
        target_object_id,
        valid_from,
        truth_status_code
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0195d145-64e8-7f4f-8a23-a0cc784cbb01',
        '0195d145-64e8-7f4f-8a23-a0cc784cb811',
        '0195d145-64e8-7f4f-8a23-a0cc784cb903',
        '0195d145-64e8-7f4f-8a23-a0cc784cb901',
        '2026-01-01T00:00:00Z',
        'authoritative'
    );
    RAISE EXCEPTION 'relation endpoint type mismatch unexpectedly succeeded';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

INSERT INTO architecture_core.architecture_relation (
    tenant_record_id,
    architecture_relation_id,
    relation_type_id,
    source_object_id,
    target_object_id,
    valid_from,
    valid_to,
    truth_status_code
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0195d145-64e8-7f4f-8a23-a0cc784cbb02',
    '0195d145-64e8-7f4f-8a23-a0cc784cb811',
    '0195d145-64e8-7f4f-8a23-a0cc784cb902',
    '0195d145-64e8-7f4f-8a23-a0cc784cb901',
    '2026-01-01T00:00:00Z',
    '2026-07-01T00:00:00Z',
    'authoritative'
);

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.architecture_relation (
        tenant_record_id,
        architecture_relation_id,
        relation_type_id,
        source_object_id,
        target_object_id,
        valid_from,
        truth_status_code
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0195d145-64e8-7f4f-8a23-a0cc784cbb03',
        '0195d145-64e8-7f4f-8a23-a0cc784cb811',
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        '0195d145-64e8-7f4f-8a23-a0cc784cb901',
        '2026-06-01T00:00:00Z',
        'authoritative'
    );
    RAISE EXCEPTION 'overlapping relation unexpectedly succeeded';
  EXCEPTION
    WHEN exclusion_violation THEN NULL;
  END;
END;
$$;

INSERT INTO architecture_core.object_revision (
    tenant_record_id,
    object_revision_id,
    architecture_object_id,
    revision_number,
    object_title,
    valid_from,
    valid_to,
    truth_status_code
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0195d145-64e8-7f4f-8a23-a0cc784cba01',
    '0195d145-64e8-7f4f-8a23-a0cc784cb902',
    1,
    'Legacy Order Platform',
    '2026-01-01T00:00:00Z',
    '2026-07-01T00:00:00Z',
    'authoritative'
);

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.object_revision (
        tenant_record_id,
        object_revision_id,
        architecture_object_id,
        revision_number,
        object_title,
        valid_from,
        truth_status_code
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0195d145-64e8-7f4f-8a23-a0cc784cba02',
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        2,
        'Overlapping Revision',
        '2026-06-01T00:00:00Z',
        'authoritative'
    );
    RAISE EXCEPTION 'overlapping object revision unexpectedly succeeded';
  EXCEPTION
    WHEN exclusion_violation THEN NULL;
  END;
END;
$$;

INSERT INTO architecture_core.identity_link (
    tenant_record_id,
    identity_link_id,
    issuer_uri,
    keyverse_subject_id,
    valid_from,
    valid_to
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0195d145-64e8-7f4f-8a23-a0cc784cbc01',
    'https://keyverse.example/issuer-a',
    'keyverse_subject_001',
    '2026-01-01T00:00:00Z',
    '2026-07-01T00:00:00Z'
);

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.identity_link (
        tenant_record_id,
        identity_link_id,
        issuer_uri,
        keyverse_subject_id,
        valid_from
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0195d145-64e8-7f4f-8a23-a0cc784cbc02',
        'https://keyverse.example/issuer-a',
        'keyverse_subject_001',
        '2026-06-01T00:00:00Z'
    );
    RAISE EXCEPTION 'overlapping identity link unexpectedly succeeded';
  EXCEPTION
    WHEN exclusion_violation THEN NULL;
  END;
END;
$$;

INSERT INTO architecture_core.lifecycle_interval (
    tenant_record_id,
    lifecycle_interval_id,
    architecture_object_id,
    lifecycle_phase_id,
    valid_from,
    valid_to
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0195d145-64e8-7f4f-8a23-a0cc784cbd01',
    '0195d145-64e8-7f4f-8a23-a0cc784cb902',
    '0195d145-64e8-7f4f-8a23-a0cc784cb821',
    '2026-01-01T00:00:00Z',
    '2027-01-01T00:00:00Z'
);

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.lifecycle_interval (
        tenant_record_id,
        lifecycle_interval_id,
        architecture_object_id,
        lifecycle_phase_id,
        valid_from
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0195d145-64e8-7f4f-8a23-a0cc784cbd02',
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        '0195d145-64e8-7f4f-8a23-a0cc784cb822',
        '2026-12-01T00:00:00Z'
    );
    RAISE EXCEPTION 'overlapping lifecycle interval unexpectedly succeeded';
  EXCEPTION
    WHEN exclusion_violation THEN NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.outbox_event (
        tenant_record_id,
        outbox_event_id,
        aggregate_object_id,
        event_type_code,
        event_payload_json,
        event_schema_version
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0195d145-64e8-7f4f-8a23-a0cc784cbe01',
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        'org.contextualwisdomlab.ea.object.changed.v1',
        '[]'::jsonb,
        '1.0.0'
    );
    RAISE EXCEPTION 'non-object outbox payload unexpectedly succeeded';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.projection_receipt (
        tenant_record_id,
        projection_receipt_id,
        event_source_uri,
        event_identifier,
        payload_sha256,
        schema_version
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf01',
        'urn:cwl:tenant_001:ea_core',
        '550e8400-e29b-41d4-a716-446655440000',
        repeat('b', 64),
        '1.0.0'
    );
    RAISE EXCEPTION 'non-UUIDv7 event identifier unexpectedly succeeded';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

BEGIN;
INSERT INTO architecture_core.outbox_event (
    tenant_record_id,
    outbox_event_id,
    aggregate_object_id,
    event_type_code,
    event_payload_json,
    event_schema_version
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0195d145-64e8-7f4f-8a23-a0cc784cbe02',
    '0195d145-64e8-7f4f-8a23-a0cc784cb902',
    'org.contextualwisdomlab.ea.object.changed.v1',
    '{"change_type":"test_rollback"}'::jsonb,
    '1.0.0'
);
ROLLBACK;

DO $$
DECLARE
  outbox_count integer;
BEGIN
  SELECT count(*)
    INTO outbox_count
    FROM architecture_core.outbox_event
   WHERE outbox_event_id = '0195d145-64e8-7f4f-8a23-a0cc784cbe02';
  IF outbox_count <> 0 THEN
    RAISE EXCEPTION 'rolled-back outbox event remained visible';
  END IF;
END;
$$;

RESET ROLE;
